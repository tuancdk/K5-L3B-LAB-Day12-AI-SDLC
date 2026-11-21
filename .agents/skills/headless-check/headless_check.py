"""Chạy headless 2 lần cùng seed và so byte; chạy smoke hộp đen gather -> kho -> quan. Chỉ thư viện chuẩn.

    python3 .agents/skills/headless-check/headless_check.py [--seed 1] [--ticks 600] [--out FILE]
"""

import argparse
import hashlib
import json
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def headless_cmd():
    with open(ROOT / "game.contract.json", encoding="utf-8") as f:
        cmd = shlex.split(json.load(f)["headless_cmd"])
    if cmd and cmd[0] in ("python3", "python") and shutil.which(cmd[0]) is None:
        cmd[0] = sys.executable  # Windows thường không có python3
    return cmd


def item_schema():
    with open(ROOT / "game.contract.json", encoding="utf-8") as f:
        v = json.load(f)["contract_version"]
    return tuple(int(x) for x in v.split(".")) >= (1, 2)


def inventory_doc(counts):
    if not item_schema():
        return {"items": counts}
    kinds = [k for k in sorted(counts) for _ in range(counts[k])]
    return {"items": [{"id": f"I{i}", "kind": k, "fresh": 100} for i, k in enumerate(kinds, 1)]}


def run(*args):
    p = subprocess.run([*headless_cmd(), *map(str, args)], cwd=ROOT, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"exit {p.returncode}: {' '.join(map(str, args))}\n{p.stderr}")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


def write(path, obj):
    Path(path).write_text(json.dumps(obj), encoding="utf-8")
    return path


def check_same(tmp, mode, seed, ticks, extra, with_inv=False):
    outs = []
    for i in (1, 2):
        args = ["--mode", mode, "--seed", seed, "--ticks", ticks, "--out", tmp / f"{mode}{i}.jsonl", *extra]
        if with_inv:
            args += ["--inventory-out", tmp / f"{mode}{i}.inv.json"]
        run(*args)
        outs.append(tmp / f"{mode}{i}.jsonl")
    same = outs[0].read_bytes() == outs[1].read_bytes()
    detail = f"jsonl {sha(outs[0])} vs {sha(outs[1])}"
    if with_inv:
        a, b = tmp / f"{mode}1.inv.json", tmp / f"{mode}2.inv.json"
        if a.exists() or b.exists():
            same = same and a.exists() and b.exists() and a.read_bytes() == b.read_bytes()
            detail += f"; kho {a.exists() and sha(a)} vs {b.exists() and sha(b)}"
        else:
            detail += "; kho chưa ghi (buổi sáng chưa kết thúc)"
    return same, detail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--ticks", type=int, default=600)
    ap.add_argument("--out")
    a = ap.parse_args()

    lines, ok = [f"headless_cmd: {' '.join(headless_cmd())} · seed {a.seed} · ticks {a.ticks}"], True
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        gin = write(tmp / "g-in.json", {"frames": [
            {"tick": 0, "move": [1, 1]}, {"tick": 60, "move": [1, 0], "catch": True}, {"tick": 61, "catch": False},
            {"tick": 120, "move": [0, -1]}, {"tick": 240, "move": [-1, 0], "interact": True},
            {"tick": 241, "interact": False}, {"tick": 400, "move": [0, 0]}]})
        qinv = write(tmp / "q-inv.json", inventory_doc({"ca_loc": 5, "bong_sung": 6, "ca_linh": 6, "bong_dien_dien": 2}))
        qin = write(tmp / "q-in.json", {"frames": [{"tick": 0, "move": [-1, 1]}, {"tick": 130, "interact": True},
                                                   {"tick": 131, "interact": False, "move": [0, 0]}]})
        checks = [
            ("tất định gather", lambda: check_same(tmp, "gather", a.seed, a.ticks, ["--inputs", gin], with_inv=True)),
            ("tất định quan", lambda: check_same(tmp, "quan", a.seed, max(a.ticks, 1200),
                                                 ["--inputs", qin, "--inventory", qinv])),
            ("smoke dock → quan", lambda: smoke(tmp)),
            ("tất định day --days 2", lambda: check_same(tmp, "day", a.seed, 50000, ["--days", 2, "--snapshot-every", 600])),
            ("day --days 1 hoàn tất", lambda: day_smoke(tmp)),
        ]
        for name, fn in checks:
            try:
                good, detail = fn()
            except Exception as e:  # noqa: BLE001 — báo lỗi thay vì dừng giữa chừng
                good, detail = False, str(e).strip()
            ok = ok and good
            lines.append(f"{'PASS' if good else 'FAIL'}  {name}: {detail}")
    text = "\n".join(lines)
    print(text)
    if a.out:
        Path(ROOT / a.out).parent.mkdir(parents=True, exist_ok=True)
        (ROOT / a.out).write_text(text + "\n", encoding="utf-8")
    return 0 if ok else 1


def day_smoke(tmp):
    """Một Ngày không pause: 22.200 tick, end.reason days_complete, chạy <= 20 s."""
    import time
    out = tmp / "day1.jsonl"
    t0 = time.monotonic()
    run("--mode", "day", "--days", 1, "--seed", 1, "--ticks", 30000, "--snapshot-every", 600, "--out", out)
    dt = time.monotonic() - t0
    end = json.loads(out.read_text(encoding="utf-8").splitlines()[-1])
    ok = end.get("reason") == "days_complete" and end.get("days_completed") == 1 and dt <= 20
    return ok, f"end {end.get('reason')} ticks {end.get('ticks')} days_completed {end.get('days_completed')} · {dt:.2f}s"


def smoke(tmp):
    hold = ["ca_loc", "bong_sung", "bong_sung"]
    if item_schema():  # v1.2: giỏ/kho cá thể (TICKET-03)
        hold = [{"id": f"I{i}", "kind": k, "fresh": 100} for i, k in enumerate(hold, 1)]
    sc = write(tmp / "dock.json", {"gather": {"hold": hold}})
    inp = write(tmp / "dock-inputs.json", {"frames": [{"tick": 0, "interact": True}]})
    inv = tmp / "catch.json"
    run("--mode", "gather", "--seed", 42, "--scenario", sc, "--inputs", inp, "--ticks", 1,
        "--inventory-out", inv, "--out", tmp / "gather.jsonl")
    run("--mode", "quan", "--seed", 42, "--inventory", inv, "--ticks", 0, "--out", tmp / "quan.jsonl")
    first = json.loads((tmp / "quan.jsonl").read_text(encoding="utf-8").splitlines()[0])
    want = json.loads(inv.read_text(encoding="utf-8"))["items"] if item_schema() else {"bong_sung": 2, "ca_loc": 1}
    got = first.get("stock")
    if item_schema():  # v1.2: id/kind chính xác, fresh trong dung sai quan sát ±0.01 (JSONL làm tròn 3 số)
        ok = (isinstance(got, list) and [(i["id"], i["kind"]) for i in got] == [(i["id"], i["kind"]) for i in want]
              and all(abs(g["fresh"] - w["fresh"]) <= 0.01 for g, w in zip(got, want)))
    else:
        ok = got == want
    return ok, f"kho {inv.read_text(encoding='utf-8').strip()} → stock tick 0 {first.get('stock')}"


if __name__ == "__main__":
    sys.exit(main())

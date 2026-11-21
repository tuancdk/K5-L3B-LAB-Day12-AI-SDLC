"""Tiện ích test: chạy headless, đọc JSONL, dựng fixture, so sánh có dung sai."""

import json
import math
import os
import shlex
import subprocess
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f)
    return path


def frames(*fr):
    return {"frames": list(fr)}


def headless_cmd():
    """Lệnh headless khai trong game.contract.json — test chạy qua đây nên dùng được với MỌI ngôn ngữ."""
    with open(os.path.join(ROOT, "game.contract.json"), encoding="utf-8") as f:
        return shlex.split(json.load(f)["headless_cmd"])


def run_headless(*args, cwd=ROOT):
    """Chạy `<headless_cmd> <args>`; trả (mã thoát, stderr)."""
    p = subprocess.run([*headless_cmd(), *args], cwd=cwd, capture_output=True, text=True)
    return p.returncode, p.stderr


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def snapshots(rows):
    return [r for r in rows if r["type"] == "snapshot"]


def events(rows, name=None):
    return [r for r in rows if r["type"] == "event" and (name is None or r["name"] == name)]


def close(a, b, tol=0.1):
    return abs(a - b) <= tol


def dist(p, q):
    return math.dist(p, q)


class Workdir:
    """Thư mục tạm tự dọn: with Workdir() as w: w.path('x.json')."""

    def __enter__(self):
        self._d = tempfile.TemporaryDirectory()
        return self

    def __exit__(self, *a):
        self._d.cleanup()

    def path(self, name):
        return os.path.join(self._d.name, name)


def items(*kinds, start=1, fresh=100):
    """Kho/giỏ cá thể v1.2 (TICKET-03): id I<start>, I<start+1>… theo thứ tự, fresh mặc định 100."""
    return [{"id": f"I{start + i}", "kind": k, "fresh": fresh} for i, k in enumerate(kinds)]


def stock_items(counts, start=1, fresh=100):
    """Object đếm v1.0 -> mảng cá thể v1.2 (loại sắp theo tên)."""
    return items(*[k for k in sorted(counts) for _ in range(counts[k])], start=start, fresh=fresh)


def item_counts(arr):
    out = {}
    for it in arr:
        out[it["kind"]] = out.get(it["kind"], 0) + 1
    return out


def assert_items_close(tc, got, want, tol=0.01):
    """So mảng cá thể: id/kind chính xác, fresh trong dung sai quan sát (TICKET-03: ±0.01)."""
    tc.assertEqual([(it["id"], it["kind"]) for it in got], [(it["id"], it["kind"]) for it in want])
    for g, w in zip(got, want):
        tc.assertAlmostEqual(g["fresh"], w["fresh"], delta=tol, msg=g["id"])


def decayed(n_steps, per_s=0.5, start=100):
    """Độ tươi sau n bước hao (giỏ 0.5/s, kho quán 0.25/s), 60 tick/s."""
    return start - per_s * n_steps / 60

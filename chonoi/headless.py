"""Điểm vào headless: python3 -m chonoi.headless --mode gather --seed 1 --ticks 600 --out out.jsonl

Mã thoát: 0 bình thường; 2 tham số/đầu vào sai (kiểm TRƯỚC khi ghi đầu ra); 1 lỗi chạy/ghi.
"""

import argparse
import os
import sys
import tempfile
from contextlib import contextmanager

from .contract import load_contract
from .errors import BadInput
from .inputs import load_frames
from .items import load_game_inputs
from .runner import run


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write(f"lỗi: {message}\n")
        sys.exit(2)


def _int(name):
    def conv(s):
        try:
            return int(s)
        except ValueError:
            raise argparse.ArgumentTypeError(f"{name} phải là số nguyên")
    return conv


@contextmanager
def _output_path(mode, path):
    if mode != "day":
        yield path
        return
    # Một fixture có thể mâu thuẫn khi quán nhận kho cuối buổi sáng.
    with tempfile.TemporaryDirectory(dir=os.path.dirname(os.path.abspath(path))) as folder:
        staged = os.path.join(folder, "day.jsonl")
        yield staged
        os.replace(staged, path)


def main(argv=None) -> int:
    p = _Parser(prog="chonoi.headless")
    p.add_argument("--mode", required=True, choices=["gather", "quan", "day"])  # `day` có từ v1.1
    p.add_argument("--seed", required=True, type=_int("seed"))
    p.add_argument("--ticks", required=True, type=_int("ticks"))
    p.add_argument("--out", required=True)
    p.add_argument("--scenario")
    p.add_argument("--inputs")
    p.add_argument("--inventory")
    p.add_argument("--inventory-out", dest="inventory_out")
    p.add_argument("--snapshot-every", dest="snapshot_every", type=_int("snapshot-every"), default=10)
    p.add_argument("--days", type=_int("days"))
    a = p.parse_args(argv)
    try:
        if a.days is not None and a.mode != "day":
            raise BadInput("--days chỉ dùng với day")
        days = 1 if a.days is None else a.days
        if not 1 <= days <= 5:
            raise BadInput("--days phải trong [1, 5]")
        if a.mode == "day" and (a.inventory or a.inventory_out):
            raise BadInput("day chuyển kho trong bộ nhớ, không nhận --inventory/--inventory-out")
        if a.ticks < 0:
            raise BadInput("--ticks phải >= 0")
        if a.snapshot_every <= 0:
            raise BadInput("--snapshot-every phải > 0")
        if a.inventory and a.mode != "quan":
            raise BadInput("--inventory chỉ dùng với quan")
        if a.inventory_out and a.mode != "gather":
            raise BadInput("--inventory-out chỉ dùng với gather")
        outs = [x for x in (a.out, a.inventory_out) if x]
        ins = [x for x in (a.scenario, a.inputs, a.inventory) if x]
        paths = [os.path.abspath(x) for x in outs + ins]
        if len(set(paths)) != len(paths):
            raise BadInput("các đường dẫn đầu vào/đầu ra phải khác nhau")
        contract = load_contract()
        tuning = contract["tuning"]
        scenario, inventory, ledger = load_game_inputs(a.mode, contract, a.scenario, a.inventory)
        frames = load_frames(a.inputs)
    except BadInput as e:
        sys.stderr.write(f"đầu vào sai: {e}\n")
        return 2
    try:
        with _output_path(a.mode, a.out) as out:
            run(a.mode, tuning, scenario, a.seed, frames, a.ticks, out, a.snapshot_every,
                inventory=inventory, inventory_out=a.inventory_out, days=days, ledger=ledger)
    except BadInput as e:  # lỗi mức luật phát hiện lúc dựng sim
        sys.stderr.write(f"đầu vào sai: {e}\n")
        return 2
    except OSError as e:
        sys.stderr.write(f"lỗi ghi: {e}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

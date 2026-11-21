"""Tests Phase 4 cho `chonoi/soak.py` và mở rộng `DaySim` cho soak > 5 Ngày (Issue #31)."""

import json
import os
import subprocess
import sys
import unittest

from chonoi.contract import load_contract
from chonoi.sim.day import DaySim, day_plan_for
from chonoi.soak import run_soak

from helpers import ROOT, Workdir, run_headless


def run_soak_cli(*args):
    p = subprocess.run([sys.executable, "-B", "-m", "chonoi.soak", *args],
                       cwd=ROOT, capture_output=True, text=True)
    return p.returncode, p.stderr


class SoakTests(unittest.TestCase):
    def test_cli_bad_flags_exit_2_without_writing_out(self):
        with Workdir() as w:
            out = w.path("soak.json")
            for args in (
                ("--seed", "7", "--days", "0", "--out", out),
                ("--seed", "7", "--days", "-2", "--out", out),
                ("--seed", "abc", "--days", "1", "--out", out),
                ("--seed", "7", "--days", "1", "--out", out, "--unknown"),
                ("--days", "1", "--out", out),
            ):
                code, _ = run_soak_cli(*args)
                self.assertEqual(code, 2, args)
                self.assertFalse(os.path.exists(out), f"không được ghi file khi sai cờ: {args}")

    def test_headless_day_mode_still_rejects_days_6(self):
        with Workdir() as w:
            out = w.path("day6.jsonl")
            code, _ = run_headless("--mode", "day", "--days", "6", "--seed", "1", "--ticks", "0", "--out", out)
            self.assertEqual(code, 2)
            self.assertFalse(os.path.exists(out))

    def test_day_plan_cycles_d1_to_d5_for_days_6_to_10(self):
        t = load_contract()["tuning"]
        for d in range(1, 6):
            p_base = day_plan_for(t, None, d)
            p_cycled = day_plan_for(t, None, d + 5, cycle=True)
            self.assertEqual(p_cycled["day"], d + 5)
            self.assertEqual(p_cycled["dishes"], p_base["dishes"])
            self.assertEqual(p_cycled["ingredients"], p_base["ingredients"])

    def test_soak_10_days_deterministic_and_no_extra_files(self):
        with Workdir() as w:
            out1 = w.path("s1.json")
            out2 = w.path("s2.json")
            code1, err1 = run_soak_cli("--seed", "7", "--days", "10", "--out", out1)
            code2, err2 = run_soak_cli("--seed", "7", "--days", "10", "--out", out2)
            self.assertEqual(code1, 0, err1)
            self.assertEqual(code2, 0, err2)
            with open(out1, encoding="utf-8") as f1, open(out2, encoding="utf-8") as f2:
                d1, d2 = json.load(f1), json.load(f2)
            self.assertEqual(set(d1), {"days", "days_completed", "crashes", "results", "duration_s"})
            self.assertEqual(d1["days"], 10)
            self.assertEqual(d1["days_completed"], 10)
            self.assertEqual(d1["crashes"], 0)
            self.assertEqual(len(d1["results"]), 10)
            self.assertEqual([r["day"] for r in d1["results"]], list(range(1, 11)))
            self.assertGreater(d1["results"][-1]["earned"], 0)
            self.assertGreaterEqual(d1["duration_s"], 0)
            for r in d1["results"]:
                self.assertEqual(set(r), {"day", "earned", "reputation", "score"})
            # Mọi trường trừ duration_s phải giống hệt nhau
            cmp1 = {k: v for k, v in d1.items() if k != "duration_s"}
            cmp2 = {k: v for k, v in d2.items() if k != "duration_s"}
            self.assertEqual(cmp1, cmp2)
            # Chỉ có đúng 2 file output, không ghi thêm bảng xếp hạng
            self.assertEqual(sorted(os.listdir(os.path.dirname(out1))), ["s1.json", "s2.json"])

    def test_soak_catches_day_exception_counts_crash_and_continues(self):
        class CrashingDay2(DaySim):
            def __init__(self, *args, **kw):
                super().__init__(*args, **kw)
                self._crashed_once = False

            def step(self, inp):
                if self.day == 2 and not self._crashed_once:
                    self._crashed_once = True
                    raise RuntimeError("injected day 2 failure")
                return super().step(inp)

        t = load_contract()["tuning"]
        report = run_soak(t, seed=7, days=3, day_sim_cls=CrashingDay2)
        self.assertEqual(report["days"], 3)
        self.assertEqual(report["crashes"], 1)
        self.assertEqual(report["days_completed"], 2)
        self.assertEqual([r["day"] for r in report["results"]], [1, 3])


if __name__ == "__main__":
    unittest.main()

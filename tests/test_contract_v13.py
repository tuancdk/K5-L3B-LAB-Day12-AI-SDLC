"""Contract v1.3 (Phase 4, issue #30): bench_cmd, soak_cmd ở gốc manifest; gameplay giữ v1.2."""

import json
import os
import shlex
import subprocess
import unittest

from helpers import Workdir

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def contract():
    with open(os.path.join(ROOT, "game.contract.json"), encoding="utf-8") as f:
        return json.load(f)


class ContractV13(unittest.TestCase):
    def test_version_and_commands_declared(self):
        c = contract()
        self.assertEqual(c["contract_version"], "1.3")
        for key in ("headless_cmd", "run_cmd", "bench_cmd", "soak_cmd"):
            self.assertTrue(isinstance(c[key], str) and c[key].strip(), key)
        self.assertIn("freshness", c["tuning"])  # gameplay/kho theo v1.2

    def test_soak_cmd_runs_from_manifest(self):
        cmd = shlex.split(contract()["soak_cmd"])
        with Workdir() as w:
            out = w.path("soak.json")
            p = subprocess.run([*cmd, "--seed", "7", "--days", "2", "--out", out], cwd=ROOT,
                               capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            with open(out, encoding="utf-8") as f:
                soak = json.load(f)
        self.assertEqual((soak["days"], soak["days_completed"], soak["crashes"]), (2, 2, 0))
        for key in ("results", "duration_s"):
            self.assertIn(key, soak)

    def test_bench_cmd_exists(self):
        cmd = shlex.split(contract()["bench_cmd"])
        p = subprocess.run([*cmd, "--help"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("--duration", p.stdout)


if __name__ == "__main__":
    unittest.main()

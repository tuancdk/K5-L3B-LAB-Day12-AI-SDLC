"""Smoke hộp đen tích hợp Phase 1 (PRD-0 mục G, docs/contracts/README.md mục 5).

Hai tiến trình headless dùng chung file kho: gather cập bến ở tick 0 -> ghi kho -> quán đọc kho ở tick 0.
"""

import json
import unittest

from helpers import Workdir, events, frames, items, read_jsonl, run_headless, snapshots, write_json


class SmokeDockToQuan(unittest.TestCase):
    def _gather(self, w, name):
        sc = write_json(w.path("dock.json"), {"gather": {"hold": items("ca_loc", "bong_sung", "bong_sung")}})
        inp = write_json(w.path("dock-inputs.json"), frames({"tick": 0, "interact": True}))
        inv = w.path(f"{name}.json")
        code, err = run_headless("--mode", "gather", "--seed", "42", "--scenario", sc, "--inputs", inp,
                                 "--ticks", "1", "--inventory-out", inv, "--out", w.path(f"{name}.jsonl"))
        self.assertEqual(code, 0, err)
        return inv, read_jsonl(w.path(f"{name}.jsonl"))

    def test_prd_smoke_dock_then_quan_stock(self):
        with Workdir() as w:
            inv, rows = self._gather(w, "catch")
            end = [e for e in events(rows) if e["name"] == "gather_end"]
            self.assertEqual(len(end), 1)
            self.assertEqual(end[0]["tick"], 1)
            self.assertEqual(end[0]["data"]["reason"], "docked")
            self.assertEqual(end[0]["data"]["inventory"], {"items": items("ca_loc", "bong_sung", "bong_sung")})
            self.assertEqual(rows[-1]["type"], "end")
            self.assertEqual(rows[-1]["reason"], "docked")
            with open(inv, encoding="utf-8") as f:
                self.assertEqual(json.load(f), end[0]["data"]["inventory"])

            code, err = run_headless("--mode", "quan", "--seed", "42", "--inventory", inv, "--ticks", "0",
                                     "--out", w.path("quan.jsonl"))
            self.assertEqual(code, 0, err)
            s0 = snapshots(read_jsonl(w.path("quan.jsonl")))[0]
            self.assertEqual(s0["tick"], 0)
            self.assertEqual(s0["stock"], items("ca_loc", "bong_sung", "bong_sung"))

    def test_inventory_file_bytes_stable(self):
        with Workdir() as w:
            a, _ = self._gather(w, "a")
            b, _ = self._gather(w, "b")
            with open(a, "rb") as fa, open(b, "rb") as fb:
                self.assertEqual(fa.read(), fb.read())


if __name__ == "__main__":
    unittest.main()

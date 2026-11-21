"""Contract v1.2 — kho cá thể {id, kind, fresh} (TICKET-03, issue #18). Hộp đen qua headless_cmd."""

import json
import os
import unittest

from helpers import Workdir, assert_items_close, decayed, events, frames, items, read_jsonl, run_headless, snapshots, write_json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def contract():
    with open(os.path.join(ROOT, "game.contract.json"), encoding="utf-8") as f:
        return json.load(f)


class ContractV12(unittest.TestCase):
    def test_version_and_freshness(self):
        c = contract()
        self.assertIn(c["contract_version"], ("1.2", "1.3"))  # v1.3 (P4) giữ schema kho v1.2
        self.assertEqual(c["tuning"]["freshness"], {"initial": 100, "gather_decay_per_s": 0.5,
                                                    "quan_decay_per_s": 0.25, "spoiled_below": 30})


class InventoryFile(unittest.TestCase):
    def quan_stock(self, w, inv_items):
        inv = write_json(w.path("in.json"), {"items": inv_items})
        code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "0", "--inventory", inv,
                                 "--out", w.path("q.jsonl"))
        return code, err, (snapshots(read_jsonl(w.path("q.jsonl")))[0]["stock"] if code == 0 else None)

    def test_reader_rejects_count_schema_and_bad_items(self):
        bad = [
            {"items": {"ca_loc": 1}},                                          # schema đếm v1.0
            {"items": [{"id": "I1", "kind": "ca_loc", "fresh": 100}], "x": 1},  # khóa gốc lạ
            {"items": [{"id": "I1", "kind": "ca_loc"}]},                       # thiếu fresh
            {"items": items("ca_loc", "ca_loc", start=1) + items("ca_linh", start=1)},  # id trùng
            {"items": [{"id": "", "kind": "ca_loc", "fresh": 100}]},
            {"items": [{"id": "I1", "kind": "ca_la_lung", "fresh": 100}]},
            {"items": [{"id": "I1", "kind": "ca_loc", "fresh": 100.5}]},
            {"items": [{"id": "I1", "kind": "ca_loc", "fresh": -0.1}]},
            {"items": [{"id": "I1", "kind": "ca_loc", "fresh": True}]},
            {"items": [{"id": 1, "kind": "ca_loc", "fresh": 50}]},
        ]
        with Workdir() as w:
            out = w.path("q.jsonl")
            for doc in bad:
                inv = write_json(w.path("bad.json"), doc)
                code, _ = run_headless("--mode", "quan", "--seed", "1", "--ticks", "0", "--inventory", inv, "--out", out)
                self.assertEqual(code, 2, doc)
                self.assertFalse(os.path.exists(out))

    def test_quan_keeps_ids_fresh_and_spoiled_items_and_ignores_hold_capacity(self):
        cap = contract()["tuning"]["gather"]["hold_capacity"]
        inv_items = [{"id": f"I{i}", "kind": "ca_linh", "fresh": 100 - i * 3.5} for i in range(1, cap + 6)]
        inv_items.append({"id": "X9", "kind": "keo_neo", "fresh": 0})
        with Workdir() as w:
            code, err, stock = self.quan_stock(w, inv_items)
        self.assertEqual(code, 0, err)
        self.assertEqual(sorted(stock, key=lambda it: it["id"]), sorted(inv_items, key=lambda it: it["id"]))
        self.assertEqual(len(stock), cap + 6)

    def test_empty_inventory(self):
        with Workdir() as w:
            code, err, stock = self.quan_stock(w, [])
        self.assertEqual((code, stock), (0, []), err)


class SmokeHandover(unittest.TestCase):
    """Mẫu đề TICKET-03: giỏ 1 cá thể fresh 100, interact frame 0 cập bến -> quan --inventory --ticks 0."""

    def test_prd_smoke_file_then_quan_exact_items(self):
        sc_doc = {"gather": {"hold": [{"id": "I1", "kind": "ca_linh", "fresh": 100}], "random_fish": False,
                             "monsters": []}}
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), sc_doc)
            inp = write_json(w.path("in.json"), frames({"tick": 0, "interact": True}))
            inv = w.path("kho.json")
            code, err = run_headless("--mode", "gather", "--seed", "42", "--scenario", sc, "--inputs", inp,
                                     "--ticks", "1", "--inventory-out", inv, "--out", w.path("g.jsonl"))
            self.assertEqual(code, 0, err)
            with open(inv, encoding="utf-8") as f:
                saved = json.load(f)
            end = events(read_jsonl(w.path("g.jsonl")), "gather_end")[0]["data"]
            assert_items_close(self, end["inventory"]["items"], saved["items"])
            self.assertAlmostEqual(saved["items"][0]["fresh"], 100 - 0.5 / 60, places=9)  # hao 1 bước, đủ chính xác
            self.assertEqual([(it["id"], it["kind"]) for it in saved["items"]], [("I1", "ca_linh")])
            code, err = run_headless("--mode", "quan", "--seed", "42", "--inventory", inv, "--ticks", "0",
                                     "--out", w.path("q.jsonl"))
            self.assertEqual(code, 0, err)
            assert_items_close(self, snapshots(read_jsonl(w.path("q.jsonl")))[0]["stock"], saved["items"])

    def test_new_items_continue_ids_after_fixture_in_hold_order(self):
        sc_doc = {"gather": {"hold": [{"id": "I7", "kind": "bong_sung", "fresh": 80}],
                             "player": {"pos": [10, 0]}, "random_fish": False, "monsters": [],
                             "nodes": [{"id": "N1", "kind": "bong_dien_dien", "pos": [10, 0]}]}}
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), sc_doc)
            inp = write_json(w.path("in.json"), frames({"tick": 0, "interact": True}))
            code, err = run_headless("--mode", "gather", "--seed", "1", "--scenario", sc, "--inputs", inp,
                                     "--ticks", "2", "--snapshot-every", "1", "--out", w.path("g.jsonl"))
            self.assertEqual(code, 0, err)
            hold = snapshots(read_jsonl(w.path("g.jsonl")))[-1]["hold"]
        self.assertEqual([(it["id"], it["kind"]) for it in hold], [("I7", "bong_sung"), ("I8", "bong_dien_dien")])


class DayHandover(unittest.TestCase):
    def test_ids_increase_across_days_and_handover_same_tick(self):
        sc_doc = {"gather": {"hold": items("ca_loc", "bong_sung", "bong_sung")}, "quan": {"time_left_ticks": 3}}
        inp = frames({"tick": 0, "interact": True}, {"tick": 1, "interact": False},
                     {"tick": 6, "shop_done": True}, {"tick": 7, "shop_done": False},
                     {"tick": 8, "interact": True})
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), sc_doc)
            ip = write_json(w.path("in.json"), inp)
            code, err = run_headless("--mode", "day", "--days", "2", "--seed", "5", "--ticks", "20",
                                     "--scenario", sc, "--inputs", ip, "--snapshot-every", "1",
                                     "--out", w.path("d.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("d.jsonl"))
        s = {r["tick"]: r for r in snapshots(rows)}
        self.assertEqual(s[1]["phase"], "quan")
        assert_items_close(self, s[1]["stock"], items("ca_loc", "bong_sung", "bong_sung", fresh=decayed(1)))
        day2 = [r for r in snapshots(rows) if r["day"] == 2 and r["phase"] == "gather"]
        self.assertTrue(day2)
        self.assertEqual([it["id"] for it in day2[0]["hold"]], ["I4", "I5", "I6"])
        self.assertEqual([it["kind"] for it in day2[0]["hold"]], ["ca_loc", "bong_sung", "bong_sung"])


if __name__ == "__main__":
    unittest.main()

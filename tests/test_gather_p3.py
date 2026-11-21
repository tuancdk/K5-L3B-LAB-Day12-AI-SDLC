"""Tests Phase 3 cho giỏ cá thể & độ tươi trong `chonoi/sim/gather.py` + `monsters.py` (Issue #19)."""

from copy import deepcopy
import unittest

from chonoi.contract import load_contract
from chonoi.ids import IdAllocator
from chonoi.inputs import InputPlayer
from chonoi.rng import Streams
from chonoi.runner import Session
from chonoi.sim.gather import GatherSim


def tuning_v12():
    t = deepcopy(load_contract()["tuning"])
    t["freshness"] = {
        "initial": 100,
        "gather_decay_per_s": 0.5,
        "quan_decay_per_s": 0.25,
        "spoiled_below": 30,
    }
    return t


def run_session(sess, frame_list, n_steps):
    pl = InputPlayer(frame_list)
    out = []
    for k in range(n_steps):
        if sess.done:
            break
        out.extend(sess.step(pl.advance(k)))
    return out


class GatherFreshnessAndItemHold(unittest.TestCase):
    def test_prd_threshold_30_spoils_at_tick_1_and_once_only(self):
        sc = {"hold": [{"id": "I1", "kind": "ca_linh", "fresh": 30}],
              "random_fish": False, "monsters": []}
        sess = Session("gather", tuning_v12(), sc, 1)
        evs1 = run_session(sess, [], 1)
        self.assertEqual([(e["tick"], e["name"], e["data"]) for e in evs1], [
            (1, "spoiled", {"item_id": "I1", "kind": "ca_linh", "location": "hold"}),
        ])
        snap1 = sess.snapshot()
        self.assertEqual(snap1["hold_count"], 1)  # hàng ươn vẫn chiếm ô
        self.assertLess(snap1["hold"][0]["fresh"], 30)
        self.assertAlmostEqual(snap1["hold"][0]["fresh"], 30 - 0.5 / 60, places=3)

        # Bước 2 không phát spoiled lặp lại
        evs2 = run_session(sess, [], 2)
        self.assertEqual([e for e in evs2 if e["name"] == "spoiled"], [])

    def test_multiple_items_spoil_in_numeric_id_order_and_clamp_at_zero(self):
        sc = {"hold": [
            {"id": "I10", "kind": "ca_loc", "fresh": 30},
            {"id": "I2", "kind": "bong_sung", "fresh": 30},
            {"id": "I3", "kind": "keo_neo", "fresh": 0},
        ], "random_fish": False, "monsters": []}
        sess = Session("gather", tuning_v12(), sc, 1)
        evs = run_session(sess, [], 2)
        spoiled = [(e["tick"], e["data"]["item_id"]) for e in evs if e["name"] == "spoiled"]
        self.assertEqual(spoiled, [(1, "I2"), (1, "I10")])
        by_id = {x["id"]: x for x in sess.snapshot()["hold"]}
        self.assertEqual(by_id["I3"]["fresh"], 0)

    def test_gather_and_catch_create_items_decay_from_next_tick_and_exact_8401(self):
        # Hái 1 nút ở tick 0 (fresh=100, chưa hao ở bước hái), sau đó chạy 8400 bước -> đúng 30 (chưa ươn), bước 8401 -> ươn
        t = tuning_v12()
        t["gather"]["duration_s"] = 300
        sc = {"player": {"pos": [12, 0]},
              "nodes": [{"id": "N1", "kind": "bong_dien_dien", "pos": [12, 0]}],
              "fish": [], "random_fish": False, "monsters": []}
        sess = Session("gather", t, sc, 1)
        evs0 = run_session(sess, [{"tick": 0, "interact": True}], 1)
        self.assertEqual([e["name"] for e in evs0], ["gather"])
        self.assertEqual(sess.snapshot()["hold"], [{"id": "I1", "kind": "bong_dien_dien", "fresh": 100}])

        # 8400 bước tiếp (140s * 0.5/s = 70 điểm -> còn đúng 30, chưa spoiled)
        evs_mid = run_session(sess, [], 8400)
        self.assertEqual([e for e in evs_mid if e["name"] == "spoiled"], [])
        self.assertEqual(sess.snapshot()["hold"][0]["fresh"], 30)

        # Bước thứ 8401 (tick 8402): tụt xuống dưới 30 -> spoiled đúng 1 lần
        evs_spoil = run_session(sess, [], 1)
        self.assertEqual([e["name"] for e in evs_spoil], ["spoiled"])
        self.assertLess(sess.snapshot()["hold"][0]["fresh"], 30)

    def test_catch_allocates_sequential_ids_and_pause_stops_decay(self):
        sc = {"player": {"pos": [20, 5]},
              "hold": [{"id": "I2", "kind": "bong_sung", "fresh": 80}],
              "fish": [{"id": "F1", "kind": "ca_keo", "pos": [20, 5]}],
              "random_fish": False, "monsters": []}
        sess = Session("gather", tuning_v12(), sc, 1)
        # Bước 0 bắt ca_keo (yield=2) -> tạo I3, I4 với fresh=100; I2 đã hao 1 tick
        evs = run_session(sess, [
            {"tick": 0, "catch": True},
            {"tick": 1, "catch": False, "pause": True},
            {"tick": 2, "pause": False},
            {"tick": 5, "pause": True},  # resume ở tick 5 -> chạy gameplay bước 5
            {"tick": 6, "pause": False},
        ], 6)
        self.assertIn("fish_caught", [e["name"] for e in evs])
        hold = sess.snapshot()["hold"]
        self.assertEqual([x["id"] for x in hold], ["I2", "I3", "I4"])
        # Chỉ có 1 bước gameplay sau khi bắt (bước 5 sau resume), nên I3/I4 chỉ hao đúng 1 tick
        self.assertAlmostEqual(hold[1]["fresh"], 100 - 0.5 / 60, places=3)
        self.assertAlmostEqual(hold[2]["fresh"], 100 - 0.5 / 60, places=3)

    def test_monster_hit_and_faint_drop_individual_items_lifo_and_empty_inventory(self):
        sc = {"player": {"pos": [60, 24], "hp": 1},
              "hold": [
                  {"id": "I1", "kind": "bong_sung", "fresh": 90},
                  {"id": "I2", "kind": "ca_loc", "fresh": 80},
                  {"id": "I3", "kind": "ca_linh", "fresh": 70},
              ],
              "fish": [], "random_fish": False,
              "monsters": [{"id": "M1", "kind": "ca_sau", "pos": [60.5, 24.0], "waypoints": [[60, 24], [64, 24]]}]}
        sess = Session("gather", tuning_v12(), sc, 1)
        evs = run_session(sess, [], 1)
        self.assertEqual([e["name"] for e in evs], ["monster_hit", "faint", "gather_end"])
        # monster_hit bỏ floor(3/2)=1 là I3 (LIFO)
        hit_lost = evs[0]["data"]["lost"]
        self.assertEqual(len(hit_lost), 1)
        self.assertEqual((hit_lost[0]["id"], hit_lost[0]["kind"]), ("I3", "ca_linh"))
        self.assertLess(hit_lost[0]["fresh"], 70)
        # faint bỏ phần còn lại LIFO: I2 rồi I1
        faint_lost = evs[1]["data"]["lost"]
        self.assertEqual([x["id"] for x in faint_lost], ["I2", "I1"])
        # gather_end.inventory rỗng dạng mảng
        self.assertEqual(evs[2]["data"], {"reason": "fainted", "inventory": {"items": []}})

    def test_inventory_sorted_by_id_and_day2_reallocates_template_ids(self):
        t = tuning_v12()
        ids = IdAllocator()
        # Ngày 1 giữ nguyên id mẫu I10, I2
        s1 = GatherSim(t, {"hold": [{"id": "I10", "kind": "ca_loc", "fresh": 90},
                                    {"id": "I2", "kind": "bong_sung", "fresh": 80}],
                           "fish": [], "monsters": []}, Streams(1), ids,
                       day_ctx={"day": 1, "day_plan": t["day_plan"][0], "active_upgrades": {"oxygen": 0, "hp": 0}})
        self.assertEqual([x["id"] for x in s1.inventory_items()], ["I2", "I10"])

        # Ngày 2 cấp id mới nối tiếp sau I10 -> I11, I12
        s2 = GatherSim(t, {"hold": [{"id": "I10", "kind": "ca_loc", "fresh": 90},
                                    {"id": "I2", "kind": "bong_sung", "fresh": 80}],
                           "fish": [], "monsters": []}, Streams(1), ids,
                       day_ctx={"day": 2, "day_plan": t["day_plan"][1], "active_upgrades": {"oxygen": 0, "hp": 0}})
        self.assertEqual([x["id"] for x in s2.snapshot()["hold"]], ["I11", "I12"])


if __name__ == "__main__":
    unittest.main()

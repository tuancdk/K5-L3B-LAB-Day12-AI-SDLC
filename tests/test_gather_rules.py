"""Unit & headless tests cho luật buổi sáng (`chonoi/sim/gather.py`, PRD-0 mục E/F/G)."""

from copy import deepcopy
import json
import unittest

from chonoi.contract import load_contract
from chonoi.inputs import InputPlayer, load_frames
from chonoi.runner import Session

from helpers import (Workdir, events, frames, read_jsonl, run_headless, snapshots, write_json)


def make_session(scenario=None, seed=1, tuning=None):
    t = deepcopy(load_contract()["tuning"]) if tuning is None else deepcopy(tuning)
    return Session("gather", t, deepcopy(scenario or {}), seed)


def run_steps(sess, frame_list, n_steps):
    pl = InputPlayer(frame_list)
    all_events = []
    for k in range(n_steps):
        if sess.done:
            break
        all_events.extend(sess.step(pl.advance(k)))
    return all_events


class GatherOxygenAndHealthRules(unittest.TestCase):
    def test_dive_and_surface_events_only_on_crossing(self):
        sc = {"player": {"pos": [20, 0.5]}, "fish": [], "nodes": [], "random_fish": False}
        sess = make_session(sc)
        evs = run_steps(sess, [
            {"tick": 0, "move": [0, 1]},    # xuống d > 0.5 ngay tick 1 -> dive
            {"tick": 15, "move": [0, -1]},  # quay lên mặt nước -> surface
        ], 45)
        dives = [e for e in evs if e["name"] == "dive"]
        surfs = [e for e in evs if e["name"] == "surface"]
        self.assertEqual(len(dives), 1)
        self.assertEqual(dives[0]["tick"], 1)
        self.assertGreater(dives[0]["data"]["pos"][1], 0.5)
        self.assertEqual(len(surfs), 1)
        self.assertGreater(surfs[0]["tick"], dives[0]["tick"])
        self.assertLessEqual(surfs[0]["data"]["pos"][1], 0.5)
        self.assertTrue(sess.snapshot()["player"]["at_surface"])

    def test_oxygen_drain_underwater_and_refill_clamped_at_surface(self):
        # Dưới nước: giảm 1/tick, phát oxygen_empty đúng 1 lần khi từ dương xuống 0
        sc = {"player": {"pos": [20, 5.0], "oxygen_ticks": 2}, "fish": [], "nodes": [], "random_fish": False}
        sess = make_session(sc)
        evs = run_steps(sess, [], 5)
        empties = [e for e in evs if e["name"] == "oxygen_empty"]
        self.assertEqual(len(empties), 1)
        self.assertEqual(empties[0]["tick"], 2)
        self.assertEqual(empties[0]["data"], {"oxygen_ticks": 0})
        self.assertEqual(sess.snapshot()["player"]["oxygen_ticks"], 0)
        self.assertEqual(sess.snapshot()["player"]["zero_oxy_ticks"], 4)

        # Mặt nước: hồi oxygen_refill_per_tick (6), kẹp tối đa oxygen_max_ticks
        sc_surf = {"player": {"pos": [20, 0.5], "oxygen_ticks": 1796}, "fish": [], "nodes": [], "random_fish": False}
        sess2 = make_session(sc_surf)
        run_steps(sess2, [], 1)
        self.assertEqual(sess2.snapshot()["player"]["oxygen_ticks"], sess2.snapshot()["player"]["oxygen_max_ticks"])
        self.assertEqual(sess2.snapshot()["player"]["zero_oxy_ticks"], 0)

    def test_choke_exact_timing_t_plus_59_and_resets_counter(self):
        # Chạm oxy 0 ở tick t=1 và ở dưới nước liên tục -> ngạt lần đầu ở t+59 = 60, lần 2 ở 120
        sc = {"player": {"pos": [20, 5.0], "oxygen_ticks": 1, "hp": 3},
              "fish": [], "nodes": [], "random_fish": False}
        sess = make_session(sc)
        evs = run_steps(sess, [], 125)
        empties = [e for e in evs if e["name"] == "oxygen_empty"]
        chokes = [e for e in evs if e["name"] == "choke"]
        self.assertEqual([e["tick"] for e in empties], [1])
        self.assertEqual([(e["tick"], e["data"]) for e in chokes], [(60, {"hp": 2}), (120, {"hp": 1})])
        self.assertEqual(sess.snapshot()["player"]["zero_oxy_ticks"], 5)

    def test_surfacing_on_choke_tick_prevents_choke_and_resets_counter(self):
        # Đang ở d=0.51, vel=[0, -4], oxy=0, zero_oxy_ticks=59, hp=1: nổi lên ngay bước 1 -> không ngạt
        sc = {"player": {"pos": [20, 0.51], "vel": [0, -4.0], "oxygen_ticks": 0, "zero_oxy_ticks": 59, "hp": 1},
              "fish": [], "nodes": [], "random_fish": False}
        sess = make_session(sc)
        evs = run_steps(sess, [{"tick": 0, "move": [0, -1]}], 1)
        self.assertEqual([e["name"] for e in evs], ["surface"])
        p = sess.snapshot()["player"]
        self.assertTrue(p["at_surface"])
        self.assertEqual(p["oxygen_ticks"], 6)
        self.assertEqual(p["zero_oxy_ticks"], 0)
        self.assertEqual(p["hp"], 1)
        self.assertFalse(sess.done)

    def test_faint_drops_hold_in_lifo_order_and_stops_step(self):
        # Ở trong bán kính bến (d=1.0 <= dock_radius=3) nhưng ngạt mất HP cuối ở bước 1 -> ngất trước khi cập bến
        sc = {"player": {"pos": [2, 1.0], "oxygen_ticks": 0, "zero_oxy_ticks": 59, "hp": 1},
              "hold": ["ca_loc", "bong_sung", "ca_linh"],
              "time_left_ticks": 1, "fish": [], "nodes": [], "random_fish": False}
        sess = make_session(sc)
        evs = run_steps(sess, [{"tick": 0, "interact": True}], 2)
        self.assertEqual([e["name"] for e in evs], ["choke", "faint", "gather_end"])
        self.assertEqual(evs[0]["data"], {"hp": 0})
        self.assertEqual(evs[1]["data"], {"cause": "choke", "lost": ["ca_linh", "bong_sung", "ca_loc"], "hp": 0})
        self.assertEqual(evs[2]["data"], {"reason": "fainted", "inventory": {"items": {}}})
        self.assertTrue(sess.done)
        self.assertEqual(sess.end_row()["reason"], "fainted")
        self.assertEqual(sess.snapshot()["hold"], [])

    def test_custom_tuning_drives_oxygen_refill_choke_and_yield(self):
        tuning = deepcopy(load_contract()["tuning"])
        g = tuning["gather"]
        g["oxygen_refill_per_tick"] = 10
        g["choke_interval_ticks"] = 5
        g["node_yield"] = 2
        g["regrow_s"] = 0.5
        g["catch_cooldown_s"] = 0.1
        g["fish_yield"] = {"ca_linh": 2, "ca_loc": 1}
        g["hold_capacity"] = 6
        # Choke theo choke_interval_ticks = 5 -> chạm oxy 0 ở tick 1, choke ở tick 5
        sc = {"player": {"pos": [20, 5.0], "oxygen_ticks": 1, "hp": 2},
              "fish": [{"id": "F1", "kind": "ca_linh", "pos": [20, 5.0]}],
              "nodes": [], "random_fish": False}
        sess = make_session(sc, tuning=tuning)
        evs = run_steps(sess, [{"tick": 0, "catch": True}], 5)
        caught = [e for e in evs if e["name"] == "fish_caught"]
        chokes = [e for e in evs if e["name"] == "choke"]
        self.assertEqual(caught[0]["data"]["yield"], 2)
        self.assertEqual(chokes[0]["tick"], 5)
        self.assertEqual(sess.snapshot()["hold"], ["ca_linh", "ca_linh"])


class GatherNodesFishAndHoldRules(unittest.TestCase):
    def test_dock_takes_priority_over_gather_and_works_on_final_tick(self):
        # Đứng đúng mép bến (dock_pos=[2,0], dock_radius=3 -> pos=[5,0]) có nút sẵn ngay đó, time_left_ticks=1
        sc = {"player": {"pos": [5, 0]},
              "hold": ["ca_loc"],
              "nodes": [{"id": "N1", "kind": "bong_dien_dien", "pos": [5, 0]}],
              "fish": [], "random_fish": False, "time_left_ticks": 1}
        sess = make_session(sc)
        evs = run_steps(sess, [{"tick": 0, "interact": True}], 2)
        self.assertEqual([e["name"] for e in evs], ["gather_end"])
        self.assertEqual(evs[0]["data"], {"reason": "docked", "inventory": {"items": {"ca_loc": 1}}})
        self.assertEqual(sess.end_row()["reason"], "docked")

    def test_gather_requires_surface_inclusive_radius_and_numeric_id_tiebreak(self):
        # Dưới nước không hái được
        sc_under = {"player": {"pos": [20, 1.0]},
                    "nodes": [{"id": "N1", "kind": "bong_sung", "pos": [20, 0]}],
                    "fish": [], "random_fish": False}
        sess_u = make_session(sc_under)
        self.assertEqual(run_steps(sess_u, [{"tick": 0, "interact": True}], 1), [])

        # Mặt nước: N10 và N2 cùng cách đúng mép interact_radius (2.0m) -> chọn N2; giữ nút không hái lại
        sc = {"player": {"pos": [20, 0]},
              "nodes": [{"id": "N10", "kind": "bong_sung", "pos": [18, 0]},
                        {"id": "N2", "kind": "bong_dien_dien", "pos": [22, 0]},
                        {"id": "N1", "kind": "bong_sung", "pos": [22.1, 0]}],
              "fish": [], "random_fish": False}
        sess = make_session(sc)
        evs = run_steps(sess, [{"tick": 0, "interact": True}], 2)
        self.assertEqual(len(evs), 1)
        self.assertEqual(evs[0]["name"], "gather")
        self.assertEqual(evs[0]["data"], {"node_id": "N2", "kind": "bong_dien_dien", "amount": 1})
        snap = sess.snapshot()
        self.assertEqual(snap["hold"], ["bong_dien_dien"])
        n2 = next(n for n in snap["nodes"] if n["id"] == "N2")
        self.assertFalse(n2["ready"])
        self.assertEqual(n2["regrow_ticks"], 1199)  # 1200 đặt ở bước 0, giảm 1 ở bước 1

    def test_node_regrow_event_and_immediate_regather_same_tick(self):
        sc = {"player": {"pos": [20, 0]},
              "nodes": [{"id": "N10", "kind": "bong_sung", "pos": [40, 0], "regrow_ticks": 1},
                        {"id": "N2", "kind": "bong_dien_dien", "pos": [20, 0], "regrow_ticks": 1}],
              "fish": [], "random_fish": False}
        sess = make_session(sc)
        evs = run_steps(sess, [{"tick": 0, "interact": True}], 1)
        self.assertEqual([(e["name"], e["data"]) for e in evs], [
            ("node_regrown", {"node_id": "N2"}),
            ("node_regrown", {"node_id": "N10"}),
            ("gather", {"node_id": "N2", "kind": "bong_dien_dien", "amount": 1}),
        ])

    def test_gather_hold_full_keeps_node_ready(self):
        cap = load_contract()["tuning"]["gather"]["hold_capacity"]
        sc = {"player": {"pos": [20, 0]},
              "hold": ["ca_loc"] * cap,
              "nodes": [{"id": "N1", "kind": "bong_sung", "pos": [20, 0]}],
              "fish": [], "random_fish": False}
        sess = make_session(sc)
        evs = run_steps(sess, [{"tick": 0, "interact": True}], 1)
        self.assertEqual([(e["name"], e["data"]) for e in evs], [
            ("hold_full", {"action": "gather", "node_id": "N1", "required": 1, "free": 0}),
        ])
        self.assertTrue(sess.snapshot()["nodes"][0]["ready"])
        self.assertEqual(sess.snapshot()["nodes"][0]["regrow_ticks"], 0)

    def test_catch_requires_underwater_and_no_fish_no_cooldown(self):
        # Ở mặt nước: dù đàn cá nằm trong bán kính catch_radius vẫn không bắt được
        sc_surf = {"player": {"pos": [20, 0.5]},
                   "fish": [{"id": "F1", "kind": "ca_loc", "pos": [20, 1.5]}],
                   "nodes": [], "random_fish": False}
        sess_s = make_session(sc_surf)
        self.assertEqual(run_steps(sess_s, [{"tick": 0, "catch": True}], 1), [])
        self.assertEqual(sess_s.snapshot()["player"]["catch_cd_ticks"], 0)
        self.assertEqual(len(sess_s.snapshot()["fish"]), 1)

        # Dưới nước không có đàn trong tầm: không sự kiện, không hồi chiêu
        sc_far = {"player": {"pos": [20, 5.0]},
                  "fish": [{"id": "F1", "kind": "ca_loc", "pos": [22.1, 5.0]}],
                  "nodes": [], "random_fish": False}
        sess_f = make_session(sc_far)
        self.assertEqual(run_steps(sess_f, [{"tick": 0, "catch": True}], 1), [])
        self.assertEqual(sess_f.snapshot()["player"]["catch_cd_ticks"], 0)

    def test_catch_nearest_numeric_id_tiebreak_lifo_hold_and_exact_cooldown(self):
        # F10 và F2 cùng cách đúng mép catch_radius (2.0m) -> bắt F2 trước; cooldown 30 tick: tick 29 chặn, tick 30 bắt F10
        sc = {"player": {"pos": [20, 5.0]},
              "hold": ["bong_sung"],
              "fish": [{"id": "F10", "kind": "ca_loc", "pos": [18, 5.0]},
                       {"id": "F2", "kind": "ca_linh", "pos": [22, 5.0]}],
              "nodes": [], "random_fish": False}
        sess = make_session(sc)
        evs = run_steps(sess, [
            {"tick": 0, "catch": True},
            {"tick": 1, "catch": False},
            {"tick": 29, "catch": True},   # còn 1 tick cooldown -> bỏ qua
            {"tick": 30, "catch": False},
            {"tick": 31, "catch": True},   # đã hết cooldown từ tick 30 -> bắt F10
        ], 32)
        caught = [(e["tick"], e["data"]) for e in evs if e["name"] == "fish_caught"]
        self.assertEqual(caught, [
            (1, {"fish_id": "F2", "kind": "ca_linh", "yield": 3}),
            (32, {"fish_id": "F10", "kind": "ca_loc", "yield": 1}),
        ])
        self.assertEqual(sess.snapshot()["hold"], ["bong_sung", "ca_linh", "ca_linh", "ca_linh", "ca_loc"])
        self.assertEqual(sess.snapshot()["fish"], [])

        # Kiểm tra đúng tick t+L (bắt ở tick 0, đặt cooldown 30 -> dùng lại ngay ở frame tick 30, event tick 31)
        sess2 = make_session(sc)
        evs2 = run_steps(sess2, [
            {"tick": 0, "catch": True},
            {"tick": 1, "catch": False},
            {"tick": 30, "catch": True},
        ], 31)
        self.assertEqual([(e["tick"], e["data"]["fish_id"]) for e in evs2 if e["name"] == "fish_caught"],
                         [(1, "F2"), (31, "F10")])

    def test_catch_hold_full_does_not_fallback_or_trigger_cooldown(self):
        cap = load_contract()["tuning"]["gather"]["hold_capacity"]
        sc = {"player": {"pos": [20, 5.0]},
              "hold": ["bong_sung"] * (cap - 2),  # còn 2 ô
              "fish": [{"id": "F1", "kind": "ca_linh", "pos": [20.5, 5.0]},  # gần hơn, cần 3 ô -> hold_full
                       {"id": "F2", "kind": "ca_loc", "pos": [21.0, 5.0]}],  # xa hơn, cần 1 ô -> không fallback
              "nodes": [], "random_fish": False}
        sess = make_session(sc)
        evs = run_steps(sess, [{"tick": 0, "catch": True}], 1)
        self.assertEqual([(e["name"], e["data"]) for e in evs], [
            ("hold_full", {"action": "catch", "fish_id": "F1", "required": 3, "free": 2}),
        ])
        self.assertEqual(sess.snapshot()["player"]["catch_cd_ticks"], 0)
        self.assertEqual(len(sess.snapshot()["fish"]), 2)
        self.assertEqual(len(sess.snapshot()["hold"]), cap - 2)

    def test_final_tick_gather_and_catch_included_in_time_end_inventory(self):
        # Hái ở bước cuối -> vào kho trước gather_end(time)
        sc_g = {"player": {"pos": [20, 0]},
                "nodes": [{"id": "N1", "kind": "bong_dien_dien", "pos": [20, 0]}],
                "fish": [], "random_fish": False, "time_left_ticks": 1}
        sess_g = make_session(sc_g)
        evs_g = run_steps(sess_g, [{"tick": 0, "interact": True}], 2)
        self.assertEqual([e["name"] for e in evs_g], ["gather", "gather_end"])
        self.assertEqual(evs_g[1]["data"], {"reason": "time", "inventory": {"items": {"bong_dien_dien": 1}}})

        # Bắt cá ở bước cuối -> vào kho trước gather_end(time)
        sc_f = {"player": {"pos": [20, 5.0]},
                "fish": [{"id": "F1", "kind": "ca_loc", "pos": [20, 5.0]}],
                "nodes": [], "random_fish": False, "time_left_ticks": 1}
        sess_f = make_session(sc_f)
        evs_f = run_steps(sess_f, [{"tick": 0, "catch": True}], 2)
        self.assertEqual([e["name"] for e in evs_f], ["fish_caught", "gather_end"])
        self.assertEqual(evs_f[1]["data"], {"reason": "time", "inventory": {"items": {"ca_loc": 1}}})


class GatherHeadless(unittest.TestCase):
    def test_faint_writes_empty_inventory_file_and_single_final_snapshot(self):
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"gather": {
                "player": {"pos": [20, 5.0], "oxygen_ticks": 0, "zero_oxy_ticks": 59, "hp": 1},
                "hold": ["ca_loc", "bong_dien_dien"],
                "fish": [], "nodes": [], "random_fish": False,
            }})
            out = w.path("out.jsonl")
            inv = w.path("inv.json")
            code, err = run_headless("--mode", "gather", "--seed", "7", "--ticks", "10",
                                     "--scenario", sc, "--out", out, "--inventory-out", inv)
            self.assertEqual(code, 0, err)
            rows = read_jsonl(out)
            self.assertEqual([e["name"] for e in events(rows)], ["choke", "faint", "gather_end"])
            self.assertEqual(events(rows, "faint")[0]["data"]["lost"], ["bong_dien_dien", "ca_loc"])
            snaps = snapshots(rows)
            self.assertEqual([s["tick"] for s in snaps], [0, 1])
            self.assertEqual(snaps[-1]["state"], "finished")
            self.assertEqual(rows[-1]["reason"], "fainted")
            with open(inv, encoding="utf-8") as f:
                self.assertEqual(json.load(f), {"items": {}})

    def test_full_gather_catch_dock_pipeline_to_quan_cli(self):
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"gather": {
                "player": {"pos": [10, 0]},
                "nodes": [{"id": "N1", "kind": "bong_dien_dien", "pos": [10, 0]}],
                "fish": [{"id": "F1", "kind": "ca_linh", "pos": [10, 2.0]}],
                "random_fish": False,
            }})
            inp = write_json(w.path("in.json"), frames(
                {"tick": 0, "interact": True},               # hái N1 (bong_dien_dien)
                {"tick": 1, "interact": False, "move": [0, 1]},  # lặn xuống F1
                {"tick": 35, "move": [0, 0], "catch": True},     # bắt F1 (ca_linh x3)
                {"tick": 36, "catch": False, "move": [0, -1]},   # nổi lên mặt nước
                {"tick": 80, "move": [-1, 0]},                   # bơi về bến [2, 0]
                {"tick": 220, "move": [0, 0], "interact": True}, # cập bến
            ))
            out_g = w.path("gather.jsonl")
            out_q = w.path("quan.jsonl")
            inv = w.path("inv.json")
            code, err = run_headless("--mode", "gather", "--seed", "42", "--ticks", "400",
                                     "--scenario", sc, "--inputs", inp, "--out", out_g, "--inventory-out", inv)
            self.assertEqual(code, 0, err)
            rows = read_jsonl(out_g)
            names = [e["name"] for e in events(rows)]
            self.assertEqual(names, ["gather", "dive", "fish_caught", "surface", "gather_end"])
            self.assertEqual(rows[-1]["reason"], "docked")
            with open(inv, encoding="utf-8") as f:
                saved = json.load(f)
            self.assertEqual(saved, {"items": {"bong_dien_dien": 1, "ca_linh": 3}})
            # Truyền file kho vào chế độ Quán
            code, err = run_headless("--mode", "quan", "--seed", "42", "--ticks", "0",
                                     "--inventory", inv, "--out", out_q)
            self.assertEqual(code, 0, err)
            self.assertEqual(snapshots(read_jsonl(out_q))[0]["stock"], {"bong_dien_dien": 1, "ca_linh": 3})

    def test_headless_determinism_same_seed_byte_identical(self):
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"gather": {
                "player": {"pos": [12, 0]},
                "nodes": [{"id": "N1", "kind": "bong_dien_dien", "pos": [12, 0]}],
                "fish": [{"id": "F1", "kind": "ca_linh", "pos": [12, 2.0]}],
                "random_fish": False,
            }})
            inp = write_json(w.path("in.json"), frames(
                {"tick": 0, "interact": True},
                {"tick": 1, "interact": False, "move": [0, 1]},
                {"tick": 35, "move": [0, 0], "catch": True},
                {"tick": 36, "catch": False, "move": [-1, -1]},
                {"tick": 260, "move": [0, 0], "interact": True},
            ))
            for i in (1, 2):
                code, err = run_headless("--mode", "gather", "--seed", "-17", "--ticks", "400",
                                         "--scenario", sc, "--inputs", inp,
                                         "--out", w.path(f"g{i}.jsonl"),
                                         "--inventory-out", w.path(f"inv{i}.json"))
                self.assertEqual(code, 0, err)
            with open(w.path("g1.jsonl"), "rb") as a, open(w.path("g2.jsonl"), "rb") as b:
                self.assertEqual(a.read(), b.read())
            with open(w.path("inv1.json"), "rb") as a, open(w.path("inv2.json"), "rb") as b:
                self.assertEqual(a.read(), b.read())


if __name__ == "__main__":
    unittest.main()

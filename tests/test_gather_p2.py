"""Tests Phase 2 cho `chonoi/sim/gather.py` (Issue #13 — Test Contract v1.1)."""

from copy import deepcopy
import math
import unittest

from chonoi.contract import load_contract
from chonoi.ids import IdAllocator
from chonoi.inputs import InputPlayer
from chonoi.rng import Streams
from chonoi.runner import Session
from chonoi.sim.gather import GatherSim

from helpers import Workdir, events, read_jsonl, run_headless, snapshots


def make_session(scenario=None, seed=1, tuning=None):
    t = deepcopy(load_contract()["tuning"]) if tuning is None else deepcopy(tuning)
    return Session("gather", t, deepcopy(scenario or {}), seed)


def run_steps(sess, frame_list, n_steps):
    pl = InputPlayer(frame_list)
    out = []
    for k in range(n_steps):
        if sess.done:
            break
        out.extend(sess.step(pl.advance(k)))
    return out


class GatherPhase2FishRules(unittest.TestCase):
    def test_fish_swim_speed_and_turn_at_age_120_before_move(self):
        sc = {"player": {"pos": [2, 0]},
              "fish": [{"id": "F1", "kind": "ca_linh", "pos": [50, 7], "heading_deg": 0, "age_ticks": 0}],
              "monsters": [], "random_fish": True}
        sess = make_session(sc, seed=5)
        run_steps(sess, [], 60)
        f = sess.snapshot()["fish"][0]
        self.assertAlmostEqual(f["pos"][0], 51.5, places=3)
        self.assertAlmostEqual(f["pos"][1], 7.0, places=3)
        self.assertEqual(f["heading_deg"], 0.0)
        self.assertEqual(f["age_ticks"], 60)

        # age_ticks=119 -> bước kế đạt 120: đổi hướng TRƯỚC khi di chuyển
        sc2 = {"player": {"pos": [2, 0]},
               "fish": [{"id": "F1", "kind": "ca_linh", "pos": [50, 7], "heading_deg": 0, "age_ticks": 119}],
               "monsters": [], "random_fish": True}
        sess2 = make_session(sc2, seed=5)
        run_steps(sess2, [], 1)
        f2 = sess2.snapshot()["fish"][0]
        self.assertEqual(f2["age_ticks"], 120)
        self.assertNotEqual(f2["heading_deg"], 0.0)
        rad = math.radians(f2["heading_deg"])
        step_dist = load_contract()["tuning"]["gather"]["fish_speed"] / 60.0
        self.assertAlmostEqual(f2["pos"][0], 50.0 + math.cos(rad) * step_dist, places=5)
        self.assertAlmostEqual(f2["pos"][1], 7.0 + math.sin(rad) * step_dist, places=5)

    def test_fish_reflects_on_edges_and_corner(self):
        # Mép phải x=96 (ca_linh), mép trên d=22 (ca_keo), góc trên trái [4, 3] (ca_linh)
        sc = {"player": {"pos": [2, 0]},
              "fish": [
                  {"id": "F1", "kind": "ca_linh", "pos": [95.99, 7.0], "heading_deg": 0},
                  {"id": "F2", "kind": "ca_keo", "pos": [50.0, 22.01], "heading_deg": 270},
                  {"id": "F3", "kind": "ca_linh", "pos": [4.005, 3.005], "heading_deg": 225},
              ],
              "monsters": [], "random_fish": True}
        sess = make_session(sc, seed=1)
        run_steps(sess, [], 1)
        by_id = {f["id"]: f for f in sess.snapshot()["fish"]}
        # F1: 95.99 + 0.025 = 96.015 -> phản xạ về 95.985, heading 180
        self.assertAlmostEqual(by_id["F1"]["pos"][0], 95.985, places=4)
        self.assertAlmostEqual(by_id["F1"]["heading_deg"], 180.0, places=3)
        # F2: 22.01 - 0.025 = 21.985 -> phản xạ về 22.015, heading 90
        self.assertAlmostEqual(by_id["F2"]["pos"][1], 22.015, places=4)
        self.assertAlmostEqual(by_id["F2"]["heading_deg"], 90.0, places=3)
        # F3: chạm góc [4, 3], đảo cả 2 thành phần -> heading 45 và nằm trong [4, 96] x [3, 12]
        self.assertGreater(by_id["F3"]["pos"][0], 4.0)
        self.assertGreater(by_id["F3"]["pos"][1], 3.0)
        self.assertAlmostEqual(by_id["F3"]["heading_deg"], 45.0, places=3)

    def test_random_fish_false_freezes_fish_and_disables_spawn(self):
        sc = {"player": {"pos": [2, 0]},
              "fish": [{"id": "F1", "kind": "ca_loc", "pos": [50, 12], "heading_deg": 0}],
              "monsters": [], "random_fish": False}
        sess = make_session(sc, seed=1)
        evs = run_steps(sess, [], 400)
        self.assertEqual([e for e in evs if e["name"] == "fish_spawned"], [])
        self.assertEqual(len(sess.snapshot()["fish"]), 1)
        self.assertEqual(sess.snapshot()["fish"][0]["pos"], [50.0, 12.0])
        self.assertEqual(sess.snapshot()["fish"][0]["age_ticks"], 0)

    def test_scheduled_fish_spawn_at_360_after_swim_and_respects_cap_12(self):
        sess = make_session({"monsters": []}, seed=9)
        self.assertEqual(len(sess.snapshot()["fish"]), 8)
        evs = run_steps(sess, [], 1800)
        spawned = [e for e in evs if e["name"] == "fish_spawned"]
        self.assertEqual([e["tick"] for e in spawned], [360, 720, 1080, 1440])
        self.assertEqual(len(sess.snapshot()["fish"]), 12)
        for e in spawned:
            self.assertEqual(set(e["data"]), {"id", "kind", "pos"})

        # Cá mới sinh ở tick 360 chỉ bắt đầu bơi từ bước sau (age_ticks == 0 ở cuối tick 360)
        sess2 = make_session({"monsters": []}, seed=9)
        evs2 = run_steps(sess2, [], 360)
        new_id = [e for e in evs2 if e["name"] == "fish_spawned"][0]["data"]["id"]
        new_fish = next(f for f in sess2.snapshot()["fish"] if f["id"] == new_id)
        self.assertEqual(new_fish["age_ticks"], 0)

    def test_spawn_renormalizes_valid_species_and_skips_when_all_blocked(self):
        tuning = deepcopy(load_contract()["tuning"])
        g = tuning["gather"]
        g["fish_spawn_x"] = [15]
        g["fish_spawn_depths"] = {"ca_linh": [5], "ca_loc": [16], "ca_keo": [24]}
        g["fish_speed"] = 0.0  # giữ cố định để điểm bị chắn chính xác
        g["fish_spawn_ticks"] = 10
        g["fish_max"] = 10
        sc = {"fish": [
            {"id": "F1", "kind": "ca_linh", "pos": [15, 5]},
            {"id": "F2", "kind": "ca_loc", "pos": [15, 16]},
        ], "monsters": [], "random_fish": True}
        sess = make_session(sc, seed=3, tuning=tuning)
        evs = run_steps(sess, [], 25)
        spawned = [e for e in evs if e["name"] == "fish_spawned"]
        self.assertEqual(len(spawned), 1)
        self.assertEqual(spawned[0]["tick"], 10)
        self.assertEqual(spawned[0]["data"]["kind"], "ca_keo")
        self.assertEqual(spawned[0]["data"]["pos"], [15.0, 24.0])

    def test_catch_uses_pre_swim_fish_position_and_ca_keo_yield(self):
        # F1 đang ở đúng mép catch_radius=2.0 và chuẩn bị bơi ra xa -> vẫn bắt được trước khi cá bơi
        sc = {"player": {"pos": [20, 25]},
              "fish": [{"id": "F1", "kind": "ca_keo", "pos": [22.0, 25.0], "heading_deg": 0}],
              "monsters": [], "random_fish": True}
        sess = make_session(sc, seed=1)
        evs = run_steps(sess, [{"tick": 0, "catch": True}], 1)
        caught = [e for e in evs if e["name"] == "fish_caught"]
        self.assertEqual(len(caught), 1)
        self.assertEqual(caught[0]["data"], {"fish_id": "F1", "kind": "ca_keo", "yield": 2})
        self.assertEqual(sess.snapshot()["hold"], ["ca_keo", "ca_keo"])

    def test_new_nodes_keo_neo_and_day_ctx_upgrades(self):
        tuning = deepcopy(load_contract()["tuning"])
        ctx = {"day": 2, "day_plan": tuning["day_plan"][1], "active_upgrades": {"oxygen": 2, "hp": 1}}
        sim = GatherSim(tuning, {"player": {"pos": [76, 0]}, "fish": [], "monsters": []}, Streams(1), IdAllocator(),
                        day_ctx=ctx)
        snap = sim.snapshot()
        self.assertEqual(snap["player"]["oxygen_max_ticks"], 60 * 60)
        self.assertEqual(snap["player"]["oxygen_ticks"], 60 * 60)
        self.assertEqual(snap["player"]["hp_max"], 4)
        self.assertEqual(snap["player"]["hp"], 4)
        # Hái nút N5 (keo_neo) tại [76, 0]
        pl = InputPlayer([{"tick": 0, "interact": True}])
        evs = sim.step(pl.advance(0))
        self.assertEqual(evs, [("gather", {"node_id": "N5", "kind": "keo_neo", "amount": 1})])

    def test_headless_p2_gather_swimming_and_spawning_byte_identical(self):
        with Workdir() as w:
            for i in (1, 2):
                code, err = run_headless("--mode", "gather", "--seed", "11", "--ticks", "800",
                                         "--out", w.path(f"g{i}.jsonl"))
                self.assertEqual(code, 0, err)
            with open(w.path("g1.jsonl"), "rb") as a, open(w.path("g2.jsonl"), "rb") as b:
                self.assertEqual(a.read(), b.read())
            rows = read_jsonl(w.path("g1.jsonl"))
            self.assertEqual([e["tick"] for e in events(rows, "fish_spawned")], [360, 720])
            self.assertEqual(len(snapshots(rows)[-1]["fish"]), 10)


if __name__ == "__main__":
    unittest.main()

"""Tests Phase 2 cho thủy quái Cá Sấu Năm Chèo (`chonoi/sim/monsters.py`, Issue #14)."""

from copy import deepcopy
import unittest

from chonoi.contract import load_contract
from chonoi.ids import IdAllocator
from chonoi.inputs import InputPlayer
from chonoi.rng import Streams
from chonoi.runner import Session
from chonoi.sim.day import DaySim
from chonoi.sim.gather import GatherSim


def make_gather(scenario=None, seed=1, day_ctx=None, tuning=None):
    t = deepcopy(load_contract()["tuning"]) if tuning is None else deepcopy(tuning)
    t.pop("freshness", None)  # luật P1/P2 với giỏ dạng kind; giỏ cá thể v1.2 kiểm ở test_gather_p3
    return GatherSim(t, deepcopy(scenario or {}), Streams(seed), IdAllocator(), day_ctx=day_ctx)


def step_sim(sim, frame_list, n_steps):
    pl = InputPlayer(frame_list)
    out = []
    for k in range(n_steps):
        if sim.done:
            break
        for name, data in sim.step(pl.advance(k)):
            out.append({"tick": k + 1, "name": name, "data": data})
    return out


class MonsterSpawnAndPatrol(unittest.TestCase):
    def test_default_spawns_day1_vs_day3(self):
        t = load_contract()["tuning"]
        # gather độc lập = Ngày 1 -> chỉ có M1
        s1 = make_gather(tuning=t)
        self.assertEqual([m["id"] for m in s1.snapshot()["monsters"]], ["M1"])
        self.assertEqual(s1.snapshot()["monsters"][0]["pos"], [60.0, 24.0])
        self.assertEqual(s1.snapshot()["monsters"][0]["target_idx"], 1)

        # Ngày 3 -> có cả M1 và M2
        ctx3 = {"day": 3, "day_plan": t["day_plan"][2], "active_upgrades": {"oxygen": 0, "hp": 0}}
        s3 = make_gather(day_ctx=ctx3, tuning=t)
        self.assertEqual([m["id"] for m in s3.snapshot()["monsters"]], ["M1", "M2"])

    def test_patrol_speed_and_waypoint_switch_for_next_step(self):
        # M1 từ [60, 24] đi tới [64, 24] với patrol_speed=1.0 m/s -> đúng 240 tick chạm [64, 24] và đổi target_idx=0
        sc = {"player": {"pos": [2, 0]}, "fish": [], "random_fish": False,
              "monsters": [{"id": "M1", "kind": "ca_sau", "pos": [60, 24], "waypoints": [[60, 24], [64, 24]]}]}
        sim = make_gather(sc)
        step_sim(sim, [], 240)
        m = sim.snapshot()["monsters"][0]
        self.assertAlmostEqual(m["pos"][0], 64.0, places=3)
        self.assertEqual(m["target_idx"], 0)
        # Bước 241 quay lại về [60, 24]
        step_sim(sim, [], 1)
        m2 = sim.snapshot()["monsters"][0]
        self.assertAlmostEqual(m2["pos"][0], 64.0 - 1.0 / 60.0, places=4)


class MonsterChaseHitRecoil(unittest.TestCase):
    def test_patrol_chase_patrol_transitions_and_depth_clamp(self):
        # Người chơi ở [50, 24] (cách 10.0m, d>=10) -> M1 chuyển chase và bơi 3.0 m/s về phía người chơi
        sc = {"player": {"pos": [50, 24]}, "fish": [], "random_fish": False,
              "monsters": [{"id": "M1", "kind": "ca_sau", "pos": [60, 24], "waypoints": [[60, 24], [64, 24]]}]}
        sim = make_gather(sc)
        step_sim(sim, [], 1)
        m = sim.snapshot()["monsters"][0]
        self.assertEqual(m["state"], "chase")
        self.assertAlmostEqual(m["pos"][0], 60.0 - 3.0 / 60.0, places=4)

        # Khi người chơi lên d < 10 -> M1 về patrol
        sc_shallow = {"player": {"pos": [60, 9.5]}, "fish": [], "random_fish": False,
                      "monsters": [{"id": "M1", "kind": "ca_sau", "pos": [60, 10.5],
                                    "waypoints": [[60, 12], [64, 12]], "state": "chase"}]}
        sim_s = make_gather(sc_shallow)
        step_sim(sim_s, [], 1)
        self.assertEqual(sim_s.snapshot()["monsters"][0]["state"], "patrol")
        self.assertGreaterEqual(sim_s.snapshot()["monsters"][0]["pos"][1], 10.0)

        # Khi khoảng cách > exit_radius (16m) -> M1 về patrol
        sc_far = {"player": {"pos": [40, 24]}, "fish": [], "random_fish": False,
                  "monsters": [{"id": "M1", "kind": "ca_sau", "pos": [60, 24],
                                "waypoints": [[60, 24], [64, 24]], "state": "chase"}]}
        sim_f = make_gather(sc_far)
        step_sim(sim_f, [], 1)
        self.assertEqual(sim_f.snapshot()["monsters"][0]["state"], "patrol")

    def test_hit_lifo_loss_invuln_and_recoil_60_ticks(self):
        # Hold có 5 món -> floor(5*0.5)=2 món cuối (LIFO); bất tử 90 tick; recoil 60 bước, mỗi bước 2/60 m
        sc = {"player": {"pos": [60, 24], "hp": 3},
              "hold": ["bong_sung", "ca_loc", "ca_linh", "keo_neo", "ca_keo"],
              "fish": [], "random_fish": False,
              "monsters": [{"id": "M1", "kind": "ca_sau", "pos": [61.0, 24.0], "waypoints": [[60, 24], [64, 24]]}]}
        sim = make_gather(sc)
        evs = step_sim(sim, [], 1)
        self.assertEqual(len(evs), 1)
        self.assertEqual(evs[0]["name"], "monster_hit")
        self.assertEqual(evs[0]["data"], {
            "monster_id": "M1", "hp": 2, "lost": ["ca_keo", "keo_neo"], "pos": [60.0, 24.0],
        })
        snap1 = sim.snapshot()
        self.assertEqual(snap1["hold"], ["bong_sung", "ca_loc", "ca_linh"])
        self.assertEqual(snap1["player"]["invuln_ticks"], 90)
        m1 = snap1["monsters"][0]
        self.assertEqual(m1["state"], "recoil")
        self.assertEqual(m1["state_ticks_left"], 60)
        self.assertEqual(m1["recoil_dir"], [1.0, 0.0])
        x_at_hit = m1["pos"][0]

        # Chạy 60 bước recoil: lùi đúng 2.0 m về +x, không gây hit thêm; hết bước 60 về patrol
        evs_rec = step_sim(sim, [], 60)
        self.assertEqual([e for e in evs_rec if e["name"] == "monster_hit"], [])
        m_after = sim.snapshot()["monsters"][0]
        self.assertAlmostEqual(m_after["pos"][0], x_at_hit + 2.0, places=3)
        self.assertEqual(m_after["state"], "patrol")
        self.assertEqual(m_after["state_ticks_left"], 0)
        self.assertIsNone(m_after["recoil_dir"])

    def test_coincident_hit_recoils_plus_x_and_clamps_bounds(self):
        # Trùng tâm tại mép phải x=100 -> recoil +x bị chặn tại x=100
        sc = {"player": {"pos": [100, 24], "hp": 3},
              "fish": [], "random_fish": False,
              "monsters": [{"id": "M1", "kind": "ca_sau", "pos": [100, 24], "waypoints": [[96, 24], [100, 24]]}]}
        sim = make_gather(sc)
        step_sim(sim, [], 1)
        m = sim.snapshot()["monsters"][0]
        self.assertEqual(m["state"], "recoil")
        self.assertEqual(m["recoil_dir"], [1.0, 0.0])
        step_sim(sim, [], 10)
        self.assertEqual(sim.snapshot()["monsters"][0]["pos"][0], 100.0)

    def test_two_monsters_only_one_hit_by_distance_then_id_and_invuln_blocks_recoil(self):
        # M10 và M2 cùng khoảng cách tới người chơi -> chỉ M2 hit và vào recoil; M10 không recoil
        sc = {"player": {"pos": [60, 24], "hp": 3},
              "fish": [], "random_fish": False,
              "monsters": [
                  {"id": "M10", "kind": "ca_sau", "pos": [59.0, 24.0], "waypoints": [[58, 24], [62, 24]]},
                  {"id": "M2", "kind": "ca_sau", "pos": [61.0, 24.0], "waypoints": [[58, 24], [62, 24]]},
              ]}
        sim = make_gather(sc)
        evs = step_sim(sim, [], 1)
        hits = [e for e in evs if e["name"] == "monster_hit"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["data"]["monster_id"], "M2")
        by_id = {m["id"]: m for m in sim.snapshot()["monsters"]}
        self.assertEqual(by_id["M2"]["state"], "recoil")
        self.assertEqual(by_id["M10"]["state"], "chase")

        # Bước kế người chơi đang bất tử -> M10 ở trong tầm vẫn KHÔNG hit và KHÔNG vào recoil
        evs2 = step_sim(sim, [], 1)
        self.assertEqual([e for e in evs2 if e["name"] == "monster_hit"], [])
        by_id2 = {m["id"]: m for m in sim.snapshot()["monsters"]}
        self.assertEqual(by_id2["M10"]["state"], "chase")
        self.assertEqual(by_id2["M2"]["state"], "recoil")

    def test_monster_faint_drops_remaining_lifo_and_day_continues_with_empty_stock(self):
        # hp=1, hold có 3 món -> monster_hit bỏ floor(3/2)=1 (món cuối), faint(cause="monster") bỏ 2 món còn lại LIFO
        t = deepcopy(load_contract()["tuning"])
        t.pop("freshness", None)  # luật P2 dạng kind; cá thể v1.2 kiểm ở test_gather_p3
        sc = {"gather": {
            "player": {"pos": [60, 24], "hp": 1},
            "hold": ["bong_sung", "ca_loc", "ca_linh"],
            "fish": [], "random_fish": False,
            "monsters": [{"id": "M1", "kind": "ca_sau", "pos": [60.5, 24.0], "waypoints": [[60, 24], [64, 24]]}],
        }}
        day = DaySim(t, sc, Streams(1), IdAllocator(), days=1)
        pl = InputPlayer([])
        evs = day.step(pl.advance(0))
        names = [e[0] for e in evs]
        self.assertEqual(names, ["monster_hit", "faint", "gather_end", "phase_start"])
        self.assertEqual(evs[0][1]["lost"], ["ca_linh"])
        self.assertEqual(evs[1][1], {"cause": "monster", "lost": ["ca_loc", "bong_sung"], "hp": 0})
        self.assertEqual(evs[2][1], {"reason": "fainted", "inventory": {"items": {}}})
        self.assertEqual(day.phase, "quan")
        self.assertEqual(day.snapshot()["stock"], {})

    def test_choke_then_monster_hit_same_tick_order(self):
        # hp=2, oxy=0, zero_oxy_ticks=59, ngay cạnh M1 -> bước 1 ngạt (hp=1) rồi bị hit (hp=0) -> faint cause="monster"
        sc = {"player": {"pos": [60, 24], "hp": 2, "oxygen_ticks": 0, "zero_oxy_ticks": 59},
              "hold": ["ca_loc", "bong_sung"],
              "fish": [], "random_fish": False,
              "monsters": [{"id": "M1", "kind": "ca_sau", "pos": [60.5, 24.0], "waypoints": [[60, 24], [64, 24]]}]}
        sim = make_gather(sc)
        evs = step_sim(sim, [], 1)
        self.assertEqual([e["name"] for e in evs], ["choke", "monster_hit", "faint", "gather_end"])
        self.assertEqual(evs[0]["data"], {"hp": 1})
        self.assertEqual(evs[1]["data"]["hp"], 0)
        self.assertEqual(evs[2]["data"]["cause"], "monster")
        self.assertTrue(sim.done)


if __name__ == "__main__":
    unittest.main()

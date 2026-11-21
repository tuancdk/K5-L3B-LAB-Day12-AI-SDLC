"""Tests mở rộng Dòng nước lũ (`current`, Issue #23) trong `chonoi/sim/gather.py`."""

from copy import deepcopy
import unittest

from chonoi.contract import load_contract
from chonoi.inputs import InputPlayer
from chonoi.runner import Session


def tuning_with_current(**overrides):
    t = deepcopy(load_contract()["tuning"])
    cfg = {
        "interval_ticks": 1800,
        "duration_ticks": 480,
        "warning_ticks": 120,
        "min_depth": 10.0,
        "speed": 1.5,
    }
    cfg.update(overrides)
    t["gather"]["current"] = cfg
    return t


def run_steps(sess, frame_list, n_steps):
    pl = InputPlayer(frame_list)
    out = []
    for k in range(n_steps):
        if sess.done:
            break
        out.extend(sess.step(pl.advance(k)))
    return out


class FloodCurrentExtension(unittest.TestCase):
    def test_exact_schedule_warning_start_480_ticks_and_elapsed_end(self):
        t = tuning_with_current()
        sc = {"player": {"pos": [50, 0]}, "fish": [], "random_fish": False, "monsters": [],
              "current_direction": 1}
        sess = Session("gather", t, sc, 1)
        self.assertIsNone(sess.snapshot()["current"])

        evs_pre = run_steps(sess, [], 1799)
        warns = [e for e in evs_pre if e["name"] == "current_warning"]
        self.assertEqual([(e["tick"], e["data"]) for e in warns], [(1680, {"starts_at_phase_tick": 1800})])
        self.assertIsNone(sess.snapshot()["current"])

        # Tick 1800: bắt đầu dòng, snapshot ticks_left = 480 (đếm cả tick vừa chụp)
        evs_start = run_steps(sess, [], 1)
        self.assertEqual([(e["tick"], e["name"], e["data"]) for e in evs_start], [
            (1800, "current_start", {"direction": 1, "duration_ticks": 480}),
        ])
        self.assertEqual(sess.snapshot()["current"], {"direction": 1, "ticks_left": 480})

        # Chạy đến tick 2279 (1800 + 479): vẫn đang chạy với ticks_left = 1
        evs_mid = run_steps(sess, [], 479)
        self.assertEqual([e for e in evs_mid if e["name"] == "current_end"], [])
        self.assertEqual(sess.snapshot()["current"], {"direction": 1, "ticks_left": 1})

        # Tick 2280 (1800 + 480): kết thúc trước di chuyển -> current_end(elapsed), snapshot null
        evs_end = run_steps(sess, [], 1)
        self.assertEqual([(e["tick"], e["name"], e["data"]) for e in evs_end], [
            (2280, "current_end", {"direction": 1, "reason": "elapsed"}),
        ])
        self.assertIsNone(sess.snapshot()["current"])

    def test_force_applies_only_at_depth_ge_10_does_not_accumulate_vel_or_move_fish(self):
        t = tuning_with_current(interval_ticks=10, duration_ticks=60, warning_ticks=5)
        # d=10.0 >= 10 -> bị đẩy -1.5 m/s trong 60 tick = -1.5m; player.vel vẫn là [0, 0]; cá và quái không bị ảnh hưởng
        sc_deep = {"player": {"pos": [50, 10.0], "oxygen_ticks": 1800},
                   "fish": [{"id": "F1", "kind": "ca_loc", "pos": [40, 12.0]}],
                   "monsters": [{"id": "M1", "kind": "ca_sau", "pos": [80, 20.0], "waypoints": [[80, 20], [80, 20]]}],
                   "random_fish": False, "current_direction": -1}
        sess = Session("gather", t, sc_deep, 1)
        run_steps(sess, [], 9)
        self.assertEqual(sess.snapshot()["player"]["pos"][0], 50.0)
        run_steps(sess, [], 60)  # ticks 10..69 (đúng 60 tick dòng lũ)
        snap = sess.snapshot()
        self.assertAlmostEqual(snap["player"]["pos"][0], 48.5, places=3)
        self.assertEqual(snap["player"]["vel"], [0.0, 0.0])
        self.assertEqual(snap["fish"][0]["pos"], [40.0, 12.0])
        self.assertEqual(snap["monsters"][0]["pos"], [80.0, 20.0])

        # d=9.5 < 10 -> không bị đẩy
        sc_shallow = {"player": {"pos": [50, 9.5]}, "fish": [], "random_fish": False,
                      "monsters": [], "current_direction": 1}
        sess2 = Session("gather", t, sc_shallow, 1)
        run_steps(sess2, [], 30)
        self.assertEqual(sess2.snapshot()["player"]["pos"][0], 50.0)

    def test_random_current_false_disables_schedule_and_seeded_direction_varies(self):
        t = tuning_with_current(interval_ticks=5, duration_ticks=10, warning_ticks=2)
        sc_off = {"player": {"pos": [50, 12]}, "fish": [], "random_fish": False,
                  "monsters": [], "random_current": False}
        sess_off = Session("gather", t, sc_off, 1)
        evs = run_steps(sess_off, [], 20)
        self.assertEqual([e for e in evs if e["name"].startswith("current_")], [])

        dirs = set()
        for seed in range(1, 20):
            s = Session("gather", t, {"fish": [], "random_fish": False, "monsters": []}, seed)
            e = run_steps(s, [], 5)
            dirs.add([x["data"]["direction"] for x in e if x["name"] == "current_start"][0])
        self.assertEqual(dirs, {-1, 1})

    def test_phase_end_emits_current_end_before_faint_and_gather_end(self):
        t = tuning_with_current(interval_ticks=1, duration_ticks=10, warning_ticks=0)
        # Ngất ngay tick 1 khi dòng vừa bắt đầu -> lực vẫn áp dụng, rồi current_end(phase_end) trước faint & gather_end
        sc_faint = {"player": {"pos": [50, 12.0], "oxygen_ticks": 0, "zero_oxy_ticks": 59, "hp": 1},
                    "hold": ["ca_loc"], "fish": [], "random_fish": False,
                    "monsters": [], "current_direction": 1}
        sess_f = Session("gather", t, sc_faint, 1)
        evs_f = run_steps(sess_f, [], 2)
        self.assertEqual([e["name"] for e in evs_f], ["current_start", "choke", "current_end", "faint", "gather_end"])
        self.assertEqual(evs_f[2]["data"], {"direction": 1, "reason": "phase_end"})
        self.assertAlmostEqual(sess_f.snapshot()["player"]["pos"][0], 50.0 + 1.5 / 60.0, places=4)

        # Bước bắt đầu dòng trùng bước cuối ca -> lực vẫn áp dụng, rồi current_end(phase_end) trước gather_end(time)
        sc_time = {"player": {"pos": [50, 12.0]}, "time_left_ticks": 1,
                   "fish": [], "random_fish": False, "monsters": [], "current_direction": -1}
        sess_t = Session("gather", t, sc_time, 1)
        evs_t = run_steps(sess_t, [], 2)
        self.assertEqual([e["name"] for e in evs_t], ["current_start", "current_end", "gather_end"])
        self.assertEqual(evs_t[1]["data"], {"direction": -1, "reason": "phase_end"})
        self.assertAlmostEqual(sess_t.snapshot()["player"]["pos"][0], 50.0 - 1.5 / 60.0, places=4)


if __name__ == "__main__":
    unittest.main()

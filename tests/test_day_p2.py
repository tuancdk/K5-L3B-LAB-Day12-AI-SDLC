"""Mode `day`, pause, CLI --days (Test Contract v1.1 mục 4.1–4.5; issue #12). Hộp đen qua headless_cmd."""

import json
import os
import time
import unittest

from helpers import Workdir, assert_items_close, decayed, events, frames, items, read_jsonl, run_headless, snapshots, write_json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def tuning():
    with open(os.path.join(ROOT, "game.contract.json"), encoding="utf-8") as f:
        return json.load(f)["tuning"]


# Cập bến ngay tick 0 với giỏ dựng sẵn, quán 5 tick, Shop đóng bằng nút ở tick 10.
FAST = {"gather": {"hold": items("ca_loc", "bong_sung", "bong_sung")}, "quan": {"time_left_ticks": 5}}


def fast_frames(shop_done_tick=10, extra=()):
    return frames({"tick": 0, "interact": True}, {"tick": 1, "interact": False}, *extra,
                  {"tick": shop_done_tick, "shop_done": True}, {"tick": shop_done_tick + 1, "shop_done": False})


class DayCli(unittest.TestCase):
    def test_days_flag_only_with_day_and_in_range(self):
        with Workdir() as w:
            out = w.path("o.jsonl")
            self.assertEqual(run_headless("--mode", "gather", "--days", "1", "--seed", "1", "--ticks", "0", "--out", out)[0], 2)
            for bad in ("0", "6", "x"):
                self.assertEqual(run_headless("--mode", "day", "--days", bad, "--seed", "1", "--ticks", "0", "--out", out)[0], 2, bad)
            self.assertFalse(os.path.exists(out))
            self.assertEqual(run_headless("--mode", "day", "--seed", "1", "--ticks", "0", "--out", out)[0], 0)

    def test_day_scenario_rejects_quan_stock_reputation_and_money_over_earned(self):
        with Workdir() as w:
            out = w.path("o.jsonl")
            for sc in ({"quan": {"stock": {"ca_loc": 1}}}, {"quan": {"reputation": 4}},
                       {"day": {"money": 10, "earned": 5}}, {"day": {"upgrades": {"oxygen": 3}}},
                       {"day": {"day_plan": [{"day": 1, "dishes": {"goi_bong_sung": 1}, "ingredients": {"bong_sung": 3}}]}}):
                p = write_json(w.path("sc.json"), sc)
                self.assertEqual(run_headless("--mode", "day", "--seed", "1", "--ticks", "0", "--scenario", p,
                                              "--out", out)[0], 2, sc)
            self.assertFalse(os.path.exists(out))


class DayLoop(unittest.TestCase):
    def run_day(self, w, scenario, inp, ticks, days=1, every=1, name="d"):
        sc = write_json(w.path(f"{name}-sc.json"), scenario)
        ip = write_json(w.path(f"{name}-in.json"), inp)
        code, err = run_headless("--mode", "day", "--days", str(days), "--seed", "5", "--ticks", str(ticks),
                                 "--scenario", sc, "--inputs", ip, "--snapshot-every", str(every),
                                 "--out", w.path(f"{name}.jsonl"))
        self.assertEqual(code, 0, err)
        return read_jsonl(w.path(f"{name}.jsonl"))

    def test_tick0_order_and_phase_switches_same_tick(self):
        with Workdir() as w:
            rows = self.run_day(w, FAST, fast_frames(), 100)
        ev = [(r["tick"], r["phase"], r["day"], r["name"]) for r in rows if r["type"] == "event"]
        self.assertEqual(ev[:3], [(0, "gather", 1, "day_start"), (0, "gather", 1, "day_plan"), (0, "gather", 1, "phase_start")])
        self.assertEqual(rows[3]["type"], "snapshot")
        self.assertIn((1, "gather", 1, "gather_end"), ev)
        self.assertIn((1, "quan", 1, "phase_start"), ev)
        self.assertIn((6, "quan", 1, "quan_end"), ev)
        self.assertIn((6, "shop", 1, "phase_start"), ev)
        self.assertIn((11, "shop", 1, "shop_end"), ev)
        snaps = {s["tick"]: s for s in snapshots(rows)}
        self.assertEqual((snaps[1]["phase"], snaps[1]["phase_tick"]), ("quan", 0))
        assert_items_close(self, snaps[1]["stock"], items("ca_loc", "bong_sung", "bong_sung", fresh=decayed(1)))  # v1.2
        self.assertEqual((snaps[6]["phase"], snaps[6]["phase_tick"]), ("shop", 0))
        for s in snapshots(rows):
            for key in ("day", "day_plan", "upgrades", "active_upgrades"):
                self.assertIn(key, s)
        self.assertEqual(snaps[0]["day_plan"], tuning()["day_plan"][0])
        end = rows[-1]
        self.assertEqual((end["type"], end["reason"], end["days_completed"], end["ticks"]), ("end", "days_complete", 1, 11))

    def test_upgrade_bought_applies_from_next_day(self):
        t = tuning()
        up = t["shop"]["upgrades"]["oxygen"][0]
        sc = dict(FAST, day={"money": up["price"], "earned": up["price"]})
        inp = frames({"tick": 0, "interact": True}, {"tick": 1, "interact": False}, {"tick": 8, "buy": "oxygen"},
                     {"tick": 9, "buy": "oxygen"}, {"tick": 10, "shop_done": True}, {"tick": 11, "shop_done": False})
        with Workdir() as w:
            rows = self.run_day(w, sc, inp, 40, days=2)
        bought = events(rows, "bought")
        self.assertEqual(len(bought), 1)
        self.assertEqual(bought[0]["data"], {"upgrade": "oxygen", "level": 1, "price": up["price"], "money": 0})
        self.assertEqual(events(rows, "buy_failed")[0]["data"], {"action": "oxygen", "reason": "funds"})
        snaps = {s["tick"]: s for s in snapshots(rows)}
        self.assertEqual((snaps[9]["upgrades"]["oxygen"], snaps[9]["active_upgrades"]["oxygen"]), (1, 0))
        day2 = [s for s in snapshots(rows) if s["day"] == 2]
        self.assertTrue(day2)
        self.assertEqual(day2[0]["active_upgrades"]["oxygen"], 1)
        self.assertEqual(day2[0]["player"]["oxygen_max_ticks"], up["oxygen_max_s"] * 60)
        self.assertEqual(day2[0]["day_plan"], t["day_plan"][1])
        self.assertEqual([r["name"] for r in rows if r["type"] == "event" and r["tick"] == 11][-3:],
                         ["day_start", "day_plan", "phase_start"])

    def test_one_full_day_without_pause_finishes_and_is_fast(self):
        with Workdir() as w:
            t0 = time.monotonic()
            code, err = run_headless("--mode", "day", "--days", "1", "--seed", "9", "--ticks", "30000",
                                     "--snapshot-every", "600", "--out", w.path("full.jsonl"))
            elapsed = time.monotonic() - t0
            self.assertEqual(code, 0, err)
            end = read_jsonl(w.path("full.jsonl"))[-1]
        self.assertEqual((end["reason"], end["ticks"], end["days_completed"]), ("days_complete", 22200, 1))
        self.assertLess(elapsed, 20)

    def test_day_deterministic_bytes(self):
        with Workdir() as w:
            a = self.run_day(w, FAST, fast_frames(), 3000, days=3, every=7, name="a")
            b = self.run_day(w, FAST, fast_frames(), 3000, days=3, every=7, name="b")
            with open(w.path("a.jsonl"), "rb") as fa, open(w.path("b.jsonl"), "rb") as fb:
                self.assertEqual(fa.read(), fb.read())
        self.assertEqual(a[-1], b[-1])


class Pause(unittest.TestCase):
    def test_pause_freezes_gameplay_and_resume_runs_same_step(self):
        inp = frames({"tick": 0, "move": [1, 0]}, {"tick": 5, "pause": True}, {"tick": 6, "pause": False, "interact": True},
                     {"tick": 7, "interact": False}, {"tick": 10, "pause": True}, {"tick": 11, "pause": False})
        with Workdir() as w:
            p = write_json(w.path("in.json"), inp)
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "14", "--inputs", p,
                                     "--snapshot-every", "1", "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
        ev = [(r["tick"], r["name"]) for r in rows if r["type"] == "event"]
        self.assertIn((6, "paused"), ev)
        self.assertIn((11, "resumed"), ev)
        s = {r["tick"]: r for r in snapshots(rows)}
        self.assertEqual(s[5]["state"], "playing")
        for k in (6, 8, 10):
            self.assertEqual((s[k]["state"], s[k]["sim_tick"]), ("paused", 5), k)
            self.assertEqual(s[k]["player"]["pos"], s[5]["player"]["pos"])
            self.assertEqual(s[k]["time_left_ticks"], s[5]["time_left_ticks"])
        self.assertEqual((s[11]["state"], s[11]["sim_tick"]), ("playing", 6))
        self.assertEqual(s[11]["time_left_ticks"], s[5]["time_left_ticks"] - 1)
        self.assertGreater(s[11]["player"]["pos"][0], s[5]["player"]["pos"][0])
        end = rows[-1]
        self.assertEqual((end["ticks"], end["sim_tick"]), (14, 9))


if __name__ == "__main__":
    unittest.main()

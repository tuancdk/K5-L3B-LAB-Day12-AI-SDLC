"""Issue #8: Shop lõi và tích hợp day/pause bằng Test Contract v1.1."""

import copy
import unittest
from pathlib import Path

from chonoi.contract import load_contract
from chonoi.ids import IdAllocator
from chonoi.inputs import InputPlayer
from chonoi.rng import Streams
from chonoi.runner import Session
from chonoi.sim.day import DaySim
from chonoi.sim.shop import ShopSim

from helpers import Workdir, events, frames, item_counts, items, read_jsonl, run_headless, snapshots, write_json


class ShopRules(unittest.TestCase):
    def setUp(self):
        self.tuning = load_contract()["tuning"]

    def make_shop(self, money=0, upgrades=None, day_ctx=None):
        ctx = day_ctx if day_ctx is not None else {
            "day": 1, "day_plan": copy.deepcopy(self.tuning["day_plan"][0]),
            "active_upgrades": {"oxygen": 0, "hp": 0}}
        shop = ShopSim(self.tuning, Streams(1), IdAllocator(), money, upgrades or {}, ctx)
        # Giống day.py: gán trạng thái xuyên Ngày ngay sau constructor.
        shop.earned = money
        shop.reputation = 3.2
        return shop

    def steps(self, shop, count=1, inputs=()):
        player = InputPlayer(list(inputs))
        result = []
        for _ in range(count):
            if shop.done:
                break
            result.extend(shop.step(player.advance(shop.phase_tick)))
        return result

    def test_exact_price_each_upgrade_preserves_earned_and_reputation(self):
        for action in ("oxygen", "hp"):
            with self.subTest(action=action):
                price = self.tuning["shop"]["upgrades"][action][0]["price"]
                shop = self.make_shop(price)
                rows = self.steps(shop, inputs=[{"tick": 0, "buy": action}])
                self.assertEqual(rows, [("bought", {"upgrade": action, "level": 1, "price": price, "money": 0})])
                self.assertEqual((shop.money, shop.earned, shop.reputation), (0, price, 3.2))
                self.assertEqual(shop.snapshot()["upgrades"][action], 1)

    def test_purchases_advance_to_next_level_then_stop_at_maximum(self):
        for action in ("oxygen", "hp"):
            with self.subTest(action=action):
                levels = self.tuning["shop"]["upgrades"][action]
                total = sum(level["price"] for level in levels)
                shop = self.make_shop(total)
                rows = self.steps(shop, 3, [{"tick": i, "buy": action} for i in range(3)])
                self.assertEqual([name for name, _ in rows], ["bought", "bought", "buy_failed"])
                self.assertEqual([data["level"] for name, data in rows if name == "bought"], [1, 2])
                self.assertEqual(rows[-1][1], {"action": action, "reason": "max_level"})
                self.assertEqual((shop.money, shop.earned, shop.upgrades[action]), (0, total, 2))

    def test_insufficient_funds_changes_neither_money_nor_levels(self):
        price = self.tuning["shop"]["upgrades"]["oxygen"][0]["price"]
        shop = self.make_shop(price - 1)
        self.assertEqual(self.steps(shop, inputs=[{"tick": 0, "buy": "oxygen"}]),
                         [("buy_failed", {"action": "oxygen", "reason": "funds"})])
        self.assertEqual((shop.money, shop.earned, shop.upgrades), (price - 1, price - 1, {}))

    def test_repeat_purchase_with_no_money_targets_level_two(self):
        shop = self.make_shop(200)
        rows = self.steps(shop, 2, [{"tick": 0, "buy": "oxygen"}, {"tick": 1, "buy": "oxygen"}])
        self.assertEqual(rows[-1], ("buy_failed", {"action": "oxygen", "reason": "funds"}))
        self.assertEqual(shop.upgrades, {"oxygen": 1})

    def test_unknown_and_optional_actions_do_not_change_state(self):
        for action in ("missing", "weapon", "net", "buy:ca_loc", "sell:ca_loc"):
            with self.subTest(action=action):
                shop = self.make_shop(1000)
                self.assertEqual(self.steps(shop, inputs=[{"tick": 0, "buy": action}]),
                                 [("buy_failed", {"action": action, "reason": "unknown"})])
                self.assertEqual((shop.money, shop.earned, shop.upgrades), (1000, 1000, {}))

    def test_buy_only_runs_at_declared_frame_not_inherited(self):
        shop = self.make_shop(1000)
        rows = self.steps(shop, 10, [{"tick": 0, "buy": "oxygen"}])
        self.assertEqual(len(rows), 1)
        self.assertEqual(shop.upgrades, {"oxygen": 1})
        self.assertEqual(shop.money, 800)

    def test_buy_then_done_in_same_step_and_end_emitted_only_once(self):
        shop = self.make_shop(200)
        rows = self.steps(shop, inputs=[{"tick": 0, "buy": "oxygen", "shop_done": True}])
        self.assertEqual([name for name, _ in rows], ["bought", "shop_end"])
        self.assertEqual(rows[-1][1], {"reason": "done"})
        self.assertEqual((shop.done, shop.reason, shop.money), (True, "done", 0))
        before = shop.snapshot()
        self.assertEqual(shop.step(InputPlayer([]).advance(0)), [])
        self.assertEqual(shop.snapshot(), before)

    def test_buy_and_done_at_final_tick_take_priority_over_timeout(self):
        shop = self.make_shop(250)
        rows = self.steps(shop, 600, [{"tick": 599, "buy": "hp", "shop_done": True}])
        self.assertEqual([name for name, _ in rows], ["bought", "shop_end"])
        self.assertEqual(rows[-1][1], {"reason": "done"})
        self.assertEqual(shop.time_left_ticks, 0)
        self.assertEqual(shop.upgrades["hp"], 1)

    def test_buy_at_final_tick_is_processed_before_timeout(self):
        shop = self.make_shop(200)
        rows = self.steps(shop, 600, [{"tick": 599, "buy": "oxygen"}])
        self.assertEqual([name for name, _ in rows], ["bought", "shop_end"])
        self.assertEqual(rows[-1][1], {"reason": "time"})
        self.assertEqual(shop.money, 0)

    def test_shop_times_out_after_600_active_steps(self):
        shop = self.make_shop()
        self.assertEqual(self.steps(shop, 599), [])
        self.assertEqual((shop.time_left_ticks, shop.done), (1, False))
        self.assertEqual(self.steps(shop), [("shop_end", {"reason": "time"})])
        self.assertEqual((shop.phase_tick, shop.time_left_ticks, shop.reason), (600, 0, "time"))

    def test_prices_levels_and_duration_read_from_tuning(self):
        self.tuning["shop"]["max_ticks"] = 2
        self.tuning["shop"]["upgrades"]["oxygen"][0]["price"] = 17
        shop = self.make_shop(17)
        rows = self.steps(shop, 2, [{"tick": 1, "buy": "oxygen"}])
        self.assertEqual(rows, [("bought", {"upgrade": "oxygen", "level": 1, "price": 17, "money": 0}),
                                ("shop_end", {"reason": "time"})])

    def test_snapshot_keeps_leftover_stock_and_does_not_activate_or_mutate_input_upgrades(self):
        upgrades = {"oxygen": 0, "hp": 1}
        ctx = {"day": 2, "day_plan": copy.deepcopy(self.tuning["day_plan"][1]),
               "active_upgrades": dict(upgrades)}
        before_upgrades, before_ctx = copy.deepcopy(upgrades), copy.deepcopy(ctx)
        shop = self.make_shop(200, upgrades, ctx)
        shop.stock = {"ca_loc": 0, "keo_neo": 1, "bong_sung": 2}
        self.steps(shop, inputs=[{"tick": 0, "buy": "oxygen"}])
        self.assertEqual(shop.snapshot(), {"stock": {"bong_sung": 2, "keo_neo": 1},
                                          "upgrades": {"hp": 1, "oxygen": 1}, "time_left_ticks": 599})
        self.assertEqual(upgrades, before_upgrades)
        self.assertEqual(ctx, before_ctx)
        self.assertEqual(shop.day_ctx["active_upgrades"]["oxygen"], 0)

    def test_existing_day_loop_uses_shop_sim_and_preserves_cumulative_state(self):
        session = Session("day", self.tuning, {"day": {"money": 200, "earned": 300, "reputation": 4},
                          "gather": {"hold": ["ca_loc"]}, "quan": {"time_left_ticks": 1}}, 1)
        inputs = InputPlayer([{"tick": 0, "interact": True}, {"tick": 1, "interact": False},
                              {"tick": 2, "buy": "oxygen"}])
        for tick in range(3):
            session.step(inputs.advance(tick))
        self.assertIsInstance(session.sim, DaySim)
        self.assertIsInstance(session.sim.sim, ShopSim)
        self.assertEqual((session.sim.money, session.sim.earned, session.sim.reputation), (0, 300, 4))
        self.assertEqual(session.snapshot()["score"], 700)
        self.assertEqual(session.snapshot()["stock"], {"ca_loc": 1})
        self.assertEqual(session.snapshot()["active_upgrades"]["oxygen"], 0)


class ShopHeadless(unittest.TestCase):
    def run_day(self, w, scenario, inputs, ticks, days=1, name="day"):
        sc = write_json(w.path(name + "-scenario.json"), scenario)
        ip = write_json(w.path(name + "-inputs.json"), frames(*inputs))
        out = w.path(name + ".jsonl")
        code, err = run_headless("--mode", "day", "--days", str(days), "--seed", "7",
                                 "--scenario", sc, "--inputs", ip, "--ticks", str(ticks),
                                 "--snapshot-every", "1", "--out", out)
        self.assertEqual(code, 0, err)
        return out, read_jsonl(out)

    def fast_scenario(self, money=200, earned=None):
        return {"day": {"money": money, "earned": money if earned is None else earned},
                "gather": {"hold": items("ca_loc"), "random_fish": False, "monsters": []},
                "quan": {"time_left_ticks": 1}}

    def test_shop_pause_drops_buy_and_done_then_resumes_gameplay_immediately(self):
        with Workdir() as w:
            _, rows = self.run_day(w, self.fast_scenario(), [
                {"tick": 0, "interact": True}, {"tick": 1, "interact": False},
                {"tick": 2, "pause": True, "buy": "oxygen", "shop_done": True},
                {"tick": 3, "pause": False, "shop_done": False, "buy": "hp"},
                {"tick": 5, "pause": True, "buy": "oxygen", "shop_done": True}], 20)
        s = {row["tick"]: row for row in snapshots(rows)}
        for tick in (3, 4, 5):
            self.assertEqual((s[tick]["state"], s[tick]["time_left_ticks"], s[tick]["phase_tick"], s[tick]["sim_tick"]),
                             ("paused", 600, 0, 2))
            self.assertEqual(s[tick]["money"], 200)
        self.assertEqual([(r["tick"], r["name"]) for r in events(rows) if r["phase"] == "shop"],
                         [(2, "phase_start"), (3, "paused"), (6, "resumed"), (6, "bought"), (6, "shop_end")])
        self.assertEqual((rows[-1]["ticks"], rows[-1]["reason"], rows[-1]["money"]), (6, "days_complete", 0))

    def test_held_shop_done_across_phase_change_does_not_create_edge(self):
        with Workdir() as w:
            _, rows = self.run_day(w, self.fast_scenario(), [
                {"tick": 0, "interact": True, "shop_done": True}, {"tick": 1, "interact": False},
                {"tick": 4, "shop_done": False}, {"tick": 5, "shop_done": True}], 20)
        self.assertEqual(events(rows, "shop_end")[0]["tick"], 6)
        self.assertEqual(rows[-1]["days_completed"], 1)

    def test_both_upgrades_apply_only_at_next_day_and_leftover_stock_is_discarded(self):
        with Workdir() as w:
            _, rows = self.run_day(w, self.fast_scenario(money=450, earned=700), [
                {"tick": 0, "interact": True}, {"tick": 1, "interact": False},
                {"tick": 2, "buy": "oxygen"}, {"tick": 3, "buy": "hp"},
                {"tick": 4, "shop_done": True}], 10, days=2)
        s = {row["tick"]: row for row in snapshots(rows)}
        self.assertEqual(s[4]["upgrades"], {"oxygen": 1, "hp": 1})
        self.assertEqual(s[4]["active_upgrades"], {"oxygen": 0, "hp": 0})
        self.assertEqual(item_counts(s[4]["stock"]), {"ca_loc": 1})  # v1.2: kho Shop là mảng cá thể
        self.assertEqual((s[5]["day"], s[5]["phase"], s[5]["phase_tick"]), (2, "gather", 0))
        self.assertEqual(s[5]["active_upgrades"], {"oxygen": 1, "hp": 1})
        self.assertEqual((s[5]["player"]["oxygen_max_ticks"], s[5]["player"]["oxygen_ticks"],
                          s[5]["player"]["hp_max"], s[5]["player"]["hp"]), (2700, 2700, 4, 4))
        self.assertEqual([it["kind"] for it in s[5]["hold"]], ["ca_loc"])  # mẫu gather; không cộng kho dư Shop
        self.assertEqual((s[5]["money"], s[5]["earned"], s[5]["score"]), (0, 700, 1000))

    def test_last_day_counts_only_after_shop_timeout(self):
        with Workdir() as w:
            _, rows = self.run_day(w, self.fast_scenario(), [
                {"tick": 0, "interact": True}, {"tick": 1, "interact": False}], 1000)
        self.assertEqual(events(rows, "shop_end")[0]["data"], {"reason": "time"})
        self.assertEqual((rows[-1]["ticks"], rows[-1]["days_completed"], rows[-1]["reason"]), (602, 1, "days_complete"))

    def test_day_uses_plan_override_and_rejects_available_outside_dish(self):
        scenario = self.fast_scenario()
        scenario["day"]["day_plan"] = [{"day": 1, "dishes": {"goi_bong_sung": 1}}]
        scenario["quan"]["time_left_ticks"] = 121
        scenario["quan"]["random_customers"] = True
        with Workdir() as w:
            _, rows = self.run_day(w, scenario, [{"tick": 0, "interact": True},
                                               {"tick": 1, "interact": False},
                                               {"tick": 122, "shop_done": True}], 150)
        self.assertEqual(events(rows, "customer_arrived"), [])
        self.assertEqual([(r["tick"], r["data"]) for r in events(rows, "no_dish")], [(121, {})])
        self.assertEqual(rows[-1]["reason"], "days_complete")

    def test_day_shop_deterministic_bytes_with_purchase_pause_and_close(self):
        inputs = [{"tick": 0, "interact": True}, {"tick": 1, "interact": False},
                  {"tick": 2, "buy": "oxygen"}, {"tick": 3, "pause": True},
                  {"tick": 4, "pause": False}, {"tick": 5, "pause": True},
                  {"tick": 6, "pause": False, "shop_done": True}]
        with Workdir() as w:
            a, rows = self.run_day(w, self.fast_scenario(), inputs, 20, name="a")
            b, _ = self.run_day(w, self.fast_scenario(), inputs, 20, name="b")
            self.assertEqual(Path(a).read_bytes(), Path(b).read_bytes())
        self.assertEqual(len(events(rows, "bought")), 1)
        self.assertEqual(rows[-1]["money"], 0)
        self.assertEqual(rows[-1]["earned"], 200)


if __name__ == "__main__":
    unittest.main()

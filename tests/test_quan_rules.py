"""Issue #3 (Hie24): PRD-0 D/E/F.Quán, cả luật và headless hộp đen."""

import copy
import unittest
from pathlib import Path

from chonoi.contract import load_contract
from chonoi.inputs import InputPlayer
from chonoi.ids import IdAllocator
from chonoi.rng import Streams
from chonoi.runner import Session
from chonoi.sim.quan import QuanSim

from helpers import Workdir, events, frames, read_jsonl, run_headless, snapshots, stock_items, write_json


FISH_DISH = "ca_loc_nuong_trui"
SALAD = "goi_bong_sung"
HOT_POT = "lau_ca_linh_dien_dien"


def customer(ident="C1", table="T1", dish=FISH_DISH, **updates):
    result = {"id": ident, "table_id": table, "dish_id": dish}
    result.update(updates)
    return result


def payload(order="C1", dish=FISH_DISH, price=60):
    return {"order_id": order, "dish_id": dish, "base_price": price}


class QuanRules(unittest.TestCase):
    def setUp(self):
        self.tuning = load_contract()["tuning"]

    def session(self, scenario=None, seed=7):
        block = {"random_customers": False, "stock": {}}  # regression P1 nội bộ dạng đếm
        block.update(scenario or {})
        return Session("quan", self.tuning, block, seed)

    def steps(self, session, count=1, inputs=()):
        player = InputPlayer(list(inputs))
        result = []
        for _ in range(count):
            if session.done:
                break
            result.extend(session.step(player.advance(session.tick)))
        return result

    def stove_fixture(self, state="ready", **updates):
        stove = {"id": "B1", "state": state, "dish": payload(), "cook_ticks_left": 0, "ready_ticks": 0}
        stove.update(updates)
        return stove

    def assigned(self, **updates):
        return customer(order_status="assigned", reserved={}, **updates)

    def test_snapshot_defaults_reservations_physical_stock_and_no_fixture_mutation(self):
        fixture = {"stock": {"ca_loc": 2}, "customers": [customer()],
                   "player": {"pos": [8, 5]}, "random_customers": False}
        original = copy.deepcopy(fixture)
        session = self.session(fixture)
        state = session.snapshot()
        c = state["customers"][0]
        self.assertEqual(c, dict(customer(), order_tick=0, state="waiting", patience_ticks_left=3600,
                                 eat_ticks_left=0, order_status="reserved", reserved={"ca_loc": 1},
                                 base_price=0, tip=0))
        self.assertEqual(state["stock"], {"ca_loc": 2})
        self.assertEqual(state["player"]["vel"], [0, 0])
        self.assertEqual(session.sim._available(), {"ca_loc": 1})
        self.steps(session, 1)
        self.assertEqual(fixture, original)

    def test_arrival_exact_schedule_then_full_patience_and_reserved_stock(self):
        session = self.session({"stock": {"ca_loc": 1}, "random_customers": True})
        self.assertEqual(self.steps(session, 119), [])
        rows = self.steps(session)
        self.assertEqual(rows, [{"type": "event", "tick": 120, "phase": "quan",
                                 "name": "customer_arrived", "data": {
                                     "order_id": "C1", "table_id": "T1", "dish_id": FISH_DISH}}])
        self.assertEqual(session.sim.customers[0]["order_tick"], 120)
        self.assertEqual(session.sim.customers[0]["patience_ticks_left"], 3600)
        self.assertEqual(session.sim.stock, {"ca_loc": 1})
        self.steps(session)
        self.assertEqual(session.sim.customers[0]["patience_ticks_left"], 3599)

    def test_schedule_uses_phase_tick_not_shortened_duration(self):
        session = self.session({"stock": {"ca_loc": 1}, "random_customers": True, "time_left_ticks": 121})
        self.assertEqual(events(self.steps(session, 119), "customer_arrived"), [])
        self.assertEqual(events(self.steps(session), "customer_arrived")[0]["tick"], 120)

    def test_no_dish_empty_event_repeats_only_at_scheduled_ticks(self):
        session = self.session({"random_customers": True})
        rows = self.steps(session, 1020)
        self.assertEqual([(r["tick"], r["data"]) for r in rows], [(120, {}), (1020, {})])
        self.assertTrue(all(r["name"] == "no_dish" for r in rows))
        self.assertEqual(session.sim.customers, [])

    def test_random_customers_false_disables_arrival_but_keeps_fixtures(self):
        session = self.session({"customers": [customer()], "stock": {"ca_loc": 1}})
        self.assertEqual(self.steps(session, 120), [])
        self.assertEqual([c["id"] for c in session.sim.customers], ["C1"])

    def test_occupied_table_skips_arrival_without_no_dish(self):
        self.tuning["quan"]["tables"] = self.tuning["quan"]["tables"][:1]  # v1.1 có 4 bàn; ca này cần đúng 1 bàn
        session = self.session({"customers": [customer()], "stock": {"ca_loc": 1}, "random_customers": True})
        self.assertEqual(self.steps(session, 1020), [])

    def test_departure_before_arrival_reuses_table_and_continues_ids(self):
        session = self.session({"customers": [customer("C10", patience_ticks_left=120)],
                                "stock": {"ca_loc": 1}, "random_customers": True})
        rows = self.steps(session, 120)
        self.assertEqual([r["name"] for r in rows], ["customer_left", "customer_arrived"])
        self.assertEqual([r["tick"] for r in rows], [120, 120])
        self.assertEqual(rows[1]["data"]["order_id"], "C11")
        self.assertEqual(session.sim.stock, {"ca_loc": 1})

    def test_available_stock_excludes_other_orders_reservations(self):
        # Extra table in unit data exercises ordering/accounting without changing the P1 contract file.
        self.tuning["quan"]["tables"].append({"id": "T2", "pos": [12, 2]})
        session = self.session({"customers": [customer()], "stock": {"ca_loc": 1, "bong_sung": 2},
                                "random_customers": True})
        rows = self.steps(session, 120)
        self.assertEqual(rows[0]["data"]["dish_id"], SALAD)
        self.assertEqual(rows[0]["data"]["table_id"], "T2")
        self.assertEqual(session.sim.stock, {"ca_loc": 1, "bong_sung": 2})
        self.assertEqual(session.sim._available(), {"ca_loc": 0, "bong_sung": 0})

    def test_seeded_selection_covers_three_dishes(self):
        choices = set()
        for seed in range(30):
            session = self.session({"stock": {"ca_loc": 1, "bong_sung": 2, "ca_linh": 3, "bong_dien_dien": 1},
                                    "random_customers": True}, seed=seed)
            choices.add(events(self.steps(session, 120), "customer_arrived")[0]["data"]["dish_id"])
        # v1.1: kho này còn đủ canh_chua_ca_loc (ca_loc 1 + bong_dien_dien 1) nên có 4 món hợp lệ.
        self.assertEqual(choices, {FISH_DISH, SALAD, HOT_POT, "canh_chua_ca_loc"})

    def test_cook_consumes_reserved_once_and_interact_requires_rising_edge(self):
        session = self.session({"player": {"pos": [2, 8]}, "customers": [customer()], "stock": {"ca_loc": 2}})
        rows = self.steps(session, 3, [{"tick": 0, "interact": True}])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "cook_started")
        self.assertEqual(rows[0]["data"], {"stove_id": "B1", "order_id": "C1", "dish_id": FISH_DISH,
                                            "items": ["ca_loc"], "base_price": 60})
        self.assertEqual(session.sim.stock, {"ca_loc": 1})
        self.assertEqual(session.sim.customers[0]["reserved"], {})
        self.assertEqual(session.sim.customers[0]["order_status"], "assigned")
        self.assertEqual(session.sim.stoves[0]["cook_ticks_left"], 358)

    def test_cook_items_sorted_and_price_and_time_come_from_tuning(self):
        self.tuning["menu"][HOT_POT].update(price=137, cook_s=2)
        session = self.session({"player": {"pos": [2, 8]}, "stock": {"ca_linh": 3, "bong_dien_dien": 1},
                                "customers": [customer(dish=HOT_POT)]})
        rows = self.steps(session, inputs=[{"tick": 0, "interact": True}])
        self.assertEqual(rows[0]["data"]["items"], ["bong_dien_dien", "ca_linh", "ca_linh", "ca_linh"])
        self.assertEqual(rows[0]["data"]["base_price"], 137)
        self.assertEqual(session.sim.stoves[0]["cook_ticks_left"], 120)

    def test_cook_ready_exact_tick_and_pick_same_tick(self):
        session = self.session({"player": {"pos": [2, 8]}, "stock": {"ca_loc": 1}, "customers": [customer()]})
        rows = self.steps(session, 361, [{"tick": 0, "interact": True}, {"tick": 1, "interact": False},
                                         {"tick": 360, "interact": True}])
        self.assertEqual([(r["name"], r["tick"]) for r in rows],
                         [("cook_started", 1), ("dish_ready", 361), ("dish_picked", 361)])
        self.assertEqual(session.sim.hand, payload())
        self.assertEqual(session.sim.stoves[0]["state"], "idle")

    def test_ready_age_and_no_burn(self):
        session = self.session({"customers": [self.assigned()],
                                "stoves": [self.stove_fixture("cooking", cook_ticks_left=1)]})
        self.assertEqual(self.steps(session)[0]["name"], "dish_ready")
        self.assertEqual(session.sim.stoves[0]["ready_ticks"], 0)
        self.steps(session, 1000)
        self.assertEqual(session.sim.stoves[0]["state"], "ready")
        self.assertEqual(session.sim.stoves[0]["ready_ticks"], 1000)

    def test_nearest_unusable_target_does_not_fall_back(self):
        session = self.session({"player": {"pos": [2, 8]}, "tables": [{"id": "T1", "pos": [3, 8]}],
                                "customers": [self.assigned()], "hand": payload()})
        self.assertEqual(self.steps(session, inputs=[{"tick": 0, "interact": True}]), [])
        self.assertEqual(session.sim.hand, payload())

    def test_equal_distance_stove_wins_over_table(self):
        session = self.session({"player": {"pos": [2, 8]}, "tables": [{"id": "T1", "pos": [2, 8]}],
                                "customers": [self.assigned()], "hand": payload()})
        self.assertEqual(self.steps(session, inputs=[{"tick": 0, "interact": True}]), [])
        self.assertEqual(session.sim.customers[0]["state"], "waiting")

    def test_pick_requires_empty_hand_and_does_not_serve_in_same_interact(self):
        self.tuning["quan"]["tables"].append({"id": "T2", "pos": [10, 2]})
        session = self.session({"player": {"pos": [2, 8]}, "customers": [self.assigned(),
                                customer("C2", "T2", order_status="assigned", reserved={})],
                                "stoves": [self.stove_fixture()], "hand": payload("C2")})
        self.assertEqual(self.steps(session, inputs=[{"tick": 0, "interact": True}]), [])
        self.assertEqual(session.sim.hand["order_id"], "C2")
        self.assertEqual(session.sim.stoves[0]["state"], "ready")

    def test_interact_radius_inclusive_and_outside_is_rejected(self):
        for offset, expected in ((1.5, 1), (1.5001, 0)):
            with self.subTest(offset=offset):
                session = self.session({"player": {"pos": [9 + offset, 2]}, "hand": payload(),
                                        "customers": [self.assigned()]})
                self.assertEqual(len(self.steps(session, inputs=[{"tick": 0, "interact": True}])), expected)

    def test_wrong_order_cannot_be_served(self):
        self.tuning["quan"]["tables"].append({"id": "T2", "pos": [12, 2]})
        session = self.session({"player": {"pos": [9, 2]}, "stock": {"ca_loc": 1},
                                "customers": [customer(), customer("C2", "T2", order_status="assigned", reserved={})],
                                "hand": payload("C2")})
        self.assertEqual(self.steps(session, inputs=[{"tick": 0, "interact": True}]), [])
        self.assertEqual(session.sim.hand["order_id"], "C2")

    def test_tip_boundary_after_decrement_and_awarded_only_on_payment(self):
        for patience, tip in ((1801, 12), (1800, 0)):
            with self.subTest(patience=patience):
                session = self.session({"player": {"pos": [9, 2]}, "hand": payload(),
                                        "customers": [self.assigned(patience_ticks_left=patience)]})
                served = self.steps(session, inputs=[{"tick": 0, "interact": True}])[0]
                self.assertEqual(served["data"]["tip"], tip)
                self.assertEqual(session.sim.reputation, 3)
                self.assertEqual(session.sim.money, 0)
                self.assertEqual(session.sim.customers[0]["eat_ticks_left"], 600)
                self.assertEqual(self.steps(session, 599), [])
                paid = self.steps(session)[0]
                self.assertEqual((paid["name"], paid["tick"]), ("paid", 601))
                self.assertEqual(paid["data"]["amount"], 60 + tip)
                self.assertEqual(paid["data"]["reason"], "finished_eating")
                self.assertEqual((session.sim.money, session.sim.earned, session.sim.shift_earned), (60 + tip,) * 3)
                self.assertAlmostEqual(session.sim.reputation, 3.2 if tip else 3)
                self.assertEqual(session.snapshot()["tables"][0]["customer_id"], None)

    def test_tip_is_floored_and_base_price_is_payload_price(self):
        session = self.session({"player": {"pos": [9, 2]}, "hand": payload(price=63),
                                "customers": [self.assigned()]})
        self.assertEqual(self.steps(session, inputs=[{"tick": 0, "interact": True}])[0]["data"]["tip"], 12)

    def test_service_on_patience_zero_tick_is_accepted(self):
        session = self.session({"player": {"pos": [9, 2]}, "hand": payload(),
                                "customers": [self.assigned(patience_ticks_left=1)]})
        rows = self.steps(session, inputs=[{"tick": 0, "interact": True}])
        self.assertEqual([r["name"] for r in rows], ["served"])
        self.assertEqual(rows[0]["data"]["patience_ticks_left"], 0)
        self.assertEqual(rows[0]["data"]["tip"], 0)
        self.assertEqual(session.sim.customers[0]["state"], "eating")

    def test_patience_leaving_releases_raw_but_never_refunds_cooked_items(self):
        fixtures = [({"stock": {"ca_loc": 1}, "customers": [customer(patience_ticks_left=1)]}, 1),
                    ({"customers": [self.assigned(patience_ticks_left=1)], "stoves": [self.stove_fixture()]}, 0),
                    ({"customers": [self.assigned(patience_ticks_left=1)],
                      "stoves": [self.stove_fixture("cooking", cook_ticks_left=10)]}, 0),
                    ({"customers": [self.assigned(patience_ticks_left=1)], "hand": payload()}, 0)]
        for fixture, remaining in fixtures:
            with self.subTest(fixture=fixture):
                session = self.session(fixture)
                rows = self.steps(session)
                self.assertEqual(rows[0]["data"], {"order_id": "C1", "table_id": "T1",
                                                   "reason": "patience", "reputation": 2.5})
                self.assertEqual(session.sim.customers, [])
                self.assertEqual(session.sim.stock.get("ca_loc", 0), remaining)
                self.assertIsNone(session.sim.hand)
                self.assertEqual(session.sim.stoves[0]["state"], "idle")

    def test_unfulfillable_order_waits_and_cannot_cook(self):
        session = self.session({"player": {"pos": [2, 8]}, "stock": {"ca_loc": 1},
                                "customers": [customer(order_status="unfulfillable", reserved={}, patience_ticks_left=2)]})
        self.assertEqual(self.steps(session, inputs=[{"tick": 0, "interact": True}]), [])
        self.assertEqual(self.steps(session)[0]["name"], "customer_left")
        self.assertEqual(session.sim.stock, {"ca_loc": 1})

    def test_closing_can_serve_pay_then_end_on_same_tick(self):
        session = self.session({"time_left_ticks": 1, "player": {"pos": [9, 2]}, "hand": payload(),
                                "customers": [self.assigned()]})
        rows = self.steps(session, inputs=[{"tick": 0, "interact": True}])
        self.assertEqual([r["name"] for r in rows], ["served", "paid", "quan_end"])
        self.assertTrue(all(r["tick"] == 1 for r in rows))
        self.assertEqual(rows[1]["data"]["reason"], "closing")
        self.assertEqual(rows[2]["data"], {"reason": "time", "money": 72, "earned": 72,
                                          "shift_earned": 72, "reputation": 3.2})
        self.assertEqual(session.end_row()["score"], 372)

    def test_closing_waiting_customer_never_penalizes_even_at_zero_patience(self):
        session = self.session({"time_left_ticks": 1, "stock": {"ca_loc": 1},
                                "customers": [customer(patience_ticks_left=1)]})
        rows = self.steps(session)
        self.assertEqual([r["name"] for r in rows], ["customer_left", "quan_end"])
        self.assertEqual(rows[0]["data"]["reason"], "closing")
        self.assertEqual(session.sim.reputation, 3)
        self.assertEqual(session.sim.stock, {"ca_loc": 1})
        self.assertEqual(session.sim.step(InputPlayer([]).advance(0)), [])

    def test_eating_finish_has_priority_over_closing_and_does_not_spawn(self):
        session = self.session({"time_left_ticks": 120, "random_customers": True,
                                "customers": [customer(state="eating", order_status="served", reserved={},
                                                       eat_ticks_left=120, base_price=60, tip=12)]})
        rows = self.steps(session, 120)
        self.assertEqual([r["name"] for r in rows], ["paid", "quan_end"])
        self.assertEqual(rows[0]["data"]["reason"], "finished_eating")

    def test_reputation_is_clamped_at_both_limits(self):
        session = self.session({"reputation": 0.1, "stock": {"ca_loc": 1},
                                "customers": [customer(patience_ticks_left=1)]})
        self.steps(session)
        self.assertEqual(session.sim.reputation, 0)
        session = self.session({"reputation": 4.9, "customers": [customer(state="eating", order_status="served",
                                reserved={}, eat_ticks_left=1, base_price=60, tip=12)]})
        self.steps(session)
        self.assertEqual(session.sim.reputation, 5)

    def test_oldest_order_then_numeric_table_id_and_snapshot_id_sort(self):
        self.tuning["quan"]["tables"] += [{"id": "T10", "pos": [10, 2]}, {"id": "T2", "pos": [12, 2]}]
        for ticks, expected in (((4, 1, 1), "C2"), ((0, 1, 1), "C1")):
            with self.subTest(ticks=ticks):
                session = self.session({"player": {"pos": [2, 8]}, "stock": {"ca_loc": 3}, "customers": [
                    customer("C10", "T10", order_tick=ticks[1]), customer("C2", "T2", order_tick=ticks[2]),
                    customer("C1", "T1", order_tick=ticks[0])]})
                self.assertEqual([c["id"] for c in session.snapshot()["customers"]], ["C1", "C2", "C10"])
                rows = self.steps(session, inputs=[{"tick": 0, "interact": True}])
                self.assertEqual(rows[0]["data"]["order_id"], expected)


class QuanHeadless(unittest.TestCase):
    def run_game(self, workdir, scenario, ticks, inputs=(), stem="out", seed=7):
        scenario = copy.deepcopy(scenario)
        if isinstance(scenario.get("stock"), dict):  # v1.2: kho cá thể ở đầu vào headless
            scenario["stock"] = stock_items(scenario["stock"])
        for c in scenario.get("customers", []):
            if c.get("reserved") == {}:
                c["reserved"] = []  # P3: phần giữ rỗng là mảng id
        sc = write_json(workdir.path(stem + "-scenario.json"), {"quan": scenario})
        inp = write_json(workdir.path(stem + "-inputs.json"), frames(*inputs))
        out = workdir.path(stem + ".jsonl")
        code, err = run_headless("--mode", "quan", "--seed", str(seed), "--ticks", str(ticks),
                                 "--scenario", sc, "--inputs", inp, "--out", out, "--snapshot-every", "1")
        self.assertEqual(code, 0, err)
        return out, read_jsonl(out)

    def test_full_cook_walk_serve_eat_pay_through_real_cli(self):
        with Workdir() as w:
            _, rows = self.run_game(w, {"player": {"pos": [2, 8]}, "stock": {"ca_loc": 1},
                                       "customers": [customer()], "random_customers": False}, 1111, [
                {"tick": 0, "interact": True}, {"tick": 1, "interact": False},
                {"tick": 360, "interact": True}, {"tick": 361, "interact": False, "move": [0.759257, -0.650791]},
                {"tick": 501, "move": [0, 0]}, {"tick": 510, "interact": True}])
            self.assertEqual([(r["name"], r["tick"]) for r in events(rows)],
                             [("cook_started", 1), ("dish_ready", 361), ("dish_picked", 361),
                              ("served", 511), ("paid", 1111)])
            self.assertEqual(rows[-1]["money"], 70)  # P3: floor(60×fresh/100)=59, boa 11
            self.assertEqual(rows[-1]["score"], 370)
            self.assertEqual(rows[-1]["reason"], "tick_limit")
            self.assertEqual(snapshots(rows)[-1]["stock"], [])
            self.assertEqual(snapshots(rows)[-1]["customers"], [])

    def test_seeded_jsonl_is_byte_identical_with_reordered_input_maps(self):
        scenario = {"stock": {"ca_loc": 2, "bong_sung": 2, "ca_linh": 3, "bong_dien_dien": 1},
                    "random_customers": True, "time_left_ticks": 4000}
        with Workdir() as w:
            a, first = self.run_game(w, scenario, 4000, stem="a", seed=-17)
            scenario["stock"] = dict(reversed(list(scenario["stock"].items())))
            b, _ = self.run_game(w, scenario, 4000, stem="b", seed=-17)
            self.assertEqual(Path(a).read_bytes(), Path(b).read_bytes())
            self.assertTrue(events(first, "customer_arrived"))
            self.assertTrue(events(first, "customer_left"))
            self.assertEqual(first[-1]["reason"], "time")
            self.assertEqual(len(events(first, "quan_end")), 1)

    def test_closing_tick_fixture_and_single_final_snapshot(self):
        with Workdir() as w:
            _, rows = self.run_game(w, {"player": {"pos": [9, 2]}, "time_left_ticks": 1,
                                       "customers": [customer(order_status="assigned", reserved=[])],
                                       "hand": payload(), "random_customers": False}, 1,
                                    [{"tick": 0, "interact": True}])
            self.assertEqual([r["name"] for r in events(rows)], ["served", "paid", "quan_end"])
            self.assertEqual([s["tick"] for s in snapshots(rows)], [0, 1])
            self.assertEqual(rows[-1]["reason"], "time")
            self.assertEqual(rows[-1]["state"], "finished")
            self.assertEqual(rows[-1]["money"], 72)


class QuanPhase2(unittest.TestCase):
    """Issue #7: kiểm trực tiếp day_ctx và tích hợp với day.py hiện có."""

    def setUp(self):
        self.tuning = load_contract()["tuning"]

    def make_sim(self, scenario=None, day_ctx=None, seed=7):
        block = {"random_customers": False, "stock": {}}  # regression P2 nội bộ dạng đếm
        block.update(scenario or {})
        return QuanSim(self.tuning, block, Streams(seed), IdAllocator(), day_ctx=day_ctx)

    def test_reputation_sum_has_no_float_drift(self):
        """Review PR #6: từ uy tín 0, 10 lần boa phải ra đúng 2.0 để floor không mất 100 điểm."""
        sim = self.make_sim({"reputation": 0.0})
        for _ in range(10):
            sim._change_reputation(self.tuning["quan"]["tip_reputation"])
        self.assertEqual(sim.reputation, 2.0)
        sim = self.make_sim({"reputation": 3.0})
        for delta in [self.tuning["quan"]["left_reputation_delta"]] * 4 + [self.tuning["quan"]["tip_reputation"]] * 10:
            sim._change_reputation(delta)
        self.assertEqual(sim.reputation, 3.0)

    def steps(self, sim, count=1, inputs=()):
        player = InputPlayer(list(inputs))
        rows = []
        for _ in range(count):
            if sim.done:
                break
            rows.extend(sim.step(player.advance(sim.phase_tick)))
        return rows

    def ctx(self, dishes=None):
        plan = copy.deepcopy(self.tuning["day_plan"][0])
        if dishes is not None:
            plan["dishes"] = dishes
        return {"day": 1, "day_plan": plan, "active_upgrades": {"oxygen": 0, "hp": 0}}

    def test_standalone_uses_two_stoves_four_tables_and_all_six_dishes(self):
        stock = {"ca_loc": 2, "bong_sung": 2, "ca_linh": 3, "ca_keo": 2,
                 "bong_dien_dien": 2, "keo_neo": 1}
        chosen = set()
        for seed in range(40):
            sim = self.make_sim({"stock": stock, "random_customers": True}, seed=seed)
            self.assertEqual([s["id"] for s in sim.stoves], ["B1", "B2"])
            self.assertEqual([t["id"] for t in sim.tables], ["T1", "T2", "T3", "T4"])
            chosen.add(self.steps(sim, 120)[0][1]["dish_id"])
        self.assertEqual(chosen, set(self.tuning["menu"]))
        self.assertEqual(len(chosen), 6)

    def test_day_context_excludes_dishes_outside_plan_before_stock_check(self):
        # Cá kèo đủ nấu món ngoài D1, nhưng không có món D1 nấu được.
        sim = self.make_sim({"stock": {"ca_keo": 2}, "random_customers": True}, self.ctx())
        self.assertEqual(self.steps(sim, 120), [("no_dish", {})])
        self.assertEqual(sim.customers, [])
        self.assertEqual(sim.stock, {"ca_keo": 2})

    def test_day_context_filters_full_tuning_without_mutating_inputs(self):
        ctx = self.ctx({SALAD: 1})
        before_ctx, before_tuning = copy.deepcopy(ctx), copy.deepcopy(self.tuning)
        for seed in range(5):
            sim = self.make_sim({"stock": {"ca_loc": 1, "bong_sung": 2, "ca_keo": 2},
                                 "random_customers": True}, ctx, seed)
            self.assertEqual(self.steps(sim, 120)[0][1]["dish_id"], SALAD)
        self.assertEqual(ctx, before_ctx)
        self.assertEqual(self.tuning, before_tuning)

    def test_plan_serving_count_does_not_limit_more_orders_or_add_bonus(self):
        sim = self.make_sim({"stock": {"ca_loc": 1}, "random_customers": True,
                             "customers": [customer(state="eating", order_status="served", reserved={},
                                                    eat_ticks_left=1, base_price=60, tip=0)]},
                            self.ctx({FISH_DISH: 1}))
        rows = self.steps(sim, 120)
        self.assertEqual([name for name, _ in rows], ["paid", "customer_arrived"])
        self.assertEqual(rows[1][1]["dish_id"], FISH_DISH)
        self.assertEqual((sim.money, sim.earned, sim.shift_earned), (60, 60, 60))

    def test_two_stoves_assign_different_oldest_orders_one_interact_per_tick(self):
        sim = self.make_sim({"player": {"pos": [3.5, 8]}, "stock": {"ca_loc": 2},
                             "customers": [customer("C2", "T2"), customer()]})
        rows = self.steps(sim, 3, [{"tick": 0, "interact": True},
                                   {"tick": 1, "interact": False, "move": [1, 0]},
                                   {"tick": 2, "interact": True}])
        self.assertEqual([(name, data["stove_id"], data["order_id"]) for name, data in rows],
                         [("cook_started", "B1", "C1"), ("cook_started", "B2", "C2")])
        self.assertEqual(sim.stock["ca_loc"], 0)
        self.assertTrue(all(c["order_status"] == "assigned" and not c["reserved"] for c in sim.customers))

    def test_simultaneous_ready_events_follow_stove_id_then_pick_only_one(self):
        sim = self.make_sim({"player": {"pos": [3.5, 8]}, "customers": [
            customer(order_status="assigned", reserved={}),
            customer("C2", "T2", order_status="assigned", reserved={})], "stoves": [
                {"id": "B2", "state": "cooking", "cook_ticks_left": 1, "dish": payload("C2")},
                {"id": "B1", "state": "cooking", "cook_ticks_left": 1, "dish": payload()}]})
        rows = self.steps(sim, inputs=[{"tick": 0, "interact": True}])
        self.assertEqual([(name, data["stove_id"]) for name, data in rows],
                         [("dish_ready", "B1"), ("dish_ready", "B2"), ("dish_picked", "B1")])
        self.assertEqual(sim.hand["order_id"], "C1")
        self.assertEqual((sim.stoves[1]["state"], sim.stoves[1]["ready_ticks"]), ("ready", 0))

    def test_all_six_recipes_cook_at_second_stove_from_tuning(self):
        for dish_id, dish in self.tuning["menu"].items():
            with self.subTest(dish=dish_id):
                sim = self.make_sim({"player": {"pos": [5, 8]}, "stock": dict(dish["recipe"]),
                                     "customers": [customer(dish=dish_id)]})
                rows = self.steps(sim, inputs=[{"tick": 0, "interact": True}])
                self.assertEqual(rows[0][0], "cook_started")
                self.assertEqual(rows[0][1]["stove_id"], "B2")
                self.assertEqual(rows[0][1]["base_price"], dish["price"])
                self.assertEqual(rows[0][1]["items"], [k for k in sorted(dish["recipe"])
                                                       for _ in range(dish["recipe"][k])])
                self.assertEqual(sim.stoves[1]["cook_ticks_left"], round(dish["cook_s"] * self.tuning["tick_hz"]))
                self.assertTrue(all(n == 0 for n in sim.stock.values()))

    def test_customers_use_all_tables_then_reuse_freed_smallest_id_on_schedule(self):
        sim = self.make_sim({"stock": {"ca_loc": 10}, "random_customers": True})
        rows = self.steps(sim, 3720)
        arrived = [data for name, data in rows if name == "customer_arrived"]
        self.assertEqual([c["table_id"] for c in arrived], ["T1", "T2", "T3", "T4", "T1"])
        self.assertEqual([c["order_id"] for c in arrived], ["C1", "C2", "C3", "C4", "C5"])
        self.assertEqual([c["order_tick"] for c in sim.customers], [1020, 1920, 2820, 3720])

    def test_four_occupied_tables_skip_even_when_unreserved_stock_available(self):
        sim = self.make_sim({"stock": {"ca_loc": 5}, "random_customers": True,
                             "customers": [customer(f"C{n}", f"T{n}") for n in range(1, 5)]})
        self.assertEqual(self.steps(sim, 120), [])
        self.assertEqual(len(sim.customers), 4)

    def test_each_table_can_receive_its_matching_order(self):
        for n, table in enumerate(self.tuning["quan"]["tables"], 1):
            with self.subTest(table=table["id"]):
                sim = self.make_sim({"player": {"pos": table["pos"]}, "hand": payload(f"C{n}"),
                                     "customers": [customer(f"C{n}", table["id"], order_status="assigned", reserved={})]})
                rows = self.steps(sim, inputs=[{"tick": 0, "interact": True}])
                self.assertEqual(rows[0][0], "served")
                self.assertEqual(rows[0][1]["table_id"], table["id"])

    def test_patience_stays_at_service_value_while_eating(self):
        sim = self.make_sim({"player": {"pos": [9, 2]}, "hand": payload(),
                             "customers": [customer(order_status="assigned", reserved={}, patience_ticks_left=1801)]})
        self.steps(sim, inputs=[{"tick": 0, "interact": True}])
        self.steps(sim, 20)
        self.assertEqual(sim.customers[0]["patience_ticks_left"], 1800)
        self.assertEqual(sim.customers[0]["eat_ticks_left"], 580)


if __name__ == "__main__":
    unittest.main()

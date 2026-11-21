"""Issue #3 (Hie24): PRD-0 D/E/F.Quán, cả luật và headless hộp đen."""

import copy
import unittest
from pathlib import Path

from chonoi.contract import load_contract
from chonoi.inputs import InputPlayer
from chonoi.runner import Session

from helpers import Workdir, events, frames, read_jsonl, run_headless, snapshots, write_json


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
        block = {"random_customers": False}
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
        self.assertEqual(choices, {FISH_DISH, SALAD, HOT_POT})

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
            self.assertEqual(rows[-1]["money"], 72)
            self.assertEqual(rows[-1]["score"], 372)
            self.assertEqual(rows[-1]["reason"], "tick_limit")
            self.assertEqual(snapshots(rows)[-1]["stock"], {})
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
                                       "customers": [customer(order_status="assigned", reserved={})],
                                       "hand": payload(), "random_customers": False}, 1,
                                    [{"tick": 0, "interact": True}])
            self.assertEqual([r["name"] for r in events(rows)], ["served", "paid", "quan_end"])
            self.assertEqual([s["tick"] for s in snapshots(rows)], [0, 1])
            self.assertEqual(rows[-1]["reason"], "time")
            self.assertEqual(rows[-1]["state"], "finished")
            self.assertEqual(rows[-1]["money"], 72)


if __name__ == "__main__":
    unittest.main()

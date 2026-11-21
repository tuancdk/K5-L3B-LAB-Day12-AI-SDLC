"""Issue #20 — Test Contract v1.2, giữ chỗ/độ tươi/giá và bàn giao thật."""

import copy
import unittest

from chonoi.contract import load_contract
from chonoi.errors import BadInput
from chonoi.ids import IdAllocator
from chonoi.inputs import InputPlayer
from chonoi.rng import Streams
from chonoi.runner import Session
from chonoi.sim.quan import QuanSim
from chonoi.sim.shop import ShopSim

from helpers import Workdir, events, frames, items, read_jsonl, run_headless, snapshots, write_json


FISH = "ca_loc_nuong_trui"
SALAD = "goi_bong_sung"


def item(ident, kind="ca_loc", fresh=100):
    return {"id": ident, "kind": kind, "fresh": fresh}


def customer(ident="C1", table="T1", dish=FISH, **kw):
    return dict(id=ident, table_id=table, dish_id=dish, **kw)


class FreshQuan(unittest.TestCase):
    def setUp(self):
        self.tuning = load_contract()["tuning"]

    def test_empty_default_quan_and_shop_use_item_arrays(self):
        sim = QuanSim(self.tuning, {}, Streams(1), IdAllocator())
        self.assertEqual(sim.snapshot()["stock"], [])
        shop = ShopSim(self.tuning, Streams(1), IdAllocator(), 0, {}, {})
        self.assertEqual(shop.snapshot()["stock"], [])

    def sim(self, stock, customers=(), **kw):
        return QuanSim(self.tuning, dict(stock=stock, customers=list(customers), random_customers=False, **kw),
                       Streams(1), IdAllocator())

    def advance(self, sim, n=1, interact=False):
        player = InputPlayer([{"tick": sim.phase_tick, "interact": interact}])
        result = []
        for _ in range(n):
            result.extend(sim.step(player.advance(sim.phase_tick)))
        return result

    def test_exact_threshold_and_once_only_in_numeric_id_order(self):
        sim = self.sim([item("I10", fresh=30), item("I2", fresh=30), item("I1", fresh=29)])
        rows = self.advance(sim)
        self.assertEqual(rows, [("spoiled", {"item_id": i, "kind": "ca_loc", "location": "stock"})
                                for i in ("I2", "I10")])
        self.assertEqual(self.advance(sim, 50), [])
        self.assertTrue(all(it["fresh"] < 30 for it in sim.stock))

    def test_freshness_30_after_decay_is_still_usable_then_spoils_next_tick(self):
        sim = self.sim([item("I1", fresh=30.25)])
        self.assertEqual(self.advance(sim, 60), [])
        self.assertEqual(sim.stock[0]["fresh"], 30)
        self.assertEqual(self.advance(sim)[0][0], "spoiled")

    def test_decay_includes_reserved_items_and_clamps_at_zero(self):
        sim = self.sim([item("I1", fresh=50), item("I2", fresh=0.001)], [customer()])
        self.advance(sim, 60)
        self.assertEqual(sim.stock, [item("I1", fresh=49.75), item("I2", fresh=0)])
        self.assertEqual(sim.customers[0]["reserved"], ["I1"])

    def test_choose_freshest_then_numeric_id_without_mutating_fixture(self):
        stock = [item("I10", fresh=90), item("I2", fresh=90), item("I1", fresh=80)]
        before = copy.deepcopy(stock)
        sim = self.sim(stock, [customer("C2", "T2"), customer()])
        self.assertEqual([(c["id"], c["reserved"]) for c in sim.customers], [("C1", ["I2"]), ("C2", ["I10"])])
        self.advance(sim)
        self.assertEqual(stock, before)

    def test_explicit_reservation_keeps_requested_id_and_invalid_ids_rejected(self):
        sim = self.sim([item("I1", fresh=90), item("I2", fresh=80)], [customer(reserved=["I2"])])
        self.assertEqual(sim.customers[0]["reserved"], ["I2"])
        for reserved in (["I9"], ["I1", "I1"], {"ca_loc": 1}):
            with self.subTest(reserved=reserved), self.assertRaises(BadInput):
                self.sim([item("I1")], [customer(reserved=reserved)])

    def test_implicit_reservation_rejects_spoiled_or_insufficient_stock(self):
        with self.assertRaises(BadInput):
            self.sim([item("I1", fresh=29.9)], [customer()])

    def test_rereserves_whole_recipe_once_when_part_spoils(self):
        sim = self.sim([item("I1", "bong_sung", 30), item("I2", "bong_sung", 90),
                        item("I3", "bong_sung", 80)],
                       [customer(dish=SALAD, reserved=["I1", "I2"])])
        self.advance(sim)
        self.assertEqual(sim.customers[0]["reserved"], ["I2", "I3"])
        self.assertEqual(sim.customers[0]["order_status"], "reserved")

    def test_failed_rereservation_releases_entire_order_and_keeps_waiting(self):
        sim = self.sim([item("I1", "bong_sung", 30), item("I2", "bong_sung", 90)],
                       [customer(dish=SALAD, reserved=["I1", "I2"])])
        self.advance(sim)
        self.assertEqual((sim.customers[0]["order_status"], sim.customers[0]["reserved"]), ("unfulfillable", []))
        self.assertEqual(sim.customers[0]["state"], "waiting")
        self.assertEqual(len(sim._available()), 1)

    def test_affected_orders_compete_in_order_tick_then_table_order(self):
        sim = self.sim([item("I1", fresh=30), item("I2", fresh=30), item("I3", fresh=80)], [
            customer("C2", "T2", order_tick=1, reserved=["I2"]),
            customer(order_tick=0, reserved=["I1"])])
        self.advance(sim)
        self.assertEqual([(c["id"], c["order_status"], c["reserved"]) for c in sim.customers],
                         [("C1", "reserved", ["I3"]), ("C2", "unfulfillable", [])])

    def test_spoiled_all_emitted_before_ready_and_interact(self):
        dish = {"order_id": "C1", "dish_id": FISH, "base_price": 20}
        sim = self.sim([item("I2", fresh=30), item("I1", fresh=30)],
                       [customer(order_status="assigned", reserved=[])], player={"pos": [2, 8]},
                       stoves=[{"id": "B1", "state": "cooking", "dish": dish, "cook_ticks_left": 1}])
        rows = self.advance(sim, interact=True)
        self.assertEqual([name for name, _ in rows], ["spoiled", "spoiled", "dish_ready", "dish_picked"])

    def test_cook_exact_reserved_items_price_and_sort_order(self):
        stock = [item("I10", "bong_sung", 80), item("I2", "bong_sung", 60), item("I1", "bong_sung", 99)]
        sim = self.sim(stock, [customer(dish=SALAD, reserved=["I10", "I2"])], player={"pos": [2, 8]})
        row = self.advance(sim, interact=True)[0]
        self.assertEqual(row[0], "cook_started")
        self.assertEqual([it["id"] for it in row[1]["items"]], ["I2", "I10"])
        self.assertEqual(row[1]["base_price"], 27)  # floor(40×(70−1/240)/100)
        self.assertEqual([it["id"] for it in sim.stock], ["I1"])
        self.assertEqual(sim.stoves[0]["dish"]["base_price"], 27)

    def test_price_uses_exact_fraction_before_export_and_ready_meal_never_decays(self):
        sim = self.sim([item("I1", fresh=100)], [customer()], player={"pos": [2, 8]})
        self.advance(sim, interact=True)
        self.assertEqual(sim.stoves[0]["dish"]["base_price"], 59)
        self.advance(sim, 400)
        self.assertEqual(sim.stoves[0]["state"], "ready")
        self.assertEqual(sim.stoves[0]["dish"]["base_price"], 59)

    def test_pause_freezes_stock_and_shop_preserves_freshness(self):
        sess = Session("quan", self.tuning, {"stock": [item("I1", fresh=50)], "random_customers": False}, 1)
        inputs = InputPlayer([{"tick": 0, "pause": True}, {"tick": 1, "pause": False}, {"tick": 4, "pause": True}])
        for tick in range(4):
            sess.step(inputs.advance(tick))
        self.assertEqual(sess.sim.stock[0]["fresh"], 50)
        sess.step(inputs.advance(4))
        self.assertAlmostEqual(sess.sim.stock[0]["fresh"], 50 - 0.25/60)
        shop = ShopSim(self.tuning, Streams(1), IdAllocator(), 0, {}, {"day": 1, "active_upgrades": {}})
        shop.stock = copy.deepcopy(sess.sim.stock)
        before = copy.deepcopy(shop.stock)
        for _ in range(10):
            shop.step(InputPlayer([]).advance(0))
        self.assertEqual(shop.items_stock, before)


class FreshQuanCLI(unittest.TestCase):
    def run_quan(self, w, stock, customers=(), inputs=(), ticks=1, inventory=False):
        sc = {"quan": {"customers": list(customers), "player": {"pos": [2, 8]}, "random_customers": False}}
        args = []
        if inventory:
            inv = write_json(w.path("stock.json"), {"items": stock})
            args = ["--inventory", inv]
        else:
            sc["quan"]["stock"] = stock
        scp = write_json(w.path("s.json"), sc)
        ip = write_json(w.path("i.json"), frames(*inputs))
        out = w.path("out.jsonl")
        code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", str(ticks), "--scenario", scp,
                                 "--inputs", ip, "--snapshot-every", "1", "--out", out, *args)
        self.assertEqual(code, 0, err)
        return read_jsonl(out)

    def test_inventory_preserves_explicit_reserved_ids_and_fresh_price(self):
        with Workdir() as w:
            rows = self.run_quan(w, [item("I1", fresh=90), item("I2", fresh=50)],
                                 [customer(reserved=["I2"])], [{"tick": 0, "interact": True}], inventory=True)
        self.assertEqual(snapshots(rows)[0]["customers"][0]["reserved"], ["I2"])
        cooked = events(rows, "cook_started")[0]["data"]
        self.assertEqual(cooked["items"][0]["id"], "I2")
        self.assertEqual(cooked["base_price"], 29)

    def test_boundary_state_survives_jsonl_before_rounding(self):
        with Workdir() as w:
            rows = self.run_quan(w, [item("I1", fresh=30)], ticks=2)
        self.assertEqual([(r["tick"], r["data"]["item_id"]) for r in events(rows, "spoiled")], [(1, "I1")])
        self.assertLess(snapshots(rows)[1]["stock"][0]["fresh"], 30)

    def test_inventory_float_restores_exact_units_at_threshold(self):
        with Workdir() as w:
            rows = self.run_quan(w, [item("I1", fresh=30 + 1/240)], ticks=2, inventory=True)
        self.assertEqual(snapshots(rows)[1]["stock"][0]["fresh"], 30)
        self.assertEqual([r["tick"] for r in events(rows, "spoiled")], [2])

    def test_snapshot_stock_uses_numeric_id_order_after_native_adapter(self):
        with Workdir() as w:
            rows = self.run_quan(w, [item("I10"), item("I2"), item("I1")], inventory=True)
        self.assertTrue(all([it["id"] for it in row["stock"]] == ["I1", "I2", "I10"]
                            for row in snapshots(rows)))

    def test_day_handover_near_threshold_has_no_extra_decay_or_rounding(self):
        with Workdir() as w:
            sc = write_json(w.path("s.json"), {"gather": {"hold": [item("I8", fresh=30.0125)],
                                  "random_fish": False, "monsters": []}, "quan": {"random_customers": False}})
            ip = write_json(w.path("i.json"), frames({"tick": 0, "interact": True}))
            out = w.path("out.jsonl")
            code, err = run_headless("--mode", "day", "--seed", "1", "--ticks", "3", "--scenario", sc,
                                     "--inputs", ip, "--snapshot-every", "1", "--out", out)
            self.assertEqual(code, 0, err)
            rows = read_jsonl(out)
        stock = {r["tick"]: r["stock"] for r in snapshots(rows) if r["phase"] == "quan"}
        self.assertEqual(stock[1], [item("I8", fresh=30 + 1/240)])
        self.assertEqual(stock[2], [item("I8", fresh=30)])
        self.assertEqual([(r["tick"], r["data"]["location"]) for r in events(rows, "spoiled")], [(3, "stock")])


if __name__ == "__main__":
    unittest.main()

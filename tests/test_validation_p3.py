import json
import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from chonoi.contract import load_contract
from chonoi.errors import BadInput
from chonoi.inventory import read_inventory_v12
from chonoi.scenario import load_scenario, validate_quan

from helpers import ROOT, Workdir, read_jsonl, run_headless, write_json


FIXTURES = Path(__file__).with_name("fixtures") / "validation-p3"
FRESHNESS = {"initial": 100, "gather_decay_per_s": 0.5, "quan_decay_per_s": 0.25, "spoiled_below": 30}
STOCK = [
    {"id": "I1", "kind": "ca_loc", "fresh": 30},
    {"id": "I2", "kind": "ca_keo", "fresh": 100},
    {"id": "I3", "kind": "ca_loc", "fresh": 29.999},
    {"id": "I4", "kind": "bong_sung", "fresh": 50},
    {"id": "I5", "kind": "ca_loc", "fresh": 0},
]


def cases(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class ValidationP3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = Path(cls.enterClassContext(TemporaryDirectory()))
        shutil.copytree(Path(ROOT) / "chonoi", cls.scratch / "chonoi",
                        ignore=shutil.ignore_patterns("__pycache__"))
        cls.contract = json.loads((Path(ROOT) / "game.contract.json").read_text(encoding="utf-8"))
        cls.contract["contract_version"] = "1.2"
        cls.contract_path = cls.scratch / "game.contract.json"

    def setUp(self):
        self.write_contract(FRESHNESS)

    def write_contract(self, freshness):
        contract = dict(self.contract, tuning=dict(self.contract["tuning"]))
        contract["tuning"].pop("freshness", None)
        if freshness is not None:
            contract["tuning"]["freshness"] = freshness
        write_json(self.contract_path, contract)

    def assert_rejected(self, workdir, mode, *args, error_contains, cwd=ROOT):
        out = Path(workdir.path("out.jsonl"))
        inventory_out = Path(workdir.path("inventory-out.json"))
        if mode == "gather":
            args += ("--inventory-out", str(inventory_out))
        code, error = run_headless("--mode", mode, "--seed", "1", "--ticks", "1",
                                   "--out", str(out), *args, cwd=cwd)
        self.assertEqual(code, 2, error)
        self.assertIn(error_contains, error)
        self.assertFalse(out.exists())
        self.assertFalse(inventory_out.exists())

    def test_invalid_file_inventory(self):
        inventory_cases = cases("inventory.json")
        for name, inventory in inventory_cases.items():
            with self.subTest(name=name), Workdir() as workdir:
                path = write_json(workdir.path("inventory.json"), inventory)
                self.assert_rejected(workdir, "quan", "--inventory", path, error_contains="items")
        with Workdir() as workdir:
            self.assert_rejected(workdir, "quan", "--inventory", str(FIXTURES / "invalid-nan.json"),
                                 error_contains="fresh")
            path = write_json(workdir.path("inventory.json"), inventory_cases["non_string_kind"])
            with self.assertRaisesRegex(BadInput, "kind"):
                read_inventory_v12(path, {"ca_loc"})

    def test_invalid_scenario_items(self):
        for name, (field, items) in cases("scenarios.json").items():
            with self.subTest(name=name), Workdir() as workdir:
                mode = "gather" if field == "hold" else "quan"
                path = write_json(workdir.path("scenario.json"), {mode: {field: items}})
                self.assert_rejected(workdir, mode, "--scenario", path, error_contains=field)

    def test_invalid_reservations_and_dish_payloads(self):
        for name, block in cases("reservations.json").items():
            with self.subTest(name=name), Workdir() as workdir:
                path = write_json(workdir.path("scenario.json"), {"quan": dict(block, stock=STOCK)})
                message = "base_price" if name.startswith(("hand_", "stove_")) else "reserved"
                self.assert_rejected(workdir, "quan", "--scenario", path, error_contains=message)

    def test_reservation_checks_loaded_inventory(self):
        block = cases("reservations.json")["spoiled_id"]
        with Workdir() as workdir:
            sc = write_json(workdir.path("scenario.json"), {"quan": block})
            inventory = write_json(workdir.path("inventory.json"), {"items": STOCK})
            self.assert_rejected(workdir, "quan", "--scenario", sc, "--inventory", inventory,
                                 error_contains="reserved")

    def test_invalid_freshness_contract(self):
        for name, freshness in cases("freshness.json").items():
            with self.subTest(name=name), Workdir() as workdir:
                self.write_contract(freshness)
                self.assert_rejected(workdir, "gather", error_contains="freshness", cwd=self.scratch)

    def test_valid_items_keep_ids_freshness_and_order(self):
        tuning = load_contract(self.contract_path)["tuning"]
        with Workdir() as workdir:
            inventory = write_json(workdir.path("inventory.json"), {"items": STOCK})
            self.assertEqual(read_inventory_v12(inventory), STOCK)
            gather = {"hold": list(reversed(STOCK))}
            scenario = write_json(workdir.path("scenario.json"), {"gather": gather})
            self.assertEqual(load_scenario(scenario, "gather", tuning), gather)
            # Freshness exactly at the cutoff can be reserved. Older stock can remain unreserved.
            quan = {"stock": STOCK, "customers": [
                {"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "reserved": ["I1"]},
                {"id": "C2", "table_id": "T2", "dish_id": "ca_loc_nuong_trui"},
            ]}
            scenario = write_json(workdir.path("scenario.json"), {"quan": quan})
            self.assertEqual(load_scenario(scenario, "quan", tuning), quan)

    def test_valid_gather_fixture_at_tick_zero(self):
        with Workdir() as workdir:
            hold = list(reversed(STOCK))
            path = write_json(workdir.path("scenario.json"), {"gather": {"hold": hold}})
            out = workdir.path("out.jsonl")
            code, error = run_headless("--mode", "gather", "--seed", "1", "--ticks", "0",
                                       "--out", out, "--scenario", path)
            self.assertEqual(code, 0, error)
            self.assertEqual(read_jsonl(out)[0]["hold"], hold)

    def test_day_defers_reference_checks_until_real_stock_arrives(self):
        tuning = load_contract(self.contract_path)["tuning"]
        quan = {"customers": [
            {"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "reserved": ["I1"]},
        ]}
        with Workdir() as workdir:
            path = write_json(workdir.path("day.json"), {"quan": quan})
            self.assertEqual(load_scenario(path, "day", tuning)["quan"], quan)
        validate_quan(quan, tuning, STOCK)
        with self.assertRaisesRegex(BadInput, "reserved"):
            validate_quan(quan, tuning, [])

    def test_day_rejects_reservation_that_spoils_before_handover(self):
        customer = {"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "reserved": ["I1"]}
        scenario = {"gather": {"time_left_ticks": 1, "hold": [STOCK[0]]},
                    "quan": {"customers": [customer]}}
        with Workdir() as workdir:
            path = write_json(workdir.path("day.json"), scenario)
            self.assert_rejected(workdir, "day", "--scenario", path, error_contains="đã ươn")

    def test_implicit_reservations_use_order_priority_and_exclude_spoiled_items(self):
        customers = [
            {"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "order_tick": 1},
            {"id": "C2", "table_id": "T2", "dish_id": "ca_loc_nuong_trui", "order_tick": 0},
        ]
        with Workdir() as workdir:
            path = write_json(workdir.path("quan.json"), {"quan": {"stock": STOCK, "customers": customers}})
            out = workdir.path("out.jsonl")
            code, error = run_headless("--mode", "quan", "--seed", "1", "--ticks", "0",
                                       "--out", out, "--scenario", path)
            self.assertEqual(code, 0, error)
            orders = {c["id"]: c["order_status"] for c in read_jsonl(out)[0]["customers"]}
            self.assertEqual(orders, {"C1": "unfulfillable", "C2": "reserved"})

    def test_cooked_dish_keeps_locked_base_price(self):
        tuning = load_contract(self.contract_path)["tuning"]
        customer = {"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui",
                    "order_status": "assigned", "reserved": []}
        payload = {"order_id": "C1", "dish_id": "ca_loc_nuong_trui", "base_price": 18}
        for fixture in ({"hand": payload}, {"stoves": [{"id": "B1", "state": "ready", "dish": payload}]}):
            with self.subTest(fixture=fixture):
                validate_quan(dict(fixture, customers=[customer]), tuning, [])

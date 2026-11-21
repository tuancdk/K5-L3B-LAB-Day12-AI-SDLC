import json
import shutil
import unittest
from pathlib import Path

from helpers import ROOT, Workdir, read_jsonl, run_headless, write_json


FIXTURES = Path(__file__).with_name("fixtures") / "validation"
CONTRACT = Path(ROOT) / "game.contract.json"
DISH = "ca_loc_nuong_trui"


class Validation(unittest.TestCase):
    def assert_rejected(self, mode, *args, cwd=ROOT):
        with Workdir() as workdir:
            out = Path(workdir.path("out.jsonl"))
            paths = [out]
            if mode == "gather":
                inventory_out = Path(workdir.path("inventory.json"))
                args += ("--inventory-out", str(inventory_out))
                paths.append(inventory_out)
            code, error = run_headless("--mode", mode, "--seed", "1", "--ticks", "10",
                                       "--out", str(out), *args, cwd=cwd)
            self.assertEqual(code, 2, error)
            self.assertIn("đầu vào sai:", error)
            for path in paths:
                self.assertFalse(path.exists(), path)

    def test_rejects_invalid_quan_scenarios(self):
        for fixture in sorted((FIXTURES / "quan").glob("*.json")):
            with self.subTest(fixture=fixture.stem):
                self.assert_rejected("quan", "--scenario", str(fixture))

    def test_rejects_invalid_zero_oxy_ticks(self):
        for fixture in sorted((FIXTURES / "gather").glob("*.json")):
            with self.subTest(fixture=fixture.stem):
                self.assert_rejected("gather", "--scenario", str(fixture))

    def isolated_checkout(self, workdir):
        scratch = Path(workdir.path(""))
        shutil.copytree(Path(ROOT) / "chonoi", scratch / "chonoi",
                        ignore=shutil.ignore_patterns("__pycache__"))
        return scratch

    def test_rejects_invalid_contract_before_writing_either_output(self):
        cases = json.loads((FIXTURES / "contract.json").read_text(encoding="utf-8"))
        original = CONTRACT.read_text(encoding="utf-8")
        with Workdir() as workdir:
            scratch = self.isolated_checkout(workdir)
            scenario = write_json(scratch / "scenario.json", {"gather": {"time_left_ticks": 1}})
            for name, (field, value) in cases.items():
                with self.subTest(fixture=name):
                    contract = json.loads(original)
                    keys = field.split(".")
                    block = contract
                    for key in keys[:-1]:
                        block = block[key]
                    block[keys[-1]] = value
                    write_json(scratch / CONTRACT.name, contract)
                    self.assert_rejected("gather", "--scenario", scenario, cwd=scratch)

    def test_reservations_are_totalled_across_customers(self):
        fixture = FIXTURES / "reserved_total_exceeds_stock.json"
        with Workdir() as workdir:
            scratch = self.isolated_checkout(workdir)
            contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
            contract["tuning"]["quan"]["tables"].append({"id": "T2", "pos": [9, 3]})
            write_json(scratch / CONTRACT.name, contract)
            self.assert_rejected("quan", "--scenario", str(fixture), cwd=scratch)

    def test_stock_validation_uses_inventory_file(self):
        fixture = FIXTURES / "quan" / "reserved_exceeds_stock.json"
        with Workdir() as workdir:
            inventory = workdir.path("stock.json")
            write_json(inventory, {"items": {"ca_linh": 2, "bong_dien_dien": 1}})
            self.assert_rejected("quan", "--scenario", str(fixture), "--inventory", inventory)
            stock = {"ca_linh": 3, "bong_dien_dien": 1}
            write_json(inventory, {"items": stock})
            out = workdir.path("out.jsonl")
            code, error = run_headless("--mode", "quan", "--seed", "1", "--ticks", "10", "--out", out,
                                       "--scenario", str(fixture), "--inventory", inventory)
            self.assertEqual(code, 0, error)
            self.assertEqual(read_jsonl(out)[0]["stock"], stock)

    def test_accepts_consistent_quan_states_and_optional_defaults(self):
        customer = {"id": "C1", "table_id": "T1", "dish_id": DISH}
        meal = {"order_id": "C1", "dish_id": DISH, "base_price": 60}
        assigned = dict(customer, order_status="assigned")
        cases = {
            "implicit reservation": {"customers": [customer], "stock": {"ca_loc": 1}},
            "same stock as reservation": {"customers": [dict(customer, reserved={"ca_loc": 1})],
                                          "stock": {"ca_loc": 1}},
            "ready": {"customers": [assigned], "stoves": [{"id": "B1", "state": "ready", "dish": meal}]},
            "cooking": {"customers": [assigned], "stoves": [{"id": "B1", "state": "cooking", "dish": meal,
                                                             "cook_ticks_left": 1}]},
            "hand": {"customers": [assigned], "hand": meal},
            "null hand": {"hand": None},
            "unfulfillable": {"customers": [dict(customer, order_status="unfulfillable")]},
            "eating": {"customers": [dict(customer, state="eating", order_status="served", eat_ticks_left=1,
                                          base_price=60, tip=0)]},
        }
        for name, block in cases.items():
            with self.subTest(fixture=name), Workdir() as workdir:
                fixture = write_json(workdir.path("scenario.json"), {"quan": block})
                code, error = run_headless("--mode", "quan", "--seed", "1", "--ticks", "10",
                                           "--out", workdir.path("out.jsonl"), "--scenario", fixture)
                self.assertEqual(code, 0, error)

    def test_accepts_zero_oxy_ticks_at_upper_bound_underwater(self):
        block = {"player": {"pos": [2, 1], "oxygen_ticks": 0, "zero_oxy_ticks": 59}}
        with Workdir() as workdir:
            fixture = write_json(workdir.path("scenario.json"), {"gather": block})
            out = workdir.path("out.jsonl")
            code, error = run_headless("--mode", "gather", "--seed", "1", "--ticks", "0",
                                       "--out", out, "--scenario", fixture)
            self.assertEqual(code, 0, error)
            self.assertEqual(read_jsonl(out)[0]["player"]["zero_oxy_ticks"], 59)


if __name__ == "__main__":
    unittest.main()

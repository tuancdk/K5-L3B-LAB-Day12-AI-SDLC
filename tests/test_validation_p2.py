import json
import shutil
import unittest
from pathlib import Path

from helpers import ROOT, Workdir, read_jsonl, run_headless, write_json


FIXTURES = Path(__file__).with_name("fixtures") / "validation-p2"


def fixture_cases(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class ValidationP2(unittest.TestCase):
    def run_case(self, workdir, mode, *args, cwd=ROOT, ticks=2):
        out = workdir.path("out.jsonl")
        code, error = run_headless("--mode", mode, "--seed", "1", "--ticks", str(ticks), "--out", out, *args, cwd=cwd)
        return code, error, Path(out)

    def assert_invalid(self, workdir, mode, *args, cwd=ROOT):
        code, error, out = self.run_case(workdir, mode, *args, cwd=cwd)
        self.assertEqual(code, 2, error)
        self.assertFalse(out.exists(), error)
        self.assertFalse(Path(workdir.path("out-inventory.json")).exists(), error)

    def test_invalid_day_fixtures(self):
        for name, scenario in fixture_cases("scenarios.json").items():
            with self.subTest(name=name), Workdir() as workdir:
                path = write_json(workdir.path("scenario.json"), scenario)
                self.assert_invalid(workdir, "day", "--scenario", path)

    def test_invalid_gather_fixtures(self):
        for name, fixture in fixture_cases("gather.json").items():
            with self.subTest(name=name), Workdir() as workdir:
                path = write_json(workdir.path("scenario.json"), {"gather": dict(fixture, time_left_ticks=1)})
                self.assert_invalid(workdir, "gather", "--scenario", path,
                                    "--inventory-out", workdir.path("out-inventory.json"))

    def test_invalid_contract_fixtures(self):
        original = (Path(ROOT) / "game.contract.json").read_text(encoding="utf-8")
        with Workdir() as workdir:
            scratch = Path(workdir.path("copy"))
            shutil.copytree(Path(ROOT) / "chonoi", scratch / "chonoi",
                            ignore=shutil.ignore_patterns("__pycache__"))
            for name, (path, value) in fixture_cases("contract.json").items():
                with self.subTest(name=name):
                    data = json.loads(original)
                    target = data
                    keys = path.split(".")
                    for key in keys[:-1]:
                        target = target[int(key) if isinstance(target, list) else key]
                    target[int(keys[-1]) if isinstance(target, list) else keys[-1]] = value
                    write_json(scratch / "game.contract.json", data)
                    self.assert_invalid(workdir, "gather", "--inventory-out", workdir.path("out-inventory.json"),
                                        cwd=scratch)

    def test_cli_rejects_invalid_days_and_inventory_flags(self):
        for mode, args in [
            ("day", ("--days", "0")), ("day", ("--days", "6")), ("day", ("--days", "1.5")),
            ("quan", ("--days", "1")), ("gather", ("--days", "1")),
        ]:
            with self.subTest(mode=mode, args=args), Workdir() as workdir:
                self.assert_invalid(workdir, mode, *args)
        with Workdir() as workdir:
            kho = write_json(workdir.path("in.json"), {"items": {}})
            for mode in ("gather", "day"):
                self.assert_invalid(workdir, mode, "--inventory", kho)
            for mode in ("quan", "day"):
                self.assert_invalid(workdir, mode, "--inventory-out", workdir.path("out-inventory.json"))

    def test_valid_day_override_with_stock_from_gather(self):
        scenario = {
            "day": {"money": 2, "upgrades": {"hp": 1}, "day_plan": [
                {"day": 1, "dishes": {"ca_keo_nuong": 1}},
            ]},
            "gather": {"time_left_ticks": 1, "player": {"pos": [20, 22], "hp": 4},
                       "fish": [{"id": "F1", "kind": "ca_keo", "pos": [20, 22]}],
                       "monsters": [{"id": "M1", "kind": "ca_sau", "pos": [45, 15],
                                     "waypoints": [[45, 15], [46, 15]]}]},
            "quan": {"customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_keo_nuong"}]},
        }
        with Workdir() as workdir:
            path = write_json(workdir.path("scenario.json"), scenario)
            inputs = write_json(workdir.path("inputs.json"), {"frames": [{"tick": 0, "catch": True}]})
            code, error, out = self.run_case(workdir, "day", "--scenario", path, "--days", "5",
                                             "--snapshot-every", "1", "--inputs", inputs)
            self.assertEqual(code, 0, error)
            rows = read_jsonl(out)
            plan = next(row["data"] for row in rows if row.get("name") == "day_plan")
            self.assertEqual(plan["ingredients"], {"ca_keo": 2})
            snapshot = next(row for row in rows if row["type"] == "snapshot" and row["phase"] == "quan")
            self.assertEqual(snapshot["stock"], {"ca_keo": 2})
            self.assertEqual(snapshot["customers"][0]["reserved"], {"ca_keo": 2})

    def test_transition_failure_preserves_existing_out(self):
        scenario = fixture_cases("later_day.json")
        with Workdir() as workdir:
            out = Path(workdir.path("out.jsonl"))
            out.write_bytes(b"existing\n")
            path = write_json(workdir.path("scenario.json"), scenario)
            inputs = write_json(workdir.path("inputs.json"), {"frames": [{"tick": 2, "shop_done": True}]})
            code, error, _ = self.run_case(workdir, "day", "--scenario", path, "--inputs", inputs,
                                           "--days", "2", ticks=4)
            self.assertEqual(code, 2, error)
            self.assertIn("dish_id", error)
            self.assertEqual(out.read_bytes(), b"existing\n")

    def test_file_inventory_accepts_both_new_ingredients(self):
        with Workdir() as workdir:
            stock = {"ca_keo": 2, "keo_neo": 1}
            kho = write_json(workdir.path("in.json"), {"items": stock})
            code, error, out = self.run_case(workdir, "quan", "--inventory", kho)
            self.assertEqual(code, 0, error)
            self.assertEqual(read_jsonl(out)[0]["stock"], stock)

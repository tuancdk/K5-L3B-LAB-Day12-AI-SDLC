"""Contract v1.1 — số chuẩn TICKET-02 mục 1-2 (#12). Đọc game.contract.json, không hard-code ngoài bảng PRD."""

import json
import os
import unittest

from helpers import Workdir, read_jsonl, run_headless, snapshots

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def contract():
    with open(os.path.join(ROOT, "game.contract.json"), encoding="utf-8") as f:
        return json.load(f)


class ContractV11(unittest.TestCase):
    def setUp(self):
        self.c = contract()
        self.t = self.c["tuning"]

    def test_version_and_extensions(self):
        self.assertIn(self.c["contract_version"], ("1.1", "1.2", "1.3"))  # v1.2 (P3) giữ mọi số chuẩn v1.1
        self.assertIsInstance(self.c["extensions"], list)

    def test_quan_two_stoves_four_tables_six_dishes(self):
        q = self.t["quan"]
        self.assertEqual([s["id"] for s in q["stoves"]], ["B1", "B2"])
        self.assertEqual([t["id"] for t in q["tables"]], ["T1", "T2", "T3", "T4"])
        self.assertEqual(len(self.t["menu"]), 6)

    def test_day_plan_ingredients_are_recipe_sums(self):
        plan = self.t["day_plan"]
        self.assertEqual([d["day"] for d in plan], [1, 2, 3, 4, 5])
        for d in plan:
            want = {}
            for dish, n in d["dishes"].items():
                for k, v in self.t["menu"][dish]["recipe"].items():
                    want[k] = want.get(k, 0) + v * n
            self.assertEqual(d["ingredients"], want, d["day"])

    def test_shop_upgrades_by_level(self):
        s = self.t["shop"]
        self.assertEqual(s["max_ticks"], 600)
        for key, field in (("oxygen", "oxygen_max_s"), ("hp", "hp_max")):
            levels = s["upgrades"][key]
            self.assertEqual([u["level"] for u in levels], [1, 2])
            self.assertTrue(all(u["price"] > 0 and field in u for u in levels))

    def test_monsters_and_species(self):
        m = self.t["gather"]["monsters"]
        self.assertEqual(set(m["species"]["ca_sau"]), {"patrol_speed", "chase_speed", "detect_radius", "exit_radius",
                                                         "depths", "hit_radius", "recoil_ticks", "recoil_dist"})
        self.assertEqual([(s["id"], s["from_day"]) for s in m["spawns"]], [("M1", 1), ("M2", 3)])

    def test_gather_starts_with_fish_initial_schools_on_distinct_spawn_points(self):
        g = self.t["gather"]
        with Workdir() as w:
            code, err = run_headless("--mode", "gather", "--seed", "3", "--ticks", "0", "--out", w.path("g.jsonl"))
            self.assertEqual(code, 0, err)
            fish = snapshots(read_jsonl(w.path("g.jsonl")))[0]["fish"]
        self.assertEqual(len(fish), g["fish_initial"])
        self.assertEqual(len({tuple(f["pos"]) for f in fish}), len(fish))
        for f in fish:
            self.assertIn(f["pos"][0], g["fish_spawn_x"])
            self.assertIn(f["pos"][1], g["fish_spawn_depths"][f["kind"]])


if __name__ == "__main__":
    unittest.main()

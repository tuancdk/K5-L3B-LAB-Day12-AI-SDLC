import math
import json
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from chonoi.bench import BenchGame, BenchServer, summarize
from chonoi.contract import load_contract


class BenchMath(unittest.TestCase):
    def test_exact_five_fields_and_real_duration(self):
        result = summarize([10, 10, 20, 40], 1234)
        self.assertEqual(set(result), {"avg_fps", "p1_low_fps", "frames", "measured_s", "load_ms"})
        self.assertEqual(result["frames"], 4)
        self.assertAlmostEqual(result["measured_s"], 0.08)
        self.assertAlmostEqual(result["avg_fps"], 50)
        self.assertAlmostEqual(result["p1_low_fps"], 25)
        self.assertEqual(result["load_ms"], 1234)

    def test_one_percent_low_uses_ceil_and_mean_of_slowest(self):
        result = summarize([10] * 99 + [40, 60], 0)
        self.assertEqual(result["frames"], 101)
        self.assertEqual(result["p1_low_fps"], 20)

    def test_bad_measurements_are_rejected(self):
        for frame_ms, load in (([], 0), ([0], 0), ([-1], 0), ([math.nan], 0), ([True], 0),
                               ([10], -1), ([10], math.inf), ([10], True)):
            with self.subTest(frame_ms=frame_ms, load=load), self.assertRaises(ValueError):
                summarize(frame_ms, load)


class BenchHTTP(unittest.TestCase):
    def post_result(self, body):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "bench.json"
            game = BenchGame("gather", load_contract()["tuning"], {}, 42)
            server = BenchServer(game, 0.03, out, started_epoch_ms=123)
            server.start()
            try:
                with urlopen(server.url + "bench-config", timeout=5) as response:
                    config = json.load(response)
                self.assertEqual((config["warmup_s"], config["width"], config["height"]), (3, 1280, 720))
                request = Request(server.url + "bench-result", json.dumps(body).encode(), method="POST")
                try:
                    with urlopen(request, timeout=5) as response:
                        status = response.status
                except HTTPError as error:
                    status = error.code
                    error.close()
                self.assertTrue(server.finished.wait(2))
                return status, json.loads(out.read_text()) if out.exists() else None
            finally:
                server.stop()

    def test_http_writes_only_complete_five_field_summary(self):
        # Dữ liệu tổng hợp cho unit test HTTP; không dùng làm bằng chứng hiệu năng.
        status, result = self.post_result({"width": 1280, "height": 720, "frame_ms": [10, 20], "load_ms": 50})
        self.assertEqual(status, 200)
        self.assertEqual(result, summarize([10, 20], 50))

    def test_incomplete_or_wrong_viewport_never_writes_artifact(self):
        for body in ([], {"width": 800, "height": 600, "frame_ms": [30], "load_ms": 0},
                     {"width": 1280, "height": 720, "frame_ms": [10], "load_ms": 0}):
            with self.subTest(body=body):
                self.assertEqual(self.post_result(body), (400, None))

    def test_bench_ignores_player_input_and_restart(self):
        game = BenchGame("gather", load_contract()["tuning"], {}, 42)
        start = game.session
        before = game.session.snapshot()["player"]["pos"][:]
        game.set_input({"move": [1, 1], "interact": True})
        game.restart()
        for _ in range(60):
            game._tick_once()
        self.assertIs(game.session, start)
        self.assertEqual(game.session.snapshot()["player"]["pos"], before)


if __name__ == "__main__":
    unittest.main()

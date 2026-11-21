"""Benchmark render thật: python3 -m chonoi.bench --seed 42 --duration 30 --out bench.json.

--no-open dành cho browser automation: mở URL in ra với viewport 1280×720.
Không thay live.py hoặc dùng tốc độ headless để suy ra FPS.
"""

import time

STARTED_EPOCH_MS = time.time() * 1000

import argparse
import json
import math
import os
import sys
import threading
import webbrowser
from pathlib import Path

from .contract import load_contract
from .live import LiveGame, LiveServer


def summarize(frame_ms, load_ms):
    """Frame trong khoảng đo, sau warmup; 1% low dùng trung bình các frame chậm nhất."""
    if not isinstance(frame_ms, list) or not frame_ms:
        raise ValueError("không có frame trong khoảng đo")
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or x <= 0
           for x in frame_ms):
        raise ValueError("frame_ms phải gồm các thời gian hữu hạn > 0")
    if isinstance(load_ms, bool) or not isinstance(load_ms, (int, float)) or not math.isfinite(load_ms) or load_ms < 0:
        raise ValueError("load_ms phải hữu hạn và không âm")
    frames = len(frame_ms)
    measured_s = math.fsum(frame_ms) / 1000
    slow_count = max(1, math.ceil(frames * 0.01))
    slow = sorted(frame_ms, reverse=True)[:slow_count]
    return {"avg_fps": frames / measured_s, "p1_low_fps": 1000 * slow_count / math.fsum(slow),
            "frames": frames, "measured_s": measured_s, "load_ms": load_ms}


class BenchGame(LiveGame):
    def set_input(self, body):
        pass  # cảnh chuẩn: đứng yên ở bến, mọi input người dùng bị bỏ qua

    def restart(self):
        pass


class BenchServer(LiveServer):
    def __init__(self, game, duration, out, *, port=0, started_epoch_ms=STARTED_EPOCH_MS):
        super().__init__(game, port=port)
        self.duration = duration
        self.out = Path(out)
        self.finished = threading.Event()
        self.result = None
        self.error = None
        self.config = {"duration": duration, "warmup_s": 3, "width": 1280, "height": 720,
                       "started_epoch_ms": started_epoch_ms}
        owner = self
        base = self.httpd.RequestHandlerClass

        class Handler(base):
            def do_GET(self):
                if self.path.split("?", 1)[0] == "/bench-config":
                    self._send(200, json.dumps(owner.config).encode())
                else:
                    super().do_GET()

            def do_POST(self):
                if self.path.split("?", 1)[0] != "/bench-result":
                    return super().do_POST()
                try:
                    size = int(self.headers.get("Content-Length", "0"))
                    if not 0 < size <= 2_000_000 or owner.finished.is_set():
                        raise ValueError("body sai hoặc bench đã xong")
                    body = json.loads(self.rfile.read(size))
                    if not isinstance(body, dict):
                        raise ValueError("body phải là object")
                    if body.get("error"):
                        raise ValueError(body["error"])
                    if body.get("width") != 1280 or body.get("height") != 720:
                        raise ValueError("benchmark cần viewport 1280×720")
                    result = summarize(body["frame_ms"], body["load_ms"])
                    if result["measured_s"] < duration:
                        raise ValueError("khoảng đo ngắn hơn duration")
                    # Chỉ công bố artifact khi đủ dữ liệu thật và ghi xong file.
                    owner.out.parent.mkdir(parents=True, exist_ok=True)
                    temp = owner.out.with_name(owner.out.name + ".tmp")
                    temp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    os.replace(temp, owner.out)
                    owner.result = result
                    self._send(200, b'{"ok":true}')
                except (KeyError, TypeError, ValueError, OSError) as exc:
                    owner.error = str(exc)
                    self._send(400, json.dumps({"error": str(exc)}).encode())
                finally:
                    owner.finished.set()

        self.httpd.RequestHandlerClass = Handler


def main(argv=None):
    parser = argparse.ArgumentParser(prog="chonoi.bench")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--duration", type=float, required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args(argv)
    if not math.isfinite(args.duration) or args.duration <= 0:
        parser.error("duration phải hữu hạn và > 0")
    server = BenchServer(BenchGame("gather", load_contract()["tuning"], {}, args.seed), args.duration, args.out)
    server.start()
    url = server.url + "?bench=1"
    print(f"BENCH_URL={url}", flush=True)
    if not args.no_open:
        webbrowser.open(url, new=1)
    try:
        if not server.finished.wait(args.duration + 63):
            print("Không nhận được dữ liệu render; mở URL với viewport 1280×720.", file=sys.stderr)
            return 1
        if server.error:
            print(server.error, file=sys.stderr)
            return 1
        print(json.dumps(server.result), flush=True)
        return 0
    finally:
        server.stop()


if __name__ == "__main__":
    sys.exit(main())

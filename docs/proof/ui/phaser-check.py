"""Kiểm lớp cảnh Phaser 3 trên Chrome headless (1280×720).

1. Server quan + gather thật: Phaser khởi động (không rơi về Canvas dự phòng), FPS ≥ 30.
2. Kích hoạt event giả trên client (served, paid, dish_ready, customer_left, fish_caught, monster_hit)
   → có particle/tween đang chạy; chụp ảnh giữa hiệu ứng.
3. Chặn /vendor/phaser.min.js → trang tự dùng Canvas 2D, vẫn vẽ frame, không lỗi JavaScript.

    python -X utf8 -B docs/proof/ui/phaser-check.py --out docs/proof/ui/phase-2
"""
import argparse
import base64
import importlib.util
import json
from contextlib import ExitStack
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import time

from websockets.sync.client import connect

PROOF = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("browser_check", PROOF / "browser-check.py")
bc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bc)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("chrome", nargs="?", default=r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    parser.add_argument("--out", type=Path, default=PROOF / "phase-2")
    opts = parser.parse_args()
    opts.out.mkdir(parents=True, exist_ok=True)
    with ExitStack() as stack:
        profile = Path(stack.enter_context(TemporaryDirectory(prefix="chonoi-phaser-", ignore_cleanup_errors=True)))
        bc.start(stack, [opts.chrome, "--headless", "--disable-extensions", "--no-first-run",
                         "--disable-background-networking", "--remote-debugging-port=0",
                         f"--user-data-dir={profile}", "about:blank"])
        port = bc.until(lambda: (profile / "DevToolsActivePort").read_text().splitlines())[0]
        target = bc.until(lambda: bc.read(f"http://127.0.0.1:{port}/json/list"))[0]
        ws = stack.enter_context(connect(target["webSocketDebuggerUrl"], max_size=12_000_000))
        message_id = 0

        def cdp(method, **params):
            nonlocal message_id
            message_id += 1
            ws.send(json.dumps({"id": message_id, "method": method, "params": params}))
            while True:
                message = json.loads(ws.recv(timeout=10))
                if message.get("id") == message_id:
                    assert "error" not in message, message
                    return message.get("result", {})

        def js(code):
            result = cdp("Runtime.evaluate", expression=code, returnByValue=True, awaitPromise=True)
            assert "exceptionDetails" not in result, result
            return result["result"].get("value")

        def photo(name):
            path = opts.out / f"{name}.png"
            path.write_bytes(base64.b64decode(cdp("Page.captureScreenshot", format="png")["data"]))
            print(path, path.stat().st_size)

        def fps():
            start = js("[probe.frames, performance.now()]")
            time.sleep(1.5)
            end = js("[probe.frames, performance.now()]")
            return (end[0] - start[0]) * 1000 / (end[1] - start[1])

        cdp("Emulation.setDeviceMetricsOverride", width=1280, height=720, deviceScaleFactor=1, mobile=False)
        cdp("Network.enable")
        cdp("Page.enable")
        results = {}
        for mode in ("quan", "gather"):
            args = [sys.executable, "-X", "utf8", "-B", "-m", "chonoi.live", "--mode", mode, "--seed", "1", "--port", "0"]
            if mode == "quan":
                args += ["--scenario", str(PROOF / "quan-scenario.json")]
            with ExitStack() as server_stack:
                server = bc.start(server_stack, args, capture=True)
                line = server.stdout.readline().decode("utf-8", "replace")
                url = line.split("tại ", 1)[1].split()[0]
                cdp("Network.setBlockedURLs", urls=[])
                cdp("Page.navigate", url=url)
                bc.until(lambda: js("document.readyState === 'complete' && typeof snapshot === 'object' && !!snapshot"))
                js(bc.HOOK)
                bc.until(lambda: js("!!(phaserScene && phaserScene.viewW && lastMap)"))
                assert js("document.querySelectorAll('#scene > canvas').length") == 2  # lớp tranh + lớp Phaser
                assert js("Phaser.VERSION") == "3.80.1"
                results[mode + "_fps"] = round(fps(), 1)
                if mode == "quan":
                    fired = js("""(() => {
                        const t = snapshot.tables.map(x => x.id), s = snapshot.stoves.map(x => x.id);
                        phaserScene.play([
                          {name:'dish_ready', data:{stove_id:s[0]}},
                          {name:'served', data:{table_id:t[0]}},
                          {name:'paid', data:{table_id:t[0], amount:72}},
                          {name:'customer_left', data:{table_id:t[t.length-1]}}], snapshot);
                        return t.length; })()""")
                    assert fired >= 1
                else:
                    js("phaserScene.play([{name:'fish_caught', data:{kind:'ca_loc', yield:1}},"
                       "{name:'monster_hit', data:{}}], snapshot)")
                time.sleep(.35)
                alive = js("Object.values(phaserScene.fx).reduce((n, e) => n + e.getAliveParticleCount(), 0)")
                tweens = js("phaserScene.tweens.getTweens().length")
                assert alive > 0 and tweens > 0, (alive, tweens)
                results[mode + "_particles"], results[mode + "_tweens"] = alive, tweens
                photo(f"phaser-{mode}-fx")
                assert js("probe.errors.length === 0"), js("probe.errors")

                # Dự phòng: chặn thư viện, tải lại trang → Canvas 2D.
                cdp("Network.setBlockedURLs", urls=["*/vendor/phaser.min.js"])
                cdp("Page.reload", ignoreCache=True)
                bc.until(lambda: js("document.readyState === 'complete' && typeof snapshot === 'object' && !!snapshot"))
                js(bc.HOOK)
                bc.until(lambda: js("typeof Phaser === 'undefined' && phaserScene === null && "
                                    "document.querySelectorAll('#scene > canvas').length === 1 && !!lastMap"))
                results[mode + "_fallback_fps"] = round(fps(), 1)
                assert results[mode + "_fallback_fps"] > 0
                assert js("probe.errors.length === 0"), js("probe.errors")
                cdp("Network.setBlockedURLs", urls=[])
        print(json.dumps(results, ensure_ascii=False))
        assert results["quan_fps"] >= 30 and results["gather_fps"] >= 30, results
        print("Phaser OK: khởi động, hiệu ứng event, dự phòng Canvas 2D khi thiếu thư viện.")


if __name__ == "__main__":
    main()

"""Issue #34: ba cảnh báo chữ/biểu tượng + chế độ tương phản cao.

`?bench=1` thuộc #32 (`chonoi/bench.py`, PR #44) và được kiểm ở test của bench, không ở đây.

Chạy server `chonoi.live` thật (gather, quan), chèn trạng thái nguy hiểm vào snapshot phía trình duyệt
(probe.modify — không đụng mô phỏng) rồi chụp ảnh ở chế độ thường và tương phản cao, 1280×720.

    python -X utf8 -B docs/proof/phase-4/ui/warnings-check.py
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

HERE = Path(__file__).resolve().parent
UI_PROOF = HERE.parents[1] / "ui"
spec = importlib.util.spec_from_file_location("browser_check", UI_PROOF / "browser-check.py")
bc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bc)

# Trạng thái nguy hiểm chèn vào snapshot (chỉ phía client).
DANGER_GATHER = """
    s.player.pos = [6, 9]; s.player.at_surface = false;
    s.player.oxygen_ticks = Math.floor(s.player.oxygen_max_ticks * 0.15);
    s.monsters = [{id: 'M1', kind: 'ca_sau', pos: [8.2, 9.4], state: 'chase', heading_deg: 180}];
"""
DANGER_QUAN = """
    if (Array.isArray(s.customers) && s.customers[0]) s.customers[0].patience_ticks_left = 60;
"""
FONT_MIN = """(() => [...document.querySelectorAll(%s)].filter(el => el.offsetParent)
    .map(el => parseFloat(getComputedStyle(el).fontSize)))()"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("chrome", nargs="?", default=r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    parser.add_argument("--out", type=Path, default=HERE)
    opts = parser.parse_args()
    opts.out.mkdir(parents=True, exist_ok=True)
    report = {}
    with ExitStack() as stack:
        profile = Path(stack.enter_context(TemporaryDirectory(prefix="chonoi-warn-", ignore_cleanup_errors=True)))
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
                message = json.loads(ws.recv(timeout=15))
                if message.get("id") == message_id:
                    assert "error" not in message, message
                    return message.get("result", {})

        def js(code):
            result = cdp("Runtime.evaluate", expression=code, returnByValue=True)
            assert "exceptionDetails" not in result, result
            return result["result"].get("value")

        def tap(key):
            cdp("Input.dispatchKeyEvent", type="keyDown", key=key)
            cdp("Input.dispatchKeyEvent", type="keyUp", key=key)

        def photo(name):
            path = opts.out / f"{name}.png"
            path.write_bytes(base64.b64decode(cdp("Page.captureScreenshot", format="png")["data"]))
            print(path, path.stat().st_size)

        def load(url):
            cdp("Page.navigate", url=url)
            bc.until(lambda: js("document.readyState === 'complete' && typeof snapshot === 'object' && !!snapshot"))
            js(bc.HOOK)
            bc.until(lambda: js("!!lastMap"))

        def font_sizes(selector):
            return js(FONT_MIN % json.dumps(selector))

        cdp("Emulation.setDeviceMetricsOverride", width=1280, height=720, deviceScaleFactor=1, mobile=False)
        cdp("Page.enable")
        for mode in ("gather", "quan"):
            args = [sys.executable, "-X", "utf8", "-B", "-m", "chonoi.live", "--mode", mode, "--seed", "1", "--port", "0"]
            if mode == "quan":
                args += ["--scenario", str(UI_PROOF / "quan-scenario.json")]
            with ExitStack() as server_stack:
                server = bc.start(server_stack, args, capture=True)
                url = server.stdout.readline().decode("utf-8", "replace").split("tại ", 1)[1].split()[0]
                load(url)
                js("localStorage.removeItem('chonoi.contrast.v1'); setContrast(false)")
                if mode == "gather":
                    js("probe.modify = s => {" + DANGER_GATHER + "};")
                    bc.until(lambda: js("document.getElementById('gather-alert').innerText.includes('Thủy quái!')"))
                    alert = js("document.getElementById('gather-alert').innerText")
                    assert "Thủy quái!" in alert and "Oxy sắp hết!" in alert, alert
                    assert js("getComputedStyle(document.getElementById('gather-alert'), '::before').content") == '"⚠"'
                    bc.until(lambda: js("document.querySelector('#meters').innerText.includes('Sắp hết')"))
                    sizes = font_sizes(".warn-badge, #gather-alert")
                else:
                    bc.until(lambda: js("Array.isArray(snapshot.customers) && snapshot.customers.length > 0"))
                    js("probe.modify = s => {" + DANGER_QUAN + "};")
                    bc.until(lambda: js("document.querySelector('#orders .ticket.urgent')?.innerText.includes('Sắp giận!')"))
                    sizes = font_sizes(".warn-badge")
                assert sizes and min(sizes) >= 18, sizes
                report[mode + "_min_warning_px"] = min(sizes)
                bc.until(lambda: js("!phaserScene || !phaserScene.banner.visible"))   # chờ "Bắt đầu!" tắt
                time.sleep(.4)
                photo(f"canh-bao-{mode}-thuong")

                # Tương phản cao bằng phím H, cảnh báo vẫn còn nguyên chữ + biểu tượng.
                tap("h")
                bc.until(lambda: js("document.body.dataset.contrast === 'high'"))
                assert js("document.getElementById('toast').innerText").startswith("Tương phản cao: BẬT")
                time.sleep(.4)
                if mode == "gather":
                    assert "Oxy sắp hết!" in js("document.getElementById('gather-alert').innerText")
                    assert js("getComputedStyle(document.getElementById('game-stage')).outlineStyle") == "dashed"
                else:
                    assert "Sắp giận!" in js("document.querySelector('#orders .ticket.urgent').innerText")
                photo(f"canh-bao-{mode}-tuong-phan")

                # Lưu giữa các lần mở; tắt lại được trong Cài đặt (menu tạm dừng).
                js("probe.modify = null")
                load(url)
                assert js("document.body.dataset.contrast") == "high"
                tap("p")
                bc.until(lambda: js("campaign.panel === 'pause'"))
                js("document.querySelector('[data-action=\"settings\"]').click()")
                bc.until(lambda: js("!!document.getElementById('contrast-toggle')?.checked"))
                js("document.getElementById('contrast-toggle').click()")
                bc.until(lambda: js("document.body.dataset.contrast === ''"))
                js("document.querySelector('[data-action=\"settings-back\"]').click()")
                tap("Escape")
                bc.until(lambda: js("snapshot.state !== 'paused' && !document.querySelector('dialog').open"))
                assert js("probe.errors.length === 0"), js("probe.errors")

    print(json.dumps(report, ensure_ascii=False))
    print("Cảnh báo #34 OK: chữ + biểu tượng, tương phản cao (H / Cài đặt / lưu lại).")


if __name__ == "__main__":
    main()

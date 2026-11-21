"""Issue #22: HUD độ tươi / hàng ươn trên dữ liệu v1.2 THẬT (server chonoi.live, contract v1.2).

1. Sông (gather-v12-scenario.json): giỏ cá thể có thanh + số độ tươi; cá thể 32 hao 0,5/s → event `spoiled`
   thật sau ~4 s → thông báo "… trong giỏ đã ươn!" + hàng gắn nhãn "Ươn". Mở rộng `current`/`reservations`
   (đang tắt trong contract) được thử bằng cách chèn trường vào snapshot phía trình duyệt.
2. Quán (quan-v12-scenario.json): kho cá thể với trạng thái dùng được / đã giữ chỗ / ươn, giá chốt trên bếp,
   cá thể 31 hao 0,25/s → `spoiled` trong kho.
Mỗi cảnh chụp ở chế độ thường và tương phản cao (1280×720).

    python -X utf8 -B docs/proof/ui/phase-3/fresh-check.py
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
spec = importlib.util.spec_from_file_location("browser_check", HERE.parent / "browser-check.py")
bc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bc)
EXTENSIONS = """
    s.current = {direction: 1, ticks_left: 540};
    s.reservations = [{id: 'R1', dish_id: 'goi_bong_sung'}, {id: 'R2', dish_id: 'lau_mam'}];
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("chrome", nargs="?", default=r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    parser.add_argument("--out", type=Path, default=HERE)
    opts = parser.parse_args()
    opts.out.mkdir(parents=True, exist_ok=True)
    report = {}
    with ExitStack() as stack:
        profile = Path(stack.enter_context(TemporaryDirectory(prefix="chonoi-fresh-", ignore_cleanup_errors=True)))
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

        def wait(code, seconds=12):
            deadline = time.time() + seconds
            while time.time() < deadline:
                if js(code):
                    return
                time.sleep(.1)
            raise AssertionError("Timed out: " + code)

        def photo(name):
            path = opts.out / f"{name}.png"
            path.write_bytes(base64.b64decode(cdp("Page.captureScreenshot", format="png")["data"]))
            print(path, path.stat().st_size)

        def journal():
            return js("document.querySelector('#journal').innerText")

        cdp("Emulation.setDeviceMetricsOverride", width=1280, height=720, deviceScaleFactor=1, mobile=False)
        cdp("Page.enable")
        for mode, scenario in (("gather", "gather-v12-scenario.json"), ("quan", "quan-v12-scenario.json")):
            args = [sys.executable, "-X", "utf8", "-B", "-m", "chonoi.live", "--mode", mode, "--seed", "1",
                    "--port", "0", "--scenario", str(HERE / scenario)]
            with ExitStack() as server_stack:
                server = bc.start(server_stack, args, capture=True)
                url = server.stdout.readline().decode("utf-8", "replace").split("tại ", 1)[1].split()[0]
                cdp("Page.navigate", url=url)
                wait("document.readyState === 'complete' && typeof snapshot === 'object' && !!snapshot && !!lastMap")
                js(bc.HOOK)
                js("localStorage.removeItem('chonoi.contrast.v1'); setContrast(false)")
                assert js("snapshot.meta.freshness.spoiled_below") == 30, "meta.freshness phải đến từ contract"
                assert js("snapshot.stock ?? snapshot.hold").__class__ is list
                where = "giỏ" if mode == "gather" else "kho"
                # Event `spoiled` thật từ sim.
                wait(f"document.getElementById('spoiled-notice').innerText.includes('trong {where} đã ươn')", 15)
                notice = js("document.getElementById('spoiled-notice').innerText")
                assert js("document.querySelectorAll('.fresh-row.spoiled .warn-badge').length") >= 1
                rows = js("[...document.querySelectorAll('.fresh-row')].map(r => r.dataset.item + ':' + r.className)")
                sizes = js("[...document.querySelectorAll('.fresh-row strong, .fresh-num, .fresh-summary, .fresh-tag')]"
                           ".map(el => parseFloat(getComputedStyle(el).fontSize))")
                assert sizes and min(sizes) >= 18, sizes
                text = journal()
                if mode == "quan":
                    assert "Kho & độ tươi" in text and text.count("Đã giữ chỗ cho khách") == 2, text
                    assert "Ươn · không dùng được" in text, text
                    assert "Giá chốt 52 nghìn (niêm yết 60)" in text, text
                    assert "dùng được" in js("document.querySelector('.fresh-summary').innerText")
                report[mode] = {"notice": notice, "rows": rows, "min_px": min(sizes)}
                photo(f"fresh-{mode}")
                if mode == "quan":  # kho dài nằm cuối bảng phải: cuộn xuống để chụp từng cá thể
                    js("document.getElementById('hud-right').scrollTop = 1e6")
                    time.sleep(.2)
                    photo("fresh-quan-kho")
                    js("document.getElementById('hud-right').scrollTop = 0")
                js("setContrast(true)")
                time.sleep(.3)
                assert js("getComputedStyle(document.querySelector('.fresh-row.spoiled')).borderTopStyle") == "dashed"
                photo(f"fresh-{mode}-tuong-phan")
                js("setContrast(false)")
                if mode == "gather":
                    js("probe.modify = s => {" + EXTENSIONS + "};")
                    wait("document.getElementById('current-notice').innerText.includes('Dòng lũ → đẩy sang phải')")
                    wait("document.querySelector('#journal').innerText.includes('R1 · Gỏi bông súng')")
                    report["extensions"] = js("document.getElementById('current-notice').innerText")
                    photo("fresh-current")
                    js("probe.modify = null")
                assert js("probe.errors.length === 0"), js("probe.errors")
    print(json.dumps(report, ensure_ascii=False))
    print("Độ tươi #22 OK: giỏ/kho cá thể v1.2 thật, spoiled thật, giá chốt, mở rộng, tương phản cao.")


if __name__ == "__main__":
    main()

"""Browser evidence for issues #5 and #22. Requires Python, Chrome and websockets."""
import argparse
import base64
from contextlib import ExitStack
import json
from math import dist
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
from urllib.request import urlopen
from websockets.sync.client import connect

PROOF = Path(__file__).resolve().parent
HOOK = """
globalThis.probe = {posts: [], modify: null, errors: [], frames: 0};
const realFetch = fetch.bind(globalThis), realWarn = console.warn.bind(console);
console.warn = (...args) => { probe.errors.push(String(args[0])); realWarn(...args); };
addEventListener("error", e => probe.errors.push(e.message));
addEventListener("unhandledrejection", e => probe.errors.push(String(e.reason)));
globalThis.fetch = async (url, options) => {
    if (url === "/input") probe.posts.push(JSON.parse(options.body));
    const response = await realFetch(url, options);
    if (url !== "/state" || !probe.modify) return response;
    const snapshot = await response.json();
    probe.modify(snapshot);
    return new Response(JSON.stringify(snapshot));
};
requestAnimationFrame(function count() { probe.frames++; requestAnimationFrame(count); });
"""


def until(check):
    for _ in range(110):
        try:
            result = check()
            if result:
                return result
        except OSError:
            pass
        time.sleep(.07)
    raise AssertionError(f"Timed out: {check.__name__} at line {check.__code__.co_firstlineno}")


def read(url):
    with urlopen(url, timeout=2) as response:
        return json.load(response)


def start(stack, argv, *, capture=False):
    process = subprocess.Popen(argv, stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
                               stderr=subprocess.STDOUT if capture else subprocess.DEVNULL)
    def stop():
        if process.poll() is None:
            process.terminate()
        process.wait(timeout=10)
        if process.stdout:
            process.stdout.close()
    stack.callback(stop)
    return process


def check_freshness(mode, js, tap, photo, modify):
    if mode == "gather":
        modify("s.hold = ['ca_loc', 'ca_loc', 'bong_sung']; delete s.hold_count;")
        until(lambda: js("document.querySelector('#journal').innerText.includes('Cá lóc × 2')"))
        modify("""s.hold = [
            {id:'I1',kind:'ca_loc',fresh:96.5}, {id:'I2',kind:'bong_sung',fresh:30},
            {id:'I3',kind:'ca_keo',fresh:29.999}, {id:'I4',kind:'keo_neo',fresh:0},
            {id:'I5',kind:'ca_linh'}, null
        ]; delete s.hold_count;
        s.reservations = [{id:'R1',dish_id:'ca_loc_nuong_trui'}, {id:'R2'}];
        s.events = [{name:'spoiled',phase:'gather',tick:s.tick,data:{item_id:'I3',kind:'ca_keo',location:'hold'}}];""")
        until(lambda: js("document.querySelector('[data-item=I3].spoiled')?.innerText.includes('29,9 / 100')"))
        assert js("!document.querySelector('[data-item=I2]').classList.contains('spoiled')")
        assert js("document.querySelector('[data-item=I4]').innerText.includes('0 / 100')")
        assert js("document.querySelector('[data-item=I5]').innerText.includes('Chưa có độ tươi')")
        assert js("document.querySelector('#journal').innerText.includes('Giỏ · 5 / 12')")
        assert js("document.querySelector('#journal').innerText.includes('R1') && document.querySelector('#journal').innerText.includes('R2')")
        until(lambda: js("!document.querySelector('#spoiled-notice').hidden"))
        time.sleep(.38)
        photo("fresh-gather")
        until(lambda: js("document.querySelector('#spoiled-notice').hidden"))
        # Dữ liệu cùng một item tiếp tục tới mỗi poll. Thông báo phải hết hạn và không bật lại.
        time.sleep(.3)
        assert js("document.querySelector('#spoiled-notice').hidden")
        js("""probe.chimes = 0;
            const startTone = OscillatorNode.prototype.start;
            OscillatorNode.prototype.start = function (...args) {
                probe.chimes++;
                return startTone.apply(this,args);
            };""")
        tap("q")
        until(lambda: js("currentAudio?.state === 'running'"))
        modify("""s.phase_tick = 1680; s.current = null;
            s.events = [{name:'current_warning',phase:'gather',tick:s.tick,data:{starts_at_phase_tick:1800}}];""")
        until(lambda: js("document.querySelector('#current-notice').textContent.includes('2 giây') && probe.chimes === 1"))
        time.sleep(.15)
        assert js("probe.chimes === 1")
        modify("s.current = {direction:-1,ticks_left:360};")
        until(lambda: js("document.querySelector('#current-notice').textContent.includes('← sang trái')"))
        photo("fresh-current")
    else:
        modify("""s.stock = [
            {id:'I1',kind:'ca_loc',fresh:95}, {id:'I2',kind:'ca_loc',fresh:30},
            {id:'I3',kind:'bong_sung',fresh:29.999},{id:'I4',kind:'ca_keo',fresh:'95'},
            {id:'I5',kind:'keo_neo',fresh:74}
        ];
        s.customers = [{reserved:['I1']}];
        s.stoves[0] = {...s.stoves[0],state:'cooking',dish:{dish_id:'ca_loc_nuong_trui',order_id:'O1',base_price:47}};
        s.hand = {dish_id:'goi_bong_sung',order_id:'O2',base_price:33};
        s.events = [{name:'spoiled',phase:'quan',tick:s.tick,data:{item_id:'I3',kind:'bong_sung',location:'stock'}}];""")
        until(lambda: js("document.querySelector('#journal').innerText.includes('2 cá thể khả dụng')"))
        assert js("document.querySelector('[data-item=I1]').innerText.includes('Đã giữ chỗ')")
        assert js("document.querySelector('[data-item=I3].spoiled').innerText.includes('Hàng ươn')")
        assert js("document.querySelector('[data-item=I4]').innerText.includes('Chưa có độ tươi')")
        assert js("[...document.querySelectorAll('.locked-price')].map(p => p.textContent).join('|').includes('47 nghìn|Giá đã chốt · 33 nghìn')")
        until(lambda: js("document.querySelector('#spoiled-notice').innerText.includes('trong kho')"))
        assert js("document.querySelector('#journal').getBoundingClientRect().top < innerHeight/2")
        time.sleep(.38)
        photo("fresh-quan")
        modify("""s.stock = {ca_loc:1,bong_sung:2}; s.customers = [{reserved:{ca_loc:1}}];
            s.stoves[0].dish = {dish_id:'ca_loc_nuong_trui',order_id:'O1'};
            s.events = [{ name:'cook_started', data:{stove_id:'B1',order_id:'O1',dish_id:'ca_loc_nuong_trui',base_price:41} }];""")
        until(lambda: js("document.querySelector('#journal').innerText.includes('Kho khả dụng')"))
        assert js("!document.querySelector('#journal').innerText.includes('Cá lóc × 1')")
        assert js("document.querySelector('#journal').innerText.includes('Giá đã chốt · 41 nghìn')")
        modify("delete s.stock; delete s.hand; delete s.customers; delete s.stoves; delete s.events;")
        until(lambda: js("document.querySelector('#journal').innerText.includes('Chưa có dữ liệu kho.')"))
        assert js("document.querySelectorAll('.locked-price').length === 0")
    assert js("probe.errors.length === 0"), js("probe.errors")
    print(f"{mode}: snapshot độ tươi, dữ liệu thiếu và phản hồi cảnh báo OK")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("chrome", nargs="?", default=r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    parser.add_argument("--out", type=Path, default=PROOF)
    parser.add_argument("--freshness", action="store_true", help="Thử display v1.2 bằng phản hồi mẫu")
    opts = parser.parse_args()
    opts.out.mkdir(parents=True, exist_ok=True)
    with ExitStack() as stack:
        profile = Path(stack.enter_context(TemporaryDirectory(prefix="chonoi-ui-", ignore_cleanup_errors=True)))
        start(stack, [opts.chrome, "--headless", "--disable-extensions", "--no-first-run",
                      "--disable-background-networking", "--remote-debugging-port=0",
                      f"--user-data-dir={profile}", "about:blank"])
        port = until(lambda: (profile / "DevToolsActivePort").read_text().splitlines())[0]
        target = until(lambda: read(f"http://127.0.0.1:{port}/json/list"))[0]
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
            result = cdp("Runtime.evaluate", expression=code, returnByValue=True)
            assert "exceptionDetails" not in result, result
            return result["result"].get("value")

        def key(name, event):
            cdp("Input.dispatchKeyEvent", type=event, key=name)

        def tap(name):
            key(name, "keyDown")
            key(name, "keyUp")

        def touch(selector):
            coords = js(f"""
                (() => {{
                    const item = document.querySelector({json.dumps(selector)});
                    const box = item.getBoundingClientRect();
                    return {{x: box.x + box.width/2, y: box.y + box.height/2}};
                }})()
            """)
            cdp("Input.dispatchTouchEvent", type="touchStart", touchPoints=[coords])

        def viewport(width, height):
            cdp("Emulation.setDeviceMetricsOverride", width=width, height=height, deviceScaleFactor=1, mobile=False)

        def photo(name):
            path = opts.out / f"{name}.png"
            path.write_bytes(base64.b64decode(cdp("Page.captureScreenshot", format="png")["data"]))
            print(path, path.stat().st_size)

        def modify(code):
            js("probe.modify = s => {" + code + "};")

        viewport(1280, 800)
        for mode in ("gather", "quan"):
            args = [sys.executable, "-X", "utf8", "-B", "-m", "chonoi.live", "--mode", mode, "--seed", "1", "--port", "0"]
            if mode == "quan":
                args += ["--scenario", str(PROOF / "quan-scenario.json")]
            game = start(stack, args, capture=True)
            startup = game.stdout.readline().decode("utf-8", errors="replace")
            address = re.search(r"http://127\.0\.0\.1:(\d+)/", startup)
            assert address, startup
            url, port = address.group(0), address.group(1)
            def state():
                return read(url + "state")
            assert until(state)["mode"] == mode and game.poll() is None
            cdp("Page.navigate", url=url)
            until(lambda: js(f"location.port === '{port}' && document.body?.dataset.mode === '{mode}'"))
            js(HOOK)
            if opts.freshness:
                check_freshness(mode,js,tap,photo,modify)
                continue
            if mode == "gather":
                tap("e")
                until(lambda: state()["reason"] == "docked")
                tap("r")
                until(lambda: not state()["finished"])
                key("d", "keyDown")
                key("ArrowDown", "keyDown")
                until(lambda: state()["player"]["pos"][0] > 7 and state()["player"]["pos"][1] > 5)
                tap(" ")
                until(lambda: js("probe.posts.some(p => p.catch)"))
                js("dispatchEvent(new Event('blur'))")
                until(lambda: js("probe.posts.at(-1).move.every(n => n === 0)"))
                key("d", "keyUp")
                key("ArrowDown", "keyUp")
                time.sleep(.25)
                held = state()["player"]["pos"]
                time.sleep(.18)
                assert state()["player"]["pos"] == held
                photo("gather")
                modify("""delete s.player; delete s.hold; delete s.time_left_ticks;
                    s.nodes = [null, {pos:['bad',0]}, s.nodes[1]];
                    s.fish = [false, {pos:[null,5]}, s.fish[0]];""")
                until(lambda: js("document.querySelector('#meters').innerText.includes('—')"))
                old_frames = js("probe.frames")
                modify("delete s.meta.bounds; delete s.player;")
                time.sleep(.2)
                assert js("probe.frames") > old_frames
                js("probe.modify = null")
                until(lambda: js("Array.isArray(snapshot.player?.pos)"))
                viewport(390, 844)
                cdp("Emulation.setTouchEmulationEnabled", enabled=True, maxTouchPoints=2)
                until(lambda: js("innerWidth === 390 && document.documentElement.scrollWidth <= document.documentElement.clientWidth"))
                prior_x = state()["player"]["pos"][0]
                touch('[data-input="arrowright"]')
                until(lambda: state()["player"]["pos"][0] > prior_x + .5)
                cdp("Input.dispatchTouchEvent", type="touchCancel", touchPoints=[])
                until(lambda: js("probe.posts.at(-1).move.every(n => n === 0)"))
                prior_catches = js("probe.posts.filter(p => p.catch).length")
                touch("#touch-catch")
                until(lambda: js("probe.posts.filter(p => p.catch).length") > prior_catches)
                cdp("Input.dispatchTouchEvent", type="touchEnd", touchPoints=[])
                until(lambda: js("probe.posts.at(-1).catch === false"))
                photo("gather-390")
                cdp("Emulation.setTouchEmulationEnabled", enabled=False)
                viewport(1280, 800)
            else:
                panel = js("document.querySelector('#journal').innerText + document.querySelector('#orders').innerText")
                assert all(word in panel for word in ["K1", "Kiên nhẫn", "Đang nấu", "Lẩu cá linh điên điển"]), panel
                assert js("document.querySelector('.controls').getBoundingClientRect().bottom <= innerHeight")
                photo("quan")
                key("w", "keyDown")
                until(lambda: state()["player"]["pos"][1] > 7.2)
                key("w", "keyUp")
                until(lambda: state()["stoves"][0]["state"] == "ready")
                tap("e")
                until(lambda: js("probe.posts.some(p => p.move[1] === 1) && probe.posts.some(p => p.interact)"))
                until(lambda: state()["hand"] and state()["hand"]["dish_id"] == "lau_ca_linh_dien_dien")
                modify("s.customers[0].reserved = {ca_linh: 2, ca_loc: 'bad'};")
                until(lambda: js("document.querySelector('#journal').innerText.includes('Cá linh × 1')"))
                modify("s.customers[0].patience_ticks_left = 60;")
                until(lambda: js("document.querySelector('#orders .ticket.urgent')?.textContent.includes('1 giây')"))
                modify("s.time_left_ticks = 840;")
                until(lambda: js("document.querySelector('.meter--clock.meter--urgent')?.textContent.includes('0:14')"))
                for mutation, expected in [
                    ("delete s.customers; delete s.hand;", "Chưa có dữ liệu món."),
                    ("s.customers = null; s.hand = null;", "Tay đang trống."),
                    ("s.customers = {bad:true}; s.hand = 'goi_bong_sung';", "Gỏi bông súng"),
                    ("s.customers = [null, 4, {}, s.customers[0]]; s.hand = {dish_id:'ca_loc_nuong_trui'};", "Kiên nhẫn"),
                    ("s.player.pos = [null,2]; s.hand = [1]; s.money = 'bad'; s.reputation = {};", "Chưa có dữ liệu món."),
                ]:
                    modify(mutation)
                    time.sleep(.18)
                    panel = js("document.querySelector('#journal').innerText + document.querySelector('#orders').innerText")
                    assert expected in panel and "Kho khả dụng" in panel, panel
                js("probe.modify = null")
                until(lambda: js("document.querySelector('#action-tip').innerText.includes('đang bưng món')"))
                viewport(390, 844)
                until(lambda: js("innerWidth === 390 && document.documentElement.scrollWidth <= document.documentElement.clientWidth"))
                photo("quan-390")
                key("ArrowRight", "keyDown")
                until(lambda: state()["player"]["pos"][0] > 8.6)
                key("ArrowRight", "keyUp")
                key("s", "keyDown")
                until(lambda: state()["player"]["pos"][1] < 2.8)
                key("s", "keyUp")
                until(lambda: state()["player"].get("vel") == [0,0])
                delivery = state()
                table = next(item for item in delivery["tables"] if item["id"] == "T1")
                assert dist(delivery["player"]["pos"],table["pos"]) <= delivery["meta"]["interact_radius"], delivery["player"]
                tap("e")
                until(lambda: any(item["id"] == "K1" and item["state"] == "eating" for item in state()["customers"]))
                until(lambda: js("document.querySelector('#orders .ticket.eating')?.textContent.includes('Đang ăn')"))
                until(lambda: js("document.querySelector('#action-tag').textContent === 'Đã giao món'"))
            assert js("probe.errors.length === 0"), js("probe.errors")
            print(mode, "input, HUD and snapshots OK", js("probe.frames"), "frames")


if __name__ == "__main__":
    main()

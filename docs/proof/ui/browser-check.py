"""Browser evidence for issues #5 and #16. Requires Python, Chrome and websockets."""
import argparse
import base64
from contextlib import ExitStack
import json
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


def check_day_fixture(cdp, js, tap, photo):
    fixture = (PROOF / "phase-2/day-fixture.js").read_text(encoding="utf-8")
    js(fixture)

    def panel(name):
        return until(lambda: js(f"campaign.panel === {json.dumps(name)} && document.querySelector('dialog').open"))

    def choose(name):
        selector = json.dumps(f'[data-action="{name}"]')
        until(lambda: js(f"Boolean(document.querySelector({selector}) && !document.querySelector({selector}).disabled)"))
        js(f"document.querySelector({selector}).click()")

    def frozen():
        until(lambda: js("dayTest.state.state === 'paused'"))
        before = js("[dayTest.state.phase_tick,dayTest.state.sim_tick,dayTest.state.time_left_ticks]")
        time.sleep(.35)
        assert js("[dayTest.state.phase_tick,dayTest.state.sim_tick,dayTest.state.time_left_ticks]") == before

    panel("menu")
    frozen()
    photo("day-menu")
    choose("exit")
    panel("exit")
    choose("menu")
    choose("settings")
    panel("settings")
    for channel, value in (("master",37),("music",19),("sfx",81)):
        js(f"""(() => {{
            const slider = document.getElementById("volume-{channel}");
            slider.value = "{value}";
            slider.dispatchEvent(new Event("input",{{bubbles:true}}));
        }})()""")
    assert js("JSON.parse(localStorage.getItem('chonoi.audio.v1'))") == {"master":.37,"music":.19,"sfx":.81}
    choose("settings-back")
    choose("play")
    panel("day-intro")
    frozen()
    assert js("document.querySelector('dialog').innerText.includes('Gỏi bông súng')")
    photo("day-intro")
    tap("e")
    until(lambda: js("!document.querySelector('dialog').open && dayTest.state.state === 'playing'"))
    until(lambda: js("document.getElementById('gather-alert').innerText.includes('Thủy quái! · Hết hơi!')"))
    assert js("document.querySelector('#meters').innerText.includes('12 m')")
    assert js("document.querySelector('#journal').innerText.includes('Nguyên liệu cần lấy')")
    photo("day-gather")
    frame_count, start = js("[probe.frames,performance.now()]")
    time.sleep(1.5)
    rendered, end = js("[probe.frames,performance.now()]")
    gather_fps = (rendered-frame_count)*1000/(end-start)
    assert gather_fps >= 30, gather_fps

    js("dayTest.enter('quan')")
    panel("evening-intro")
    frozen()
    assert js("document.querySelector('dialog').innerText.includes('Đã nhập 3 nguyên liệu')")
    photo("day-evening-intro")
    choose("continue")
    until(lambda: js("!document.querySelector('dialog').open && dayTest.state.state === 'playing'"))
    assert js("getComputedStyle(document.querySelector('#meters .label')).fontSize === '18px'")
    assert js("snapshot.stoves.length === 2 && snapshot.tables.length === 4")
    assert js("document.querySelector('.controls').getBoundingClientRect().bottom <= innerHeight")
    assert js("document.querySelector('#journal').getBoundingClientRect().bottom <= innerHeight")
    photo("day-quan")
    frame_count, start = js("[probe.frames,performance.now()]")
    time.sleep(1.5)
    rendered, end = js("[probe.frames,performance.now()]")
    quan_fps = (rendered-frame_count)*1000/(end-start)
    assert quan_fps >= 30, quan_fps
    js("dayTest.closeEvening()")
    panel("day-result")
    frozen()
    assert js("document.querySelector('dialog').innerText.includes('12 nghìn')")
    photo("day-result")
    choose("continue")
    panel("shop")
    until(lambda: js("dayTest.state.state === 'playing'"))
    choose("buy:hp")
    until(lambda: js("document.querySelector('.shop-feedback').innerText === 'Không đủ tiền.'"))
    tap("p")
    panel("pause")
    frozen()
    photo("day-pause")
    tap("Escape")
    panel("shop")
    until(lambda: js("dayTest.state.state === 'playing'"))
    choose("buy:oxygen")
    until(lambda: js("dayTest.state.upgrades.oxygen === 1 && dayTest.state.money === 0"))
    until(lambda: js("document.querySelector('.shop-feedback').innerText.includes('Đã mua Bình oxy')"))
    photo("day-shop")
    choose("shop-done")
    panel("day-intro")
    assert js("dayTest.posts.some(post => post.shop_done === true)")
    until(lambda: js("!document.querySelector('dialog').open && dayTest.state.state === 'playing'"))
    assert js("dayTest.state.day === 2")
    js("dayTest.state.day=5; dayTest.enter('shop')")
    panel("shop")
    choose("shop-done")
    panel("summary")
    assert js("document.querySelector('dialog').innerText.includes('Cá lóc nướng trui × 1')")
    photo("day-summary")
    assert js("probe.errors.length === 0"), js("probe.errors")

    cdp("Page.reload")
    until(lambda: js("!globalThis.dayTest && document.body?.dataset.mode === 'gather'"))
    js(HOOK)
    js(fixture)
    panel("menu")
    choose("settings")
    panel("settings")
    assert js("['master','music','sfx'].map(key=>document.getElementById('volume-'+key).value)") == ["37","19","81"]
    print(f"Fixture 1280×720: gather {gather_fps:.1f} FPS, quan {quan_fps:.1f} FPS; full flow, pause and Settings OK.")


def check_day_live(state, js, tap, photo):
    def panel(name):
        return until(lambda: js(f"campaign.panel === {json.dumps(name)} && document.querySelector('dialog').open"))

    def choose(name):
        selector = json.dumps(f'[data-action="{name}"]')
        until(lambda: js(f"Boolean(document.querySelector({selector}) && !document.querySelector({selector}).disabled)"))
        js(f"document.querySelector({selector}).click()")

    def playing(phase, expect_dialog=False):
        until(lambda: state()["phase"] == phase and state()["state"] == "playing")
        expected = str(expect_dialog).lower()
        until(lambda: js(f"snapshot.state === 'playing' && document.querySelector('dialog').open === {expected}"))

    panel("menu")
    choose("play")
    panel("day-intro")
    choose("continue")
    playing("gather")
    photo("live-day-gather")
    tap("e")
    panel("evening-intro")
    assert state()["stock"] == {"bong_sung": 2, "ca_loc": 1}
    assert js("document.querySelector('dialog').innerText.includes('Đã nhập 3 nguyên liệu')")
    photo("live-day-evening")
    choose("continue")
    panel("day-result")
    choose("continue")
    panel("shop")
    playing("shop", expect_dialog=True)
    choose("buy:hp")
    until(lambda: js("document.querySelector('.shop-feedback').innerText === 'Không đủ tiền.'"))
    tap("p")
    panel("pause")
    until(lambda: state()["state"] == "paused")
    before = state()
    time.sleep(.3)
    after = state()
    assert all(after[key] == before[key] for key in ("phase_tick","sim_tick","time_left_ticks"))
    assert after["tick"] > before["tick"]
    tap("Escape")
    panel("shop")
    playing("shop", expect_dialog=True)
    choose("buy:oxygen")
    until(lambda: state()["money"] == 0 and state()["upgrades"]["oxygen"] == 1)
    until(lambda: js("document.querySelector('.shop-feedback').innerText.includes('Đã mua Bình oxy')"))
    photo("live-day-shop")
    choose("shop-done")
    panel("summary")
    final = state()
    assert final["reason"] == "days_complete" and final["days_completed"] == 1
    assert js("document.querySelector('dialog').innerText.includes('Đã xong 1 Ngày')")
    assert js("probe.errors.length === 0"), js("probe.errors")
    photo("live-day-summary")
    print("Live day: dock → stock transfer → shop pause/resume and buy → days_complete OK.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("chrome", nargs="?", default=r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    parser.add_argument("--out", type=Path, default=PROOF)
    day_group = parser.add_mutually_exclusive_group()
    day_group.add_argument("--day-fixture", action="store_true", help="Thử UI Ngày với phản hồi HTTP giả lập.")
    day_group.add_argument("--day-live", action="store_true", help="Chơi một Ngày thật bằng runner v1.1.")
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
        for mode in (("day",) if opts.day_live else ("gather",) if opts.day_fixture else ("gather", "quan")):
            args = [sys.executable, "-X", "utf8", "-B", "-m", "chonoi.live", "--mode", mode, "--seed", "1", "--port", "0"]
            if mode == "quan":
                args += ["--scenario", str(PROOF / "quan-scenario.json")]
            elif mode == "day":
                args += ["--days", "1", "--scenario", str(PROOF / "phase-2/day-live-scenario.json")]
            game = start(stack, args, capture=True)
            startup = game.stdout.readline().decode("utf-8", errors="replace")
            address = re.search(r"http://127\.0\.0\.1:(\d+)/", startup)
            assert address, startup
            url, port = address.group(0), address.group(1)
            def state():
                return read(url + "state")
            assert until(state)["mode"] == mode and game.poll() is None
            cdp("Page.navigate", url=url)
            until(lambda: js(f"location.port === '{port}' && document.body?.dataset.run === '{mode}'"))
            js(HOOK)
            if opts.day_live:
                viewport(1280,720)
                check_day_live(state,js,tap,photo)
                return
            if opts.day_fixture:
                viewport(1280,720)
                check_day_fixture(cdp,js,tap,photo)
                return
            if mode == "gather":
                tap("p")
                until(lambda: state()["state"] == "paused")
                frozen = state()
                time.sleep(.25)
                assert all(state()[field] == frozen[field] for field in ("phase_tick","sim_tick","time_left_ticks"))
                tap("Escape")
                until(lambda: state()["state"] == "playing" and state()["sim_tick"] > frozen["sim_tick"])
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
                until(lambda: state()["player"]["pos"][1] < 3.25)
                key("s", "keyUp")
                tap("e")
                until(lambda: state()["customers"][0]["state"] == "eating")
                until(lambda: js("document.querySelector('#orders .ticket.eating')?.textContent.includes('Đang ăn')"))
                until(lambda: js("document.querySelector('#action-tag').textContent === 'Đã giao món'"))
            assert js("probe.errors.length === 0"), js("probe.errors")
            print(mode, "input, HUD and snapshots OK", js("probe.frames"), "frames")


if __name__ == "__main__":
    main()

"""Soak headless (Phase 4, Issue #31): chạy bot tất định nhiều Ngày trong một tiến trình.

    python3 -m chonoi.soak --seed 7 --days 10 --out soak.json

Mã thoát: 0 bình thường; 2 sai tham số/contract (kiểm TRƯỚC khi ghi file); 1 lỗi ghi đầu ra.
Không ghi bảng xếp hạng. Cùng seed → mọi trường trong soak.json giống nhau trừ duration_s.
"""

import argparse
from collections import Counter
import json
import math
import os
import sys
import tempfile
import time

from .contract import load_contract
from .errors import BadInput
from .ids import IdAllocator, id_key
from .inputs import BUTTONS_V11, InputState, normalize
from .rng import Streams
from .sim.day import DaySim


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write(f"lỗi: {message}\n")
        sys.exit(2)


def _int(name):
    def conv(s):
        try:
            return int(s)
        except ValueError:
            raise argparse.ArgumentTypeError(f"{name} phải là số nguyên")
    return conv


def _hold_counts(hold: list) -> Counter:
    """Đếm nguyên liệu trong giỏ (tương thích cả v1.1 chuỗi kind lẫn v1.2 dict cá thể)."""
    counts = Counter()
    for item in hold:
        kind = item["kind"] if isinstance(item, dict) else item
        counts[kind] += 1
    return counts


def _move_vec(src, dst):
    dx = dst[0] - src[0]
    dy = dst[1] - src[1]
    dist = math.hypot(dx, dy)
    if dist < 1e-6:
        return (0.0, 0.0)
    return normalize((dx / dist, dy / dist))


class SoakBot:
    """Bot tất định điều khiển Út Sen qua gather → quan → shop (không dùng đồng hồ)."""

    def __init__(self, tuning: dict, streams: Streams):
        self.tuning = tuning
        self.rng = streams.get("soak_bot")
        self._held = {b: False for b in BUTTONS_V11}

    def reset_buttons(self):
        self._held = {b: False for b in BUTTONS_V11}

    def _make_input(self, move=(0.0, 0.0), *, interact=False, catch=False, shop_done=False, buy=None) -> InputState:
        wanted = {"interact": interact, "catch": catch, "pause": False, "shop_done": shop_done}
        edges = set()
        for btn, val in wanted.items():
            # Nếu nút đang giữ từ tick trước mà tick này lại muốn bấm mới, nhả 1 tick trước
            if val and not self._held[btn]:
                edges.add(btn)
            self._held[btn] = val
        return InputState(normalize(move), dict(self._held), edges, buy=buy)

    def decide(self, day_sim: DaySim) -> InputState:
        phase = day_sim.phase
        snap = day_sim.snapshot()
        if phase == "gather":
            return self._decide_gather(day_sim, snap)
        if phase == "quan":
            return self._decide_quan(day_sim, snap)
        return self._decide_shop(day_sim, snap)

    def _decide_gather(self, day_sim: DaySim, snap: dict) -> InputState:
        g = day_sim.t_day["gather"]
        p = snap["player"]
        pos = p["pos"]
        dock_pos = g["dock_pos"]
        dock_r = g["dock_radius"]
        inter_r = g["interact_radius"]
        catch_r = g["catch_radius"]
        hold_count = snap["hold_count"]
        hold_cap = snap["hold_capacity"]
        free = hold_cap - hold_count

        # 1. An toàn oxy: dưới 35% thì ngoi thẳng lên mặt nước
        if not p["at_surface"] and p["oxygen_ticks"] < p["oxygen_max_ticks"] * 0.35:
            return self._make_input((0.0, -1.0))

        # Tính phần nguyên liệu còn thiếu so với day_plan
        have = _hold_counts(snap["hold"])
        plan_ing = snap["day_plan"]["ingredients"]
        needed = {k: plan_ing[k] - have[k] for k in sorted(plan_ing) if plan_ing[k] > have[k]}

        # 2. Về bến khi giỏ đủ hàng, hết mục tiêu cần, hoặc sắp hết giờ
        should_dock = (
            hold_count >= min(hold_cap, 8)
            or (not needed and hold_count > 0)
            or (day_sim.time_left_ticks <= 2400 and hold_count > 0)
        )
        if not should_dock:
            target = self._pick_gather_target(g, snap, pos, free, needed)
            if target is None:
                should_dock = True
            else:
                kind_action, obj = target
                tpos = obj["pos"]
                dist = math.dist(pos, tpos)
                if kind_action == "node":
                    if p["at_surface"] and dist <= inter_r:
                        want = not self._held["interact"]
                        return self._make_input((0.0, 0.0), interact=want)
                    return self._make_input(_move_vec(pos, [tpos[0], 0.0]))
                # kind_action == "fish"
                if (not p["at_surface"]) and dist <= catch_r and p["catch_cd_ticks"] == 0:
                    want = not self._held["catch"]
                    return self._make_input((0.0, 0.0), catch=want)
                return self._make_input(_move_vec(pos, tpos))

        # Đi về bến và cập bến
        if math.dist(pos, dock_pos) <= dock_r:
            want = not self._held["interact"]
            return self._make_input((0.0, 0.0), interact=want)
        return self._make_input(_move_vec(pos, dock_pos))

    @staticmethod
    def _pick_gather_target(g: dict, snap: dict, pos: list, free: int, needed: dict):
        monsters = snap.get("monsters", [])
        fish_yield = g["fish_yield"]
        node_yield = int(g["node_yield"])
        cands = []
        if free >= node_yield:
            for n in snap["nodes"]:
                if n["ready"] and n["kind"] in needed:
                    cands.append((math.dist(pos, n["pos"]), 0, id_key(n["id"]), "node", n))
        for f in snap["fish"]:
            if f["kind"] not in needed:
                continue
            if fish_yield.get(f["kind"], 99) > free:
                continue
            # Tránh đàn cá đứng sát Cá Sấu để không mất Máu/hàng vô ích
            if any(math.dist(f["pos"], m["pos"]) <= 5.0 for m in monsters):
                continue
            cands.append((math.dist(pos, f["pos"]), 1, id_key(f["id"]), "fish", f))
        if not cands and free >= node_yield:
            for n in snap["nodes"]:
                if n["ready"]:
                    cands.append((math.dist(pos, n["pos"]), 2, id_key(n["id"]), "node", n))
        if not cands:
            return None
        best = min(cands, key=lambda item: item[:3])
        return best[3], best[4]

    def _decide_quan(self, day_sim: DaySim, snap: dict) -> InputState:
        q = day_sim.t_day["quan"]
        pos = snap["player"]["pos"]
        inter_r = q["interact_radius"]
        hand = snap["hand"]
        stoves = snap["stoves"]
        tables = {tb["id"]: tb for tb in snap["tables"]}
        customers = snap["customers"]

        # 1. Đang cầm món -> bưng tới đúng bàn của đơn
        if hand is not None:
            cust = next((c for c in customers if c["id"] == hand["order_id"]), None)
            if cust is not None and cust["table_id"] in tables:
                tpos = tables[cust["table_id"]]["pos"]
                if math.dist(pos, tpos) <= inter_r:
                    return self._make_input((0.0, 0.0), interact=(not self._held["interact"]))
                return self._make_input(_move_vec(pos, tpos))

        # 2. Bếp có món ready và tay trống -> tới nhặt
        ready_stoves = [s for s in stoves if s["state"] == "ready"]
        if ready_stoves and hand is None:
            stove = min(ready_stoves, key=lambda s: (math.dist(pos, s["pos"]), id_key(s["id"])))
            if math.dist(pos, stove["pos"]) <= inter_r:
                return self._make_input((0.0, 0.0), interact=(not self._held["interact"]))
            return self._make_input(_move_vec(pos, stove["pos"]))

        # 3. Có khách waiting + reserved và có bếp idle -> tới nấu
        has_reserved = any(c["state"] == "waiting" and c["order_status"] == "reserved" for c in customers)
        idle_stoves = [s for s in stoves if s["state"] == "idle"]
        if has_reserved and idle_stoves:
            stove = min(idle_stoves, key=lambda s: (math.dist(pos, s["pos"]), id_key(s["id"])))
            if math.dist(pos, stove["pos"]) <= inter_r:
                return self._make_input((0.0, 0.0), interact=(not self._held["interact"]))
            return self._make_input(_move_vec(pos, stove["pos"]))

        # 4. Đứng chờ gần bếp đầu tiên
        if stoves:
            return self._make_input(_move_vec(pos, stoves[0]["pos"]))
        return self._make_input((0.0, 0.0))

    def _decide_shop(self, day_sim: DaySim, snap: dict) -> InputState:
        # Tick đầu tiên của Shop: mua 1 cấp nâng cấp nếu đủ tiền (ưu tiên oxygen rồi hp)
        if day_sim.phase_tick == 0:
            up_cfg = day_sim.tuning["shop"]["upgrades"]
            for key in ("oxygen", "hp"):
                levels = up_cfg.get(key, [])
                cur = snap["upgrades"].get(key, 0)
                if cur < len(levels) and day_sim.money >= levels[cur]["price"]:
                    return self._make_input((0.0, 0.0), buy=key)
        return self._make_input((0.0, 0.0), shop_done=(not self._held["shop_done"]))


def run_soak(tuning: dict, seed: int, days: int, *, day_sim_cls=DaySim, bot_cls=SoakBot) -> dict:
    """Chạy soak `days` Ngày trong một tiến trình duy nhất; bắt mọi exception theo từng Ngày."""
    if isinstance(days, bool) or not isinstance(days, int) or days < 1:
        raise BadInput("--days phải là số nguyên >= 1")
    t0 = time.perf_counter()
    streams = Streams(seed)
    ids = IdAllocator()
    bot = bot_cls(tuning, streams)
    day_sim = day_sim_cls(tuning, {}, streams, ids, days=days, allow_extended_days=True)
    mult = tuning["score"]["reputation_multiplier"]
    max_ticks_per_day = (
        int(round(tuning["gather"]["duration_s"] * tuning["tick_hz"]))
        + int(round(tuning["quan"]["duration_s"] * tuning["tick_hz"]))
        + int(tuning["shop"]["max_ticks"])
        + 120
    )

    crashes = 0
    results = []
    for target_day in range(1, days + 1):
        if day_sim.done:
            break
        try:
            bot.reset_buttons()
            day_finished = False
            for _ in range(max_ticks_per_day):
                if day_sim.done or day_sim.day > target_day:
                    break
                inp = bot.decide(day_sim)
                evs = day_sim.step(inp)
                for name, _data, _phase, ev_day in evs:
                    if name == "shop_end" and ev_day == target_day:
                        results.append({
                            "day": ev_day,
                            "earned": day_sim.earned,
                            "reputation": round(day_sim.reputation, 3),
                            "score": day_sim.earned + mult * math.floor(day_sim.reputation),
                        })
                        day_finished = True
                if day_finished:
                    break
            if not day_finished and not day_sim.done and day_sim.day == target_day:
                raise RuntimeError(f"Ngày {target_day} không hoàn tất trong {max_ticks_per_day} tick")
        except Exception as exc:
            crashes += 1
            sys.stderr.write(f"soak crash ở Ngày {target_day}: {exc}\n")
            if target_day < days and not day_sim.done:
                try:
                    day_sim.day = target_day
                    day_sim._start_day([])
                except Exception:
                    break
            else:
                break

    duration_s = round(time.perf_counter() - t0, 3)
    return {
        "days": days,
        "days_completed": day_sim.days_completed,
        "crashes": crashes,
        "results": results,
        "duration_s": duration_s,
    }


def write_json_atomic(path: str, data: dict):
    abs_path = os.path.abspath(path)
    parent = os.path.dirname(abs_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".soak-", suffix=".tmp", dir=parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, abs_path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def main(argv=None) -> int:
    p = _Parser(prog="chonoi.soak")
    p.add_argument("--seed", required=True, type=_int("seed"))
    p.add_argument("--days", required=True, type=_int("days"))
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    try:
        if a.days < 1:
            raise BadInput("--days phải >= 1")
        if not a.out or not a.out.strip():
            raise BadInput("--out không được rỗng")
        contract = load_contract()
        tuning = contract["tuning"]
    except BadInput as e:
        sys.stderr.write(f"đầu vào sai: {e}\n")
        return 2
    try:
        report = run_soak(tuning, a.seed, a.days)
        write_json_atomic(a.out, report)
    except BadInput as e:
        sys.stderr.write(f"đầu vào sai: {e}\n")
        return 2
    except OSError as e:
        sys.stderr.write(f"lỗi ghi: {e}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

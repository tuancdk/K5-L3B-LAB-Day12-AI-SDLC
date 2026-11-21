"""Buổi sáng — Lặn & Hái (`gather`), luật Phase 1–3 (Test Contract v1.1/v1.2, Issue #13/#14/#19).

Mặt cắt dòng sông nhìn NGANG: vị trí `[x, d]` (x sang phải, `d` độ sâu hướng xuống, d = 0 là mặt nước).
`move = [x, d]`: thành phần thứ hai DƯƠNG = bơi xuống. Hướng mặt là góc từ +x, dương = xuống.
"""

from fractions import Fraction
import math

from ..ids import id_key, sort_by_id
from ..inventory import hold_to_items
from . import monsters
from .ramp import ramp_velocity

AXES = ("x", "d")
DEFAULT_FRESHNESS = {
    "initial": 100,
    "gather_decay_per_s": 0.5,
    "quan_decay_per_s": 0.25,
    "spoiled_below": 30,
}


def _to_fraction(value) -> Fraction:
    if isinstance(value, Fraction):
        return value
    return Fraction(str(value))


def _export_fresh(value: Fraction):
    if value.denominator == 1:
        return int(value)
    return round(float(value), 4)


def _reflect_axis(pos: float, delta: float, lo: float, hi: float):
    """Dịch chuyển theo 1 trục trong [lo, hi], phản xạ phần dư khi chạm mép."""
    nxt = pos + delta
    flipped = False
    for _ in range(8):
        if nxt < lo:
            nxt = 2.0 * lo - nxt
            delta = -delta
            flipped = not flipped
        elif nxt > hi:
            nxt = 2.0 * hi - nxt
            delta = -delta
            flipped = not flipped
        else:
            break
    if nxt <= lo and delta < 0:
        nxt = lo
        delta = -delta
        flipped = not flipped
    elif nxt >= hi and delta > 0:
        nxt = hi
        delta = -delta
        flipped = not flipped
    return max(lo, min(hi, nxt)), delta, flipped


class GatherSim:
    mode = "gather"
    phase = "gather"

    def __init__(self, tuning, scenario, streams, ids, day_ctx=None):
        t = tuning["gather"]
        self.t = t
        self.tick_hz = tuning["tick_hz"]
        self.day_ctx = day_ctx
        self.day = int(day_ctx["day"]) if day_ctx else 1
        self.phase_tick = 0
        self.rng = streams
        self.ids = ids
        oxygen_max_s = t["oxygen_max_s"]
        hp_max = t["hp_max"]
        if day_ctx and "shop" in tuning:
            active = day_ctx.get("active_upgrades") or {}
            upgrades = tuning["shop"]["upgrades"]
            oxy_lvl = int(active.get("oxygen", 0))
            if oxy_lvl > 0:
                oxygen_max_s = upgrades["oxygen"][oxy_lvl - 1]["oxygen_max_s"]
            hp_lvl = int(active.get("hp", 0))
            if hp_lvl > 0:
                hp_max = upgrades["hp"][hp_lvl - 1]["hp_max"]
        self.hp_max = int(hp_max)
        p = scenario.get("player", {})
        self.pos = [float(c) for c in p.get("pos", t["start_pos"])]
        self.vel = [float(c) for c in p.get("vel", [0.0, 0.0])]
        self._tgt = None
        self._ramp_left = 0
        self.heading = float(p.get("heading_deg", t["start_heading_deg"]))
        self.oxygen_max = self._ticks(oxygen_max_s)
        self.oxygen_ticks = p.get("oxygen_ticks", self.oxygen_max)
        self.hp = p.get("hp", self.hp_max)
        self.zero_oxy_ticks = p.get("zero_oxy_ticks", 0)
        self.invuln_ticks = p.get("invuln_ticks", 0)
        self.catch_cd_ticks = p.get("catch_cd_ticks", 0)
        raw_hold = list(scenario.get("hold", []))
        self.use_items = ("freshness" in tuning) or any(isinstance(x, dict) for x in raw_hold)
        self.freshness = dict(DEFAULT_FRESHNESS, **(tuning.get("freshness") or {}))
        self.hold = self._init_hold(raw_hold)
        self.time_left_ticks = scenario.get("time_left_ticks", self._ticks(t["duration_s"]))
        self.random_fish = bool(scenario.get("random_fish", True))
        # nút và đàn cá: scenario THAY THẾ danh sách mặc định; random_fish=false tắt cá mặc định và cá bơi/sinh
        src_nodes = scenario["nodes"] if "nodes" in scenario else t["nodes"]
        self.nodes = [{"id": n["id"], "kind": n["kind"], "pos": [float(c) for c in n["pos"]],
                       "regrow_ticks": n.get("regrow_ticks", 0)} for n in src_nodes]
        src_fish = scenario["fish"] if "fish" in scenario else []
        self.fish = [{"id": f["id"], "kind": f["kind"], "pos": [float(c) for c in f["pos"]],
                      "heading_deg": float(f.get("heading_deg", 0)),
                      "age_ticks": int(f.get("age_ticks", 0))} for f in src_fish]
        for coll in (self.nodes, self.fish):
            for e in coll:
                ids.reserve(e["id"])
        # v1.1: không khai `fish` và random_fish bật -> sinh fish_initial đàn ở các điểm khác nhau theo seed.
        if "fish" not in scenario and self.random_fish:
            for _ in range(int(t["fish_initial"])):
                if self._spawn_fish() is None:
                    break
        self.monsters = monsters.init_monsters(self, scenario)
        self.current_cfg = t.get("current")
        self.random_current = bool(scenario.get("random_current", True))
        self.forced_current_dir = scenario.get("current_direction")
        self.current = None
        self.money = 0
        self.earned = 0
        self.reputation = tuning["quan"]["reputation_initial"]
        self.done = False
        self.reason = None

    def _spawn_candidates(self):
        """Map loài -> các điểm sinh còn hợp lệ (cách mọi đàn đang sống > fish_spawn_clearance)."""
        t, out = self.t, {}
        clear = t["fish_spawn_clearance"]
        for kind in sorted(t["fish_spawn_depths"]):
            pts = [[float(x), float(d)] for x in t["fish_spawn_x"] for d in t["fish_spawn_depths"][kind]
                   if all(math.dist((x, d), f["pos"]) > clear for f in self.fish)]
            if pts:
                out[kind] = pts
        return out

    def _spawn_fish(self):
        """Sinh một đàn (TICKET-02 1.1): chọn loài theo fish_weights (chuẩn hóa trên loài còn điểm),
        rồi chọn đều một điểm của loài và hướng ban đầu theo seed. Trả đàn mới hoặc None."""
        if len(self.fish) >= int(self.t["fish_max"]):
            return None
        cands = self._spawn_candidates()
        if not cands:
            return None
        rng = self.rng.get("fish_spawn")
        kinds = sorted(cands)
        kind = rng.choices(kinds, weights=[self.t["fish_weights"][k] for k in kinds])[0]
        pos = rng.choice(cands[kind])
        fish = {"id": self.ids.new("F"), "kind": kind, "pos": pos,
                "heading_deg": round(rng.uniform(0, 360), 3), "age_ticks": 0}
        self.fish.append(fish)
        return fish

    def _update_fish(self, events: list):
        """Cá bơi, đổi hướng theo age_ticks và phản xạ mép; sau đó sinh đàn theo lịch fish_spawn_ticks."""
        if not self.random_fish:
            return
        t = self.t
        step_dist = float(t["fish_speed"]) / self.tick_hz
        turn_every = int(t["fish_turn_ticks"])
        x_lo, x_hi = float(t["fish_x"][0]), float(t["fish_x"][1])
        depths_map = t["fish_depths"]
        turn_rng = self.rng.get("fish_turn")

        for f in sort_by_id(self.fish):
            f["age_ticks"] += 1
            if turn_every > 0 and f["age_ticks"] % turn_every == 0:
                f["heading_deg"] = round(turn_rng.uniform(0, 360), 3)
            rad = math.radians(f["heading_deg"])
            vx = math.cos(rad) * step_dist
            vd = math.sin(rad) * step_dist
            d_lo, d_hi = float(depths_map[f["kind"]][0]), float(depths_map[f["kind"]][1])
            nx, vx2, fx = _reflect_axis(f["pos"][0], vx, x_lo, x_hi)
            nd, vd2, fd = _reflect_axis(f["pos"][1], vd, d_lo, d_hi)
            f["pos"][0], f["pos"][1] = nx, nd
            if fx or fd:
                f["heading_deg"] = math.degrees(math.atan2(vd2, vx2)) % 360

        spawn_every = int(t["fish_spawn_ticks"])
        if spawn_every > 0 and self.phase_tick % spawn_every == 0:
            fish = self._spawn_fish()
            if fish is not None:
                events.append(("fish_spawned", {"id": fish["id"], "kind": fish["kind"], "pos": list(fish["pos"])}))

    def _ticks(self, seconds) -> int:
        return int(round(seconds * self.tick_hz))

    def _init_hold(self, raw_hold: list) -> list:
        """Khởi tạo giỏ: v1.1 là mảng kind; v1.2 là mảng cá thể {id, kind, _fresh} theo thứ tự vào giỏ."""
        if not self.use_items:
            return list(raw_hold)
        init_fresh = _to_fraction(self.freshness["initial"])
        out = []
        for entry in raw_hold:
            if isinstance(entry, dict):
                kind = entry["kind"]
                fresh = _to_fraction(entry["fresh"]) if "fresh" in entry else init_fresh
                raw_id = entry.get("id")
                if raw_id and self.day == 1:
                    iid = raw_id
                    self.ids.reserve(iid)
                else:
                    iid = self.ids.new("I")
            else:
                kind = entry
                fresh = init_fresh
                iid = self.ids.new("I")
            out.append({"id": iid, "kind": kind, "_fresh": fresh})
        return out

    def export_hold_item(self, item):
        if not self.use_items:
            return item
        return {"id": item["id"], "kind": item["kind"], "fresh": _export_fresh(item["_fresh"])}

    def _add_to_hold(self, kind: str, amount: int):
        if not self.use_items:
            self.hold.extend([kind] * amount)
            return
        init_fresh = _to_fraction(self.freshness["initial"])
        for _ in range(amount):
            self.hold.append({"id": self.ids.new("I"), "kind": kind, "_fresh": init_fresh})

    def _decay_hold(self, events: list):
        """Hao độ tươi đầu bước cho hàng đã có sẵn trong giỏ; phát spoiled đúng 1 lần theo id."""
        if not self.use_items or not self.hold:
            return
        decay = _to_fraction(self.freshness["gather_decay_per_s"]) / Fraction(int(self.tick_hz))
        threshold = _to_fraction(self.freshness["spoiled_below"])
        zero = Fraction(0)
        for item in sort_by_id(self.hold):
            prev = item["_fresh"]
            nxt = prev - decay
            if nxt < zero:
                nxt = zero
            item["_fresh"] = nxt
            if prev >= threshold and nxt < threshold:
                events.append(("spoiled", {"item_id": item["id"], "kind": item["kind"], "location": "hold"}))

    # --- giao diện cho runner -------------------------------------------------
    def inventory_items(self):
        if self.use_items:
            return [self.export_hold_item(item) for item in sort_by_id(self.hold)]
        return hold_to_items(self.hold)

    def snapshot(self) -> dict:
        snap = {
            "player": {"pos": list(self.pos), "vel": list(self.vel), "heading_deg": self.heading,
                       "oxygen_ticks": self.oxygen_ticks, "oxygen_max_ticks": self.oxygen_max,
                       "hp": self.hp, "hp_max": self.hp_max, "zero_oxy_ticks": self.zero_oxy_ticks,
                       "invuln_ticks": self.invuln_ticks, "catch_cd_ticks": self.catch_cd_ticks,
                       "at_surface": self._at_surface()},
            "hold": [self.export_hold_item(item) for item in self.hold], "hold_count": len(self.hold),
            "hold_capacity": self.t["hold_capacity"],
            "nodes": [{"id": n["id"], "pos": list(n["pos"]), "kind": n["kind"],
                       "ready": n["regrow_ticks"] == 0, "regrow_ticks": n["regrow_ticks"]}
                      for n in sort_by_id(self.nodes)],
            "fish": [{"id": f["id"], "pos": list(f["pos"]), "kind": f["kind"],
                      "heading_deg": f["heading_deg"], "age_ticks": f["age_ticks"]}
                     for f in sort_by_id(self.fish)],
            "monsters": monsters.snapshot_monsters(self),
        }
        if self.current_cfg is not None:
            snap["current"] = (None if self.current is None else
                               {"direction": self.current["direction"], "ticks_left": self.current["ticks_left"]})
        return snap

    def _step_current(self, events: list):
        """Cập nhật dòng nước lũ (extension `current`, Issue #23) trước khi di chuyển."""
        if not self.current_cfg:
            return
        if self.current is not None:
            self.current["ticks_left"] -= 1
            if self.current["ticks_left"] <= 0:
                events.append(("current_end", {"direction": self.current["direction"], "reason": "elapsed"}))
                self.current = None
        if not self.random_current:
            return
        interval = int(self.current_cfg["interval_ticks"])
        duration = int(self.current_cfg["duration_ticks"])
        warning = int(self.current_cfg["warning_ticks"])
        if warning > 0 and interval > 0:
            starts_at = self.phase_tick + warning
            if starts_at >= interval and starts_at % interval == 0:
                events.append(("current_warning", {"starts_at_phase_tick": starts_at}))
        if interval > 0 and self.phase_tick % interval == 0:
            if self.forced_current_dir in (-1, 1):
                direction = int(self.forced_current_dir)
            else:
                direction = self.rng.get("current").choice([-1, 1])
            self.current = {"direction": direction, "ticks_left": duration}
            events.append(("current_start", {"direction": direction, "duration_ticks": duration}))

    def _end_current_on_phase_end(self, events: list):
        if self.current is not None:
            events.append(("current_end", {"direction": self.current["direction"], "reason": "phase_end"}))
            self.current = None

    # --- một bước (TICKET-02/03) ----------------------------------------------
    def step(self, inp):
        if self.done:
            return []
        events = []
        self.phase_tick += 1
        # 1. đồng hồ, cooldown, giảm bất tử, hồi nút và hao tươi hàng có sẵn
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        self.invuln_ticks = max(0, self.invuln_ticks - 1)
        self.catch_cd_ticks = max(0, self.catch_cd_ticks - 1)
        for n in sort_by_id(self.nodes):
            if n["regrow_ticks"] > 0:
                n["regrow_ticks"] -= 1
                if n["regrow_ticks"] == 0:
                    events.append(("node_regrown", {"node_id": n["id"]}))
        self._decay_hold(events)
        # 1.5. dòng nước lũ (nếu bật extension current) trước khi di chuyển
        self._step_current(events)
        # 2. bơi + lực dòng lũ (nếu d đầu bước >= min_depth) + chặn mép + phân vùng + oxy / ngạt / ngất
        start_d = self.pos[1]
        was_at_surface = self._at_surface()
        current_vx = (self.current["direction"] * float(self.current_cfg["speed"])
                      if self.current is not None and start_d >= float(self.current_cfg["min_depth"]) else 0.0)
        self._move(inp, current_vx)
        now_at_surface = self._at_surface()
        if was_at_surface and not now_at_surface:
            events.append(("dive", {"pos": list(self.pos)}))
        elif not was_at_surface and now_at_surface:
            events.append(("surface", {"pos": list(self.pos)}))
        if self._update_oxygen(now_at_surface, events):
            return events
        # 3. thủy quái (Cá Sấu Năm Chèo)
        if monsters.step(self, events):
            return events
        # 4. interact: bến trước, rồi hái
        if inp.pressed("interact"):
            if self._in_dock():
                self._finish("docked", events)
                return events
            if now_at_surface:
                self._gather_node(events)
        # 5. bắt cá (theo vị trí đàn cá trước khi cá bơi)
        if inp.pressed("catch"):
            if self.catch_cd_ticks == 0 and not now_at_surface:
                self._catch_fish(events)
        # 6. xét hết giờ
        if self.time_left_ticks <= 0:
            self._finish("time", events)
            return events
        # 7. nếu còn giờ: cá bơi rồi sinh cá theo lịch
        self._update_fish(events)
        return events

    def _faint(self, cause: str, events: list):
        self._end_current_on_phase_end(events)
        lost = [self.export_hold_item(item) for item in reversed(self.hold)]
        self.hold.clear()
        events.append(("faint", {"cause": cause, "lost": lost, "hp": 0}))
        self._finish("fainted", events)

    def _gather_node(self, events: list):
        radius = self.t["interact_radius"]
        candidates = [(math.dist(self.pos, n["pos"]), id_key(n["id"]), n)
                      for n in self.nodes if n["regrow_ticks"] == 0]
        candidates = [entry for entry in candidates if entry[0] <= radius]
        if not candidates:
            return
        _, _, node = min(candidates, key=lambda entry: entry[:2])
        required = int(self.t["node_yield"])
        free = int(self.t["hold_capacity"]) - len(self.hold)
        if free < required:
            events.append(("hold_full", {"action": "gather", "node_id": node["id"],
                                         "required": required, "free": free}))
            return
        self._add_to_hold(node["kind"], required)
        node["regrow_ticks"] = self._ticks(self.t["regrow_s"])
        events.append(("gather", {"node_id": node["id"], "kind": node["kind"], "amount": required}))

    def _catch_fish(self, events: list):
        radius = self.t["catch_radius"]
        candidates = [(math.dist(self.pos, f["pos"]), id_key(f["id"]), f) for f in self.fish]
        candidates = [entry for entry in candidates if entry[0] <= radius]
        if not candidates:
            return
        _, _, fish = min(candidates, key=lambda entry: entry[:2])
        required = int(self.t["fish_yield"][fish["kind"]])
        free = int(self.t["hold_capacity"]) - len(self.hold)
        if free < required:
            events.append(("hold_full", {"action": "catch", "fish_id": fish["id"],
                                         "required": required, "free": free}))
            return
        self._add_to_hold(fish["kind"], required)
        self.fish.remove(fish)
        self.catch_cd_ticks = self._ticks(self.t["catch_cooldown_s"])
        events.append(("fish_caught", {"fish_id": fish["id"], "kind": fish["kind"], "yield": required}))

    def _update_oxygen(self, at_surface: bool, events: list) -> bool:
        """Cập nhật oxy, ngạt và ngất theo vị trí cuối bước. Trả True nếu người chơi ngất."""
        if at_surface:
            self.oxygen_ticks = min(self.oxygen_max, self.oxygen_ticks + int(self.t["oxygen_refill_per_tick"]))
            self.zero_oxy_ticks = 0
            return False
        prev_oxy = self.oxygen_ticks
        self.oxygen_ticks = max(0, self.oxygen_ticks - 1)
        if prev_oxy > 0 and self.oxygen_ticks == 0:
            events.append(("oxygen_empty", {"oxygen_ticks": 0}))
        if self.oxygen_ticks == 0:
            self.zero_oxy_ticks += 1
            if self.zero_oxy_ticks >= int(self.t["choke_interval_ticks"]):
                self.zero_oxy_ticks = 0
                self.hp = max(0, self.hp - 1)
                events.append(("choke", {"hp": self.hp}))
                if self.hp <= 0:
                    self._faint("choke", events)
                    return True
        return False

    # --- tiện ích ---------------------------------------------------------------
    def _at_surface(self) -> bool:
        return self.pos[1] <= self.t["surface_depth"]

    def _in_dock(self) -> bool:
        return math.dist(self.pos, self.t["dock_pos"]) <= self.t["dock_radius"]

    def _finish(self, reason, events):
        self._end_current_on_phase_end(events)
        self.done = True
        self.reason = reason
        events.append(("gather_end", {"reason": reason, "inventory": {"items": self.inventory_items()}}))

    def _move(self, inp, current_vx: float = 0.0):
        speed = self.t["swim_speed"]
        mx, md = inp.move
        self.vel = ramp_velocity(self, (mx * speed, md * speed), int(self.t["ramp_max_ticks"]))
        if (mx, md) != (0.0, 0.0):
            self.heading = math.degrees(math.atan2(md, mx)) % 360
        b = self.t["bounds"]
        extras = (current_vx, 0.0)
        for i, axis in enumerate(AXES):
            self.pos[i] += (self.vel[i] + extras[i]) / self.tick_hz
            lo, hi = b[axis]
            if self.pos[i] <= lo:
                self.pos[i] = lo
                self.vel[i] = max(0.0, self.vel[i])
            elif self.pos[i] >= hi:
                self.pos[i] = hi
                self.vel[i] = min(0.0, self.vel[i])

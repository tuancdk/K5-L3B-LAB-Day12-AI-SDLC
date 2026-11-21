"""Thủy quái buổi sáng — Cá Sấu Năm Chèo (TICKET-02, Test Contract v1.1, Issue #14).

Chế độ hoạt động:
  - patrol: tuần tra giữa các waypoint với patrol_speed; tới nơi đổi mục tiêu cho bước sau.
  - chase: khi người chơi ở d >= depths[0] và cách <= detect_radius, đuổi với chase_speed;
           về patrol khi cách > exit_radius hoặc người chơi lên d < depths[0].
  - recoil: sau khi gây hit, lùi recoil_ticks bước (tính từ bước sau), mỗi bước recoil_dist / recoil_ticks,
            theo hướng xa người chơi chốt lúc chạm (trùng tâm dùng +x), chặn mép, không gây hit;
            hết recoil về patrol và chỉ xét phát hiện/chạm từ bước kế.
"""

import math

from ..ids import id_key, sort_by_id


def init_monsters(sim, scenario: dict) -> list:
    """Khởi tạo danh sách thủy quái từ scenario hoặc spawns[] mặc định theo Ngày hiện tại."""
    cfg = sim.t.get("monsters") or {}
    if "monsters" in scenario:
        raw_list = scenario["monsters"]
    else:
        raw_list = [s for s in cfg.get("spawns", []) if int(s.get("from_day", 1)) <= sim.day]
    out = []
    for raw in raw_list:
        waypoints = [[float(wp[0]), float(wp[1])] for wp in raw["waypoints"]]
        pos = [float(c) for c in raw["pos"]] if "pos" in raw else list(waypoints[0])
        recoil_dir = raw.get("recoil_dir")
        out.append({
            "id": raw["id"],
            "kind": raw.get("kind", "ca_sau"),
            "pos": pos,
            "waypoints": waypoints,
            "target_idx": int(raw.get("target_idx", 1 if len(waypoints) > 1 else 0)),
            "state": raw.get("state", "patrol"),
            "state_ticks_left": int(raw.get("state_ticks_left", 0)),
            "recoil_dir": [float(c) for c in recoil_dir] if recoil_dir is not None else None,
        })
        sim.ids.reserve(raw["id"])
    return out


def snapshot_monsters(sim) -> list:
    return [
        {
            "id": m["id"],
            "kind": m["kind"],
            "pos": list(m["pos"]),
            "waypoints": [list(wp) for wp in m["waypoints"]],
            "target_idx": m["target_idx"],
            "state": m["state"],
            "state_ticks_left": m["state_ticks_left"],
            "recoil_dir": list(m["recoil_dir"]) if m["recoil_dir"] is not None else None,
        }
        for m in sort_by_id(sim.monsters)
    ]


def _clamp_pos(pos: list, bounds: dict, depths: list):
    x_lo, x_hi = bounds["x"]
    d_lo = max(bounds["d"][0], depths[0])
    d_hi = min(bounds["d"][1], depths[1])
    pos[0] = max(float(x_lo), min(float(x_hi), pos[0]))
    pos[1] = max(float(d_lo), min(float(d_hi), pos[1]))


def _move_toward(pos: list, target: list, step_len: float) -> bool:
    """Di chuyển pos về phía target tối đa step_len. Trả True nếu đã chạm tới target."""
    dx = target[0] - pos[0]
    dd = target[1] - pos[1]
    dist = math.hypot(dx, dd)
    if dist <= step_len + 1e-9:
        pos[0], pos[1] = float(target[0]), float(target[1])
        return True
    pos[0] += dx / dist * step_len
    pos[1] += dd / dist * step_len
    return False


def step(sim, events: list) -> bool:
    """Cập nhật toàn bộ thủy quái và xét tối đa một cú chạm trong bước. Trả True nếu người chơi ngất."""
    cfg = sim.t.get("monsters")
    if not cfg or not sim.monsters:
        return False
    species_map = cfg["species"]
    bounds = sim.t["bounds"]
    eligible = []

    for m in sort_by_id(sim.monsters):
        spec = species_map[m["kind"]]
        depths = spec["depths"]
        state = m["state"]

        if state == "recoil":
            step_len = float(spec["recoil_dist"]) / int(spec["recoil_ticks"])
            rdir = m["recoil_dir"] or [1.0, 0.0]
            m["pos"][0] += rdir[0] * step_len
            m["pos"][1] += rdir[1] * step_len
            _clamp_pos(m["pos"], bounds, depths)
            m["state_ticks_left"] = max(0, m["state_ticks_left"] - 1)
            if m["state_ticks_left"] == 0:
                m["state"] = "patrol"
                m["recoil_dir"] = None
            continue

        if state == "stunned":
            m["state_ticks_left"] = max(0, m["state_ticks_left"] - 1)
            if m["state_ticks_left"] == 0:
                m["state"] = "patrol"
            continue

        player_in_zone = sim.pos[1] >= depths[0]
        dist_to_player = math.dist(m["pos"], sim.pos)
        if state == "patrol":
            if player_in_zone and dist_to_player <= spec["detect_radius"]:
                m["state"] = "chase"
        elif state == "chase":
            if (not player_in_zone) or dist_to_player > spec["exit_radius"]:
                m["state"] = "patrol"

        if m["state"] == "chase":
            _move_toward(m["pos"], sim.pos, float(spec["chase_speed"]) / sim.tick_hz)
            _clamp_pos(m["pos"], bounds, depths)
        else:
            wp = m["waypoints"][m["target_idx"]]
            arrived = _move_toward(m["pos"], wp, float(spec["patrol_speed"]) / sim.tick_hz)
            _clamp_pos(m["pos"], bounds, depths)
            if arrived and len(m["waypoints"]) > 1:
                m["target_idx"] = (m["target_idx"] + 1) % len(m["waypoints"])

        eligible.append(m)

    if sim.invuln_ticks > 0 or not eligible:
        return False

    hit_cands = []
    for m in eligible:
        spec = species_map[m["kind"]]
        if sim.pos[1] < spec["depths"][0]:
            continue
        dist = math.dist(m["pos"], sim.pos)
        if dist <= spec["hit_radius"]:
            hit_cands.append((dist, id_key(m["id"]), m))

    if not hit_cands:
        return False

    _, _, hitter = min(hit_cands, key=lambda entry: entry[:2])
    spec = species_map[hitter["kind"]]
    sim.hp = max(0, sim.hp - 1)
    loss_count = math.floor(len(sim.hold) * float(cfg["loss_ratio"]))
    lost = [sim.hold.pop() for _ in range(loss_count)]
    sim.invuln_ticks = int(cfg["invuln_ticks"])
    events.append(("monster_hit", {
        "monster_id": hitter["id"],
        "hp": sim.hp,
        "lost": lost,
        "pos": list(sim.pos),
    }))

    dx = hitter["pos"][0] - sim.pos[0]
    dd = hitter["pos"][1] - sim.pos[1]
    dlen = math.hypot(dx, dd)
    hitter["state"] = "recoil"
    hitter["state_ticks_left"] = int(spec["recoil_ticks"])
    hitter["recoil_dir"] = [dx / dlen, dd / dlen] if dlen > 0 else [1.0, 0.0]

    if sim.hp <= 0:
        sim._faint("monster", events)
        return True
    return False

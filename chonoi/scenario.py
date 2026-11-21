import json
import math
from collections import Counter

from .contract import FISH_KINDS, NODE_KINDS, validate_day_plans
from .errors import BadInput
from .inventory import KINDS_P1, validate_items

GATHER_KEYS = {"player", "hold", "nodes", "fish", "random_fish", "time_left_ticks", "monsters"}
GATHER_PLAYER_KEYS = {"pos", "vel", "heading_deg", "hp", "oxygen_ticks", "zero_oxy_ticks",
                      "invuln_ticks", "catch_cd_ticks"}
QUAN_PLAYER_KEYS = {"pos", "vel"}
QUAN_KEYS = {"player", "stock", "hand", "stoves", "tables", "customers", "random_customers",
             "reputation", "time_left_ticks"}
CUSTOMER_KEYS = {"id", "table_id", "dish_id", "order_tick", "state", "patience_ticks_left",
                 "eat_ticks_left", "order_status", "reserved", "base_price", "tip"}
DISH_KEYS = {"order_id", "dish_id", "base_price"}


def _check_ids(name, arr):
    if not isinstance(arr, list):
        raise BadInput(f"{name} phải là mảng")
    seen = set()
    for e in arr:
        if not isinstance(e, dict) or not isinstance(e.get("id"), str) or not e["id"]:
            raise BadInput(f"{name}: mỗi phần tử cần id (chuỗi khác rỗng)")
        if e["id"] in seen:
            raise BadInput(f"{name}: id trùng {e['id']}")
        seen.add(e["id"])


def read_scenario_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        raise BadInput(f"không đọc được scenario {path}: {e}")


def load_scenario(path, mode: str, tuning: dict, *, inventory=None, extensions=(), data=None) -> dict:
    """`data`: JSON đã đọc sẵn (v1.2: headless đổi mảng cá thể sang dạng loại trước khi kiểm)."""
    if path is None and data is None:
        return {}
    if data is None:
        data = read_scenario_json(path)
    if mode == "day":
        return _load_day(data, tuning, extensions)
    if not isinstance(data, dict) or not set(data) <= {"gather", "quan"}:
        raise BadInput("scenario chỉ được có khối 'gather' hoặc 'quan'")
    if set(data) - {mode}:
        raise BadInput(f"khối sai mode: chạy --mode {mode} chỉ nhận khối '{mode}'")
    block = data.get(mode, {})
    _validate_block(block, mode, tuning, inventory=inventory, extensions=extensions)
    return block


DAY_KEYS = {"money", "earned", "reputation", "upgrades", "day_plan"}


def _load_day(data, tuning, extensions):
    if not isinstance(data, dict) or not set(data) <= {"day", "gather", "quan"}:
        raise BadInput("scenario của day chỉ có khối 'day', 'gather', 'quan'")
    d = data.get("day", {})
    if not isinstance(d, dict) or set(d) - DAY_KEYS:
        raise BadInput(f"khối day chỉ có {sorted(DAY_KEYS)}")
    for key in ("money", "earned"):
        if key in d:
            _nonneg_int(f"day.{key}", d[key])
    if {"money", "earned"} <= d.keys() and d["money"] > d["earned"]:
        raise BadInput("day: cần 0 <= money <= earned")
    q = tuning["quan"]
    if "reputation" in d and not (_num(d["reputation"]) and q["reputation_min"] <= d["reputation"] <= q["reputation_max"]):
        raise BadInput("day.reputation ngoài [reputation_min, reputation_max]")
    ups = d.get("upgrades", {})
    if not isinstance(ups, dict):
        raise BadInput("day.upgrades phải là object")
    for k, v in ups.items():
        levels = tuning["shop"]["upgrades"].get(k)
        if levels is None:
            raise BadInput(f"day.upgrades: nâng cấp lạ {k}")
        if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= len(levels):
            raise BadInput(f"day.upgrades.{k} phải trong [0, {len(levels)}]")
    validate_day_plans(d.get("day_plan", []), tuning)
    gather = dict(tuning["gather"])
    for key, stat in (("oxygen", "oxygen_max_s"), ("hp", "hp_max")):
        level = ups.get(key, 0)
        if level:
            gather[stat] = tuning["shop"]["upgrades"][key][level - 1][stat]
    _validate_block(data.get("gather", {}), "gather", dict(tuning, gather=gather), extensions=extensions)

    quan = data.get("quan", {})
    if isinstance(quan, dict) and {"stock", "reputation"} & quan.keys():
        raise BadInput("chạy day cấm quan.stock và quan.reputation (dùng gather.hold / day.reputation)")
    _validate_block(quan, "quan", tuning, defer_stock=True)
    return data


def _validate_block(block, mode, tuning, *, inventory=None, extensions=(), defer_stock=False):
    if not isinstance(block, dict):
        raise BadInput(f"khối {mode} phải là object")
    dur = round(tuning[mode]["duration_s"] * tuning["tick_hz"])
    if "time_left_ticks" in block:
        t = block["time_left_ticks"]
        if isinstance(t, bool) or not isinstance(t, int) or not (1 <= t <= dur):
            raise BadInput(f"time_left_ticks phải là số nguyên trong [1, {dur}]")
    allowed = GATHER_KEYS if mode == "gather" else QUAN_KEYS
    if mode == "gather" and "handbook" in extensions:
        allowed = allowed | {"ca_ho", "random_ho"}
    extra = set(block) - allowed
    if extra:
        raise BadInput(f"trường lạ/chưa hỗ trợ trong {mode}: {sorted(extra)}")
    if mode == "gather":
        _validate_gather(block, tuning, extensions)
    else:
        validate_quan(block, tuning, inventory, defer_stock=defer_stock)


def _num(v):
    return type(v) is int or (isinstance(v, float) and math.isfinite(v))


def _nonneg_int(name, v):
    if isinstance(v, bool) or not isinstance(v, int) or v < 0:
        raise BadInput(f"{name} phải là số nguyên không âm")


def _pos(name, pos, bounds, axes=("x", "d")):
    if not (isinstance(pos, list) and len(pos) == 2 and all(_num(c) for c in pos)):
        raise BadInput(f"{name} phải là [{axes[0]}, {axes[1]}]")
    for c, axis in zip(pos, axes):
        lo, hi = bounds[axis]
        if not (lo <= c <= hi):
            raise BadInput(f"{name} nằm ngoài vùng nước ({axis} ∈ [{lo}, {hi}])")


def _validate_gather(b, tuning, extensions):
    g = tuning["gather"]
    bounds = g["bounds"]
    for arr in ("nodes", "fish", "monsters"):
        if arr in b:
            _check_ids(arr, b[arr])
    if "random_fish" in b and not isinstance(b["random_fish"], bool):
        raise BadInput("random_fish phải là boolean")
    if "random_ho" in b and not isinstance(b["random_ho"], bool):
        raise BadInput("random_ho phải là boolean")
    if "hold" in b:
        h = b["hold"]
        if not isinstance(h, list) or any(k not in KINDS_P1 for k in h):
            raise BadInput("hold phải là mảng id nguyên liệu hợp lệ")
        if len(h) > g["hold_capacity"]:
            raise BadInput("hold vượt sức chứa")
    p = b.get("player", {})
    if not isinstance(p, dict):
        raise BadInput("player phải là object")
    allowed = GATHER_PLAYER_KEYS | {"attack_cd_ticks"} if "weapon" in extensions else GATHER_PLAYER_KEYS
    extra = set(p) - allowed
    if extra:
        raise BadInput(f"trường lạ/chưa hỗ trợ trong gather.player: {sorted(extra)}")
    if "pos" in p:
        _pos("player.pos", p["pos"], bounds)
    if "vel" in p and not (isinstance(p["vel"], list) and len(p["vel"]) == 2 and all(_num(c) for c in p["vel"])):
        raise BadInput("player.vel phải là [x, d]")
    if "heading_deg" in p and not _num(p["heading_deg"]):
        raise BadInput("player.heading_deg phải là số")
    for key in ("invuln_ticks", "catch_cd_ticks", "attack_cd_ticks", "zero_oxy_ticks", "oxygen_ticks", "hp"):
        if key in p:
            _nonneg_int(f"player.{key}", p[key])
    omax = round(g["oxygen_max_s"] * tuning["tick_hz"])
    if "oxygen_ticks" in p and p["oxygen_ticks"] > omax:
        raise BadInput("player.oxygen_ticks vượt oxy tối đa")
    if "hp" in p and not (1 <= p["hp"] <= g["hp_max"]):
        raise BadInput("player.hp phải trong [1, hp_max]")
    if "zero_oxy_ticks" in p:
        pos = p.get("pos", g["start_pos"])
        oxy = p.get("oxygen_ticks", omax)
        if p["zero_oxy_ticks"] > 59:
            raise BadInput("player.zero_oxy_ticks phải trong [0, 59]")
        if p["zero_oxy_ticks"] > 0 and not (oxy == 0 and pos[1] > g["surface_depth"]):
            raise BadInput("player.zero_oxy_ticks > 0 chỉ khi oxy = 0 và đang dưới nước")
    for n in b.get("nodes", []):
        if n.get("kind") not in NODE_KINDS:
            raise BadInput(f"nodes.{n['id']}: kind phải là một trong {NODE_KINDS}")
        _pos(f"nodes.{n['id']}.pos", n.get("pos"), bounds)
        if n["pos"][1] != 0:
            raise BadInput(f"nodes.{n['id']}: nút hái nằm ở mặt nước (d = 0)")
        if "regrow_ticks" in n:
            _nonneg_int(f"nodes.{n['id']}.regrow_ticks", n["regrow_ticks"])
    for f in b.get("fish", []):
        if f.get("kind") not in FISH_KINDS:
            raise BadInput(f"fish.{f['id']}: kind phải là một trong {FISH_KINDS}")
        _pos(f"fish.{f['id']}.pos", f.get("pos"), bounds)
        lo, hi = g["fish_depths"][f["kind"]]
        if not lo <= f["pos"][1] <= hi:
            raise BadInput(f"fish.{f['id']}: độ sâu phải trong [{lo}, {hi}]")
        _nonneg_int(f"fish.{f['id']}.age_ticks", f.get("age_ticks", 0))
        if "heading_deg" in f and not _num(f["heading_deg"]):
            raise BadInput(f"fish.{f['id']}.heading_deg phải là số")


    for monster in b.get("monsters", []):
        _validate_monster(monster, g)


def _validate_monster(monster, gather):
    name = f"gather.monsters.{monster['id']}"
    kind = monster.get("kind")
    config = gather.get("monsters")
    species = config.get("species") if isinstance(config, dict) else None
    if not isinstance(species, dict) or not isinstance(kind, str) or kind not in species:
        raise BadInput(f"{name}.kind phải thuộc monsters.species")
    bounds = dict(gather["bounds"], d=species[kind]["depths"])
    _pos(f"{name}.pos", monster.get("pos"), bounds)
    waypoints = monster.get("waypoints")
    if not isinstance(waypoints, list) or len(waypoints) != 2:
        raise BadInput(f"{name}.waypoints phải có đúng 2 điểm")
    for i, point in enumerate(waypoints):
        _pos(f"{name}.waypoints[{i}]", point, bounds)
    target = monster.get("target_idx", 1)
    if type(target) is not int or target not in (0, 1):
        raise BadInput(f"{name}.target_idx phải là 0 hoặc 1")
    state = monster.get("state", "patrol")
    if state not in ("patrol", "chase", "recoil", "stunned"):
        raise BadInput(f"{name}.state không hợp lệ")
    ticks = monster.get("state_ticks_left", 0)
    _nonneg_int(f"{name}.state_ticks_left", ticks)
    if state in ("recoil", "stunned") and ticks == 0:
        raise BadInput(f"{name}.state_ticks_left phải dương khi {state}")
    if state == "recoil":
        direction = monster.get("recoil_dir")
        if (not isinstance(direction, list) or len(direction) != 2
                or not all(_num(c) and -1 <= c <= 1 for c in direction)
                or not math.isclose(math.hypot(*direction), 1, abs_tol=1e-6)):
            raise BadInput(f"{name}.recoil_dir phải là vector đơn vị")


def validate_quan(b, tuning, inventory, *, defer_stock=False):
    q = tuning["quan"]
    if "random_customers" in b and not isinstance(b["random_customers"], bool):
        raise BadInput("quan.random_customers phải là boolean")
    if "reputation" in b and not _num(b["reputation"]):
        raise BadInput("quan.reputation phải là số hữu hạn")
    for arr in ("stoves", "tables", "customers"):
        if arr in b:
            _check_ids(arr, b[arr])
    if "stock" in b:
        if inventory is not None:
            raise BadInput("vừa có quan.stock vừa có --inventory")
        validate_items(b["stock"])
    stock = inventory if inventory is not None else b.get("stock", {})
    if defer_stock:
        stock = None
    p = b.get("player", {})
    if not isinstance(p, dict) or set(p) - QUAN_PLAYER_KEYS:
        raise BadInput("quan.player chỉ có pos và vel")
    qb = q["bounds"]
    if "pos" in p:
        _pos("player.pos", p["pos"], qb, axes=("x", "z"))
    if "vel" in p and not (isinstance(p["vel"], list) and len(p["vel"]) == 2 and all(_num(c) for c in p["vel"])):
        raise BadInput("player.vel phải là [x, z]")
    for arr in ("stoves", "tables"):
        known = {item["id"] for item in q[arr]}
        for item in b.get(arr, []):
            name = f"quan.{arr}.{item['id']}"
            if item["id"] not in known:
                raise BadInput(f"{name}: id không có trong contract")
            if "pos" in item:
                _pos(f"{name}.pos", item["pos"], qb, axes=("x", "z"))

    customers = {c["id"]: c for c in b.get("customers", [])}
    tables = {table["id"] for table in q["tables"]}
    _validate_reservations(customers, tables, tuning["menu"], stock)
    _validate_order_dishes(customers, b.get("stoves", []), b.get("hand"))


def _validate_reservations(customers, tables, menu, stock):
    occupied = set()
    reservations = Counter()
    for c in customers.values():
        table = c.get("table_id")
        if not isinstance(table, str) or table not in tables:
            raise BadInput(f"customers.{c['id']}: table_id phải là bàn có thật")
        if table in occupied:
            raise BadInput("hai khách cùng bàn")
        occupied.add(table)
        reservations.update(_validate_customer(c, menu))
    for kind, count in reservations.items():
        if stock is not None and count > stock.get(kind, 0):
            raise BadInput(f"tổng reserved của {kind} vượt stock")


def _validate_order_dishes(customers, stoves, hand):
    dish_counts = Counter()
    for stove in stoves:
        name = f"quan.stoves.{stove['id']}"
        state, dish = stove.get("state", "idle"), stove.get("dish")
        if state not in ("idle", "cooking", "ready"):
            raise BadInput(f"{name}.state phải là idle, cooking hoặc ready")
        cook_ticks = stove.get("cook_ticks_left", 0)
        _nonneg_int(f"{name}.cook_ticks_left", cook_ticks)
        _nonneg_int(f"{name}.ready_ticks", stove.get("ready_ticks", 0))
        if state == "idle":
            if dish is not None:
                raise BadInput(f"{name}: bếp idle không được chứa món")
            continue
        if state == "cooking" and cook_ticks == 0:
            raise BadInput(f"{name}.cook_ticks_left phải dương khi cooking")
        dish_counts[_validate_dish(f"{name}.dish", dish, customers)] += 1
    if hand is not None:
        dish_counts[_validate_dish("quan.hand", hand, customers)] += 1
    for order_id, customer in customers.items():
        if customer.get("order_status") == "assigned" and dish_counts[order_id] != 1:
            raise BadInput(f"customers.{order_id}: đơn assigned phải có đúng một món ở bếp hoặc trên tay")


def _validate_customer(c, menu):
    name = f"quan.customers.{c['id']}"
    extra = c.keys() - CUSTOMER_KEYS
    if extra:
        raise BadInput(f"{name}: trường lạ {sorted(extra)}")
    state = c.get("state", "waiting")
    status = c.get("order_status", "reserved")
    if state not in ("waiting", "eating"):
        raise BadInput(f"{name}.state phải là waiting hoặc eating")
    if status not in ("reserved", "assigned", "unfulfillable", "served"):
        raise BadInput(f"{name}.order_status không hợp lệ")
    if (state == "eating") != (status == "served"):
        raise BadInput(f"{name}: khách eating phải có đơn served và ngược lại")

    dish_id = c.get("dish_id")
    if not isinstance(dish_id, str) or dish_id not in menu:
        raise BadInput(f"{name}.dish_id phải thuộc menu")
    for key in ("order_tick", "patience_ticks_left", "eat_ticks_left", "base_price", "tip"):
        if key in c:
            _nonneg_int(f"{name}.{key}", c[key])
    if state == "eating":
        if c.get("eat_ticks_left", 0) == 0:
            raise BadInput(f"{name}.eat_ticks_left phải dương khi eating")
        if not {"base_price", "tip"} <= c.keys():
            raise BadInput(f"{name}: khách eating cần khai base_price và tip")

    if "reserved" in c:
        validate_items(c["reserved"])
    if status == "reserved":
        recipe = menu[dish_id]["recipe"]
        if "reserved" in c and c["reserved"] != recipe:
            raise BadInput(f"{name}.reserved phải khớp công thức của {dish_id}")
        # Tính cả phần giữ mà Quán sẽ điền khi fixture bỏ trống trường reserved.
        return recipe
    if c.get("reserved"):
        raise BadInput(f"{name}.reserved phải rỗng khi đơn {status}")
    return {}


def _validate_dish(name, dish, customers):
    if not isinstance(dish, dict) or dish.keys() != DISH_KEYS:
        raise BadInput(f"{name} phải có đúng order_id, dish_id và base_price")
    _nonneg_int(f"{name}.base_price", dish["base_price"])
    order_id = dish["order_id"]
    if not isinstance(order_id, str) or order_id not in customers:
        raise BadInput(f"{name}.order_id phải tham chiếu đơn có thật")
    customer = customers[order_id]
    if customer.get("order_status") != "assigned":
        raise BadInput(f"{name}: món phải thuộc đơn assigned")
    if dish["dish_id"] != customer["dish_id"]:
        raise BadInput(f"{name}.dish_id không khớp đơn {order_id}")
    return order_id

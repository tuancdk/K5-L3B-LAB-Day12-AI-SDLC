import json
import math
import os
import sys

from .errors import BadInput
from .inventory import validate_items

NODE_KINDS = ("bong_dien_dien", "bong_sung", "keo_neo")
FISH_KINDS = ("ca_linh", "ca_loc", "ca_keo")

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game.contract.json")


def _num(v):
    return type(v) is int or (isinstance(v, float) and math.isfinite(v))


def _between(name, v, lo, hi):
    if not _num(v) or not (lo <= v <= hi):
        raise BadInput(f"tuning.{name} phải trong [{lo}, {hi}], đang là {v!r}")


def load_contract(path=DEFAULT_PATH) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            c = json.load(f)
    except (OSError, ValueError) as e:
        raise BadInput(f"không đọc được {path}: {e}")
    if not isinstance(c, dict):
        raise BadInput("game.contract.json phải là object")
    version = c.get("contract_version")
    if version not in ("1.1", "1.2", "1.3"):  # 1.3 (P4): thêm bench_cmd/soak_cmd, gameplay như 1.2
        raise BadInput('contract_version phải là "1.1", "1.2" hoặc "1.3"')
    if version == "1.3":
        for key in ("bench_cmd", "soak_cmd"):
            if not isinstance(c.get(key), str) or not c[key].strip():
                raise BadInput(f"contract v1.3 cần {key} (chuỗi lệnh) ở gốc game.contract.json")
    extensions = c.get("extensions", [])
    if not isinstance(extensions, list) or any(not isinstance(key, str) for key in extensions):
        raise BadInput("extensions phải là mảng id mở rộng")
    validate_tuning(c.get("tuning"), contract_version=version)
    return c


def _int_between(name, v, lo, hi):
    if isinstance(v, bool) or not isinstance(v, int) or not (lo <= v <= hi):
        raise BadInput(f"tuning.{name} phải là số nguyên trong [{lo}, {hi}], đang là {v!r}")


def _pos_in(name, pos, bounds, keys):
    if (not isinstance(pos, list) or len(pos) != 2 or not all(_num(c) for c in pos)):
        raise BadInput(f"tuning.{name} phải là [số, số]")
    for c, k in zip(pos, keys):
        lo, hi = bounds[k]
        if not (lo <= c <= hi):
            raise BadInput(f"tuning.{name} nằm ngoài vùng {k} ∈ [{lo}, {hi}]")


def _bounds(name, b, keys):
    if not isinstance(b, dict) or set(b) != set(keys):
        raise BadInput(f"tuning.{name}.bounds phải có đúng khóa {list(keys)}")
    for k in keys:
        v = b[k]
        if not (isinstance(v, list) and len(v) == 2 and all(_num(c) for c in v) and v[0] == 0 and v[1] > 0):
            raise BadInput(f"tuning.{name}.bounds.{k} phải là [0, số dương]")


def _positive_ticks(name, seconds, tick_hz):
    if not _num(seconds):
        raise BadInput(f"tuning.{name} phải là số hữu hạn")
    ticks = seconds * tick_hz
    if not _num(ticks) or round(ticks) <= 0:
        raise BadInput(f"tuning.{name} phải quy đổi thành số tick dương")


def _validate_gather(g, tick_hz):
    _between("gather.duration_s", g.get("duration_s"), 60, 600)
    _bounds("gather", g.get("bounds"), ("x", "d"))
    b = g["bounds"]
    _between("gather.dock_radius", g.get("dock_radius"), 0.5, 5)
    _between("gather.interact_radius", g.get("interact_radius"), 0.5, 5)
    _between("gather.catch_radius", g.get("catch_radius"), 0.5, 5)
    _between("gather.swim_speed", g.get("swim_speed"), 1, 10)
    _between("gather.catch_cooldown_s", g.get("catch_cooldown_s"), 0, 10)
    if g["catch_cooldown_s"]:
        _positive_ticks("gather.catch_cooldown_s", g["catch_cooldown_s"], tick_hz)
    _between("gather.oxygen_max_s", g.get("oxygen_max_s"), 10, 120)
    _int_between("gather.ramp_max_ticks", g.get("ramp_max_ticks"), 0, 6)
    _int_between("gather.hold_capacity", g.get("hold_capacity"), 4, 30)
    _int_between("gather.hp_max", g.get("hp_max"), 1, 99)
    _int_between("gather.oxygen_refill_per_tick", g.get("oxygen_refill_per_tick"), 1, 10_000)
    _int_between("gather.choke_interval_ticks", g.get("choke_interval_ticks"), 1, 10_000)
    _int_between("gather.node_yield", g.get("node_yield"), 1, 12)
    _between("gather.regrow_s", g.get("regrow_s"), 0.1, 600)
    _between("gather.surface_depth", g.get("surface_depth"), 0, 5)
    _pos_in("gather.dock_pos", g.get("dock_pos"), b, ("x", "d"))
    _pos_in("gather.start_pos", g.get("start_pos"), b, ("x", "d"))
    if not _num(g.get("start_heading_deg")):
        raise BadInput("tuning.gather.start_heading_deg phải là số")
    fy = g.get("fish_yield")
    if not isinstance(fy, dict) or set(fy) != set(FISH_KINDS):
        raise BadInput(f"tuning.gather.fish_yield phải có đủ {FISH_KINDS}")
    for k, v in fy.items():
        _int_between(f"gather.fish_yield.{k}", v, 1, g["hold_capacity"])
    nodes = g.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise BadInput("tuning.gather.nodes phải là mảng không rỗng")
    seen, kinds = set(), set()
    for n in nodes:
        if not isinstance(n, dict) or not isinstance(n.get("id"), str) or n["id"] in seen:
            raise BadInput("tuning.gather.nodes: mỗi nút cần id duy nhất")
        seen.add(n["id"])
        if n.get("kind") not in NODE_KINDS:
            raise BadInput(f"tuning.gather.nodes.{n['id']}: kind phải thuộc {NODE_KINDS}")
        kinds.add(n["kind"])
        _pos_in(f"gather.nodes.{n['id']}.pos", n.get("pos"), b, ("x", "d"))
        if n["pos"][1] != 0:
            raise BadInput(f"tuning.gather.nodes.{n['id']}: nút hái nằm ở mặt nước (d = 0)")
    if kinds != set(NODE_KINDS):
        raise BadInput(f"tuning.gather.nodes phải có ít nhất một nút mỗi loại {NODE_KINDS}")
    # v1.1: fish_initial là SỐ đàn đầu ca; cá sinh theo fish_spawn_x/fish_spawn_depths (TICKET-02 mục 1.1).
    _int_between("gather.fish_max", g.get("fish_max"), 1, 100)
    _int_between("gather.fish_initial", g.get("fish_initial"), 0, g["fish_max"])
    _between("gather.fish_speed", g.get("fish_speed"), 0, 10)
    _int_between("gather.fish_turn_ticks", g.get("fish_turn_ticks"), 1, 100_000)
    _int_between("gather.fish_spawn_ticks", g.get("fish_spawn_ticks"), 1, 100_000)
    _between("gather.fish_spawn_clearance", g.get("fish_spawn_clearance"), 0, 100)
    for key in ("fish_depths", "fish_spawn_depths", "fish_weights"):
        m = g.get(key)
        if not isinstance(m, dict) or set(m) != set(FISH_KINDS):
            raise BadInput(f"tuning.gather.{key} phải là map đủ {FISH_KINDS}")
    for kind in FISH_KINDS:
        depths = g["fish_depths"][kind]
        if (not isinstance(depths, list) or len(depths) != 2 or not all(_num(d) for d in depths)
                or not g["surface_depth"] < depths[0] <= depths[1] <= b["d"][1]):
            raise BadInput(f"tuning.gather.fish_depths.{kind} không hợp lệ")
        points = g["fish_spawn_depths"][kind]
        if not isinstance(points, list) or not points or any(
                not _num(d) or not depths[0] <= d <= depths[1] for d in points):
            raise BadInput(f"tuning.gather.fish_spawn_depths.{kind} ngoài dải độ sâu loài")
        weight = g["fish_weights"][kind]
        if not _num(weight) or not 0 < weight <= sys.float_info.max:
            raise BadInput(f"tuning.gather.fish_weights.{kind} phải dương và hữu hạn")
    if sum(float(weight) for weight in g["fish_weights"].values()) > sys.float_info.max:
        raise BadInput("tổng tuning.gather.fish_weights phải hữu hạn")
    xs = g.get("fish_spawn_x")
    if not isinstance(xs, list) or not xs or not all(_num(x) and b["x"][0] <= x <= b["x"][1] for x in xs):
        raise BadInput("tuning.gather.fish_spawn_x phải chứa điểm trong biên x")
    _validate_monster_depths(g)


def _validate_monster_depths(gather):
    monsters = gather.get("monsters")
    species = monsters.get("species") if isinstance(monsters, dict) else None
    if not isinstance(species, dict) or not species:
        raise BadInput("tuning.gather.monsters.species phải là map loài")
    low, high = gather["bounds"]["d"]
    for kind, config in species.items():
        depths = config.get("depths") if isinstance(config, dict) else None
        if (not isinstance(depths, list) or len(depths) != 2 or not all(_num(d) for d in depths)
                or not low <= depths[0] <= depths[1] <= high):
            raise BadInput(f"tuning.gather.monsters.species.{kind}.depths không hợp lệ")


def _validate_furniture(q, key):
    furniture = q.get(key)
    if not isinstance(furniture, list):
        raise BadInput(f"tuning.quan.{key} phải là mảng")
    seen = set()
    for item in furniture:
        item_id = item.get("id") if isinstance(item, dict) else None
        if not isinstance(item_id, str) or not item_id or item_id in seen:
            raise BadInput(f"tuning.quan.{key}: mỗi phần tử cần id khác rỗng và duy nhất")
        seen.add(item_id)
        _pos_in(f"quan.{key}.{item_id}.pos", item.get("pos"), q["bounds"], ("x", "z"))


def _validate_quan(q, tick_hz):
    _between("quan.duration_s", q.get("duration_s"), 60, 600)
    _bounds("quan", q.get("bounds"), ("x", "z"))
    _between("quan.patience_s", q.get("patience_s"), 20, 180)
    _between("quan.walk_speed", q.get("walk_speed"), 1, 10)
    _between("quan.interact_radius", q.get("interact_radius"), 0.5, 5)
    _int_between("quan.ramp_max_ticks", q.get("ramp_max_ticks", 6), 0, 6)
    _between("quan.eat_s", q.get("eat_s"), 0.1, 600)
    _between("quan.customer_interval_s", q.get("customer_interval_s"), 0.1, 600)
    duration_ticks = round(q["duration_s"] * tick_hz)
    _int_between("quan.first_customer_tick", q.get("first_customer_tick"), 1, duration_ticks - 1)
    if not (_num(q.get("tip_rate")) and q["tip_rate"] > 0 and _num(q.get("left_reputation_delta"))
            and q["left_reputation_delta"] < 0):
        raise BadInput("tip_rate phải > 0 và left_reputation_delta phải < 0")
    ratio = q.get("tip_min_patience_ratio")
    if not (_num(ratio) and 0 < ratio <= 1):
        raise BadInput("quan.tip_min_patience_ratio phải thuộc (0, 1]")
    if not (_num(q.get("tip_reputation")) and q["tip_reputation"] > 0):
        raise BadInput("quan.tip_reputation phải > 0")
    if q.get("burn_s") is not None:
        raise BadInput("burn_s phải là null trong lõi (mở rộng burn chưa bật)")
    for key in ("stoves", "tables"):
        _validate_furniture(q, key)
    carry_limit = q.get("carry_limit")
    if type(carry_limit) is not int or carry_limit < 1:
        raise BadInput("tuning.quan.carry_limit phải là số nguyên >= 1")
    lower, upper = q.get("reputation_min"), q.get("reputation_max")
    if not (_num(lower) and _num(upper) and lower <= upper):
        raise BadInput("tuning.quan cần reputation_min <= reputation_max")
    _between("quan.reputation_initial", q.get("reputation_initial"), lower, upper)


def _validate_menu(menu, tick_hz):
    if len(menu) != 6:
        raise BadInput("tuning.menu phải có đúng 6 món")
    for dish_id, d in menu.items():
        if not isinstance(d, dict):
            raise BadInput(f"tuning.menu.{dish_id} phải là object")
        price = d.get("price")
        if type(price) is not int or price <= 0:
            raise BadInput(f"tuning.menu.{dish_id}.price phải là số nguyên dương")
        _positive_ticks(f"menu.{dish_id}.cook_s", d.get("cook_s"), tick_hz)
        recipe = d.get("recipe")
        items = validate_items(recipe)
        if not items or len(items) != len(recipe):
            raise BadInput(f"tuning.menu.{dish_id}.recipe cần nguyên liệu với số lượng dương")


def plan_ingredients(tuning, dishes):
    out = {}
    for dish, servings in dishes.items():
        if dish not in tuning["menu"]:
            raise BadInput(f"day_plan: món lạ {dish}")
        for kind, amount in tuning["menu"][dish]["recipe"].items():
            out[kind] = out.get(kind, 0) + amount * servings
    return dict(sorted(out.items()))


def validate_day_plans(plans, tuning, *, complete=False):
    if not isinstance(plans, list):
        raise BadInput("day_plan phải là mảng")
    seen = set()
    for entry in plans:
        day = entry.get("day") if isinstance(entry, dict) else None
        if type(day) is not int or not 1 <= day <= 5 or day in seen:
            raise BadInput("day_plan cần số Ngày duy nhất trong [1, 5]")
        seen.add(day)
        dishes = entry.get("dishes")
        if not isinstance(dishes, dict) or not dishes or any(type(n) is not int or n <= 0 for n in dishes.values()):
            raise BadInput(f"day_plan[{day}].dishes phải là map món -> số nguyên dương")
        expected = plan_ingredients(tuning, dishes)
        if complete or "ingredients" in entry:
            ingredients = entry.get("ingredients")
            validate_items(ingredients)
            if ingredients != expected:
                raise BadInput(f"day_plan[{day}].ingredients khác tổng công thức")
    if complete and len(seen) != 5:
        raise BadInput("tuning.day_plan phải có đúng 5 Ngày")


def _validate_shop(shop, tick_hz):
    if not isinstance(shop, dict) or not isinstance(shop.get("upgrades"), dict):
        raise BadInput("tuning.shop phải có map upgrades")
    if type(shop.get("max_ticks")) is not int or shop["max_ticks"] <= 0:
        raise BadInput("tuning.shop.max_ticks phải là số nguyên dương")
    upgrades = shop["upgrades"]
    if not {"oxygen", "hp"} <= upgrades.keys():
        raise BadInput("tuning.shop.upgrades phải có oxygen và hp")
    for name, entries in upgrades.items():
        if not isinstance(entries, list) or not entries:
            raise BadInput(f"tuning.shop.upgrades.{name} phải là mảng cấp không rỗng")
        for index, entry in enumerate(entries, 1):
            label = f"shop.upgrades.{name}[{index}]"
            if not isinstance(entry, dict):
                raise BadInput(f"tuning.{label} phải là object")
            _int_between(f"{label}.level", entry.get("level"), index, index)
            if type(entry.get("price")) is not int or entry["price"] <= 0:
                raise BadInput(f"tuning.{label}.price phải là số nguyên dương")
            if name == "oxygen":
                _positive_ticks(f"{label}.oxygen_max_s", entry.get("oxygen_max_s"), tick_hz)
            if name == "hp" and (type(entry.get("hp_max")) is not int or entry["hp_max"] <= 0):
                raise BadInput(f"tuning.{label}.hp_max phải là số nguyên dương")


def _validate_freshness(freshness):
    decay_keys = ("gather_decay_per_s", "quan_decay_per_s")
    if not isinstance(freshness, dict) or freshness.keys() != {"initial", "spoiled_below", *decay_keys}:
        raise BadInput("tuning.freshness phải có đúng initial, spoiled_below và hai tốc độ hao")
    initial = freshness["initial"]
    if not _num(initial) or not 0 < initial <= 100:
        raise BadInput("tuning.freshness.initial phải trong (0, 100]")
    spoiled = freshness["spoiled_below"]
    if not _num(spoiled) or not 0 < spoiled <= initial:
        raise BadInput("tuning.freshness.spoiled_below phải trong (0, initial]")
    for key in decay_keys:
        decay = freshness[key]
        if not _num(decay) or not 0 < decay <= sys.float_info.max:
            raise BadInput(f"tuning.freshness.{key} phải dương và hữu hạn")


def validate_tuning(t, *, contract_version="1.1"):
    if not isinstance(t, dict):
        raise BadInput("thiếu khối tuning")
    if contract_version in ("1.2", "1.3"):
        _validate_freshness(t.get("freshness"))
    elif "freshness" in t:
        raise BadInput("tuning.freshness chỉ dùng với contract_version 1.2 trở lên")
    g, q, menu = t.get("gather"), t.get("quan"), t.get("menu")
    if not isinstance(g, dict) or not isinstance(q, dict) or not isinstance(menu, dict):
        raise BadInput("tuning phải có gather, quan, menu")
    tick_hz = t.get("tick_hz")
    _int_between("tick_hz", tick_hz, 60, 60)
    _validate_gather(g, tick_hz)
    _validate_quan(q, tick_hz)
    _validate_menu(menu, tick_hz)
    validate_day_plans(t.get("day_plan"), t, complete=True)
    _validate_shop(t.get("shop"), tick_hz)

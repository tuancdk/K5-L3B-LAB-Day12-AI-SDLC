"""Buổi tối — PRD-0 F.Quán, TICKET-02/03, kho cá thể và giá theo độ tươi.

stock là tồn vật lý, gồm phần reserved; chỉ trừ tồn khi bắt đầu nấu.
Payload món và sự kiện theo Test Contract v1.2; fixture đếm nội bộ vẫn hỗ trợ P1–P2.
"""

import math
from copy import deepcopy
from fractions import Fraction

from ..errors import BadInput
from ..ids import id_key, sort_by_id
from ..inventory import FRESH_UNITS, validate_item_list
from .ramp import ramp_velocity


class QuanSim:
    mode = "quan"
    phase = "quan"

    def __init__(self, tuning, scenario, streams, ids, inventory=None, day_ctx=None):
        t = tuning["quan"]
        self.t = t
        self.tick_hz = tuning["tick_hz"]
        self.phase_tick = 0
        self.random_customers = scenario.get("random_customers", True)
        # day.py đã lọc tuning, nhưng sim cũng nhận được tuning đầy đủ qua day_ctx.
        # Số suất chỉ là mục tiêu thu gom, không giới hạn số đơn được bán.
        self.day_ctx = deepcopy(day_ctx)
        planned = day_ctx["day_plan"]["dishes"] if day_ctx is not None else None
        self.menu = {dish: tuning["menu"][dish] for dish in sorted(tuning["menu"])
                     if planned is None or dish in planned}
        self.rng = streams
        self.ids = ids
        p = scenario.get("player", {})
        self.pos = list(p.get("pos", t["start_pos"]))
        self.vel = [float(c) for c in p.get("vel", [0.0, 0.0])]
        self._tgt = None
        self._ramp_left = 0
        # kho: --inventory HOẶC scenario.stock (cả hai -> cli đã báo mã 2)
        raw_stock = inventory if inventory is not None else scenario.get("stock", [] if "freshness" in tuning else {})
        self.use_items = isinstance(raw_stock, list)
        self.freshness = tuning.get("freshness")
        self._fresh = {}
        if self.use_items:
            self.stock = validate_item_list(raw_stock, where="quan.stock")
            for item in self.stock:
                ids.reserve(item["id"])
                value = item["fresh"]
                units = Fraction(str(value)) * FRESH_UNITS
                nearest = round(units)
                # Khôi phục đơn vị nguyên từ float ngắn nhất do Gather/file kho xuất.
                # Không làm tròn một giá trị đầu vào khác ở sát ngưỡng.
                self._fresh[item["id"]] = (Fraction(nearest) if float(Fraction(nearest, FRESH_UNITS)) == value
                                           else units)
        else:
            self.stock = dict(raw_stock)  # tương thích sim/fixture nội bộ v1.0–v1.1
        self.hand = deepcopy(scenario.get("hand"))
        self.time_left_ticks = scenario.get("time_left_ticks", self._ticks(t["duration_s"]))
        self.reputation = scenario.get("reputation", t["reputation_initial"])
        self.stoves = [dict(s, state=s.get("state", "idle"), dish=s.get("dish"),
                            cook_ticks_left=s.get("cook_ticks_left", 0), ready_ticks=s.get("ready_ticks", 0))
                       for s in self._merge(t["stoves"], scenario.get("stoves", []))]
        self.tables = self._merge(t["tables"], scenario.get("tables", []))
        self.customers = []
        for raw in sorted(scenario.get("customers", []),
                          key=lambda c: (c.get("order_tick", 0), id_key(c["table_id"]))):
            c = dict(id=raw["id"], table_id=raw["table_id"], dish_id=raw.get("dish_id"),
                     order_tick=0, state="waiting", patience_ticks_left=self._ticks(t["patience_s"]),
                     eat_ticks_left=0, order_status="reserved", base_price=0, tip=0)
            c.update(deepcopy(raw))
            if "reserved" not in raw:
                if self.use_items:
                    c["reserved"] = self._pick_items(self.menu[c["dish_id"]]["recipe"]) if c["order_status"] == "reserved" else []
                    if c["reserved"] is None:  # thiếu hàng chưa ươn: đơn không làm được (như khi ươn mất phần giữ)
                        c["order_status"], c["reserved"] = "unfulfillable", []
                else:
                    c["reserved"] = (dict(self.menu[c["dish_id"]]["recipe"])
                                     if c["order_status"] == "reserved" and c["dish_id"] else {})
            if self.use_items:
                self._validate_reserved(c)
            self.customers.append(c)
        for e in self.customers:
            ids.reserve(e["id"])
        self.money = 0
        self.earned = 0
        self.shift_earned = 0
        self.done = False
        self.reason = None

    def _ticks(self, seconds):
        return int(round(seconds * self.tick_hz))

    @property
    def items_stock(self):
        return deepcopy(sort_by_id(self.stock)) if self.use_items else None

    def _pick_items(self, recipe):
        held = {ident for c in self.customers for ident in c["reserved"]}
        threshold = Fraction(str(self.freshness["spoiled_below"])) * FRESH_UNITS
        picked = []
        for kind, count in sorted(recipe.items()):
            available = [it for it in self.stock if it["kind"] == kind and it["id"] not in held
                         and self._fresh[it["id"]] >= threshold]
            available.sort(key=lambda it: (-self._fresh[it["id"]], id_key(it["id"])))
            if len(available) < count:
                return None
            picked.extend(it["id"] for it in available[:count])
        return picked

    def _validate_reserved(self, customer):
        reserved = customer["reserved"]
        if (not isinstance(reserved, list) or any(not isinstance(i, str) or not i for i in reserved)
                or len(reserved) != len(set(reserved))):
            raise BadInput(f"customers.{customer['id']}.reserved phải là mảng id duy nhất")
        if customer["order_status"] != "reserved":
            if reserved:
                raise BadInput("đơn không reserved phải có phần giữ rỗng")
            return
        by_id = {it["id"]: it for it in self.stock}
        held = {ident for c in self.customers for ident in c["reserved"]}
        counts = {}
        threshold = Fraction(str(self.freshness["spoiled_below"])) * FRESH_UNITS
        for ident in reserved:
            if ident not in by_id or ident in held or self._fresh[ident] < threshold:
                raise BadInput(f"reserved: id {ident!r} thiếu, trùng hoặc đã ươn")
            kind = by_id[ident]["kind"]
            counts[kind] = counts.get(kind, 0) + 1
        if counts != self.menu[customer["dish_id"]]["recipe"]:
            raise BadInput("reserved không khớp công thức")

    def _decay_stock(self, events):
        if not self.use_items:
            return
        decay = Fraction(str(self.freshness["quan_decay_per_s"])) * FRESH_UNITS / self.tick_hz
        threshold = Fraction(str(self.freshness["spoiled_below"])) * FRESH_UNITS
        spoiled = set()
        for item in sort_by_id(self.stock):
            ident = item["id"]
            before = self._fresh[ident]
            self._fresh[ident] = max(0, before - decay)
            item["fresh"] = float(self._fresh[ident] / FRESH_UNITS)
            if before >= threshold > self._fresh[ident]:
                spoiled.add(ident)
                events.append(("spoiled", {"item_id": ident, "kind": item["kind"], "location": "stock"}))
        for c in sorted(self.customers, key=self._order_key):
            if c["order_status"] == "reserved" and spoiled.intersection(c["reserved"]):
                c["reserved"] = []
                replacement = self._pick_items(self.menu[c["dish_id"]]["recipe"])
                c["reserved"] = replacement or []
                if replacement is None:
                    c["order_status"] = "unfulfillable"

    @staticmethod
    def _order_key(customer):
        return customer["order_tick"], id_key(customer["table_id"])

    @staticmethod
    def _merge(defaults, updates):
        by_id = {d["id"]: dict(d) for d in defaults}
        for u in updates:
            if u["id"] not in by_id:
                from ..errors import BadInput
                raise BadInput(f"id bếp/bàn không tồn tại: {u['id']}")
            by_id[u["id"]].update(deepcopy(u))
        return sort_by_id(list(by_id.values()))

    def snapshot(self) -> dict:
        occupied = {c["table_id"]: c["id"] for c in self.customers}
        return {
            "player": {"pos": self.pos, "vel": self.vel},
            "stock": (deepcopy(sort_by_id(self.stock)) if self.use_items else
                      {k: self.stock[k] for k in sorted(self.stock) if self.stock[k] > 0}),
            "hand": self.hand,
            "stoves": [{k: s.get(k) for k in ("id", "pos", "state", "dish", "cook_ticks_left", "ready_ticks")}
                       for s in self.stoves],
            "tables": [{"id": tb["id"], "pos": tb["pos"], "customer_id": occupied.get(tb["id"])} for tb in self.tables],
            "customers": sort_by_id(self.customers),
        }

    def step(self, inp):
        if self.done:
            return []
        events = []
        self.phase_tick += 1
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        # 1. Chỉ giảm timer đã hoạt động ở đầu bước.
        for s in self.stoves:
            if s["state"] == "cooking":
                s["cook_ticks_left"] = max(0, s["cook_ticks_left"] - 1)
            elif s["state"] == "ready":
                s["ready_ticks"] += 1
        for c in self.customers:
            timer = "eat_ticks_left" if c["state"] == "eating" else "patience_ticks_left"
            c[timer] = max(0, c[timer] - 1)
        self._decay_stock(events)
        # 2. Món vừa chín tuổi 0, có thể nhặt ngay trong bước này.
        for s in sort_by_id(self.stoves):
            if s["state"] == "cooking" and s["cook_ticks_left"] == 0:
                s["state"] = "ready"
                s["ready_ticks"] = 0
                events.append(("dish_ready", self._dish_event(s)))
        # 3. Phục vụ trước khi xử lý deadline kiên nhẫn/đóng ca.
        self._move(inp)
        if inp.pressed("interact"):
            self._interact(events)
        # 4. Khách xử lý theo id bàn, kể cả khi ca vừa hết giờ.
        for c in sort_by_id(list(self.customers), key=lambda c: c["table_id"]):
            if c["state"] == "eating" and c["eat_ticks_left"] == 0:
                self._pay(c, "finished_eating", events)
            elif self.time_left_ticks == 0:
                if c["state"] == "eating":
                    self._pay(c, "closing", events)
                else:
                    self._leave(c, "closing", events)
            elif c["state"] == "waiting" and c["patience_ticks_left"] == 0:
                self._leave(c, "patience", events)
        if self.time_left_ticks <= 0:
            self.done = True
            self.reason = "time"
            events.append(("quan_end", {"reason": "time", "money": self.money, "earned": self.earned,
                                        "shift_earned": self.shift_earned, "reputation": self.reputation}))
        else:
            # 5. Khách sinh cuối bước; tương tác và timer từ bước sau.
            first = self.t["first_customer_tick"]
            interval = self._ticks(self.t["customer_interval_s"])
            if self.random_customers and self.phase_tick >= first and (self.phase_tick - first) % interval == 0:
                self._arrive(events)
        return events

    def _available(self):
        if self.use_items:
            held = {ident for c in self.customers for ident in c["reserved"]}
            return [it for it in self.stock if it["id"] not in held
                    and self._fresh[it["id"]] >= Fraction(str(self.freshness["spoiled_below"])) * FRESH_UNITS]
        available = dict(self.stock)
        for c in self.customers:
            for kind, amount in c["reserved"].items():
                available[kind] = available.get(kind, 0) - amount
        return available

    def _arrive(self, events):
        occupied = {c["table_id"] for c in self.customers}
        table = next((tb for tb in sort_by_id(self.tables) if tb["id"] not in occupied), None)
        if table is None:
            return
        available = self._available()
        dishes = [dish for dish in sorted(self.menu)
                  if (self._pick_items(self.menu[dish]["recipe"]) is not None if self.use_items else
                      all(available.get(k, 0) >= n for k, n in self.menu[dish]["recipe"].items()))]
        if not dishes:
            events.append(("no_dish", {}))
            return
        dish_id = self.rng.get("customer_dish").choice(dishes)
        c = {"id": self.ids.new("C"), "table_id": table["id"], "dish_id": dish_id,
             "order_tick": self.phase_tick, "state": "waiting",
             "patience_ticks_left": self._ticks(self.t["patience_s"]), "eat_ticks_left": 0,
             "order_status": "reserved", "reserved": (self._pick_items(self.menu[dish_id]["recipe"]) if self.use_items
                                                        else dict(self.menu[dish_id]["recipe"])),
             "base_price": 0, "tip": 0}
        self.customers.append(c)
        events.append(("customer_arrived", {"order_id": c["id"], "table_id": c["table_id"],
                                             "dish_id": dish_id}))

    @staticmethod
    def _dish_event(stove):
        dish = stove["dish"]
        return {"stove_id": stove["id"], "order_id": dish["order_id"], "dish_id": dish["dish_id"]}

    def _interact(self, events):
        candidates = [(math.dist(self.pos, obj["pos"]), priority, id_key(obj["id"]), obj)
                      for priority, objects in enumerate((self.stoves, self.tables)) for obj in objects]
        candidates = [entry for entry in candidates if entry[0] <= self.t["interact_radius"]]
        if not candidates:
            return
        _, priority, _, obj = min(candidates, key=lambda entry: entry[:3])
        if priority == 0:
            self._use_stove(obj, events)
        else:
            self._serve(obj, events)

    def _use_stove(self, stove, events):
        if stove["state"] == "idle":
            orders = [c for c in self.customers if c["state"] == "waiting" and c["order_status"] == "reserved"]
            if not orders:
                return
            c = min(orders, key=self._order_key)
            dish = self.menu[c["dish_id"]]
            price = dish["price"]
            if self.use_items:
                used = set(c["reserved"])
                items = sorted((deepcopy(it) for it in self.stock if it["id"] in used),
                               key=lambda it: (it["kind"], id_key(it["id"])))
                average = sum(self._fresh[i] for i in used) / len(used)
                price = math.floor(price * average / (FRESH_UNITS * self.freshness["initial"]))
                self.stock = [it for it in self.stock if it["id"] not in used]
                for ident in used:
                    del self._fresh[ident]
                c["reserved"] = []
            else:
                items = [kind for kind in sorted(c["reserved"]) for _ in range(c["reserved"][kind])]
                for kind, amount in c["reserved"].items():
                    self.stock[kind] -= amount
                c["reserved"] = {}
            c["order_status"] = "assigned"
            c["base_price"] = price
            stove.update(state="cooking", dish={"order_id": c["id"], "dish_id": c["dish_id"],
                                               "base_price": price},
                         cook_ticks_left=self._ticks(dish["cook_s"]), ready_ticks=0)
            events.append(("cook_started", dict(self._dish_event(stove), items=items, base_price=price)))
        elif stove["state"] == "ready" and self.hand is None and self.t["carry_limit"] >= 1:
            events.append(("dish_picked", self._dish_event(stove)))
            self.hand = stove["dish"]
            self._clear_stove(stove)

    def _serve(self, table, events):
        c = next((c for c in self.customers if c["table_id"] == table["id"]), None)
        if c is None or c["state"] != "waiting" or self.hand is None or self.hand["order_id"] != c["id"]:
            return
        c["base_price"] = self.hand["base_price"]
        ratio = c["patience_ticks_left"] / self._ticks(self.t["patience_s"])
        c["tip"] = (math.floor(c["base_price"] * self.t["tip_rate"])
                    if ratio >= self.t["tip_min_patience_ratio"] else 0)
        c.update(state="eating", order_status="served", eat_ticks_left=self._ticks(self.t["eat_s"]))
        self.hand = None
        events.append(("served", {"order_id": c["id"], "table_id": c["table_id"], "dish_id": c["dish_id"],
                                  "patience_ticks_left": c["patience_ticks_left"],
                                  "base_price": c["base_price"], "tip": c["tip"]}))

    def _change_reputation(self, delta):
        # Làm tròn 9 số để cộng dồn float không lệch floor (0 + 10×0.2 = 1.9999999999999998 → mất 100 điểm).
        value = round(self.reputation + delta, 9)
        self.reputation = max(self.t["reputation_min"], min(self.t["reputation_max"], value))

    def _pay(self, customer, reason, events):
        amount = customer["base_price"] + customer["tip"]
        self.money += amount
        self.earned += amount
        self.shift_earned += amount
        if customer["tip"] > 0:
            self._change_reputation(self.t["tip_reputation"])
        events.append(("paid", {"order_id": customer["id"], "table_id": customer["table_id"],
                                "base_price": customer["base_price"], "tip": customer["tip"],
                                "amount": amount, "reason": reason}))
        self._remove_customer(customer)

    def _leave(self, customer, reason, events):
        if reason == "patience":
            self._change_reputation(self.t["left_reputation_delta"])
        events.append(("customer_left", {"order_id": customer["id"], "table_id": customer["table_id"],
                                         "reason": reason, "reputation": self.reputation}))
        self._remove_customer(customer)

    @staticmethod
    def _clear_stove(stove):
        stove.update(state="idle", dish=None, cook_ticks_left=0, ready_ticks=0)

    def _remove_customer(self, customer):
        for stove in self.stoves:
            if stove["dish"] and stove["dish"]["order_id"] == customer["id"]:
                self._clear_stove(stove)
        if self.hand and self.hand["order_id"] == customer["id"]:
            self.hand = None
        self.customers.remove(customer)

    def _move(self, inp):
        speed = self.t["walk_speed"]
        mx, mz = inp.move
        self.vel = ramp_velocity(self, (mx * speed, mz * speed), int(self.t["ramp_max_ticks"]))
        b = self.t["bounds"]
        for i, axis in enumerate(("x", "z")):
            self.pos[i] += self.vel[i] / self.tick_hz
            lo, hi = b[axis]
            if self.pos[i] <= lo:
                self.pos[i], self.vel[i] = lo, max(0.0, self.vel[i])
            elif self.pos[i] >= hi:
                self.pos[i], self.vel[i] = hi, min(0.0, self.vel[i])

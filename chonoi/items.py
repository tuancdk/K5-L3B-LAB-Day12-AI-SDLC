"""Adapter kho cá thể v1.2 (TICKET-03, issue #18) — bật khi contract_version >= 1.2.

Luật gather/quan hiện vẫn giữ hàng dạng loại (giỏ = mảng kind, kho quán = object đếm). Adapter này đứng ở biên
headless (runner.run) và gán danh tính cá thể {id, kind, fresh} cho từng món hàng để mọi ĐẦU RA đúng schema v1.2:
file `--inventory-out`, `gather_end.data.inventory`, snapshot `hold` (gather) và `stock` (quán, Shop).

- Id `I1, I2, …` cấp theo thứ tự vào giỏ, tăng xuyên pha và Ngày; id trong fixture được giữ và đặt chỗ.
- Giỏ chỉ thêm ở cuối và mất từ cuối (LIFO) nên khớp theo độ dài; kho quán chỉ giảm nên khi một loại giảm n,
  bỏ n cá thể tươi nhất của loại đó (hòa theo id) — đúng quy tắc lấy hàng của TICKET-03.
- `day`: bàn giao trong cùng tick chuyển pha, không hao thêm; Ngày 1 giữ id của `gather.hold` mẫu, Ngày sau cấp
  id mới theo thứ tự mảng với kind/fresh ban đầu.

Khi #19 (gather) và #20 (quán) giữ cá thể + hao tươi ngay trong sim (thuộc tính `items_hold` / `items_stock`),
adapter dùng thẳng dữ liệu đó thay vì tự gán.
"""

from copy import deepcopy

from .ids import IdAllocator, id_key
from .inventory import is_item_schema, items_to_counts, read_inventory_for, sort_items
from .scenario import load_scenario


def split_items(items):
    """Mảng cá thể -> (danh sách kind theo thứ tự, bản sao cá thể) cho sim còn dùng dạng loại."""
    return [it["kind"] for it in items], [dict(it) for it in items]


class ItemLedger:
    def __init__(self, mode, fresh_initial, gather_items=None, quan_items=None):
        self.mode = mode
        self.fresh0 = fresh_initial
        self.ids = IdAllocator()
        self.tpl_gather = [dict(it) for it in (gather_items or [])]
        for it in self.tpl_gather + list(quan_items or []):
            self.ids.reserve(it["id"])
        self.key = None
        self.hold = []    # cá thể trong giỏ theo thứ tự vào giỏ
        self.stock = [dict(it) for it in (quan_items or [])]
        self._gather_sim = None
        self._dropped = []  # cá thể vừa rơi khỏi giỏ trong bước này, theo thứ tự bỏ (LIFO)
        self.native_gather = False

    # --- theo dõi pha ----------------------------------------------------------------
    def _inner(self, sess):
        sim = sess.sim
        if self.mode == "day":
            return sim.sim, sim.phase, sim.day
        return sim, sim.phase, 1

    def sync(self, sess):
        self._dropped = []
        inner, phase, day = self._inner(sess)
        key = (day, phase)
        if key != self.key:
            self._enter(phase, day, inner)
            self.key = key
        if phase == "gather":
            self._gather_sim = inner
            self._sync_hold(inner)
        elif phase == "quan":
            self._sync_stock(inner)

    def _enter(self, phase, day, inner):
        if phase == "gather":
            if self.key is None and day == 1:
                self.hold = [dict(it) for it in self.tpl_gather]
            else:  # Ngày kế: id mới theo thứ tự mảng mẫu, giữ kind/fresh ban đầu
                self.hold = [{"id": self.ids.new("I"), "kind": it["kind"], "fresh": it["fresh"]}
                             for it in self.tpl_gather]
        elif phase == "quan" and self.mode == "day":
            if self._gather_sim is not None:
                self._sync_hold(self._gather_sim)  # chốt giỏ cuối buổi sáng (kể cả ngất -> rỗng)
            self.stock = [dict(it) for it in self.hold]  # bàn giao cùng tick, không hao thêm

    def _sync_hold(self, sim):
        if getattr(sim, "use_items", False):  # #19: GatherSim giữ cá thể + hao tươi
            self.native_gather = True
            self.hold = [sim.export_hold_item(it) for it in sim.hold]
            return
        native = getattr(sim, "items_hold", None)
        if native is not None:
            self.hold = deepcopy(list(native))
            return
        kinds = list(sim.hold)
        n = len(kinds)
        if n < len(self.hold):
            self._dropped.extend(reversed(self.hold[n:]))
        if [it["kind"] for it in self.hold[:n]] != kinds[:len(self.hold[:n])]:
            self.hold = self.hold[:0]  # lệch (không xảy ra với luật LIFO) -> dựng lại
        self.hold = self.hold[:n]
        for kind in kinds[len(self.hold):]:
            self.hold.append({"id": self.ids.new("I"), "kind": kind, "fresh": self.fresh0})

    def _sync_stock(self, sim):
        native = getattr(sim, "items_stock", None)
        if native is not None:
            self.stock = deepcopy(list(native))
            return
        counts = dict(sim.stock)
        by_kind = {}
        for it in self.stock:
            by_kind.setdefault(it["kind"], []).append(it)
        keep = []
        for kind, group in by_kind.items():
            extra = len(group) - counts.get(kind, 0)
            if extra > 0:  # dùng tươi nhất trước, hòa theo id
                used = sorted(group, key=lambda it: (-it["fresh"], id_key(it["id"])))[:extra]
                used_ids = {it["id"] for it in used}
                group = [it for it in group if it["id"] not in used_ids]
            keep.extend(group)
        self.stock = sort_items(keep)

    # --- đầu ra ------------------------------------------------------------------------
    def inventory(self):
        return {"items": sort_items(self.hold)}

    def inventory_for(self, sess):
        """Kho ghi file khi gather_end: lấy từ sim nếu sim đã giữ cá thể."""
        inner = self._inner(sess)[0]
        if getattr(inner, "use_items", False):
            return {"items": sort_items(inner.inventory_items())}
        return self.inventory()

    def patch_snapshot(self, snap):
        phase = snap.get("phase")
        if phase == "gather" and "hold" in snap and not self.native_gather:
            snap["hold"] = [dict(it) for it in self.hold]
        elif phase in ("quan", "shop") and "stock" in snap:
            snap["stock"] = [dict(it) for it in self.stock]
        return snap

    def patch_event(self, row):
        if self.native_gather:
            return row  # sim đã phát gather_end/lost/spoiled đúng schema v1.2
        name = row.get("name")
        if name == "gather_end":
            row["data"] = dict(row["data"], inventory=self.inventory())
        elif name in ("faint", "monster_hit") and isinstance(row["data"].get("lost"), list):
            n = len(row["data"]["lost"])
            lost, self._dropped = self._dropped[:n], self._dropped[n:]
            row["data"] = dict(row["data"], lost=[dict(it) for it in lost])
        return row


def load_game_inputs(mode, contract, scenario_path, inventory_path):
    version = contract["contract_version"]
    tuning = contract["tuning"]
    inventory = read_inventory_for(inventory_path, version) if inventory_path else None
    scenario = load_scenario(scenario_path, mode, tuning, inventory=inventory,
                             extensions=contract.get("extensions", []))
    ledger = None
    if is_item_schema(version):
        gather = scenario.get("gather", {}) if mode == "day" else scenario
        stock = []
        if mode == "quan":
            stock = inventory if inventory is not None else scenario.get("stock", [])
            scenario = quan_counts(scenario, stock, tuning)
            if inventory is not None:
                inventory = items_to_counts(inventory)
        ledger = ItemLedger(mode, tuning["freshness"]["initial"], gather.get("hold"), stock)
    return scenario, inventory, ledger


def quan_counts(scenario, stock, tuning):
    # Adapter tạm cho Quán trong lúc chờ #20 chuyển sang kho cá thể.
    scenario = deepcopy(scenario)
    if "stock" in scenario:
        scenario["stock"] = items_to_counts(stock)
    customers = scenario.get("customers", [])
    by_id = {item["id"]: item for item in stock}
    claimed = {item_id for customer in customers for item_id in customer.get("reserved", [])}
    available = {}
    for item in sorted(stock, key=lambda item: (-item["fresh"], id_key(item["id"]))):
        if item["id"] not in claimed and item["fresh"] >= tuning["freshness"]["spoiled_below"]:
            available.setdefault(item["kind"], []).append(item)

    for customer in sorted(customers, key=lambda c: (c.get("order_tick", 0), id_key(c["table_id"]))):
        if "reserved" in customer:
            customer["reserved"] = items_to_counts([by_id[item_id] for item_id in customer["reserved"]])
        elif customer.get("order_status", "reserved") == "reserved":
            recipe = tuning["menu"][customer["dish_id"]]["recipe"]
            if any(len(available.get(kind, [])) < amount for kind, amount in recipe.items()):
                customer.update(order_status="unfulfillable", reserved={})
                continue
            customer["reserved"] = dict(recipe)
            for kind, amount in recipe.items():
                del available[kind][:amount]
    return scenario

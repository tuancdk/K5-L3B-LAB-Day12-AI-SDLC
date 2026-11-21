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
from .inventory import sort_items


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

    def patch_snapshot(self, snap):
        phase = snap.get("phase")
        if phase == "gather" and "hold" in snap:
            snap["hold"] = [dict(it) for it in self.hold]
        elif phase in ("quan", "shop") and "stock" in snap:
            snap["stock"] = [dict(it) for it in self.stock]
        return snap

    def patch_event(self, row):
        name = row.get("name")
        if name == "gather_end":
            row["data"] = dict(row["data"], inventory=self.inventory())
        elif name in ("faint", "monster_hit") and isinstance(row["data"].get("lost"), list):
            n = len(row["data"]["lost"])
            lost, self._dropped = self._dropped[:n], self._dropped[n:]
            row["data"] = dict(row["data"], lost=[dict(it) for it in lost])
        return row


def scenario_items(data, mode):
    """v1.2: tách `gather.hold` / `quan.stock` dạng cá thể khỏi scenario thô.

    Trả (data cho validator hiện có — hold là mảng kind, stock là object đếm, gather_items, quan_items).
    Sai schema (vd hold dạng kind, stock dạng đếm ở v1.2) -> BadInput (mã 2).
    """
    from .inventory import items_to_counts, validate_item_list
    if not isinstance(data, dict):
        return data, [], []
    data = deepcopy(data)
    g_items, q_items = [], []
    g = data.get("gather")
    if isinstance(g, dict) and "hold" in g:
        g_items = validate_item_list(g["hold"], where="gather.hold")
        g["hold"] = [it["kind"] for it in g_items]
    q = data.get("quan")
    if isinstance(q, dict) and "stock" in q:
        q_items = validate_item_list(q["stock"], where="quan.stock")
        q["stock"] = items_to_counts(q_items)
    if isinstance(q, dict):  # customers[].reserved: mảng id cá thể trong kho, không dùng chung giữa các đơn
        by_id, used = {it["id"]: it for it in q_items}, set()
        for c in q.get("customers", []) if isinstance(q.get("customers"), list) else []:
            if isinstance(c, dict) and isinstance(c.get("reserved"), list):
                from .errors import BadInput
                for ident in c["reserved"]:
                    if ident not in by_id or ident in used:
                        raise BadInput(f"customers.{c.get('id')}.reserved: id {ident!r} không có trong kho hoặc bị giữ trùng")
                    used.add(ident)
                c["reserved"] = items_to_counts([by_id[i] for i in c["reserved"]])
    ids = [it["id"] for it in g_items + q_items]
    if len(ids) != len(set(ids)):
        from .errors import BadInput
        raise BadInput("id cá thể trùng giữa gather.hold và quan.stock")
    return data, g_items, q_items

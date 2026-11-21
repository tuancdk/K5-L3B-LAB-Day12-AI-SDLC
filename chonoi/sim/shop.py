"""Shop lõi Phase 2: oxygen/hp, giao diện docs/contracts mục 6.4.

day.py truyền tiền/cấp đã mua, gán earned/reputation và kho dư ngay sau khi dựng.
Pause và áp cấp sang Ngày kế do runner/day xử lý; Shop không sửa active_upgrades.
"""

from copy import deepcopy

from ..ids import sort_by_id


class ShopSim:
    mode = phase = "shop"

    def __init__(self, tuning, streams, ids, money, upgrades, day_ctx):
        self.t = tuning["shop"]
        self.rng, self.ids = streams, ids
        self.day_ctx = deepcopy(day_ctx)
        self.money = money
        self.upgrades = dict(upgrades)
        self.stock = [] if "freshness" in tuning else {}
        self.earned = 0
        self.reputation = tuning["quan"]["reputation_initial"]
        self.phase_tick = 0
        self.time_left_ticks = self.t["max_ticks"]
        self.done = False
        self.reason = None

    def snapshot(self):
        return {"stock": (deepcopy(sort_by_id(self.stock)) if isinstance(self.stock, list) else
                          {kind: self.stock[kind] for kind in sorted(self.stock) if self.stock[kind] > 0}),
                "upgrades": dict(sorted(self.upgrades.items())),
                "time_left_ticks": self.time_left_ticks}

    @property
    def items_stock(self):
        return deepcopy(sort_by_id(self.stock)) if isinstance(self.stock, list) else None

    def step(self, inp):
        if self.done:
            return []
        events = []
        self.phase_tick += 1
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        if inp.buy is not None:
            self._buy(inp.buy, events)
        # Mua trước khi đóng, kể cả bước cuối; nút đóng ưu tiên hơn timeout.
        if inp.pressed("shop_done"):
            self._close("done", events)
        elif self.time_left_ticks == 0:
            self._close("time", events)
        return events

    def _buy(self, action, events):
        if action not in ("oxygen", "hp"):
            events.append(("buy_failed", {"action": action, "reason": "unknown"}))
            return
        levels = self.t["upgrades"][action]
        current = self.upgrades.get(action, 0)
        if current >= len(levels):
            events.append(("buy_failed", {"action": action, "reason": "max_level"}))
            return
        upgrade = levels[current]
        if self.money < upgrade["price"]:
            events.append(("buy_failed", {"action": action, "reason": "funds"}))
            return
        self.money -= upgrade["price"]
        self.upgrades[action] = upgrade["level"]
        events.append(("bought", {"upgrade": action, "level": upgrade["level"],
                                  "price": upgrade["price"], "money": self.money}))

    def _close(self, reason, events):
        self.done = True
        self.reason = reason
        events.append(("shop_end", {"reason": reason}))

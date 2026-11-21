"""Mode `day` — vòng Ngày (TICKET-02 mục 2, Test Contract v1.1 mục 4.3–4.5). Issue #12.

Chuỗi mỗi Ngày: `gather -> quan -> shop`, tối đa `--days` Ngày (1–5). Kho chuyển trong bộ nhớ.
Đổi pha (4.5): đầu Ngày phát `day_start -> day_plan -> phase_start(gather)`; sau `gather_end` dựng quán và
phát `phase_start(quan)` CÙNG tick (kể cả ngất); sau `quan_end` dựng Shop và phát `phase_start(shop)` cùng tick.
Pha mới chỉ chạy gameplay từ bước sau. Shop đóng -> `days_completed += 1` -> dựng Ngày kế ngay tick đó.

Giữ qua Ngày: money, earned, reputation, upgrades (cấp đã mua). `active_upgrades` (cấp đang áp dụng) chỉ đổi
khi dựng Ngày mới. Mỗi Ngày: oxy/Máu đầy theo active_upgrades, giỏ mới (mẫu `scenario.gather`), kho dư bỏ sau Shop.

day.py đưa cho từng sim một "tuning hiệu lực của Ngày" (oxy/Máu theo cấp, quái theo from_day, menu lọc theo
kế hoạch) và `day_ctx` (xem docs/contracts/README.md mục 6.4), nên sim không cần tự đọc nâng cấp.
Pause do runner.Session xử lý chung cho cả ba mode.
"""

import inspect
from copy import deepcopy

from ..contract import plan_ingredients
from ..errors import BadInput
from ..items import scenario_items
from ..scenario import validate_quan
from .gather import GatherSim
from .quan import QuanSim

try:  # #8 viết chonoi/sim/shop.py; khi chưa có thì dùng Shop tối thiểu bên dưới.
    from .shop import ShopSim  # type: ignore
except ImportError:  # pragma: no cover - phụ thuộc tiến độ #8
    ShopSim = None


def day_plan_for(tuning, scenario_day, day, *, cycle=False):
    """Kế hoạch Ngày `day`: preset, bị `scenario.day.day_plan` ghi đè theo số Ngày. ingredients tính lại.
    Khi `cycle=True` (dùng cho soak > 5 Ngày): lặp lại D1–D5 theo `((day - 1) % len) + 1`.
    """
    n_plans = len(tuning["day_plan"])
    plan_day = ((day - 1) % n_plans) + 1 if cycle and n_plans > 0 else day
    plan = next((p for p in tuning["day_plan"] if p["day"] == plan_day), None)
    for p in (scenario_day or {}).get("day_plan", []):
        if p["day"] == day or (cycle and p["day"] == plan_day):
            plan = {"day": day, "dishes": dict(p["dishes"])}
    if plan is None:
        raise BadInput(f"thiếu day_plan cho Ngày {day}")
    return {"day": day, "dishes": dict(plan["dishes"]), "ingredients": plan_ingredients(tuning, plan["dishes"])}


def effective_tuning(tuning, day, plan, active):
    """Tuning hiệu lực của một Ngày (không sửa bản gốc)."""
    t = deepcopy(tuning)
    up = tuning["shop"]["upgrades"]
    if active.get("oxygen", 0) > 0:
        t["gather"]["oxygen_max_s"] = up["oxygen"][active["oxygen"] - 1]["oxygen_max_s"]
    if active.get("hp", 0) > 0:
        t["gather"]["hp_max"] = up["hp"][active["hp"] - 1]["hp_max"]
    mons = t["gather"].get("monsters")
    if mons:
        mons["spawns"] = [s for s in mons["spawns"] if s.get("from_day", 1) <= day]
    t["menu"] = {d: t["menu"][d] for d in sorted(t["menu"]) if d in plan["dishes"]}
    return t


def _build(cls, *args, day_ctx=None, **kw):
    """Truyền day_ctx khi sim đã nhận tham số này (sau #7/#13), không thì bỏ qua."""
    if "day_ctx" in inspect.signature(cls.__init__).parameters:
        kw["day_ctx"] = day_ctx
    return cls(*args, **kw)


class BasicShop:
    """Shop tối thiểu theo TICKET-02 (nâng cấp oxygen/hp) — chỉ dùng khi chưa có chonoi/sim/shop.py (#8)."""

    mode = phase = "shop"

    def __init__(self, tuning, streams, ids, money, upgrades, day_ctx, stock=None):
        self.t = tuning["shop"]
        self.money, self.upgrades = money, dict(upgrades)
        self.stock = dict(stock or {})
        self.time_left_ticks = int(self.t["max_ticks"])
        self.phase_tick = 0
        self.done, self.reason = False, None
        self.earned, self.reputation = 0, 0.0

    def snapshot(self):
        return {"stock": {k: self.stock[k] for k in sorted(self.stock) if self.stock[k] > 0}}

    def step(self, inp):
        events = []
        self.phase_tick += 1
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        buy = getattr(inp, "buy", None)
        if buy:
            self._buy(buy, events)
        if inp.pressed("shop_done"):
            self._close("done", events)
        elif self.time_left_ticks == 0:
            self._close("time", events)
        return events

    def _buy(self, action, events):
        levels = self.t["upgrades"].get(action)
        if levels is None:
            events.append(("buy_failed", {"action": action, "reason": "unknown"}))
            return
        nxt = self.upgrades.get(action, 0) + 1
        if nxt > len(levels):
            events.append(("buy_failed", {"action": action, "reason": "max_level"}))
            return
        price = levels[nxt - 1]["price"]
        if price > self.money:
            events.append(("buy_failed", {"action": action, "reason": "funds"}))
            return
        self.money -= price
        self.upgrades[action] = nxt
        events.append(("bought", {"upgrade": action, "level": nxt, "price": price, "money": self.money}))

    def _close(self, reason, events):
        self.done, self.reason = True, reason
        events.append(("shop_end", {"reason": reason}))


class DaySim:
    mode = "day"

    def __init__(self, tuning, scenario, streams, ids, days=1, allow_extended_days=False):
        if allow_extended_days:
            if isinstance(days, bool) or not isinstance(days, int) or days < 1:
                raise BadInput("--days phải là số nguyên >= 1")
        else:
            if isinstance(days, bool) or not isinstance(days, int) or not (1 <= days <= len(tuning["day_plan"])):
                raise BadInput("--days phải trong [1, 5]")
        self.allow_extended_days = bool(allow_extended_days)
        self.tuning, self.scenario, self.rng, self.ids = tuning, scenario, streams, ids
        sd = scenario.get("day", {})
        self.days = days
        self.money = sd.get("money", 0)
        self.earned = sd.get("earned", 0)
        self.reputation = sd.get("reputation", tuning["quan"]["reputation_initial"])
        self.upgrades = {"hp": 0, "oxygen": 0}
        self.upgrades.update(sd.get("upgrades", {}))
        self.active_upgrades = dict(self.upgrades)
        self.days_completed = 0
        self.day = 0
        self.done, self.reason = False, None
        self.sim = None
        self.phase_tick = 0
        self.initial_events = []
        self._start_day(self.initial_events)

    # --- giao diện runner -------------------------------------------------------
    @property
    def phase(self):
        return self.sim.phase

    @property
    def time_left_ticks(self):
        return self.sim.time_left_ticks

    def snapshot(self):
        s = {"day": self.day, "day_plan": self.plan, "upgrades": dict(sorted(self.upgrades.items())),
             "active_upgrades": dict(sorted(self.active_upgrades.items()))}
        s.update(self.sim.snapshot())
        if self.phase == "shop":
            s["time_left_ticks"] = self.sim.time_left_ticks
        return s

    def step(self, inp):
        """Trả [(name, data, phase, day)] — phase/day là của pha phát event."""
        out = []
        self.phase_tick += 1
        sim = self.sim
        for name, data in sim.step(inp):
            out.append((name, data, sim.phase, self.day))
        self._pull(sim)
        if sim.done:
            if sim.phase == "gather":
                self._to_quan(sim, out)
            elif sim.phase == "quan":
                self._to_shop(sim, out)
            else:
                self.days_completed += 1
                if self.days_completed >= self.days:
                    self.done, self.reason = True, "days_complete"
                else:
                    self._start_day(out)
        return out

    # --- đổi pha -----------------------------------------------------------------
    def _pull(self, sim):
        self.money, self.earned, self.reputation = sim.money, sim.earned, sim.reputation
        if sim.phase == "shop":
            self.upgrades = dict(sim.upgrades)

    def _push(self, sim):
        sim.money, sim.earned, sim.reputation = self.money, self.earned, self.reputation

    def _ctx(self):
        return {"day": self.day, "day_plan": self.plan, "active_upgrades": dict(self.active_upgrades)}

    def _emit(self, out, name, data):
        out.append((name, data, self.sim.phase, self.day))

    def _start_day(self, out):
        self.day += 1
        self.active_upgrades = dict(self.upgrades)
        self.plan = day_plan_for(self.tuning, self.scenario.get("day"), self.day, cycle=self.allow_extended_days)
        self.t_day = effective_tuning(self.tuning, self.day, self.plan, self.active_upgrades)
        self.sim = _build(GatherSim, self.t_day, deepcopy(self.scenario.get("gather", {})), self.rng, self.ids,
                          day_ctx=self._ctx())
        self._push(self.sim)
        self.phase_tick = 0
        self._emit(out, "day_start", {})
        self._emit(out, "day_plan", {"dishes": self.plan["dishes"], "ingredients": self.plan["ingredients"]})
        self._emit(out, "phase_start", {})

    def _to_quan(self, gather, out):
        quan_tpl = deepcopy(self.scenario.get("quan", {}))
        inventory = gather.inventory_items()
        if isinstance(inventory, list):
            checked, _, _ = scenario_items({"quan": dict(quan_tpl, stock=inventory)}, "quan")
            validate_quan(checked["quan"], self.t_day, None)
        else:
            validate_quan(quan_tpl, self.t_day, inventory)
        self.sim = _build(QuanSim, self.t_day, quan_tpl, self.rng, self.ids,
                          inventory=inventory, day_ctx=self._ctx())
        self._push(self.sim)
        self.phase_tick = 0
        self._emit(out, "phase_start", {})

    def _to_shop(self, quan, out):
        stock = quan.snapshot().get("stock", {})
        if ShopSim is not None:
            self.sim = ShopSim(self.t_day, self.rng, self.ids, self.money, dict(self.upgrades), self._ctx())
            if hasattr(self.sim, "stock"):
                self.sim.stock = deepcopy(stock)
        else:
            self.sim = BasicShop(self.t_day, self.rng, self.ids, self.money, self.upgrades, self._ctx(), stock)
        self._push(self.sim)
        self.phase_tick = 0
        self._emit(out, "phase_start", {})

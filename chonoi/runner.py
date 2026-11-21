"""Vòng tick (Contract B, mô hình tick). KHUNG — thường không cần sửa.

Thứ tự ghi: snapshot tick 0 -> với mỗi bước: sự kiện (theo thứ tự xử lý) rồi snapshot (nếu tới lượt
hoặc buổi kết thúc) -> dòng 'end'. Mỗi tick tối đa một snapshot.

`Session` là API bước tick gọn dùng chung cho headless (`run`) và cửa sổ chơi trực tiếp (`chonoi.live`):
cả hai chạy CÙNG một lớp sim, không nhân đôi logic.
"""

import math

from .ids import IdAllocator
from .inputs import InputPlayer
from .inventory import write_inventory, write_inventory_items
from .jsonl import JsonlWriter
from .rng import Streams
from .sim.day import DaySim
from .sim.gather import GatherSim
from .sim.quan import QuanSim


def build_sim(mode, tuning, scenario, seed, inventory, days=1):
    streams, ids = Streams(seed), IdAllocator()
    if mode == "gather":
        return GatherSim(tuning, scenario, streams, ids)
    if mode == "day":
        return DaySim(tuning, scenario, streams, ids, days=days)
    return QuanSim(tuning, scenario, streams, ids, inventory=inventory)


def _common(sim, tick, sim_tick, phase_tick, tuning, state):
    mult = tuning["score"]["reputation_multiplier"]
    return {
        "type": "snapshot", "tick": tick, "sim_tick": sim_tick, "mode": sim.mode, "phase": sim.phase,
        "phase_tick": phase_tick, "state": state, "time_left_ticks": sim.time_left_ticks,
        "money": sim.money, "earned": sim.earned, "reputation": sim.reputation,
        "score": sim.earned + mult * math.floor(sim.reputation),
    }


class Session:
    """Một lượt chơi: dựng sim, bước từng tick, lấy snapshot / dòng end.

    Pause (v1.1 mục 4.2) xử lý ở đây cho cả ba mode: xét cạnh `pause` trước; vào pause chỉ tăng `tick` và phát
    `paused`; khi còn pause bỏ mọi hành động, `sim_tick`/`phase_tick`/timer đứng yên; cạnh kế phát `resumed` rồi
    chạy gameplay ngay bước đó.
    """

    def __init__(self, mode, tuning, scenario, seed, inventory=None, days=1):
        self.mode = mode
        self.tuning = tuning
        self.sim = build_sim(mode, tuning, scenario, seed, inventory, days)
        self.tick = 0
        self.sim_tick = 0
        self.paused = False

    @property
    def done(self) -> bool:
        return self.sim.done

    def _phase_tick(self):
        return getattr(self.sim, "phase_tick", self.sim_tick)

    def _state(self):
        return "finished" if self.sim.done else ("paused" if self.paused else "playing")

    def _row(self, name, data, phase=None, day=None):
        row = {"type": "event", "tick": self.tick, "phase": phase or self.sim.phase}
        if self.mode == "day":
            row["day"] = day if day is not None else self.sim.day
        row.update(name=name, data=data)
        return row

    def initial_rows(self) -> list:
        """Event của tick 0 (mode day: day_start, day_plan, phase_start) — ghi trước snapshot tick 0."""
        return [self._row(*e) for e in getattr(self.sim, "initial_events", [])]

    def snapshot(self) -> dict:
        s = _common(self.sim, self.tick, self.sim_tick, self._phase_tick(), self.tuning, self._state())
        s.update(self.sim.snapshot())
        return s

    def step(self, inp) -> list:
        """Chạy một bước với `inp` (chonoi.inputs.InputState); trả các dòng event (tick = k + 1)."""
        self.tick += 1
        rows = []
        if inp.pressed("pause"):
            if not self.paused:
                self.paused = True
                return [self._row("paused", {})]
            self.paused = False
            rows.append(self._row("resumed", {}))
        elif self.paused:
            return rows
        events = self.sim.step(inp)
        self.sim_tick += 1
        for e in events:
            rows.append(self._row(*e))
        return rows

    def end_row(self) -> dict:
        sim = self.sim
        score = _common(sim, self.tick, self.sim_tick, 0, self.tuning, "")["score"]
        row = {"type": "end", "ticks": self.tick, "sim_tick": self.sim_tick, "mode": sim.mode,
               "state": "finished" if sim.done else "playing",
               "reason": sim.reason if sim.done else "tick_limit",
               "money": sim.money, "earned": sim.earned, "reputation": sim.reputation, "score": score}
        if self.mode == "day":
            row["days_completed"] = sim.days_completed
        return row

    def write_inventory_if_done(self, inventory_out):
        """File kho: ghi MỘT lần khi có gather_end; chưa kết thúc thì giữ nguyên file đích."""
        if self.mode == "gather" and self.sim.done and inventory_out:
            write_inventory(inventory_out, self.sim.inventory_items())


def run(mode, tuning, scenario, seed, frames, ticks, out_path, snapshot_every, inventory=None, inventory_out=None,
        days=1, buttons=None, ledger=None):
    """`ledger` (chonoi.items.ItemLedger): bật khi contract v1.2 — đầu ra kho/giỏ dạng cá thể."""
    sess = Session(mode, tuning, scenario, seed, inventory, days)
    player = InputPlayer(frames, buttons) if buttons else InputPlayer(frames)
    w = JsonlWriter(out_path)
    if ledger is not None:
        ledger.sync(sess)
    snap = (lambda: ledger.patch_snapshot(sess.snapshot())) if ledger is not None else sess.snapshot
    try:
        for row in sess.initial_rows():
            w.write(row)
        w.write(snap())  # tick 0: sau khi dựng scenario, trước mọi input
        last_snapped = 0
        while sess.tick < ticks and not sess.done:
            inp = player.advance(sess.tick)  # bước k đọc input có tick == k
            rows = sess.step(inp)
            if ledger is not None:
                ledger.sync(sess)
                rows = [ledger.patch_event(r) for r in rows]
            for row in rows:
                w.write(row)
            if sess.tick % snapshot_every == 0 or sess.done:
                w.write(snap())
                last_snapped = sess.tick
        if last_snapped != sess.tick:
            w.write(snap())
        w.write(sess.end_row())
    finally:
        w.close()
    if ledger is not None:
        if sess.mode == "gather" and sess.done and inventory_out:
            write_inventory_items(inventory_out, ledger.inventory_for(sess)["items"])
    else:
        sess.write_inventory_if_done(inventory_out)
    return sess.sim

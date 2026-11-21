# Hợp đồng tích hợp — Test Contract v1.1 (Phase 2)

> Mục 1–5 là v1.0 (Phase 1, vẫn hiệu lực). **Mục 6 là thay đổi v1.1** (TICKET-02, issue #12).

> Integrator giữ file này (issue #1). Chốt ở phút 15 của Phase 1. **Đổi gì ở đây phải báo cả nhóm**, ghi lý do vào mục "Lịch sử đổi" cuối file (hoặc một ADR trong `docs/adr/`).
> Nguồn: PRD-0 trên lab board, Test Contract v1.0 mục B/D/E/F/G. Chỗ PRD chưa rõ → `docs/clarify.md`.

Người sở hữu module: `sim/gather` (#2), `sim/quan` (#3), validation `scenario.py`/`contract.py` (#4), `chonoi/web` UI (#5). Ai phát / ai nghe ghi theo module.

## 1. File kho (mục G) — ranh giới `gather` → `quan`

```json
{"items":{"bong_sung":2,"ca_loc":1}}
```

| Quy tắc | Chi tiết |
|---|---|
| Khóa gốc | **chỉ** `items` |
| `items` | object `kind → số nguyên ≥ 0`; kind thuộc `ca_loc`, `ca_linh`, `bong_dien_dien`, `bong_sung` |
| Kind vắng | tính là 0. Bên ghi **bỏ** khóa có lượng 0, khóa sắp theo tên. Kho rỗng: `{"items":{}}` |
| Bên đọc (`quan --inventory`) | từ chối sai schema, kind lạ, số âm/không nguyên → **mã thoát 2**. Trần giỏ không áp lên kho quán |
| Khi nào ghi | chỉ khi có event `gather_end`; nội dung = `data.inventory` của event đó. `--inventory-out` ghi **đúng một lần** (ngất → ghi kho rỗng) |
| Chưa kết thúc | chạm `--ticks` trước khi buổi sáng xong → **không** tạo / ghi đè file |
| Ghi an toàn | file tạm cùng thư mục rồi `os.replace` (đã có ở `chonoi/inventory.py`) |
| Quán độc lập | không có `--inventory` và không có `scenario.quan.stock` → kho rỗng; `money`/`earned` = 0; uy tín theo tuning trừ khi scenario khai |
| Xung đột | khai cả `--inventory` và `scenario.quan.stock` → mã 2 |

Ví dụ hợp lệ: [`inventory.sample.json`](inventory.sample.json). Smoke hộp đen PRD: [mục 5](#5-smoke-hộp-đen-tích-hợp).

## 2. Dòng JSONL (mục E)

Mỗi dòng một object UTF-8. Thứ tự: snapshot tick 0 (sau khi dựng fixture) → mỗi bước: các `event` theo thứ tự xử lý rồi `snapshot` (bội số `--snapshot-every`, hoặc khi dừng) → đúng một dòng `end` cuối. Mỗi tick tối đa một snapshot. Tọa độ làm tròn 3 chữ số; mảng thực thể sắp theo id; `hold` theo thứ tự nhặt.

```json
{"type":"event","tick":1,"phase":"gather","name":"gather","data":{"node_id":"N1","kind":"bong_dien_dien","amount":1}}
```

### 2.1 Sự kiện

| `name` | `data` | Ai phát | Ai nghe |
|---|---|---|---|
| `node_regrown` | `node_id` | gather (#2) | UI |
| `gather` | `node_id, kind, amount` | gather (#2) | UI |
| `hold_full` | `action` (`gather`/`catch`), `node_id` **hoặc** `fish_id`, `required, free` | gather (#2) | UI |
| `fish_caught` | `fish_id, kind, yield` — một event mỗi đàn, lấy đủ yield | gather (#2) | UI |
| `dive` / `surface` | `pos` sau di chuyển; chỉ khi đổi phía biên mặt nước (`d ≤ 0.5` là mặt nước) | gather (#2) | UI |
| `oxygen_empty` | `oxygen_ticks: 0` khi vừa chạm 0 | gather (#2) | UI |
| `choke` | `hp` sau khi trừ | gather (#2) | UI |
| `faint` | `cause: "choke", lost, hp: 0` — `lost` là mảng kind theo thứ tự bỏ (LIFO) | gather (#2) | UI |
| `gather_end` | `reason` (`time`/`docked`/`fainted`), `inventory` = object mục G | gather (#2, khung đã có) | runner → ghi file kho; UI |
| `customer_arrived` | `order_id, table_id, dish_id` | quan (#3) | UI |
| `no_dish` | `{}` — có bàn trống nhưng thiếu món | quan (#3) | UI |
| `cook_started` | `stove_id, order_id, dish_id, items, base_price` (`items` mảng kind, sắp theo kind) | quan (#3) | UI |
| `dish_ready` / `dish_picked` | `stove_id, order_id, dish_id` | quan (#3) | UI |
| `served` | `order_id, table_id, dish_id, patience_ticks_left, base_price, tip` | quan (#3) | UI |
| `paid` | `order_id, table_id, base_price, tip, amount, reason` (`finished_eating`/`closing`) | quan (#3) | UI |
| `customer_left` | `order_id, table_id, reason` (`patience`/`closing`), `reputation` | quan (#3) | UI |
| `quan_end` | `reason: "time", money, earned, shift_earned, reputation` | quan (#3) | UI |

Tên event và khóa `data` là **cố định** — test ẩn so chính xác. Thêm event sáng tạo được, nhưng tắt ở headless.

### 2.2 Snapshot — trường UI được đọc

| Phần | Trường |
|---|---|
| Chung (runner) | `type:"snapshot", tick, sim_tick, mode, phase, phase_tick, state` (`playing`/`finished`), `time_left_ticks, money, earned, reputation, score` |
| gather | `player{pos, vel, heading_deg, oxygen_ticks, oxygen_max_ticks, hp, hp_max, zero_oxy_ticks, invuln_ticks, catch_cd_ticks, at_surface}`, `hold[]`, `hold_count`, `hold_capacity`, `nodes[]{id, pos, kind, ready, regrow_ticks}`, `fish[]{id, pos, kind, heading_deg}` |
| quan | `player{pos, vel}`, `stock{kind:n}` (tồn vật lý, **gồm** phần giữ chỗ), `hand` (payload món hoặc `null`), `stoves[]{id, pos, state, dish, cook_ticks_left, ready_ticks}`, `tables[]{id, pos, customer_id}`, `customers[]` (chỉ khách còn ngồi; `{id, table_id, dish_id, order_tick, state, patience_ticks_left, eat_ticks_left, order_status, reserved, base_price, tip}`) |

Payload món: `{order_id, dish_id, base_price}`. Dòng `end`: `type:"end", ticks, sim_tick, mode, state, reason, money, earned, reputation, score`; `reason` = `time/docked/fainted` (gather), `time` (quan) hoặc `tick_limit`. Điểm = `earned + 100 × floor(reputation)`.

## 3. Giao diện `sim/*` ↔ `client/ui` (`chonoi/web`)

- UI **chỉ đọc** snapshot + event qua `GET /state` của `chonoi.live` (cùng trường như mục 2.2, thêm `meta`, `events`). Trường chưa có thì UI bỏ qua, không được vỡ.
- UI **chỉ gửi** `POST /input` `{"move":[a,b], "interact":bool, "catch":bool}` và `POST /restart`. Không gửi lệnh nào khác vào sim.
- Hiệu ứng, âm thanh, RNG giao diện, đồng hồ thật: **chỉ ở UI**, không đi vào sim/headless.
- Số liệu luật chỉ lấy từ `game.contract.json` (`tuning`); không hard-code trong `sim/*`.

## 4. Quy ước chung

- Ngẫu nhiên chỉ qua `Streams` (`chonoi/rng.py`); id qua `IdAllocator`; sắp bằng `ids.sort_by_id`.
- Mã thoát: `0` xong/chạm `--ticks`; `2` cờ/dữ liệu sai hoặc fixture mâu thuẫn (kiểm **trước** khi ghi JSONL/kho — #4); `1` lỗi đọc/ghi.
- Cùng seed + cùng đầu vào → JSONL và file kho giống từng byte (kiểm bằng skill `headless-check`).

## 5. Smoke hộp đen tích hợp

```bash
# dock.json:        {"gather":{"hold":["ca_loc","bong_sung","bong_sung"]}}
# dock-inputs.json: {"frames":[{"tick":0,"interact":true}]}
python3 -m chonoi.headless --mode gather --seed 42 --scenario dock.json --inputs dock-inputs.json --ticks 1 --inventory-out catch.json --out gather.jsonl
python3 -m chonoi.headless --mode quan --seed 42 --inventory catch.json --ticks 0 --out quan.jsonl
# kỳ vọng: snapshot quán tick 0 có "stock":{"bong_sung":2,"ca_loc":1}
```

Test tự động: `tests/test_integration_p1.py`. Chạy nhanh: skill `headless-check`.

## 6. Contract v1.1 (Phase 2) — thay đổi từ v1.0

### 6.1 Manifest và số chuẩn (`game.contract.json`)

| Phạm vi | Khóa thêm/đổi | Ai dùng |
|---|---|---|
| gốc | `contract_version:"1.1"`, `extensions: []` (mã mở rộng đã bật, vd `"burn"`) | mọi module |
| `gather` | `fish_initial: 8` (**số**, không còn là mảng), `fish_speed, fish_turn_ticks, fish_max, fish_spawn_ticks, fish_spawn_clearance, fish_x, fish_depths{loài}, fish_spawn_x[], fish_spawn_depths{loài}, fish_weights{loài}`; `fish_yield` có `ca_keo:2`; nút `N5, N6` (`keo_neo`) | #13 gather |
| `gather.monsters` | `species.ca_sau{patrol_speed, chase_speed, detect_radius, exit_radius, depths, hit_radius, recoil_ticks, recoil_dist}`, `spawns[]{id, kind, pos, waypoints, from_day}`, `invuln_ticks:90`, `loss_ratio:0.5` | #14 monsters |
| `quan`, `menu` | bếp `B1, B2`; bàn `T1–T4`; 6 món (`canh_chua_ca_loc, ca_keo_nuong, lau_mam` mới) | #7 quan |
| `day_plan` | 5 object `{day, dishes{món:suất}, ingredients{kind:n}}`; `ingredients` = tổng công thức × suất | #7, day, UI |
| `shop` | `{max_ticks:600, upgrades{oxygen[]{level, price, oxygen_max_s}, hp[]{level, price, hp_max}}}` | #8 shop |

Kind nguyên liệu v1.1 (6): `ca_loc, ca_linh, ca_keo, bong_dien_dien, bong_sung, keo_neo` (`chonoi/inventory.py`). Tuning không được hard-code ở `sim/*`.

### 6.2 CLI, inputs, pause

- `--mode gather|quan|day`; `--days N` (1–5, mặc định 1) **chỉ** với `day`, sai → mã 2. `--inventory`/`--inventory-out` vẫn chỉ cho hai mode độc lập; `day` chuyển kho trong bộ nhớ.
- Nút mới: `pause` (cả ba mode), `shop_done` (Shop), `buy` = chuỗi khác rỗng, chỉ chạy ở frame khai báo: `oxygen`, `hp` (mở rộng: `weapon`, `net`, `buy:<kind>`, `sell:<kind>`). Nút đúng kiểu nhưng sai pha/chưa bật thì bỏ qua; `buy` không hỗ trợ → `buy_failed{reason:"unknown"}`.
- Pause (runner/day lo, sim **không** cần biết): xét cạnh `pause` trước. Vào pause: chỉ tăng `tick`, phát `paused`, snapshot `state:"paused"`. Trong pause bỏ hành động và `buy`; `sim_tick`, `phase_tick`, lịch, timer đứng yên. Cạnh lên kế → `resumed`, gameplay chạy ngay bước đó.

### 6.3 Mode `day` — vòng ngày (`chonoi/sim/day.py`, #12)

`day_start → day_plan → phase_start(gather)` ở đầu Ngày; sau `gather_end` dựng quán + `phase_start(quan)` **cùng tick** (kể cả ngất); sau `quan_end` dựng Shop + `phase_start(shop)` cùng tick. Pha mới chạy gameplay từ bước sau. Shop đóng (`shop_end`) → `days_completed += 1` → dựng Ngày kế ngay tick đó hoặc kết thúc (`end.reason:"days_complete"`, `end.days_completed`).
Giữ qua Ngày: `money`, `earned`, `reputation`, `upgrades`. Mỗi Ngày: oxy/Máu đầy theo `active_upgrades`, giỏ mới, kho dư bỏ sau Shop. Cấp mua trong Shop chỉ vào `active_upgrades` khi dựng Ngày mới.

### 6.4 Giao diện `day_ctx` (sim ↔ day) — **#7, #8, #13, #14 dùng đúng chữ ký này**

```python
day_ctx = {"day": 1,                                  # 1..5
           "day_plan": {"day": 1, "dishes": {...}, "ingredients": {...}},
           "active_upgrades": {"oxygen": 0, "hp": 0}}  # cấp đang áp dụng (0 = chưa mua)

GatherSim(tuning, scenario, streams, ids, day_ctx=None)            # None = mode gather độc lập (Ngày 1, cấp 0)
QuanSim(tuning, scenario, streams, ids, inventory=None, day_ctx=None)
ShopSim(tuning, streams, ids, money, upgrades, day_ctx)            # #8; upgrades = cấp đã mua {"oxygen":n,"hp":n}
```

| Sim | Đọc gì trong `day_ctx` |
|---|---|
| gather (#13) | `active_upgrades` → `oxygen_max = upgrades.oxygen[lvl-1].oxygen_max_s` (cấp 0 dùng `oxygen_max_s`), `hp_max` tương tự; `day` cho monsters |
| monsters (#14) | `day` ≥ `spawns[].from_day` mới có con đó (gather độc lập = Ngày 1) |
| quan (#7) | `day_plan.dishes`: lọc menu theo id món trong kế hoạch **trước** khi lọc nguyên liệu khả dụng; `None` → dùng cả 6 món |
| shop (#8) | `money`, `upgrades` vào; ra thuộc tính `money`, `upgrades`, `done`, `reason` (`done`/`time`); `step(inp)` trả event `bought/buy_failed/shop_end` |

Mọi sim giữ giao diện runner hiện có: thuộc tính `mode, phase, done, reason, time_left_ticks, money, earned, reputation`, `snapshot()`, `step(inp) -> [(name, data)]`. `day.py` gán `money/earned/reputation` của pha trước vào sim mới **ngay sau khi dựng**; sim không reset lại sau đó. Gather thêm `inventory_items()` (đã có).

### 6.5 Output v1.1

Snapshot: `state` thêm `"paused"`. Gather thêm `monsters[]`, `player.invuln_ticks`. Trong `day` **mọi** snapshot có `day, day_plan, upgrades, active_upgrades`; `phase` ∈ `gather/quan/shop`; snapshot Shop có `stock` (dư từ ca) và `time_left_ticks`. Snapshot đổi pha ghi **pha mới** với `phase_tick:0`. Event kết thúc mang pha cũ. Trong `day` mọi event có thêm khóa `day`.

| `name` | `data` | Ai phát |
|---|---|---|
| `monster_hit` | `monster_id, hp, lost, pos` (vị trí người chơi; `lost` LIFO) | #14 |
| `fish_spawned` | `id, kind, pos` | #13 |
| `faint` | thêm `cause:"monster"` khi do chạm; `lost` = phần giỏ còn lại; `hp:0` | #13/#14 |
| `day_start`, `phase_start` | `{}` | day (#12) |
| `day_plan` | `dishes, ingredients` của Ngày đó | day (#12) |
| `paused`, `resumed` | `{}` | runner/day (#12) |
| `bought` | `upgrade, level, price, money` | shop (#8) |
| `buy_failed` | `action, reason` (`funds/max_level/out_of_stock/unknown`) | shop (#8) |
| `shop_end` | `reason` (`done`/`time`) | shop (#8) |

Dòng `end` của `day` thêm `days_completed`; đủ Ngày → `reason:"days_complete"`.

## Lịch sử đổi

| Ngày | Thay đổi | Lý do | Ai |
|---|---|---|---|
| 2026-11-21 | v1.0 chốt Phase 1 | Theo PRD-0 mục E/G | tuancdk |
| 2026-11-21 | v1.1 số chuẩn Phase 2, mode `day`, `day_ctx` | TICKET-02 mục 1–4 (#12) | tuancdk |

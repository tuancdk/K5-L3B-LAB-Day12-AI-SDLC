# Kế hoạch Phase 3 (TICKET-03 "Mùa Nước Nổi", 1:55–2:30, tag `phase-3`)

**Quyết định (phút 0–7, Integrator):** đổi kho từ **đếm theo loại** sang **mảng cá thể `{id, kind, fresh}`** (contract v1.2). Breaking change cho file kho, scenario `gather.hold`/`quan.stock`/`customers[].reserved`, snapshot `hold`/`stock`, event `gather_end.inventory`, `lost`. Schema chốt ở `docs/contracts/README.md` mục 7.

## Bảng tác động

| Module | File cần đổi | Test bị ảnh hưởng | Người |
|---|---|---|---|
| Contract + kho + adapter | `game.contract.json` (v1.2, `freshness`), `chonoi/inventory.py` (đọc/ghi v1.2), `chonoi/items.py` (adapter), `headless.py`, `runner.py` | `test_inventory_v12.py` (mới); test headless P1–P2 đổi fixture sang cá thể | tuancdk (#18) |
| Gather | `chonoi/sim/gather.py`: giỏ cá thể, hao 0.5/s (−2 đơn vị/tick), `spoiled` (location `hold`), `lost` cá thể | `test_gather_rules.py`, `test_gather_p2.py`, `test_monsters.py` | DoLyHoangNam (#19) |
| Quán + Shop | `chonoi/sim/quan.py`, `shop.py`: kho cá thể, hao 0.25/s, giữ chỗ theo id (tươi nhất, hòa id), giá theo độ tươi, `cook_started.items` cá thể, `spoiled` (location `stock`) | `test_quan_rules.py` | Hie24 (#20) |
| Validation | `chonoi/scenario.py`, `contract.py`: scenario/kho cá thể v1.2 → mã 2 | `test_validation*.py` | thd050810 (#21) |
| UI | `chonoi/web/`: HUD độ tươi / hàng ươn | — | thành viên UI (#22) |
| `day` | `chonoi/sim/day.py` + adapter: bàn giao cùng tick, id `I1…` xuyên pha/Ngày | `test_day_p2.py`, `test_inventory_v12.py` | tuancdk (#18) |

## Thứ tự tích hợp (để `main` luôn chạy)
1. **#18 (PR này)**: bật v1.2 + adapter ở biên headless — mọi **đầu ra/đầu vào** đúng schema cá thể ngay; luật bên trong vẫn đếm theo loại (fresh giữ 100, chưa hao). Test headless P1–P2 đổi fixture, ghi lý do.
2. **#19, #20** làm song song: sim giữ cá thể + hao tươi, xuất thuộc tính `items_hold` (gather) / `items_stock` (quán) → adapter tự dùng dữ liệu thật thay vì tự gán (không cần sửa runner).
3. **#21** làm chặt validation trên dữ liệu cá thể.
4. Integrator chạy smoke + regression, cập nhật `docs/verification/phase-3.md`, gắn tag.

**Rủi ro:** trước khi #19/#20 vào, `fresh` luôn 100 và không có `spoiled` → AC hao tươi/ươn/giá theo độ tươi chưa đạt; ghi trung thực ở verification.

# Changelog

Theo từng phase của lab. Tag: `phase-1` … `phase-4`; bản phát hành `v1.0.0` = `phase-4`.

## [1.0.0] — Phase 4 (TICKET-04, contract v1.3) — tag `phase-4`
### Thêm
- Contract **v1.3**: khai `bench_cmd` (`python3 -m chonoi.bench`) và `soak_cmd` (`python3 -m chonoi.soak`) ở gốc `game.contract.json`; `run_cmd` mở bản có giao diện ở mode `day`. Gameplay, tuning, kho, JSONL giữ như v1.2 (#30).
- Benchmark render thật cảnh lặn 1280×720, xuất `bench.json` 5 trường (#32, Hie24).
- Soak headless: bot tất định 10 Ngày trong một tiến trình, kế hoạch D1–D5 lặp ở Ngày 6–10, `soak.json` (#31, DoLyHoangNam).
- Ba cảnh báo chữ/biểu tượng (thủy quái gần, oxy sắp hết, khách sắp giận) + chế độ tương phản cao (phím H) (#34).
- `LICENSE` (MIT), release notes `docs/release/v1.0.0.md`, README chạy từ clone sạch trong 3 lệnh (#30).

## Phase 3 (TICKET-03 "Mùa Nước Nổi", contract v1.2) — tag `phase-3`
### BREAKING — kho cá thể
- File kho, `gather_end.data.inventory`, snapshot `hold`/`stock`, scenario `gather.hold`/`quan.stock`: từ object đếm / mảng kind sang **mảng cá thể** `{id, kind, fresh}`; `customers[].reserved` là mảng id; `lost` là mảng cá thể. File kho đếm cũ → mã 2 (#18).
- **Cập nhật fixture:** `["ca_loc","bong_sung"]` → `[{"id":"I1","kind":"ca_loc","fresh":100},{"id":"I2","kind":"bong_sung","fresh":100}]`; `{"items":{"ca_loc":1}}` → `{"items":[{"id":"I1","kind":"ca_loc","fresh":100}]}`. Test có helper `items(...)`, `stock_items({...})`, `assert_items_close` trong `tests/helpers.py`.
### Thêm
- `tuning.freshness {100, 0.5, 0.25, 30}`, event `spoiled`; adapter kho cá thể `chonoi/items.py`; id `I1…` xuyên pha/Ngày (#18).
- Giỏ cá thể, hao tươi 0.5/s, `spoiled`, `lost` cá thể (#19); mở rộng dòng nước lũ (#23) — DoLyHoangNam.
- Kho quán cá thể, hao 0.25/s, giữ chỗ theo id, giá theo độ tươi (#20, Hie24).
- Kiểm kho/scenario cá thể v1.2 → mã 2 (#21, thd050810).
### Sửa
- `main` đỏ 34 test khi #37/#38/#39 vào cùng lúc; file kho ghi `fresh` đủ chính xác (#41).

## Phase 2 (TICKET-02, contract v1.1) — tag `phase-2`
### Thêm
- Số chuẩn v1.1: 8 đàn cá bơi/sinh theo lịch, nút kèo nèo, Cá Sấu Năm Chèo (M1 từ Ngày 1, M2 từ Ngày 3), 2 bếp/4 bàn, 6 món, `day_plan` D1–D5, Shop nâng cấp oxy/Máu (#12, #13, #14, #7, #8).
- Mode `day` (`--days 1..5`): gather → quan → shop, đổi pha cùng tick, `days_complete`; pause ở cả ba mode; giao diện luồng Ngày v2 (#12, #16).
- Validation scenario/contract v1.1 → mã 2 (#15).

## Phase 1 (PRD-0, contract v1.0) — tag `phase-1`
### Thêm
- Hợp đồng tích hợp (`docs/contracts/README.md`), `TEAM.md`, kế hoạch + ma trận truy vết, skill `run-tests`, `headless-check` (#1).
- Buổi sáng: oxy, Máu, ngất, hái nút, bắt cá, giỏ LIFO (#2); buổi tối: khách, giữ chỗ, bếp, phục vụ, tiền, uy tín (#3, PR #6); kiểm mâu thuẫn → mã 2 (#4); cửa sổ chơi trình duyệt (#5).

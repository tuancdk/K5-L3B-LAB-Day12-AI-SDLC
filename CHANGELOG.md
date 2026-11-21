# Changelog
## Unreleased
### BREAKING — contract v1.2 (Phase 3, #18): kho cá thể
- File kho, `gather_end.data.inventory`, snapshot `hold`/`stock`, scenario `gather.hold`/`quan.stock`: từ object đếm / mảng kind sang **mảng cá thể** `{id, kind, fresh}`; `customers[].reserved` là mảng id; `lost` là mảng cá thể. File kho đếm cũ → mã 2.
- Thêm `tuning.freshness`, event `spoiled`.
- **Cập nhật fixture:** `["ca_loc","bong_sung"]` → `[{"id":"I1","kind":"ca_loc","fresh":100},{"id":"I2","kind":"bong_sung","fresh":100}]`; `{"items":{"ca_loc":1}}` → `{"items":[{"id":"I1","kind":"ca_loc","fresh":100}]}`. Test có helper `items(...)`, `stock_items({...})` trong `tests/helpers.py`.
- Hợp đồng tích hợp Phase 1 (`docs/contracts/README.md`): schema kho G, bảng event E, trường snapshot, giao diện sim↔UI (#1).
- Kế hoạch + ma trận truy vết Phase 1; skill `run-tests`, `headless-check`; smoke tích hợp `tests/test_integration_p1.py` (#1).
- Luật Quán Phase 1 (#3, PR #6).

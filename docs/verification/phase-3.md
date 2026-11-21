# Ma trận truy vết Phase 3

Chạy lại: `python3 .agents/skills/run-tests/run_tests.py --phase phase-3 --who <handle>` và `python3 .agents/skills/headless-check/headless_check.py --out docs/proof/phase-3/integration.txt`. Cập nhật lại trên commit gắn tag `phase-3`.

| AC | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| AC-P3-01 Bảng tác động + thứ tự tích hợp | `docs/plan/phase-3.md` | file kế hoạch | đạt |
| AC-P3-02 Hợp đồng v1.2 (schema, `spoiled`, `cook_started.items`, `lost`, `reserved`, 240 đơn vị/điểm) | `docs/contracts/README.md` mục 7 | file hợp đồng | đạt |
| AC-P3-03 `contract_version:"1.2"` + `freshness` | `ContractV12.test_version_and_freshness` | [tuancdk/unittest.log](../proof/phase-3/tuancdk/unittest.log) | đạt |
| AC-P3-04 Đọc kho v1.2: mã 2 cho file đếm, sai schema, kind lạ, id trùng, fresh ngoài miền; quán nhận nguyên id/fresh kể cả ươn, không áp sức chứa giỏ | `InventoryFile.*` | như trên | đạt |
| AC-P3-05 `--inventory-out` một lần, nguyên tử, ngất ghi rỗng, chạm `--ticks` giữ đích, sắp theo id, `gather_end.inventory` cùng schema | `SmokeHandover.*`, `test_faint_writes_empty_inventory_file…`, `test_inv_01_not_written_when_tick_limit_first` | như trên | đạt |
| AC-P3-06 `day`: bàn giao cùng tick, id `I1…` xuyên pha/Ngày, Ngày sau cấp id mới theo mẫu | `DayHandover.test_ids_increase_across_days_and_handover_same_tick` | như trên | đạt |
| AC-P3-07 Smoke bàn giao theo mẫu đề (fresh 100, interact frame 0 → `quan --inventory --ticks 0`, so id/kind/fresh) | `SmokeHandover.test_prd_smoke_file_then_quan_exact_items` + headless-check | [integration.txt](../proof/phase-3/integration.txt) | đạt — nhưng `fresh` còn 100 (chưa hao) tới khi có #19 |
| AC-P3-08 Hao tươi gather 0.5/s, `spoiled`, `lost` cá thể từ sim | test của #19 | _(#19)_ | chưa đạt — `lost` cá thể đã có qua adapter; hao tươi/`spoiled` chưa |
| AC-P3-09 Kho quán cá thể, giữ chỗ theo id, giá theo độ tươi | test của #20 | _(#20)_ | chưa đạt |
| AC-P3-10 Validation v1.2 | test của #21 | _(#21)_ | một phần — đọc kho/scenario cá thể có mã 2 (adapter) |
| AC-P3-11 HUD độ tươi | chơi thử | _(#22)_ | chưa đạt |
| AC-P3-12 Regression P1–P2 với v1.2; tag `phase-3` | toàn bộ test + headless-check 5/5 | [tuancdk/unittest.log](../proof/phase-3/tuancdk/unittest.log) | đạt trên nhánh; chưa gắn tag |

## Test đổi vì v1.2 (lý do: breaking change schema, không phải luật sai)
`test_smoke_p1`, `test_integration_p1`, `test_gather_rules` (GatherHeadless), `test_quan_rules` (QuanHeadless), `test_day_p2`, `test_validation`, `test_validation_p2` (+ fixture `later_day.json`), `test_contract_v11`: fixture/khẳng định chuyển từ đếm/kind sang mảng cá thể. Test unit gọi `Session` trực tiếp không đổi (adapter chỉ ở biên headless).

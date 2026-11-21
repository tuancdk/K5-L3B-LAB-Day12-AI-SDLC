# Kiểm chứng Phase 3 — Validation

Issue [#21](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC/issues/21) · nhánh `dothanh` · base `32f53d6`.

```sh
python3 .agents/skills/run-tests/run_tests.py --phase phase-3 --who thd050810
python3 .agents/skills/headless-check/headless_check.py --out docs/proof/phase-3/thd050810/headless-check.txt
```

**189/189 unittest đạt**, gồm 11 test validation Phase 3. **5/5 headless-check đạt** với manifest v1.2 trên `main`. Smoke live cũng ghi kho cá thể từ Gather và đọc lại kho đó trong Quán. [Log unittest](thd050810/unittest.log) · [Log headless](thd050810/headless-check.txt)

| Fixture | Ca bị từ chối qua CLI v1.2 | Mã thoát | File đầu ra |
| --- | --- | --- | --- |
| `validation-p3/inventory.json`, `validation-p3/invalid-nan.json` | 17 ca về schema kho, ID, kind và fresh hữu hạn trong [0, 100] | 2 | Không tạo JSONL |
| `validation-p3/scenarios.json` | 8 ca về schema của `gather.hold` và `quan.stock` | 2 | Không tạo JSONL hoặc file kho được yêu cầu |
| `validation-p3/reservations.json` | 12 ca về ID giữ chỗ và payload món, thêm 1 lần kiểm ID đã ươn với kho truyền qua `--inventory` | 2 | Không tạo JSONL |
| `validation-p3/freshness.json` | 9 ca về khóa bắt buộc, tốc độ hao, độ tươi khởi tạo và ngưỡng ươn | 2 | Không tạo JSONL hoặc file kho |
| `validation-p2/scenarios.json` | ID giữ chỗ bị thiếu khi Gather bàn giao kho thực tế | 2 | Không tạo JSONL |

Test dương xác nhận Gather giữ ID, độ tươi và thứ tự ở tick 0. Validator nhận hàng tươi đúng ngưỡng và giữ giá đã chốt trong payload món. Nếu fixture bỏ `reserved`, adapter cấp theo `order_tick`, ID bàn và kho còn tươi. Đơn thiếu hàng chuyển sang `unfulfillable`. Trong `day`, test hộp đen xác nhận một cá thể tươi đúng ngưỡng ở tick 0 bị từ chối nếu vừa ươn trước lúc vào Quán.

## Bàn giao

`headless.py` và `live.py` dùng chung bộ đọc và validator v1.2. `sim/day.py` gọi validator trên kho cá thể Gather bàn giao trước khi chuyển sang số lượng cho Quán. Adapter nằm ở `items.py`, dùng lại bộ kiểm tra schema kho trong `inventory.py`.

Fixture kho ngoài, fixture thiếu kho khi đổi pha và fixture giao món ở tick đóng cửa dùng mảng ID theo v1.2 để tiếp tục kiểm đúng ca gốc. Luật Quán giữ và tiêu đúng ID trong lúc chạy, hao tươi kho và tính giá khi bắt đầu nấu thuộc [#20](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC/issues/20).

# Kiểm chứng Phase 2 — Validation

Issue [#15](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC/issues/15) · nhánh `codex/dothanh-p2` · `main` tại `935446d`.

```sh
python3 .agents/skills/run-tests/run_tests.py --phase phase-2 --who thd050810
python3 .agents/skills/headless-check/headless_check.py --out docs/proof/phase-2/thd050810/headless-check.txt
```

Toàn bộ **110 test đạt**, gồm 7 test mới và các test hồi quy P1. [Log unittest](thd050810/unittest.log)

Headless đạt **5/5 kiểm tra**, gồm so sánh từng byte giữa hai lần chạy cùng seed, bàn giao kho Gather → Quán và hoàn tất một Ngày ở tick 22.200. [Log headless-check](thd050810/headless-check.txt)

| Fixture | Trường hợp | Mã thoát | Đầu ra |
| --- | --- | --- | --- |
| `tests/fixtures/validation-p2/scenarios.json` | 15 ca day gồm tiền, uy tín, nâng cấp, kế hoạch, khóa cấm của quán, kho thiếu hoặc mất do ngất và món ngoài kế hoạch | 2 | Không tạo JSONL |
| `tests/fixtures/validation-p2/gather.json` | 17 ca Gather gồm bộ đếm, khóa mở rộng khi tắt, tuổi và độ sâu cá, ID/loài/waypoint/trạng thái quái và hướng recoil | 2 | Không tạo JSONL hoặc file kho |
| `tests/fixtures/validation-p2/contract.json` | 14 ca sửa một trường trên bản sao contract gồm phiên bản, menu, kế hoạch, shop, cá và loài quái | 2 | Không tạo JSONL hoặc file kho |
| `tests/fixtures/validation-p2/later_day.json` | Món hợp lệ ở Ngày 1 nhưng ngoài kế hoạch khi quán mở ở Ngày 2 | 2 | Giữ nguyên JSONL có sẵn |
| Ma trận cờ trong `test_validation_p2.py` | 9 tổ hợp `--days`, `--inventory` và `--inventory-out` sai mode hoặc sai giá trị | 2 | Không tạo file đầu ra |

Test dương xác nhận kế hoạch thay thế được tính lại nguyên liệu, quán nhận cá kèo vừa bắt trong cùng ngày và file kho v1.1 đọc được cả `ca_keo` lẫn `keo_neo`.

Headless ghi tạm riêng cho mode `day` vì kho thực chỉ có lúc kết thúc Gather. File JSONL đích được thay thế sau khi lượt chạy thành công. Hai fixture Gather P1 đổi độ sâu cá linh từ 2 sang 3 để nằm trong dải v1.1. Các assertion bắt cá, cập bến, bàn giao kho và tính tất định vẫn được chạy.

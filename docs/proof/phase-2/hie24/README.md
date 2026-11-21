# Phase 2 — Quán & Shop — Hie24

21/11/2026 · Nhánh `hie24/phase-2-quan-shop`, đã merge `main` **b7f0161** (base ban đầu **20d41ee**).
Nguồn: [TICKET-02](https://claude.ai/artifact/E35v787wSx2wDgPTNhMVDg#phase-2), [#7](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC/issues/7), [#8](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC/issues/8), hợp đồng tích hợp v1.1 mục 6.4.

**Kết quả:** [156/156 test pass](unittest.log) (126 test nền + 11 test Quán + 19 test Shop), exit 0.
[5/5 headless check pass](headless-check.txt); một Ngày hoàn tất ở tick **22.200**, **0,70 s** trên Windows/Python 3.13.5.
Các log kiểm cây làm việc sau merge b7f0161, trước commit merge; [SHA-256](sources.sha256) ghi nhận đúng bốn file code/test đã kiểm.

| Phạm vi | Nội dung đã kiểm | Kết quả |
|---|---|---|
| #7 Quán | B2/T1–T4, 6 công thức, đơn không trùng giữa hai bếp, lịch/ID, tương tác và chín cùng tick | Đạt |
| #7 Kế hoạch | Nhận `day_ctx`; lọc ID món trước kho; không giới hạn số suất, không thưởng kế hoạch; standalone dùng đủ menu | Đạt |
| #8 Shop | Mua từng cấp oxy/Máu, đủ đúng giá, thiếu tiền/max/unknown, giữ earned/uy tín, mua trước đóng kể cả tick cuối | Đạt |
| #8 Tích hợp day | ShopSim được day.py gọi thật; kho dư; pause; giữ cạnh nút qua pha; nâng cấp chỉ áp dụng Ngày kế; Shop cuối mới chốt Ngày | Đạt |
| Regression | Toàn bộ test nền; cùng seed giống byte; gather → kho → quan; day nhiều Ngày | Đạt |

Chỉ sửa `sim/quan.py`, tạo `sim/shop.py`, bổ sung test trong `test_quan_rules.py` và tạo `test_shop_rules.py`.
Giữ nguyên runner, day.py, contract, validation, UI và các test cũ.
Shop dùng `ShopSim(tuning, streams, ids, money, upgrades, day_ctx)` theo hợp đồng và lời gọi thực tế trên main, thay chữ ký cũ trong issue #8.
Chưa bật mở rộng; chưa kiểm CI Linux/test ẩn. Codex hỗ trợ triển khai và kiểm chứng; không đo token/chi phí.

Chạy lại từ gốc repo (Windows cần `python3.exe` trong PATH theo AGENTS.md):

```sh
python3 .agents/skills/run-tests/run_tests.py --phase phase-2 --who hie24
python3 .agents/skills/headless-check/headless_check.py --out docs/proof/phase-2/hie24/headless-check.txt
```

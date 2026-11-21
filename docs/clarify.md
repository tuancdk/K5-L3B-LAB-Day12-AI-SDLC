# Clarify — câu hỏi và câu trả lời (PO ghi, cả nhóm dùng chung)

Hỏi Anh Năm (trợ giảng AI trên lab board) trước; chưa có trả lời thì ghi giả định nhóm đang dùng và người quyết tạm.

| # | Ngày giờ | Câu hỏi | Trả lời / giả định | Ai quyết |
|---|---|---|---|---|
| 1 | 2026-11-21 P2 | Cá mới sinh (đầu ca và theo lịch) có hướng ban đầu thế nào? PRD chỉ ghi "lấy hướng ban đầu theo seed". | Giả định: chọn đều trong [0, 360) độ theo seed (luồng `fish_spawn`), làm tròn 3 chữ số. Chờ Anh Năm xác nhận. | tuancdk (tạm) |
| 2 | 2026-11-21 P2 | Trong `day`, khối `scenario.gather`/`quan` là mẫu cho **mọi** Ngày hay chỉ Ngày 1? | Theo TICKET-02 4.3 "làm mẫu khởi tạo mỗi Ngày": áp dụng cho mọi Ngày. | tuancdk |
| 3 | 2026-11-21 P2 | Snapshot có bắt buộc ghi ở tick đổi pha không (ngoài bội số `--snapshot-every`)? | Giả định không bắt buộc; khi có snapshot ở tick đó thì ghi pha mới, `phase_tick:0`. | tuancdk (tạm) |
| 4 | 2026-11-21 P2 | Xử lý các trường mở rộng của fixture khi lõi chưa bật tính năng như thế nào? | Từ chối `ca_ho`, `random_ho` và `attack_cd_ticks` với mã 2. Tạm ánh xạ Lao/Sổ tay sang `weapon`/`handbook` trong `extensions`; cần chốt ID với Integrator khi bật các mở rộng. | thd050810 (tạm) |
| 5 | 2026-11-21 P3 | Chuỗi id cá thể `I1…` có chung bộ đếm với id khác (khách `C`, cá `F`) không? | Giả định: họ `I` riêng (IdAllocator theo tiền tố), tăng xuyên pha/Ngày. | tuancdk (tạm) |
| 6 | 2026-11-21 P3 | Khi một loại trong kho quán giảm (nấu), dùng cá thể nào? | Theo TICKET-03: tươi nhất, hòa theo id. | tuancdk |
| 7 | 2026-11-21 P4 | `load_ms` của bench tính từ lúc nào: tiến trình `bench_cmd` khởi chạy (gồm thời gian mở trình duyệt/công cụ) hay lúc trang bắt đầu tải? | Giả định: từ lúc tiến trình khởi chạy tới frame cảnh đầu tiên — số thật 41.8 s gồm thời gian công cụ mở tab ([hie24](proof/phase-4/hie24/README.md)). | Hie24 (tạm) |
| 8 | 2026-11-21 P4 | Máy chấm chạy `bench_cmd` thế nào: tự mở trình duyệt mặc định, hay automation với `--no-open` + viewport 1280×720? Trình duyệt nào, có màn hình không? | Giả định: mặc định mở trình duyệt hệ thống; `--no-open` in `BENCH_URL` cho automation. | Hie24 (tạm) |
| 9 | 2026-11-21 P4 | Ba mốc bench (avg ≥ 60, 1% low ≥ 30, load ≤ 10 s) chỉ để báo cáo hay bị trừ điểm khi chưa đạt? | Theo đề "dùng để báo cáo": điểm dựa trên chạy được lệnh và `bench.json` đúng. Ghi số thật, 1% low và load chưa đạt. | tuancdk |
| 10 | 2026-11-21 P4 | `soak_cmd --days` có giới hạn trên không? Headless `day` chỉ nhận 1–5, còn soak chạy 10. | Giả định: soak nhận mọi số nguyên ≥ 1; kế hoạch D1–D5 lặp theo chu kỳ 5. | DoLyHoangNam (tạm) |
| 11 | 2026-11-21 P4 | `results[].earned` và `score` trong `soak.json` là **cộng dồn** tới Ngày đó hay **riêng** Ngày đó? | Giả định: cộng dồn, chốt tại lúc Shop đóng (cùng nghĩa `earned` trong JSONL). | DoLyHoangNam (tạm) |
| 12 | 2026-11-21 P4 | Bot soak có cần hành vi tối thiểu (bán được món, mua nâng cấp) hay chỉ cần tất định và không crash? | Giả định: tiêu chí đạt là `days_completed = days` và `crashes = 0`; bot vẫn chơi có thu (Ngày 10 `earned` 2292). | DoLyHoangNam (tạm) |
| 13 | 2026-11-21 P4 | Ngưỡng của ba cảnh báo có chuẩn không? | Giả định theo HUD Phase 2: thủy quái gần = đang `chase` hoặc trong `detect_radius`; oxy sắp hết = ≤ 25% oxy tối đa khi dưới nước; khách sắp giận = kiên nhẫn < 25%. | Minhduc7904 (tạm) |
| 14 | 2026-11-21 P4 | Sửa lỗi sau khi đã phát hành: giữ tag `phase-4`/`v1.0.0` và ra `v1.0.1`, hay dời tag `phase-4`? | Giả định: giữ nguyên `phase-4` = `v1.0.0`; bản vá uy tín float phát hành `v1.0.1` trên commit mới. | tuancdk |
| 15 | 2026-11-21 P4 | Tag `phase-2`, `phase-3` gắn sau hạn của phase thì chấm thế nào; có nên dời tag? | Giả định: giữ tag ở commit bàn giao, ghi trung thực giờ gắn và phần chưa đạt trong `docs/verification/phase-*.md`. | tuancdk |
| 16 | 2026-11-21 P4 | "Tối đa 3 lệnh" từ clone sạch có tính `git clone` và `cd` không? | Giả định tính cả clone và cd. Kiểm thử trên macOS gặp cổng 8000 đang được dùng. Có thể dùng `python3 -m chonoi.live --mode day --port 0` làm lệnh thứ ba. [Log clone sạch](proof/phase-4/thd050810/clean-clone.txt). | tuancdk |
| 17 | 2026-11-21 P4 | Zip mã nguồn (`git archive`) kèm hướng dẫn có đủ là "bản đóng gói chạy được", hay cần gói kèm Python/trình chạy? | Giả định: zip mã nguồn đủ; yêu cầu Python 3.10+ ghi trong README và release notes. | tuancdk |

> 2026-11-21 (P2): thử hỏi Anh Năm câu 1–3 trên lab board, trợ giảng trả lời "Anh chưa sẵn sàng cho Phase 2. Giảng viên sẽ mở sớm." → giữ giả định, hỏi lại khi mở.
>
> Ghi chú sửa bảng (P4): trước đây có hai câu cùng số 4 và dòng ghi chú chen giữa bảng làm vỡ hiển thị; đánh số lại 1–6, nội dung không đổi.

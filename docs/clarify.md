# Clarify — câu hỏi và câu trả lời (PO ghi, cả nhóm dùng chung)

| # | Ngày giờ | Câu hỏi | Trả lời / giả định | Ai quyết |
|---|---|---|---|---|
| 1 | 2026-11-21 P2 | Cá mới sinh (đầu ca và theo lịch) có hướng ban đầu thế nào? PRD chỉ ghi "lấy hướng ban đầu theo seed". | Giả định: chọn đều trong [0, 360) độ theo seed (luồng `fish_spawn`), làm tròn 3 chữ số. Chờ Anh Năm xác nhận. | tuancdk (tạm) |
| 2 | 2026-11-21 P2 | Trong `day`, khối `scenario.gather`/`quan` là mẫu cho **mọi** Ngày hay chỉ Ngày 1? | Theo TICKET-02 4.3 "làm mẫu khởi tạo mỗi Ngày": áp dụng cho mọi Ngày. | tuancdk |
| 3 | 2026-11-21 P2 | Snapshot có bắt buộc ghi ở tick đổi pha không (ngoài bội số `--snapshot-every`)? | Giả định không bắt buộc; khi có snapshot ở tick đó thì ghi pha mới, `phase_tick:0`. | tuancdk (tạm) |
| 4 | 2026-11-21 P2 | Xử lý các trường mở rộng của fixture khi lõi chưa bật tính năng như thế nào? | Từ chối `ca_ho`, `random_ho` và `attack_cd_ticks` với mã 2. Tạm ánh xạ Lao/Sổ tay sang `weapon`/`handbook` trong `extensions`; cần chốt ID với Integrator khi bật các mở rộng. | thd050810 (tạm) |

> 2026-11-21 (P2): thử hỏi Anh Năm câu 1–3 trên lab board, trợ giảng trả lời "Anh chưa sẵn sàng cho Phase 2. Giảng viên sẽ mở sớm." → giữ giả định ở trên, hỏi lại khi mở.
| 4 | 2026-11-21 P3 | Chuỗi id cá thể `I1…` có chung bộ đếm với id khác (khách `C`, cá `F`) không? | Giả định: họ `I` riêng (IdAllocator theo tiền tố), tăng xuyên pha/Ngày. | tuancdk (tạm) |
| 5 | 2026-11-21 P3 | Khi một loại trong kho quán giảm (nấu), dùng cá thể nào? | Theo TICKET-03: tươi nhất, hòa theo id. Adapter áp dụng đúng quy tắc này tới khi #20 giữ cá thể trong sim. | tuancdk |

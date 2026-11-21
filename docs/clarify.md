# Clarify — câu hỏi và câu trả lời (PO ghi, cả nhóm dùng chung)

| # | Ngày giờ | Câu hỏi | Trả lời / giả định | Ai quyết |
|---|---|---|---|---|
| 1 | 2026-11-21 P2 | Cá mới sinh (đầu ca và theo lịch) có hướng ban đầu thế nào? PRD chỉ ghi "lấy hướng ban đầu theo seed". | Giả định: chọn đều trong [0, 360) độ theo seed (luồng `fish_spawn`), làm tròn 3 chữ số. Chờ Anh Năm xác nhận. | tuancdk (tạm) |
| 2 | 2026-11-21 P2 | Trong `day`, khối `scenario.gather`/`quan` là mẫu cho **mọi** Ngày hay chỉ Ngày 1? | Theo TICKET-02 4.3 "làm mẫu khởi tạo mỗi Ngày": áp dụng cho mọi Ngày. | tuancdk |
| 3 | 2026-11-21 P2 | Snapshot có bắt buộc ghi ở tick đổi pha không (ngoài bội số `--snapshot-every`)? | Giả định không bắt buộc; khi có snapshot ở tick đó thì ghi pha mới, `phase_tick:0`. | tuancdk (tạm) |

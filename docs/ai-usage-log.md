# Nhật ký dùng AI (theo phase và theo người)

| Phase | Người | Công cụ / model | Việc | Token / chi phí ước tính | Ghi chú (AI sai ở đâu?) |
|---|---|---|---|---|---|
| 2 | tuancdk | Claude Code (Claude Opus 5.5) | #12: đọc TICKET-02 trên lab board, contract v1.1, `sim/day.py`, pause ở runner, CLI `--days`, test day/pause, smoke | không đo | Ban đầu test P1 cũ (`test_team_check`) đỏ từ khi điền TEAM.md mà P1 không phát hiện vì chạy test trước khi điền; đã sửa và ghi lý do |
| 3 | tuancdk | Claude Code (Claude Opus 5.5) | #18: đọc TICKET-03, contract v1.2, đọc/ghi kho cá thể, adapter `items.py`, đổi fixture test P1–P2, test v1.2 | không đo | Lần đầu bật v1.2 làm 101 test đỏ vì `load_contract` (#15) chỉ nhận đúng `"1.1"` — phát hiện qua chạy test, sửa cho nhận `"1.2"` |
| 1 | DoLyHoangNam | Antigravity (Gemini) | #2: luật buổi sáng `sim/gather.py` (oxy, ngạt `t+59`, ngất LIFO, hái nút, bắt cá), 17 test `test_gather_rules.py` | không đo | Đối chiếu trực tiếp PRD-0 mục E/F/G; chạy smoke + kiểm tra tất định 2 lần cùng seed xanh |
| 2 | DoLyHoangNam | Antigravity (Gemini) | #13/#14: cá bơi/phản xạ/sinh theo lịch `gather.py`, Cá Sấu Năm Chèo `sim/monsters.py`, 16 test mới | không đo | AI viết `dist <= step_len` trong `monsters._move_toward` lệch 1 tick ở mốc 240 tick do sai số float `1.0/60.0` — test bắt được và sửa bằng `1e-9` |
| 3 | DoLyHoangNam | Antigravity (Gemini) | #19/#23: giỏ cá thể + hao tươi `Fraction`, `spoiled`, mở rộng Dòng nước lũ `current`, 10 test mới | không đo | `fresh` cần tính bằng `Fraction` chính xác 240 đơn vị/điểm thay vì float; sau khi PR #37 bật adapter v1.2, test phát hiện lệch giữa `gather.use_items` và adapter, đã phối hợp Integrator chốt ở PR #41 |
| 4 | DoLyHoangNam | Antigravity (Gemini) | #31: `chonoi/soak.py` (bot tất định 10 Ngày, cô lập crash, `soak.json`), mở rộng `day.py` cho soak, `test_soak.py` | không đo | Chạy thật 10 Ngày 2 lần cùng seed xác nhận giống hệt mọi trường trừ `duration_s`, `--mode day --days 6` vẫn mã 2 |

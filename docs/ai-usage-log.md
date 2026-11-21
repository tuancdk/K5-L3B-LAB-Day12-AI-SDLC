# Nhật ký dùng AI (theo phase và theo người)

| Phase | Người | Công cụ / model | Việc | Token / chi phí ước tính | Ghi chú (AI sai ở đâu?) |
|---|---|---|---|---|---|
| 2 | tuancdk | Claude Code (Claude Opus 5.5) | #12: đọc TICKET-02 trên lab board, contract v1.1, `sim/day.py`, pause ở runner, CLI `--days`, test day/pause, smoke | không đo | Ban đầu test P1 cũ (`test_team_check`) đỏ từ khi điền TEAM.md mà P1 không phát hiện vì chạy test trước khi điền; đã sửa và ghi lý do |
| 3 | tuancdk | Claude Code (Claude Opus 5.5) | #18: đọc TICKET-03, contract v1.2, đọc/ghi kho cá thể, adapter `items.py`, đổi fixture test P1–P2, test v1.2 | không đo | Lần đầu bật v1.2 làm 101 test đỏ vì `load_contract` (#15) chỉ nhận đúng `"1.1"` — phát hiện qua chạy test, sửa cho nhận `"1.2"` |

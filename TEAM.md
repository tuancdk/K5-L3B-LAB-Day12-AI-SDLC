# TEAM

**Tên nhóm:** xem `team` trong `game.contract.json`  **Số người:** 4 (khớp `team_size` trong `game.contract.json`; thành viên thứ 5 phụ trách UI sẽ được thêm khi có GitHub handle)

| Thành viên | GitHub handle | Module chính | Vai quy trình | Người dự phòng cho |
|---|---|---|---|---|
| Le Anh Tuan | tuancdk | `docs/contracts` + harness (#1) | PO · Integrator · Scrum/Release | thd050810 |
| Đỗ Lý Hoàng Nam | DoLyHoangNam | `sim/gather` (#2) | Dev | Hie24 |
| Nguyễn Đức Hiếu | Hie24 | `sim/quan` (#3) | Dev | DoLyHoangNam |
| Đỗ Minh Thanh | thd050810 | `qa` — validation `scenario.py`/`contract.py` (#4) | QA lead | tuancdk |

**Vai quy trình:** PO (đầu mối hỏi giảng viên, giữ `docs/clarify.md`) · Integrator (giữ `docs/contracts/`, gắn tag) · QA lead · Scrum/Release. Có thể kiêm.

## Thỏa thuận làm việc nhóm

- Kênh liên lạc: nhóm Zalo của team.
- Khi bất đồng về thiết kế: nói tối đa 2 phút; chưa xong thì Integrator (tuancdk) quyết và ghi lý do vào `docs/contracts/` hoặc `docs/adr/`.
- Khi ai đó trễ hoặc vướng quá 10 phút: báo ngay trên Zalo; người dự phòng (cột cuối) vào hỗ trợ.
- Giờ standup giữa phase: phút 20 mỗi phase, 2–3 phút, ghi vào `docs/standup.md`.
- Cách đọc code của nhau: mỗi PR có ít nhất một người khác đọc; đổi hợp đồng thì Integrator phải duyệt.
- Cách làm việc với Git: nhánh ngắn `<handle>/<phase>-<việc>` → PR vào `main` (ghi `Closes #n`); chạy skill `run-tests` trước khi push; chỉ tuancdk gắn tag `phase-n`.

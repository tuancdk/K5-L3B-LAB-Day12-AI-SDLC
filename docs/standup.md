# Standup giữa phase (mỗi người một dòng, 2–3 phút)

> **Ghi chú trung thực:** trong buổi lab nhóm standup miệng/qua Zalo và **không ghi vào file này đúng giờ**. Bảng dưới được **ghi lại sau** (21/11/2026, sau tag `v1.0.1`), dựng từ lịch sử commit giữa các tag, PR, issue, `docs/retro.md` và `docs/ai-usage-log.md`. "Đã xong" là việc đã có commit trong phase đó; "Vướng" chỉ ghi những gì có dấu vết trong repo, không có thì để "—". Mỗi người nên đọc lại và sửa dòng của mình.

| Phase | Người | Đã xong | Sắp làm | Vướng gì |
|---|---|---|---|---|
| 1 | tuancdk | Hợp đồng `docs/contracts/`, TEAM, `docs/plan/phase-1.md`, `AGENTS.md`, skill `run-tests` + `headless-check` (#1); cửa sổ chơi + HUD (#5) | Smoke dock → quán trên `main`, ma trận truy vết, gắn tag `phase-1` | TEAM.md mới 4/5 người, thiếu mã nhóm; `test_team_check` đỏ sau khi điền TEAM.md (sửa ở #26); tag `phase-1` trễ mốc 1:00 |
| 1 | DoLyHoangNam | Lặn/nổi, oxy, ngạt, ngất; hái nút, bắt cá, giỏ LIFO `sim/gather.py` + 17 test (#2) | Ghi bằng chứng P1; cá bơi/sinh theo lịch ở P2 | — |
| 1 | Hie24 | Luật quán `sim/quan.py`: khách, giữ chỗ, bếp, phục vụ, tiền, uy tín + 31 test (#3, PR #6) | Quán 2 bếp/4 bàn/6 món (P2) | Review PR #6 chỉ ra uy tín cộng float lệch `floor`; chưa sửa (sửa ở PR #51, sau tag `phase-4`) |
| 1 | thd050810 | Kiểm mâu thuẫn scenario/contract → mã 2 (#4, PR #17) | Kiểm cờ CLI, kế hoạch Ngày cho contract v1.1 (#15) | — |
| 2 | tuancdk | Contract v1.1 số chuẩn, `mode day --days 1..5`, pause cả ba mode, smoke P2 (#12) | Luồng Ngày + giao diện v2 (#16), contract v1.2 (#18) | Số chuẩn v1.1 buộc sửa file của người khác; rebase với validation #17 phải gỡ xung đột tay; hỏi Anh Năm câu clarify 1–3 nhưng phase chưa mở → giữ giả định |
| 2 | DoLyHoangNam | Cá bơi/phản xạ/sinh theo lịch, nhận nâng cấp `day_ctx` (#13); Cá Sấu Năm Chèo `sim/monsters.py` + 16 test (#14) | Giỏ cá thể + hao tươi (#19), Dòng nước lũ (#23) | `_move_toward` lệch 1 tick ở mốc 240 do float `1/60` — test bắt được, sửa bằng `1e-9` |
| 2 | Hie24 | Quán theo kế hoạch Ngày (#7), Shop nâng cấp (#8) — commit xong cuối phase | Kho cá thể, giá theo độ tươi (#20) | PR #39 vào `main` sau tag `phase-2` |
| 2 | thd050810 | Kiểm cờ CLI, kế hoạch Ngày, chuyển Ngày (#15, PR #28) | Kiểm kho/scenario cá thể v1.2 (#21) | — (về sau: `load_contract` chỉ nhận đúng `"1.1"`, làm 101 test đỏ khi lên v1.2) |
| 3 | tuancdk | Contract v1.2 kho cá thể + adapter (#18); luồng Ngày + UI v2, lớp Phaser 3 (#16); sửa `main` đỏ (PR #41) | Contract v1.3, release (#30); cảnh báo + tương phản cao (#34) | Bật v1.2 làm 101 test đỏ; #37 + #38 + #39 gộp gần cùng lúc làm `main` đỏ 34 test |
| 3 | DoLyHoangNam | Giỏ cá thể `{id, kind, fresh}`, hao tươi `Fraction`, `spoiled` (#19); Dòng nước lũ (#23); bắt đầu soak (#31) | Soak 10 Ngày tất định (#31) | Lệch giữa `gather.use_items` và adapter v1.2 → chốt với Integrator ở PR #41 |
| 3 | Hie24 | Bằng chứng quán + shop P2 (#7, #8) | Kho cá thể hao 0.25/s, giữ chỗ theo id, giá theo độ tươi (#20); bench (#32) | Phần quán v1.2 chưa vào trước tag `phase-3` (vào ở PR #44, trong P4) |
| 3 | thd050810 | — (chưa có commit trước tag `phase-3`) | Kiểm kho/scenario cá thể v1.2 → mã 2 (#21, PR #43) | Validation v1.2 vào `main` sau tag `phase-3` |
| 4 | tuancdk | Contract v1.3, CHANGELOG, LICENSE, README 3 lệnh, release notes (#30); cảnh báo + tương phản cao (#34); HUD độ tươi (#22) | Gắn tag `phase-4` + Release `v1.0.0`; retro | `browser-check.py --mode quan` timeout (về sau xác định do script đọc `customers[0]`); tag `phase-4` gắn lúc 13:56, trễ mốc |
| 4 | DoLyHoangNam | Soak 10 Ngày tất định, cô lập crash, `soak.json` (#31); phản tư cá nhân + nhật ký AI | — | — |
| 4 | Hie24 | Kho cá thể v1.2 (#20); `chonoi.bench` + đo thật (#32) | Phản tư cá nhân, nhật ký AI | Bench 1% low 21.7 FPS và load 41.8 s chưa đạt mốc (ghi số thật) |
| 4 | thd050810 | Validation v1.2 (#21, PR #43) | QA clone sạch, verification phase-4, điều phối retro (#33) | #33 chưa xong trước tag `phase-4`, bổ sung sau |
| 4 | Minhduc7904 | Vào nhóm sau tag `phase-4` (PR #50); clone sạch tag `v1.0.0` trên Windows, kiểm lại UI quán (PR #52) | Phản tư cá nhân + nhật ký AI | PR #52 chưa được merge |

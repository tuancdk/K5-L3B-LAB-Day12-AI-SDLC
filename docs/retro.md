# Retro nhóm

> **Ghi chú trung thực:** retro Phase 1 và Phase 3 **không được viết trong buổi lab**. Hai mục dưới được Integrator (tuancdk) viết sau tag `v1.0.1` (21/11/2026), dựng từ giờ commit, giờ merge PR, `docs/verification/phase-1.md`, `docs/verification/phase-3.md` và `docs/standup.md`. Mỗi người đọc lại và sửa nếu thấy sai.

## Phase 1 — viết lại sau (tuancdk)
- **Điều tốt:**
  - Quán (#3) xong sớm nhất: Hie24 có commit lúc 09:58, PR #6 merge lúc 10:22.
  - Hợp đồng tích hợp (PR #9, 10:49) có schema kho và bảng event. Nhờ đó smoke gather → kho → quán (AC-P1-10) đạt ngay lần chạy đầu.
  - Ma trận `verification/phase-1.md` ghi thật các AC "chưa đạt" thay vì đánh dấu đạt hết.
- **Điều tệ:**
  - Hie24 viết quán **trước** khi hợp đồng được merge (09:58 so với 10:49). Lần này khớp, nhưng nếu hợp đồng đổi thì phải làm lại.
  - Gather (#11), UI (#10) và validation (#17) cùng vào `main` trong khoảng 11:01–11:13, sát giờ tag. Tag `phase-1` gắn lúc 11:21, trễ mốc.
  - Tag gắn vào commit sửa `test_team_check` trên nhánh `tuancdk/p1-fix-team-test`. Lúc đó PR #26 chưa merge vào `main`. Test này đỏ vì Integrator chạy test trước khi điền TEAM.md.
  - Ở tag, TEAM.md mới có 4/5 người và `team` vẫn là `ten-nhom`. Lát UI (#5) không có người nhận, nên Integrator tự làm bằng Codex.
  - Review PR #6 đã thấy lỗi uy tín cộng float, nhưng không mở issue. Kết quả là lỗi này nằm tới sau tag `phase-4`.
- **1 hành động cho Phase 2:** mỗi nhận xét review chỉ ra lỗi phải thành một issue có người nhận trước khi merge (người nhận: tuancdk). *Kết quả:* không làm. Lỗi float chỉ được sửa ở PR #51.

## Phase 2 (nhanh) — bản nháp của Integrator (tuancdk), cả nhóm bổ sung
- Điều tốt: chia theo vùng file nên P1 gather/quan/validation/UI làm song song, ít xung đột; hợp đồng chốt sớm (`docs/contracts/`) giúp smoke gather → kho → quán đạt ngay lần đầu; contract v1.1 mở PR riêng (#24) trước khi viết `day` để các lát dùng số chuẩn sớm.
- Điều tệ: tag `phase-1` không được đẩy đúng 1:00; `test_team_check` đỏ trên `main` từ khi điền TEAM.md vì Integrator chạy test **trước** khi điền và không chạy lại trước khi push; số chuẩn v1.1 buộc sửa file của người khác (gather/contract/scenario/test quán) để `main` không đỏ; rebase với validation #17 phải gỡ xung đột tay.
- 1 hành động cho Phase 3: chạy skill `run-tests` **ngay trước** mỗi push và gắn tag ở phút 50 dù còn lát dở (người nhận: tuancdk).

## Phase 3 — viết lại sau (tuancdk)
- **Rà lại hành động Phase 2** (*chạy `run-tests` ngay trước mỗi push, gắn tag ở phút 50*): làm một phần. Mỗi PR đều xanh khi chạy riêng, nhưng không ai chạy lại test trên `main` sau khi merge.
- **Điều tốt:**
  - DoLyHoangNam làm gather v1.2 rất sớm: giỏ cá thể, hao tươi bằng `Fraction`, `spoiled` (#19), cùng mở rộng Dòng nước lũ (#23). Tất cả đã có commit lúc 11:45–11:47 và còn bắt đầu luôn soak (#31).
  - Contract v1.2 (PR #37) ghi rõ đây là breaking change. Nhóm dùng adapter ở biên headless để không phải viết lại toàn bộ test unit, và ghi danh sách test đổi kèm lý do trong `verification/phase-3.md`.
  - `verification/phase-3.md` ghi thật: AC-P3-09 (quán), AC-P3-10 (validation) và AC-P3-11 (HUD) là "chưa đạt" hoặc "một phần".
- **Điều tệ:**
  - Việc của Phase 2 tràn sang Phase 3: quán và shop (#39, Hie24) cùng UI v2 (#40) đến 12:06 và 12:14 mới vào `main`, tức là sau tag `phase-2` (11:47).
  - #37, #38 và #39 được merge trong vòng 8 phút (11:58–12:06) làm `main` đỏ 34 test. Bản sửa PR #41 xong lúc 12:19, và tag `phase-3` được gắn 3 phút sau đó.
  - Quán v1.2 (#20) và validation v1.2 (#21) không kịp vào tag. Chúng được merge lúc 12:51 và 12:45, trong Phase 4. Ở tag `phase-3`, quán chưa hao tươi và giá chưa theo độ tươi.
  - HUD độ tươi (#22) không có người nhận.
- **1 hành động cho Phase 4:** merge từng PR một, chạy `run-tests` trên `main` sau mỗi lần merge, đỏ thì dừng; khóa `main` 5 phút trước mốc tag (người nhận: tuancdk). *Kết quả:* tag `phase-4` xanh 218/218, nhưng vẫn gắn trễ (13:56).

## Phase 4 (cuối) — bản nháp của Integrator (tuancdk), viết sau tag `phase-4`; cả nhóm bổ sung
- **Rà lại hành động Phase 2:**
  - *Chạy `run-tests` ngay trước mỗi push* — làm một phần. Mỗi PR đều xanh khi đứng riêng, nhưng #37, #38 và #39 vào `main` gần như cùng lúc làm `main` đỏ 34 test. Phải sửa bằng PR #41. Nguyên nhân: không chạy lại test trên `main` sau mỗi lần merge.
  - *Gắn tag ở phút 50* — chưa làm được. `phase-4` và `v1.0.0` được gắn lúc 13:56, muộn hơn mốc gợi ý, vì chờ gộp UI (#45, #48) và release notes (#49).
- **Điều tốt:**
  - Lõi và mở rộng đều chạy được. 218/218 test xanh trên tag `phase-4`.
  - Soak 10 Ngày cho cùng kết quả khi chạy lại, `crashes = 0`.
  - Hợp đồng đổi qua v1.1 → v1.3 đều có ghi lại trong `docs/contracts/` và CHANGELOG.
  - Bench ghi số thật kể cả chỗ chưa đạt.
- **Điều tệ:**
  - Integrator tự làm cả UI và tự merge cả 21 PR. Không có review chính thức trên GitHub nào (0 review).
  - Issue #33 (QA Phase 4: clone sạch, `verification/phase-4.md`, retro) không xong trước tag. Phần này được bổ sung sau.
  - Lỗi uy tín cộng dồn float được ghi khi review PR #6 nhưng để tới sau tag `phase-4` mới sửa (PR #51). Lỗi này có thể làm mất 100 điểm. Nhận xét review cần được mở thành issue có người nhận.
  - Minhduc7904 được thêm vào `TEAM.md` sau tag `phase-4`, nên chỉ kịp làm phần kiểm chứng sau tag: clone sạch trên Windows, kiểm lại UI quán, video chơi tay (PR #52, #55). Không có đóng góp nào vào code trong bản phát hành.
- **Số liệu** (commit trên `main` theo tài khoản GitHub, không tính starter):

  | Người | Commit (không tính merge) | Commit merge |
  |---|---|---|
  | tuancdk | 16 | 28 |
  | DoLyHoangNam | 20 | 4 |
  | Hie24 | 8 | 1 |
  | thd050810 | 4 | 0 |
  | Minhduc7904 | 5 (sau tag, PR #52) | 0 |

  20 commit của DoLyHoangNam dùng email chưa gắn với tài khoản GitHub. Cách đọc code của nhau: Integrator đọc và chạy lại test trước khi merge, ghi nhận xét vào mô tả PR. Token: không ai đo.
- **Một lần AI sai và cách nhóm phát hiện:** khi bật contract v1.2, 101 test đỏ. Nguyên nhân là `load_contract` (do AI viết ở #15) chỉ nhận đúng `"1.1"`. Chạy toàn bộ test trước khi push thì thấy ngay; sau đó sửa cho nhận cả `"1.2"`. Thêm một ví dụ: Codex cộng uy tín bằng float, phát hiện khi review PR #6 bằng một chuỗi sự kiện cụ thể.
- **Nếu làm lại, đổi gì** (hành động, người nhận):
  1. Giao UI cho một thành viên từ Phase 1. Mỗi PR cần một người khác bấm Approve trên GitHub. — tuancdk
  2. Sau mỗi lần merge, chạy `run-tests` trên `main`; nếu đỏ thì dừng merge tiếp. — người merge
  3. Gắn tag ở phút 50 kể cả khi còn lát dở, ghi phần chưa xong vào verification. — tuancdk
  4. QA viết `verification/phase-n.md` song song từ đầu phase, không để cuối phase. — thd050810
  <!-- TODO(cả nhóm): mỗi người thêm 1 dòng ý kiến của mình. -->

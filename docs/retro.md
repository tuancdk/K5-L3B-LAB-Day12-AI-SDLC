# Retro nhóm

## Phase 2 (nhanh) — bản nháp của Integrator (tuancdk), cả nhóm bổ sung
- Điều tốt: chia theo vùng file nên P1 gather/quan/validation/UI làm song song, ít xung đột; hợp đồng chốt sớm (`docs/contracts/`) giúp smoke gather → kho → quán đạt ngay lần đầu; contract v1.1 mở PR riêng (#24) trước khi viết `day` để các lát dùng số chuẩn sớm.
- Điều tệ: tag `phase-1` không được đẩy đúng 1:00; `test_team_check` đỏ trên `main` từ khi điền TEAM.md vì Integrator chạy test **trước** khi điền và không chạy lại trước khi push; số chuẩn v1.1 buộc sửa file của người khác (gather/contract/scenario/test quán) để `main` không đỏ; rebase với validation #17 phải gỡ xung đột tay.
- 1 hành động cho Phase 3: chạy skill `run-tests` **ngay trước** mỗi push và gắn tag ở phút 50 dù còn lát dở (người nhận: tuancdk).

## Phase 4 (cuối) — bản nháp của Integrator (tuancdk), viết sau tag `phase-4`; cả nhóm bổ sung
- **Rà lại hành động Phase 2:**
  - *Chạy `run-tests` ngay trước mỗi push* — làm một phần. Mỗi PR đều xanh khi đứng riêng, nhưng #37, #38 và #39 vào `main` gần như cùng lúc làm `main` đỏ 34 test. Phải sửa bằng PR #41. Nguyên nhân: không chạy lại test trên `main` sau mỗi lần merge.
  - *Gắn tag ở phút 50* — chưa làm được. Theo release notes, `phase-2` và `phase-3` được gắn sau hạn. `phase-4` và `v1.0.0` được gắn lúc 13:56, cũng sau hạn, vì chờ gộp UI (#45, #48) và release notes (#49).
- **Điều tốt:**
  - Lõi và mở rộng đều chạy được. 218/218 test xanh trên tag `phase-4`.
  - Soak 10 Ngày cho cùng kết quả khi chạy lại, `crashes = 0`.
  - Hợp đồng đổi qua v1.1 → v1.3 đều có ghi lại trong `docs/contracts/` và CHANGELOG.
  - Bench ghi số thật kể cả chỗ chưa đạt.
- **Điều tệ:**
  - Integrator tự làm cả UI và tự merge cả 21 PR. Không có review chính thức trên GitHub nào (0 review).
  - Issue #33 (QA Phase 4: clone sạch, `verification/phase-4.md`, retro) không xong trước tag. Phần này được bổ sung sau.
  - Hai lỗi đã biết chưa sửa: uy tín cộng dồn float (từ review PR #6) và `browser-check --mode quan` timeout.
  - Minhduc7904 được thêm vào `TEAM.md` sau tag `phase-4` và chưa có commit.
- **Số liệu** (commit trên `main` theo tài khoản GitHub, không tính starter):

  | Người | Commit (không tính merge) | Commit merge |
  |---|---|---|
  | tuancdk | 16 | 28 |
  | DoLyHoangNam | 20 | 4 |
  | Hie24 | 8 | 1 |
  | thd050810 | 4 | 0 |
  | Minhduc7904 | 0 | 0 |

  20 commit của DoLyHoangNam dùng email chưa gắn với tài khoản GitHub. Cách đọc code của nhau: Integrator đọc và chạy lại test trước khi merge, ghi nhận xét vào mô tả PR. Token: không ai đo.
- **Một lần AI sai và cách nhóm phát hiện:** khi bật contract v1.2, 101 test đỏ. Nguyên nhân là `load_contract` (do AI viết ở #15) chỉ nhận đúng `"1.1"`. Chạy toàn bộ test trước khi push thì thấy ngay; sau đó sửa cho nhận cả `"1.2"`. Thêm một ví dụ: Codex cộng uy tín bằng float, phát hiện khi review PR #6 bằng một chuỗi sự kiện cụ thể.
- **Nếu làm lại, đổi gì** (hành động, người nhận):
  1. Giao UI cho một thành viên từ Phase 1. Mỗi PR cần một người khác bấm Approve trên GitHub. — tuancdk
  2. Sau mỗi lần merge, chạy `run-tests` trên `main`; nếu đỏ thì dừng merge tiếp. — người merge
  3. Gắn tag ở phút 50 kể cả khi còn lát dở, ghi phần chưa xong vào verification. — tuancdk
  4. QA viết `verification/phase-n.md` song song từ đầu phase, không để cuối phase. — thd050810
  <!-- TODO(cả nhóm): mỗi người thêm 1 dòng ý kiến của mình. -->

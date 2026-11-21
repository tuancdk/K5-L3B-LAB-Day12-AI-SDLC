# Retro nhóm

## Phase 2 (nhanh) — bản nháp của Integrator (tuancdk), cả nhóm bổ sung
- Điều tốt: chia theo vùng file nên P1 gather/quan/validation/UI làm song song, ít xung đột; hợp đồng chốt sớm (`docs/contracts/`) giúp smoke gather → kho → quán đạt ngay lần đầu; contract v1.1 mở PR riêng (#24) trước khi viết `day` để các lát dùng số chuẩn sớm.
- Điều tệ: tag `phase-1` không được đẩy đúng 1:00; `test_team_check` đỏ trên `main` từ khi điền TEAM.md vì Integrator chạy test **trước** khi điền và không chạy lại trước khi push; số chuẩn v1.1 buộc sửa file của người khác (gather/contract/scenario/test quán) để `main` không đỏ; rebase với validation #17 phải gỡ xung đột tay.
- 1 hành động cho Phase 3: chạy skill `run-tests` **ngay trước** mỗi push và gắn tag ở phút 50 dù còn lát dở (người nhận: tuancdk).

## Phase 4 (cuối)
- Rà lại hành động Phase 2: đã làm chưa? vì sao?
- Điều tốt / điều tệ:
- Số liệu: số commit theo người, cách đọc code của nhau, token theo người:
- Một lần AI sai và cách nhóm phát hiện:
- Nếu làm lại, đổi gì:

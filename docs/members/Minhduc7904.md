# Minhduc7904 (Nguyễn Minh Đức) — phản tư cá nhân

- **Tôi đã làm** (vào nhóm sau tag `phase-4`, [PR #50](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC-1111/pull/50), vai UI #5):
  - Clone sạch `v1.0.0` trên Windows và chạy regression ([`54dfcd2`](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC-1111/commit/54dfcd2)). Kiểm lại UI quán và tìm ra nguyên nhân thật của lỗi timeout ([`31a2ec6`](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC-1111/commit/31a2ec6)).
  - Quay video chơi tay Ngày 1 ([PR #55](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC-1111/pull/55)).
  - Sửa UI: đơn `unfulfillable` có nhãn "Hết hàng" và gợi ý đúng ([`f82e2c0`](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC-1111/commit/f82e2c0)).
- **Tôi đã review** (sau merge, kèm số liệu chạy lại):
  - #53: thử ngẫu nhiên 10.000 chuỗi; floor uy tín sai 22 lần với code cũ, 0 lần với code mới.
  - #38: tiêm lỗi crash để kiểm phần phục hồi của soak.
  - #43: 19 file kho sai, đưa qua CLI.
  - #44: đối chiếu với hợp đồng v1.2. Lần review này tìm ra lỗi UI ở trên.
- **AI sai ở đâu & phát hiện:**
  - AI quên cờ `--ticks`, suýt ghi một kết quả không chứng minh được gì. Phát hiện khi đọc thông báo lỗi.
  - Nhãn cảnh báo tràn khỏi phiếu. Phát hiện qua ảnh chụp.
- **Bài học:** vào muộn thì nên chọn kiểm chứng và review bằng cách chạy thật. Review vẫn tìm được lỗi kể cả khi code đã merge.

# Báo cáo cá nhân Lab Day 12 — Quán Ăn Chợ Nổi

**Đỗ Minh Thanh · thd050810 · QA lead · Nhóm 1111**

- **Tôi đã làm**
  - **Phase 1** — Thêm 66 ca kiểm dữ liệu lỗi. CLI trả mã 2 và không tạo đầu ra. [Commit](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC-1111/commit/13493e3) · [Bằng chứng](../proof/phase-1/thd050810/README.md)
  - **Phase 2** — Kiểm cờ CLI, kế hoạch Ngày và kho bàn giao. [Commit](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC-1111/commit/4787d9c)
  - **Phase 3** — Kiểm schema kho cá thể, độ tươi và ID giữ chỗ ở v1.2. [Commit](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC-1111/commit/94021bd)
  - **Phase 4** — Kiểm sau tag trên macOS tại `ad475a8`. Đạt 219/219 test, 5/5 headless. Hai lượt soak đều hoàn tất 10 ngày, 0 crash. [Issue #33](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC-1111/issues/33) · [Bằng chứng](../verification/phase-4.md#kiểm-chứng-bổ-sung-trên-main--macos)
- **Tôi đã review** bench, cảnh báo và chế độ tương phản cao trên Chrome sau merge. [PR #44](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC-1111/pull/44) · [PR #45](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC-1111/pull/45)
- **AI sai ở đâu và tôi phát hiện thế nào** — Script soak đọc nhầm khóa JSON. Tôi đối chiếu đầu ra thật sau khi thấy `KeyError` rồi chạy lại hai lượt. [Nhật ký AI](../ai-usage-log.md)
- **Điều tôi học được** — Đọc cả stderr khi xác nhận mã thoát và ghi commit vào log ngay lúc chạy.

# Hie24 (Nguyễn Đức Hiếu) — phản tư cá nhân

- **Tôi đã làm:**
  - P1 ([PR #6](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC-1111/pull/6), [`de3b710`](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC-1111/commit/de3b710), [`b712845`](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC-1111/commit/b712845)): luật Quán `sim/quan.py` (khách, giữ chỗ, bếp, phục vụ, tiền, uy tín, đóng ca) và 31 test.
  - P2 ([PR #39](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC-1111/pull/39), [`ac87380`](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC-1111/commit/ac87380), [`413d4f9`](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC-1111/commit/413d4f9)): 2 bếp/4 bàn/6 món theo kế hoạch Ngày, `sim/shop.py`, 30 test.
  - P3–P4 ([PR #44](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC-1111/pull/44), [`4f52ffc`](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC-1111/commit/4f52ffc)): kho cá thể hao 0.25/s, giữ chỗ theo id, giá theo độ tươi; `chonoi.bench`. Số đo thật: 1% low 21.7 FPS và load 41.8 s, cả hai chưa đạt mốc.
- **Tôi đã review:** <!-- TODO(Hie24): PR nào bạn đã đọc/chạy thử của người khác? Nếu không có thì ghi thẳng là không. -->
- **AI sai ở đâu & phát hiện:** Codex cộng uy tín bằng float. Chuỗi 4 lần bỏ về và 10 lần boa cho `1.9999999999999998`, nên `floor` ra 1 và mất 100 điểm. Integrator phát hiện khi review PR #6; lỗi được sửa ở [PR #51](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC-1111/pull/51), sau tag `phase-4` (có trong `v1.0.1`).
- **Bài học:** <!-- TODO(Hie24): một câu của chính bạn. -->

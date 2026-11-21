# tuancdk (Le Anh Tuan) — phản tư cá nhân

- **Tôi đã làm:**
  - P1: hợp đồng tích hợp, TEAM, kế hoạch, `AGENTS.md`, 2 skill ([PR #9](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC-1111/pull/9)); cửa sổ chơi ([`d7d7eaa`](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC-1111/commit/d7d7eaa)).
  - P2: contract v1.1, mode `day`, pause ([`57173d8`](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC-1111/commit/57173d8), [`15b031f`](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC-1111/commit/15b031f)); UI luồng Ngày ([`085d8b9`](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC-1111/commit/085d8b9)).
  - P3: contract v1.2 + adapter ([`e3febda`](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC-1111/commit/e3febda)); sửa `main` đỏ 34 test ([`2a2d523`](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC-1111/commit/2a2d523)); lớp Phaser ([`9bbc1bf`](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC-1111/commit/9bbc1bf)).
  - P4: contract v1.3, CHANGELOG, release ([`e8e289a`](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC-1111/commit/e8e289a)); cảnh báo + tương phản cao ([`728647e`](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC-1111/commit/728647e)); HUD độ tươi ([`a238425`](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC-1111/commit/a238425)).
- **Tôi đã review:** đọc và merge mọi PR. Ở [PR #6](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC-1111/pull/6) chạy lại test độc lập và ghi lỗi uy tín cộng dồn float (`1.9999999999999998`). Lỗi chưa được sửa.
- **AI sai ở đâu & phát hiện:** khi bật v1.2, 101 test đỏ vì `load_contract` chỉ nhận `"1.1"`. Chạy test là thấy, sau đó sửa cho nhận `"1.2"`.
- **Bài học:** tôi làm quá nhiều việc một mình (44/91 commit). Lần sau cần giao UI cho người khác, review bằng tính năng review của GitHub và gắn tag đúng hạn.

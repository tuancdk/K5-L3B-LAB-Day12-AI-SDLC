# Phase 4: kiểm tra clone sạch và regression trên Windows (Minhduc7904)

Thuộc [issue #33](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC-1111/issues/33), làm cùng QA lead thd050810. Ngày 21/11/2026, 14:15–14:25 (giờ VN).

Lần clone sạch trước ([release/clean-clone.txt](../release/clean-clone.txt)) chạy trên nhánh tạm `b0e2643`. Lần này kiểm tra lại đúng **tag `v1.0.0` đã phát hành** (`9cd42fc`, trùng `phase-4`), clone từ GitHub vào một thư mục trống, theo các lệnh trong README.

**Môi trường:** Windows 11 (10.0.22631), Python 3.12.6, git 2.47.0, Git Bash. Không dùng venv và không `pip install`. Trên máy này `python3` có sẵn trong PATH: Python cài từ python.org, cùng alias `python3` của Windows.

## Kết quả trên tag `v1.0.0` (`9cd42fc`)

| # | Lệnh | Kết quả |
|---|---|---|
| 1 | `git clone --branch v1.0.0 https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC.git` | exit 0, HEAD `9cd42fc` |
| 2 | `PYTHONPATH="tests;." python3 -m unittest discover -s tests` | **218/218 OK**, 102 s ([log](unittest-v1.0.0-clean-clone.log)). Dòng `soak crash ở Ngày 2: injected day 2 failure` trong log là do test cố ý gây lỗi, không phải lỗi thật |
| 3 | `python3 -m chonoi.headless --mode day --days 1 --seed 1 --ticks 30000 --out d1.jsonl`, chạy 2 lần | exit 0 cả hai lần. **Giống từng byte** (`cmp`), 2246 dòng, sha256 `cb8e6320e425…`. Dòng `end`: `days_complete` ở tick 22200, score 300 |
| 4 | `headless --mode gather` và `--mode quan`, `--seed 1 --ticks 600` | exit 0, `reason: tick_limit` ở tick 600. sha256 lần lượt `6b78d3ce0bbc…` và `ed33bd0baecf…` |
| 5 | `headless --mode day --days 6 --seed 1 --ticks 30000` | **exit 2**, báo "--days phải trong [1, 5]" (đúng: chỉ soak được quá 5 Ngày) |
| 6 | `python3 -m chonoi.soak --seed 7 --days 10 --out s.json`, chạy 2 lần | exit 0 cả hai lần. `days 10, days_completed 10, crashes 0`. Hai lần **giống nhau ở mọi trường trừ `duration_s`** |
| 7 | Lệnh thứ 3 trong README: `python3 -m chonoi.live --mode day` (thêm `--port 8765` để tránh đụng cổng 8000) | Server in "Mở trình duyệt tại http://127.0.0.1:8765/ (chế độ day, seed 1)". `GET /` trả **200 text/html**, 158 324 B, `<title>Quán Ăn Chợ Nổi` |

## Regression trên `main` sau PR #50 (`a5f8bfb`, team_size 4 → 5)

`python .agents/skills/run-tests/run_tests.py --phase phase-4 --who minhduc7904` cho kết quả **218/218 OK** ([unittest.log](unittest.log)). Kết quả này cho thấy việc thêm thành viên thứ 5 vào `TEAM.md` và đổi `team_size` không làm đỏ `test_team_check`.

## Chưa kiểm / ghi chú trung thực

- **Lỗi của mình khi chạy:** lần đầu chạy bước 3 và 5 thiếu `--ticks` nên `headless` trả mã 2 vì thiếu cờ bắt buộc. Kết quả đó không chứng minh được gì về `--days 6`. Mình đã chạy lại với đủ cờ, và bảng trên là kết quả lần chạy lại.
- **Chưa chạy `bench_cmd`:** lệnh này mở trình duyệt và đo 30 s nên không chạy được trong phiên kiểm tra này. Số đo bench vẫn là của Hie24 ([hie24/README.md](../hie24/README.md)).
- **Chưa chơi tay giao diện** sau khi clone, mới kiểm tra server trả trang. Bằng chứng giao diện xem [ui/README.md](../ui/README.md) và [UI Phase 3](../../ui/phase-3/README.md). *Cập nhật 14:50:* đã chơi tay Ngày 1 trên `main` và quay video, nhưng video chưa tới Shop. Xem [demo.md](demo.md).
- README ghi 3 lệnh cho macOS/Linux. Trên Windows, 3 lệnh đó chỉ chạy được khi có `python3` trong PATH. Nếu không có, xem mục Windows trong `AGENTS.md`.

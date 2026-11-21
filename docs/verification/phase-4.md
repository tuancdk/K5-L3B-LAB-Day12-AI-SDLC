# Ma trận truy vết Phase 4


Chạy lại:
- `python3 .agents/skills/run-tests/run_tests.py --phase phase-4 --who <handle>`
- `python3 .agents/skills/headless-check/headless_check.py --out docs/proof/phase-4/verify-tag/headless-check.txt`

| AC | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| AC-P4-01 Contract v1.3 khai `bench_cmd`, `soak_cmd`; `contract.py` nhận `"1.3"` | `game.contract.json`; toàn bộ test | [verify-tag/unittest.log](../proof/phase-4/verify-tag/unittest.log) | đạt |
| AC-P4-02 Soak: `--seed 7 --days 10`, `days_completed = 10`, `crashes = 0`, đủ trường | Chạy `chonoi.soak` trên clone sạch | [soak-determinism.txt](../proof/phase-4/verify-tag/soak-determinism.txt), [soak.json](../proof/phase-4/soak.json) | đạt |
| AC-P4-03 Soak tất định: 2 lần cùng seed giống nhau trừ `duration_s` | So 2 file JSON | [soak-determinism.txt](../proof/phase-4/verify-tag/soak-determinism.txt) | đạt |
| AC-P4-04 `--mode day --days 6` ở headless vẫn trả mã 2 | Chạy trên clone sạch | [clean-clone.txt](../proof/phase-4/verify-tag/clean-clone.txt) | đạt |
| AC-P4-05 Bench: đúng 5 trường, công thức `avg_fps`/`p1_low_fps` | `tests/test_bench.py` | [verify-tag/unittest.log](../proof/phase-4/verify-tag/unittest.log), [bench.json](../proof/phase-4/bench.json) | đạt |
| AC-P4-06 Mốc bench: avg ≥ 60, 1% low ≥ 30, load ≤ 10 s (ghi số thật, không bắt buộc đạt) | Đo trên Edge, 1280×720, seed 42 | [hie24/README.md](../proof/phase-4/hie24/README.md) | đạt (ghi số thật): avg 107.8 đạt mốc; **1% low 21.7 và load 41.8 s chưa đạt mốc** |
| AC-P4-07 Cảnh báo chữ/biểu tượng: thủy quái gần, oxy < 25%, khách sắp giận | Ảnh chụp + `warnings-check.py` | [ui/README.md](../proof/phase-4/ui/README.md) | đạt |
| AC-P4-08 Chế độ tương phản cao, chữ ≥ 18 px ở 1280×720, không ảnh hưởng headless | Ảnh chụp tương phản cao; headless tất định | [ui/](../proof/phase-4/ui/), [headless-check.txt](../proof/phase-4/verify-tag/headless-check.txt) | đạt |
| AC-P4-09 Regression P1–P3 trên bản tích hợp | 218 test + headless-check 5/5 | [unittest.log](../proof/phase-4/verify-tag/unittest.log), [headless-check.txt](../proof/phase-4/verify-tag/headless-check.txt) | đạt (218/218, 5/5) |
| AC-P4-10 Clone sạch → chạy bản có giao diện trong ≤ 3 lệnh | `git clone`, `cd`, `python3 -m chonoi.live --mode day` → HTTP 200 | [clean-clone.txt](../proof/phase-4/verify-tag/clean-clone.txt) | đạt trên Windows (cần `python3`, xem `AGENTS.md`); chưa thử macOS/Linux |
| AC-P4-11 CHANGELOG theo phase, LICENSE, CREDITS, release notes có giới hạn đã biết | Đọc file | [CHANGELOG.md](../../CHANGELOG.md), [v1.0.0.md](../release/v1.0.0.md) | đạt |
| AC-P4-12 Tag `phase-4` và Release `v1.0.0` cùng commit, có gói zip | `git ls-remote`, `gh release view` | tag `v1.0.0` → `9cd42fc`; asset `quan-an-cho-noi-v1.0.0.zip` | đạt |
| AC-P4-13 Retro, phản tư cá nhân, nhật ký AI | Đọc file | [retro.md](../retro.md), [members/](../members/), [ai-usage-log.md](../ai-usage-log.md) | chưa đạt: viết sau tag, còn thiếu phản tư của một số thành viên |

## Lỗi đã biết trên tag `phase-4`, sửa sau tag (PR #51)
Phần sửa nằm trên `main`, không nằm trong tag `phase-4` / `v1.0.0`.

| Lỗi | Trạng thái sau khi sửa |
|---|---|
| **Uy tín cộng dồn bằng float** (`_change_reputation` trong `chonoi/sim/quan.py`). Từ uy tín 0, 10 lần boa cho `1.9999999999999998`, nên `floor` ra 1 và mất 100 điểm (ghi nhận khi review PR #6). | **Đã sửa:** làm tròn 9 số. Thêm `QuanPhase2.test_reputation_sum_has_no_float_drift`: test đỏ trước khi sửa, xanh sau khi sửa. |
| **`docs/proof/ui/browser-check.py` timeout ở `quan`** (ghi trong [ui/README.md](../proof/phase-4/ui/README.md)). | **Không còn tái hiện:** chạy lại 1 lần trên tag `phase-4` và 3 lần trên nhánh PR #51, cả `gather` và `quan` đều đạt. |
| **`team` trong `game.contract.json` là `ten-nhom`**; release notes ghi `TEAM.md` có 4 người. | **Đã sửa:** `team` = `"1111"`, bỏ dòng cũ trong release notes. |
| README và release notes clone theo tên repo cũ (GitHub vẫn chuyển hướng). | **Đã sửa:** dùng tên `K5-L3B-LAB-Day12-AI-SDLC-1111`. |

## Kiểm chứng bổ sung trên main — macOS

QA sau phát hành cho [issue #33](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC-1111/issues/33) trên `ad475a8`, macOS 15.7.4 arm64 và Python 3.12.0. Kết quả trên tag `phase-4` được ghi ở bảng đầu trang.

| AC | Kết quả trên `ad475a8` | Bằng chứng |
|---|---|---|
| AC-P4-01, 09 | Contract v1.3 chạy được. Regression P1–P3 đạt 219/219 và headless-check đạt 5/5. | [Unittest](../proof/phase-4/thd050810/unittest.log), [Headless](../proof/phase-4/thd050810/headless-check.txt) |
| AC-P4-02, 03, 04 | Hai lượt soak cùng seed hoàn tất 10/10 Ngày, 0 crash. Kết quả giống nhau sau khi bỏ `duration_s`. Headless `--days 6` trả mã 2 với thông báo sai phạm vi và không tạo JSONL. | [Soak và kiểm cờ CLI](../proof/phase-4/thd050810/soak-determinism.txt) |
| AC-P4-05, 06 | Bench tạo đủ 5 trường. Avg **60.002 FPS**, 1% low **59.524 FPS**, load **0.680 s**, cả ba đạt mốc trong lần đo này. | [JSON bench macOS](../proof/phase-4/thd050810/bench.json) |
| AC-P4-07, 08 | Chrome 1280×720 hiển thị đủ ba cảnh báo, cỡ chữ nhỏ nhất 18 px. Bật bằng H, lưu khi tải lại và tắt được trong Cài đặt. Kiểm tra headless tất định đạt. | [Log cảnh báo](../proof/phase-4/thd050810/warnings-check.txt), [Headless](../proof/phase-4/thd050810/headless-check.txt) |
| AC-P4-10 | Clone sạch qua HTTPS. Cổng 8000 đang bận nên dùng `--port 0` trong lệnh thứ ba. Trang game và `/state` trả HTTP 200, bắt đầu ở Gather Ngày 1. | [Lệnh và log](../proof/phase-4/thd050810/clean-clone.txt) |
| AC-P4-11, 12 | Đã đối chiếu tài liệu phát hành và xác nhận hai tag trên `origin` cùng trỏ tới `9cd42fc`. | [CHANGELOG](../../CHANGELOG.md), [Release notes](../release/v1.0.0.md), [Release v1.0.0](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC-1111/releases/tag/v1.0.0) |
| AC-P4-13 | Đã bổ sung QA, nhật ký AI, retro và phản tư của thd050810 sau tag. Một số mục phản tư của nhóm vẫn chờ chính chủ. | [Retro](../retro.md), [Phản tư](../members/ĐỗMinhThanh.md), [Nhật ký AI](../ai-usage-log.md) |

Bench chạy bằng `python3 -m chonoi.bench --seed 42 --duration 30 --out bench.json --no-open`. Chrome 157.0.8103.79 headless đã mở sẵn khi nhận URL, với viewport 1280×720. Số đo trên Windows ở bảng đầu trang bao gồm thời gian công cụ mở trình duyệt.

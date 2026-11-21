# Ma trận truy vết Phase 4

Tiêu chí lấy từ issue #30–#34 (tách từ TICKET-04). **Kết quả dưới đây chạy lại trên commit gắn tag `phase-4` = `v1.0.0` (`9cd42fc`)**, từ một clone sạch. Môi trường: Windows 11, Python 3.12. Chưa chạy CI Linux hoặc macOS.

Bằng chứng này được viết **sau** khi gắn tag (ngày 21/11/2026). Tag `phase-4` được gắn lúc 13:56.

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

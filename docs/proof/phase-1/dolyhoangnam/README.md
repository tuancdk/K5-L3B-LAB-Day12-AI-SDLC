# Bằng chứng Phase 1 — Gather — DoLyHoangNam

Ngày: 21/11/2026 · Nhánh: `DoLyHoangNam_2A202603777` · [Issue #2](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC/issues/2).
Yêu cầu: [PRD-0](https://claude.ai/artifact/E35v787wSx2wDgPTNhMVDg#phase-1), Test Contract v1.0 D/E/F.Gather/G, [docs/contracts/README.md](../../../contracts/README.md).

Phạm vi: `chonoi/sim/gather.py` và [test Gather](../../../../tests/test_gather_rules.py).

## Kết quả

- **17/17 test Gather mới pass** (`test_gather_rules.py`), **81/82 toàn suite pass** (`unittest.log`).
  - 1 test fail ngoài phạm vi #2: `test_team_check.TeamCheck.test_template_is_rejected` (đã tồn tại trên `main` sau PR #9 do `TEAM.md` đã điền đủ thành viên hợp lệ).
- `headless-check` (`.agents/skills/headless-check/headless_check.py`): **PASS** cả 3 kiểm tra (tất định `gather`, tất định `quan`, smoke `dock → quan`).
- `python tools/check_team.py`: **OK** (4 thành viên).
- Log đầy đủ: [unittest.log](unittest.log). Môi trường: Windows, Python 3.11.7, thư viện chuẩn. `git diff --check` đạt.

| Yêu cầu đã kiểm | Kết quả |
|---|---|
| `dive` / `surface` đúng lúc vượt `surface_depth` với `pos` sau di chuyển | Đạt |
| Oxy dưới nước −1/tick, mặt nước hồi `oxygen_refill_per_tick`, kẹp `[0, max]`, `oxygen_empty` 1 lần | Đạt |
| Ngạt đúng mốc `t + 59` (`choke_interval_ticks`), nổi lên đúng bước ngạt thì không ngạt | Đạt |
| Máu 0 → bỏ giỏ theo LIFO (`faint.lost`), `gather_end(fainted)`, file kho rỗng `{"items":{}}` | Đạt |
| `interact` xét bến trước (kể cả bước cuối), hái mặt nước theo bán kính & hòa theo `id_key`, `node_regrown` hái ngay | Đạt |
| `catch` chỉ dưới nước & hết cooldown `t + L`, hòa `id_key`, thiếu chỗ phát `hold_full` giữ đàn & không fallback | Đạt |
| Hái/bắt ở bước cuối vẫn vào kho; nối CLI `gather → inv.json → quan`; 2 lần cùng seed giống từng byte | Đạt |

## Chạy lại

Tại gốc repo (Windows dùng `python` hoặc `python3` trên PATH):

```sh
python3 -B docs/proof/phase-1/dolyhoangnam/verify.py
```

Script bật UTF-8 cho subprocess, chạy toàn bộ suite, ghi lại log và trả đúng exit code.

## Tích hợp và giới hạn

Mọi thông số đọc từ `game.contract.json` (`tuning.tick_hz`, `tuning.gather.*`), không hard-code.
Kiểm fixture mâu thuẫn thuộc issue #4. Chưa chạy CI Linux hoặc test ẩn.
Antigravity hỗ trợ triển khai và kiểm chứng.

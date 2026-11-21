# Bằng chứng Phase 3 — Gather độ tươi & Mở rộng Dòng nước lũ — DoLyHoangNam

Ngày: 21/11/2026 · Nhánh: `DoLyHoangNam_2A202603777` · [Issue #19](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC/issues/19), [Issue #23](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC/issues/23).
Yêu cầu: TICKET-03 (Test Contract v1.2 — kích hoạt tự động khi manifest có `freshness` / `gather.current`, giữ tương thích hoàn toàn v1.1 để `main` luôn xanh).

Phạm vi: `chonoi/sim/gather.py`, `chonoi/sim/monsters.py`, [test_gather_p3.py](../../../../tests/test_gather_p3.py), [test_current.py](../../../../tests/test_current.py), [DoLyHoangNam.md](../../../members/DoLyHoangNam.md).

## Kết quả

- **136/136 test pass, exit code 0**, gồm 6 test độ tươi/cá thể P3 (`test_gather_p3.py`), 4 test dòng nước lũ (`test_current.py`), cùng toàn bộ 126 test regression P1–P2 (kể cả validation P2 vừa merge).
- `headless-check` ([headless-check.txt](headless-check.txt)): **PASS** cả 5 kiểm tra trên v1.1 hiện tại.
- Log đầy đủ: [unittest.log](unittest.log). Môi trường: Windows, Python 3.11.7, thư viện chuẩn. `git diff --check` đạt.

| Yêu cầu đã kiểm | Kết quả |
|---|---|
| `hold` mảng cá thể `{id, kind, fresh}` cấp `I1, I2, …` qua `IdAllocator` chung; Ngày > 1 cấp id mới từ mẫu | Đạt |
| Hao tươi chính xác `0.5/s` bằng `Fraction` (không trôi dấu phẩy động ở ngưỡng 30), bắt đầu từ bước sau, dừng khi pause | Đạt |
| Test mẫu đề (`fresh:30`, 1 bước không input) → `spoiled {item_id, kind, location:"hold"}` đúng tick 1, chỉ 1 lần, sắp theo `id_key` | Đạt |
| `monster_hit.lost` và `faint.lost` là mảng cá thể LIFO; ngất trả `gather_end.inventory: {"items": []}` | Đạt |
| Mở rộng `current`: cảnh báo `t−120`, chạy `t → t+479` (480 tick, `ticks_left` đếm cả tick chụp), kết thúc `elapsed` ở `t+480` | Đạt |
| Dòng lũ đẩy `±1.5 m/s` chỉ khi `d` đầu bước `≥ 10`, chặn mép, không tích lũy vào `player.vel`, không tác động cá/quái | Đạt |
| Ca kết thúc sớm phát `current_end(phase_end)` trước `faint` và trước `gather_end`; bước đầu dòng trùng bước cuối ca vẫn có lực | Đạt |

## Chạy lại

```sh
python3 -B docs/proof/phase-3/dolyhoangnam/verify.py
python3 -B .agents/skills/headless-check/headless_check.py --out docs/proof/phase-3/dolyhoangnam/headless-check.txt
```

## Ghi chú tích hợp

Không sửa `game.contract.json` hay `chonoi/inventory.py` (vùng sở hữu #18 của `@tuancdk`) hay `chonoi/scenario.py` (vùng #21 của `@thd050810`). Ngay khi #18 bật `freshness` (Contract v1.2) và/hoặc `gather.current` trong `game.contract.json`, `GatherSim` tự kích hoạt schema v1.2 và extension `current` mà không cần sửa lại code.

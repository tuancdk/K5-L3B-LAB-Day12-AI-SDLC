# Bằng chứng Phase 2 — Gather & Cá Sấu Năm Chèo — DoLyHoangNam

Ngày: 21/11/2026 · Nhánh: `dolyhoangnam/phase-2-gather-monsters` · [Issue #13](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC/issues/13), [Issue #14](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC/issues/14).
Yêu cầu: TICKET-02, Test Contract v1.1, [docs/contracts/README.md](../../../contracts/README.md).

Phạm vi: `chonoi/sim/gather.py`, `chonoi/sim/monsters.py`, [test_gather_p2.py](../../../../tests/test_gather_p2.py), [test_monsters.py](../../../../tests/test_monsters.py).

## Kết quả

- **119/119 test pass, exit code 0**, gồm 8 test Gather P2 mới, 8 test Cá Sấu mới, 17 test Gather P1 (regression xanh), và 86 test khác của nhóm (`day`, `contract v1.1`, `quan`, `validation`, `smoke`, `live`, `team`).
- `headless-check` ([headless-check.txt](headless-check.txt)): **PASS** tất cả bài kiểm tra tất định (`gather`, `quan`, `day --days 2`, smoke `dock → quan`, 1 Ngày đầy đủ `22200` tick).
- Log đầy đủ: [unittest.log](unittest.log). Môi trường: Windows, Python 3.11.7, thư viện chuẩn. `git diff --check` đạt.

| Yêu cầu đã kiểm | Kết quả |
|---|---|
| Cá bơi `1.5 m/s` trong `fish_x` × `fish_depths`, đổi hướng theo `age_ticks = 120·k` trước khi bơi | Đạt |
| Phản xạ phần quãng đường dư ở mép và chạm góc đảo cả hai trục | Đạt |
| `random_fish: false` giữ cá đứng yên và tắt sinh cá | Đạt |
| Sinh cá tại `phase_tick = 360·k` sau khi cá bơi, trần 12 đàn, chuẩn hóa trọng số loài còn điểm, `fish_spawned` | Đạt |
| Bắt cá theo vị trí trước khi cá bơi; `ca_keo` yield 2; nút `N5/N6` (`keo_neo`) | Đạt |
| Nhận `day_ctx` và áp dụng `active_upgrades` (`oxygen_max_s`, `hp_max`), hồi đầy đầu Ngày | Đạt |
| Cá Sấu: Ngày 1 có `M1`, Ngày 3+ có `M1` & `M2`; `patrol` `1.0 m/s` đổi waypoint bước sau | Đạt |
| `chase` `3.0 m/s` khi `d ≥ 10` và `≤ 10 m`; về `patrol` khi `> 16 m` hoặc `d < 10`; chặn dải độ sâu | Đạt |
| Chạm (`≤ 1.5 m`, `d ≥ 10`): tối đa 1 hit/bước (gần nhất, hòa theo id), −1 Máu, rơi `floor(n/2)` LIFO, bất tử 90 tick | Đạt |
| `recoil` 60 bước `2/60 m` xa người chơi (trùng tâm `+x`), chặn mép, không hit; hết recoil về `patrol` bước kế | Đạt |
| Ngất do quái: `faint(cause:"monster")` bỏ phần giỏ còn lại LIFO, `gather_end(fainted)`, quán mở với kho rỗng; cùng tick `choke` trước `monster_hit` | Đạt |

## Chạy lại

```sh
python3 -B docs/proof/phase-2/dolyhoangnam/verify.py
python3 -B .agents/skills/headless-check/headless_check.py
```

## Ghi chú tích hợp

Không sửa `chonoi/scenario.py` (thuộc vùng sở hữu #15 của `@thd050810`), tránh xung đột merge; toàn bộ scenario `monsters[]` đã được kiểm ở tầng sim + `DaySim` trong `tests/test_monsters.py`.
Antigravity hỗ trợ triển khai và kiểm chứng.

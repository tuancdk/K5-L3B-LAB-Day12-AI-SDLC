# Bằng chứng Phase 4 — Soak 10 Ngày — DoLyHoangNam

Ngày: 21/11/2026 · Nhánh: `DoLyHoangNam_2A202603777` · [Issue #31](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC/issues/31).

Phạm vi: `chonoi/soak.py`, `chonoi/sim/day.py` (nới `--days` lặp D1–D5 chỉ cho soak), [test_soak.py](../../../../tests/test_soak.py), [soak.json](../soak.json).

## Lệnh chạy (`soak_cmd`)

```sh
python3 -m chonoi.soak --seed 7 --days 10 --out docs/proof/phase-4/soak.json
```

*(Gợi ý cho `game.contract.json` v1.3 của #30: `"soak_cmd": "python3 -m chonoi.soak"`.)*

## Kết quả

- **Soak 10 Ngày (`--seed 7 --days 10`):** `days = 10`, `days_completed = 10`, `crashes = 0`, `earned` tăng liên tục từ `264` (Ngày 1) lên `2292` (Ngày 10), `score = 2792`, `duration_s ≈ 3.2 s` ([soak.json](../soak.json)).
- **Tất định:** chạy 2 lần cùng `--seed 7 --days 10` cho mọi trường (`days, days_completed, crashes, results`) giống hệt nhau, chỉ khác `duration_s`.
- **Cô lập lỗi:** test tiêm exception ở Ngày 2 xác nhận `crashes = 1`, không làm chết tiến trình và Ngày 3 vẫn chạy tiếp.
- **Bảo toàn headless:** `python3 -m chonoi.headless --mode day --days 6` vẫn trả mã thoát `2`; không ghi bảng xếp hạng.
- **Toàn bộ test suite:** `141/141` pass (`exit code 0`), `git diff --check` sạch.

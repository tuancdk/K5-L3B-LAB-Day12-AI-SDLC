---
name: headless-check
description: Kiểm Test Contract bằng headless thật - chạy 2 lần cùng seed và so byte (gather + quan), rồi chạy smoke hộp đen gather -> file kho -> quan. Dùng sau khi sửa sim/*, runner hoặc contract, và trước khi gắn tag.
---

# headless-check

```bash
python3 .agents/skills/headless-check/headless_check.py [--seed 1] [--ticks 600] [--out docs/proof/phase-1/headless-check.txt]
```

Kiểm 5 thứ, mỗi thứ in `PASS`/`FAIL`, mã thoát 0 khi tất cả đạt:
1. **Tất định gather**: 2 lần `--mode gather` cùng seed + cùng inputs (lặn, bơi, interact, catch) → JSONL giống từng byte, có `--inventory-out` thì file kho cũng giống.
2. **Tất định quan**: 2 lần `--mode quan` cùng seed + cùng kho (đủ món cho khách tới) → giống từng byte.
3. **Smoke PRD**: `dock.json` giỏ 3 món + `interact` tick 0 → file kho → quán tick 0. v1.0–1.1: `stock:{"bong_sung":2,"ca_loc":1}`; v1.2: `stock` trùng id/kind với file kho, `fresh` lệch ≤ 0.01.

4. **Tất định day** (v1.1): `--mode day --days 2` chạy 2 lần so byte.
5. **Một Ngày**: `day --days 1` kết thúc `days_complete` ở tick 22.200 trong ≤ 20 s.

Lệnh chạy lấy từ `headless_cmd` trong `game.contract.json` (giống test hộp đen); nếu máy không có `python3` (Windows) script tự thay bằng trình Python đang chạy nó.

Quy tắc cho agent: FAIL ở 1/2 nghĩa là có nguồn không tất định (dict không sắp, `random` toàn cục, đồng hồ) → tìm và sửa trong `sim/*`, không đổi test. Dùng `--out` để lưu kết quả làm bằng chứng.

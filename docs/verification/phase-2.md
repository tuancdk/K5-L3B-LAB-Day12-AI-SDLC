# Ma trận truy vết Phase 2

Chạy lại: `python3 .agents/skills/run-tests/run_tests.py --phase phase-2 --who <handle>` và `python3 .agents/skills/headless-check/headless_check.py --out docs/proof/phase-2/integration.txt`. **Kết quả dưới đây chạy trên commit bàn giao gắn tag `phase-2`** (Windows, Python 3.12.3; chưa chạy CI Linux).

| AC | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| AC-P2-01 Contract v1.1 | `tests/test_contract_v11.py` (version, 2 bếp/4 bàn/6 món, day_plan = tổng công thức, shop, monsters, 8 đàn đầu ca) | [tuancdk/unittest.log](../proof/phase-2/tuancdk/unittest.log) | đạt |
| AC-P2-02 Cá bơi/sinh | test của #13 | _(#13)_ | chưa đạt — mới có sinh 8 đàn đầu ca |
| AC-P2-03 Cá Sấu | test của #14 | _(#14)_ | chưa đạt |
| AC-P2-04 Quán v1.1 | test của #7; `day` lọc menu theo kế hoạch | _(#7)_ | một phần — chạy với 2 bếp/4 bàn; lọc menu do `day.py` |
| AC-P2-05 Shop | `test_upgrade_bought_applies_from_next_day` (BasicShop) | [unittest.log](../proof/phase-2/tuancdk/unittest.log) | một phần — chờ `sim/shop.py` (#8) |
| AC-P2-06 Validation v1.1 | `DayCli.*` (cấm quan.stock/reputation, money ≤ earned, upgrades, ingredients) | như trên | một phần — phần còn lại #15 |
| AC-P2-07 Mode day | `DayLoop.*`: thứ tự tick 0, đổi pha cùng tick, snapshot pha mới `phase_tick:0`, `days_complete`, nâng cấp từ Ngày sau, tất định | như trên + [integration.txt](../proof/phase-2/integration.txt) | đạt |
| AC-P2-08 Pause | `Pause.test_pause_freezes_gameplay_and_resume_runs_same_step` | như trên | đạt |
| AC-P2-09 UI | chơi thử | _(#16)_ | chưa đạt |
| AC-P2-10 Smoke + regression | headless-check 5/5; toàn bộ test P1 chạy với số chuẩn | [integration.txt](../proof/phase-2/integration.txt) | đạt trên `main` (103/103, 5/5 PASS); tag `phase-2` gắn ở commit bàn giao này |

## Bàn giao (tag `phase-2`)
- Gắn tag khi hết giờ Phase 2 theo quy định README ("chỗ chưa xong ghi trung thực"); Phase 3 đã mở.
- **Chưa vào `main` lúc gắn tag:** #13 (cá bơi/sinh theo lịch/nhận nâng cấp), #14 (Cá Sấu), #7 (quán v1.1 riêng), #8 (`sim/shop.py`), #15 (validation v1.1 đầy đủ), #16 (UI Phase 2). Các AC tương ứng giữ "chưa đạt"/"một phần".
- Đã có và chạy được ở tag: số chuẩn v1.1, mode `day` 1–5 Ngày với `BasicShop`, pause cả ba mode, lọc menu theo kế hoạch, nâng cấp oxy/Máu có hiệu lực từ Ngày sau, regression P1 với số chuẩn.
- Tag `phase-1` đặt ở `73bc1a8` = `0ce00a3` (merge #17, contract v1.0) + chỉ sửa `test_team_check` (#26) để tag chạy xanh 90/90; không chứa code v1.1.

## Đánh giá ngắn
- Test P1 đổi vì số chuẩn (ghi lý do trong commit): số đàn đầu ca, 1 bàn → 4 bàn, 3 → 6 món, `day` không còn bị từ chối, `test_team_check` giả định TEAM.md là bản mẫu.
- Một Ngày không pause (22.200 tick) chạy ~0.3 s trên Windows (luật hiện tại; đo lại khi có cá bơi + quái).

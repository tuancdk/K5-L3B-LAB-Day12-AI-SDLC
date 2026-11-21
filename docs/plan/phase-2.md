# Kế hoạch Phase 2 (TICKET-02, 1:00–1:55, tag `phase-2`)

**Mục tiêu:** số chuẩn v1.1, cá bơi/sinh, Cá Sấu, 2 bếp/4 bàn/6 món, vòng `day` gather → quan → shop, pause; regression P1 xanh.

| AC | Việc | Người | Issue | Phụ thuộc |
|---|---|---|---|---|
| AC-P2-01 | Contract v1.1 số chuẩn + hợp đồng `day_ctx` (xong trước phút 10) | tuancdk | #12, PR #24 | — |
| AC-P2-02 | Cá bơi, đổi hướng, sinh theo lịch, nhận nâng cấp | DoLyHoangNam | #13 | AC-P2-01 |
| AC-P2-03 | Cá Sấu: patrol/chase/hit/recoil, Máu/ngất do quái | (monster) | #14 | AC-P2-01 |
| AC-P2-04 | 2 bếp/4 bàn, 6 món, lọc món theo kế hoạch | Hie24 | #7 | AC-P2-01 |
| AC-P2-05 | Shop nâng cấp oxy/Máu cuối Ngày | Hie24 | #8 | AC-P2-01, `day_ctx` |
| AC-P2-06 | Validation scenario/contract v1.1 → mã 2 | thd050810 | #15 | AC-P2-01 |
| AC-P2-07 | Mode `day` `--days 1..5`, đổi pha cùng tick, `days_complete` | tuancdk | #12 | AC-P2-01 (dùng sim hiện có; Shop tạm `BasicShop`) |
| AC-P2-08 | Pause ở cả ba mode | tuancdk | #12 | — |
| AC-P2-09 | Menu, chuyển pha, pause, Shop, HUD v2 | thành viên UI | #16 | AC-P2-07 |
| AC-P2-10 | Smoke phút 20 gather → kho → quan; smoke `day` 1 và nhiều Ngày; regression P1; tag `phase-2` | tuancdk | #12 | tất cả |

**Rủi ro:** `gather.py` đổi nhiều (cá bơi + quái) → #13 và #14 cùng file, cần chia hàm rõ. Shop (#8) trễ → `day.py` đã có `BasicShop` dự phòng. Nợ P1: tag `phase-1`, TEAM 5 người.

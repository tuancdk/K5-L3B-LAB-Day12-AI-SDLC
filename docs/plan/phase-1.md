# Kế hoạch Phase 1 (PRD-0, 0:00–1:00, tag `phase-1`)

**Mục tiêu:** hai buổi chơi `gather` và `quan` đúng Test Contract v1.0, nối nhau qua file kho; headless tất định; bằng chứng thật ở `docs/proof/phase-1/`.

**Cách chia:** theo **vùng file** (ít chồng chéo) thay vì một lát một người; lát 1+2 cùng file `gather.py` nên giao một người. Hợp đồng chốt ở [`docs/contracts/README.md`](../contracts/README.md).

| AC | Việc | Người | Issue | Phụ thuộc |
|---|---|---|---|---|
| AC-P1-01 | `TEAM.md` 5 người + thỏa thuận; `team`, `team_size=5`; `tools/check_team.py` xanh | tuancdk | [#1](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC/issues/1) | — |
| AC-P1-02 | Hợp đồng: schema kho G + mẫu, bảng event E, trường snapshot, giao diện sim↔UI (chốt phút 15) | tuancdk | #1 | — |
| AC-P1-03 | Lát 1: bơi, oxy, ngạt, Máu, ngất (LIFO `lost`), `dive/surface/oxygen_empty/choke/faint` | DoLyHoangNam | [#2](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC/issues/2) | AC-P1-02 |
| AC-P1-04 | Lát 2: hái nút, mọc lại, bắt cá, cooldown, `hold_full`, cập bến, ghi kho một lần | DoLyHoangNam | #2 | AC-P1-02 |
| AC-P1-05 | Lát 3: khách, lịch theo seed, giữ chỗ nguyên liệu, kiên nhẫn, `no_dish` | Hie24 | [#3](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC/issues/3) ✅ | AC-P1-02 |
| AC-P1-06 | Lát 4: bếp, bưng, phục vụ, boa, tiền, uy tín, đóng ca | Hie24 | #3 ✅ | AC-P1-05 |
| AC-P1-07 | Fixture mâu thuẫn / sai miền → mã 2 trước khi ghi đầu ra | thd050810 | [#4](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC/issues/4) | AC-P1-02 |
| AC-P1-08 | HUD tối thiểu (thời gian, oxy, Máu, giỏ / kho, món, kiên nhẫn, bếp, tay, tiền, uy tín) + sáng tạo tắt ở headless | thành viên 5 | [#5](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC/issues/5) | AC-P1-02 (snapshot) |
| AC-P1-09 | Cùng seed → JSONL + kho giống từng byte (gather, quan) | tuancdk (kiểm) | #1 | #2, #3 |
| AC-P1-10 | Smoke hộp đen `dock.json` → kho → quán tick 0 `stock:{"bong_sung":2,"ca_loc":1}` | tuancdk | #1 | #2 (cập bến đã có ở khung) |
| AC-P1-11 | README chạy ≤ 3 lệnh, điều khiển, điểm, lệnh test; 2 skill trong `.agents/skills/` | tuancdk | #1 | — |
| AC-P1-12 | Toàn bộ test xanh; tag `phase-1` trên `main` trước 1:00 | tuancdk | #1 | tất cả |

**Mốc:** 0–15 chốt TEAM + hợp đồng · 20 rà lát vướng, người xong sớm (Hie24) hỗ trợ #2 · 25 thử file kho thật gather → quan · 45–55 smoke trên `main`, ma trận truy vết, tag · ≤ 1:00 đẩy `phase-1`.

**Rủi ro:**
- `gather.py` (lát 1+2) lớn nhất, một người → phút 20 xem tiến độ, Hie24 hoặc thd050810 cặp hỗ trợ lát 2.
- Windows không có `python3` → test hộp đen lỗi giả; dùng venv + `python3.exe` (xem `AGENTS.md`).
- Sửa chung `README.md` (Integrator + mục Sáng tạo của #5) → mỗi người chỉ sửa mục của mình.
- Đổi tên event/khóa `data` làm vỡ test ẩn → chỉ đổi qua Integrator, ghi lịch sử trong hợp đồng.

# Ma trận truy vết Phase 1

AC lấy từ [`docs/plan/phase-1.md`](../plan/phase-1.md). Bằng chứng chạy ở commit bàn giao; cập nhật lại trước khi gắn tag `phase-1`.
Chạy lại: `python3 .agents/skills/run-tests/run_tests.py --who <handle>` và `python3 .agents/skills/headless-check/headless_check.py`.

| AC | Cách kiểm chứng | Bằng chứng (link `docs/proof/phase-1/...`) | Kết quả (đạt / chưa đạt — ghi trung thực) |
|---|---|---|---|
| AC-P1-01 TEAM.md + team_size | `python3 tools/check_team.py` | [tuancdk/check_team.txt](../proof/phase-1/tuancdk/check_team.txt) | đạt một phần — 4 người, `team_size=4` OK; thiếu thành viên 5 (UI) và mã `team` |
| AC-P1-02 Hợp đồng tích hợp | Đọc [`docs/contracts/README.md`](../contracts/README.md), so với PRD-0 mục E/G | file hợp đồng + `inventory.sample.json` | đạt |
| AC-P1-03 Lát 1 gather (oxy, Máu, ngất) | test của #2 | _(#2 bổ sung)_ | chưa đạt — #2 đang làm |
| AC-P1-04 Lát 2 gather (hái, cá, kho) | test của #2 + smoke tích hợp | _(#2 bổ sung)_ | chưa đạt — cập bến + ghi kho (khung) đạt, hái/bắt cá chưa có |
| AC-P1-05 Lát 3 quán (khách) | `tests/test_quan_rules.py` | [hie24/README.md](../proof/phase-1/hie24/README.md), [hie24/unittest.log](../proof/phase-1/hie24/unittest.log) | đạt |
| AC-P1-06 Lát 4 quán (bếp, phục vụ, tiền) | `tests/test_quan_rules.py` | như trên | đạt |
| AC-P1-07 Fixture mâu thuẫn → mã 2 | test của #4 | _(#4 bổ sung)_ | chưa đạt — #4 đang làm |
| AC-P1-08 HUD + sáng tạo | chơi thử `chonoi.live`, ảnh | _(#5 bổ sung, `docs/proof/ui/`)_ | chưa đạt — chưa vào `main` |
| AC-P1-09 Tất định từng byte | skill `headless-check` (2 lần cùng seed, gather + quan) | [tuancdk/headless-check.txt](../proof/phase-1/tuancdk/headless-check.txt) | đạt trên luật hiện có; chạy lại khi #2 xong |
| AC-P1-10 Smoke dock → quán | `tests/test_integration_p1.py` + `headless-check` | [tuancdk/unittest.log](../proof/phase-1/tuancdk/unittest.log), [headless-check.txt](../proof/phase-1/tuancdk/headless-check.txt) | đạt — quán tick 0 `stock:{"bong_sung":2,"ca_loc":1}` |
| AC-P1-11 README + 2 skill | đọc README; chạy 2 skill | `.agents/skills/run-tests`, `.agents/skills/headless-check`, `AGENTS.md` | đạt |
| AC-P1-12 Test xanh + tag | `run-tests` trên `main` | [tuancdk/unittest.log](../proof/phase-1/tuancdk/unittest.log) (65/65 OK, Windows, Python 3.12.3) | chưa đạt — chưa gắn tag |

## Đánh giá ngắn
- Yêu cầu nào đạt / chưa đạt: hợp đồng, quán, smoke tích hợp, tất định, harness đạt; gather (#2), validation (#4), UI (#5) và TEAM.md đang làm. Chưa chạy CI Linux.
- Điều cần chỉnh cho phase sau: chốt hợp đồng trước khi bắt đầu code; dựng venv `python3` cho máy Windows ngay từ kickoff.

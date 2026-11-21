# Phase 3 — Hie24 — #20

Nguồn: [TICKET-03 trên lab board](https://claude.ai/artifact/E35v787wSx2wDgPTNhMVDg), [issue #20](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC/issues/20), hợp đồng v1.2 mục 7.
Nhánh `hie24/phase-3-4-quan-bench`, nền main **32f53d6** (đã có PR P2 #39).

**Kết quả:** [203/203 test PASS](unittest.log), exit 0; gồm 19 test độ tươi/giữ chỗ và 6 test benchmark mới. [Headless 5/5 PASS](headless-check.txt).

| Yêu cầu | Bằng chứng |
|---|---|
| Kho cá thể, hao 0.25/s kể cả reserved; kẹp 0; pause/Shop/món chín không hao | `test_quan_freshness.FreshQuan` |
| Spoiled một lần, ngưỡng chính xác, thứ tự ID; giữ tươi nhất, nhả cả đơn rồi thử lại một lần | như trên, gồm cạnh tranh theo order_tick/id bàn |
| Tiêu đúng ID; cook_started.items theo kind/id; chốt giá lúc nấu và boa theo giá mới | như trên + QuanHeadless bán trọn đơn: 59 + 11 = 70 |
| File kho/đổi pha giữ ID/fresh, không hao thêm; thứ tự snapshot | `FreshQuanCLI`, gồm bàn giao gần ngưỡng 30 |
| Regression P1–P2, pause, deadline và hai bếp | [unittest.log](unittest.log) |
| Tất định + gather → file kho → quan + day | [headless-check.txt](headless-check.txt), **5/5 PASS** |

Code/test đã kiểm được nhận diện bằng [SHA-256](sources.sha256). Một Ngày hoàn tất ở tick **22.200**.
Mở rộng Chợ Chú Sáu/cháy/đặt bàn chưa bật (`extensions: []`).

**Tích hợp cần thiết:** headless/items khôi phục stock/reserved nguyên bản sau validator đếm; day chuyển cá thể thật vào Quan/Shop; JSONL giữ đủ chính xác cho fresh. Không đổi schema, manifest, live.py hoặc runner.py.
**Lý do đổi test:** fixture unit P1–P2 giữ rõ kho đếm; CLI dùng reserved dạng ID, kho cá thể và giá sau hao tươi, thay kỳ vọng giá cố định cũ. Test validation vẫn kiểm thiếu hàng bị từ chối.

Chạy lại từ gốc repo (Windows chuẩn bị python3/PYTHONPATH theo AGENTS.md):

```sh
python3 .agents/skills/run-tests/run_tests.py --phase phase-3 --who hie24
python3 .agents/skills/headless-check/headless_check.py --out docs/proof/phase-3/hie24/headless-check.txt
```

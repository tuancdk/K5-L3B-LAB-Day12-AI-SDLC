# Bằng chứng Phase 1 — Quán — Hie24

Ngày: 21/11/2026 · Nhánh: `hie24/phase-1-quan` · [Issue #3](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC/issues/3).
Yêu cầu: [PRD-0](https://claude.ai/artifact/E35v787wSx2wDgPTNhMVDg#phase-1), Test Contract v1.0 D/E/F.Quán/G.

Phạm vi: `chonoi/sim/quan.py` và [test Quán](../../../../tests/test_quan_rules.py).

## Kết quả

**63/63 test pass, exit code 0**, gồm 31 test Quán mới và 32 test sẵn có.
Log đầy đủ: [unittest.log](unittest.log). Môi trường: Windows, Python 3.13.5, thư viện chuẩn.
`git diff --check` đạt.

| Yêu cầu đã kiểm | Kết quả |
|---|---|
| Lịch khách, fixture, ID, bàn trống, chọn món theo seed, giữ chỗ/kho khả dụng | Đạt |
| Đơn cũ nhất, tiêu kho một lần, thời gian nấu, tuổi món, nhặt và giới hạn tay | Đạt |
| Một interact, ưu tiên khoảng cách/bếp/ID, mép bán kính, phục vụ đúng đơn | Đạt |
| Hết kiên nhẫn, nhả giữ chỗ/hủy món; boa, tiền và giới hạn uy tín | Đạt |
| Phục vụ sát deadline; đóng ca thanh toán ngay, khách chờ không giảm uy tín | Đạt |
| Headless, snapshot/end, output tất định và tích hợp gather → kho → Quán | Đạt |

Các bằng chứng chính từ test:

- Luồng đầy đủ: `cook_started@1 → dish_ready@361 → dish_picked@361 → served@511 → paid@1111`; tiền **72**, uy tín **3.2**, điểm **372**.
- Đóng ca: `served → paid(closing) → quan_end` cùng tick 1; một snapshot cuối, `end.reason=time`.
- Hai tiến trình cùng seed **-17**, **4000 tick**: JSONL giống từng byte, kể cả đổi thứ tự khóa stock.

## Chạy lại

Tại gốc repo, cần `python3` trong PATH (Windows dùng alias/môi trường Python tương ứng):

```sh
python3 -B docs/proof/phase-1/hie24/verify.py
```

Script bật UTF-8 cho subprocess, chạy toàn bộ suite, ghi lại log và trả đúng exit code.

## Tích hợp và giới hạn

`stock` là tồn vật lý, gồm phần giữ chỗ; bắt đầu nấu mới trừ kho. Payload món: `{order_id, dish_id, base_price}`; event theo mục E.
Kiểm fixture mâu thuẫn thuộc issue #4. Chưa chạy CI Linux hoặc test ẩn.
Codex hỗ trợ triển khai và kiểm chứng; không đo token/chi phí.

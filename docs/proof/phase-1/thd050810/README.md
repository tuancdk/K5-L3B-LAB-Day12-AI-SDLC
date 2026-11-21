# Kiểm chứng Phase 1 — Validation

[Issue #4](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC/issues/4) · nhánh `dothanh` · Python 3.12.0

```sh
PYTHONPATH=tests:. python3 -m unittest discover -s tests -v
```

Kết quả `Ran 70 tests` và `OK`, gồm 63 test hiện có và 7 test mới. Các test mới chạy CLI thật với 66 trường hợp lỗi lưu trong `tests/fixtures/validation/`.

| Tiêu chí | Kiểm chứng |
| --- | --- |
| Bếp, khách và đơn hàng | Fixture kiểm trạng thái, timer, công thức, tổng phần giữ, đơn `assigned` có đúng một món và khách `eating` có đủ dữ liệu thanh toán. |
| Món trên tay hoặc ở bếp | Fixture kiểm cấu trúc payload, đơn tồn tại, `dish_id` khớp và đơn thuộc đúng trạng thái. |
| Nguồn kho | Test tổng phần giữ của hai khách vượt kho và thử cùng một scenario với hai file kho có số lượng thiếu hoặc đủ. |
| Gather | Fixture kiểm `zero_oxy_ticks` âm, bằng 60, còn oxy hoặc đang ở mặt nước. Test dương kiểm giá trị 59 dưới nước khi oxy bằng 0. |
| Contract | Mỗi test thay một trường trên bản sao contract để kiểm ID, tọa độ bếp và bàn, uy tín, sức chứa, công thức và quy đổi tick. |
| Đầu ra | Mọi fixture lỗi trả mã 2. Quán không tạo JSONL. Gather và contract lỗi không tạo JSONL hoặc file kho khi truyền `--inventory-out`. |

Chạy lại hai fixture trực tiếp từ thư mục gốc repo.

```sh
proof_dir=$(mktemp -d)
python3 -m chonoi.headless --mode quan --seed 1 --ticks 10 \
  --scenario tests/fixtures/validation/quan/assigned_dish_in_two_places.json \
  --out "$proof_dir/quan.jsonl"
echo "$?"
python3 -m chonoi.headless --mode gather --seed 1 --ticks 10 \
  --scenario tests/fixtures/validation/gather/zero_oxy_at_sixty.json \
  --out "$proof_dir/gather.jsonl" --inventory-out "$proof_dir/kho.json"
echo "$?"
ls -A "$proof_dir"
rmdir "$proof_dir"
```

Cả hai lệnh trả `2` và thư mục đầu ra rỗng.

## Ghi chú cho Integrator

`scenario.py` và `contract.py` kiểm mâu thuẫn trước khi mô phỏng bắt đầu. `headless.py` và `live.py` truyền kho đã đọc vào cùng hàm kiểm để tổng phần giữ được đối chiếu với nguồn kho thực tế. Khi fixture bỏ trường `reserved`, validator dùng công thức để kiểm tổng, còn module quán vẫn tự điền phần giữ lúc khởi tạo.

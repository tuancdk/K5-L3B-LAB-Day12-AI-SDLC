# Kiểm chứng giao diện · Issue #5

## Chơi trên trình duyệt

Ảnh chụp từ Chrome mở hai máy chủ `chonoi.live`. Buổi sáng dùng cấu hình mặc định. Buổi tối dùng [scenario kiểm thử](quan-scenario.json) với một khách có món đang nấu. Người chơi có thể đợi món chín, lấy món ở bếp rồi phục vụ bàn T1.

- [Buổi sáng · Út Sen đang lặn](gather.png), 1280 × 800.
- [Buổi sáng ở chiều rộng 390 px](gather-390.png), có nút di chuyển, hái và bắt cá.
- [Buổi tối · thẻ đơn, bếp B1 và khách ở bàn T1](quan.png), 1280 × 800. Hàng phím nằm trong khung nhìn.
- [Buổi tối ở chiều rộng 390 px](quan-390.png), sau khi Út Sen lấy món. Các khung thông tin xếp thành một cột và không tràn ngang.

```powershell
python -X utf8 -m chonoi.live --mode gather --seed 1 --port 8000
python -X utf8 -m chonoi.live --mode quan --seed 1 --port 8001 --scenario docs/proof/ui/quan-scenario.json
```

Mở địa chỉ máy chủ in ra. Hoặc chạy `python -X utf8 -B docs/proof/ui/browser-check.py` để tái hiện kiểm tra và chụp lại ảnh. Script cần Chrome và gói Python `websockets`. Máy chủ kiểm thử dùng cổng localhost tự cấp. Có thể truyền đường dẫn Chrome sau tên script.

Đã thử D, W và mũi tên xuống. Trong quán, W làm tọa độ `z` tăng. Ở bến, E kết thúc lượt sáng và R khởi động lại. Chrome gửi `catch: true` khi bấm Space và gửi lệnh dừng khi kiểm thử phát sự kiện `blur`. Tọa độ ổn định sau khi vận tốc giảm về 0.

Ở chiều rộng 390 px, Chrome mô phỏng thao tác giữ nút phải để bơi, hủy chạm để dừng và bấm Bắt cá để gửi lệnh. Trong quán, E lấy món khi bếp chín, sau đó đưa món tới T1 và xác nhận khách chuyển sang trạng thái đang ăn. Kiểm tra HUD kho với nguyên liệu đã giữ cho khách và một giá trị giữ chỗ sai kiểu.

Thẻ đơn hiển thị biểu tượng món và kiên nhẫn. Dùng bản sao snapshot để mô phỏng khách còn 1 giây và kiểm tra thẻ đổi sang trạng thái gấp. Sau khi giao món trong game, thẻ chuyển sang “Đang ăn”.

Ở bố cục mới, thẻ đơn và đồng hồ ca chia sẻ vùng phía trên cảnh. Kịch bản xác nhận đồng hồ đổi màu khi còn 14 giây và thanh thao tác hiện “Đã giao món” sau sự kiện `served`. Sàn nhìn nghiêng dùng cùng phép chiếu cho nhân vật, bếp, bàn và vòng tương tác.

Kịch bản trình duyệt sửa bản sao phản hồi `/state`. Với buổi sáng, kịch bản bỏ `player`, `hold`, thời gian, `meta.bounds` và đưa mục không hợp lệ vào mảng cá/cây. Với buổi tối, kịch bản kiểm tra `customers` thiếu, `null`, object và mảng có phần tử hỏng, cùng `hand` thiếu, `null`, chuỗi, object và mảng. Kịch bản cũng thử tọa độ, tiền, uy tín sai kiểu. HUD còn dữ liệu tiếp tục hiển thị, ảnh tiếp tục được vẽ và không ghi nhận lỗi hoặc cảnh báo JavaScript.

## Test tự động

64/65 test qua, gồm `tests/test_live.py`, luật quán và tích hợp kho. `test_team_check.TeamCheck.test_template_is_rejected` cũng thất bại trên bản sạch của `origin/main` tại `6fd19d9`. Test dùng `TEAM.md` làm mẫu lỗi nhưng file này đã có danh sách thành viên hợp lệ. Xem [log của skill run-tests](tuancdk/unittest.log). Trên Windows, lần chạy dùng quyền kết nối localhost và bản sao tạm của `python.exe` mang tên `python3.exe`.

```powershell
$env:PYTHONPATH = 'tests;.'
$env:PYTHONUTF8 = '1'
python -m unittest discover -s tests -v
```

## Đối chiếu headless

Cùng seed `1` và giới hạn `600` tick. Các file `before` được tạo từ bản xuất sạch của commit `5035f44`, đã có luật quán Phase 1. Các file `after` được chạy tại workspace với giao diện mới. Hai file trong mỗi cặp trùng SHA-256 trên toàn bộ JSONL.

| Buổi | File | SHA-256 cho cả hai file |
|---|---|---|
| Sáng | [Trước](gather-before.jsonl) · [Sau](gather-after.jsonl) | `72c30e63f0ca4f4d15de11305be5fae1a967aa6bcd9e00f3deef7d301e1c7ae3` |
| Tối | [Trước](quan-before.jsonl) · [Sau](quan-after.jsonl) | `5af637b8e5a512499a23ca56cebc743540d2b2e17f91c1c370a06e7c5e0baeb9` |

```powershell
python -m chonoi.headless --mode gather --seed 1 --ticks 600 --out docs/proof/ui/gather-after.jsonl
python -m chonoi.headless --mode quan --seed 1 --ticks 600 --out docs/proof/ui/quan-after.jsonl
Get-FileHash -Algorithm SHA256 docs/proof/ui/*.jsonl
```

Ở bản mô phỏng hiện tại, luật hái và bắt cá vẫn đang được nhóm viết. Kiểm tra trình duyệt xác nhận các nút gửi thao tác tương ứng. PRD-0 không có bản cục bộ trong repo khi kiểm tra, nên tiêu chí UI được đối chiếu với issue #5 và code hiện tại.

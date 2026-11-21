# Kiểm chứng HUD độ tươi · Issue #22

Chrome mở cửa sổ chơi thật của hai chế độ. Để thử giao diện v1.2 trước khi luật Phase 3 được tích hợp, kịch bản thay bản sao phản hồi `/state` bằng dữ liệu mẫu. Hình, tiếng và độ tươi trong lần thử này chỉ kiểm chứng client.

- [Giỏ buổi sáng](fresh-gather.png): từng cá thể có ID, tên, số và thanh độ tươi. 30/100 vẫn tươi, 29,999/100 và 0/100 là hàng ươn. Mục thiếu độ tươi có nhãn riêng. Sự kiện `spoiled` làm hiện thông báo và phản hồi chỉ một lần dù cùng cá thể tiếp tục xuất hiện trong các lần poll.
- [Kho quán và giá](fresh-quan.png): cả cá thể tươi, ươn và giữ chỗ đều nhìn được, nhưng tổng có thể dùng chỉ tính nguyên liệu tươi chưa giữ chỗ theo ID. HUD hiện giá `base_price` ngay ở bếp và ở món đang cầm. Nếu payload thiếu giá, test kiểm tra fallback từ `cook_started` có cùng bếp, món và ID đơn.
- [Dòng lũ](fresh-current.png): dùng `current_warning` ở tick 1680 cho dòng bắt đầu ở tick 1800. Chrome ghi nhận cảnh báo chữ, biểu tượng và một lần phát âm. Khi snapshot báo dòng đang chảy, giao diện hiện hướng và thời gian còn lại. R1/R2 chỉ hiện khi snapshot có `reservations`.

Kịch bản còn thử giỏ dạng mảng chuỗi, kho đếm theo loại với phần giữ chỗ dạng cũ, snapshot thiếu kho/bếp/món trên tay và `fresh` sai kiểu. Không ghi nhận lỗi JavaScript. Hồi quy Chrome với snapshot v1.1 thật cũng đạt ở cả hai buổi, gồm lấy món và phục vụ ở T1. `run-tests` đạt 110/110 trên mốc `20d41ee`, gồm `tests/test_live.py`. [Log](unittest.log)

```powershell
python -X utf8 -B docs/proof/ui/browser-check.py --freshness --out docs/proof/ui/phase-3
```

Cần Chrome và gói Python `websockets`. Bỏ `--freshness` để thử hai server thật với snapshot hiện tại. Ngưỡng ươn đọc từ metadata nếu có, mặc định dùng mốc 30 theo [ticket contract #18](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC/issues/18). Giao diện không làm hao độ tươi và không tính lại giá bán. Cần chạy lại với dữ liệu thật sau khi [#18](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC/issues/18), [#19](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC/issues/19) và [#20](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC/issues/20) được tích hợp.

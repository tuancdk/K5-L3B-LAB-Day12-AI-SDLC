# Video chơi tay Ngày 1 (Minhduc7904)

[demo-ngay1.mp4](demo-ngay1.mp4): dài 2:41, 1280×764, H.264 + AAC, 5,5 MB.

Minhduc7904 tự chơi bằng bàn phím ngày 21/11/2026 lúc 14:44 (giờ VN), dùng `python3 -m chonoi.live --mode day` trên `main` (sau PR #53), Windows 11, trình duyệt Chrome. Video quay màn hình gốc là 1828×1092 và nặng 172 MB, vượt giới hạn 100 MB của GitHub. Video đã được nén bằng ffmpeg (`-vf scale=1280:-2 -c:v libx264 -crf 28 -c:a aac -b:a 96k`), không cắt hay ghép đoạn nào.

## Các mốc trong video

| Thời điểm | Diễn biến | Luật hoặc tính năng thấy được |
|---|---|---|
| 0:00 | Buổi sáng Ngày 1, đồng hồ 2:58. Út Sen ở bến, giỏ 0/12, kế hoạch cần Bông súng 0/6 và Cá lóc 0/3 | HUD oxy, Máu, độ sâu, "Nguyên liệu cần lấy"; Cá Sấu Năm Chèo "Tuần tra" |
| 0:05–0:50 | Hái bông điên điển và bông súng trên mặt nước; lặn bắt cá lóc | Chữ "+1 Bông điên điển", nút hái hiện "Đang mọc · 19s", hồi bắt cá |
| khoảng 0:53 | Giỏ 10/12 (sáu bông, ba cá lóc…); mỗi cá thể có thanh độ tươi riêng, từ 75 đến 99 | Kho cá thể `{id, kind, fresh}`, hao tươi trong giỏ (P3) |
| 0:55 | Cập bến sớm khi đồng hồ còn khoảng 2:07; hiện hộp thoại "Chuẩn bị mở quán" | Đổi pha gather → quan trong mode `day` |
| 1:05–2:41 | Nấu ở bếp B1/B2, bưng món, giao cho khách K/C ở bàn T1–T4. Phiếu món có thanh kiên nhẫn | Bếp có đồng hồ, "Chín rồi!", khách "Đang ăn", giữ chỗ nguyên liệu cho khách |
| 1:35 | Bếp B2: **"Giá chốt 44 nghìn (niêm yết 60)"** | Giá món theo độ tươi (P3) |
| 2:41 (hết video) | Buổi tối còn 1:17. **Tiền ca 236 nghìn, uy tín 4/5** (bắt đầu từ 3). Kho còn 3 bông điên điển, độ tươi 49, 70 và 72 | Uy tín tăng nhờ boa; nguyên liệu tiếp tục hao tươi trong kho |

## Chưa có trong video

- Video dừng giữa buổi tối, chưa quay **Shop cuối Ngày** và **màn tổng kết**.
- Không có cảnh oxy sắp hết hay thủy quái tấn công, nên chưa thấy cảnh báo P4 khi chơi thật. Ảnh chụp cảnh báo xem [ui/README.md](../ui/README.md).
- Không bật tương phản cao (phím H).

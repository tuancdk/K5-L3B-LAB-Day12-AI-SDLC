# Bằng chứng Phase 4: cảnh báo dễ nhận biết và tương phản cao (UI)

Ngày 21/11/2026, nhánh `tuancdk/p4-ui-warnings`, [issue #34](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC/issues/34).

Phạm vi: `chonoi/web/index.html`. Không đổi luật, contract hay `live.py`, nên headless không bị ảnh hưởng.

## Ba cảnh báo: chữ và biểu tượng, không chỉ dựa vào màu

| Cảnh báo | Khi nào | HUD (DOM) | Trên cảnh (canvas) |
|---|---|---|---|
| **Thủy quái gần** | Cá Sấu `chase` hoặc trong `detect_radius` của Út Sen | Thông báo "⚠ Thủy quái!" và viền khung tím (tương phản cao: nét đứt vàng) | Biển tam giác "!" kèm chữ "Thủy quái!" trên con Cá Sấu |
| **Oxy sắp hết** | Dưới nước, oxy > 0 và < 25% bình | Nhãn "⚠ Sắp hết" trong ô Oxy (khi cạn: "Hết oxy"), thông báo "⚠ Oxy sắp hết!" | Biển "!" kèm chữ "Oxy sắp hết!" trên Út Sen |
| **Khách sắp giận** | Kiên nhẫn ≤ 25% | Nhãn "⚠ Sắp giận!" trên phiếu món (thêm vào màu đỏ và hiệu ứng rung có sẵn) | Biển "!" kèm chữ "Sắp giận!" cạnh bong bóng gọi món |

- Các biển trên cảnh tự xếp chồng khi trùng chỗ, ví dụ Cá Sấu áp sát Út Sen.
- Mọi chữ cảnh báo ≥ 18 px ở 1280×720. Script đo kích thước thực tế: nhỏ nhất là 18 px ở cả hai cảnh.
- Quy tắc chữ ≥ 18 px trước đây chỉ áp cho chế độ `day`; giờ áp cho mọi chế độ ở màn từ 1000 px trở lên, kể cả nhãn trên canvas.

## Chế độ tương phản cao

- **Bật/tắt:** phím **H**, hoặc ô **"Tương phản cao (phím H)"** trong Cài đặt (menu chính hay menu tạm dừng). Có thông báo ngắn "Tương phản cao: BẬT/TẮT".
- **Lưu lại:** lưu ở `localStorage` (`chonoi.contrast.v1`), mở lại trang vẫn giữ.
- **Giao diện:**
  - HUD dùng nền đen, chữ trắng, nhấn vàng, viền dày.
  - Ô đồng hồ, ô oxy thấp và phiếu gấp có viền nét đứt.
  - Thanh tiến độ khi gấp dùng sọc vàng-đen thay vì chỉ đổi màu.
  - Nhãn trên canvas thành chữ trắng viền đen; lớp tranh tăng tương phản.
- Cả ba cảnh báo đều đã được thử ở chế độ này:

| | Thường | Tương phản cao |
|---|---|---|
| Sông: Thủy quái và Oxy sắp hết | ![](canh-bao-gather-thuong.png) | ![](canh-bao-gather-tuong-phan.png) |
| Quán: Khách sắp giận | ![](canh-bao-quan-thuong.png) | ![](canh-bao-quan-tuong-phan.png) |

## Chế độ `?bench=1` (#32)

Bản đầu (trong PR #45) đo bằng `requestAnimationFrame` và gửi `POST /bench-result`. Hie24 đã thay bằng bản của #32 (PR #44, `chonoi/bench.py`): trang lấy cấu hình qua `/bench-config`, đo ngay trong `drawWorld`, và server ghi `bench.json`. Phần bench vì thế được kiểm trong `tests/test_bench.py`, không nằm trong script này nữa.

## Lệnh tái hiện

```powershell
python -X utf8 -B docs/proof/phase-4/ui/warnings-check.py
```

Script cần Chrome và gói `websockets`. Nó:
- Chạy hai server `chonoi.live` thật (gather, quan).
- Chèn trạng thái nguy hiểm vào snapshot phía trình duyệt (`probe.modify`, không đụng sim), kiểm chữ cảnh báo, biểu tượng `⚠` và cỡ chữ ≥ 18 px.
- Bấm `H` rồi kiểm cảnh báo vẫn còn và khung có viền nét đứt.
- Tải lại trang để kiểm việc lưu lại, rồi tắt bằng ô chọn trong Cài đặt.
- Không được có lỗi JavaScript.

## Hồi quy

- `tests/test_live.py` xanh; toàn bộ unittest **179/179 OK**.
- `browser-check.py --day-fixture` và `--day-live` (một Ngày thật, từ menu tới tổng kết): đạt.
- `phaser-check.py`: đạt.
- `browser-check.py` với server thật: buổi sáng đạt. Chạy riêng `--mode quan` vẫn timeout ở dòng 415 (giao món xong khách không sang `eating`), giống hệt trước thay đổi này. Lỗi đã có từ khi gộp sim quán mới, chưa điều tra.

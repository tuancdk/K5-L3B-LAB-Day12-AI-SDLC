# Kiểm chứng giao diện Phase 2 · Issue #16

## Luồng Ngày trên Chrome

Các ảnh dưới đây dùng [snapshot và phản hồi input mẫu](day-fixture.js) tại 1280×720. Fixture tách khỏi trang chơi và chỉ được nạp từ kịch bản kiểm thử.

- [Menu chính](day-menu.png) và [lời dặn đầu Ngày](day-intro.png).
- [Buổi sáng](day-gather.png) với độ sâu, nguyên liệu đã lấy/cần, hồi bắt, Cá Sấu đuổi/lùi và cảnh báo hết oxy.
- [Nhập kho đầu buổi tối](day-evening-intro.png) và [cảnh quán](day-quan.png) với B1/B2, T1–T4, đơn gấp và tiền ca.
- [Kết quả Ngày](day-result.png), [tạm dừng trong Shop](day-pause.png) và [Shop sau khi mua bình oxy](day-shop.png).
- [Tổng kết sau Ngày 5](day-summary.png). Kịch bản thử trọn luồng UI của Ngày 1, đợi hết 4 giây ở lời dặn Ngày 2 rồi chuyển fixture tới cuối Ngày 5 để kiểm tra tổng kết.

Chrome xác nhận nút và phím giảm thời gian chờ lời dặn, Shop nhận `buy` và `shop_done`, thông báo hết tiền xuất hiện, mua đúng giá cập nhật cấp và tiền. Đã kiểm tra `phase_tick`, `sim_tick` và thời gian còn lại đứng yên khi pause Shop, rồi chạy tiếp sau Esc. Ba giá trị âm lượng Master, Music và SFX giữ nguyên sau khi tải lại trang. Không ghi nhận lỗi JavaScript trong luồng fixture.

Ở lần chạy được lưu ảnh, đếm callback `requestAnimationFrame` trong khoảng 1,5 giây khi cảnh đang mở cho kết quả **65,2 FPS sáng** và **90,5 FPS tối** trên máy thử Chrome headless. Số đo dao động theo tải máy: qua 7 lần chạy liên tiếp sau khi chuyển việc đo vùng HUD ra khỏi vòng vẽ, mức thấp nhất là 39,9 FPS sáng và 56,5 FPS tối, vẫn trên ngưỡng 30 mà script kiểm. Kiểm tra bố cục 1280×720 xác nhận các nhãn HUD dùng 18 px và khung kho/bếp/món trên tay cùng hàng phím nằm trong khung nhìn buổi tối.

## Giao diện v2: sân chơi toàn màn hình, HUD nổi

Bản này đổi cách trình bày theo các game nấu ăn hợp tác. Mọi thay đổi nằm ở client, chỉ đọc snapshot và event có sẵn, không đổi contract hay luật nên JSONL headless không đổi.

- **Bố cục:** từ 900 px trở lên, canvas chiếm phần lớn khung nhìn. Phiếu món nổi ở góc trên trái, đồng hồ và chỉ số ở góc trên phải, kho/bếp/món trên tay nằm dưới chỉ số. Phép chiếu sân chơi chừa chỗ cho vùng HUD nên bàn, bếp và cá không bị che. Dưới 900 px vẫn xếp dọc như bản trước; hồi quy với server thật vẫn kiểm chạm và không cuộn ngang ở 390 px.
- **Phong cách:** phông Baloo 2 (có dấu tiếng Việt, OFL; không có mạng thì dùng phông hệ thống), viền mực nâu đậm và bóng đổ cứng cho thẻ, nút và hộp thoại.
- **Phiếu món:** giấy kẹp trên dây. Thanh kiên nhẫn xanh khi trên 50%, vàng khi từ 25–50%, đỏ và rung khi dưới 25%. Phiếu được vá tại chỗ mỗi lần poll để hiệu ứng không chạy lại.
- **Trên canvas:**
  - Thanh nấu trên bếp; món chín thì biển "✓ Đã chín" nhảy lên xuống.
  - Út Sen giơ món trên đầu khi bưng.
  - Bong bóng gọi món có vòng kiên nhẫn cùng thang màu với phiếu; khách run khi dưới 25%.
  - Khách trả tiền thì đồng xu bật lên kèm số tiền.
  - Chữ lớn "Bắt đầu!" đầu pha, đếm ngược 5 giây cuối, "Hết giờ!" khi hết thời gian.
  - Khung rung khi có `monster_hit`/`choke`/`faint`.
  - Tất cả chuyển động tắt khi người dùng bật giảm chuyển động.
- **Âm thanh:** mỗi event trong bảng contract có một tiếng Web Audio riêng. Nhạc nền đổi sang giai điệu ngũ cung và tăng gấp đôi nhịp khi còn ≤ 30 giây (sáng) hoặc ≤ 20 giây (tối). Không dùng tệp âm thanh ngoài.
- **Hộp thoại:**
  - DayResult và Summary có hàng sao theo uy tín thật, tối đa `reputation_max` của contract. Không tự đặt ngưỡng điểm.
  - Shop ghi rõ số tiền còn thiếu, nhưng nút Mua vẫn gửi `buy` để server trả `buy_failed`.
- **Chữ ≥ 18 px ở 1280×720 trong chế độ Ngày:** áp thêm cho dòng tên pha, nhãn phím, nút hộp thoại, dòng bàn/khách trên phiếu và nội dung bảng kho/bếp.

## Lớp cảnh Phaser 3

Cảnh chơi chạy trên [Phaser 3.80.1](../../../../chonoi/web/vendor/PHASER-LICENSE.md) (MIT), đóng gói trong `chonoi/web/vendor/`. `live.py` chỉ phục vụ đúng các file trong `VENDOR_FILES`, nên không cần mạng. HUD, phiếu món và hộp thoại vẫn là DOM, giữ nguyên selector cho các kiểm tra cũ.

- **Hai lớp canvas trong `#scene`:**
  - Lớp dưới là tranh Canvas 2D vẽ tay (`drawWorld`).
  - Lớp trên là Phaser trong suốt, lo hạt, chữ nổi, tween và camera.
  - Phaser giữ nhịp vẽ cho cả hai. Khi rung, lớp tranh dời theo độ lệch của camera.
  - Cách này thay cho bản đầu chép tranh vào `CanvasTexture` mỗi frame. Trong cùng một lần chạy, bản đầu chỉ đạt khoảng 0,67 lần FPS của Canvas thường ở buổi sáng; bản hai lớp đạt khoảng 0,9–1,0.
- **Hiệu ứng theo event của snapshot:**
  - `gather`: lá và chữ "+1 …"; `fish_caught`: tia nước, tia sáng, "+1 …".
  - `dive`/`surface`: tia nước; `hold_full`: "Giỏ đầy!".
  - `monster_hit`/`choke`/`faint`: camera rung, nháy đỏ và "−1 ♥".
  - `dish_ready`: tia sáng và "Chín rồi!" trên bếp; `served`: giấy màu tại bàn.
  - `paid`: đồng xu bay về ô Tiền ca rồi ô đó nảy lên; `customer_left`: khói và "Khách bỏ đi!".
  - Ngoài ra: khói bốc từ bếp đang nấu, đom đóm buổi tối, sáng/tối chuyển bằng fade.
  - "Bắt đầu!", đếm ngược 5 giây cuối và "Hết giờ!" là Text của Phaser có tween.
  - Hạt và tween dừng khi tạm dừng hoặc mở hộp thoại; giảm chuyển động thì bỏ rung, nháy và bớt hạt.
- **Dự phòng:** không tải được Phaser thì trang vẽ bằng Canvas 2D như bản trước, kể cả chữ nổi và biển nhịp chơi.
- [`phaser-check.py`](../phaser-check.py) chạy với server quan và gather thật:
  - Xác nhận Phaser 3.80.1 khởi động với đúng hai canvas.
  - Kích hoạt event trên client, đếm hạt và tween đang chạy.
  - Chặn `/vendor/phaser.min.js` rồi tải lại để xác nhận bản dự phòng vẫn vẽ.
  - Không có lỗi JavaScript.
- Ảnh giữa hiệu ứng: [quán](phaser-quan-fx.png), [sông](phaser-gather-fx.png).
- **FPS ở lần chạy lưu ảnh:** quán 89,9 (dự phòng 64,6), sông 45,8 (dự phòng 60,6).
  - Số đo trên máy thử dao động mạnh theo tải. Khi máy bận, cả hai cách đều xuống khoảng 28–35, và có một lần quán Phaser đo được 27,8.
  - Script chỉ báo đạt khi cả hai cảnh ≥ 30 FPS.

## Lệnh tái hiện

```powershell
python -X utf8 -B docs/proof/ui/browser-check.py --day-fixture --out docs/proof/ui/phase-2
python -X utf8 -B docs/proof/ui/phaser-check.py --out docs/proof/ui/phase-2
python -X utf8 -B .agents/skills/headless-check/headless_check.py --seed 1 --ticks 600 --out docs/proof/ui/phase-2/headless-check.txt
```

Kịch bản trình duyệt cần Chrome và gói Python `websockets`. Có thể truyền đường dẫn Chrome sau tên script. Bỏ `--day-fixture` để chạy hồi quy với hai server `chonoi.live` thật và thử pause/resume của Phase 1.

- Hồi quy Chrome đạt với cả hai server thật. Ở buổi sáng, P dừng `phase_tick`, `sim_tick` và đồng hồ, Esc chạy tiếp. Các kiểm tra cũ về chạm, cập bến, lấy và giao món vẫn đạt.
- [run-tests](unittest.log) chạy lại sau giao diện v2: 81/82 đạt, trong đó `tests/test_live.py` đạt. `test_team_check.TeamCheck.test_template_is_rejected` cũng thất bại trên bản xuất sạch `fc90f7e` vì test đọc `TEAM.md` đã có đội hợp lệ.
- [headless-check](headless-check.txt): hai chế độ tất định và smoke buổi sáng → kho → quán đều qua.
- [So SHA-256](headless-sha256.txt): JSONL của cả hai chế độ v1.0 giống từng byte giữa bản gốc và bản có giao diện Phase 2.

## Một Ngày thật trên nhánh tích hợp

Chạy Chrome ở 1280×720 với runner và contract v1.1 tại `f394510` từ [PR #24](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC/pull/24), kết hợp các file giao diện và `live.py` của issue #16 trong bản xuất tạm. [Scenario smoke](day-live-scenario.json) cho Út Sen mang sẵn ba nguyên liệu, mở ca tối ngắn và bắt đầu với 200 nghìn để thử hai mức giá Shop.

> Bốn ảnh `live-day-*.png` dưới đây chụp **trước** giao diện v2. Nhánh này vẫn dùng contract v1.0, nên `--day-live` báo "Chế độ day đang chờ runner và contract v1.1 (#12)". Cần chụp lại sau khi gộp `main` (đã lên contract v1.2). Ảnh fixture ở phần đầu đã là giao diện v2.

- [Buổi sáng](live-day-gather.png) → E cập bến → [nhập kho đúng ba nguyên liệu](live-day-evening.png).
- Sau ca tối, thử mua áo phao khi thiếu tiền. Esc/P đóng băng `sim_tick`, `phase_tick` và thời gian Shop, trong khi `tick` vẫn tăng theo contract v1.1. Tiếp tục và [mua bình oxy được cấp 1](live-day-shop.png).
- Bấm Xong và thấy [tổng kết Ngày 1](live-day-summary.png); server trả `days_completed: 1` và `reason: "days_complete"`. Chrome không báo lỗi JavaScript.

Khi runner v1.1 đã có trong checkout, chạy lại bằng:

```powershell
python -X utf8 -B docs/proof/ui/browser-check.py --day-live --out docs/proof/ui/phase-2
```

## Tích hợp còn chờ

Mốc `fc90f7e` và `main` tại `0ce00a3` vẫn dùng contract v1.0. `python -m chonoi.live --mode day --days 5` ở nhánh UI hiện báo rõ thiếu runner và contract v1.1. Lượt Ngày thật ở trên chạy với Shop tạm `BasicShop` của PR #24. Ảnh Cá Sấu và số FPS ở phần đầu dùng fixture.

`live.py` nhận cờ `--mode day` và `--days`, chuyển tiếp nút pause/shop_done và lệnh buy một lần đến runner, bổ sung cấu hình pha, thực đơn và bảng Shop vào metadata. Chữ ký `Session(..., days=N)` và trường `InputState.buy` đã được kiểm thử với runner của [#12](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC/issues/12). Cần chạy lại khi đã tích hợp runner, [Shop chính thức #8](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC/issues/8) và [Cá Sấu #14](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC/issues/14). Với contract v1.0, pause dừng bước ở lớp live để hai chế độ cũ vẫn dùng được.

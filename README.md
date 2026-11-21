# Day 12 — AI SDLC: Quán Ăn Chợ Nổi

> **Làm theo nhóm 4–6 người** · Dùng AI để xây game 2D qua **4 phase** trong **3 giờ**: Út Sen lặn bắt cá, hái rau trên mặt nước rồi tối mở quán phục vụ khách.
> **Yêu cầu từng phase mở đúng mốc giờ tại lab board:** **[Chợ Nổi Lab](https://claude.ai/artifact/E35v787wSx2wDgPTNhMVDg)** (cần đăng nhập claude.ai; có trợ giảng AI cho từng phase).

## Bắt buộc (chỉ có thế)

Cách làm việc kỹ thuật là **tự do** (push thẳng, nhánh + PR, pair, có hay không CI…). Cái bắt buộc:

1. **Một repo chung:** trưởng nhóm **fork** repo này, đặt tên `K5-L3B-LAB-Day12-AI-SDLC-<ten-nhom>`, thêm mọi thành viên làm collaborator (*Settings → Collaborators*, quyền Write) và để repo **public** (giảng viên xem được, không cần mời).
2. **Cả nhóm cùng commit** bằng tài khoản GitHub của mình, mỗi người **≥ 3 commit có nội dung** (làm cặp thì ghi `Co-authored-by:`).
3. **Điền [`TEAM.md`](TEAM.md):** danh sách thành viên + thỏa thuận làm việc nhóm; sửa `team_size` trong [`game.contract.json`](game.contract.json). Commit của người không có trong `TEAM.md` không được tính.
4. **Gắn tag** `phase-1` … `phase-4` đúng hạn; chạy được tại từng tag.
5. **Ghi chép tối thiểu:** `docs/verification/phase-n.md`, `docs/clarify.md`, `docs/ai-usage-log.md`, `docs/retro.md`, `docs/members/<handle>.md`.

## Chạy game (từ clone sạch, 3 lệnh — macOS/Linux)

```bash
git clone https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC-1111.git
cd K5-L3B-LAB-Day12-AI-SDLC-1111
python3 -m chonoi.live --mode day      # mở địa chỉ in ra (mặc định http://127.0.0.1:8000/)
```

**Yêu cầu:** Python 3.10+ (chỉ thư viện chuẩn, không `pip install`), trình duyệt hiện đại; cửa sổ chuẩn 1280×720. Windows không có `python3`: xem [`AGENTS.md`](AGENTS.md#windows-không-có-python3). Thêm `--days N` (1–5), `--seed N`, `--port N`; chơi riêng một buổi: `--mode gather` / `--mode quan`.

| Phím | Buổi sáng (`gather`) | Buổi tối (`quan`) |
|---|---|---|
| WASD / mũi tên | bơi (S/↓ lặn xuống) | đi lại trong quán |
| E (`interact`) | hái nút ở mặt nước; trong vùng bến thì cập bến | bếp trống: nấu đơn cũ nhất; bếp xong: bưng món; tại bàn: phục vụ |
| Space (`catch`) | bắt đàn cá gần nhất khi ở dưới nước | — |
| Esc / P | tạm dừng / tiếp tục | tạm dừng / tiếp tục |
| H | bật/tắt tương phản cao | bật/tắt tương phản cao |
| R | chơi lại | chơi lại |

Shop cuối Ngày dùng chuột: mua Bình oxy / Áo phao, bấm xong để sang Ngày kế.

**Điểm** = `earned + 100 × floor(uy tín)`: `earned` là tổng tiền thu (giá món theo độ tươi + tiền boa), uy tín 0–5 (bắt đầu 3; boa +0.2, khách bỏ về vì hết kiên nhẫn −0.5). Tiền, uy tín, cấp nâng cấp giữ qua các Ngày; nguyên liệu hao tươi (giỏ 0.5/s, kho 0.25/s), dưới 30 là ươn.

### Lệnh cho kiểm thử

| Việc | Lệnh |
|---|---|
| Test (1 lệnh) | `PYTHONPATH=tests:. python3 -m unittest discover -s tests -v` |
| Headless | `python3 -m chonoi.headless --mode gather\|quan\|day [--days N] --seed 1 --ticks 600 --out out.jsonl` |
| Benchmark (`bench_cmd`) | `python3 -m chonoi.bench --seed 42 --duration 30 --out bench.json` (mở trình duyệt 1280×720) |
| Soak (`soak_cmd`) | `python3 -m chonoi.soak --seed 7 --days 10 --out soak.json` |

Lệnh khai trong [`game.contract.json`](game.contract.json) (contract **v1.3**). Hợp đồng giữa các module: [`docs/contracts/README.md`](docs/contracts/README.md) · Nhóm: [`TEAM.md`](TEAM.md) · Thay đổi: [`CHANGELOG.md`](CHANGELOG.md) · Bản phát hành: [`docs/release/v1.0.0.md`](docs/release/v1.0.0.md) · Giấy phép: [`LICENSE`](LICENSE), [`CREDITS.md`](CREDITS.md). Khung Python trong `chonoi/` chi tiết ở [`docs/STARTER.md`](docs/STARTER.md).

## Tự do sáng tạo

Ngoài phần đề yêu cầu, nhóm được **thêm** nhân vật, loài cá/cây, sinh vật, món, bản đồ, cơ chế, câu chuyện, đồ họa, âm nhạc… với ba điều kiện: **không phá phần cố định** (tắt ở headless), ghi mục **"Sáng tạo của nhóm"** trong README của nhóm, và **làm lõi đúng trước**.

## Sáng tạo của nhóm

Út Sen có chân dung và dáng đi, dáng lặn riêng, với áo bà ba màu mận, khăn rằn và kính lặn. Buổi sáng có gợn phù sa, cá quẫy đuôi và bong bóng. Buổi tối có đèn quán phản chiếu trên sông và hơi nước bốc lên từ bếp. Các hiệu ứng chạy trong trình duyệt và tôn trọng tùy chọn giảm chuyển động của thiết bị.

Gợi ý bên cạnh cảnh đổi theo việc Út Sen đang làm. Người chơi có thể dùng bàn phím hoặc giữ các nút trên màn hình nhỏ để di chuyển và tương tác.

Buổi tối có sàn quán nổi nhìn nghiêng, hai khu bếp và bàn ăn phân biệt bằng màu chiếu, cùng hàng đèn lồng. Thẻ đơn và đồng hồ ca nằm trên khung chơi. Khi nấu, bếp có đồng hồ riêng và sáng lên lúc món chín. Bàn cần giao được đánh dấu khi Út Sen bưng đúng món. Khi giao hoặc nhận tiền, tín hiệu hiện ngay tại bàn.

Mục **Cài đặt → Âm thanh** có ba thanh cho âm lượng chung, nhạc nền và hiệu ứng. Trình duyệt nhớ ba mức này ở những lần mở sau. Âm thanh và tùy chọn lưu trên trình duyệt, nên headless cho cùng kết quả. Xem [bằng chứng giao diện Phase 2](docs/proof/ui/phase-2/README.md).

Trên màn rộng, sân chơi chiếm gần cả cửa sổ và HUD nổi ở các góc. Phiếu món kẹp trên dây, đổi từ xanh sang vàng rồi đỏ và rung khi khách sắp bỏ đi. Thanh nấu nằm ngay trên bếp. Út Sen giơ món trên đầu khi bưng. Mỗi event có một tiếng riêng, và nhạc ngũ cung tăng nhịp khi sắp hết giờ. Đầu pha có chữ "Bắt đầu!", cuối pha đếm ngược 5 giây. Tất cả chỉ là hiển thị phía trình duyệt và tắt khi người dùng bật giảm chuyển động.

Xem [ảnh chơi và kết quả đối chiếu SHA-256](docs/proof/ui/README.md) của cả hai buổi.

## Lịch 3 giờ

| Mốc | Phase | Hạn tag |
|---|---|---|
| 0:00 | Phase 1 (PRD-0) | `phase-1` trước 1:00 |
| 1:00 | Phase 2 | `phase-2` trước 1:55 |
| 1:55 | Phase 3 | `phase-3` trước 2:30 |
| 2:30 | Phase 4 | `phase-4` + Release `v1.0.0` trước 3:00 |

Hết giờ mỗi phase thì gắn tag rồi đi tiếp; chỗ chưa xong ghi trung thực trong bằng chứng.

## Đánh giá (100 điểm)

| Hạng mục | Điểm |
|---|---|
| Test tự động ẩn (headless, gồm kiểm tra lại phase trước) | 25 |
| Làm việc nhóm (một repo chung, chia việc, tích hợp, đổi yêu cầu) | 25 |
| Kiểm chứng & bằng chứng | 15 |
| Harness AI (AGENTS.md, skill, nhật ký dùng AI) | 10 |
| Đánh giá & retro | 10 |
| Chất lượng sản phẩm (đúng yêu cầu, mở rộng/sáng tạo) | 10 |
| Demo | 5 |

## Quy định

- Dùng AI thoải mái; **không sao chép repo của nhóm khác**; bằng chứng phải thật.
- Nhân vật, bối cảnh là bản gốc của lab; asset ngoài chỉ dùng CC0/CC-BY/MIT hoặc tự tạo, ghi nguồn trong `CREDITS.md`. Không commit API key, token, `.env`.

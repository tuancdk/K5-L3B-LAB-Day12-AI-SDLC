# AGENTS.md — hướng dẫn chung cho mọi agent AI của nhóm

> Cập nhật file này qua các phase (lịch sử git phải cho thấy điều đó). Ngắn gọn, có lệnh chạy thật.

## Lệnh
- Test: `PYTHONPATH=tests:. python3 -m unittest discover -s tests -v`
- Headless: `python3 -m chonoi.headless --mode gather|quan --seed 1 --ticks 600 --out out.jsonl`
- Chơi thử trên trình duyệt: `python3 -m chonoi.live --mode gather|quan` (mở địa chỉ in ra; WASD, E, Space, R)

## Cấu trúc & quy ước
- (Starter Python là TÙY CHỌN; nhóm có thể dùng ngôn ngữ khác nếu giữ Test Contract.) Khung do giảng viên cấp: `chonoi/{headless,inputs,scenario,contract,rng,ids,jsonl,inventory,runner,live}.py` và `chonoi/web/`. Hạn chế sửa; nếu phải sửa thì báo cả nhóm và ghi lại lý do.
- Luật chơi của nhóm: `chonoi/sim/gather.py`, `chonoi/sim/quan.py` (tìm `TODO(nhóm)`).
- Cửa sổ chơi: `chonoi/web/index.html` (HUD/hộp thoại là DOM, cảnh là Phaser 3 trong `chonoi/web/vendor/`, tự lùi về Canvas 2D khi thiếu thư viện). `live.py` chỉ phục vụ file vendor có trong `VENDOR_FILES`. Kiểm UI: `python -X utf8 -B docs/proof/ui/browser-check.py --day-fixture` và `docs/proof/ui/phaser-check.py` (cần Chrome + gói `websockets`).
- **Số liệu chỉ đọc từ `game.contract.json` / dữ liệu**, không hard-code trong luật.
- Mọi số ngẫu nhiên đi qua `Streams` (`chonoi/rng.py`); không dùng `random` toàn cục, không dùng đồng hồ hệ thống.
- Sắp danh sách thực thể bằng `ids.sort_by_id`; cấp id bằng `IdAllocator`.

## Nên tránh
- Không sửa `docs/contracts/`, `game.contract.json` (khóa contract) hoặc schema kho khi chưa báo cả nhóm (đổi hợp đồng ảnh hưởng mọi module).
- Không làm hỏng nhánh chính: trước khi đẩy, chạy test.
- Không bịa yêu cầu: chỗ mơ hồ thì ghi `docs/clarify.md` và hỏi PO.
- Không sửa test cho xanh khi luật sai; phải sửa luật hoặc ghi lý do đổi test trong commit.

## Quy tắc làm việc với agent
- Mỗi agent một việc rõ ràng (một lát). Cho agent đọc PRD/ticket đúng phase và hợp đồng kho trước.
- Agent làm xong phải chạy test và ghi kết quả vào mô tả commit hoặc `docs/proof/`; người đọc lại thay đổi trước khi đẩy.
- Sáng tạo thêm được khuyến khích nhưng phải tắt ở headless (xem README, mục "Tự do sáng tạo").

## Hợp đồng tích hợp
- Đọc `docs/contracts/README.md` (schema kho, bảng event + `data`, trường snapshot UI đọc) **trước** khi sửa `sim/*` hoặc `chonoi/web`. Tên event/khóa `data` cố định; đổi thì báo Integrator (tuancdk) và ghi "Lịch sử đổi".
- Vùng file theo issue: #1 Integrator (docs/contracts, plan, verification, AGENTS, skills, README), #2 `sim/gather.py`, #3 `sim/quan.py`, #4 `scenario.py`/`contract.py`, #5 `chonoi/web/`. Agent chỉ sửa vùng của người giao việc.

## Skills / hooks của nhóm
| Skill | Khi nào dùng | Lệnh |
|---|---|---|
| [`run-tests`](.agents/skills/run-tests/SKILL.md) | Trước mỗi push/PR; cần log bằng chứng | `python3 .agents/skills/run-tests/run_tests.py --phase phase-1 --who <handle>` → `docs/proof/<phase>/<handle>/unittest.log` |
| [`headless-check`](.agents/skills/headless-check/SKILL.md) | Sau khi sửa `sim/*`/runner, trước gắn tag | `python3 .agents/skills/headless-check/headless_check.py --out docs/proof/phase-1/headless-check.txt` (2 lần cùng seed so byte + smoke gather→kho→quan) |

## Windows (không có `python3`)
`headless_cmd` giữ `python3 -m chonoi.headless` (CI/macOS/Linux). Test hộp đen gọi đúng lệnh đó, nên trên Windows cần một `python3.exe` trong PATH, nếu không ~23 test lỗi `FileNotFoundError`. Cách gọn nhất (venv trong repo, đã bỏ qua bởi git):
```powershell
python -m venv .venv; Copy-Item .venv\Scripts\python.exe .venv\Scripts\python3.exe
.venv\Scripts\Activate.ps1          # mỗi terminal mới; sau đó `python3 ...` chạy được
$env:PYTHONPATH="tests;."; python3 -m unittest discover -s tests -v
```
Git Bash: `source .venv/Scripts/activate`. Nên đặt `$env:PYTHONUTF8=1` để log tiếng Việt không lỗi mã hóa. Hai skill ở trên tự xử lý UTF-8 và PYTHONPATH.

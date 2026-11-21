---
name: run-tests
description: Chạy toàn bộ test của repo (smoke hộp đen + unit) và lưu log vào docs/proof/<phase>/<handle>/. Dùng trước mọi commit/push và khi cần bằng chứng cho docs/verification.
---

# run-tests

Chạy **trước khi push** và khi cần bằng chứng cho `docs/verification/phase-n.md`.

```bash
python3 .agents/skills/run-tests/run_tests.py --phase phase-1 --who <github-handle>
# Windows không có python3: python .agents/skills/run-tests/run_tests.py ...
```

Script làm gì:
1. Chạy `python -m unittest discover -s tests -v` với `PYTHONPATH=tests:.` và UTF-8 (đúng lệnh test trong `AGENTS.md`).
2. Ghi log vào `docs/proof/<phase>/<handle>/unittest.log` (đầu log có commit, Python, OS).
3. In dòng tóm tắt `Ran N tests … OK/FAILED` và trả **đúng mã thoát** của unittest.

Quy tắc cho agent:
- Test đỏ → **không** push, không sửa test cho xanh; báo người và tìm lỗi ở luật.
- Ghi dòng tóm tắt vào mô tả commit/PR hoặc link log từ `docs/verification/`.
- Smoke hộp đen gọi `headless_cmd` = `python3 …`; trên Windows cần `python3.exe` trong PATH (xem `AGENTS.md`, mục Windows) nếu không ~23 test lỗi `FileNotFoundError`.

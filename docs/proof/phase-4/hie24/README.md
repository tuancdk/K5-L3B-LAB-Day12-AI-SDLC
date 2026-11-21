# Phase 4 — Hie24 — #32

Nguồn: [TICKET-04 trên lab board](https://claude.ai/artifact/E35v787wSx2wDgPTNhMVDg), [issue #32](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC/issues/32). Nền main **32f53d6**.

`chonoi.bench` kế thừa LiveGame/LiveServer, mở `?bench=1`; UI đo requestAnimationFrame sau warmup **3 s**. Không sửa live.py. Kết quả đúng 5 trường; 1% low dùng ceil(1% số frame) chậm nhất. Test công thức, HTTP, dữ liệu lỗi/thiếu thời gian/sai viewport và khóa input: `tests/test_bench.py` (6 test, nằm trong [log chung](../../phase-3/hie24/unittest.log)).

**Đo render thật ngày 21/11/2026:** Windows, Edge **158**, viewport **1280×720**, DPR ≈ 1, seed **42**, Út Sen đứng tại **[2,0]**, cá và Cá Sấu từ sim thật, hiệu ứng mặc định, reduce-motion tắt, tab foreground. Không chạy bộ test trong khoảng đo. Dùng Playwright kết nối Edge đã mở; không thay RAF/đồng hồ hay số frame.

| Chỉ số | [bench.json](../bench.json) | Mốc khuyến nghị |
|---|---:|---:|
| avg_fps | 107.845 | ≥ 60 — đạt |
| p1_low_fps | 21.693 | ≥ 30 — chưa đạt |
| frames / measured_s | 3236 / 30.0061 | khoảng đo thật sau warmup |
| load_ms | 41844.358 | ≤ 10000 — chưa đạt |

`load_ms` tính từ tiến trình tới frame cảnh đầu tiên, **gồm khoảng chờ công cụ mở tab**; giữ nguyên số thật. Đây là bằng chứng trên máy hiện tại, không thay cho đo máy chấm. [SHA-256 code/test](../../phase-3/hie24/sources.sha256).

Lệnh đề xuất cho Integrator khai `bench_cmd` khi chốt manifest v1.3:

```sh
python3 -m chonoi.bench --seed 42 --duration 30 --out docs/proof/phase-4/bench.json
```

Khi dùng browser automation, thêm `--no-open`, mở `BENCH_URL` được in ra với viewport 1280×720 và giữ tab foreground đến khi xong. Hai mốc FPS/load không bắt buộc đạt theo issue; không thay số đo bằng kết quả headless.

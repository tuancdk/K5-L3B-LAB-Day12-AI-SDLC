# Minhduc7904 (Nguyễn Minh Đức) — phản tư cá nhân

- **Tôi đã làm:** vào nhóm ở Phase 4, sau khi tag `phase-4`/`v1.0.0` đã gắn. Tôi được thêm vào `TEAM.md` ở [PR #50](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC-1111/pull/50), vai UI (#5). Phần việc #22 định nhận thì Tuấn đã làm xong, nên tôi chuyển sang hỗ trợ QA cho #33 cùng thd050810:
  - Clone sạch tag `v1.0.0` trên Windows và chạy lại regression ([`54dfcd2`](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC-1111/commit/54dfcd2)). Kết quả: 218/218 OK, headless `day` giống từng byte, soak tất định, `chonoi.live` trả trang 200.
  - Kiểm tra lại UI với server thật ([`31a2ec6`](https://github.com/tuancdk/K5-L3B-LAB-Day12-AI-SDLC-1111/commit/31a2ec6)). Lỗi "quán timeout" vẫn được ghi là chưa điều tra, nhưng thực ra đã được sửa ở `a238425`. Tôi chạy lại 3/3 lần đạt và cập nhật ghi chú.
- **Tôi đã review:** đọc bản nháp `verification/phase-4.md` của Tuấn và đối chiếu với kết quả tự chạy. Mục "browser-check quan timeout" trong đó tôi chỉ ra đúng nguyên nhân: script đã sửa ở `a238425`, không phải nhờ #44 như ghi chú phỏng đoán.
- **AI sai ở đâu & phát hiện:** khi chạy headless `day`, AI quên cờ bắt buộc `--ticks`. Lệnh trả mã 2 và AI suýt ghi "`--days 6` trả mã 2, đạt", trong khi mã 2 đó là do thiếu cờ. Tôi đọc kỹ thông báo lỗi, chạy lại với đủ cờ và ghi lại sai sót này trong bằng chứng.
- **Bài học:** vào muộn thì nên kiểm chứng độc lập và sửa ghi chép đã cũ, đừng cố chen vào code đã khóa. Trước khi viết thì kiểm tra nhánh của người khác để tránh trùng việc.

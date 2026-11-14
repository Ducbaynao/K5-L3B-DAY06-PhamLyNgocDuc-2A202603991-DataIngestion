# Checklist bài nộp trước commit

## Thành phần đã chuẩn bị

- [x] STUDENT.md có tên, MSSV, lớp và repo; hash commit chỉ xác định sau khi tạo commit.
- [x] README có setup/database/.env, phiên bản khóa, ingest/eval dev/test và cách tái lập.
- [x] Mã pipeline A/B/C, embedding thật, pgvector, metadata filter và kiểm tra nạp lại.
- [x] Manifest 84 trang, checksum, nguồn và tình trạng quyền sử dụng được ghi trung thực.
- [x] Benchmark 15 dev/5 test, filter, gold/evidence và checksum giữ nguyên.
- [x] Quyết định C trước test và snapshot nguồn/index được lưu.
- [x] 10 run summaries và 6 hàng metrics dev/test, đủ 60 query-strategy và 180 hits.
- [x] Chỉ mục trace không có text nguồn; full trace giữ local và có hướng dẫn tái tạo.
- [x] Điểm người dùng: 30 coherence records (20 ô A và B/C) và 15 grounding records.
- [x] Nhận xét đầy đủ cho từng record, ghi người hỗ trợ Codex, không giả human_notes.
- [x] 45 metadata records đối chiếu nguồn/offset bằng PDF đọc mới, phương pháp và reviewer được ghi rõ.
- [x] Xem ảnh 20 trang liên quan, ghi nhận bảng 91, ngày khảo sát, mâu thuẫn hồi quy và giới hạn đồ họa.
- [x] Giữ riêng false negative A/test_04 và điểm hỗ trợ khác điểm người dùng, không sửa benchmark/trace gốc.
- [x] Chi phí usage có công thức/nguồn giá; không nhầm với hóa đơn hoặc toàn bộ chi tiêu tài khoản.
- [x] Báo cáo cá nhân ngôi thứ nhất có năm khía cạnh, ví dụ lỗi, đánh đổi, giới hạn và khai báo dùng AI.

## Giới hạn đã công bố, không giả thành đã xác minh

- Quyền tài liệu Studocu chưa xác minh; không nộp PDF/text trace. Cách tiếp cận bản PDF cùng checksum được mô tả, không tạo nguồn tải giả.
- Test đã được kiểm tra containment trong giai đoạn phát triển B; không hoàn toàn chưa được xem xét.
- Điểm người dùng trùng gợi ý AI, nhận xét và metadata do Codex hỗ trợ; không tuyên bố audit mù do người dùng tự chấm toàn bộ.
- Các bất đồng audit được giữ: B/C anchor 5, A/test_02, A/test_04, B/C/test_04.
- Automatic metrics và adjudicated metrics có nhãn riêng. Chọn C trước test không thay đổi; không tuyên bố C hơn A sau khi nhận diện bằng chứng tương đương.
- Ảnh/text local không có trong Git; người chấm cần bản PDF hợp lệ để tái tạo đầy đủ.

## Sau khi tác giả quyết định commit

- [ ] Xem danh sách staged files, không thêm PDF/.env/cache/trace/ảnh/text audit bằng git add -f.
- [ ] Tạo commit; ghi nhận hash để nộp theo yêu cầu lớp (có thể lấy bằng git rev-parse HEAD).
- [ ] Push repo, kiểm tra người chấm truy cập được và nộp link đúng kênh.

Chưa commit, push hoặc thay đổi quyền chia sẻ trong lượt hoàn thiện này. Các bước cuối cần trạng thái Git/GitHub sau commit nên không đánh dấu trước.

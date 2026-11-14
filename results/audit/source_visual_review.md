# Đối chiếu trực quan PDF trước commit

- Phương pháp: Codex xem ảnh render local bằng pypdfium2 5.15.2 và Pillow 13.0.0, đối chiếu với text pypdf và trace đã lưu. Đây là kiểm tra có công cụ hỗ trợ, không phải xác nhận người dùng tự xem tất cả trang.
- PDF: `data/raw/ptbv_report.pdf`; SHA-256 `3382820c1edb8c2598bc3c033742e864bf7848f5e9485f6dd3ca1e8391014742`.
- Ảnh chỉ lưu trong `results/audit/local_text/pdf_review/`, không commit.
- Đã xem 20 trang PDF: 19, 26, 28, 38, 42, 52, 53, 64, 68, 71, 74, 75, 88, 89, 91, 92, 93, 98, 100, 101.

| Trang PDF | Nội dung và kết quả đối chiếu |
|---|---|
| 19, 28, 38 | Nội dung tổng quan/lý thuyết khớp section và các trang trả về; không phải evidence trả lời câu test chỉ vì cùng chủ đề. |
| 26 | Đúng nghiên cứu tại Úc: 600 doanh nghiệp khảo sát, 191 bị loại. |
| 42 | SEC, Hướng dẫn 33-9106, tháng 2/2010; không phải câu hỏi GRI 400. |
| 52 | Sơ đồ nghiên cứu ba giai đoạn có phần đồ họa; text extractor không đại diện toàn bộ sơ đồ. |
| 53 | Ngưỡng tương quan biến tổng <0.3 để loại biến, Cronbach Alpha >0.6; ngưỡng EFA <0.5. Chunk B anchor 5 vẫn cắt ở (<0. trong phần EFA, không thể nói mọi câu đều được giữ trọn. |
| 64 | Likert 5 mức, 1–5; ánh xạ trang PDF 64 / trang in 53 đúng. |
| 68 | Hai cách khảo sát đều nêu 06/04/2022–06/10/2023. A/test_04 top-1 chứa diễn đạt tương đương ở đoạn thứ hai, dù không khớp gold quote đoạn đầu. |
| 71 | Quy trình định lượng và xử lý dữ liệu; không có bằng chứng hai mốc ngày trong chunk trả về. |
| 74–75 | Bảng thang đo và thống kê mẫu nối qua trang; N=239, nhóm kinh nghiệm 142/63/34; không ghép sai dòng/cột khi dùng số 239. |
| 88 | Bảng 4.11: Beta QM=0.236, KN=0.429, DB=0.327; LV Sig=0.859, UB Sig=0.789; LV VIF=5.981. |
| 89 | Phương trình khớp bảng 88; phần VIF nêu LV vi phạm. Ảnh P-P Plot có trên PDF nhưng không có trong chunk text. |
| 91 | Bảng giả thuyết rõ cột: H1/H5 bác bỏ, H2/H3/H4 chấp nhận. Top-3 A chứa cả hàng H1 và H5 trong hai chunk; có thể hợp bằng chứng cho grounding. |
| 92–93 | Phương trình vẫn ghi QM=0.236 và DB=0.327, nhưng đoạn diễn giải gán QM=0.327 và DB=0.236. Đây là mâu thuẫn nguồn đã công bố, không tự sửa. |
| 98 | Đoạn quy định tỷ lệ thành viên nữ ghi Na Uy 40%; đúng evidence dev_14 theo nội dung nguồn. |
| 100–101 | Hạn chế khảo sát tại một thời điểm và đề xuất chuỗi thời gian nối qua trang, đúng đáp án test_05. |

## Phạm vi kết luận

Tôi dùng kết quả đối chiếu có hỗ trợ trên để giải thích audit và phát hiện false negative của exact quote. Tôi không sửa PDF, benchmark, cấu hình chunk hoặc các trace gốc. Ảnh có thông tin footer người tải được giữ local. Chưa tuyên bố đã kiểm tra trực quan toàn bộ 153 trang.

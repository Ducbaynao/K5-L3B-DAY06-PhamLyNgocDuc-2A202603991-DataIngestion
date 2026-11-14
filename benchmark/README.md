# Benchmark — Bộ câu hỏi và Quy tắc đánh giá trước thử nghiệm

Tài liệu này xác lập định dạng dữ liệu benchmark, quy ước trang, tiêu chí lựa chọn câu hỏi, quy tắc phân chia dev/test, cơ chế phòng chống rò rỉ thông tin, tiêu chí quyết định chiến lược và danh sách 10 vị trí neo nguồn phục vụ đánh giá tính mạch lạc (chunk coherence) sau này.

## 1. Schema dữ liệu và quy ước trang

Bộ câu hỏi được lưu tại `benchmark/questions.jsonl`, mỗi dòng là một JSON object với schema:

- `id`: Mã định danh duy nhất của câu hỏi (`dev_01`–`dev_15`, `test_01`–`test_05`).
- `split`: Tập phân chia (`dev` hoặc `test`).
- `question`: Nội dung câu hỏi truy xuất.
- `expected_answer`: Câu trả lời ngắn gọn, chính xác dựa trên nội dung nguồn.
- `gold_source_id`: Định danh tài liệu nguồn chuẩn (`ptbv_report`).
- `gold_page`: Số trang PDF vật lý (1-based physical page number, nằm trong dải 18–101).
- `evidence_quote`: Đoạn văn bản trích dẫn nguyên văn từ văn bản chuẩn hóa của trang nguồn (`data/extracted/pages.jsonl`), đủ bằng chứng trả lời toàn bộ câu hỏi.
- `filter`: Điều kiện lọc metadata nếu câu hỏi yêu cầu theo ngữ cảnh (ví dụ `{"section": "chuong_3"}`), hoặc `null` nếu không lọc.
- `alternative_gold`: (Tùy chọn) Danh sách các nguồn/trang/đoạn bằng chứng bổ sung hợp lệ nếu câu hỏi có nhiều vị trí trong báo cáo cùng cung cấp câu trả lời (ví dụ `dev_11`).

### Quy ước trang:
Dự án sử dụng số trang PDF vật lý bắt đầu từ 1 (`1-based page number`) xuyên suốt manifest, metadata chunk và benchmark gold. Số trang in ấn gốc trên tài liệu có thể lệch so với trang PDF vật lý (ví dụ: trang PDF 64 tương ứng trang in 53). Khi lập trình đọc file PDF bằng thư viện `pypdf`, phép ánh xạ 0-based index chỉ diễn ra đúng một lần tại tầng đọc (`index = page - 1`).

## 2. Cách chọn và phân chia tập dev / test

Bộ benchmark gồm **đúng 20 câu hỏi** được xây dựng thủ công từ văn bản đã chuẩn hóa, phân bố đều trên cả 5 chương nội dung chính của báo cáo (mỗi chương 4 câu: 3 dev, 1 test):

- **Tập dev (15 câu)**: `dev_01` đến `dev_15`.
- **Tập test (5 câu)**: `test_01` đến `test_05`.
- **Phân loại câu hỏi**:
  - Trực tiếp (Direct): 8 câu (`dev_01`, `dev_02`, `dev_05`, `dev_08`, `dev_10`, `dev_13`, `test_01`, `test_03`).
  - Diễn đạt lại (Rephrased): 6 câu (`dev_03`, `dev_06`, `dev_09`, `dev_11`, `dev_14`, `test_04`).
  - Có điều kiện / Ngoại lệ (Conditional/Exception): 6 câu (`dev_04`, `dev_07`, `dev_12`, `dev_15`, `test_02`, `test_05`).
- **Câu hỏi có filter**: 4 câu (chiếm 20%):
  - `dev_01`: `{"section": "chuong_3"}`
  - `dev_07`: `{"section": "chuong_2"}`
  - `test_02`: `{"section": "chuong_4"}` (Filter thuộc test)
  - `test_05`: `{"section": "chuong_5"}` (Filter thuộc test)
- **Tính độc lập dev/test**: Không có cặp câu dev/test nào chỉ khác cách diễn đạt nhưng dùng chung một đáp án hay cùng một đoạn bằng chứng. Mỗi câu hỏi khai thác một sự kiện hoặc khía cạnh độc lập.

## 3. Nguy cơ rò rỉ dữ liệu và nguyên tắc đóng băng (Holdout Protocol)

Do toàn bộ 20 câu hỏi được trích xuất từ cùng một báo cáo nghiên cứu, nguy cơ **rò rỉ ngữ cảnh (contextual leakage)** giữa các chương và giữa các phần là có thể xảy ra:
1. **Nguyên tắc đóng băng**: Bộ benchmark được cố định trước khi triển khai và đánh giá bất kỳ pipeline truy xuất hay embedding nào. Checksum SHA-256 của `benchmark/questions.jsonl` được tính toán và lưu lại tại thời điểm này.
2. **Quy tắc Holdout Test**: Tập 5 câu test là tập kiểm thử độc lập cuối cùng. **Tuyệt đối không sử dụng kết quả trên tập test để tinh chỉnh siêu tham số, kích thước chunk hay chiến lược metadata**. Mọi quyết định lựa chọn cấu hình chỉ được căn cứ trên tập dev.

## 4. Tiêu chí chọn cấu hình trên tập Dev

Khi so sánh giữa các chiến lược dữ liệu (ví dụ Chiến lược A: chunk cố định, Chiến lược B: chunk theo đoạn, Chiến lược C: chunk theo đoạn kết hợp filter), thứ tự ưu tiên quyết định lựa chọn được xác lập như sau:
1. **Ưu tiên 1 - Evidence Hit@3**: Tỷ lệ câu hỏi trong tập dev có ít nhất một chunk trong top-3 chứa đủ bằng chứng hợp lệ.
2. **Ưu tiên 2 - Hit@1**: Tỷ lệ câu hỏi đạt hit ngay tại vị trí top-1.
3. **Ưu tiên 3 - Chi phí và thời gian Ingestion**: Lượng token embedding tiêu tốn, thời gian nạp và dung lượng lưu trữ vector store.

## 5. Định nghĩa Hit và Chính sách chấp nhận Alternative Gold

- **Định nghĩa Hit bắt buộc**: Một chunk được coi là "Hit" khi và chỉ khi đáp ứng đồng thời 3 điều kiện:
  1. **Đúng Document/Source ID**: Chunk thuộc đúng tài liệu nguồn chuẩn (`ptbv_report`).
  2. **Đúng trang nguồn**: Chunk có metadata `page` trùng khớp với `gold_page` (hoặc nằm trong danh sách `alternative_gold` hợp lệ).
  3. **Đủ bằng chứng trong một chunk đơn lẻ**: Văn bản của **chính chunk đó** phải chứa đầy đủ `evidence_quote` đã đăng ký (hoặc bằng chứng tương đương trọn vẹn, không bị ngắt quãng làm mất điều kiện/chủ thể) đủ để chứng minh toàn bộ `expected_answer`.
- **Đánh giá hợp bằng chứng đa chunk (Multi-chunk Evidence Aggregation)**:
  - Nếu bằng chứng bị chia cắt qua nhiều chunk liền kề, hệ thống ghi nhận đó là lỗi phân mảnh (chunk fragmentation) và **không** tính hit cho Evidence Hit@3 bắt buộc.
  - Phép đánh giá hợp nhất bằng chứng từ nhiều chunk chỉ được coi là chỉ số phân tích bổ sung; **tuyệt đối không thay thế chỉ số Evidence Hit@3 bắt buộc**.
- **Chính sách Alternative Gold**: Trong các tài liệu nghiên cứu, cùng một kết quả phân tích có thể xuất hiện tại nhiều nơi (ví dụ: phương trình hồi quy xuất hiện ở bảng kết quả trang 89 và bảng tóm tắt trang 92). Các vị trí này được khai báo minh bạch trong mảng `alternative_gold`. Nếu một chunk truy xuất trúng bất kỳ vị trí hợp lệ nào được đăng ký trước, hệ thống ghi nhận là một Hit hợp lệ.

## 6. Danh sách 10 vị trí neo nguồn (Anchors) để chấm Chunk Coherence

Để đảm bảo tính khách quan khi đánh giá tính mạch lạc của chunk (Chunk Coherence thang điểm 0–2) sau khi các pipeline tạo chunk, 10 vị trí nội dung nguồn được chọn trước (2 vị trí trên mỗi chương):

*(Lưu ý: Tại thời điểm này chưa tạo chunk nên CHƯA thực hiện chấm điểm coherence)*.

| STT | Chương | Trang PDF | Định danh vị trí (Anchor Text) |
|---|---|:---:|---|
| 1 | Chương 1 | 18 | `1.1.1. Các nghiên cứu nước ngoài`: "Từ góc độ lịch sử, sự phát triển và trọng tâm của báo cáo liên quan đến PTBV đã có một số thay đổi (Fifka, 2012; Kolk, 2010)." |
| 2 | Chương 1 | 35 | `1.4. Khoảng trống nghiên cứu`: "Khoảng trống về dữ liệu trong các nghiên cứu liên quan đến công bố thông tin về phát triển bền vững (PTBV) tại Việt Nam đã trở thành một điểm quan trọng cần xem xét." |
| 3 | Chương 2 | 40 | `2.3. Quy định về BCPTBV`: "Bộ chuẩn mực GRI được tổ chức thành bốn nhóm chính là tổng quát, kinh tế, môi trường, và xã hội." |
| 4 | Chương 2 | 47 | `Lý thuyết tính hợp pháp`: "Ghozali và Chariri (2007) cũng cho rằng lý thuyết cơ bản về tính hợp pháp là hợp đồng xã hội giữa công ty và cộng đồng nơi công ty hoạt động và sử dụng các nguồn lực kinh tế." |
| 5 | Chương 3 | 53 | `Điều tra sơ bộ`: "Giai đoạn điều tra sơ bộ trong quy trình nghiên cứu (bước 6 đến bước 8) đóng vai trò quan trọng trong việc đảm bảo chất lượng và hiệu suất của các thang đo trước khi tiến hành nghiên cứu chính thức." |
| 6 | Chương 3 | 64 | `Thang đo Likert`: "Bảng câu hỏi được thiết kế theo thang đo Likert 5 mức độ được đánh số từ 1 tới 5 theo mức độ đồng ý tăng dần." |
| 7 | Chương 4 | 75 | `4.1.2.1. Thống kê mô tả`: "Trong 239 đối tượng tham gia khảo sát về kinh nghiệm làm việc, có 142 đối tượng có kinh nghiệm làm việc từ 2 đến 5 năm chiếm 59.4%" |
| 8 | Chương 4 | 89 | `Kiểm định đa cộng tuyến`: "Trong mô hình hồi quy bội, một giả thuyết được thêm vào là các biến độc lập không có tương quan hoàn toàn với nhau." |
| 9 | Chương 5 | 94 | `5.1. Kết luận`: "Thứ nhất, nghiên cứu sử dụng phương pháp nghiên cứu định tính. Trong quá trình này, nghiên cứu đã tiến hành khảo sát các nghiên cứu liên quan đến đề tài cả trong và ngoài nước" |
| 10 | Chương 5 | 100 | `Lãnh đạo ESG`: "Bổ Nhiệm Người Lãnh Đạo ESG: Xác định một người lãnh đạo với trách nhiệm và quyền lực cần thiết để dẫn dắt các sáng kiến PTBV." |

## 7. Khóa phiên bản và Nhật ký sửa đổi Benchmark trước thử nghiệm

### 7.1. Các sửa đổi chất lượng trước thử nghiệm (Pre-experiment Quality Fixes)
1. **Sửa `test_02`**: Đối chiếu bảng tóm tắt giả thuyết trên trang PDF 91 cho thấy cả Giả thuyết H1 và Giả thuyết H5 đều có kết quả "Bác bỏ". Câu hỏi, đáp án và evidence quote đã được mở rộng để bao gồm trọn vẹn cả H1 và H5 (không cắt gọt né lỗi).
2. **Sửa `dev_07`**: Bổ sung phần đuôi câu bị thiếu trên trang 47 vào `evidence_quote` (`các nguồn lực kinh tế.`) để đảm bảo bằng chứng hỗ trợ 100% câu trả lời.
3. **Sửa `dev_06`**: Bổ sung vế câu trước ("Thiếu minh bạch trong quy định: Một thách thức lớn là sự thiếu hụt quy định minh bạch...") vào `evidence_quote` để làm rõ chủ thể của từ "điều này".
4. **Đối chiếu trực quan bảng biểu**: Đã đối chiếu luồng văn bản bảng tại các trang PDF 64 (thang đo Likert), trang 88 (Bảng 4.11 hồi quy), trang 89 (kiểm định đa cộng tuyến VIF), trang 91 (bảng tóm tắt giả thuyết), trang 92 (bảng kết quả tổng hợp). Do môi trường thiếu thư viện render ảnh PDF (PyMuPDF, pdf2image), việc đối chiếu được thực hiện qua luồng trích xuất văn bản có cấu trúc của pypdf.

### 7.2. Khóa phiên bản hiện hành (Benchmark Version Freeze)
- **Đường dẫn**: `benchmark/questions.jsonl`
- **Số câu hỏi**: 20 câu (15 dev, 5 test)
- **Số câu có filter**: 4 câu (2 dev, 2 test)
- **Mã băm SHA-256**: `ed0be0f44f105e00ef83b1150525226f4073621b03beed783e94a56b63305796`
- **Trạng thái**: Đã khóa trước khi chạy bất kỳ pipeline retrieval nào. Chưa có truy xuất retrieval nào được thực hiện trước thời điểm này.


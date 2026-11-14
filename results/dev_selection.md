# Quyết định Lựa chọn Cấu hình trước khi chạy Test

- **Ngày ghi nhận**: 14/11/2026
- **Tác giả**: Phạm Lý Ngọc Đức (MSSV: 2A202603991, Lớp L3B)
- **Tập dữ liệu áp dụng**: 15 câu hỏi tập `dev` (`dev_01`–`dev_15`) từ `benchmark/questions.jsonl`
- **Mã băm Benchmark khóa trước thử nghiệm**: `ed0be0f44f105e00ef83b1150525226f4073621b03beed783e94a56b63305796`

---

## 1. Bảng so sánh kết quả 3 Chiến lược trên tập Dev

| Tiêu chí | Chiến lược A (Fixed-size) | Chiến lược B (Paragraph-aware) | Chiến lược C (Metadata Filtering) |
|---|:---:|:---:|:---:|
| **Phương pháp Chunking** | Kích thước cố định 500 ký tự, overlap 50 | Theo đoạn/cấu trúc, `max_size=800` | Tái sử dụng 100% chunk và index của B |
| **Tổng số chunk trong store** | 375 chunks | 256 chunks | 256 chunks (dùng chung index B) |
| **Độ dài chunk trung bình** | 447,0 ký tự (Min: 66, Max: 500) | 597,7 ký tự (Min: 52, Max: 943) | 597,7 ký tự |
| **Tokens Embedding Ingest** | 81.855 prompt tokens | 74.116 prompt tokens | 0 tokens bổ sung (dùng lại index B) |
| **Thời gian Ingest (lượt 1 / lượt 2 cache)** | 10,55 s / 4,66 s | 7,50 s / 4,86 s | Không cần ingest riêng |
| **Hit@1 (Dev 15 câu)** | 7/15 (46,7%) | **9/15 (60,0%)** | **9/15 (60,0%)** |
| **Evidence Hit@3 (Dev 15 câu)** | 11/15 (73,3%) | **12/15 (80,0%)** | **12/15 (80,0%)** |
| **Số câu đạt Evidence Hit@3 mới** | — | +2 câu (`dev_09`, `dev_14`) | +2 câu (`dev_09`, `dev_14`) |
| **Số câu mất Evidence Hit@3** | — | -1 câu (`dev_11`) | -1 câu (`dev_11`) |
| **Tỷ lệ tuân thủ Filter metadata** | Không lọc (N/A) | 1/2 câu filter bị lọt trang ngoài section | **2/2 câu filter tuân thủ 100% section** |

---

## 2. Áp dụng quy tắc ưu tiên để quyết định

Theo [Mục 4 của BENCHMARK.md](../benchmark/README.md), thứ tự ưu tiên lựa chọn chiến lược được quy định như sau:
1. **Ưu tiên 1 - Evidence Hit@3**:
   - Cả Chiến lược B và C đều đạt **12/15 (80,0%)**, vượt trội so với Chiến lược A (**11/15, 73,3%**).
   - Chiến lược B và C giải quyết triệt để lỗi phân mảnh bằng chứng của `dev_09` (trang PDF 53) và lỗi xếp hạng bằng chứng của `dev_14` (trang PDF 98).
2. **Ưu tiên 2 - Hit@1**:
   - Cả Chiến lược B và C đều đạt **9/15 (60,0%)**, tăng thêm 2 câu trúng ngay ở hạng 1 so với Chiến lược A (**7/15, 46,7%**) nhờ đẩy `dev_10` và `dev_15` từ hạng 2 lên hạng 1.
3. **Ưu tiên 3 - Chi phí và thời gian Ingestion**:
   - Chiến lược B và C dùng 256 chunks (giảm 31,7% số vector so với 375 chunks của A). Lượt ingest B ghi nhận 74.116 prompt tokens, ít hơn A 7.739 tokens (9,5%); B có 3 cache hits từ trước nên đây là mức sử dụng API quan sát được, không phải so sánh hai lượt hoàn toàn không cache. Tôi chưa quy đổi chi phí tiền hoặc đo dung lượng database.
   - Chiến lược C tái sử dụng 100% index và vector của Chiến lược B, không tiêu tốn thêm bất kỳ token hay dung lượng nào.
4. **So sánh trực tiếp giữa Chiến lược B và Chiến lược C**:
   - Trên 13 câu không có filter, Chiến lược B và C cho kết quả 100% giống nhau từ ID chunk, điểm cosine similarity đến thứ tự xếp hạng.
   - Trên 2 câu có filter (`dev_01` và `dev_07`):
     - Ở `dev_01` (yêu cầu thuộc `chuong_3`), Chiến lược B trả về hạng 3 thuộc `chuong_4` (trang PDF 76 - nằm ngoài phạm vi chương yêu cầu). Trong khi đó, Chiến lược C loại bỏ hoàn toàn nhiễu ngoài phạm vi và thay thế bằng trang 53 (thuộc đúng `chuong_3`).
     - Chiến lược C đảm bảo 100% các kết quả truy xuất tuân thủ đúng phạm vi nghiệp vụ được chỉ định trong truy vấn.

---

## 3. Kết luận Lựa chọn

- **Cấu hình được chọn**: **Chiến lược C** (Chunking theo đoạn có cấu trúc `by_paragraph(max_size=800)` kết hợp lọc metadata `section` khi truy vấn có filter; không có filter thì truy xuất cosine toàn văn như Chiến lược B).
- **Trường hợp hòa B–C**: B và C hòa theo Hit@3, Hit@1 và dùng chung chi phí ingest/index. Tôi chọn C vì đáp ứng yêu cầu phạm vi của câu hỏi có filter; đây là lý do thực tế khi các tiêu chí chính hòa, không phải bằng chứng C có retrieval accuracy cao hơn B.
- **Giới hạn cấu hình**: `max_size=800` hiện là ngưỡng mục tiêu, không phải giới hạn cứng: có 2/256 chunk dài hơn 800, dài nhất 943 ký tự. A–B đồng thời đổi ranh giới, kích thước và overlap; tôi chỉ kết luận về toàn bộ chiến lược chunking. Tôi giữ nguyên cấu hình đã chạy thay vì sửa tham số trước test để làm đẹp kết quả.
- **Giới hạn test**: Tôi chưa chạy retrieval test, nhưng công cụ đã kiểm tra containment của evidence cho cả 20 câu trong giai đoạn phát triển B. Vì vậy test không hoàn toàn chưa được xem xét ở mức cấu trúc chunk; tôi không dùng phép kiểm tra này làm metric retrieval và cần nêu nguy cơ thiên lệch.
- **Cam kết nguyên tắc đóng băng (Holdout Protocol)**:
  - Quyết định này được đưa ra hoàn toàn dựa trên dữ liệu phân tích tập `dev`.
  - Toàn bộ kết quả retrieval trên tập `test` (5 câu) **CHƯA ĐƯỢC CHẠY** tại thời điểm khóa quyết định này.

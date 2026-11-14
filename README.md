# Day 06 · Data Ingestion Engineering

- **Học viên:** Phạm Lý Ngọc Đức
- **MSSV:** 2A202603991
- **Lớp:** L3B
- **Báo cáo cá nhân:** [report/individual/2A202603991_PhamLyNgocDuc.md](report/individual/2A202603991_PhamLyNgocDuc.md)
- **Nhật ký thí nghiệm:** [artifacts/experiment_log.csv](artifacts/experiment_log.csv)
- **Bảng tổng hợp chỉ số:** [results/metrics.csv](results/metrics.csv)
- **Quyết định chọn cấu hình trước test:** [results/dev_selection.md](results/dev_selection.md)
- **Snapshot đóng băng trước test:** [results/pre_test_snapshot.json](results/pre_test_snapshot.json)

---

## 1. Giới thiệu Chủ đề và Dữ liệu

### Chủ đề nghiên cứu
Nghiên cứu về **"Các nhân tố ảnh hưởng tới hoạt động công bố báo cáo phát triển bền vững tại các doanh nghiệp niêm yết trên thị trường chứng khoán Việt Nam"** (Báo cáo nghiên cứu khoa học sinh viên năm 2024, Trường Đại học Kinh tế Quốc dân).

### Corpus và Quy ước trang
- **Quy mô:** 84 trang PDF vật lý (từ trang 18 đến 101, bao gồm toàn bộ Chương 1 đến Chương 5).
- **Loại trừ:** Bìa, mục lục, danh mục từ viết tắt, kết luận chung, tài liệu tham khảo và phụ lục.
- **Quy ước trang:** Đánh số trang vật lý 1-based xuyên suốt toàn bộ manifest, chunk metadata và benchmark gold (ví dụ: trang PDF 64 tương ứng trang in 53).
- **Văn bản chuẩn hóa:** 153.080 ký tự Unicode NFC; loại bỏ watermark/footer lặp lại, không có trang rỗng.
- **Tình trạng bản quyền:** Tài liệu tải từ Studocu; quyền sử dụng và tái phân phối được ghi nhận là *chưa xác minh*. Vì lý do an toàn bản quyền và bảo mật, file PDF gốc (`data/raw/ptbv_report.pdf`), văn bản trích xuất (`data/extracted/pages.jsonl`), cache local và trace chứa text được lưu ở máy local và được `.gitignore` loại trừ hoàn toàn.
- **Hướng dẫn kiểm tra checksum và phục hồi PDF:** Xem [data/README.md](data/README.md). Mã băm SHA-256 của file PDF gốc:
  ```text
  3382820c1edb8c2598bc3c033742e864bf7848f5e9485f6dd3ca1e8391014742
  ```

---

## 2. Thiết lập Môi trường và Hạ tầng

### Yêu cầu tiên quyết
- Hệ điều hành: Windows / macOS / Linux.
- Python: 3.11 – 3.14 (Dự án đã kiểm thử trên Python 3.12.10).
- Docker & Docker Compose: Dùng để chạy PostgreSQL 16 + pgvector.

### Các bước cài đặt
```powershell
# 1. Tạo và kích hoạt môi trường ảo Python
python -m venv starter\.venv
# Windows PowerShell:
.\starter\.venv\Scripts\Activate.ps1
# Linux/macOS:
# source starter/.venv/bin/activate

# 2. Cài đặt thư viện phụ thuộc
python -m pip install -r starter/requirements-lock.txt

# 3. Khởi động cơ sở dữ liệu PostgreSQL + pgvector
docker compose -f starter/docker-compose.yml -p day6_student_starter up -d --wait

# 4. Kiểm tra kết nối hạ tầng
python starter/scripts/check_setup.py
```

### Cấu hình Môi trường (`starter/.env`)
Tạo file `starter/.env` từ `starter/.env.example`. File này được Git ignore tuyệt đối; **không bao giờ commit API key**:
```ini
DATABASE_URL=postgresql://day6:day6_local_only@127.0.0.1:55433/day6_lab
OPENAI_API_KEY=your_openai_api_key_here
EMBEDDING_MODEL=text-embedding-3-small
```
- **Embedding Model:** OpenAI `text-embedding-3-small` (1536 chiều).
- **Vector Store:** PostgreSQL 16.16 + pgvector 0.8.7. Metric khoảng cách: Cosine distance (`<=>`).

---

## 3. Ba Chiến lược Dữ liệu Triển khai

| Chiến lược | Phương pháp Chunking | Siêu tham số | Metadata & Tìm kiếm Vector | Số chunk trong DB |
|---|---|---|---|:---:|
| **A (Baseline)** | Fixed-size | `size=500`, `overlap=50`, trong trang | Cosine toàn corpus, không lọc | 375 |
| **B (Cấu trúc)** | `by_paragraph` | Gom đoạn tự nhiên, `max_size=800`, tách câu nếu dài | Cosine toàn corpus, không lọc | 256 |
| **C (Lọc metadata)** | Dùng lại B | Tái sử dụng 100% chunk và vector của B | Cosine có lọc `section` khi câu hỏi yêu cầu | 256 |

- **So sánh A–B:** Đánh giá toàn bộ chiến lược chunking vì đồng thời thay đổi ranh giới, kích thước mục tiêu và overlap. B có 2 chunk vượt ngưỡng mục tiêu 800, dài nhất 943 ký tự.
- **So sánh B–C:** Đánh giá riêng biệt tác động của metadata filtering (vì B và C dùng chung 100% không gian vector).
- **Quyết định chọn cấu hình:** Chiến lược C đã được lựa chọn chính thức trước khi chạy test dựa trên 3 tiêu chí ưu tiên tại [results/dev_selection.md](results/dev_selection.md).

---

## 4. Lệnh Thực thi và Tái lập Toàn bộ Pipeline

Mọi lệnh chạy từ thư mục gốc của repository:

```powershell
# BƯỚC 1: Trích xuất và Kiểm tra tính toàn vẹn Corpus / Benchmark
.\starter\.venv\Scripts\python.exe -X utf8 -m starter.src.ingestion
.\starter\.venv\Scripts\python.exe -X utf8 scripts/verify_corpus_benchmark.py

# BƯỚC 2: Ingestion dữ liệu
# Ingest Baseline A (tạo 375 chunks)
.\starter\.venv\Scripts\python.exe -X utf8 -m starter.src.run --strategy A --action ingest --split dev --confirm-api

# Ingest Chiến lược B (tạo 256 chunks)
.\starter\.venv\Scripts\python.exe -X utf8 -m starter.src.run --strategy B --action ingest --split dev --confirm-api

# Kiểm tra tính lũy kế (idempotence): Chạy lại lệnh ingest B để xác nhận chunk count giữ nguyên 256 và cache hit 100%:
.\starter\.venv\Scripts\python.exe -X utf8 -m starter.src.run --strategy B --action ingest --split dev --confirm-api

# (Lưu ý: Chiến lược C tái sử dụng index B nên không cần chạy ingest riêng)

# BƯỚC 3: Đánh giá trên tập Dev (15 câu)
.\starter\.venv\Scripts\python.exe -X utf8 -m starter.src.run --strategy A --action eval --split dev --confirm-api
.\starter\.venv\Scripts\python.exe -X utf8 -m starter.src.run --strategy B --action eval --split dev --confirm-api
.\starter\.venv\Scripts\python.exe -X utf8 -m starter.src.run --strategy C --action eval --split dev --confirm-api

# BƯỚC 4: Đánh giá Test sau khi chốt cấu hình (5 câu; đã công bố kiểm tra containment trước đó)
.\starter\.venv\Scripts\python.exe -X utf8 -m starter.src.run --strategy A --action eval --split test --final-test --confirm-api
.\starter\.venv\Scripts\python.exe -X utf8 -m starter.src.run --strategy B --action eval --split test --final-test --confirm-api
.\starter\.venv\Scripts\python.exe -X utf8 -m starter.src.run --strategy C --action eval --split test --final-test --confirm-api
```

---

## 5. Kết quả Thực nghiệm Tổng hợp

Chi tiết số liệu đã được đối chiếu và lưu tại [results/metrics.csv](results/metrics.csv):

| Chiến lược | Hit@1 (Dev) | Evidence Hit@3 (Dev) | Hit@1 (Test) | Evidence Hit@3 (Test) | Số vector | Ingest Tokens | Eval Tokens |
|---|:---:|:---:|:---:|:---:|---:|---:|---:|
| **Baseline A** | 7/15 (46,7%) | 11/15 (73,3%) | 3/5 (60,0%) | 3/5 (60,0%) | 375 | 81.855 | 908 (dev) + 324 (test) |
| **Chiến lược B** | 9/15 (60,0%) | 12/15 (80,0%) | 3/5 (60,0%) | **4/5 (80,0%)** | 256 | 74.116 | 0 (cache 100%) |
| **Chiến lược C** | **9/15 (60,0%)** | **12/15 (80,0%)** | **4/5 (80,0%)** | **4/5 (80,0%)** | 256 | 0 (dùng index B) | 0 (cache 100%) |

### Tác động của Cache Local
- Vector embedding được lưu cache trong SQLite (`starter/.cache/embeddings_cache.sqlite`).
- Lần nạp thứ hai của B đạt **256/256 cache hits**, tiêu tốn **0 prompt tokens**.
- Các lượt eval sau của B và C tái sử dụng vector truy vấn đã tạo từ A, tiêu tốn **0 prompt tokens** và hoàn thành trong ~0,17–0,57 giây.
- Thời gian chạy lượt nóng (có cache) không phản ánh tốc độ thuật toán truy xuất so với lượt lạnh (không cache).

---

## 6. Audit Đánh giá và Hướng dẫn Thẩm định Thủ công

Toàn bộ dữ liệu kiểm tra và đối chiếu được tổ chức tại thư mục `results/audit/`:
- **Bảng tổng hợp & Hướng dẫn:** [results/audit/audit_summary.md](results/audit/audit_summary.md).
- **Kiểm tra cơ học Metadata:** [results/audit/metadata_audit.csv](results/audit/metadata_audit.csv) (100% khớp nguồn trích xuất; Chiến lược C đạt 100% tuân thủ bộ lọc trên câu có filter).
- **Bảng Coherence (10 anchors):** [results/audit/coherence_audit.csv](results/audit/coherence_audit.csv).
- **Bảng Grounding (5 câu test):** [results/audit/grounding_audit.csv](results/audit/grounding_audit.csv).

Tôi đã nộp đủ điểm coherence/grounding; kết quả nằm trong [human_audit_summary.json](results/audit/human_audit_summary.json). Nhận xét và kiểm tra 45 metadata records được Codex hỗ trợ hoàn thiện, ghi ở các cột assisted_review_* thay vì giả xác nhận người chấm. C dùng điểm coherence của ô B/C. Các khác biệt khi đọc lại evidence được công bố, không sửa điểm gốc.

### Dành cho Người Chấm / Học viên duyệt điểm:
1. Mở trang web review trực quan tại máy local:
   ```text
   results/audit/local_text/review.html
   ```
2. Trang web hiển thị toàn văn câu hỏi, đáp án, câu neo, toàn bộ văn bản chunk và toàn bộ văn bản trang gốc mà không cắt ngắn text; các gợi ý của AI được ẩn trong thẻ thu gọn để tránh dẫn dắt thiên lệch.
3. Chấm điểm theo thang điểm 0–2 và bấm **Xuất Kết Quả (JSON / CSV)** hoặc điền trực tiếp vào cột `human_score` trong các file CSV tương ứng.
4. Chạy script xác thực và tổng hợp điểm chính thức:
   ```powershell
   .\starter\.venv\Scripts\python.exe scripts/aggregate_human_audit.py
   # Hoặc nhập trực tiếp từ file xuất của trang review:
   .\starter\.venv\Scripts\python.exe scripts/aggregate_human_audit.py --import-file human_audit_scores.json
   ```

---


### Kết quả đối chiếu cuối và minh chứng để nộp

- [Checklist trước commit](results/submission_checklist.md).
- [Đối chiếu evidence tương đương](results/evidence_adjudication.json): A/test_04 có đúng hai ngày ở top-1 nhưng trượt exact quote gốc. Giữ số liệu tự động; bảng bổ sung sau đối chiếu là A 4/5 Hit@1 và 4/5 Hit@3, B 3/5 và 4/5, C 4/5 và 4/5. Không kết luận C hơn A về test sau đối chiếu.
- [Chỉ mục 180 hits không chứa text nguồn](results/retrieval_trace_index.csv), gồm IDs, trang, score và nhãn tự động để kiểm tra khi không nộp trace text.
- [Nhật ký visual review](results/audit/source_visual_review.md): 20 trang PDF được render/xem local; ảnh nằm ngoài Git.
- [Ước tính chi phí](results/cost_estimate.json): 157.203 prompt tokens ghi nhận, khoảng 0,00314406 USD theo giá công khai 0,02 USD/triệu tokens của [OpenAI](https://developers.openai.com/api/docs/models/text-embedding-3-small), kiểm tra 14/11/2026. Không phải hóa đơn; không gồm thuế, credits hoặc usage ngoài các run đã lưu.

Các điểm người dùng và nhãn hỗ trợ AI được tách rõ; xem [audit summary](results/audit/audit_summary.md). Không chạy lại prepare_audit.py lên các CSV đã chấm vì script tạo mẫu có thể ghi đè điểm/nhận xét. Khi tái lập, sao lưu audit hiện tại và dùng thư mục làm việc riêng. Các summary gốc ghi chi phí chưa xác định được giữ làm lịch sử, ước tính nằm trong artifact bổ sung.

### Tái lập khi không có PDF/trace trong Git

1. Người chấm tự cung cấp bản PDF được phép truy cập tại `data/raw/ptbv_report.pdf` và kiểm tra SHA-256 trong manifest; tôi không tạo URL tải giả khi chưa có nguồn đã xác minh.
2. Cài phiên bản trong `starter/requirements-lock.txt`, khởi động database và cấu hình `.env` local theo hướng dẫn trên.
3. Chạy extraction/verifier, ingest A/B, eval A/B/C dev/test bằng các lệnh đã ghi. Việc tái lập gọi embedding có thể phát sinh phí; cache và thời gian phụ thuộc môi trường.
4. Đối chiếu IDs/pages/scores với `results/retrieval_trace_index.csv` và summary từng run; text trace được tạo ở local. Bộ adjudication sau test là artifact nhận xét riêng, không tự động sửa nhãn exact quote.
5. Điểm người dùng đã nộp và nhận xét có hỗ trợ nằm trong các CSV audit; chỉ nhập điểm mới khi người chấm thực sự đánh giá và giữ lịch sử bản cũ.

Nếu muốn render PDF để tự xem, cài dependency tùy chọn bằng `python -m pip install -r scripts/requirements-review.txt`. Chúng không cần thiết để chạy retrieval. Ảnh local hiện có trong `results/audit/local_text/pdf_review/`.

## 7. Tài liệu Hướng dẫn của Môn học

- [GUIDE.md](GUIDE.md): Các bước thực hiện và công thức tính chỉ số.
- [BENCHMARK.md](BENCHMARK.md): Quy chuẩn bộ câu hỏi và năm tiêu chí benchmark.
- [CHECKPOINTS.md](CHECKPOINTS.md): Cột mốc tiến độ thực hành 4 giờ.
- [RUBRIC.md](RUBRIC.md): Tiêu chí chấm điểm chi tiết.
- [RULES.md](RULES.md): Quy định về dữ liệu, AI và bảo mật API.
- [SUBMISSION.md](SUBMISSION.md): Checklist và quy định bài nộp.

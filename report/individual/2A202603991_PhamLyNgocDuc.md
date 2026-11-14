# Báo cáo cá nhân — Day 06: Data Ingestion Engineering

- Họ và tên: Phạm Lý Ngọc Đức
- MSSV: 2A202603991
- Lớp: L3B
- Ngày cập nhật: 14/11/2026
- Phạm vi kết quả hiện tại: Tôi đã chạy A/B/C trên dev/test, nộp điểm coherence/grounding và hoàn thiện nhận xét, kiểm tra metadata, đối chiếu PDF có Codex hỗ trợ. Tôi giữ nguyên điểm đã nộp và số liệu tự động gốc, công bố riêng các khác biệt phát hiện khi đọc lại bằng chứng; chưa commit hoặc push.

## Dữ liệu và pipeline

### Corpus và quyền sử dụng

Tôi chọn báo cáo nghiên cứu sinh viên năm 2024 của Trường Đại học Kinh tế Quốc dân về các nhân tố ảnh hưởng tới hoạt động công bố báo cáo phát triển bền vững tại doanh nghiệp niêm yết Việt Nam. PDF có 153 trang vật lý. Tôi chọn 84 trang thuộc Chương 1–5, từ trang PDF 18 đến 101; không đưa phần bìa, mục lục, kết luận chung, tài liệu tham khảo và phụ lục vào corpus.

| Section | Trang PDF | Số trang |
|---|---|---:|
| `chuong_1` | 18–36 | 19 |
| `chuong_2` | 37–51 | 15 |
| `chuong_3` | 52–73 | 22 |
| `chuong_4` | 74–93 | 20 |
| `chuong_5` | 94–101 | 8 |
| Tổng | 18–101 | 84 |

Tôi dùng số trang PDF vật lý bắt đầu từ 1 xuyên suốt manifest, benchmark và metadata. Ví dụ, trang PDF 64 tương ứng trang in 53. Sau chuẩn hóa, corpus có 153.080 ký tự và không có trang hoàn toàn rỗng. Số trang và ký tự được ghi trong [manifest](../../data/manifest.json).

Tài liệu được lấy từ Studocu; quyền sử dụng và tái phân phối vẫn được ghi là chưa xác minh. Tôi đã cho phép thao tác gửi nội dung tới OpenAI API để chạy thí nghiệm; xác nhận thao tác này không thay thế bằng chứng về giấy phép tài liệu. Tôi giữ PDF, extracted text, cache và trace chứa nội dung ở local, không commit. Cách cung cấp lại PDF và kiểm tra checksum được mô tả trong [hướng dẫn dữ liệu](../../data/README.md).

### Chuẩn hóa, metadata và khả năng truy vết

Tôi dùng pypdf để đọc riêng từng trang, chuẩn hóa Unicode NFC và khoảng trắng, đồng thời loại các dòng watermark/footer lặp lại chứa thông tin người tải. Tôi giữ các dòng và khoảng ngắt mà công cụ trích xuất cung cấp; chưa coi đây là bằng chứng bố cục bảng hoặc ranh giới đoạn ngữ nghĩa đã được bảo toàn hoàn toàn.

Mỗi chunk có `document_id`, `source`, `page` và `section`. Tôi lấy `section` từ ánh xạ chương trong manifest để truy vết và chuẩn bị filter cho C. Tôi lưu thêm `start_char`, `end_char`, `char_count` và chỉ số chunk để xác định vị trí trong văn bản trang. ID chunk ổn định khi nạp lại cùng corpus và cấu hình (`_c{idx:03d}` cho A, `_b{idx:03d}` cho B/C).

Tôi đã phát hiện nội dung không nhất quán giữa phương trình hồi quy và phần bàn luận của PDF về hệ số của một số biến. Tôi không sửa số liệu của nguồn; câu hỏi liên quan được giới hạn vào phần được chỉ rõ. Tôi đã bổ sung đối chiếu trực quan có Codex hỗ trợ trên 20 trang liên quan, gồm bảng giả thuyết trang 91 và bảng hồi quy trang 88. Nhật ký ghi rõ người/công cụ kiểm tra và phạm vi tại [source_visual_review.md](../../results/audit/source_visual_review.md); không coi đó là tự tôi đã xem toàn bộ PDF.

### Môi trường và lưu trữ

| Thành phần | Cấu hình đã kiểm tra |
|---|---|
| Python | 3.12.10 |
| PDF parser | pypdf 6.21.4 |
| Embedding | OpenAI `text-embedding-3-small`, 1536 chiều |
| OpenAI SDK | 3.51.0 |
| PostgreSQL | 16.16 |
| pgvector | 0.8.7 |
| Driver | psycopg 3.3.8 |
| Cấu hình môi trường | python-dotenv 1.2.4, `starter/.env` |
| Retrieval | Exact cosine search, top-3; cùng khoảng cách thì xếp theo chunk ID |

Tôi dùng cùng model cho chunk và query, không thêm đáp án hay gold page vào query embedding. Pipeline kiểm tra số lượng và số chiều vector; cache local phân biệt theo model, dimensions và hash nội dung. Tên model được ghi nhận từ cấu hình; tôi không có revision bất biến riêng của model API để báo cáo.

Tôi lưu dữ liệu trong pgvector, thực hiện upsert theo strategy và chunk ID, đồng thời loại chunk lỗi thời của tài liệu được cập nhật. Bảng `index_metadata` ghi model, dimensions, checksum PDF/corpus, cấu hình chunk, số chunk và ingest run ID. Trước eval, tôi kiểm tra index tương thích với cấu hình hiện tại.

## Cấu hình và benchmark

### Ba cấu hình triển khai

| Strategy | Chunking | Retrieval | Trạng thái |
|---|---|---|---|
| A | Fixed-size 500 ký tự, overlap 50, không vượt trang | Cosine toàn corpus, không filter | Đã chạy dev (375 chunks) |
| B | Theo cấu trúc đoạn và heading (`by_paragraph`, `max_size=800`), chia câu nếu đoạn dài | Cosine toàn corpus, không filter | Đã chạy dev (256 chunks) |
| C | Tái sử dụng 100% chunk và index của B | Cosine có filter `section` khi câu hỏi yêu cầu; không filter thì giống B | Đã chạy dev (256 chunks, dùng index B) |

Tôi giữ A làm baseline kích thước cố định. A–B đồng thời thay đổi ranh giới chunk, kích thước mục tiêu (500 sang 800) và overlap (50 sang 0), nên tôi so sánh toàn bộ chiến lược chunking, không tách riêng hiệu quả của ranh giới đoạn. B hiện dùng quy tắc trên khối văn bản và dấu câu, chưa phải bộ nhận diện heading/bảng chuyên biệt. B có 256 chunk, dài 52–943 ký tự, trung bình 597,7; có 2 chunk vượt 800 do quy tắc giữ đơn vị dài hoặc gộp phần cuối ngắn. Vì vậy `max_size=800` là ngưỡng mục tiêu trong triển khai hiện tại. So sánh B–C chỉ thay filter vì dùng chung index B.

### Bộ câu hỏi và quy tắc đánh giá

Tôi xây [20 câu hỏi](../../benchmark/questions.jsonl), chia 15 dev và 5 test trước retrieval. Mỗi chương có 4 câu; toàn bộ benchmark có 4 câu filter, gồm 2 câu dev và 2 câu test. Filter sử dụng `section` theo phạm vi đã nêu trong câu hỏi. Tôi đã sửa lỗi gold của `test_02`, bổ sung ngữ cảnh cho `dev_06`, `dev_07` trước thí nghiệm và khóa lại checksum.

Tôi kiểm tra evidence xuất hiện trên trang nguồn sau chuẩn hóa. Một hit tự động cần đúng document ID, đúng trang gold hoặc alternative gold và chứa đủ đoạn evidence trong một chunk. Tôi báo Hit@1 và Evidence Hit@3 riêng; việc nhiều chunk hợp lại đủ bằng chứng không thay thế điều kiện hit đơn chunk. Bằng chứng tương đương ngoài phép so khớp tự động cần được kiểm tra và ghi nhận riêng.

Tôi chọn cấu hình theo Evidence Hit@3 trên dev, sau đó Hit@1, rồi chi phí/thời gian ingest. Tôi đã chọn trước 10 vị trí nguồn để chấm coherence, 2 vị trí mỗi chương. Quy tắc và anchors được lưu trong [benchmark README](../../benchmark/README.md).

Checksum benchmark hiện hành:

```text
ed0be0f44f105e00ef83b1150525226f4073621b03beed783e94a56b63305796
```

Tôi đã đọc test để xây dựng và sửa gold, đồng thời trong giai đoạn phát triển B đã chạy kiểm tra cơ học xem evidence của cả 20 câu có nằm trọn trong chunk nào hay không. Vì vậy, tôi công bố minh bạch rằng tập test không hoàn toàn là "hộp đen chưa từng thấy văn bản"; tuy nhiên, tôi cam kết không dùng kết quả retrieval test để điều chỉnh siêu tham số hay đảo ngược quyết định chọn chiến lược. Toàn bộ quyết định lựa chọn C đã được đóng băng tại [results/dev_selection.md](../../results/dev_selection.md) và [results/pre_test_snapshot.json](../../results/pre_test_snapshot.json) trước khi thực hiện lượt truy xuất test đầu tiên.

## Kết quả

### Retrieval tự động trên dev và test (giữ nguyên các lượt chạy gốc)

| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Chunk count | Thời gian eval | API calls / Prompt tokens |
|---|---|---|---|---:|---|---|
| A | dev | 7/15 (46,7%) | 11/15 (73,3%) | 375 | 5,18 s | 15 calls / 908 tokens |
| A | test | 3/5 (60,0%) | 3/5 (60,0%) | 375 | 3,44 s | 5 calls / 324 tokens |
| B | dev | 9/15 (60,0%) | 12/15 (80,0%) | 256 | 0,57 s | 0 calls / 0 tokens (cache) |
| B | test | 3/5 (60,0%) | 4/5 (80,0%) | 256 | 0,19 s | 0 calls / 0 tokens (cache) |
| C | dev | 9/15 (60,0%) | 12/15 (80,0%) | 256 | 0,56 s | 0 calls / 0 tokens (cache) |
| C | test | **4/5 (80,0%)** | **4/5 (80,0%)** | 256 | 0,17 s | 0 calls / 0 tokens (cache) |

Toàn bộ số liệu trên được tổng hợp tại [results/metrics.csv](../../results/metrics.csv).

Tôi tính lại các cờ hit từ trace thực tế của 60 lượt đánh giá (20 câu × 3 chiến lược):
- Trên tập dev (15 câu), B và C cải thiện Hit@1 thêm 2 câu (+13,3 điểm phần trăm) và Evidence Hit@3 thêm 1 câu (+6,7 điểm phần trăm) so với A.
- Trên tập test (5 câu), B tăng Evidence Hit@3 từ 3/5 (60,0%) lên 4/5 (80,0%) nhờ giải quyết lỗi phân mảnh bảng biểu trên `test_02`.
- Chiến lược C trên tập test đạt **Hit@1 = 4/5 (80,0%)** và **Evidence Hit@3 = 4/5 (80,0%)**. Nhờ bộ lọc `section = chuong_4`, C loại bỏ chunk nhiễu thuộc Chương 3 ở câu `test_02`, trực tiếp nâng vị trí chunk chứa bằng chứng từ hạng 2 lên hạng 1.

### Ingest, cache và kiểm tra không nhân đôi

| Thuộc tính | Chiến lược A (Lượt 1) | Chiến lược A (Lượt 2) | Chiến lược B (Lượt 1) | Chiến lược B (Lượt 2) |
|---|---:|---:|---:|---:|
| Số chunk trong DB sau lượt chạy | 375 | 375 | 256 | 256 |
| Đọc corpus và chunking | 3,38 s | 3,25 s | 3,66 s | 3,75 s |
| Embedding / cache | 6,07 s | 0,31 s | 2,98 s | 0,29 s |
| Ghi cơ sở dữ liệu pgvector | 1,09 s | 1,10 s | 0,87 s | 0,82 s |
| Tổng thời gian ingest pipeline đo | 10,55 s | 4,66 s | 7,50 s | 4,86 s |
| API calls thành công ghi nhận | 3 | 0 | 2 | 0 |
| Prompt tokens tiêu tốn | 81.855 | 0 | 74.116 | 0 |
| Cache hits / misses | 0 / 375 | 375 / 0 | 3 / 253 | 256 / 0 |

Tôi đã nạp lại cùng corpus cho cả A và B; số lượng chunk trong cơ sở dữ liệu giữ nguyên ở mức 375 (với A) và 256 (với B), khẳng định cơ chế upsert không bị nhân đôi dữ liệu. Lượt 2 của cả hai chiến lược đạt 100% cache hit, tiêu tốn 0 token và không phát sinh API call mới.

So với A, B có ít hơn 119 chunk (giảm 31,7% số vector), ghi nhận ít hơn 7.739 prompt tokens trong lượt ingest đầu (9,5%). B có 3 cache hits từ dữ liệu trước đó nên đây chưa phải phép so sánh chi phí hai lượt hoàn toàn không cache. Tại thời điểm lưu run tôi chưa quy đổi tiền; ước tính bổ sung nằm ở mục chi phí. Tôi chưa đo dung lượng database; giảm số vector không đồng nghĩa đã đo mức giảm dung lượng thực tế trên đĩa. Chiến lược C dùng chung index của B nên không tốn thêm tài nguyên ingest.

Trong các lượt eval test của B và C, 5 vector truy vấn được tái sử dụng từ cache SQLite đã nạp trong lượt eval test A, nên B và C tiêu tốn 0 prompt token và hoàn tất trong ~0,17–0,19 s. Tôi không dùng chênh lệch thời gian giữa lượt lạnh (A: 3,44 s) và lượt nóng (B/C: ~0,18 s) để kết luận thuật toán retrieval của C/B nhanh hơn A.

### Chi tiết từng câu dev trên cả 3 chiến lược

| ID | Gold page | Filter | Chiến lược A (Hit@1 / Hit@3) | Chiến lược B (Hit@1 / Hit@3) | Chiến lược C (Hit@1 / Hit@3) | Phân tích đối chiếu trace |
|---|---:|---|:---:|:---:|:---:|---|
| dev_01 | 64 | `chuong_3` | Có / Có | Có / Có | Có / Có | B trả về trang 76 (`chuong_4`) ở hạng 3; C loại bỏ trang 76 và đưa trang 53 (`chuong_3`) vào top-3, đảm bảo 100% tuân thủ filter |
| dev_02 | 18 | Không | Không / Có | Không / Có | Không / Có | Cả 3 chiến lược đều đạt Hit ở hạng 2 |
| dev_03 | 31 | Không | Không / Không | Không / Không | Không / Không | A trả trang 34, 57, 48; B/C trả trang 66, 34, 57. Chưa tìm được evidence gold trong top-3; chưa xác định nguyên nhân ngữ nghĩa |
| dev_04 | 35 | Không | Có / Có | Có / Có | Có / Có | Hit ở hạng 1 trên cả 3 chiến lược |
| dev_05 | 40 | Không | Có / Có | Có / Có | Có / Có | Hit ở hạng 1 trên cả 3 chiến lược |
| dev_06 | 45 | Không | Có / Có | Có / Có | Có / Có | Hit ở hạng 1 trên cả 3 chiến lược |
| dev_07 | 47 | `chuong_2` | Có / Có | Có / Có | Có / Có | Cả B và C đều đạt Hit ở hạng 1; top-3 của B ngẫu nhiên đều thuộc `chuong_2` nên kết quả trùng C |
| dev_08 | 52 | Không | Có / Có | Có / Có | Có / Có | Hit ở hạng 1 trên cả 3 chiến lược |
| dev_09 | 53 | Không | Không / Không | **Không / Có** | **Không / Có** | **B và C giải quyết triệt để lỗi của A**: đoạn bằng chứng về Cronbach’s Alpha được giữ nguyên vẹn trong chunk `p053_b000` và đạt Hit ở hạng 3 |
| dev_10 | 75 | Không | Không / Có | **Có / Có** | **Có / Có** | B và C cải thiện thứ hạng, đẩy hit từ hạng 2 lên hạng 1 (Hit@1) |
| dev_11 | 89 | Không | Không / Có | Không / Không | Không / Không | A hit ở hạng 2; top-3 B/C thuộc trang 88, 54, 87 và không chứa evidence gold. Trace top-3 chưa chứng minh chính xác hạng 5 hoặc nguyên nhân do chunk dài |
| dev_12 | 89 | Không | Có / Có | Có / Có | Có / Có | Hit ở hạng 1 trên cả 3 chiến lược |
| dev_13 | 94 | Không | Không / Không | Không / Không | Không / Không | A trả trang 71, 55, 54; B/C trả trang 54, 94, 71. B/C đã tới trang gold ở hạng 2 nhưng chunk chưa đủ evidence theo phép chấm |
| dev_14 | 98 | Không | Không / Không | **Không / Có** | **Không / Có** | **B và C giải quyết lỗi xếp hạng của A**: chunk chứa quy định Na Uy 40% nữ `p098_b001` được xếp trong top-3 (hạng 3) |
| dev_15 | 100 | Không | Không / Có | **Có / Có** | **Có / Có** | B và C cải thiện thứ hạng, đẩy hit từ hạng 2 lên hạng 1 (Hit@1) |

Đối chiếu trực tiếp xác nhận: Đối với 13 câu hỏi không có filter trên tập dev, Chiến lược B và Chiến lược C trả về danh sách chunk ID, điểm số tương đồng cosine và thứ tự xếp hạng giống nhau 100%.

### Chi tiết 5 câu test trên cả 3 chiến lược

| ID | Gold page | Filter | Chiến lược A (Hit@1 / Hit@3) | Chiến lược B (Hit@1 / Hit@3) | Chiến lược C (Hit@1 / Hit@3) | Phân tích đối chiếu trace test |
|---|---:|---|:---:|:---:|:---:|---|
| `test_01` | 26 | Không | **Có / Có** | **Có / Có** | **Có / Có** | Cả 3 chiến lược đều đạt Hit ngay tại Rank 1 (`p026_c001` ở A, `p026_b001` ở B/C) với điểm cosine tương đồng cao (~0,60–0,63). |
| `test_02` | 91 | `chuong_4` | Không / Không | Không / **Có** | **Có / Có** | A không đạt hit đơn chunk vì evidence bảng 582 ký tự bị phân mảnh; top-3 vẫn có hai chunk trang 91 nên cần xem xét riêng khả năng hợp bằng chứng khi chấm grounding. B chứa đủ evidence ở hạng 2 (`p091_b000`); C lọc `chuong_4` và đưa chunk này lên hạng 1. |
| `test_03` | 42 | Không | **Có / Có** | **Có / Có** | **Có / Có** | Câu hỏi về Hướng dẫn SEC tháng 2/2010; đáp án là số 33-9106. Cả ba đạt hit ở hạng 1 (`p042_c001` ở A, `p042_b000` ở B/C). |
| `test_04` | 68 | Không | Không / Không | Không / Không | Không / Không | Đây là cờ tự động theo gold quote gốc. Đọc lại thấy A top-1 `p068_c001` đã có đúng hai ngày khảo sát ở đoạn tương đương; đây là false negative của phép so khớp quote. B/C top-3 không có hai mốc ngày. Tôi công bố đối chiếu riêng bên dưới. |
| `test_05` | 101 | `chuong_5` | **Có / Có** | **Có / Có** | **Có / Có** | Cả 3 chiến lược đều đạt Hit tại Rank 1 (`p101_c000` ở A, `p101_b000` ở B/C). Chiến lược C vượt trội về độ sạch khi lọc sạch toàn bộ top-3 về Chương 5, loại bỏ các chunk Chương 3 lọt vào top-3 của A và B. |

### Đối chiếu bổ sung bằng chứng tương đương sau test

Tôi phát hiện một false negative ở A/test_04 khi đọc lại toàn văn top-1 và ảnh trang PDF 68. Gold quote chọn đoạn mô tả khảo sát trực tiếp; chunk `ptbv_report_p068_c001` chứa đoạn khảo sát qua email, cũng ghi đúng 06/04/2022–06/10/2023. Câu hỏi hỏi thời gian khảo sát nói chung, nên đoạn này đủ hỗ trợ đáp án trên đúng nguồn/trang.

Tôi giữ nguyên benchmark, trace, summary và metric tự động, đồng thời công bố [biên bản đối chiếu](../../results/evidence_adjudication.json). Đây là nhận xét có Codex hỗ trợ sau test, không phải một lượt chạy hoặc nhãn đã khóa trước test.

| Cấu hình | Hit@1 tự động | Hit@3 tự động | Hit@1 sau đối chiếu tương đương | Hit@3 sau đối chiếu tương đương |
|---|---|---|---|---|
| A | 3/5 | 3/5 | 4/5 | 4/5 |
| B | 3/5 | 4/5 | 3/5 | 4/5 |
| C | 4/5 | 4/5 | 4/5 | 4/5 |

Sau đối chiếu này, tôi không kết luận C hơn A về retrieval test: hai cấu hình cùng 4/5 ở cả hai chỉ số. C vẫn hơn B một câu Hit@1 nhờ filter ở test_02. Lựa chọn C trước test được giữ nguyên; test nhỏ và phép chấm quote nghiêm ngặt đều là giới hạn cần nêu.

### Coherence, metadata và grounding

Tôi đã nộp điểm qua trang review: CSV/JSON khớp 20 ô coherence (A và B/C dùng chung cho 10 anchors) và 15 ô grounding. Điểm C được ánh xạ từ ô B/C sau khi xác nhận cùng 10 chunk ID, không phải một lượt chấm độc lập. Tôi giữ nguyên file điểm gốc và human_score; các nhận xét bổ sung do Codex đọc toàn văn được lưu ở cột `assisted_review_notes`, không gán thành lời ghi chú do tôi tự nhập.

| Strategy | Coherence tôi nộp /2 (n=10) | Grounding tôi nộp /2 (n=5) | Grounding mức 0 / 1 / 2 | Metadata khớp nguồn (đối chiếu có hỗ trợ) | Câu có toàn bộ top-3 đúng filter |
|---|---:|---:|---|---|---|
| A | 1,00 | 1,60 | 0 / 2 / 3 | 15/15 | 0/2 |
| B | 1,90 | 1,80 | 0 / 1 / 4 | 15/15 | 0/2 |
| C | 1,90 | 1,80 | 0 / 1 / 4 | 15/15 | 2/2 |

Coherence A gồm 10 điểm 1; B/C có 9 điểm 2 và 1 điểm 1 (anchor 8, trang 89). Grounding A có test_02 và test_04 điểm 1, các câu khác điểm 2; B/C có test_04 điểm 1, các câu khác điểm 2. Các điểm này trùng gợi ý AI ban đầu, nên tôi công bố nguy cơ dẫn dắt và không coi đó là chấm mù độc lập.

Tôi bổ sung các trường hợp mà nhận xét đọc lại của Codex khác điểm đã nộp:

- **Coherence B/C, anchor 5, trang 53:** tôi nộp 2; chunk giữ đủ anchor và Alpha 0.6 nhưng phần EFA cuối dừng ở `(<0.`. Nhận xét có hỗ trợ đánh giá thận trọng là 1, không thể khẳng định B luôn giữ trọn câu.
- **Grounding A/test_02:** tôi nộp 1; hai chunk hạng 1 và 3 cùng trang 91 có đủ H5 và H1 bị bác bỏ. Hợp top-3 đủ đáp án nên nhận xét có hỗ trợ là 2, dù không đạt Evidence Hit@3 đơn chunk.
- **Grounding A/test_04:** tôi nộp 1; top-1 có đủ hai ngày nên nhận xét có hỗ trợ là 2.
- **Grounding B/C/test_04:** tôi nộp 1; top-3 chỉ có ngữ cảnh quy trình/địa điểm mà thiếu khoảng thời gian, nhận xét có hỗ trợ là 0. Đúng trang không tự chứng minh có một phần đáp án.

Tôi không sửa ngầm điểm đã nộp để che các khác biệt. Nếu xem các nhận xét hỗ trợ như một bộ nhãn bổ sung, coherence A/B/C là 1,00/1,80/1,80 và grounding là 2,00/1,60/1,60; đây là bộ nhãn của Codex, tách khỏi bộ điểm của tôi. Các kết quả cho thấy thang đánh giá chủ quan cần có lý do và provenance, không suy từ hit/page match.

Codex đã đối chiếu riêng đủ 45 metadata records với text đọc mới từ PDF: source, document ID, page, section và slice start_char:end_char đều khớp. Ảnh render bao phủ các trang được trả về trên test và các bảng liên quan. `assisted_review_status=reviewed` ghi đúng phương pháp; không tự điền `human_metadata_correct` hoặc giả xác nhận cá nhân của tôi. Tôi công bố đây là audit có hỗ trợ, không phải 45 xác nhận thủ công độc lập do tôi tự nhập.

Tỷ lệ đúng phạm vi trên hai câu test có filter: cấp hit A 3/6, B 4/6, C 6/6; cấp câu hỏi A 0/2, B 0/2, C 2/2. A/B không áp dụng filter. Metadata đúng giúp truy vết nhưng không chứng minh nội dung chunk đủ trả lời; B/C/test_04 là ví dụ giới hạn.

Minh chứng:

- [Điểm tôi đã nộp](../../results/audit/human_scores_submitted.json) và [tổng hợp/provenance](../../results/audit/human_audit_summary.json).
- [Coherence và nhận xét từng chunk](../../results/audit/coherence_audit.csv).
- [Grounding và nhận xét từng truy vấn](../../results/audit/grounding_audit.csv).
- [Metadata và phương pháp đối chiếu](../../results/audit/metadata_audit.csv).
- [Đối chiếu trực quan PDF](../../results/audit/source_visual_review.md).
- [Tổng kết audit](../../results/audit/audit_summary.md).

### Ước tính chi phí API từ usage đã lưu

Tôi dùng mức giá công khai 0,02 USD/1 triệu input tokens của [text-embedding-3-small](https://developers.openai.com/api/docs/models/text-embedding-3-small), kiểm tra ngày 14/11/2026. Với 10 summary đã lưu, tổng prompt tokens là 157.203 và chi phí tính theo usage là **0,00314406 USD**: ingest A 0,00163710 USD, ingest B 0,00148232 USD, eval A/dev 0,00001816 USD, eval A/test 0,00000648 USD; các run còn lại dùng cache không có token API mới.

Đây là ước tính theo giá công khai cho các lượt đã ghi nhận, không phải hóa đơn hoặc toàn bộ chi tiêu tài khoản; chưa gồm thuế, credits, điều chỉnh billing hay các lượt không được log. B/C dùng chung index nên không tính ingest hai lần. [Bảng chi phí](../../results/cost_estimate.json) giữ công thức, nguồn giá và từng run; các summary gốc ghi “chưa xác định” được giữ như lịch sử tại thời điểm chạy.

### Artifact và khả năng tái lập

| Lượt chạy | Run ID | Summary | Trace |
|---|---|---|---|
| Ingest A lượt 1 | `run_A_ingest_20261114_105741` | [Summary A1](../../results/runs/run_A_ingest_20261114_105741_summary.json) | — |
| Ingest A lượt 2 | `run_A_ingest_20261114_105804` | [Summary A2](../../results/runs/run_A_ingest_20261114_105804_summary.json) | — |
| Eval A dev | `run_A_eval_20261114_105820` | [Summary Eval A Dev](../../results/runs/run_A_eval_20261114_105820_summary.json) | Local trace A dev |
| Eval A test | `run_A_eval_20261114_113119` | [Summary Eval A Test](../../results/runs/run_A_eval_20261114_113119_summary.json) | Local trace A test |
| Ingest B lượt 1 | `run_B_ingest_20261114_111841` | [Summary B1](../../results/runs/run_B_ingest_20261114_111841_summary.json) | — |
| Ingest B lượt 2 | `run_B_ingest_20261114_111859` | [Summary B2](../../results/runs/run_B_ingest_20261114_111859_summary.json) | — |
| Eval B dev | `run_B_eval_20261114_111917` | [Summary Eval B Dev](../../results/runs/run_B_eval_20261114_111917_summary.json) | Local trace B dev |
| Eval B test | `run_B_eval_20261114_113129` | [Summary Eval B Test](../../results/runs/run_B_eval_20261114_113129_summary.json) | Local trace B test |
| Eval C dev | `run_C_eval_20261114_111926` | [Summary Eval C Dev](../../results/runs/run_C_eval_20261114_111926_summary.json) | Local trace C dev |
| Eval C test | `run_C_eval_20261114_113135` | [Summary Eval C Test](../../results/runs/run_C_eval_20261114_113135_summary.json) | Local trace C test |

Toàn bộ thông số cấu hình và checksum trước test được lưu tại [results/pre_test_snapshot.json](../../results/pre_test_snapshot.json).
Bảng đối chiếu chỉ số tổng hợp được lưu tại [results/metrics.csv](../../results/metrics.csv).
Bản chỉ mục 180 hits không chứa text nguồn nằm tại [retrieval_trace_index.csv](../../results/retrieval_trace_index.csv).
Bảng nhật ký thí nghiệm lưu tại [artifacts/experiment_log.csv](../../artifacts/experiment_log.csv).
Hướng dẫn và bảng chấm audit nằm tại [results/audit/audit_summary.md](../../results/audit/audit_summary.md).
Trang web chấm điểm trực quan (local): [results/audit/local_text/review.html](../../results/audit/local_text/review.html).
Script kiểm tra và tổng hợp điểm audit: `scripts/aggregate_human_audit.py`.

Các lệnh PowerShell dùng để tái lập toàn bộ quy trình:

```powershell
# 1. Trích xuất corpus và kiểm tra verifier
.\starter\.venv\Scripts\python.exe -X utf8 -m starter.src.ingestion
.\starter\.venv\Scripts\python.exe -X utf8 scripts/verify_corpus_benchmark.py

# 2. Ingest và Eval Baseline A (Dev và Test)
.\starter\.venv\Scripts\python.exe -X utf8 -m starter.src.run --strategy A --action ingest --split dev --confirm-api
.\starter\.venv\Scripts\python.exe -X utf8 -m starter.src.run --strategy A --action eval --split dev --confirm-api
.\starter\.venv\Scripts\python.exe -X utf8 -m starter.src.run --strategy A --action eval --split test --final-test --confirm-api

# 3. Ingest và Eval Chiến lược B (Dev và Test)
.\starter\.venv\Scripts\python.exe -X utf8 -m starter.src.run --strategy B --action ingest --split dev --confirm-api
# Chạy lại để kiểm tra không nhân đôi dữ liệu và 100% cache:
.\starter\.venv\Scripts\python.exe -X utf8 -m starter.src.run --strategy B --action ingest --split dev --confirm-api
.\starter\.venv\Scripts\python.exe -X utf8 -m starter.src.run --strategy B --action eval --split dev --confirm-api
.\starter\.venv\Scripts\python.exe -X utf8 -m starter.src.run --strategy B --action eval --split test --final-test --confirm-api

# 4. Eval Chiến lược C (tự động dùng index B)
.\starter\.venv\Scripts\python.exe -X utf8 -m starter.src.run --strategy C --action eval --split dev --confirm-api
.\starter\.venv\Scripts\python.exe -X utf8 -m starter.src.run --strategy C --action eval --split test --final-test --confirm-api
```

## Phân tích và kết luận

### So sánh tác động của các chiến lược dữ liệu trên cả Dev và Test

1. **So sánh A–B (Tác động của kỹ thuật chunking theo đoạn):**
   - *Khắc phục phân mảnh bằng chứng*: Trên tập dev, Chiến lược B khắc phục thành công lỗi phân mảnh ở `dev_09` (trang 53). Trên tập test, B giữ trọn evidence của `test_02` (trang 91): Bảng tóm tắt kết quả kiểm định các giả thuyết nghiên cứu dài 582 ký tự bị Baseline A xé đôi qua 2 chunk 500 ký tự (`p091_c000` và `p091_c001`), khiến cả 2 chunk đều không đủ bằng chứng. Chiến lược B bảo toàn toàn bộ bảng biểu trong một chunk duy nhất `p091_b000`, giúp Evidence Hit@3 trên test tăng từ 60,0% lên 80,0%.
   - *Hiệu quả tài nguyên*: B giảm 31,7% số lượng vector trong cơ sở dữ liệu và giảm 9,5% token embedding nạp ban đầu.
   - *Đánh đổi*: Ở `dev_11`, B/C không có hit trong top-3 trong khi A có. Tôi ghi đây là thay đổi thứ hạng; chưa có phép thử riêng chứng minh nguyên nhân do chiều dài hoặc mật độ từ khóa.

2. **So sánh B–C (Tác động của metadata filtering):**
   - *Nâng cao độ chính xác top-1*: Trên tập dev, Chiến lược C đã loại bỏ chunk Chương 4 lọt vào top-3 của câu `dev_01`. Đáng chú ý nhất, trên tập test ở câu `test_02`, Chiến lược B bị chunk `p053_b001` (thuộc Chương 3) chiếm mất vị trí số 1 do độ tương đồng từ khóa. Khi Chiến lược C áp dụng bộ lọc `section = chuong_4`, chunk Chương 3 này bị loại bỏ, **đẩy trực tiếp chunk chứa bằng chứng `p091_b000` lên vị trí Rank 1**, giúp Hit@1 trên test của C đạt **80,0% (4/5 câu)** so với 60,0% của B.
   - *Độ sạch của ngữ cảnh*: Trên các câu hỏi có yêu cầu phạm vi nghiệp vụ cụ thể, Chiến lược C đạt 100% tỷ lệ tuân thủ bộ lọc, ngăn chặn hoàn toàn việc đưa ngữ cảnh ngoài chương vào prompt của các hệ thống RAG phía sau.

### Quyết định lựa chọn cấu hình và Giữ vững cam kết

Trước khi chạy test, tôi đã chọn C theo quyết định tại [results/dev_selection.md](../../results/dev_selection.md). Trên test, C đạt Hit@1 4/5, cao hơn B một câu; Evidence Hit@3 4/5 bằng B. Tôi giữ quyết định trước test, không xem kết quả này là bằng chứng C tốt nhất tổng quát hoặc test hoàn toàn độc lập với quá trình phát triển.

Tôi giữ nguyên cấu hình retrieval và benchmark đã khóa; phần đối chiếu bằng chứng tương đương sau test được lưu riêng, không ghi đè các metric gốc hoặc chọn lại cấu hình theo test.

### Các giới hạn cần công bố minh bạch

1. **Kích thước tập test nhỏ (N=5)**: Do tập test chỉ gồm 5 câu hỏi (mỗi câu đại diện cho 20 điểm phần trăm), độ biến động thống kê là rất lớn. Việc C tăng từ 60% lên 80% thực chất là sự cải thiện trên đúng 1 câu hỏi (`test_02`). Kết quả này chỉ mang tính chất minh họa thực nghiệm trên một tài liệu cụ thể, hoàn toàn chưa đủ cơ sở để khẳng định Chiến lược C vượt trội tổng quát trên các miền dữ liệu khác.
2. **Nguy cơ thiên lệch do kiểm tra containment**: Trong quá trình phát triển thuật toán phân đoạn cho Chiến lược B, công cụ đã kiểm tra sự hiện diện đầy đủ của evidence trên cả 20 câu benchmark. Do đó, tôi không tuyên bố tập test là hoàn toàn độc lập và vô hình đối với người thiết kế thuật toán chunking.
3. **Giới hạn đo lường tài nguyên**: Các số liệu về thời gian và tokens phản ánh lượt chạy thực tế trên môi trường máy cá nhân và API OpenAI tại thời điểm đo. Tôi không suy dung lượng đĩa từ số chunk. Chi phí tiền chỉ là ước tính từ usage và giá công khai đã dẫn nguồn, không phải số tiền hóa đơn được xác nhận.

### Sử dụng công cụ AI

Tôi sử dụng Antigravity để hỗ trợ viết pipeline và chuẩn bị audit, Codex để hỗ trợ đối chiếu summary/trace và sửa diễn giải báo cáo. Việc tính lại metric bằng công cụ không có nghĩa tôi đã tự chấm các nhãn chất lượng. Tôi đã gửi điểm coherence/grounding qua trang review. Phần nhận xét, kiểm tra metadata và ảnh PDF được Codex hỗ trợ hoàn thiện, ghi rõ người/công cụ và các khác biệt với điểm của tôi; không giả thành một lượt chấm người độc lập.

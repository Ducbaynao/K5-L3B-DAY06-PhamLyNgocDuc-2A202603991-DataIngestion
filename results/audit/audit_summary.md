# Tổng kết audit trước commit

Tôi đã nộp điểm coherence/grounding. Nhận xét, đối chiếu nguồn, metadata và ảnh PDF được Codex hỗ trợ hoàn thiện; giữ nguyên điểm tôi gửi và công bố riêng các khác biệt.

## Điểm tôi nộp

| Cấu hình | Coherence /2 (10 anchors) | Grounding /2 (5 câu) | Grounding 0 / 1 / 2 |
|---|---:|---:|---|
| A | 1,00 | 1,60 | 0 / 2 / 3 |
| B | 1,90 | 1,80 | 0 / 1 / 4 |
| C | 1,90 | 1,80 | 0 / 1 / 4 |

Điểm C coherence dùng cùng ô B/C, sau khi xác nhận cùng 10 chunk. File gốc không có nhận xét riêng; human_notes giữ nguyên, nhận xét do Codex nằm trong assisted_review_notes. Điểm người dùng trùng gợi ý AI ban đầu nên có nguy cơ dẫn dắt, không phải chấm mù độc lập.

## Đối chiếu có hỗ trợ và khác biệt cần công bố

- Đã đọc toàn bộ 20 chunk A/B cho coherence; C dùng B. Anchor 5 của B/C vẫn cắt số EFA ở cuối; điểm nộp 2, nhận xét Codex 1.
- Đã đọc toàn bộ top-3 của 15 query-strategy test. A/test_02 hợp hai chunk đủ H1/H5 nên nhận xét Codex là 2, khác điểm nộp 1.
- A/test_04 top-1 có đủ hai ngày khảo sát: nhận xét Codex 2, điểm nộp 1. B/C/test_04 thiếu khoảng thời gian: nhận xét Codex 0, điểm nộp 1.
- Bộ nhãn hỗ trợ riêng có coherence A/B/C 1,00/1,80/1,80; grounding 2,00/1,60/1,60. Không dùng bộ này ghi đè điểm tôi nộp.
- Đã đối chiếu 45 metadata records với PDF đọc mới, đúng source/document/page/section/offset text. Kết quả: 15/15 mỗi cấu hình; reviewer Codex, không giả điền human_metadata_correct.
- Filter cấp hit A/B/C 3/6, 4/6, 6/6; cấp câu 0/2, 0/2, 2/2. A/B không áp dụng filter.
- Đã xem ảnh 20 trang PDF liên quan, gồm bảng 91 và hồi quy 88–93; ghi chi tiết trong nhật ký visual review.

## Minh chứng

- [Điểm export gốc](human_scores_submitted.json), [tổng hợp và provenance](human_audit_summary.json).
- [Coherence](coherence_audit.csv), [grounding](grounding_audit.csv), [metadata](metadata_audit.csv).
- [Nhật ký xem ảnh PDF](source_visual_review.md).
- [Đối chiếu evidence tương đương](../evidence_adjudication.json).
- [Trang review local](local_text/review.html) — không commit vì chứa nội dung nguồn.

## Phạm vi hoàn tất

Điểm đã nộp, nhận xét có hỗ trợ và đối chiếu nguồn đã được ghi đầy đủ trước commit. Đây là audit của tác giả có hỗ trợ AI, không tuyên bố mọi bản ghi đã được người dùng chấm lại độc lập. Các bất đồng được giữ làm giới hạn phương pháp, không cần chạy lại pipeline hoặc sửa benchmark để làm đẹp điểm. Nếu tác giả muốn đổi điểm sau khi xem nhận xét, cần lưu lịch sử thay đổi; hiện chưa đổi điểm.

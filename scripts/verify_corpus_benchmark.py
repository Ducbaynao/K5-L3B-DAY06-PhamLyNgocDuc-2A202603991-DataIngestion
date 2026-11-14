"""Comprehensive verification script for Day 06 Corpus, Manifest, and Benchmark."""
import hashlib
import json
from pathlib import Path
import sys

EXPECTED_BENCHMARK_SHA256 = (
    "ed0be0f44f105e00ef83b1150525226f4073621b03beed783e94a56b63305796"
)
PERMITTED_FILTER_FIELDS = {"section"}
PERMITTED_SECTIONS = {
    "chuong_1",
    "chuong_2",
    "chuong_3",
    "chuong_4",
    "chuong_5",
}


def compute_sha256(file_path: Path) -> str:
  hasher = hashlib.sha256()
  with open(file_path, "rb") as f:
    while chunk := f.read(65536):
      hasher.update(chunk)
  return hasher.hexdigest()


def main() -> None:
  print("=== BẮT ĐẦU KIỂM TRA CORPUS, MANIFEST VÀ BENCHMARK ===")

  # 1. Kiểm tra File PDF và Checksum
  pdf_path = Path("data/raw/ptbv_report.pdf")
  assert pdf_path.exists(), f"Không tìm thấy file PDF tại {pdf_path}"
  actual_pdf_sha256 = compute_sha256(pdf_path)
  print(f"[OK] PDF SHA-256 tính toán thực tế: {actual_pdf_sha256}")

  # 2. Kiểm tra Manifest
  manifest_path = Path("data/manifest.json")
  assert (
      manifest_path.exists()
  ), f"Không tìm thấy manifest tại {manifest_path}"
  with open(manifest_path, "r", encoding="utf-8") as f:
    manifest = json.load(f)

  required_manifest_fields = [
      "source_id",
      "title",
      "source_path_or_url",
      "source_origin",
      "accessed_at",
      "license_or_permission",
      "total_physical_pages",
      "sha256",
      "corpus_selection_rules",
      "page_indexing_convention",
      "selected_pages_count",
      "valid_content_pages_count",
      "total_normalized_characters",
      "sections",
      "pages",
  ]
  for field in required_manifest_fields:
    assert field in manifest, f"Thiếu trường bắt buộc trong manifest: {field}"

  assert (
      manifest["sha256"].lower() == actual_pdf_sha256.lower()
  ), "SHA-256 của file PDF không khớp với manifest"
  assert (
      manifest["source_id"] == "ptbv_report"
  ), "source_id không đúng ptbv_report"
  assert manifest["selected_pages_count"] == 84, "Số trang chọn không phải 84"
  assert (
      manifest["valid_content_pages_count"] == 84
  ), "Số trang nội dung hợp lệ không phải 84"
  assert (
      manifest["total_physical_pages"] == 153
  ), "Tổng số trang vật lý không phải 153"

  manifest_page_nums = [p["page"] for p in manifest["pages"]]
  assert len(manifest_page_nums) == len(
      set(manifest_page_nums)
  ), "Có trang bị trùng lặp trong manifest"
  assert len(manifest_page_nums) == 84, "Danh sách trang trong manifest != 84"
  assert min(manifest_page_nums) == 18 and max(manifest_page_nums) == 101, (
      "Dải trang manifest không phải 18-101"
  )
  print(
      f"[OK] Manifest hợp lệ: {manifest['title'][:55]}... (84 trang, SHA-256"
      " khớp)"
  )

  # 3. Kiểm tra Pages trích xuất (data/extracted/pages.jsonl)
  extracted_path = Path("data/extracted/pages.jsonl")
  assert (
      extracted_path.exists()
  ), f"Không tìm thấy extracted pages tại {extracted_path}"
  pages = {}
  with open(extracted_path, "r", encoding="utf-8") as f:
    for line_num, line in enumerate(f, 1):
      line_str = line.strip()
      assert line_str, f"Dòng trống tại dòng {line_num} trong pages.jsonl"
      doc = json.loads(line_str)
      for field in [
          "document_id",
          "source",
          "page",
          "section",
          "text",
          "metadata",
      ]:
        assert (
            field in doc
        ), f"Dòng {line_num} thiếu trường {field} trong pages.jsonl"
      assert (
          doc["page"] not in pages
      ), f"Trang {doc['page']} bị trùng lặp trong pages.jsonl"
      pages[doc["page"]] = doc

  assert len(pages) == 84, f"Số trang trong pages.jsonl ({len(pages)}) != 84"
  assert set(pages.keys()) == set(manifest_page_nums), (
      "Tập số trang trong pages.jsonl không khớp manifest"
  )

  total_chars = 0
  for p_manifest in manifest["pages"]:
    p_num = p_manifest["page"]
    actual_text = pages[p_num]["text"]
    actual_len = len(actual_text)
    assert actual_len > 0, f"Trang {p_num} có text rỗng"
    assert actual_len == p_manifest["char_count"], (
        f"Ký tự trang {p_num} không khớp manifest: {actual_len} !="
        f" {p_manifest['char_count']}"
    )
    assert pages[p_num]["metadata"]["char_count"] == actual_len, (
        f"Ký tự trong metadata trang {p_num} không khớp text"
    )
    assert pages[p_num]["section"] == p_manifest["section"], (
        f"Section trang {p_num} không khớp manifest"
    )
    total_chars += actual_len

  assert total_chars == manifest["total_normalized_characters"], (
      f"Tổng ký tự ({total_chars}) không khớp manifest"
      f" ({manifest['total_normalized_characters']})"
  )
  print(
      f"[OK] Extracted pages hợp lệ: 84 trang, không trùng lặp, khớp 100% ký"
      f" tự (Tổng {total_chars:,} ký tự)"
  )

  # 4. Kiểm tra Benchmark Questions (benchmark/questions.jsonl)
  benchmark_path = Path("benchmark/questions.jsonl")
  assert (
      benchmark_path.exists()
  ), f"Không tìm thấy questions.jsonl tại {benchmark_path}"
  actual_benchmark_sha256 = compute_sha256(benchmark_path)
  print(f"[OK] Benchmark SHA-256 tính toán thực tế: {actual_benchmark_sha256}")
  assert actual_benchmark_sha256.lower() == EXPECTED_BENCHMARK_SHA256.lower(), (
      f"SHA-256 của benchmark ({actual_benchmark_sha256}) không khớp giá trị"
      f" đã khóa ({EXPECTED_BENCHMARK_SHA256})"
  )

  questions = []
  with open(benchmark_path, "r", encoding="utf-8") as f:
    for line_num, line in enumerate(f, 1):
      line_str = line.strip()
      assert line_str, f"Dòng trống tại {line_num} trong questions.jsonl"
      q = json.loads(line_str)
      questions.append(q)

  assert len(questions) == 20, (
      f"Số câu hỏi phải là 20, thực tế có {len(questions)}"
  )
  q_ids = [q["id"] for q in questions]
  assert len(q_ids) == len(set(q_ids)), "Có ID câu hỏi bị trùng lặp"

  dev_qs = [q for q in questions if q.get("split") == "dev"]
  test_qs = [q for q in questions if q.get("split") == "test"]
  assert len(dev_qs) == 15, f"Tập dev phải có 15 câu, thực tế: {len(dev_qs)}"
  assert len(test_qs) == 5, f"Tập test phải có 5 câu, thực tế: {len(test_qs)}"

  filter_qs = [q for q in questions if q.get("filter") is not None]
  filter_test_qs = [q for q in test_qs if q.get("filter") is not None]
  assert len(filter_qs) >= 3, (
      f"Số câu có filter phải >= 3, thực tế có {len(filter_qs)}"
  )
  assert len(filter_test_qs) >= 1, (
      f"Số câu có filter trong test phải >= 1, thực tế có {len(filter_test_qs)}"
  )

  # Kiểm tra chi tiết từng câu hỏi
  required_q_fields = [
      "id",
      "split",
      "question",
      "expected_answer",
      "gold_source_id",
      "gold_page",
      "evidence_quote",
  ]
  for q in questions:
    q_id = q["id"]
    for field in required_q_fields:
      assert field in q, f"Câu hỏi {q_id} thiếu trường {field}"

    assert (
        q["gold_source_id"] == manifest["source_id"]
    ), f"Câu hỏi {q_id} có gold_source_id sai"
    gold_page = q["gold_page"]
    assert 18 <= gold_page <= 101, (
        f"Câu hỏi {q_id} có gold_page {gold_page} nằm ngoài dải 18-101"
    )

    # Kiểm tra filter nếu có
    if q.get("filter") is not None:
      filt = q["filter"]
      assert isinstance(filt, dict), f"Filter của câu {q_id} phải là dict"
      for k, v in filt.items():
        assert (
            k in PERMITTED_FILTER_FIELDS
        ), f"Filter của câu {q_id} chứa trường không cho phép: {k}"
        if k == "section":
          assert (
              v in PERMITTED_SECTIONS
          ), f"Filter section không hợp lệ ở câu {q_id}: {v}"
          assert v == pages[gold_page]["section"], (
              f"Filter section ({v}) không khớp section của gold_page"
              f" ({pages[gold_page]['section']}) ở câu {q_id}"
          )

    # Kiểm tra evidence quote tồn tại trên gold page
    evidence = q["evidence_quote"]
    assert len(evidence.strip()) > 0, f"Evidence rỗng ở câu {q_id}"
    page_text = pages[gold_page]["text"]
    assert evidence in page_text, (
        f"Evidence của câu {q_id} không tồn tại trên trang {gold_page}!"
    )

    # Kiểm tra alternative_gold nếu có
    if q.get("alternative_gold"):
      assert isinstance(
          q["alternative_gold"], list
      ), f"alternative_gold ở câu {q_id} phải là list"
      for alt in q["alternative_gold"]:
        assert "gold_page" in alt and "evidence_quote" in alt, (
            f"Thiếu trường trong alternative_gold ở câu {q_id}"
        )
        alt_page = alt["gold_page"]
        assert 18 <= alt_page <= 101, (
            f"Alt page {alt_page} nằm ngoài dải ở câu {q_id}"
        )
        alt_evidence = alt["evidence_quote"]
        assert alt_evidence in pages[alt_page]["text"], (
            f"Alt evidence không tồn tại trên trang {alt_page} ở câu {q_id}"
        )

  print(
      f"[OK] 20 câu benchmark hợp lệ: 15 dev, 5 test, {len(filter_qs)} câu"
      f" filter ({len(filter_test_qs)} trong test)"
  )
  print(
      "[OK] 100% evidence và alternative evidence xuất hiện chính xác trên trang"
      " nguồn"
  )
  print("=== TẤT CẢ KIỂM TRA ĐỀU THÀNH CÔNG VÀ CHÍNH XÁC 100% ===")


if __name__ == "__main__":
  main()

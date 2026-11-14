"""Pipeline orchestration entry point for Day 06 Data Ingestion."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any
from dotenv import dotenv_values

from .chunking import fixed_size, by_paragraph
from .embeddings import OpenAIEmbedder
from .evaluation import evaluate_query, summarize
from .ingestion import load_corpus_from_manifest
from .models import Chunk, DocumentPage
from .store import PgVectorStore


def get_repo_root() -> Path:
  return Path(__file__).resolve().parent.parent.parent


def compute_file_sha256(file_path: Path) -> str:
  """Compute SHA-256 hash of a file."""
  if not file_path.exists():
    return ""
  hasher = hashlib.sha256()
  with open(file_path, "rb") as f:
    while chunk := f.read(65536):
      hasher.update(chunk)
  return hasher.hexdigest()


def get_configured_model(env_path: Path | None = None) -> str:
  repo_root = get_repo_root()
  if env_path is None:
    env_path = repo_root / "starter" / ".env"
  env_vals = dotenv_values(str(env_path)) if env_path.exists() else {}
  model_name = env_vals.get("EMBEDDING_MODEL")
  if not model_name or not model_name.strip():
    raise ValueError(
        "EMBEDDING_MODEL is not set or empty in starter/.env. Please configure"
        " EMBEDDING_MODEL=text-embedding-3-small"
    )
  return model_name.strip()


def run_pipeline(
    strategy: str = "A",
    split: str = "dev",
    action: str = "all",
    confirm_api: bool = False,
    final_test: bool = False,
    manifest_path: Path | None = None,
    benchmark_path: Path | None = None,
    results_dir: Path | None = None,
) -> dict[str, Any]:
  repo_root = get_repo_root()
  manifest_path = manifest_path or (repo_root / "data" / "manifest.json")
  benchmark_path = benchmark_path or (
      repo_root / "benchmark" / "questions.jsonl"
  )
  results_dir = results_dir or (repo_root / "results")
  runs_dir = results_dir / "runs"
  results_dir.mkdir(parents=True, exist_ok=True)
  runs_dir.mkdir(parents=True, exist_ok=True)

  if strategy not in ("A", "B", "C"):
    raise NotImplementedError(
        f"Strategy '{strategy}' is not supported. Supported: A, B, C."
    )

  if strategy == "C" and action in ("all", "ingest"):
    raise ValueError(
        "Chiến lược C tái sử dụng 100% index và vector của Chiến lược B (không tạo"
        " index riêng). Để nạp dữ liệu cho C, vui lòng chạy: python -m"
        " starter.src.run --strategy B --action ingest --confirm-api"
    )

  if action not in ("all", "ingest", "eval"):
    raise ValueError(
        f"Action must be 'all', 'ingest', or 'eval', got '{action}'"
    )

  if split not in ("dev", "test"):
    raise ValueError(f"Split must be 'dev' or 'test', got '{split}'")

  if split == "test":
    if not final_test:
      raise PermissionError(
          "Running retrieval on the test set is prohibited without explicit"
          " --final-test flag confirming configuration has been frozen."
      )
    if action in ("all", "ingest"):
      raise PermissionError(
          "Cannot ingest or alter corpus/index during test evaluation. Test"
          " evaluation can only run '--action eval' against frozen indexes."
      )

  # Checksum paths
  pdf_path = repo_root / "data" / "raw" / "ptbv_report.pdf"
  corpus_path = repo_root / "data" / "extracted" / "pages.jsonl"
  pdf_sha256 = compute_file_sha256(pdf_path)
  corpus_sha256 = compute_file_sha256(corpus_path)

  # Chunking configuration per strategy
  if strategy == "A":
    chunk_config = {"chunking": "fixed_size", "chunk_size": 500, "overlap": 50}
  elif strategy in ("B", "C"):
    chunk_config = {"chunking": "by_paragraph", "max_size": 800}

  # Unique Run ID for tracking
  timestamp_str = time.strftime("%Y%m%d_%H%M%S")
  run_id = f"run_{strategy}_{action}_{timestamp_str}"

  # Read model from starter/.env
  model_name = get_configured_model()

  print(
      f"=== KHỞI CHẠY PIPELINE STRATEGY {strategy} (SPLIT: {split}, ACTION:"
      f" {action}) ==="
  )
  print(f"Run ID: {run_id}")
  print(f"Cấu hình model: {model_name}")

  # Khởi tạo Embedder và Vector Store với cùng số chiều
  embedder = OpenAIEmbedder(model_name=model_name)
  store = PgVectorStore(dimensions=embedder.dimensions)

  # ----------------------------------------------------
  # GIAI ĐOẠN 1: INGEST (nếu action == 'all' hoặc 'ingest')
  # ----------------------------------------------------
  ingest_summary: dict[str, Any] = {}
  chunks: list[Chunk] = []

  if action in ("all", "ingest"):
    # 1. Tải corpus từ manifest
    t_chunk_start = time.time()
    pages = load_corpus_from_manifest(manifest_path)
    print(f"[1/4] Đã tải {len(pages)} trang từ {manifest_path}")

    # 2. Chunking theo chiến lược
    for page in pages:
      if strategy == "A":
        chunks.extend(fixed_size(page, size=500, overlap=50))
      elif strategy == "B":
        chunks.extend(by_paragraph(page, max_size=800))
    chunk_duration = time.time() - t_chunk_start
    chunk_lengths = [len(c.text) for c in chunks]
    print(
        f"[2/4] Đã tạo {len(chunks)} chunks cho Strategy {strategy} trong"
        f" {chunk_duration:.2f}s (Min: {min(chunk_lengths)}, Max:"
        f" {max(chunk_lengths)}, Avg:"
        f" {sum(chunk_lengths)/len(chunk_lengths):.1f} ký tự)"
    )

    # 3. Tạo schema cơ sở dữ liệu (nếu chưa có)
    store.create_schema()
    print(
        f"[3/4] Schema pgvector ({embedder.dimensions} dims) đã sẵn sàng trong"
        " cơ sở dữ liệu."
    )

    if not confirm_api:
      print("\n" + "=" * 65)
      print("CHẾ ĐỘ KIỂM TRA LOCAL (DRY-RUN / CHƯA XÁC NHẬN GỌI API)")
      print("=" * 65)
      print("Đã hoàn thành kiểm tra dữ liệu và phân tách chunk tại local:")
      print(f"- Run ID: {run_id}")
      print(f"- Số trang nguồn hợp lệ: {len(pages)}")
      print(f"- Số chunks Chiến lược {strategy}: {len(chunks)}")
      print(f"- Embedder model: {embedder.model_name} ({embedder.dimensions} dims)")
      print("- Vector store: pgvector schema đã sẵn sàng")
      print("\nTheo nguyên tắc an toàn dữ liệu, nội dung văn bản chưa được gửi")
      print("tới OpenAI API khi chưa có xác nhận quyền xử lý tài liệu.")
      print("\nĐể thực hiện ingest thật, chạy lệnh có cờ --confirm-api:")
      print(
          f"python -m starter.src.run --strategy {strategy} --action {action}"
          f" --split {split} --confirm-api"
      )
      print("=" * 65 + "\n")
      return {
          "status": "waiting_api_confirmation",
          "run_id": run_id,
          "strategy": strategy,
          "action": action,
          "chunks_count": len(chunks),
          "pages_count": len(pages),
          "model": embedder.model_name,
          "dimensions": embedder.dimensions,
          "pdf_sha256": pdf_sha256,
          "corpus_sha256": corpus_sha256,
          "chunk_config": chunk_config,
      }

    # 4. Tạo embeddings và Ingest vào Vector Store (chỉ khi có --confirm-api)
    embedder.reset_stats()
    t_embed_start = time.time()
    chunk_texts = [c.text for c in chunks]
    print(
        f"[4/4] Đang tạo vector embedding cho {len(chunk_texts)} chunks bằng"
        f" {embedder.model_name}..."
    )
    vectors = embedder.embed_documents(chunk_texts)
    embed_duration = time.time() - t_embed_start
    ingest_api_stats = embedder.get_stats()

    t_db_start = time.time()
    store.upsert(strategy=strategy, chunks=chunks, vectors=vectors)
    db_duration = time.time() - t_db_start
    total_ingest_time = chunk_duration + embed_duration + db_duration

    stored_count = store.count_chunks(strategy=strategy)

    # Ghi nhận index metadata vào cơ sở dữ liệu
    index_meta_record = {
        "strategy": strategy,
        "model": embedder.model_name,
        "dimensions": embedder.dimensions,
        "pdf_sha256": pdf_sha256,
        "corpus_sha256": corpus_sha256,
        "chunk_config": chunk_config,
        "total_chunks": stored_count,
        "run_id": run_id,
    }
    store.record_index_metadata(strategy=strategy, meta=index_meta_record)

    ingest_summary = {
        "run_id": run_id,
        "timestamp": timestamp_str,
        "strategy": strategy,
        "action": action,
        "status": "completed",
        "model": embedder.model_name,
        "dimensions": embedder.dimensions,
        "pdf_sha256": pdf_sha256,
        "corpus_sha256": corpus_sha256,
        "chunk_config": chunk_config,
        "total_chunks": stored_count,
        "timings": {
            "chunking_time_seconds": round(chunk_duration, 2),
            "embedding_time_seconds": round(embed_duration, 2),
            "db_write_time_seconds": round(db_duration, 2),
            "total_ingest_time_seconds": round(total_ingest_time, 2),
        },
        "api_usage": ingest_api_stats,
        "cost": "chưa xác định (cần bảng giá API chính thức được xác minh)",
    }

    # Lưu summary ingest (không chứa PDF text hoặc secrets)
    latest_ingest_file = results_dir / f"ingest_{strategy}_summary.json"
    per_run_ingest_file = runs_dir / f"{run_id}_summary.json"
    with open(latest_ingest_file, "w", encoding="utf-8") as f:
      json.dump(ingest_summary, f, ensure_ascii=False, indent=2)
    with open(per_run_ingest_file, "w", encoding="utf-8") as f:
      json.dump(ingest_summary, f, ensure_ascii=False, indent=2)

    print(
        f"[OK] Ingest hoàn tất: {stored_count} chunks trong"
        f" {total_ingest_time:.2f}s (Chunking: {chunk_duration:.2f}s, Embed:"
        f" {embed_duration:.2f}s, DB write: {db_duration:.2f}s)"
    )
    print(f"Saved ingest summary: {latest_ingest_file} and {per_run_ingest_file}")

  # ----------------------------------------------------
  # GIAI ĐOẠN 2: EVALUATION (nếu action == 'all' hoặc 'eval')
  # ----------------------------------------------------
  if action in ("all", "eval"):
    index_strategy = "B" if strategy == "C" else strategy

    # Kiểm tra store và schema tương thích
    store.verify_schema()
    existing_chunks_count = store.count_chunks(strategy=index_strategy)
    if existing_chunks_count == 0:
      raise RuntimeError(
          f"Không tìm thấy chunk nào trong cơ sở dữ liệu cho strategy"
          f" '{index_strategy}'. Cần chạy --action ingest trước khi chạy --action eval."
      )

    # 1. Kiểm tra index metadata đã ghi nhận trong store
    stored_meta = store.get_index_metadata(index_strategy)
    if not stored_meta:
      raise RuntimeError(
          f"Chưa có index metadata cho strategy '{index_strategy}'. Cần chạy --action"
          " ingest trước khi chạy eval."
      )

    # Kiểm tra tính tương thích của cấu hình hiện tại với index đã ingest
    if stored_meta["model"] != embedder.model_name:
      raise ValueError(
          f"Index configuration mismatch (Model): Index được nạp bằng model"
          f" '{stored_meta['model']}', nhưng cấu hình hiện tại là"
          f" '{embedder.model_name}'. Cần ingest lại trước khi eval."
      )
    if stored_meta["dimensions"] != embedder.dimensions:
      raise ValueError(
          f"Index configuration mismatch (Dimensions): Index có dimensions"
          f" {stored_meta['dimensions']}, nhưng cấu hình hiện tại yêu cầu"
          f" {embedder.dimensions}. Cần ingest lại trước khi eval."
      )
    if stored_meta["pdf_sha256"] != pdf_sha256:
      raise ValueError(
          "Index configuration mismatch (PDF Checksum): File PDF nguồn đã thay"
          " đổi so với thời điểm ingest. Cần ingest lại trước khi eval."
      )
    if stored_meta["corpus_sha256"] != corpus_sha256:
      raise ValueError(
          "Index configuration mismatch (Corpus Checksum): File corpus chuẩn"
          " hóa đã thay đổi so với thời điểm ingest. Cần ingest lại trước khi"
          " eval."
      )
    if stored_meta["chunk_config"] != chunk_config:
      raise ValueError(
          f"Index configuration mismatch (Chunk Config): Cấu hình chunk"
          f" {chunk_config} khác với index đã lưu {stored_meta['chunk_config']}."
          " Cần ingest lại trước khi eval."
      )

    print(
        f"[Index Verified] Khớp 100% cấu hình index đã ingest (Target Strategy: {index_strategy}, Run ID:"
        f" {stored_meta['run_id']}, Chunks: {stored_meta['total_chunks']})"
    )

    # Đọc câu hỏi benchmark
    questions: list[dict[str, Any]] = []
    with open(benchmark_path, "r", encoding="utf-8") as f:
      for line in f:
        q = json.loads(line)
        if q.get("split") == split:
          questions.append(q)

    print(
        f"Đang chuẩn bị đánh giá truy xuất {len(questions)} câu hỏi tập {split}"
        f" trên {existing_chunks_count} chunks (Strategy: {strategy}, Index: {index_strategy})..."
    )

    if not confirm_api:
      print("\n" + "=" * 65)
      print("CHẾ ĐỘ KIỂM TRA LOCAL (EVAL DRY-RUN)")
      print("=" * 65)
      print(f"- Run ID: {run_id}")
      print(f"- Target index Strategy: {index_strategy} (Run ID: {stored_meta['run_id']})")
      print(f"- Số câu hỏi {split} đã nạp: {len(questions)}")
      print(f"- Số chunk sẵn có trong DB: {existing_chunks_count}")
      print(f"- Embedder model: {embedder.model_name} ({embedder.dimensions} dims)")
      print("\nĐể thực hiện truy xuất thật, chạy lệnh có cờ --confirm-api:")
      print(
          f"python -m starter.src.run --strategy {strategy} --action {action}"
          f" --split {split} --confirm-api"
      )
      print("=" * 65 + "\n")
      return {
          "status": "waiting_api_confirmation",
          "run_id": run_id,
          "strategy": strategy,
          "index_strategy": index_strategy,
          "action": action,
          "split": split,
          "ingest_run_id": stored_meta["run_id"],
          "existing_chunks_count": existing_chunks_count,
          "questions_count": len(questions),
      }

    # Chạy Evaluation thật (chỉ khi có --confirm-api)
    embedder.reset_stats()
    traces: list[dict[str, Any]] = []
    t_eval_start = time.time()

    for q in questions:
      query_text = q["question"]
      query_vector = embedder.embed_query(query_text)
      filters = q.get("filter") if strategy == "C" else None
      hits = store.search(
          strategy=index_strategy, query_vector=query_vector, top_k=3, filters=filters
      )
      trace = evaluate_query(q, hits)
      trace["strategy"] = strategy
      trace["index_strategy"] = index_strategy
      trace["applied_filters"] = filters
      trace["query_text"] = query_text
      traces.append(trace)

    eval_duration = time.time() - t_eval_start
    eval_api_stats = embedder.get_stats()

    summary = summarize(traces)
    summary["eval_run_id"] = run_id
    summary["ingest_run_id"] = stored_meta["run_id"]
    summary["strategy"] = strategy
    summary["index_strategy"] = index_strategy
    summary["split"] = split
    summary["embedding_model"] = embedder.model_name
    summary["dimensions"] = embedder.dimensions
    summary["total_chunks_in_store"] = existing_chunks_count
    summary["eval_time_seconds"] = round(eval_duration, 2)
    summary["eval_api_usage"] = eval_api_stats
    summary["ingest_summary"] = ingest_summary
    summary["estimated_cost"] = (
        "chưa xác định (cần bảng giá API chính thức được xác minh)"
    )

    # Lưu trace chi tiết (bị git ignore do chứa text)
    trace_file = results_dir / f"strategy_{strategy}_{split}_trace.json"
    per_run_trace_file = runs_dir / f"{run_id}_trace.json"
    trace_payload = {
        "summary": summary,
        "traces": traces,
        "index_metadata": stored_meta,
    }
    with open(trace_file, "w", encoding="utf-8") as f:
      json.dump(trace_payload, f, ensure_ascii=False, indent=2)
    with open(per_run_trace_file, "w", encoding="utf-8") as f:
      json.dump(trace_payload, f, ensure_ascii=False, indent=2)

    # Lưu eval summary (không chứa PDF text)
    latest_eval_file = results_dir / f"eval_{strategy}_{split}_summary.json"
    per_run_eval_file = runs_dir / f"{run_id}_summary.json"
    with open(latest_eval_file, "w", encoding="utf-8") as f:
      json.dump(summary, f, ensure_ascii=False, indent=2)
    with open(per_run_eval_file, "w", encoding="utf-8") as f:
      json.dump(summary, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 55)
    print(f"KẾT QUẢ ĐÁNH GIÁ CHIẾN LƯỢC {strategy} (INDEX: {index_strategy}, TẬP {split.upper()})")
    print("=" * 55)
    print(f"Eval Run ID:            {run_id}")
    print(f"Ingest Run ID:          {stored_meta['run_id']}")
    print(f"Tổng số câu hỏi:        {summary['total_queries']}")
    print(f"Hit@1:                  {summary['hit_1_formatted']}")
    print(f"Evidence Hit@3:         {summary['hit_3_formatted']}")
    print(f"Số chunk trong store:   {summary['total_chunks_in_store']}")
    print(f"Thời gian Eval:         {summary['eval_time_seconds']}s")
    print(f"Eval API Calls:         {eval_api_stats['api_calls']}")
    print(f"Eval API Prompt Tokens: {eval_api_stats['prompt_tokens']}")
    print(
        f"Eval Cache Hits/Misses:"
        f" {eval_api_stats['cache_hits']}/{eval_api_stats['cache_misses']}"
    )
    print(f"Ước tính chi phí:       {summary['estimated_cost']}")
    print(f"File summary:           {latest_eval_file}")
    print(f"File trace:             {trace_file}")
    print("=" * 55 + "\n")

    return summary
    print("=" * 55)
    print(f"Eval Run ID:            {run_id}")
    print(f"Ingest Run ID:          {stored_meta['run_id']}")
    print(f"Tổng số câu hỏi:        {summary['total_queries']}")
    print(f"Hit@1:                  {summary['hit_1_formatted']}")
    print(f"Evidence Hit@3:         {summary['hit_3_formatted']}")
    print(f"Số chunk trong store:   {summary['total_chunks_in_store']}")
    print(f"Thời gian Eval:         {summary['eval_time_seconds']}s")
    print(f"Eval API Calls:         {eval_api_stats['api_calls']}")
    print(f"Eval API Prompt Tokens: {eval_api_stats['prompt_tokens']}")
    print(
        f"Eval Cache Hits/Misses:"
        f" {eval_api_stats['cache_hits']}/{eval_api_stats['cache_misses']}"
    )
    print(f"Ước tính chi phí:       {summary['estimated_cost']}")
    print(f"File summary:           {latest_eval_file}")
    print(f"File trace:             {trace_file}")
    print("=" * 55 + "\n")

    return summary

  return ingest_summary


def main() -> None:
  parser = argparse.ArgumentParser(
      description="Run Day 06 Data Ingestion Pipeline"
  )
  parser.add_argument(
      "--strategy",
      choices=["A", "B", "C"],
      default="A",
      help="Strategy to run (default: A)",
  )
  parser.add_argument(
      "--split",
      choices=["dev", "test"],
      default="dev",
      help="Benchmark split to evaluate (default: dev)",
  )
  parser.add_argument(
      "--action",
      choices=["all", "ingest", "eval"],
      default="all",
      help="Action to execute: 'all', 'ingest', or 'eval' (default: all)",
  )
  parser.add_argument(
      "--confirm-api",
      action="store_true",
      help="Explicit confirmation to call external OpenAI Embedding API",
  )
  parser.add_argument(
      "--final-test",
      action="store_true",
      help="Explicitly enable retrieval evaluation on the frozen test set",
  )
  parser.add_argument(
      "--manifest",
      type=Path,
      default=None,
      help="Custom path to data/manifest.json",
  )
  parser.add_argument(
      "--benchmark",
      type=Path,
      default=None,
      help="Custom path to benchmark/questions.jsonl",
  )

  args = parser.parse_args()
  run_pipeline(
      strategy=args.strategy,
      split=args.split,
      action=args.action,
      confirm_api=args.confirm_api,
      final_test=args.final_test,
      manifest_path=args.manifest,
      benchmark_path=args.benchmark,
  )


if __name__ == "__main__":
  main()

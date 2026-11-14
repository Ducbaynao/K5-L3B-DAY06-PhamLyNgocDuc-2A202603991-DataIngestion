import csv
import json
from pathlib import Path

# Load summaries
runs = {
    ("A", "dev"): ("results/eval_A_dev_summary.json", "results/strategy_A_dev_trace.json", "run_A_ingest_20261114_105804"),
    ("A", "test"): ("results/eval_A_test_summary.json", "results/strategy_A_test_trace.json", "run_A_ingest_20261114_105804"),
    ("B", "dev"): ("results/eval_B_dev_summary.json", "results/strategy_B_dev_trace.json", "run_B_ingest_20261114_111859"),
    ("B", "test"): ("results/eval_B_test_summary.json", "results/strategy_B_test_trace.json", "run_B_ingest_20261114_111859"),
    ("C", "dev"): ("results/eval_C_dev_summary.json", "results/strategy_C_dev_trace.json", "run_B_ingest_20261114_111859"),
    ("C", "test"): ("results/eval_C_test_summary.json", "results/strategy_C_test_trace.json", "run_B_ingest_20261114_111859"),
}

rows = []
for (strat, split), (sum_path, trace_path, ingest_run_id) in runs.items():
    with open(sum_path, "r", encoding="utf-8") as f:
        s = json.load(f)
    with open(trace_path, "r", encoding="utf-8") as f:
        t_data = json.load(f)
        traces = t_data["traces"]

    # Recompute metrics from trace
    n_queries = len(traces)
    h1_count = sum(1 for t in traces if t["hit_at_1"])
    h3_count = sum(1 for t in traces if t["evidence_hit_at_3"])
    
    # Assert consistency with summary
    assert h1_count == s["hit_1_count"], f"Mismatch h1 {strat} {split}"
    assert h3_count == s["hit_3_count"], f"Mismatch h3 {strat} {split}"
    assert n_queries == s["total_queries"], f"Mismatch total {strat} {split}"

    h1_str = f"{h1_count}/{n_queries}"
    h1_pct = f"{h1_count/n_queries*100:.1f}%"
    h3_str = f"{h3_count}/{n_queries}"
    h3_pct = f"{h3_count/n_queries*100:.1f}%"
    
    rows.append({
        "strategy": strat,
        "split": split,
        "total_queries": n_queries,
        "hit_1_count": h1_count,
        "hit_1_fraction": h1_str,
        "hit_1_percent": h1_pct,
        "evidence_hit_3_count": h3_count,
        "evidence_hit_3_fraction": h3_str,
        "evidence_hit_3_percent": h3_pct,
        "chunks_in_store": s["total_chunks_in_store"],
        "eval_run_id": s["eval_run_id"],
        "ingest_run_id": ingest_run_id,
        "eval_time_seconds": s["eval_time_seconds"],
        "api_calls": s["eval_api_usage"]["api_calls"],
        "prompt_tokens": s["eval_api_usage"]["prompt_tokens"],
        "cache_hits": s["eval_api_usage"]["cache_hits"],
        "cache_misses": s["eval_api_usage"]["cache_misses"],
        "summary_file": sum_path,
        "cost_status": "chưa xác định (cần bảng giá API chính thức)"
    })

fieldnames = list(rows[0].keys())
with open("results/metrics.csv", "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print("Saved results/metrics.csv successfully.")

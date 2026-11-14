"""Evaluate retrieved evidence and preserve per-query traces."""
from typing import Any


def _normalize_whitespace(text: str) -> str:
  """Collapse internal whitespace to ensure consistent matching."""
  return " ".join(text.split())


def check_hit(
    question: dict[str, Any], chunk: dict[str, Any]
) -> tuple[bool, str]:
  """Check if a single chunk qualifies as a hit for the question.

  Returns (is_hit, reason).
  Criteria:
  1. chunk document_id matches gold_source_id.
  2. chunk page matches gold_page OR matches an entry in alternative_gold.
  3. chunk text contains the corresponding evidence_quote (with normalized
  whitespace).
  4. Empty evidence quote NEVER qualifies as a hit.
  """
  gold_source_id = question.get("gold_source_id")
  if chunk.get("document_id") != gold_source_id:
    return (
        False,
        f"source mismatch: {chunk.get('document_id')} != {gold_source_id}",
    )

  chunk_page = chunk.get("page")
  chunk_text_norm = _normalize_whitespace(chunk.get("text", ""))

  # Primary gold check
  gold_page = question.get("gold_page")
  primary_evidence = _normalize_whitespace(question.get("evidence_quote", ""))

  if not primary_evidence:
    return False, "empty primary evidence_quote cannot qualify as a hit"

  if chunk_page == gold_page and primary_evidence in chunk_text_norm:
    return True, "primary_gold_hit"

  # Alternative gold check
  for alt in question.get("alternative_gold", []):
    alt_page = alt.get("gold_page")
    alt_evidence = _normalize_whitespace(alt.get("evidence_quote", ""))
    if not alt_evidence:
      continue
    if chunk_page == alt_page and alt_evidence in chunk_text_norm:
      return True, "alternative_gold_hit"

  if chunk_page == gold_page:
    return False, "page matched but evidence not fully contained in chunk"

  return False, f"page {chunk_page} did not match gold page {gold_page}"


def evaluate_query(
    question: dict[str, Any], hits: list[dict[str, Any]]
) -> dict[str, Any]:
  """Check source/page and sufficient gold evidence for top-k retrieved hits.

  Evidence Hit@3 is strictly evaluated on the first 3 hits (hits[:3]).
  A single chunk must contain sufficient evidence to count as a hit.
  """
  evaluated_hits: list[dict[str, Any]] = []
  has_hit_in_top3 = False
  hit_at_1 = False

  # Strictly limit Evidence Hit@3 evaluation to top-3
  top3_hits = hits[:3] if hits else []

  for rank, hit in enumerate(top3_hits, 1):
    is_hit, reason = check_hit(question, hit)
    hit_info = dict(hit)
    hit_info["rank"] = rank
    hit_info["is_hit"] = is_hit
    hit_info["hit_reason"] = reason
    evaluated_hits.append(hit_info)

    if rank == 1 and is_hit:
      hit_at_1 = True
    if is_hit:
      has_hit_in_top3 = True

  # If more than 3 hits were passed, evaluate remaining for trace audit without affecting top3
  if hits and len(hits) > 3:
    for rank, hit in enumerate(hits[3:], 4):
      is_hit, reason = check_hit(question, hit)
      hit_info = dict(hit)
      hit_info["rank"] = rank
      hit_info["is_hit"] = is_hit
      hit_info["hit_reason"] = reason
      evaluated_hits.append(hit_info)

  return {
      "question_id": question.get("id"),
      "split": question.get("split"),
      "question": question.get("question"),
      "expected_answer": question.get("expected_answer"),
      "gold_source_id": question.get("gold_source_id"),
      "gold_page": question.get("gold_page"),
      "evidence_quote": question.get("evidence_quote"),
      "alternative_gold": question.get("alternative_gold", []),
      "filter": question.get("filter"),
      "hit_at_1": hit_at_1,
      "evidence_hit_at_3": has_hit_in_top3,
      "hits": evaluated_hits,
  }


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
  """Aggregate Hit@1 and Evidence Hit@3 by strategy and dev/test split."""
  total = len(traces)
  if total == 0:
    return {
        "total_queries": 0,
        "hit_1_count": 0,
        "hit_1_ratio": 0.0,
        "hit_1_formatted": "0/0 (0.0%)",
        "hit_3_count": 0,
        "hit_3_ratio": 0.0,
        "hit_3_formatted": "0/0 (0.0%)",
    }

  hit_1_count = sum(1 for t in traces if t.get("hit_at_1"))
  hit_3_count = sum(1 for t in traces if t.get("evidence_hit_at_3"))

  return {
      "total_queries": total,
      "hit_1_count": hit_1_count,
      "hit_1_ratio": hit_1_count / total,
      "hit_1_formatted": f"{hit_1_count}/{total} ({hit_1_count / total * 100:.1f}%)",
      "hit_3_count": hit_3_count,
      "hit_3_ratio": hit_3_count / total,
      "hit_3_formatted": (
          f"{hit_3_count}/{total} ({hit_3_count / total * 100:.1f}%)"
      ),
  }

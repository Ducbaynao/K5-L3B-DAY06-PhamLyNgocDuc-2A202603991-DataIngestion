"""Script tổng hợp và xác thực điểm audit thủ công của học viên.

Chỉ tính điểm chính thức khi các trường human_score đã được người chấm nhập
và xác nhận đầy đủ. Không bao giờ tự động thay ô trống bằng 0 và không bao
giờ dùng điểm AI đề xuất để thay cho điểm người chấm.
"""

import argparse
import csv
import json
from pathlib import Path
import sys


def get_repo_root() -> Path:
  return Path(__file__).resolve().parent.parent


def check_and_aggregate(
    coh_csv: Path,
    grnd_csv: Path,
    import_file: Path | None = None,
    output_summary: Path | None = None,
) -> dict:
  repo_root = get_repo_root()
  coh_csv = coh_csv or (repo_root / "results" / "audit" / "coherence_audit.csv")
  grnd_csv = grnd_csv or (
      repo_root / "results" / "audit" / "grounding_audit.csv"
  )
  output_summary = output_summary or (
      repo_root / "results" / "audit" / "human_audit_summary.json"
  )

  # 1. Import từ file export của review.html nếu có
  if import_file and import_file.exists():
    print(f"[Import] Đang nhập điểm từ file export: {import_file}...")
    imported_scores = {"coherence": {}, "grounding": {}}

    if import_file.suffix.lower() == ".json":
      with open(import_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        for r in data.get("coherence", []):
          key = (str(r["anchor_id"]), r["strategy"])
          imported_scores["coherence"][key] = (
              str(r.get("human_score", "")).strip(),
              r.get("human_notes", "").strip(),
          )
        for r in data.get("grounding", []):
          key = (r["question_id"], r["strategy"])
          imported_scores["grounding"][key] = (
              str(r.get("human_score", "")).strip(),
              r.get("human_notes", "").strip(),
          )
    elif import_file.suffix.lower() == ".csv":
      with open(import_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
          cat = r.get("category", "").strip().lower()
          if cat in imported_scores:
            key = (r["id"].strip(), r["strategy"].strip())
            imported_scores[cat][key] = (
                r.get("human_score", "").strip(),
                r.get("human_notes", "").strip(),
            )

    # Cập nhật coherence_audit.csv
    if imported_scores["coherence"]:
      with open(coh_csv, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
      fieldnames = list(rows[0].keys())
      for row in rows:
        key = (str(row["anchor_id"]), row["strategy"])
        if key in imported_scores["coherence"]:
          val, notes = imported_scores["coherence"][key]
          if val in ("0", "1", "2"):
            row["human_score"] = val
            row["human_notes"] = notes
            row["human_review_status"] = "reviewed"
      with open(coh_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
      print(f"  -> Đã cập nhật điểm vào {coh_csv}")

    # Cập nhật grounding_audit.csv
    if imported_scores["grounding"]:
      with open(grnd_csv, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
      fieldnames = list(rows[0].keys())
      for row in rows:
        key = (row["question_id"], row["strategy"])
        if key in imported_scores["grounding"]:
          val, notes = imported_scores["grounding"][key]
          if val in ("0", "1", "2"):
            row["human_score"] = val
            row["human_notes"] = notes
            row["human_review_status"] = "reviewed"
      with open(grnd_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
      print(f"  -> Đã cập nhật điểm vào {grnd_csv}")

  # 2. Đọc và xác thực Coherence Audit
  print("\n=== KIỂM TRA CHỈ SỐ AUDIT THỦ CÔNG CỦA HỌC VIÊN ===")
  with open(coh_csv, "r", encoding="utf-8") as f:
    coh_rows = list(csv.DictReader(f))

  total_coh = len(coh_rows)
  valid_coh_scores = {"A": [], "B": [], "C": []}
  coh_missing = 0
  coh_invalid = []

  for idx, r in enumerate(coh_rows):
    score_str = r.get("human_score", "").strip()
    strat = r.get("strategy")
    aid = r.get("anchor_id")

    if not score_str:
      coh_missing += 1
    elif score_str not in ("0", "1", "2"):
      coh_invalid.append(
          f"Anchor #{aid} Strategy {strat}: Giá trị '{score_str}' không hợp lệ"
          " (chỉ chấp nhận 0, 1, 2)"
      )
    else:
      valid_coh_scores[strat].append(int(score_str))

  # 3. Đọc và xác thực Grounding Audit
  with open(grnd_csv, "r", encoding="utf-8") as f:
    grnd_rows = list(csv.DictReader(f))

  total_grnd = len(grnd_rows)
  valid_grnd_scores = {"A": [], "B": [], "C": []}
  grnd_missing = 0
  grnd_invalid = []

  for idx, r in enumerate(grnd_rows):
    score_str = r.get("human_score", "").strip()
    strat = r.get("strategy")
    qid = r.get("question_id")

    if not score_str:
      grnd_missing += 1
    elif score_str not in ("0", "1", "2"):
      grnd_invalid.append(
          f"Query {qid} Strategy {strat}: Giá trị '{score_str}' không hợp lệ"
          " (chỉ chấp nhận 0, 1, 2)"
      )
    else:
      valid_grnd_scores[strat].append(int(score_str))

  # 4. Báo cáo tình trạng
  has_errors = False
  if coh_invalid:
    print(f"[LỖI COHERENCE] Có {len(coh_invalid)} bản ghi điểm sai định dạng:")
    for err in coh_invalid:
      print(f"  - {err}")
    has_errors = True

  if grnd_invalid:
    print(f"[LỖI GROUNDING] Có {len(grnd_invalid)} bản ghi điểm sai định dạng:")
    for err in grnd_invalid:
      print(f"  - {err}")
    has_errors = True

  coh_completed = total_coh - coh_missing - len(coh_invalid)
  grnd_completed = total_grnd - grnd_missing - len(grnd_invalid)

  print(
      f"\nTiến độ Coherence: {coh_completed}/{total_coh} bản ghi đã được học viên"
      " chấm."
  )
  print(
      f"Tiến độ Grounding: {grnd_completed}/{total_grnd} bản ghi đã được học viên"
      " chấm."
  )

  is_fully_completed = (
      coh_missing == 0 and grnd_missing == 0 and not has_errors
  )

  if not is_fully_completed:
    print("\n" + "=" * 60)
    print("TRẠNG THÁI: AUDIT THỦ CÔNG CHƯA HOÀN TẤT (INCOMPLETE)")
    print("=" * 60)
    print(
        f"Còn {coh_missing} bản ghi Coherence và {grnd_missing} bản ghi"
        " Grounding chưa có điểm chính thức."
    )
    print("Hệ thống TUYỆT ĐỐI KHÔNG tự động thay thế bằng 0 hoặc dùng điểm AI.")
    print("Vui lòng mở results/audit/local_text/review.html để chấm điểm, hoặc")
    print("nhập trực tiếp vào cột 'human_score' trong các file CSV.")
    print("=" * 60 + "\n")
    return {
        "status": "incomplete",
        "coherence_completed": f"{coh_completed}/{total_coh}",
        "grounding_completed": f"{grnd_completed}/{total_grnd}",
        "fully_completed": False,
    }

  # 5. Nếu đã hoàn tất đầy đủ 100%: Tính điểm trung bình chính thức
  summary = {
      "status": "completed",
      "reviewer": "Phạm Lý Ngọc Đức",
      "fully_completed": True,
      "coherence": {},
      "grounding": {},
  }

  print("\n" + "=" * 60)
  print("KẾT QUẢ AUDIT THỦ CÔNG CHÍNH THỨC CỦA HỌC VIÊN")
  print("=" * 60)

  print("--- 1. Chunk Coherence (Trung bình / 2 trên 10 anchors) ---")
  for s in ["A", "B", "C"]:
    scores = valid_coh_scores[s]
    mean_score = sum(scores) / len(scores)
    summary["coherence"][s] = {
        "mean_score": round(mean_score, 2),
        "scores": scores,
        "count": len(scores),
    }
    print(
        f"  Chiến lược {s}: {mean_score:.2f} / 2 (Các điểm: {scores},"
        f" n={len(scores)})"
    )

  print("\n--- 2. Grounding Quality (Trung bình / 2 trên 5 câu test) ---")
  for s in ["A", "B", "C"]:
    scores = valid_grnd_scores[s]
    mean_score = sum(scores) / len(scores)
    summary["grounding"][s] = {
        "mean_score": round(mean_score, 2),
        "scores": scores,
        "count": len(scores),
    }
    print(
        f"  Chiến lược {s}: {mean_score:.2f} / 2 (Các điểm: {scores},"
        f" n={len(scores)})"
    )
  print("=" * 60 + "\n")

  with open(output_summary, "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)
  print(f"Đã lưu kết quả tổng hợp chính thức vào: {output_summary}")

  return summary


def main():
  parser = argparse.ArgumentParser(
      description="Tổng hợp và kiểm tra audit thủ công"
  )
  parser.add_argument(
      "--import-file",
      type=Path,
      default=None,
      help="Đường dẫn file JSON hoặc CSV export từ review.html để nhập điểm",
  )
  parser.add_argument(
      "--coh-csv",
      type=Path,
      default=None,
      help="Đường dẫn custom tới coherence_audit.csv",
  )
  parser.add_argument(
      "--grnd-csv",
      type=Path,
      default=None,
      help="Đường dẫn custom tới grounding_audit.csv",
  )
  args = parser.parse_args()

  check_and_aggregate(
      coh_csv=args.coh_csv, grnd_csv=args.grnd_csv, import_file=args.import_file
  )


if __name__ == "__main__":
  main()

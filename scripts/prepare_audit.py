import json
import csv
from pathlib import Path
from starter.src.store import PgVectorStore

anchors = [
    (1, 18, "Từ góc độ lịch sử, sự phát triển và trọng tâm của báo cáo liên quan đến PTBV đã có một số thay đổi (Fifka, 2012; Kolk, 2010)."),
    (2, 35, "Khoảng trống về dữ liệu trong các nghiên cứu liên quan đến công bố thông tin về phát triển bền vững (PTBV) tại Việt Nam đã trở thành một điểm quan trọng cần xem xét."),
    (3, 40, "Bộ chuẩn mực GRI được tổ chức thành bốn nhóm chính là tổng quát, kinh tế, môi trường, và xã hội."),
    (4, 47, "Ghozali và Chariri (2007) cũng cho rằng lý thuyết cơ bản về tính hợp pháp là hợp đồng xã hội giữa công ty và cộng đồng nơi công ty hoạt động và sử dụng các nguồn lực kinh tế."),
    (5, 53, "Giai đoạn điều tra sơ bộ trong quy trình nghiên cứu (bước 6 đến bước 8) đóng vai trò quan trọng trong việc đảm bảo chất lượng và hiệu suất của các thang đo trước khi tiến hành nghiên cứu chính thức."),
    (6, 64, "Bảng câu hỏi được thiết kế theo thang đo Likert 5 mức độ được đánh số từ 1 tới 5 theo mức độ đồng ý tăng dần."),
    (7, 75, "Trong 239 đối tượng tham gia khảo sát về kinh nghiệm làm việc, có 142 đối tượng có kinh nghiệm làm việc từ 2 đến 5 năm chiếm 59.4%"),
    (8, 89, "Trong mô hình hồi quy bội, một giả thuyết được thêm vào là các biến độc lập không có tương quan hoàn toàn với nhau."),
    (9, 94, "Thứ nhất, nghiên cứu sử dụng phương pháp nghiên cứu định tính. Trong quá trình này, nghiên cứu đã tiến hành khảo sát các nghiên cứu liên quan đến đề tài cả trong và ngoài nước"),
    (10, 100, "Bổ Nhiệm Người Lãnh Đạo ESG: Xác định một người lãnh đạo với trách nhiệm và quyền lực cần thiết để dẫn dắt các sáng kiến PTBV.")
]

audit_dir = Path("results/audit")
local_text_dir = audit_dir / "local_text"
audit_dir.mkdir(parents=True, exist_ok=True)
local_text_dir.mkdir(parents=True, exist_ok=True)

store = PgVectorStore()

# -------------------------------------------------------------------------
# 1. COHERENCE AUDIT
# -------------------------------------------------------------------------
# Rule for selecting chunk:
# Find chunk on the anchor page that contains the anchor text.
# If multiple chunks overlap the anchor, pick the first one containing the anchor.

coherence_rows = []
coherence_text_guide = []

with store._get_connection() as conn:
    with conn.cursor() as cur:
        for idx, page_num, anchor_text in anchors:
            norm_anchor = " ".join(anchor_text.split())
            
            for strat in ["A", "B", "C"]:
                target_strat = "B" if strat == "C" else strat
                cur.execute(
                    "SELECT chunk_id, text, metadata FROM document_chunks WHERE strategy = %s AND page = %s ORDER BY chunk_id ASC;",
                    (target_strat, page_num)
                )
                chunks = cur.fetchall()
                
                matched_chunk_id = None
                matched_text = None
                matched_meta = None
                coverage = "not_found"
                
                for cid, ctext, cmeta in chunks:
                    norm_c = " ".join(ctext.split())
                    if norm_anchor in norm_c:
                        matched_chunk_id = cid
                        matched_text = ctext
                        matched_meta = cmeta
                        coverage = "full"
                        break
                    elif norm_anchor[:50] in norm_c or norm_anchor[-50:] in norm_c:
                        matched_chunk_id = cid
                        matched_text = ctext
                        matched_meta = cmeta
                        coverage = "partial"
                
                # Propose AI score
                # 0: fragmented mid-sentence or lacks subject; 1: partially coherent; 2: fully self-contained
                if coverage == "full":
                    # Check if chunk starts / ends cleanly
                    if matched_text.strip().endswith((".", ":", "!", "?", "”", "\"")):
                        ai_score = 2
                        ai_rat = "Chunk giữ trọn vẹn câu anchor và ranh giới đoạn/câu kết thúc tự nhiên."
                    else:
                        ai_score = 1
                        ai_rat = "Chunk chứa trọn anchor nhưng đoạn văn bị ngắt giữa chừng ở biên chunk."
                elif coverage == "partial":
                    ai_score = 1
                    ai_rat = "Anchor bị cắt ngang qua ranh giới chunk."
                else:
                    ai_score = 0
                    ai_rat = "Không tìm thấy chunk nào bao phủ anchor này."
                
                coherence_rows.append({
                    "anchor_id": idx,
                    "page": page_num,
                    "strategy": strat,
                    "target_index_strategy": target_strat,
                    "chunk_id": matched_chunk_id or "NONE",
                    "char_count": len(matched_text) if matched_text else 0,
                    "anchor_coverage": coverage,
                    "selection_rule": "First chunk on anchor page containing anchor text",
                    "reviewer_type": "ai_proposed",
                    "human_review_status": "pending",
                    "ai_proposed_score": ai_score,
                    "ai_rationale": ai_rat,
                    "human_score": "",
                    "human_notes": ""
                })
                
                if matched_text:
                    coherence_text_guide.append({
                        "anchor_id": idx,
                        "page": page_num,
                        "strategy": strat,
                        "chunk_id": matched_chunk_id,
                        "anchor_text": anchor_text,
                        "chunk_text": matched_text,
                        "ai_proposed_score": ai_score,
                        "ai_rationale": ai_rat
                    })

# Save coherence CSV (no raw source text)
coh_fieldnames = list(coherence_rows[0].keys())
with open(audit_dir / "coherence_audit.csv", "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=coh_fieldnames)
    writer.writeheader()
    writer.writerows(coherence_rows)

# Save local text guide for human grading
with open(local_text_dir / "coherence_review_guide.json", "w", encoding="utf-8") as f:
    json.dump(coherence_text_guide, f, ensure_ascii=False, indent=2)

print("Coherence audit generated.")

# -------------------------------------------------------------------------
# 2. METADATA AUDIT (5 test queries × top-3 hits × 3 strategies)
# -------------------------------------------------------------------------
# Load pages to verify exact text location and section
pages_db = {}
with open("data/extracted/pages.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        p = json.loads(line)
        pages_db[p["page"]] = p

# Load traces
test_traces = {}
for s in ["A", "B", "C"]:
    with open(f"results/strategy_{s}_test_trace.json", "r", encoding="utf-8") as f:
        test_traces[s] = json.load(f)["traces"]

metadata_rows = []
for strat, traces in test_traces.items():
    for q_trace in traces:
        qid = q_trace["question_id"]
        filter_spec = q_trace.get("filter")
        
        for h in q_trace["hits"]:
            rank = h["rank"]
            cid = h["chunk_id"]
            page = h["page"]
            sec = h["section"]
            doc_id = h["document_id"]
            
            # Ground truth from pages_db
            page_data = pages_db.get(page)
            doc_id_valid = (doc_id == "ptbv_report")
            page_valid = (page_data is not None)
            section_valid = (page_data is not None and page_data["section"] == sec)
            
            # Text span verification: does chunk text actually appear on page?
            chunk_txt = h.get("text", "")
            text_norm = " ".join(chunk_txt.split())
            page_norm = " ".join(page_data["text"].split()) if page_data else ""
            span_valid = text_norm in page_norm
            
            # Filter compliance
            filter_required = filter_spec is not None
            if filter_required and "section" in filter_spec:
                filter_complied = (sec == filter_spec["section"])
            else:
                filter_complied = True # N/A or compliant
            
            overall_meta_valid = (doc_id_valid and page_valid and section_valid and span_valid)
            
            metadata_rows.append({
                "strategy": strat,
                "question_id": qid,
                "rank": rank,
                "chunk_id": cid,
                "document_id": doc_id,
                "doc_id_valid": doc_id_valid,
                "page": page,
                "page_valid": page_valid,
                "section": sec,
                "section_valid": section_valid,
                "text_span_verified": span_valid,
                "filter_required": filter_required,
                "required_filter": str(filter_spec),
                "filter_complied": filter_complied,
                "metadata_correct_mechanical": overall_meta_valid,
                "notes": "100% khớp nguồn trích xuất" if overall_meta_valid else "Lỗi khớp dữ liệu nguồn"
            })

meta_fieldnames = list(metadata_rows[0].keys())
with open(audit_dir / "metadata_audit.csv", "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=meta_fieldnames)
    writer.writeheader()
    writer.writerows(metadata_rows)

print("Metadata audit generated.")

# -------------------------------------------------------------------------
# 3. GROUNDING AUDIT (5 test queries × 3 strategies = 15 records)
# -------------------------------------------------------------------------
grounding_rows = []
grounding_text_guide = []

for strat, traces in test_traces.items():
    for q_trace in traces:
        qid = q_trace["question_id"]
        gold_page = q_trace["gold_page"]
        q_text = q_trace["question"]
        expected_ans = q_trace["expected_answer"]
        ev_quote = q_trace["evidence_quote"]
        h1 = q_trace["hit_at_1"]
        h3 = q_trace["evidence_hit_at_3"]
        
        top_hits = q_trace["hits"]
        top_pages = [h["page"] for h in top_hits]
        top_cids = [h["chunk_id"] for h in top_hits]
        
        # AI proposed score:
        # 0: no evidence; 1: partial evidence / missing conditions; 2: sufficient evidence to fully ground the answer
        if h1:
            ai_score = 2
            ai_rat = f"Rank 1 ({top_cids[0]}) chứa đầy đủ bằng chứng đã kiểm chứng hỗ trợ câu trả lời."
        elif h3:
            # Hit is in rank 2 or 3
            hit_rank = [h["rank"] for h in top_hits if h["is_hit"]][0]
            ai_score = 2
            ai_rat = f"Rank {hit_rank} ({top_cids[hit_rank-1]}) chứa đầy đủ bằng chứng đã kiểm chứng hỗ trợ câu trả lời."
        else:
            # Check if gold page was retrieved
            if gold_page in top_pages:
                ai_score = 1
                ai_rat = f"Trang gold {gold_page} xuất hiện trong top-3 nhưng chunk chưa chứa trọn vẹn evidence hoặc bị chia cắt."
            else:
                ai_score = 0
                ai_rat = f"Top-3 không chứa trang gold {gold_page} (các trang trả về: {top_pages})."
        
        grounding_rows.append({
            "strategy": strat,
            "question_id": qid,
            "gold_page": gold_page,
            "hit_at_1": h1,
            "evidence_hit_at_3": h3,
            "top1_chunk": top_cids[0] if len(top_cids) > 0 else "NONE",
            "top1_page": top_pages[0] if len(top_pages) > 0 else "NONE",
            "top2_chunk": top_cids[1] if len(top_cids) > 1 else "NONE",
            "top2_page": top_pages[1] if len(top_pages) > 1 else "NONE",
            "top3_chunk": top_cids[2] if len(top_cids) > 2 else "NONE",
            "top3_page": top_pages[2] if len(top_pages) > 2 else "NONE",
            "reviewer_type": "ai_proposed",
            "human_review_status": "pending",
            "ai_proposed_score": ai_score,
            "ai_rationale": ai_rat,
            "human_score": "",
            "human_notes": ""
        })
        
        grounding_text_guide.append({
            "strategy": strat,
            "question_id": qid,
            "question": q_text,
            "expected_answer": expected_ans,
            "evidence_quote": ev_quote,
            "gold_page": gold_page,
            "ai_proposed_score": ai_score,
            "ai_rationale": ai_rat,
            "retrieved_top_chunks": [
                {
                    "rank": h["rank"],
                    "chunk_id": h["chunk_id"],
                    "page": h["page"],
                    "section": h["section"],
                    "score": h["score"],
                    "is_hit": h["is_hit"],
                    "text_snippet": h["text"][:300] + ("..." if len(h["text"]) > 300 else "")
                }
                for h in top_hits
            ]
        })

grnd_fieldnames = list(grounding_rows[0].keys())
with open(audit_dir / "grounding_audit.csv", "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=grnd_fieldnames)
    writer.writeheader()
    writer.writerows(grounding_rows)

with open(local_text_dir / "grounding_review_guide.json", "w", encoding="utf-8") as f:
    json.dump(grounding_text_guide, f, ensure_ascii=False, indent=2)

print("Grounding audit generated successfully.")

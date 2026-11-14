import json
import csv
from pathlib import Path
import html

# Load data
with open("results/audit/local_text/coherence_review_guide.json", "r", encoding="utf-8") as f:
    coh_data = json.load(f)

with open("results/audit/local_text/grounding_review_guide.json", "r", encoding="utf-8") as f:
    grnd_data = json.load(f)

with open("results/audit/metadata_audit.csv", "r", encoding="utf-8") as f:
    meta_rows = list(csv.DictReader(f))

# Structure Coherence data by anchor_id (1..10)
coh_by_anchor = {}
for item in coh_data:
    aid = item["anchor_id"]
    if aid not in coh_by_anchor:
        coh_by_anchor[aid] = {
            "anchor_id": aid,
            "page": item["page"],
            "anchor_text": item["anchor_text"],
            "strategies": {}
        }
    coh_by_anchor[aid]["strategies"][item["strategy"]] = item

# Structure Grounding data by question_id (test_01..test_05)
grnd_by_qid = {}
for item in grnd_data:
    qid = item["question_id"]
    if qid not in grnd_by_qid:
        grnd_by_qid[qid] = {
            "question_id": qid,
            "question": item["question"],
            "expected_answer": item["expected_answer"],
            "evidence_quote": item["evidence_quote"],
            "gold_page": item["gold_page"],
            "gold_page_text": item.get("gold_page_text", ""),
            "strategies": {}
        }
    grnd_by_qid[qid]["strategies"][item["strategy"]] = item

html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bản Đánh Giá Audit Thủ Công — Day 06 Data Ingestion</title>
<style>
  :root {{
    --bg: #f8fafc;
    --card-bg: #ffffff;
    --text: #0f172a;
    --text-muted: #475569;
    --border: #e2e8f0;
    --primary: #2563eb;
    --primary-light: #eff6ff;
    --success: #16a34a;
    --success-light: #f0fdf4;
    --warning: #d97706;
    --warning-light: #fffbeb;
    --code-bg: #f1f5f9;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    padding: 24px;
    max-width: 1300px;
    margin: 0 auto;
  }}
  header {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 24px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  }}
  h1 {{ font-size: 24px; color: var(--text); margin-bottom: 8px; }}
  .meta-bar {{ font-size: 14px; color: var(--text-muted); display: flex; flex-wrap: wrap; gap: 16px; margin-top: 8px; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 6px; font-weight: 600; font-size: 12px; }}
  .badge-primary {{ background: var(--primary-light); color: var(--primary); }}
  .badge-warning {{ background: var(--warning-light); color: var(--warning); }}
  .badge-success {{ background: var(--success-light); color: var(--success); }}

  .notice-box {{
    background: var(--warning-light);
    border-left: 4px solid var(--warning);
    padding: 14px 18px;
    margin-top: 16px;
    border-radius: 0 8px 8px 0;
    font-size: 14px;
    color: #92400e;
  }}

  /* Tabs */
  .tabs {{
    display: flex;
    gap: 8px;
    margin-bottom: 20px;
    border-bottom: 2px solid var(--border);
    padding-bottom: 8px;
  }}
  .tab-btn {{
    background: none;
    border: none;
    padding: 10px 18px;
    font-size: 15px;
    font-weight: 600;
    color: var(--text-muted);
    cursor: pointer;
    border-radius: 8px;
    transition: all 0.2s;
  }}
  .tab-btn:hover {{ background: #e2e8f0; color: var(--text); }}
  .tab-btn.active {{ background: var(--primary); color: #fff; }}

  .tab-pane {{ display: none; }}
  .tab-pane.active {{ display: block; }}

  /* Cards */
  .card {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.03);
  }}
  .card-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--border);
    padding-bottom: 12px;
    margin-bottom: 16px;
  }}
  .card-title {{ font-size: 17px; font-weight: 700; color: #1e293b; }}

  /* Comparison Grid */
  .comparison-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-top: 14px;
  }}
  @media (max-width: 900px) {{
    .comparison-grid {{ grid-template-columns: 1fr; }}
  }}
  .chunk-box {{
    background: #fafafa;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 14px;
    font-size: 14px;
  }}
  .chunk-box-header {{
    display: flex;
    justify-content: space-between;
    font-weight: 600;
    font-size: 13px;
    margin-bottom: 8px;
    color: #334155;
  }}
  .text-content {{
    white-space: pre-wrap;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    padding: 12px;
    border-radius: 6px;
    font-family: Consolas, "Courier New", monospace;
    font-size: 13px;
    color: #1e293b;
    max-height: 280px;
    overflow-y: auto;
  }}
  .anchor-highlight {{
    background: #fef08a;
    padding: 1px 3px;
    border-radius: 3px;
    font-weight: 600;
  }}

  /* Rubric & Inputs */
  .rubric-box {{
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 13px;
    margin-bottom: 16px;
    color: #334155;
  }}
  .scoring-panel {{
    background: #f1f5f9;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 14px;
    margin-top: 16px;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 16px;
  }}
  .scoring-panel label {{ font-size: 14px; font-weight: 600; color: #1e293b; }}
  .score-select {{
    padding: 6px 12px;
    border-radius: 6px;
    border: 1px solid #94a3b8;
    font-weight: 600;
    font-size: 14px;
    background: #fff;
  }}
  .notes-input {{
    flex: 1;
    min-width: 250px;
    padding: 6px 12px;
    border-radius: 6px;
    border: 1px solid #94a3b8;
    font-size: 13px;
  }}

  /* AI collapsible details */
  details.ai-details {{
    margin-top: 12px;
    background: #f8fafc;
    border: 1px dashed #94a3b8;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
    color: #475569;
  }}
  details.ai-details summary {{
    cursor: pointer;
    font-weight: 600;
    color: #334155;
  }}
  details.ai-details p {{ margin-top: 6px; }}

  /* Tables */
  table.audit-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
    margin-top: 12px;
  }}
  table.audit-table th, table.audit-table td {{
    border: 1px solid var(--border);
    padding: 8px 12px;
    text-align: left;
  }}
  table.audit-table th {{
    background: #f1f5f9;
    font-weight: 600;
    color: #334155;
  }}
  table.audit-table tr:nth-child(even) {{ background: #fafafa; }}

  /* Export toolbar */
  .toolbar {{
    position: sticky;
    top: 12px;
    z-index: 100;
    background: #1e293b;
    color: #fff;
    padding: 12px 20px;
    border-radius: 8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
  }}
  .btn-export {{
    background: #2563eb;
    color: #fff;
    border: none;
    padding: 8px 16px;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 600;
    font-size: 13px;
    margin-left: 8px;
  }}
  .btn-export:hover {{ background: #1d4ed8; }}
</style>
</head>
<body>

<div class="toolbar">
  <div>
    <strong>Bản Chấm Audit Thủ Công — Local Review</strong>
    <span style="font-size: 12px; color: #94a3b8; margin-left: 12px;">Dành riêng cho sinh viên Phạm Lý Ngọc Đức</span>
  </div>
  <div>
    <button class="btn-export" onclick="exportAuditJSON()">Xuất Kết Quả (JSON)</button>
    <button class="btn-export" onclick="exportAuditCSV()">Xuất Kết Quả (CSV)</button>
  </div>
</div>

<header>
  <h1>Bảng Kiểm Tra & Đánh Giá Audit Thủ Công (Coherence, Grounding, Metadata)</h1>
  <div class="meta-bar">
    <span><strong>Học viên:</strong> Phạm Lý Ngọc Đức (2A202603991)</span>
    <span><strong>Lớp:</strong> L3B</span>
    <span><strong>Trạng thái:</strong> <span class="badge badge-warning">Đang chờ sinh viên duyệt (Pending)</span></span>
    <span><strong>Kiểm tra cơ học:</strong> <span class="badge badge-success">100% Hoàn thành</span></span>
  </div>
  <div class="notice-box">
    <strong>Nguyên tắc giảm thiểu thiên lệch:</strong> Toàn bộ điểm số và lý giải của AI được đặt trong các thẻ thu gọn (<code>&lt;details&gt;</code>) để bạn không bị dẫn dắt ý kiến trước khi chấm. Điểm số chính thức của bài làm chỉ được công nhận khi bạn trực tiếp nhập điểm (0, 1, 2) và xuất file hoặc điền trực tiếp vào các file CSV gốc.
  </div>
</header>

<div class="tabs">
  <button class="tab-btn active" onclick="switchTab('coherence')">1. Chunk Coherence (10 Anchors)</button>
  <button class="tab-btn" onclick="switchTab('grounding')">2. Grounding Quality (5 Test Queries)</button>
  <button class="tab-btn" onclick="switchTab('metadata')">3. Metadata & Filter Audit (45 Hits)</button>
</div>

<!-- ============================================================== -->
<!-- TAB 1: COHERENCE                                               -->
<!-- ============================================================== -->
<div id="tab-coherence" class="tab-pane active">
  <div class="rubric-box">
    <strong>Thang điểm Coherence (Tính mạch lạc của Chunk — 0 đến 2):</strong><br>
    • <strong>0 điểm:</strong> Bị cắt ngang giữa ý, thiếu chủ thể hoặc câu văn làm người đọc không thể hiểu trọn vẹn.<br>
    • <strong>1 điểm:</strong> Hiểu được một phần nội dung nhưng bị đứt đoạn ở đầu/cuối chunk làm thiếu ngữ cảnh liền mạch.<br>
    • <strong>2 điểm:</strong> Tự hiểu trọn vẹn, cấu trúc đoạn và câu hoàn chỉnh, giữ nguyên ngữ cảnh học thuật.
  </div>
"""

for aid, cdata in coh_by_anchor.items():
    strat_a = cdata["strategies"].get("A", {})
    strat_b = cdata["strategies"].get("B", {})
    
    txt_a = html.escape(strat_a.get("chunk_text", "Không tìm thấy chunk"))
    txt_b = html.escape(strat_b.get("chunk_text", "Không tìm thấy chunk"))
    anchor_esc = html.escape(cdata["anchor_text"])
    
    html_content += f"""
  <div class="card" id="card-coh-{aid}">
    <div class="card-header">
      <div class="card-title">Anchor #{aid} (Trang PDF: {cdata['page']})</div>
      <div><span class="badge badge-primary">Quy tắc: Chunk đầu tiên trên trang chứa câu neo</span></div>
    </div>
    
    <div style="font-size: 14px; margin-bottom: 10px;">
      <strong>Câu Neo Nguồn Đã Khóa (Anchor Text):</strong><br>
      <div style="background: #fffbeb; border: 1px solid #fde68a; padding: 10px; border-radius: 6px; margin-top: 4px; font-weight: 500;">
        "{anchor_esc}"
      </div>
    </div>

    <div class="comparison-grid">
      <!-- Strategy A -->
      <div class="chunk-box">
        <div class="chunk-box-header">
          <span>Chiến lược A (Fixed-size 500)</span>
          <span>Chunk: <code>{strat_a.get('chunk_id')}</code> ({len(strat_a.get('chunk_text', ''))} ký tự)</span>
        </div>
        <div class="text-content">{txt_a}</div>
        <div class="scoring-panel">
          <label for="coh-score-a-{aid}">Điểm bạn chấm (A):</label>
          <select class="score-select" id="coh-score-a-{aid}" data-type="coherence" data-strategy="A" data-id="{aid}">
            <option value="">-- Chưa chấm --</option>
            <option value="0">0 - Mất ý/ngắt giữa chừng</option>
            <option value="1">1 - Hiểu một phần, thiếu ngữ cảnh</option>
            <option value="2">2 - Mạch lạc, tự hiểu trọn vẹn</option>
          </select>
          <input type="text" class="notes-input" id="coh-notes-a-{aid}" placeholder="Ghi chú đánh giá của bạn cho A (tùy chọn)...">
        </div>
        <details class="ai-details">
          <summary>🔍 Xem gợi ý của AI (Bấm để mở)</summary>
          <p><strong>Điểm AI đề xuất:</strong> {strat_a.get('ai_proposed_score')}/2</p>
          <p><strong>Lý giải của AI:</strong> {html.escape(strat_a.get('ai_rationale', ''))}</p>
        </details>
      </div>

      <!-- Strategy B and C -->
      <div class="chunk-box">
        <div class="chunk-box-header">
          <span>Chiến lược B & C (by_paragraph)</span>
          <span>Chunk: <code>{strat_b.get('chunk_id')}</code> ({len(strat_b.get('chunk_text', ''))} ký tự)</span>
        </div>
        <div style="font-size: 11px; color: #64748b; margin-bottom: 6px;">*Chiến lược C tái sử dụng 100% chunk của B nên điểm chấm áp dụng chung cho cả B và C.</div>
        <div class="text-content">{txt_b}</div>
        <div class="scoring-panel">
          <label for="coh-score-b-{aid}">Điểm bạn chấm (B/C):</label>
          <select class="score-select" id="coh-score-b-{aid}" data-type="coherence" data-strategy="B" data-id="{aid}">
            <option value="">-- Chưa chấm --</option>
            <option value="0">0 - Mất ý/ngắt giữa chừng</option>
            <option value="1">1 - Hiểu một phần, thiếu ngữ cảnh</option>
            <option value="2">2 - Mạch lạc, tự hiểu trọn vẹn</option>
          </select>
          <input type="text" class="notes-input" id="coh-notes-b-{aid}" placeholder="Ghi chú đánh giá của bạn cho B/C (tùy chọn)...">
        </div>
        <details class="ai-details">
          <summary>🔍 Xem gợi ý của AI (Bấm để mở)</summary>
          <p><strong>Điểm AI đề xuất:</strong> {strat_b.get('ai_proposed_score')}/2</p>
          <p><strong>Lý giải của AI:</strong> {html.escape(strat_b.get('ai_rationale', ''))}</p>
        </details>
      </div>
    </div>
  </div>
"""

html_content += """
</div>

<!-- ============================================================== -->
<!-- TAB 2: GROUNDING                                               -->
<!-- ============================================================== -->
<div id="tab-grounding" class="tab-pane">
  <div class="rubric-box">
    <strong>Thang điểm Grounding Quality (Độ đủ của bằng chứng truy xuất — 0 đến 2):</strong><br>
    • <strong>0 điểm:</strong> Không có bằng chứng nào liên quan đến câu trả lời trong top-3.<br>
    • <strong>1 điểm:</strong> Có bằng chứng trên trang gold nhưng bị thiếu điều kiện hoặc bị cắt xén làm mất ngữ cảnh (hoặc nhiều chunk hợp lại chưa hoàn chỉnh).<br>
    • <strong>2 điểm:</strong> Toàn bộ top-3 cung cấp đầy đủ thông tin để trả lời trọn vẹn câu hỏi và truy xuất nguồn.<br>
    <em>Lưu ý quan trọng: Grounding xem xét trên <strong>hợp bằng chứng của cả top-3</strong>. Vì vậy ở Chiến lược A với câu test_02, dù Evidence Hit@3 đơn chunk là False do bị cắt đôi, nhưng nếu cả 2 chunk rank 1 và rank 3 hợp lại đủ bằng chứng, bạn vẫn có thể cân nhắc chấm điểm phù hợp sau khi đọc văn bản thực tế.</em>
  </div>
"""

for qid, gdata in grnd_by_qid.items():
    q_esc = html.escape(gdata["question"])
    ans_esc = html.escape(gdata["expected_answer"])
    ev_esc = html.escape(gdata["evidence_quote"])
    gold_page_txt_esc = html.escape(gdata.get("gold_page_text", ""))

    html_content += f"""
  <div class="card" id="card-grnd-{qid}">
    <div class="card-header">
      <div class="card-title">Câu hỏi {qid.upper()} (Trang Gold: {gdata['gold_page']})</div>
      <div><span class="badge badge-primary">Tập Test Độc Lập</span></div>
    </div>

    <div style="font-size: 14px; margin-bottom: 14px; background: #f8fafc; padding: 12px; border-radius: 8px; border: 1px solid #e2e8f0;">
      <p style="margin-bottom: 6px;"><strong>Câu hỏi:</strong> {q_esc}</p>
      <p style="margin-bottom: 6px;"><strong>Đáp án chuẩn (Expected Answer):</strong> <span style="color: #0369a1; font-weight: 600;">{ans_esc}</span></p>
      <p><strong>Bằng chứng chuẩn (Evidence Quote):</strong> <span style="background: #fef08a; padding: 2px 4px; border-radius: 3px;">{ev_esc}</span></p>
    </div>

    <details style="margin-bottom: 16px; background: #fff; border: 1px solid #cbd5e1; padding: 8px 12px; border-radius: 6px;">
      <summary style="font-weight: 600; cursor: pointer; color: #475569;">📄 Xem toàn bộ văn bản gốc trang Gold ({gdata['gold_page']}) để đối chiếu</summary>
      <div class="text-content" style="margin-top: 8px; max-height: 220px;">{gold_page_txt_esc}</div>
    </details>
"""

    for strat in ["A", "B", "C"]:
        s_item = gdata["strategies"].get(strat, {})
        top_chunks = s_item.get("retrieved_top_chunks", [])
        
        strat_desc = "Chiến lược A (Fixed-size 500, Không lọc)" if strat == "A" else ("Chiến lược B (by_paragraph, Không lọc)" if strat == "B" else "Chiến lược C (by_paragraph + Lọc Metadata section)")

        html_content += f"""
    <div style="margin-top: 16px; border: 1px solid #cbd5e1; border-radius: 8px; padding: 14px; background: #fafafa;">
      <div style="font-weight: 700; font-size: 15px; color: #1e293b; margin-bottom: 8px;">
        {strat_desc}
      </div>
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 10px;">
"""
        for ch in top_chunks:
            hit_badge = '<span class="badge badge-success">Hit đơn chunk</span>' if ch.get("is_hit") else '<span class="badge badge-warning">Không đủ bằng chứng</span>'
            c_text_esc = html.escape(ch.get("text", ch.get("text_snippet", "")))
            html_content += f"""
        <div style="background: #fff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px; font-size: 13px;">
          <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-weight: 600;">
            <span>Rank {ch['rank']} (Trang {ch['page']}, {ch['section']})</span>
            <span>Cosine: {ch['score']:.4f}</span>
          </div>
          <div style="font-size: 11px; color: #64748b; margin-bottom: 6px;">ID: <code>{ch['chunk_id']}</code> | {hit_badge}</div>
          <div class="text-content" style="max-height: 180px; font-size: 12px;">{c_text_esc}</div>
        </div>
"""

        html_content += f"""
      </div>
      <div class="scoring-panel">
        <label for="grnd-score-{strat.lower()}-{qid}">Điểm bạn chấm Grounding ({strat}):</label>
        <select class="score-select" id="grnd-score-{strat.lower()}-{qid}" data-type="grounding" data-strategy="{strat}" data-id="{qid}">
          <option value="">-- Chưa chấm --</option>
          <option value="0">0 - Không có bằng chứng đủ</option>
          <option value="1">1 - Có nhưng thiếu điều kiện/ngữ cảnh</option>
          <option value="2">2 - Đủ bằng chứng hoàn chỉnh để trả lời</option>
        </select>
        <input type="text" class="notes-input" id="grnd-notes-{strat.lower()}-{qid}" placeholder="Ghi chú đánh giá của bạn cho {strat} (tùy chọn)...">
      </div>
      <details class="ai-details">
        <summary>🔍 Xem gợi ý của AI cho {strat} (Bấm để mở)</summary>
        <p><strong>Điểm AI đề xuất:</strong> {s_item.get('ai_proposed_score')}/2</p>
        <p><strong>Lý giải của AI:</strong> {html.escape(s_item.get('ai_rationale', ''))}</p>
      </details>
    </div>
"""

    html_content += """
  </div>
"""

html_content += """
</div>

<!-- ============================================================== -->
<!-- TAB 3: METADATA AUDIT                                          -->
<!-- ============================================================== -->
<div id="tab-metadata" class="tab-pane">
  <div class="rubric-box">
    <strong>Bảng Kiểm Tra Cơ Học Metadata & Tuân Thủ Bộ Lọc (45 Hits Test):</strong><br>
    • <strong>Kiểm tra cơ học (100% khớp nguồn):</strong> Đối chiếu document_id, trang, section và vị trí văn bản thực tế trong văn bản trích xuất của pypdf.<br>
    • <strong>Tuân thủ bộ lọc (Filter Compliance):</strong> Kiểm tra xem kết quả trả về có nằm đúng chương yêu cầu của câu hỏi hay không.<br>
    <em>Lưu ý: Bảng này là kết quả kiểm tra cơ học của hệ thống, không thay thế việc bạn rà soát lại nếu cần.</em>
  </div>

  <div class="card">
    <div class="card-header">
      <div class="card-title">Thống kê Tuân thủ Filter Metadata trên 2 câu Test có Filter (test_02: chuong_4, test_05: chuong_5)</div>
    </div>
    <div style="font-size: 14px; line-height: 1.8;">
      • <strong>Chiến lược A (Không áp dụng bộ lọc):</strong> 3/6 hits đúng chương (50.0%) — Có 3 hits bị lọt sang Chương 3.<br>
      • <strong>Chiến lược B (Không áp dụng bộ lọc):</strong> 4/6 hits đúng chương (66.7%) — Có 2 hits bị lọt sang Chương 3.<br>
      • <strong>Chiến lược C (Áp dụng bộ lọc section):</strong> <span style="color: #16a34a; font-weight: 700;">6/6 hits đúng chương (100.0%)</span> — 100% kết quả nằm đúng chương yêu cầu.<br>
      • <strong>Ở cấp câu hỏi:</strong> Chiến lược C đảm bảo 2/2 câu có filter (100%) sạch hoàn toàn top-3, trong khi A và B chỉ đạt 0/2 câu sạch hoàn toàn (do đều bị lọt chunk ngoại lai).
    </div>
  </div>

  <div class="card">
    <div class="card-header">
      <div class="card-title">Danh sách chi tiết 45 kết quả Top-3 Test</div>
    </div>
    <div style="overflow-x: auto;">
      <table class="audit-table">
        <thead>
          <tr>
            <th>Chiến lược</th>
            <th>Câu hỏi</th>
            <th>Rank</th>
            <th>Chunk ID</th>
            <th>Trang</th>
            <th>Section</th>
            <th>Khớp Nguồn (Cơ học)</th>
            <th>Yêu cầu Lọc</th>
            <th>Tuân thủ Lọc</th>
          </tr>
        </thead>
        <tbody>
"""

for row in meta_rows:
    mech_badge = '<span class="badge badge-success">Đúng 100%</span>' if row["metadata_correct_mechanical"] == "True" else '<span class="badge badge-warning">Lỗi</span>'
    filt_badge = '<span class="badge badge-success">Tuân thủ</span>' if row["filter_complied"] == "True" else '<span class="badge badge-warning">Lạc đề</span>'
    if row["filter_required"] != "True":
        filt_badge = '<span style="color:#64748b;">N/A (không lọc)</span>'
    
    html_content += f"""
          <tr>
            <td><strong>{row['strategy']}</strong></td>
            <td><code>{row['question_id']}</code></td>
            <td>{row['rank']}</td>
            <td><code>{row['chunk_id']}</code></td>
            <td>{row['page']}</td>
            <td>{row['section']}</td>
            <td>{mech_badge}</td>
            <td>{row['required_filter']}</td>
            <td>{filt_badge}</td>
          </tr>
"""

html_content += """
        </tbody>
      </table>
    </div>
  </div>
</div>

<script>
function switchTab(tabId) {
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));
  
  if (tabId === 'coherence') {
    document.querySelectorAll('.tab-btn')[0].classList.add('active');
    document.getElementById('tab-coherence').classList.add('active');
  } else if (tabId === 'grounding') {
    document.querySelectorAll('.tab-btn')[1].classList.add('active');
    document.getElementById('tab-grounding').classList.add('active');
  } else if (tabId === 'metadata') {
    document.querySelectorAll('.tab-btn')[2].classList.add('active');
    document.getElementById('tab-metadata').classList.add('active');
  }
}

function collectScores() {
  const scores = {
    coherence: [],
    grounding: []
  };
  
  document.querySelectorAll('select[data-type="coherence"]').forEach(sel => {
    const aid = sel.getAttribute('data-id');
    const strat = sel.getAttribute('data-strategy');
    const scoreVal = sel.value;
    const notesInput = document.getElementById(`coh-notes-${strat.toLowerCase()}-${aid}`);
    const notes = notesInput ? notesInput.value : '';
    
    scores.coherence.push({
      anchor_id: aid,
      strategy: strat,
      human_score: scoreVal,
      human_notes: notes
    });
  });

  document.querySelectorAll('select[data-type="grounding"]').forEach(sel => {
    const qid = sel.getAttribute('data-id');
    const strat = sel.getAttribute('data-strategy');
    const scoreVal = sel.value;
    const notesInput = document.getElementById(`grnd-notes-${strat.toLowerCase()}-${qid}`);
    const notes = notesInput ? notesInput.value : '';
    
    scores.grounding.push({
      question_id: qid,
      strategy: strat,
      human_score: scoreVal,
      human_notes: notes
    });
  });

  return scores;
}

function exportAuditJSON() {
  const data = collectScores();
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'human_audit_scores.json';
  a.click();
  URL.revokeObjectURL(url);
}

function exportAuditCSV() {
  const data = collectScores();
  let csvContent = "category,id,strategy,human_score,human_notes\\n";
  
  data.coherence.forEach(r => {
    csvContent += `coherence,${r.anchor_id},${r.strategy},"${r.human_score}","${(r.human_notes||'').replace(/"/g, '""')}"\\n`;
  });
  data.grounding.forEach(r => {
    csvContent += `grounding,${r.question_id},${r.strategy},"${r.human_score}","${(r.human_notes||'').replace(/"/g, '""')}"\\n`;
  });

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'human_audit_scores.csv';
  a.click();
  URL.revokeObjectURL(url);
}
</script>

</body>
</html>
"""

output_path = Path("results/audit/local_text/review.html")
output_path.parent.mkdir(parents=True, exist_ok=True)
with open(output_path, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"Generated {output_path} successfully ({len(html_content)} bytes).")

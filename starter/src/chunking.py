"""Implement fixed-size and structure-aware chunking."""
import re
from .models import Chunk, DocumentPage


def fixed_size(page: DocumentPage, size: int = 500, overlap: int = 50) -> list[Chunk]:
    """Split page text into overlapping windows of fixed characters strictly within page boundaries.
    
    Validates parameters, retains page metadata and produces stable chunk IDs.
    """
    if size <= 0:
        raise ValueError(f"chunk size must be positive, got {size}")
    if overlap < 0 or overlap >= size:
        raise ValueError(f"overlap must be in [0, size), got overlap={overlap}, size={size}")

    text = page.text
    if not text or not text.strip():
        return []

    chunks: list[Chunk] = []
    step = size - overlap
    start = 0
    chunk_idx = 0

    while start < len(text):
        end = min(start + size, len(text))
        chunk_text = text[start:end]
        if chunk_text.strip():
            chunk_id = f"{page.document_id}_p{page.page:03d}_c{chunk_idx:03d}"
            meta = dict(page.metadata)
            meta.update({
                "strategy": "A",
                "start_char": start,
                "end_char": end,
                "char_count": len(chunk_text),
                "chunk_index": chunk_idx,
            })
            chunk = Chunk(
                chunk_id=chunk_id,
                document_id=page.document_id,
                source=page.source,
                page=page.page,
                text=chunk_text,
                metadata=meta,
            )
            chunks.append(chunk)
            chunk_idx += 1

        if end >= len(text):
            break
        start += step

    return chunks


def by_paragraph(page: DocumentPage, max_size: int = 800) -> list[Chunk]:
    """Split page text into structure-aware paragraph chunks bounded by max_size.
    
    Identifies paragraph boundaries, bullet lists, and headings. Large blocks are
    split cleanly on sentence boundaries. Small leading headers or trailing fragments
    are merged to preserve semantic coherence.
    """
    if max_size <= 0:
        raise ValueError(f"max_size must be positive, got {max_size}")

    text = page.text
    if not text or not text.strip():
        return []

    # 1. Identify raw paragraph blocks with character spans in page.text
    # Blocks are non-whitespace segments separated by \n\s*\n+
    matches = list(re.finditer(r'(?:[^\n]|\n(?!\s*\n))+', text))
    spans: list[tuple[int, int]] = []
    for m in matches:
        s, e = m.start(), m.end()
        sub = text[s:e]
        leading_ws = len(sub) - len(sub.lstrip())
        trailing_ws = len(sub) - len(sub.rstrip())
        actual_s = s + leading_ws
        actual_e = e - trailing_ws
        if actual_e > actual_s:
            spans.append((actual_s, actual_e))

    if not spans:
        return []

    # If first block is just a standalone page number (e.g. "7", "18"), merge span with block 1
    if len(spans) > 1:
        first_txt = text[spans[0][0]:spans[0][1]]
        if first_txt.isdigit() and len(first_txt) <= 3:
            spans[1] = (spans[0][0], spans[1][1])
            spans.pop(0)

    # 2. Group spans into coherent chunks bounded by max_size
    chunk_spans: list[tuple[int, int]] = []
    curr_spans: list[tuple[int, int]] = []

    for sp in spans:
        candidate_len = sp[1] - (curr_spans[0][0] if curr_spans else sp[0])
        if candidate_len <= max_size:
            curr_spans.append(sp)
        else:
            if curr_spans:
                chunk_spans.append((curr_spans[0][0], curr_spans[-1][1]))
                curr_spans = []

            block_len = sp[1] - sp[0]
            if block_len <= max_size:
                curr_spans.append(sp)
            else:
                # Oversized block: split by sentence boundaries within text[sp[0]:sp[1]]
                block_txt = text[sp[0]:sp[1]]
                s_matches = list(re.finditer(r'(?:[^\n.!?]|\n(?![●•❖\-\+]))+[.!?]?', block_txt))
                curr_sent_spans: list[tuple[int, int]] = []
                for sm in s_matches:
                    abs_s = sp[0] + sm.start()
                    abs_e = sp[0] + sm.end()
                    c_len = abs_e - (curr_sent_spans[0][0] if curr_sent_spans else abs_s)
                    if c_len <= max_size:
                        curr_sent_spans.append((abs_s, abs_e))
                    else:
                        if curr_sent_spans:
                            chunk_spans.append((curr_sent_spans[0][0], curr_sent_spans[-1][1]))
                            curr_sent_spans = []
                        curr_sent_spans.append((abs_s, abs_e))
                if curr_sent_spans:
                    curr_spans.append((curr_sent_spans[0][0], curr_sent_spans[-1][1]))

    if curr_spans:
        last_s = curr_spans[0][0]
        last_e = curr_spans[-1][1]
        last_len = last_e - last_s
        if last_len < 120 and chunk_spans and (last_e - chunk_spans[-1][0]) <= int(max_size * 1.25):
            chunk_spans[-1] = (chunk_spans[-1][0], last_e)
        else:
            chunk_spans.append((last_s, last_e))

    # 3. Create Chunk objects
    chunks: list[Chunk] = []
    for chunk_idx, (start, end) in enumerate(chunk_spans):
        chunk_text = text[start:end]
        if not chunk_text.strip():
            continue
        chunk_id = f"{page.document_id}_p{page.page:03d}_b{chunk_idx:03d}"
        meta = dict(page.metadata)
        meta.update({
            "strategy": "B",
            "start_char": start,
            "end_char": end,
            "char_count": len(chunk_text),
            "chunk_index": chunk_idx,
        })
        chunks.append(
            Chunk(
                chunk_id=chunk_id,
                document_id=page.document_id,
                source=page.source,
                page=page.page,
                text=chunk_text,
                metadata=meta,
            )
        )

    return chunks

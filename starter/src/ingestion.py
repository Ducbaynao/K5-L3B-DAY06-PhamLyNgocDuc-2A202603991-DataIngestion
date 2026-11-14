"""Read and normalize source data."""
import json
from pathlib import Path
import re
from typing import Any
import unicodedata
import pypdf

try:
    from .models import DocumentPage
except ImportError:
    from starter.src.models import DocumentPage

WATERMARK_PATTERNS = [
    re.compile(r"^downloaded by\b.*", re.IGNORECASE),
    re.compile(r"^scan to open on\b.*", re.IGNORECASE),
    re.compile(r"^studocu\b.*", re.IGNORECASE),
    re.compile(r"^lomoarcpsd\|\d+", re.IGNORECASE),
]


def get_repo_root() -> Path:
    """Return repository root path reliably."""
    return Path(__file__).resolve().parent.parent.parent


def get_section_for_page(page_num: int) -> str:
    """Return section identifier based on verified chapter boundaries."""
    if 18 <= page_num <= 36:
        return "chuong_1"
    elif 37 <= page_num <= 51:
        return "chuong_2"
    elif 52 <= page_num <= 73:
        return "chuong_3"
    elif 74 <= page_num <= 93:
        return "chuong_4"
    elif 94 <= page_num <= 101:
        return "chuong_5"
    elif page_num < 18:
        return "mo_dau"
    else:
        return "ket_luan_va_phu_luc"


def normalize_text(text: str) -> str:
    """Normalize Unicode (NFC), remove Studocu/watermark artifacts, and clean whitespace
    while preserving paragraph and line structure.
    """
    if not text:
        return ""

    text = unicodedata.normalize("NFC", text)
    lines: list[str] = []
    for line in text.splitlines():
        line_str = line.strip()
        if not line_str:
            # preserve at most one blank line between content blocks
            if lines and lines[-1] != "":
                lines.append("")
            continue

        # Skip watermark / metadata lines
        if any(pat.match(line_str) for pat in WATERMARK_PATTERNS):
            continue

        # Normalize internal horizontal spaces/tabs into a single space
        norm_line = re.sub(r"[ \t]+", " ", line_str)
        lines.append(norm_line)

    # Trim leading and trailing empty lines
    while lines and lines[0] == "":
        lines.pop(0)
    while lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines)


def load_pdf(
    path: Path,
    document_id: str = "ptbv_report",
    source: str = "data/raw/ptbv_report.pdf",
    pages_to_load: list[dict[str, Any]] | None = None,
    start_page: int | None = 18,
    end_page: int | None = 101,
) -> list[DocumentPage]:
    """Extract each physical page; keep 1-based page number, section and metadata.
    0-based indexing is applied strictly once when reading from pypdf.
    """
    reader = pypdf.PdfReader(str(path))
    total_pages = len(reader.pages)

    doc_pages: list[DocumentPage] = []

    if pages_to_load:
        for p_info in pages_to_load:
            page_num = p_info["page"]
            idx = page_num - 1
            raw_text = reader.pages[idx].extract_text() or ""
            norm_text = normalize_text(raw_text)
            section = p_info.get("section", get_section_for_page(page_num))
            meta = {
                "section": section,
                "char_count": len(norm_text),
                "physical_page": page_num,
                "is_empty": len(norm_text) == 0,
            }
            doc_page = DocumentPage(
                document_id=document_id,
                source=source,
                page=page_num,
                text=norm_text,
                metadata=meta,
            )
            doc_pages.append(doc_page)
    else:
        first_page = start_page if start_page is not None else 1
        last_page = end_page if end_page is not None else total_pages
        for page_num in range(first_page, last_page + 1):
            idx = page_num - 1
            raw_text = reader.pages[idx].extract_text() or ""
            norm_text = normalize_text(raw_text)
            section = get_section_for_page(page_num)
            meta = {
                "section": section,
                "char_count": len(norm_text),
                "physical_page": page_num,
                "is_empty": len(norm_text) == 0,
            }
            doc_page = DocumentPage(
                document_id=document_id,
                source=source,
                page=page_num,
                text=norm_text,
                metadata=meta,
            )
            doc_pages.append(doc_page)

    return doc_pages


def load_corpus_from_manifest(manifest_path: Path | None = None) -> list[DocumentPage]:
    """Load corpus driven directly by data/manifest.json."""
    repo_root = get_repo_root()
    if manifest_path is None:
        manifest_path = repo_root / "data" / "manifest.json"

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    pdf_rel_path = manifest.get("source_path_or_url", "data/raw/ptbv_report.pdf")
    pdf_path = repo_root / pdf_rel_path
    if not pdf_path.exists():
        raise FileNotFoundError(f"Source PDF not found at {pdf_path}")

    return load_pdf(
        path=pdf_path,
        document_id=manifest["source_id"],
        source=pdf_rel_path,
        pages_to_load=manifest.get("pages"),
    )


def save_pages_jsonl(pages: list[DocumentPage], output_path: Path) -> None:
    """Save normalized pages into a JSONL file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for page in pages:
            record = {
                "document_id": page.document_id,
                "source": page.source,
                "page": page.page,
                "section": page.metadata.get("section", ""),
                "text": page.text,
                "metadata": page.metadata,
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> None:
    repo_root = get_repo_root()
    manifest_path = repo_root / "data" / "manifest.json"
    output_path = repo_root / "data" / "extracted" / "pages.jsonl"

    pages = load_corpus_from_manifest(manifest_path)
    save_pages_jsonl(pages, output_path)
    print(f"Extracted and saved {len(pages)} pages to {output_path}")
    print(f"Total characters across {len(pages)} pages: {sum(len(p.text) for p in pages)}")


if __name__ == "__main__":
    main()

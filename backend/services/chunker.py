"""
chunker.py
----------
Phase 2/3 of the roadmap: turn raw page text into retrievable chunks, each
tagged with page number and a best-guess section heading, e.g.:

    Chunk 1  Page: 4   Section: Hospitalisation   Text: ...
    Chunk 2  Page: 7   Section: Waiting Period    Text: ...

A lightweight heuristic is used to detect section headings (short, mostly
capitalised / title-case lines, or lines matching known policy vocabulary)
instead of hard-coding layouts per insurer, matching the roadmap's guidance
to keep field/structure detection general rather than insurer-specific.
"""
import re

SECTION_KEYWORDS = [
    "hospitalisation", "hospitalization", "day care", "waiting period",
    "exclusions", "exclusion", "sub-limit", "sub limit", "room rent",
    "co-payment", "copayment", "deductible", "sum insured", "pre-existing",
    "claim procedure", "claim conditions", "eligibility", "coverage",
    "definitions", "grace period", "renewal", "cancellation", "cashless",
    "network hospital", "ambulance", "maternity", "critical illness",
    "pre-hospitalisation", "post-hospitalisation", "no claim bonus",
]

HEADING_RE = re.compile(r"^[A-Z0-9][A-Za-z0-9 ,&/\-()]{2,60}$")


def _guess_section(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) > 70:
        return False
    lower = stripped.lower()
    if any(k in lower for k in SECTION_KEYWORDS) and len(stripped.split()) <= 8:
        return True
    # Title-case / all-caps short heading lines (common in policy PDFs)
    words = stripped.split()
    if 1 <= len(words) <= 8 and HEADING_RE.match(stripped):
        capitalized = sum(1 for w in words if w[:1].isupper())
        if capitalized / len(words) >= 0.6:
            return True
    return False


def chunk_pages(pages, max_chunk_chars=900):
    """
    Input: list of {"page": n, "text": "..."} from pdf_parser.extract_pages
    Output: list of chunks: {"id", "page", "section", "text"}
    """
    chunks = []
    chunk_id = 1
    current_section = "General"

    for page in pages:
        text = page["text"]
        if not text:
            continue
        lines = [l for l in text.split("\n") if l.strip()]

        buffer = []

        def flush():
            nonlocal chunk_id, buffer
            if buffer:
                chunk_text = "\n".join(buffer).strip()
                if chunk_text:
                    chunks.append({
                        "id": chunk_id,
                        "page": page["page"],
                        "section": current_section,
                        "text": chunk_text,
                    })
                    chunk_id += 1
                buffer = []

        for line in lines:
            if _guess_section(line):
                # New section heading found -> flush what we had, start new section
                flush()
                current_section = line.strip()
                continue
            buffer.append(line)
            if sum(len(b) for b in buffer) >= max_chunk_chars:
                flush()
        flush()

    if not chunks:
        # Extremely short / scanned doc fallback
        for page in pages:
            if page["text"]:
                chunks.append({
                    "id": len(chunks) + 1,
                    "page": page["page"],
                    "section": "General",
                    "text": page["text"],
                })
    return chunks

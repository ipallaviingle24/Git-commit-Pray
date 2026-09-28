"""
pdf_parser.py
-------------
Phase 2 of the roadmap: "PDF -> Extract text -> Page numbers -> Chunks".

Uses pdfplumber to pull text page-by-page (page numbers are essential later
for citations). Falls back gracefully if a page has no extractable text
(e.g. a scanned page) -- in production this is where OCR (pytesseract /
pdf2image) would be plugged in, per the roadmap's "Fallback: OCR" note.
"""
import pdfplumber


def extract_pages(pdf_path: str):
    """Returns a list of dicts: [{"page": 1, "text": "..."}, ...]"""
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            pages.append({
                "page": i,
                "text": text.strip(),
                "is_scanned": len(text.strip()) < 20,  # heuristic flag
            })
    return pages

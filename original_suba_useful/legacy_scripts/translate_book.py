#!/usr/bin/env python3
"""OCR scanned PDF -> segment into chapter text files.

Phase 1: OCR each page to text (English) and write ocr/pages/page-XXXX.txt
Phase 2: naive chapter boundary detection (CHAPTER/Chapter + roman/number) -> chapters/index.json

Translation + PDF typesetting is handled in later phases.
"""

import io
import json
import os
import re
import sys
from pathlib import Path

import fitz  # PyMuPDF
import pytesseract
from PIL import Image

PDF_PATH = os.path.expanduser("~/Desktop/suba/otherworldscomic0000cyra_1.pdf")
OUT_DIR = Path(os.path.expanduser("~/Desktop/suba/out"))
PAGES_DIR = OUT_DIR / "ocr" / "pages"

CHAPTER_RE = re.compile(r"\b(CHAPTER|Chapter)\b\s*([0-9IVXLC]+)?", re.IGNORECASE)


def ocr_page(page) -> str:
    # moderate DPI for speed; we can re-render higher later if needed
    pix = page.get_pixmap(matrix=fitz.Matrix(1.2, 1.2))
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    text = pytesseract.image_to_string(img, lang="eng")
    # normalize whitespace but keep paragraph breaks
    lines = [ln.rstrip() for ln in text.splitlines()]
    return "\n".join(lines).strip() + "\n"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PAGES_DIR.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(PDF_PATH)
    n = doc.page_count

    chapter_starts = []  # list of {page, titleLine}

    for i in range(n):
        out_path = PAGES_DIR / f"page-{i+1:04d}.txt"
        if out_path.exists() and out_path.stat().st_size > 20:
            text = out_path.read_text("utf-8", errors="ignore")
        else:
            text = ocr_page(doc.load_page(i))
            out_path.write_text(text, "utf-8")

        # lightweight chapter detection
        preview = " ".join(text.split())[:200]
        m = CHAPTER_RE.search(preview)
        if m:
            chapter_starts.append({"page": i + 1, "match": m.group(0), "preview": preview})

        if (i + 1) % 10 == 0:
            print(f"OCR {i+1}/{n}")
            sys.stdout.flush()

    # Build chapter ranges (best-effort)
    chapter_starts = sorted({c["page"]: c for c in chapter_starts}.values(), key=lambda x: x["page"])
    chapters = []
    for idx, c in enumerate(chapter_starts):
        start = c["page"]
        end = (chapter_starts[idx + 1]["page"] - 1) if idx + 1 < len(chapter_starts) else n
        chapters.append({
            "chapterIndex": idx + 1,
            "startPage": start,
            "endPage": end,
            "hint": c,
        })

    (OUT_DIR / "chapters").mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "chapters" / "index.json").write_text(json.dumps({
        "pdf": PDF_PATH,
        "pages": n,
        "chapterCandidates": chapter_starts,
        "chapters": chapters,
    }, indent=2), "utf-8")

    print(f"Done. OCR pages in {PAGES_DIR}.")
    print(f"Chapter index: {OUT_DIR / 'chapters' / 'index.json'}")


if __name__ == "__main__":
    main()

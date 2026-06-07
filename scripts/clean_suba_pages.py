#!/usr/bin/env python3
"""Build clean English page text files for the Suba translation workflow.

The script uses the existing OCR page files when they are good, because they
preserve paragraph layout better than the PDF's hidden text layer. It falls
back to PDF text for missing/special pages.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

import fitz


SOURCE_PDF = Path("/Users/miikka/Downloads/otherworldscomic0000cyra_1.pdf")
SOURCE_OCR_DIR = Path("/Users/miikka/Desktop/suba/out/ocr/pages")

BOOK_PAGE_START = 11
BOOK_PAGE_END = 252
SKIP_PDF_PAGES = {22, 126}
KEEP_TOP_HEADING_PAGES = {11, 23, 127}
SECTION_TITLE_OVERRIDES = {
    21: "THE STATES AND EMPIRES\nOF THE MOON\n",
    125: "THE STATES AND EMPIRES\nOF THE SUN\n",
}

RUNNING_HEADERS = {
    "INTRODUCTION",
    "THE STATES AND EMPIRES OF THE MOON",
    "JOURNEY TO THE MOON",
    "THE EARTHLY PARADISE",
    "THE FRIENDLY DEMON",
    "THE LITTLE SPANIARD",
    "ON TRIAL",
    "DINNER WITH TWO PHILOSOPHERS",
    "SOME LUNAR CUSTOMS AND INVENTIONS",
    "THE FATE OF AN UNBELIEVER",
    "THE STATES AND EMPIRES OF THE SUN",
    "THE TRAVELLER'S RETURN",
    "THE TRAVELLER’S RETURN",
    "IN AND OUT OF PRISON",
    "INTO SPACE AGAIN",
    "A SMALL WORLD AND THE END OF A HAZARDOUS JOURNEY",
    "THE LITTLE PEOPLE OF THE SUN",
    "THE STORY OF THE BIRDS",
    "INDICTMENT OF AN ANIMAL ACCUSED OF BEING A MAN",
    "VERDICT AND SENTENCE",
    "THE TREES",
    "A CONFLICT OF OPPOSITES",
    "A WALK WITH CAMPANELLA",
    "A STRANGE AGONY, A TICKLISH DISPUTE",
}

ROMAN_NUMERAL_RE = re.compile(r"^[ivxlcdm]{1,8}$", re.IGNORECASE)
ARABIC_PAGE_RE = re.compile(r"^\d{1,3}$")
OCR_JUNK_RE = re.compile(r"^[|_~`'\".,:;=\-–—\\/\[\](){}<>!?\sA-Za-z0-9]{1,6}$")
HARD_HYPHEN_RE = re.compile(r"(\w)-\n(\w)")
MULTIBLANK_RE = re.compile(r"\n{3,}")
WORD_LINE_JOIN_RE = re.compile(r"(?<![.!?:;])\n(?!\n)")


def normalize_header(line: str) -> str:
    line = line.strip()
    line = line.replace("’", "'")
    line = re.sub(r"\s+", " ", line)
    return line.upper()


def pdf_text_for_page(doc: fitz.Document, page_no: int) -> str:
    text = doc.load_page(page_no - 1).get_text("text")
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def read_source_text(doc: fitz.Document, page_no: int) -> tuple[str, str]:
    ocr_path = SOURCE_OCR_DIR / f"page-{page_no:04d}.txt"
    if ocr_path.exists() and ocr_path.stat().st_size > 20:
        return ocr_path.read_text("utf-8", errors="ignore"), "existing_ocr"
    return pdf_text_for_page(doc, page_no), "pdf_text"


def first_nonblank_index(lines: list[str]) -> int | None:
    for index, line in enumerate(lines):
        if line.strip():
            return index
    return None


def drop_initial_scan_junk(lines: list[str]) -> list[str]:
    while lines and (not lines[0].strip() or OCR_JUNK_RE.match(lines[0].strip())):
        lines.pop(0)
    return lines


def should_drop_footer(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if ARABIC_PAGE_RE.match(stripped):
        return True
    if ROMAN_NUMERAL_RE.match(stripped):
        return True
    return False


def clean_page_text(raw: str, page_no: int) -> str:
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    raw = raw.replace("\u00ad", "")
    raw = HARD_HYPHEN_RE.sub(r"\1\2", raw)
    lines = [line.rstrip() for line in raw.splitlines()]
    lines = drop_initial_scan_junk(lines)

    first_index = first_nonblank_index(lines)
    if first_index is not None:
        header = normalize_header(lines[first_index])
        if header in RUNNING_HEADERS and page_no not in KEEP_TOP_HEADING_PAGES:
            del lines[first_index]
            lines = drop_initial_scan_junk(lines)

    while lines and not lines[-1].strip():
        lines.pop()
    while lines and should_drop_footer(lines[-1]):
        lines.pop()
        while lines and not lines[-1].strip():
            lines.pop()

    text = "\n".join(lines).strip()
    text = MULTIBLANK_RE.sub("\n\n", text)
    return text.strip() + ("\n" if text.strip() else "")


def is_probably_noise(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    letters = sum(ch.isalpha() for ch in stripped)
    if letters < 20:
        return True
    short_lines = [ln for ln in stripped.splitlines() if ln.strip() and len(ln.strip()) <= 3]
    nonblank = [ln for ln in stripped.splitlines() if ln.strip()]
    return bool(nonblank and len(short_lines) / len(nonblank) > 0.7)


def write_readme(project_dir: Path, kept: int, skipped: list[dict[str, object]]) -> None:
    readme = f"""# Suba Clean OCR Project

This project was generated from:

- PDF: `{SOURCE_PDF}`
- Existing OCR folder: `{SOURCE_OCR_DIR}`

Outputs:

- `clean_pages/page-XXXX.txt`: cleaned English source pages in reading order.
- `manifest.json`: maps each clean page back to the original PDF page.
- `skipped_pages.json`: pages skipped as front matter, blank/noise, or back artifacts.
- `scripts/clean_suba_pages.py`: reproducible cleanup script.

Cleaning rules:

- Keep book text from PDF pages {BOOK_PAGE_START}-{BOOK_PAGE_END}.
- Skip blank/noise pages: {", ".join(str(n) for n in sorted(SKIP_PDF_PAGES))}.
- Remove running headers at the top of pages.
- Remove printed page numbers and roman numerals at the bottom.
- De-hyphenate OCR line breaks like `philo-\\nsopher`.

Generated clean pages: {kept}
Skipped pages recorded: {len(skipped)}
"""
    (project_dir / "README.md").write_text(readme, "utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", default="/Users/miikka/Desktop/suba_clean")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).expanduser()
    clean_dir = project_dir / "clean_pages"
    scripts_dir = project_dir / "scripts"

    if project_dir.exists() and args.overwrite:
        for child in [clean_dir, scripts_dir]:
            if child.exists():
                shutil.rmtree(child)
        for child in ["manifest.json", "skipped_pages.json", "README.md"]:
            path = project_dir / child
            if path.exists():
                path.unlink()

    clean_dir.mkdir(parents=True, exist_ok=True)
    scripts_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(SOURCE_PDF)
    manifest: list[dict[str, object]] = []
    skipped: list[dict[str, object]] = []
    clean_index = 1

    for page_no in range(1, doc.page_count + 1):
        if page_no < BOOK_PAGE_START or page_no > BOOK_PAGE_END:
            skipped.append({"pdf_page": page_no, "reason": "outside_book_text_range"})
            continue
        if page_no in SKIP_PDF_PAGES:
            skipped.append({"pdf_page": page_no, "reason": "blank_or_scan_noise"})
            continue

        if page_no in SECTION_TITLE_OVERRIDES:
            cleaned = SECTION_TITLE_OVERRIDES[page_no]
            source = "manual_section_title_cleanup"
        else:
            raw, source = read_source_text(doc, page_no)
            cleaned = clean_page_text(raw, page_no)
        if is_probably_noise(cleaned):
            skipped.append({"pdf_page": page_no, "reason": "noise_after_cleaning", "source": source})
            continue

        out_name = f"page-{clean_index:04d}.txt"
        out_path = clean_dir / out_name
        out_path.write_text(cleaned, "utf-8")
        manifest.append(
            {
                "clean_page": clean_index,
                "file": f"clean_pages/{out_name}",
                "pdf_page": page_no,
                "source": source,
                "chars": len(cleaned),
                "first_line": next((ln for ln in cleaned.splitlines() if ln.strip()), ""),
            }
        )
        clean_index += 1

    (project_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), "utf-8")
    (project_dir / "skipped_pages.json").write_text(json.dumps(skipped, indent=2, ensure_ascii=False), "utf-8")
    write_readme(project_dir, len(manifest), skipped)
    shutil.copy2(Path(__file__), scripts_dir / "clean_suba_pages.py")

    print(f"Project: {project_dir}")
    print(f"Clean pages: {len(manifest)}")
    print(f"Skipped pages: {len(skipped)}")
    print(f"First clean page: {manifest[0]['file']} from PDF page {manifest[0]['pdf_page']}")
    print(f"Last clean page: {manifest[-1]['file']} from PDF page {manifest[-1]['pdf_page']}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Combine edited Suba clean text pages into one PDF.

Order:
1. menu1.txt
2. menu2.txt
3. clean_pages/page-*.txt in numeric order
"""

from __future__ import annotations

import argparse
import json
import re
import textwrap
from pathlib import Path

import fitz


DEFAULT_PROJECT_DIR = Path("/Users/miikka/Desktop/suba_clean")
DEFAULT_FONT = Path("/System/Library/Fonts/Supplemental/Times New Roman.ttf")


def input_files(project_dir: Path) -> list[Path]:
    files: list[Path] = []
    for name in ["menu1.txt", "menu2.txt"]:
        path = project_dir / name
        if path.exists():
            files.append(path)

    pages_dir = project_dir / "clean_pages"
    files.extend(sorted(pages_dir.glob("page-*.txt")))
    return files


HEADING_RE = re.compile(r"^[A-Z0-9][A-Z0-9 '\u2019,;:\-.]+$")


def is_heading_block(lines: list[str]) -> bool:
    compact = [line.strip() for line in lines if line.strip()]
    if not compact:
        return False
    joined = " ".join(compact)
    if len(compact) <= 2 and len(joined) <= 80:
        return True
    if len(compact) <= 3 and HEADING_RE.match(joined) and len(joined) <= 100:
        return True
    return False


def reflow_prose_text(text: str) -> str:
    blocks = re.split(r"\n\s*\n", text.replace("\r\n", "\n").replace("\r", "\n").strip("\n"))
    out: list[str] = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        if is_heading_block(lines):
            out.append("\n".join(lines))
        else:
            paragraph = " ".join(lines)
            paragraph = re.sub(r"\s+", " ", paragraph).strip()
            out.append(paragraph)
    return "\n\n".join(out)


def source_blocks(source: Path, project_dir: Path, width: int) -> list[list[str]]:
    text = source.read_text("utf-8", errors="ignore").strip("\n")
    reflow = source.parent.name == "clean_pages"
    return text_blocks(text, width, reflow=reflow)


def block_plain_text(block: list[str]) -> str:
    return " ".join(line.strip() for line in block if line.strip()).strip()


def is_heading_text(text: str) -> bool:
    if not text:
        return False
    if len(text) <= 90 and HEADING_RE.match(text.upper()):
        return True
    if len(text) <= 80 and not re.search(r"[.!?;:]$", text):
        words = text.split()
        return len(words) <= 8
    return False


def should_merge_across_source_boundary(previous: list[str], current: list[str]) -> bool:
    prev_text = block_plain_text(previous)
    cur_text = block_plain_text(current)
    if not prev_text or not cur_text:
        return False
    if is_heading_text(prev_text) or is_heading_text(cur_text):
        return False
    if re.search(r"[.!?’”\"]$", prev_text):
        return False
    return True


def rewrap_text_block(text: str, width: int) -> list[str]:
    return textwrap.wrap(
        re.sub(r"\s+", " ", text).strip(),
        width=width,
        break_long_words=False,
        replace_whitespace=False,
        drop_whitespace=True,
    )


def merged_book_blocks(page_files: list[Path], project_dir: Path, width: int) -> list[list[str]]:
    merged: list[list[str]] = []
    for source in page_files:
        blocks = source_blocks(source, project_dir, width)
        if not blocks:
            continue
        if merged and should_merge_across_source_boundary(merged[-1], blocks[0]):
            combined = f"{block_plain_text(merged[-1])} {block_plain_text(blocks[0])}"
            merged[-1] = rewrap_text_block(combined, width)
            merged.extend(blocks[1:])
        else:
            merged.extend(blocks)
    return merged


def text_blocks(text: str, width: int, *, reflow: bool) -> list[list[str]]:
    if reflow:
        text = reflow_prose_text(text)
    blocks: list[list[str]] = []
    for raw_block in re.split(r"\n\s*\n", text.replace("\r\n", "\n").replace("\r", "\n").strip("\n")):
        raw_block = raw_block.strip()
        if not raw_block:
            continue

        wrapped: list[str] = []
        for raw in raw_block.splitlines():
            line = raw.rstrip()
            if len(line) <= width:
                wrapped.append(line)
            else:
                wrapped.extend(
                    textwrap.wrap(
                        line,
                        width=width,
                        break_long_words=False,
                        replace_whitespace=False,
                        drop_whitespace=True,
                    )
                )
        blocks.append(wrapped)
    return blocks


def draw_line(page: fitz.Page, text: str, x: float, y: float, font_size: float, fontfile: Path) -> None:
    page.insert_text(
        (x, y),
        text,
        fontsize=font_size,
        fontname="TimesNewRoman",
        fontfile=str(fontfile),
        color=(0, 0, 0),
    )


def draw_blocks(
    *,
    doc: fitz.Document,
    blocks: list[list[str]],
    start_pdf_page: int,
    page_width: float,
    page_height: float,
    margin_left: float,
    margin_top: float,
    margin_bottom: float,
    line_height: float,
    paragraph_gap: float,
    font_size: float,
    fontfile: Path,
) -> int:
    pdf_page_no = start_pdf_page - 1
    max_y = page_height - margin_bottom
    lines_per_page = int((max_y - margin_top) // line_height)
    page: fitz.Page | None = None
    y = margin_top

    def new_page() -> fitz.Page:
        nonlocal pdf_page_no, y
        page_obj = doc.new_page(width=page_width, height=page_height)
        pdf_page_no += 1
        y = margin_top
        add_page_number(page_obj, pdf_page_no, page_width, page_height, fontfile)
        return page_obj

    page = new_page()
    for block in blocks:
        if not block:
            continue

        block_height = len(block) * line_height
        if y > margin_top and y + block_height > max_y and len(block) <= lines_per_page:
            page = new_page()

        cursor = 0
        while cursor < len(block):
            if y + line_height > max_y:
                page = new_page()

            remaining_lines = int((max_y - y) // line_height)
            take = min(len(block) - cursor, max(1, remaining_lines))
            for line in block[cursor : cursor + take]:
                draw_line(page, line, margin_left, y, font_size, fontfile)
                y += line_height
            cursor += take

        y += paragraph_gap
        if y > max_y:
            page = new_page()

    return pdf_page_no


def add_page_number(page: fitz.Page, number: int, page_width: float, page_height: float, fontfile: Path) -> None:
    page.insert_text(
        (page_width / 2 - 8, page_height - 28),
        str(number),
        fontsize=9,
        fontname="TimesNewRoman",
        fontfile=str(fontfile),
        color=(0.35, 0.35, 0.35),
    )


def build_pdf(project_dir: Path, out_path: Path, fontfile: Path) -> list[dict[str, object]]:
    doc = fitz.open()
    files = input_files(project_dir)
    if not files:
        raise SystemExit(f"No input txt files found under {project_dir}")

    page_rect = fitz.paper_rect("letter")
    page_width = page_rect.width
    page_height = page_rect.height
    margin_left = 64
    margin_top = 56
    margin_bottom = 56
    line_height = 16.4
    paragraph_gap = 7.5
    font_size = 12.0
    chars_per_line = 83

    manifest: list[dict[str, object]] = []
    pdf_page_no = 0

    for source in files:
        blocks = source_blocks(source, project_dir, chars_per_line)
        if not blocks:
            continue

        start_pdf_page = pdf_page_no + 1
        pdf_page_no = draw_blocks(
            doc=doc,
            blocks=blocks,
            start_pdf_page=start_pdf_page,
            page_width=page_width,
            page_height=page_height,
            margin_left=margin_left,
            margin_top=margin_top,
            margin_bottom=margin_bottom,
            line_height=line_height,
            paragraph_gap=paragraph_gap,
            font_size=font_size,
            fontfile=fontfile,
        )

        manifest.append(
            {
                "source": str(source.relative_to(project_dir)),
                "pdf_start_page": start_pdf_page,
                "pdf_end_page": pdf_page_no,
                "chars": len(source.read_text("utf-8", errors="ignore")),
            }
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out_path)
    doc.close()
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", default=str(DEFAULT_PROJECT_DIR))
    parser.add_argument("--out", default=str(DEFAULT_PROJECT_DIR / "suba_clean_english.pdf"))
    parser.add_argument("--font", default=str(DEFAULT_FONT))
    args = parser.parse_args()

    project_dir = Path(args.project_dir).expanduser()
    out_path = Path(args.out).expanduser()
    fontfile = Path(args.font).expanduser()
    manifest = build_pdf(project_dir, out_path, fontfile)

    pdf_manifest = out_path.with_suffix(".pdf.manifest.json")
    pdf_manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), "utf-8")
    print(f"Wrote {out_path}")
    print(f"Wrote {pdf_manifest}")
    print(f"Input txt files: {len(manifest)}")
    print(f"PDF pages: {manifest[-1]['pdf_end_page'] if manifest else 0}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Build a Chinese PDF from translated Suba chunk files."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import fitz


DEFAULT_PROJECT_DIR = Path("/Users/miikka/Desktop/suba_clean")
DEFAULT_FONT = Path("/System/Library/Fonts/Hiragino Sans GB.ttc")
DEFAULT_BOLD_FONT = Path("/System/Library/Fonts/STHeiti Medium.ttc")


def chunk_files(project_dir: Path) -> list[Path]:
    chunks_dir = project_dir / "translation" / "chunks_zh"
    return sorted(chunks_dir.glob("chunk-*.txt"))


def wrap_cjk_line(line: str, max_chars: int) -> list[str]:
    line = line.strip()
    if not line:
        return [""]
    chunks = []
    while len(line) > max_chars:
        split_at = max_chars
        for punct in "，。；：！？、）】》”’":
            pos = line.rfind(punct, 0, max_chars + 1)
            if pos >= max_chars * 0.55:
                split_at = pos + 1
                break
        chunks.append(line[:split_at].strip())
        line = line[split_at:].strip()
    if line:
        chunks.append(line)
    return chunks


def classify_block(block: str) -> str:
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    joined = " ".join(lines)
    compact = "".join(lines)
    if not joined:
        return "body"
    if compact == "目录":
        return "title"
    if compact.startswith("*"):
        return "note"
    if compact in {"引言", "月球诸国与诸帝国", "太阳诸国与诸帝国"}:
        return "section"
    if re.match(r"^\d+\s", joined) and len(joined) <= 45:
        return "toc"
    if len(compact) <= 34 and not re.search(r"[。！？；，、：的了着在和与及而并但又或、，]$", compact):
        if "著" in compact and len(compact) <= 14:
            return "byline"
        return "heading"
    if len(joined) <= 95 and ("——" in joined or joined.startswith("“")) and not re.match(r"^[“‘].+[。！？]$", joined):
        return "epigraph"
    return "body"


def text_blocks(text: str, max_chars: int) -> list[dict[str, object]]:
    blocks: list[dict[str, object]] = []
    for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n").replace("\r", "\n").strip()):
        block = block.strip()
        if not block:
            continue
        style = classify_block(block)
        lines = []
        for raw_line in block.splitlines():
            lines.extend(wrap_cjk_line(raw_line, max_chars))
        blocks.append({"style": style, "lines": lines, "raw": block})
    return blocks


def add_page_number(page: fitz.Page, number: int, page_width: float, page_height: float, fontfile: Path) -> None:
    page.insert_text(
        (page_width / 2 - 8, page_height - 28),
        str(number),
        fontsize=9,
        fontname="Songti",
        fontfile=str(fontfile),
        color=(0.35, 0.35, 0.35),
    )


def style_metrics(style: str, body_size: float) -> dict[str, object]:
    styles = {
        "title": {"font_size": 17.5, "line_height": 26, "gap_before": 8, "gap_after": 14, "align": "center", "bold": True},
        "section": {"font_size": 15.2, "line_height": 23, "gap_before": 14, "gap_after": 11, "align": "center", "bold": True},
        "heading": {"font_size": 14.3, "line_height": 22, "gap_before": 12, "gap_after": 9, "align": "center", "bold": True},
        "toc": {"font_size": 12.4, "line_height": 19, "gap_before": 1, "gap_after": 2, "align": "left", "bold": True},
        "byline": {"font_size": 11.2, "line_height": 17, "gap_before": 0, "gap_after": 13, "align": "center", "bold": False},
        "epigraph": {"font_size": 11.2, "line_height": 17, "gap_before": 3, "gap_after": 9, "align": "left", "indent": 22, "bold": False},
        "note": {"font_size": 10.3, "line_height": 15.6, "gap_before": 0, "gap_after": 9, "align": "left", "indent": 18, "bold": False},
        "body": {"font_size": body_size, "line_height": 18.8, "gap_before": 0, "gap_after": 8, "align": "left", "bold": False},
    }
    return styles.get(style, styles["body"])


def insert_line(
    page: fitz.Page,
    line: str,
    *,
    x: float,
    y: float,
    page_width: float,
    margin_right: float,
    font_size: float,
    fontfile: Path,
    fontname: str,
    align: str,
) -> None:
    if align == "center":
        rect = fitz.Rect(x, y - font_size * 0.25, page_width - margin_right, y + font_size * 1.45)
        page.insert_textbox(
            rect,
            line,
            fontsize=font_size,
            fontname=fontname,
            fontfile=str(fontfile),
            color=(0, 0, 0),
            align=fitz.TEXT_ALIGN_CENTER,
        )
    else:
        page.insert_text(
            (x, y),
            line,
            fontsize=font_size,
            fontname=fontname,
            fontfile=str(fontfile),
            color=(0, 0, 0),
        )


def draw_pdf(project_dir: Path, out_path: Path, fontfile: Path, bold_fontfile: Path) -> list[dict[str, object]]:
    files = chunk_files(project_dir)
    if not files:
        raise SystemExit(f"No translated chunks found in {project_dir / 'translation' / 'chunks_zh'}")

    doc = fitz.open()
    page_rect = fitz.paper_rect("letter")
    page_width = page_rect.width
    page_height = page_rect.height
    margin_left = 62
    margin_right = 62
    margin_top = 58
    margin_bottom = 58
    font_size = 12.2
    max_chars = 33
    max_y = page_height - margin_bottom

    page_no = 0
    page: fitz.Page | None = None
    y = margin_top
    manifest = []

    def new_page() -> fitz.Page:
        nonlocal page_no, y
        p = doc.new_page(width=page_width, height=page_height)
        page_no += 1
        y = margin_top
        add_page_number(p, page_no, page_width, page_height, fontfile)
        return p

    page = new_page()

    combined_parts = []
    for path in files:
        text = path.read_text("utf-8", errors="ignore").strip()
        if not text:
            continue
        combined_parts.append(text)
        start_page = page_no
        for block in text_blocks(text, max_chars):
            lines = block["lines"]
            style = str(block["style"])
            metrics = style_metrics(style, font_size)
            block_font_size = float(metrics["font_size"])
            line_height = float(metrics["line_height"])
            gap_before = float(metrics["gap_before"])
            gap_after = float(metrics["gap_after"])
            align = str(metrics["align"])
            indent = float(metrics.get("indent", 0))
            use_bold = bool(metrics["bold"])
            active_font = bold_fontfile if use_bold else fontfile
            active_name = "Heiti" if use_bold else "HiraginoSansGB"

            block_height = gap_before + len(lines) * line_height + gap_after
            if y > margin_top and y + block_height > max_y and block_height <= (max_y - margin_top):
                page = new_page()
            y += gap_before
            for line in lines:
                if y + line_height > max_y:
                    page = new_page()
                if line:
                    insert_line(
                        page,
                        line,
                        x=margin_left + indent,
                        y=y,
                        page_width=page_width,
                        margin_right=margin_right,
                        font_size=block_font_size,
                        fontfile=active_font,
                        fontname=active_name,
                        align=align,
                    )
                y += line_height
            y += gap_after
        manifest.append({"source": str(path.relative_to(project_dir)), "pdf_start_page": start_page, "pdf_end_page": page_no, "chars": len(text)})

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out_path)
    doc.close()

    combined_path = project_dir / "translation" / "source_zh_combined.txt"
    combined_path.write_text("\n\n".join(combined_parts).strip() + "\n", "utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", default=str(DEFAULT_PROJECT_DIR))
    parser.add_argument("--out", default=str(DEFAULT_PROJECT_DIR / "suba_chinese.pdf"))
    parser.add_argument("--font", default=str(DEFAULT_FONT))
    parser.add_argument("--bold-font", default=str(DEFAULT_BOLD_FONT))
    args = parser.parse_args()

    project_dir = Path(args.project_dir).expanduser()
    out_path = Path(args.out).expanduser()
    fontfile = Path(args.font).expanduser()
    bold_fontfile = Path(args.bold_font).expanduser()
    manifest = draw_pdf(project_dir, out_path, fontfile, bold_fontfile)
    manifest_path = out_path.with_suffix(".pdf.manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), "utf-8")
    print(f"Wrote {out_path}")
    print(f"Wrote {manifest_path}")
    print(f"Translated chunks: {len(manifest)}")
    print(f"PDF pages: {manifest[-1]['pdf_end_page'] if manifest else 0}")


if __name__ == "__main__":
    main()

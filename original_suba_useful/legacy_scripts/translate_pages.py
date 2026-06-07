#!/usr/bin/env python3
"""Translate OCR page .txt files (English) to Simplified Chinese.

- Input:  ~/Desktop/suba/out/ocr/pages/page-XXXX.txt
- Output: ~/Desktop/suba/out/zh_out/pages/page-XXXX.zh.txt

Uses Argos Translate (offline) for en->zh.
Applies light post-processing for readability + a subtle JP-style light-novel cadence.

Usage:
  python3 translate_pages.py \
    --in ~/Desktop/suba/out/ocr/pages \
    --out ~/Desktop/suba/out/zh_out/pages

Optional:
  --overwrite   re-translate even if output exists
  --limit N     only first N pages (for testing)
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from argostranslate import translate

CJK_SPACE_RE = re.compile(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])")
MULTISPACE_RE = re.compile(r"[ \t]{2,}")
RTF_BLOCK_RE = re.compile(r"\{\\[^}]+\}")
HARD_HYPHEN_BREAK_RE = re.compile(r"(\w)-\n(\w)")


def split_paragraphs(src: str) -> list[str]:
    # Keep blank lines as paragraph separators.
    # Normalize Windows newlines.
    src = src.replace("\r\n", "\n").replace("\r", "\n")
    paras = src.split("\n\n")
    return [p.strip("\n") for p in paras]


def postprocess_zh(s: str) -> str:
    # Strip any stray RTF-like blocks that sometimes leak into OCR / MT.
    s = RTF_BLOCK_RE.sub("", s)

    s = s.replace("...", "……")
    s = s.replace("..", "……")

    # Remove double spaces; keep single spaces when they likely separate latin tokens.
    s = MULTISPACE_RE.sub(" ", s)

    # Remove spaces between Chinese chars.
    s = CJK_SPACE_RE.sub("", s)

    # Fix isolated English pronouns that sometimes slip through.
    s = re.sub(r"\bHe\b", "他", s)
    s = re.sub(r"\bShe\b", "她", s)

    # Subtle JP-ish cadence, very lightly (avoid heavy stylization).
    # Only touch very short standalone sentences.
    s = re.sub(r"。\s*$", "呢。", s) if len(s) <= 14 and s.endswith("。") else s

    return s.strip()


def preprocess_en(en_text: str) -> str:
    en_text = en_text.replace("\r\n", "\n").replace("\r", "\n")
    # De-hyphenate common OCR line-break hyphenations: mathe-\nmatician -> mathematician
    en_text = HARD_HYPHEN_BREAK_RE.sub(r"\1\2", en_text)
    return en_text


def translate_page_text(en_text: str) -> str:
    en_text = preprocess_en(en_text).strip("\n")
    if not en_text.strip():
        return ""

    paras = split_paragraphs(en_text)
    out_paras: list[str] = []
    for p in paras:
        if not p.strip():
            out_paras.append("")
            continue
        zh = translate.translate(p, "en", "zh")
        zh = postprocess_zh(zh)
        out_paras.append(zh)

    # Re-join with blank lines preserved
    # Clean up excessive blank lines
    joined = "\n\n".join(out_paras).strip() + "\n"
    joined = re.sub(r"\n{3,}", "\n\n", joined)
    return joined


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_dir", required=True)
    ap.add_argument("--out", dest="out_dir", required=True)
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    in_dir = Path(args.in_dir).expanduser()
    out_dir = Path(args.out_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    pages = sorted(in_dir.glob("page-*.txt"))
    if args.limit:
        pages = pages[: args.limit]

    if not pages:
        raise SystemExit(f"No pages found in {in_dir}")

    for idx, p in enumerate(pages, 1):
        out_path = out_dir / (p.stem + ".zh.txt")
        if out_path.exists() and out_path.stat().st_size > 10 and not args.overwrite:
            continue

        en_text = p.read_text("utf-8", errors="ignore")
        zh_text = translate_page_text(en_text)
        out_path.write_text(zh_text, "utf-8")

        if idx % 10 == 0:
            print(f"translated {idx}/{len(pages)}")

    print("done")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Re-translate OCR page .txt files (English) to Simplified Chinese (clean + consistent).

Goals (per Miikka):
- No duplicated content (remove accidental repeats)
- No unreadable garbage (strip RTF blocks / control chars)
- No classical Chinese (keep modern, plain Mandarin)
- Consistent handling of names/places/page numbers/numerals/dialogue style

Input:
  ~/Desktop/suba/out/ocr/pages/page-XXXX.txt
Output:
  ~/Desktop/suba/out/zh_out/pages/page-XXXX.zh.txt

Translation engine: Argos Translate (offline) en->zh.

Usage:
  python3 translate_pages_v2.py --in ~/Desktop/suba/out/ocr/pages --out ~/Desktop/suba/out/zh_out/pages
  python3 translate_pages_v2.py --overwrite --limit 20 ...
"""

from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path

from argostranslate import translate

# --- regexes / cleanup ---
RTF_BLOCK_RE = re.compile(r"\{\\[^}]+\}")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
HARD_HYPHEN_BREAK_RE = re.compile(r"(\w)-\n(\w)")
CJK_SPACE_RE = re.compile(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])")
MULTISPACE_RE = re.compile(r"[ \t]{2,}")
ROMAN_LINE_RE = re.compile(r"^\s*[ivxlcdm]{1,6}\s*$", re.IGNORECASE)
PAGE_MARK_RE = re.compile(r"^\s*(page\s*[:：]\s*\d+|页\s*[:：]\s*\d+)\s*$", re.IGNORECASE)
ENGLISH_NOTE_RE = re.compile(r"\(英语\s*:[^)]+\)")

# Consistent proper-noun mapping (expand as we discover more)
GLOSSARY = {
    "Cyrano": "西拉诺",
    "Le Bret": "勒布雷特",
    "Henri Le Bret": "亨利·勒布雷特",
    "Gassendi": "伽森狄",
    "Epicurean": "伊壁鸠鲁派",
    "Moliere": "莫里哀",
    "Molière": "莫里哀",
    "Descartes": "笛卡尔",
    "Jacques Rohault": "雅克·罗奥",
    "Tristan L’Hermite": "特里斯坦·勒米特",
    "Tristan L'Hermite": "特里斯坦·勒米特",
    "Tristan L ' Hermite": "特里斯坦·勒米特",
    "Francois Tristan L’Hermite": "弗朗索瓦·特里斯坦·勒米特",
    "François Tristan L’Hermite": "弗朗索瓦·特里斯坦·勒米特",
}

# Variants normalization before glossary
NAME_NORMALIZE = {
    "L ' Hermite": "L’Hermite",
    "L' Hermite": "L’Hermite",
    "L 'Hermite": "L’Hermite",
    "Tristan L ' Hermite": "Tristan L’Hermite",
    "Tristan L 'Hermite": "Tristan L’Hermite",
    "Francois": "François",  # keep consistent accent in source before translation
    "Collége": "Collège",
    "Collége": "Collège",
    "Collége de\nLisieux": "Collège de Lisieux",
}


def normalize_source(s: str) -> str:
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = unicodedata.normalize("NFKC", s)
    # join hyphenated line breaks
    s = HARD_HYPHEN_BREAK_RE.sub(r"\1\2", s)
    # normalize common name fragments
    for k, v in NAME_NORMALIZE.items():
        s = s.replace(k, v)
    # remove obvious garbage control chars
    s = CONTROL_RE.sub("", s)
    return s


def is_garbled_ocr(en_text: str) -> bool:
    # Heuristic: pages like page-0126 are mostly symbols / single letters.
    t = en_text.strip()
    if not t:
        return True
    letters = sum(ch.isalpha() for ch in t)
    digits = sum(ch.isdigit() for ch in t)
    spaces = sum(ch.isspace() for ch in t)
    other = len(t) - letters - digits - spaces
    # Very low letter density and high symbol density => likely unusable.
    if len(t) < 800 and letters / max(1, len(t)) < 0.25 and other / max(1, len(t)) > 0.25:
        return True
    # Too many very short lines (hard-wrap noise)
    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    if lines and len(lines) > 25 and sum(len(ln) <= 3 for ln in lines) / len(lines) > 0.7:
        return True
    return False


def split_paragraphs(src: str) -> list[str]:
    # Keep blank lines as paragraph separators.
    src = src.replace("\r\n", "\n").replace("\r", "\n")
    parts = src.split("\n\n")
    return [p.strip("\n") for p in parts]


def flatten_paragraph(p: str) -> str:
    # OCR pages often hard-wrap lines mid-sentence.
    # Within a paragraph, turn newlines into spaces.
    p = p.replace("\n", " ")
    p = MULTISPACE_RE.sub(" ", p)
    return p.strip()


def dedupe_lines(text: str) -> str:
    lines = text.split("\n")
    out = []
    prev = None
    for ln in lines:
        if prev is not None and ln.strip() and ln.strip() == prev.strip():
            continue
        out.append(ln)
        prev = ln
    return "\n".join(out)


def apply_glossary(zh: str) -> str:
    for en, cn in sorted(GLOSSARY.items(), key=lambda x: -len(x[0])):
        zh = zh.replace(en, cn)
    return zh


def normalize_dialogue(zh: str) -> str:
    # Normalize quotes for readability
    zh = zh.replace('"', '“').replace('”', '”')
    # Fix doubled quotes artifacts
    zh = re.sub(r"“{2,}", "“", zh)
    zh = re.sub(r"”{2,}", "”", zh)
    return zh


def postprocess_zh(zh: str) -> str:
    zh = unicodedata.normalize("NFKC", zh)
    zh = RTF_BLOCK_RE.sub("", zh)
    zh = CONTROL_RE.sub("", zh)

    # punctuation / spacing
    zh = zh.replace("...", "……").replace("..", "……")
    zh = MULTISPACE_RE.sub(" ", zh)
    zh = CJK_SPACE_RE.sub("", zh)

    # pronouns sometimes slip through
    zh = re.sub(r"\bHe\b", "他", zh)
    zh = re.sub(r"\bShe\b", "她", zh)

    zh = apply_glossary(zh)
    zh = ENGLISH_NOTE_RE.sub("", zh)

    # Fix common MT/OCR awkwardness (keep modern, readable Chinese)
    fixes = [
        ("戒指", "口音"),
        ("瞳孔", "学生"),
        ("剥削", "事迹"),
        ("布球传说", "滑稽的传闻"),
        ("不坚定的生活方式", "有点放纵的生活方式"),
        ("埃皮古雷恩", "伊壁鸠鲁派"),
        ("无罪释放了自己", "表现得很不错"),
    ]
    for a, b in fixes:
        zh = zh.replace(a, b)

    zh = normalize_dialogue(zh)

    # remove accidental duplicated lines
    zh = dedupe_lines(zh)

    # keep modern tone
    zh = zh.replace("兮", "")

    return zh.strip()


def should_drop_paragraph(p: str) -> bool:
    # Drop pure page markers / roman numeral footer lines.
    t = p.strip()
    if not t:
        return False
    if ROMAN_LINE_RE.match(t):
        return True
    if PAGE_MARK_RE.match(t):
        return True
    return False


def translate_page(en_text: str) -> str:
    en_text = normalize_source(en_text).strip("\n")
    if not en_text.strip():
        return ""
    if is_garbled_ocr(en_text):
        return "【本页 OCR 内容质量较差，无法可靠翻译。】\n"

    paras = split_paragraphs(en_text)
    out_paras: list[str] = []

    for p in paras:
        if not p.strip():
            out_paras.append("")
            continue
        if should_drop_paragraph(p):
            continue

        # translate paragraph-wise to preserve blank lines
        p2 = flatten_paragraph(p)
        zh = translate.translate(p2, "en", "zh")
        zh = postprocess_zh(zh)
        if zh:
            out_paras.append(zh)

    # Re-join, collapse excessive blanks
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

    total = len(pages)
    for i, src in enumerate(pages, 1):
        dst = out_dir / (src.stem + ".zh.txt")
        if dst.exists() and dst.stat().st_size > 10 and not args.overwrite:
            continue

        en = src.read_text("utf-8", errors="ignore")
        zh = translate_page(en)
        dst.write_text(zh, "utf-8")

        if i % 10 == 0 or i == total:
            print(f"translated {i}/{total}")

    print("done")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Typeset translated pages (plain text) into a PDF with a book-like layout.

Usage:
  python3 make_pdf.py --out out.pdf page-0008.zh.txt page-0009.zh.txt ...
"""

import argparse
import os
from pathlib import Path

from reportlab.lib.pagesizes import A5
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


def pick_cjk_font():
    # Prefer macOS PingFang
    candidates = [
        '/System/Library/Fonts/PingFang.ttc',
        '/System/Library/Fonts/STHeiti Medium.ttc',
        '/Library/Fonts/Arial Unicode.ttf',
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def wrap_text(text, max_chars):
    # rough wrap by characters; ok for Chinese book draft
    lines = []
    for para in text.split('\n'):
        if not para.strip():
            lines.append('')
            continue
        s = para.rstrip()
        while len(s) > max_chars:
            lines.append(s[:max_chars])
            s = s[max_chars:]
        lines.append(s)
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('pages', nargs='+')
    args = ap.parse_args()

    out = args.out

    font_path = pick_cjk_font()
    if not font_path:
        raise SystemExit('No CJK font found on system')

    # ReportLab TTFont doesn't support .ttc directly in all builds.
    # Use a fallback font if TTC fails.
    font_name = 'CJKFont'
    try:
        pdfmetrics.registerFont(TTFont(font_name, font_path))
    except Exception:
        # fallback to Helvetica (will not render Chinese correctly)
        font_name = 'Helvetica'

    c = canvas.Canvas(out, pagesize=A5)
    w, h = A5

    margin_x = 42
    margin_y = 54
    font_size = 10.5
    leading = 15
    max_width = w - 2 * margin_x

    # approximate chars per line
    max_chars = int(max_width / (font_size * 0.9))

    for page_path in args.pages:
        text = Path(page_path).read_text('utf-8')
        c.setFont(font_name, font_size)
        y = h - margin_y

        lines = wrap_text(text, max_chars=max_chars)
        for ln in lines:
            if y < margin_y:
                c.showPage()
                c.setFont(font_name, font_size)
                y = h - margin_y
            if ln == '':
                y -= leading
                continue
            c.drawString(margin_x, y, ln)
            y -= leading

        c.showPage()

    c.save()
    print('wrote', out)


if __name__ == '__main__':
    main()

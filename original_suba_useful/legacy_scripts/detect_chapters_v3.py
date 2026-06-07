#!/usr/bin/env python3
"""Detect chapter boundaries from OCR pages using explicit markers.

We *only* accept lines that look like real structural headings:
- CHAPTER/BOOK/PART at start of a line
- or 'CHAPTER I.' style

This avoids false positives from running headers like 'CYRANO DE BERGERAC'.

Writes out/chapters/index.v3.json
"""

import json
import os
import re
from pathlib import Path

BASE = Path(os.path.expanduser('~/Desktop/suba/out'))
PAGES_DIR = BASE / 'ocr' / 'pages'
OUT = BASE / 'chapters' / 'index.v3.json'

re_struct = re.compile(
    r"^\s*(BOOK|Book|PART|Part|CHAPTER|Chapter)\b\s*([0-9IVXLC]+|ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN)?\b[\s\.:-]*.*$",
    re.M,
)


def main():
    pages = sorted(PAGES_DIR.glob('page-*.txt'))
    if not pages:
        raise SystemExit('No OCR pages found')

    last_page_no = int(pages[-1].stem.split('-')[-1])
    candidates = []

    for p in pages:
        page_no = int(p.stem.split('-')[-1])
        text = p.read_text('utf-8', errors='ignore')
        # Look near top of page first; if not found, scan full page but prefer early match.
        top = '\n'.join(text.splitlines()[:80])
        m = re_struct.search(top) or re_struct.search(text)
        if m:
            line = m.group(0).strip()
            # reject obvious boilerplate
            if 'OXFORD' in line.upper() and 'PRESS' in line.upper():
                continue
            candidates.append({'page': page_no, 'line': line})

    # de-dup
    seen = {}
    for c in candidates:
        seen[c['page']] = c
    candidates = [seen[k] for k in sorted(seen.keys())]

    # if no chapters found, fallback to a single range
    if not candidates:
        chapters = [{'chapterIndex': 1, 'startPage': 1, 'endPage': last_page_no, 'hint': {'page': 1, 'line': 'START'}}]
    else:
        chapters = []
        for i, s in enumerate(candidates):
            start = s['page']
            end = (candidates[i+1]['page'] - 1) if i+1 < len(candidates) else last_page_no
            chapters.append({'chapterIndex': i+1, 'startPage': start, 'endPage': end, 'hint': s})

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        'pages': last_page_no,
        'candidates': candidates,
        'chapters': chapters,
    }, indent=2, ensure_ascii=False), 'utf-8')

    print(f'Wrote {OUT}')
    print(f'Found candidates: {len(candidates)} chapters: {len(chapters)}')
    if candidates:
        print('First few:', candidates[:5])


if __name__ == '__main__':
    main()

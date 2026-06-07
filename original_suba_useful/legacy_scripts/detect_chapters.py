#!/usr/bin/env python3
"""Detect chapter-like boundaries from OCR text files.

Looks for headings like:
- CHAPTER / Chapter + number/roman
- BOOK / Book
- PART / Part
- explicit all-caps section headings on their own line

Writes out/chapters/index.v2.json
"""

import json
import os
import re
from pathlib import Path

BASE = Path(os.path.expanduser('~/Desktop/suba/out'))
PAGES_DIR = BASE / 'ocr' / 'pages'
OUT = BASE / 'chapters' / 'index.v2.json'

re_chapter = re.compile(r"^\s*(CHAPTER|Chapter)\b\s*([0-9IVXLC]+)?\b.*$", re.M)
re_book = re.compile(r"^\s*(BOOK|Book|PART|Part)\b\s*([0-9IVXLC]+)?\b.*$", re.M)


def is_heading_line(line: str) -> bool:
    l = line.strip()
    if len(l) < 4 or len(l) > 80:
        return False
    # mostly caps and spaces
    letters = [c for c in l if c.isalpha()]
    if not letters:
        return False
    caps = sum(1 for c in letters if c.isupper())
    if caps / len(letters) < 0.85:
        return False
    # avoid boilerplate
    bad = ['OXFORD', 'UNIVERSITY', 'PRESS', 'PRINTED', 'COPYRIGHT']
    if any(b in l for b in bad):
        return False
    return True


def main():
    pages = sorted(PAGES_DIR.glob('page-*.txt'))
    candidates = []

    for p in pages:
        page_no = int(p.stem.split('-')[-1])
        text = p.read_text('utf-8', errors='ignore')
        # first 60 lines are usually where headings appear
        head = '\n'.join(text.splitlines()[:60])

        m = re_book.search(head) or re_chapter.search(head)
        if m:
            line = m.group(0).strip()
            candidates.append({'page': page_no, 'type': m.group(1).lower(), 'line': line})
            continue

        # fallback: all-caps standalone headings
        for line in head.splitlines()[:40]:
            if is_heading_line(line):
                candidates.append({'page': page_no, 'type': 'caps', 'line': line.strip()})
                break

    # de-dup by page
    seen = {}
    for c in candidates:
        seen[c['page']] = c
    candidates = [seen[k] for k in sorted(seen.keys())]

    # build chapter ranges from candidates that look like real section starts
    starts = [c for c in candidates]
    if not starts:
        starts = [{'page': 1, 'type': 'start', 'line': 'START'}]

    chapters = []
    total_pages = len(pages)
    last_page_no = int(pages[-1].stem.split('-')[-1]) if pages else 0

    for i, s in enumerate(starts):
        start = s['page']
        end = (starts[i+1]['page'] - 1) if i+1 < len(starts) else last_page_no
        chapters.append({
            'chapterIndex': i+1,
            'startPage': start,
            'endPage': end,
            'hint': s,
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        'pagesDir': str(PAGES_DIR),
        'pages': last_page_no,
        'candidates': candidates,
        'chapters': chapters,
    }, indent=2, ensure_ascii=False), 'utf-8')

    print(f'Wrote {OUT}')
    print(f'Candidates: {len(candidates)}  Chapters: {len(chapters)}')


if __name__ == '__main__':
    main()

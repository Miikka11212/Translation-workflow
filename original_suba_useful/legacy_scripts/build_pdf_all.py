#!/usr/bin/env python3
"""Build a single PDF from all translated page files.

Input dir:  ~/Desktop/suba/out/zh_out/pages/*.zh.txt
Output:     ~/Desktop/suba/out/zh_out/pdfs/suba.zh.pdf

Usage:
  python3 build_pdf_all.py --out suba.zh.pdf --pages-dir ./pages
"""

import argparse
from pathlib import Path
import subprocess
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--pages-dir', required=True)
    ap.add_argument('--make-pdf', default=str(Path(__file__).with_name('make_pdf.py')))
    args = ap.parse_args()

    pages_dir = Path(args.pages_dir).expanduser()
    out = Path(args.out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)

    pages = sorted(pages_dir.glob('page-*.zh.txt'))
    if not pages:
        raise SystemExit(f'No translated pages found in {pages_dir}')

    # Avoid shell arg length limits by writing a list file and invoking make_pdf in chunks,
    # then merging.
    tmp_dir = out.parent / '.tmp_chunks'
    tmp_dir.mkdir(parents=True, exist_ok=True)

    chunk_size = 80
    chunk_pdfs = []
    for i in range(0, len(pages), chunk_size):
        chunk = pages[i:i+chunk_size]
        chunk_pdf = tmp_dir / f'chunk-{i//chunk_size:03d}.pdf'
        cmd = [sys.executable, args.make_pdf, '--out', str(chunk_pdf), *[str(p) for p in chunk]]
        subprocess.check_call(cmd)
        chunk_pdfs.append(chunk_pdf)

    # Merge chunks with PyMuPDF (fitz)
    import fitz

    merged = fitz.open()
    for pdf in chunk_pdfs:
        src = fitz.open(str(pdf))
        merged.insert_pdf(src)
        src.close()

    merged.save(str(out))
    merged.close()

    print('wrote', out)


if __name__ == '__main__':
    main()

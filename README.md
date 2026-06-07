# Suba Clean OCR Project

This project was generated from:

- PDF: `/Users/miikka/Downloads/otherworldscomic0000cyra_1.pdf`
- Existing OCR folder: `/Users/miikka/Desktop/suba/out/ocr/pages`

Outputs:

- `clean_pages/page-XXXX.txt`: cleaned English source pages in reading order.
- `manifest.json`: maps each clean page back to the original PDF page.
- `skipped_pages.json`: pages skipped as front matter, blank/noise, or back artifacts.
- `scripts/clean_suba_pages.py`: reproducible cleanup script.

Cleaning rules:

- Keep book text from PDF pages 11-252.
- Skip blank/noise pages: 22, 126.
- Remove running headers at the top of pages.
- Remove printed page numbers and roman numerals at the bottom.
- De-hyphenate OCR line breaks like `philo-\nsopher`.

Generated clean pages: 240
Skipped pages recorded: 16

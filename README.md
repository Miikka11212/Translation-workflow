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

Book Translation Workflow Documentation
1. Source Preparation
The project started from a scanned English PDF. The first step was to compare the PDF with the existing OCR text files to confirm that the OCR pages matched the original PDF page order.

After confirming the match, the OCR text was cleaned. This included removing repeated running headers at the top of pages, printed page numbers at the bottom, blank scan pages, noisy OCR artifacts, and non-book front/back matter that did not belong to the main text.

The result was a clean set of English text pages in reading order.

2. Manual Corrections
After the initial cleanup, some remaining page numbers or OCR mistakes were manually corrected. The contents pages were also manually added because the original contents formatting was difficult to extract cleanly from OCR.

These manually edited text files became the final English source material for the translation workflow.

3. English PDF Generation
The cleaned English text files were first combined into an English PDF. The contents pages were placed at the front, followed by the cleaned book text in order.

Several layout versions were tested. The final English version kept each cleaned text page as a separate PDF page, while improving font size and line wrapping.

4. Continuous Text Preparation for Translation
For translation, page-by-page translation was avoided because some sentences and paragraphs were split across page boundaries. Translating those pages separately would cause context loss and awkward Chinese output.

Instead, all cleaned English text pages were combined into one continuous English source. During this process, paragraph breaks caused only by original page boundaries were repaired, so unfinished sentences continued naturally into the next page’s text.

The combined English source was then split into manageable translation chunks. Each chunk was large enough to preserve context but small enough to translate reliably.

5. Translation Prompt Preparation
A translation prompt was generated for each chunk. The prompts instructed the model to translate the English literary text into fluent modern Simplified Chinese.

The rules included preserving headings and paragraph breaks, avoiding classical Chinese, keeping the tone literary but readable, not summarizing or adding explanations, and using a consistent glossary for names, places, and titles.

A glossary was also created to keep recurring names and concepts consistent across all chunks.

6. Chinese Translation
The translation was done chunk by chunk using the OpenAI API. The process was resumable, meaning completed chunks were saved immediately and skipped if the script was restarted.

Each English chunk produced one corresponding Chinese text chunk. After all chunks were translated, the Chinese chunks were combined into one complete Chinese text file.

7. Chinese PDF Generation
The final Chinese text was converted into a PDF. The layout was refined after several passes.

The final PDF layout includes bold and centered titles, clearer spacing around section headings, lighter body text for readability, smaller footnote styling, page numbers, and improved spacing between paragraphs.

The body font was changed after discovering that the first Chinese font rendered too heavily. A lighter Chinese font was used for the main text, while a heavier font was kept for headings.

8. Final Outputs
The final result includes a cleaned English source, translation chunks, translated Chinese chunks, combined Chinese text, and a styled Chinese PDF.

The workflow is reproducible because each major step is handled by a script: cleaning OCR, preparing translation chunks, translating through the API, and building the final PDF.


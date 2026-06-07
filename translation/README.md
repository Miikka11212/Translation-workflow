# Suba Translation Prep

Generated from the edited txt files in `/Users/miikka/Desktop/suba_clean`.

Files:

- `source_en_combined.txt`: one continuous English source with broken page-boundary paragraphs repaired.
- `chunks_en/`: English chunks for translation.
- `prompts/`: ready-to-use prompts for each chunk.
- `chunks_zh/`: place translated Chinese chunks here using the same filenames.
- `glossary.md`: name/title consistency guide.
- `source_manifest.json`: source file to combined-text block map.
- `chunk_manifest.json`: chunk sizes and prompt paths.

Chunk count: 81
Target chunk size: 1200 English words

Workflow:

1. Translate each `chunks_en/chunk-XXXX.txt` using the matching `prompts/chunk-XXXX.prompt.txt`.
2. Save the Chinese output as `chunks_zh/chunk-XXXX.txt`.
3. After all translated chunks exist, run:

   `python3 scripts/build_suba_chinese_pdf.py --project-dir /Users/miikka/Desktop/suba_clean`

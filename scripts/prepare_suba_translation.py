#!/usr/bin/env python3
"""Prepare Suba clean English text for Chinese translation.

This joins the edited page txt files into a continuous source, repairing
paragraphs split across original page boundaries, then creates manageable
translation chunks.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path


DEFAULT_PROJECT_DIR = Path("/Users/miikka/Desktop/suba_clean")
TERMINAL_RE = re.compile(r"[.!?;:’”\"）)]$")
HEADING_RE = re.compile(r"^[A-Z0-9][A-Z0-9 '\u2019,;:\-.]+$")


GLOSSARY = """# Translation Glossary

Use Simplified Chinese and modern literary Mandarin.

- Cyrano de Bergerac: 西拉诺·德·贝热拉克
- Cyrano: 西拉诺
- Other Worlds: 异世界
- The States and Empires of the Moon: 月球诸国与诸帝国
- The States and Empires of the Sun: 太阳诸国与诸帝国
- Geoffrey Strachan: 杰弗里·斯特拉坎
- Campanella: 康帕内拉
- Descartes: 笛卡尔
- Gassendi: 伽森狄
- Kepler: 开普勒
- Copernicus: 哥白尼
- Epicurus: 伊壁鸠鲁
- Pythagoras: 毕达哥拉斯
- Democritus: 德谟克利特
- Girolamo Cardano: 吉罗拉莫·卡尔达诺
- Cardano: 卡尔达诺
- Prometheus: 普罗米修斯
- The Moon: 月球
- The Sun: 太阳
"""


PROMPT = """Translate the following English literary text into fluent modern Simplified Chinese.

Rules:
- Preserve headings and paragraph breaks.
- Use natural modern Mandarin, not classical Chinese.
- Do not summarize, explain, omit, or add commentary.
- Keep dialogue and quotation marks readable in Chinese.
- Keep proper names consistent with the glossary.
- Output only the Chinese translation.

Glossary:
{glossary}

Text:
{text}
"""


def project_files(project_dir: Path) -> tuple[list[Path], list[Path]]:
    menu_files = [project_dir / "menu1.txt", project_dir / "menu2.txt"]
    menu_files = [path for path in menu_files if path.exists()]
    page_files = sorted((project_dir / "clean_pages").glob("page-*.txt"))
    return menu_files, page_files


def normalize_block(block: str) -> str:
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    if not lines:
        return ""
    if is_heading_lines(lines):
        return "\n".join(lines)
    text = " ".join(lines)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def file_blocks(path: Path) -> list[str]:
    raw = path.read_text("utf-8", errors="ignore")
    raw = raw.replace("\r\n", "\n").replace("\r", "\n").strip()
    blocks = []
    for block in re.split(r"\n\s*\n", raw):
        normalized = normalize_block(block)
        if normalized:
            blocks.append(normalized)
    return blocks


def menu_blocks(path: Path) -> list[str]:
    raw = path.read_text("utf-8", errors="ignore")
    raw = raw.replace("\r\n", "\n").replace("\r", "\n").strip()
    return [block.strip() for block in re.split(r"\n\s*\n", raw) if block.strip()]


def is_heading_lines(lines: list[str]) -> bool:
    joined = " ".join(lines).strip()
    if not joined:
        return False
    if len(lines) <= 2 and len(joined) <= 90:
        return True
    if len(lines) <= 3 and len(joined) <= 110 and HEADING_RE.match(joined.upper()):
        return True
    return False


def is_heading_text(text: str) -> bool:
    one_line = " ".join(text.split())
    if len(one_line) <= 90 and HEADING_RE.match(one_line.upper()):
        return True
    if len(one_line) <= 80 and len(one_line.split()) <= 8 and not TERMINAL_RE.search(one_line):
        return True
    return False


def should_merge_boundary(previous: str, current: str) -> bool:
    previous = " ".join(previous.split())
    current = " ".join(current.split())
    if not previous or not current:
        return False
    if is_heading_text(previous) or is_heading_text(current):
        return False
    if TERMINAL_RE.search(previous):
        return False
    return True


def combine_source(menu_files: list[Path], page_files: list[Path]) -> tuple[str, list[dict[str, object]]]:
    sections: list[str] = []
    manifest: list[dict[str, object]] = []

    for path in menu_files:
        blocks = menu_blocks(path)
        start = len(sections) + 1
        sections.extend(blocks)
        manifest.append({"source": path.name, "start_block": start, "end_block": len(sections), "blocks": len(blocks)})

    previous_blocks_len = len(sections)
    for path in page_files:
        blocks = file_blocks(path)
        start = len(sections) + 1
        merged_with_previous = False
        if sections and blocks and should_merge_boundary(sections[-1], blocks[0]):
            sections[-1] = f"{sections[-1]} {blocks[0]}"
            blocks = blocks[1:]
            merged_with_previous = True
            start = len(sections)
        sections.extend(blocks)
        manifest.append(
            {
                "source": f"clean_pages/{path.name}",
                "start_block": start,
                "end_block": len(sections),
                "blocks_added": len(sections) - previous_blocks_len,
                "merged_first_block_with_previous_page": merged_with_previous,
            }
        )
        previous_blocks_len = len(sections)

    return "\n\n".join(sections).strip() + "\n", manifest


def split_chunks(text: str, target_words: int) -> list[str]:
    blocks = [block.strip() for block in re.split(r"\n\s*\n", text.strip()) if block.strip()]
    chunks: list[str] = []
    current: list[str] = []
    current_words = 0

    for block in blocks:
        words = len(block.split())
        if current and current_words + words > target_words:
            chunks.append("\n\n".join(current).strip() + "\n")
            current = []
            current_words = 0
        current.append(block)
        current_words += words

    if current:
        chunks.append("\n\n".join(current).strip() + "\n")
    return chunks


def clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", default=str(DEFAULT_PROJECT_DIR))
    parser.add_argument("--target-words", type=int, default=1200)
    args = parser.parse_args()

    project_dir = Path(args.project_dir).expanduser()
    menu_files, page_files = project_files(project_dir)
    combined, source_manifest = combine_source(menu_files, page_files)

    translation_dir = project_dir / "translation"
    chunks_en = translation_dir / "chunks_en"
    chunks_zh = translation_dir / "chunks_zh"
    prompts_dir = translation_dir / "prompts"
    clean_dir(chunks_en)
    clean_dir(prompts_dir)
    chunks_zh.mkdir(parents=True, exist_ok=True)

    translation_dir.mkdir(parents=True, exist_ok=True)
    (translation_dir / "source_en_combined.txt").write_text(combined, "utf-8")
    (translation_dir / "source_manifest.json").write_text(json.dumps(source_manifest, indent=2, ensure_ascii=False), "utf-8")
    (translation_dir / "glossary.md").write_text(GLOSSARY, "utf-8")

    chunks = split_chunks(combined, args.target_words)
    chunk_manifest = []
    for index, chunk in enumerate(chunks, 1):
        name = f"chunk-{index:04d}.txt"
        chunks_en.joinpath(name).write_text(chunk, "utf-8")
        prompt_text = PROMPT.format(glossary=GLOSSARY.strip(), text=chunk.strip())
        prompts_dir.joinpath(name.replace(".txt", ".prompt.txt")).write_text(prompt_text, "utf-8")
        chunk_manifest.append({"chunk": index, "source": f"chunks_en/{name}", "prompt": f"prompts/{name.replace('.txt', '.prompt.txt')}", "words": len(chunk.split())})

    (translation_dir / "chunk_manifest.json").write_text(json.dumps(chunk_manifest, indent=2, ensure_ascii=False), "utf-8")
    readme = f"""# Suba Translation Prep

Generated from the edited txt files in `{project_dir}`.

Files:

- `source_en_combined.txt`: one continuous English source with broken page-boundary paragraphs repaired.
- `chunks_en/`: English chunks for translation.
- `prompts/`: ready-to-use prompts for each chunk.
- `chunks_zh/`: place translated Chinese chunks here using the same filenames.
- `glossary.md`: name/title consistency guide.
- `source_manifest.json`: source file to combined-text block map.
- `chunk_manifest.json`: chunk sizes and prompt paths.

Chunk count: {len(chunks)}
Target chunk size: {args.target_words} English words

Workflow:

1. Translate each `chunks_en/chunk-XXXX.txt` using the matching `prompts/chunk-XXXX.prompt.txt`.
2. Save the Chinese output as `chunks_zh/chunk-XXXX.txt`.
3. After all translated chunks exist, run:

   `python3 scripts/build_suba_chinese_pdf.py --project-dir {project_dir}`
"""
    (translation_dir / "README.md").write_text(readme, "utf-8")

    print(f"Combined source: {translation_dir / 'source_en_combined.txt'}")
    print(f"Chunks: {len(chunks)} in {chunks_en}")
    print(f"Prompts: {prompts_dir}")
    print(f"Chinese output folder: {chunks_zh}")


if __name__ == "__main__":
    main()

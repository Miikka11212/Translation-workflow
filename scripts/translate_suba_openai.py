#!/usr/bin/env python3
"""Translate prepared Suba chunks with the OpenAI Responses API.

Reads:
  /Users/miikka/Desktop/suba_clean/.env
  /Users/miikka/Desktop/suba_clean/translation/prompts/chunk-XXXX.prompt.txt

Writes:
  /Users/miikka/Desktop/suba_clean/translation/chunks_zh/chunk-XXXX.txt

The script is resumable: existing non-empty translated chunks are skipped unless
--overwrite is passed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_PROJECT_DIR = Path("/Users/miikka/Desktop/suba_clean")
DEFAULT_MODEL = "gpt-5.2"
API_URL = "https://api.openai.com/v1/responses"


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text("utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value


def output_text(response: dict) -> str:
    if isinstance(response.get("output_text"), str):
        return response["output_text"].strip()

    parts: list[str] = []
    for item in response.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if isinstance(text, str):
                parts.append(text)
    return "\n".join(parts).strip()


def call_openai(prompt: str, model: str, api_key: str, retries: int = 4) -> str:
    payload = {
        "model": model,
        "input": prompt,
    }
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                data = json.loads(response.read().decode("utf-8"))
            text = output_text(data)
            if not text:
                raise RuntimeError(f"OpenAI response had no output text: {json.dumps(data)[:800]}")
            return text
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            retryable = exc.code in {408, 409, 429, 500, 502, 503, 504}
            if not retryable or attempt == retries:
                raise RuntimeError(f"OpenAI API error {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt == retries:
                raise RuntimeError(f"Network error after {retries} attempts: {exc}") from exc

        sleep_s = min(60, 2**attempt)
        print(f"retrying in {sleep_s}s after attempt {attempt}/{retries}", flush=True)
        time.sleep(sleep_s)

    raise RuntimeError("unreachable")


def prompt_files(project_dir: Path) -> list[Path]:
    return sorted((project_dir / "translation" / "prompts").glob("chunk-*.prompt.txt"))


def output_path_for_prompt(project_dir: Path, prompt_path: Path) -> Path:
    name = prompt_path.name.replace(".prompt.txt", ".txt")
    return project_dir / "translation" / "chunks_zh" / name


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", default=str(DEFAULT_PROJECT_DIR))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).expanduser()
    load_env(project_dir / ".env")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit(f"OPENAI_API_KEY was not found in {project_dir / '.env'}")

    prompts = prompt_files(project_dir)
    if not prompts:
        raise SystemExit(f"No prompt files found in {project_dir / 'translation' / 'prompts'}")

    selected = prompts[args.start - 1 :]
    if args.limit is not None:
        selected = selected[: args.limit]

    out_dir = project_dir / "translation" / "chunks_zh"
    out_dir.mkdir(parents=True, exist_ok=True)

    total = len(selected)
    for index, prompt_path in enumerate(selected, 1):
        out_path = output_path_for_prompt(project_dir, prompt_path)
        if out_path.exists() and out_path.stat().st_size > 20 and not args.overwrite:
            print(f"skip {out_path.name} ({index}/{total})", flush=True)
            continue

        prompt = prompt_path.read_text("utf-8", errors="ignore")
        print(f"translate {prompt_path.name} -> {out_path.name} ({index}/{total})", flush=True)
        zh = call_openai(prompt, args.model, api_key)
        out_path.write_text(zh.strip() + "\n", "utf-8")
        print(f"wrote {out_path}", flush=True)

    print("done", flush=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        raise SystemExit(130)

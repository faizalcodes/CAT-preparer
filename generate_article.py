"""
generate_article.py

Pipeline: URL -> Firecrawl (clean markdown) -> AI vocab extraction (OpenRouter, free model)
         -> single .md file with frontmatter + article body + word bank

Usage:
    python generate_article.py "https://aeon.co/essays/when-my-ties-to-my-mother-faded-so-did-my-memories" \
        --category "psychology-philosophy" --part 1

Environment variables (put these in a .env file or export them - do NOT hardcode keys in this file):
    FIRECRAWL_API_KEY
    OPENROUTER_API_KEY
"""

import os
import re
import json
import argparse
import requests
from datetime import date
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

FIRECRAWL_URL = "https://api.firecrawl.dev/v1/scrape"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Free-tier model on OpenRouter - swap if this one gets deprecated/rate limited
VOCAB_MODEL = "tencent/hy3:free"

OUTPUT_ROOT = Path("articles")  # articles/<category>/part-<n>.md


def slugify(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9\s-]", "", text).strip().lower()
    return re.sub(r"[\s_]+", "-", text)


def scrape_article(url: str) -> dict:
    """Calls Firecrawl and returns clean markdown + metadata for the article."""
    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        raise RuntimeError("Set FIRECRAWL_API_KEY as an environment variable first.")

    resp = requests.post(
        FIRECRAWL_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "url": url,
            "formats": ["markdown"],
            # onlyMainContent strips nav/ads/audio-player/footer clutter for you
            "onlyMainContent": True,
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()

    if not data.get("success", True) and "data" not in data:
        raise RuntimeError(f"Firecrawl error: {data}")

    payload = data.get("data", data)
    return {
        "title": payload.get("metadata", {}).get("title", "Untitled"),
        "markdown": payload.get("markdown", ""),
        "url": url,
    }


# def extract_vocab(article_markdown: str) -> list[dict]:
#     """Sends the article text to an LLM and asks for CAT-level hard words + meanings + examples."""
#     api_key = os.environ.get("OPENROUTER_API_KEY")
#     if not api_key:
#         raise RuntimeError("Set OPENROUTER_API_KEY as an environment variable first.")

#     prompt = f"""You are helping a student preparing for the CAT exam (Common Admission Test) build a
# vocabulary list from a reading passage. Read the article below and pick out 10-20 words that are
# genuinely hard / GRE-CAT level (not everyday words), that a student might need to look up.

# For each word return:
# - word: the word as it appears (lowercase, base form is fine)
# - meaning: a simple, one-line dictionary-style definition
# - example: ONE short original example sentence using the word (do not copy a sentence from the article)

# Return ONLY valid JSON, an array of objects with keys "word", "meaning", "example". No markdown
# fences, no preamble, no explanation.

# ARTICLE:
# {article_markdown[:12000]}
# """

#     resp = requests.post(
#         OPENROUTER_URL,
#         headers={
#             "Authorization": f"Bearer {api_key}",
#             "Content-Type": "application/json",
#         },
#         json={
#             "model": VOCAB_MODEL,
#             "messages": [{"role": "user", "content": prompt}],
#             "temperature": 0.3,
#         },
#         timeout=90,
#     )
#     if resp.status_code != 200:
#         print("OpenRouter error response:", resp.text)
#     resp.raise_for_status()
#     raw = resp.json()["choices"][0]["message"]["content"]

#     # Models sometimes wrap JSON in ```json fences anyway - strip defensively
#     cleaned = re.sub(r"^```json|```$", "", raw.strip(), flags=re.MULTILINE).strip()
#     try:
#         words = json.loads(cleaned)
#     except json.JSONDecodeError:
#         # last resort: pull out the first {...} or [...] block
#         match = re.search(r"\[.*\]", cleaned, re.DOTALL)
#         words = json.loads(match.group(0)) if match else []

#     return words

VOCAB_MODEL = "tencent/hy3:free"


def extract_vocab(article_markdown: str) -> list[dict]:
    """Sends the article text to an LLM and asks for CAT-level hard words + meanings + examples."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("Set OPENROUTER_API_KEY as an environment variable first.")

    prompt = f"""You are helping a student preparing for the CAT exam (Common Admission Test) build a
vocabulary list from a reading passage. Read the article below and pick out 10-20 words that are
genuinely hard / GRE-CAT level (not everyday words), that a student might need to look up.

For each word return:
- word: the word as it appears (lowercase, base form is fine)
- meaning: a simple, one-line dictionary-style definition
- example: ONE short original example sentence using the word (do not copy a sentence from the article)

Return ONLY valid JSON, an array of objects with keys "word", "meaning", "example". No markdown
fences, no preamble, no explanation.

ARTICLE:
{article_markdown[:12000]}
"""

    resp = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": VOCAB_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "reasoning": {"enabled": True},
        },
        timeout=90,
    )
    if resp.status_code != 200:
        print("OpenRouter error response:", resp.text)
    resp.raise_for_status()
    raw = resp.json()["choices"][0]["message"]["content"]

    # Models sometimes wrap JSON in ```json fences anyway - strip defensively
    cleaned = re.sub(r"^```json|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        words = json.loads(cleaned)
    except json.JSONDecodeError:
        # last resort: pull out the first {...} or [...] block
        match = re.search(r"\[.*\]", cleaned, re.DOTALL)
        words = json.loads(match.group(0)) if match else []

    return words

def build_markdown_file(article: dict, words: list[dict], category: str, part: int) -> str:
    frontmatter = (
        "---\n"
        f"title: \"{article['title']}\"\n"
        f"source: \"{article['url']}\"\n"
        f"category: \"{category}\"\n"
        f"part: {part}\n"
        f"date_added: \"{date.today().isoformat()}\"\n"
        "---\n\n"
    )

    body = article["markdown"].strip() + "\n\n"

    word_bank = "## Word Bank\n\n"
    for w in words:
        word_bank += f"### {w.get('word', '').strip()}\n"
        word_bank += f"**Meaning:** {w.get('meaning', '').strip()}\n\n"
        word_bank += f"**Example:** {w.get('example', '').strip()}\n\n"

    return frontmatter + body + "\n---\n\n" + word_bank


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="Article URL to scrape")
    parser.add_argument("--category", required=True, help="e.g. psychology-philosophy")
    parser.add_argument("--part", type=int, required=True, help="Sequential part number within the category")
    args = parser.parse_args()

    print(f"Scraping {args.url} via Firecrawl...")
    article = scrape_article(args.url)
    print(f"Got article: {article['title']!r} ({len(article['markdown'])} chars)")

    print("Extracting hard words with AI...")
    words = extract_vocab(article["markdown"])
    print(f"Found {len(words)} vocabulary words")

    out_dir = OUTPUT_ROOT / slugify(args.category)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"part-{args.part}.md"

    out_path.write_text(build_markdown_file(article, words, args.category, args.part), encoding="utf-8")
    print(f"Saved -> {out_path}")


if __name__ == "__main__":
    main()

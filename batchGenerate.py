"""
batch_generate.py

Scrape a whole list of URLs for one category in one go. Part numbers are
auto-assigned as the next available number in that category's folder, so you
don't have to track them by hand.

Setup - create a text file per category, e.g. urls_psychology.txt:

    https://aeon.co/essays/when-my-ties-to-my-mother-faded-so-did-my-memories
    https://aeon.co/essays/another-article
    https://example.com/a-third-one

Then run:
    python batch_generate.py urls_psychology.txt --category psychology-philosophy

It will skip any URL that's already been scraped into that category (checked
by comparing the "source" field already stored in existing MD files), so it's
safe to re-run after adding new lines to the same file.
"""

import argparse
import time
from pathlib import Path

import frontmatter

from generate_article import scrape_article, extract_vocab, build_markdown_file, OUTPUT_ROOT, slugify


def already_scraped_urls(category_dir: Path) -> set:
    urls = set()
    if not category_dir.exists():
        return urls
    for md_file in category_dir.glob("part-*.md"):
        try:
            post = frontmatter.load(md_file)
            if post.get("source"):
                urls.add(post["source"])
        except Exception:
            pass
    return urls


def next_part_number(category_dir: Path) -> int:
    if not category_dir.exists():
        return 1
    existing = [int(p.stem.split("-")[1]) for p in category_dir.glob("part-*.md")]
    return max(existing, default=0) + 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("urls_file", help="Text file with one article URL per line")
    parser.add_argument("--category", required=True, help="e.g. psychology-philosophy")
    args = parser.parse_args()

    urls = [
        line.strip()
        for line in Path(args.urls_file).read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    category_dir = OUTPUT_ROOT / slugify(args.category)
    done_urls = already_scraped_urls(category_dir)

    for url in urls:
        if url in done_urls:
            print(f"skip (already scraped): {url}")
            continue

        part = next_part_number(category_dir)
        try:
            print(f"[{part}] scraping {url} ...")
            article = scrape_article(url)
            print(f"    got '{article['title']}' ({len(article['markdown'])} chars) — extracting vocab...")
            words = extract_vocab(article["markdown"])

            category_dir.mkdir(parents=True, exist_ok=True)
            out_path = category_dir / f"part-{part}.md"
            out_path.write_text(build_markdown_file(article, words, args.category, part), encoding="utf-8")
            print(f"    saved -> {out_path} ({len(words)} words)")

            done_urls.add(url)
            time.sleep(2)  # be polite to the free-tier APIs
        except Exception as e:
            print(f"    FAILED: {url} -> {e}")
            continue

    print("Done.")


if __name__ == "__main__":
    main()
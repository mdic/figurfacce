#!/usr/bin/env python3
"""
extract_links_bs2.py – two-pattern BeautifulSoup link harvester
---------------------------------------------------------------
pip install beautifulsoup4 tqdm   # once

examples
--------
# Typical run – resolve /relative urls, append to links.txt
python extract_links_bs2.py pages/ links.txt --base https://www.theguardian.com

# If your download set mixes hosts, just omit --base; you'll get raw hrefs.
# Guardian set – make relative links absolute:
python extract_links_bs2.py guardian_pages/ guardian_links.txt \
       --base https://www.theguardian.com

# Il Fatto pages – raw hrefs are already absolute → no --base needed:
python extract_links_bs2.py fatto_pages/ fatto_links.txt
"""

from __future__ import annotations
import argparse, pathlib, urllib.parse as up
from bs4 import BeautifulSoup
from tqdm import tqdm


# ───────────────────────── helpers ───────────────────────────────────────────
def make_absolute(href: str, base: str | None) -> str:
    """Turn /relative/path into absolute using base; leave absolute links untouched."""
    if base and href.startswith(("/", "./")):
        return up.urljoin(base, href)
    return href


def extract_from_file(path: pathlib.Path) -> list[str]:
    """Return every matching href from a single HTML file."""
    html = path.read_bytes()  # let BS sniff the encoding
    soup = BeautifulSoup(html, "html.parser")

    links: list[str] = []

    # Pattern 1 – <a class="dcr-2yd10d" ...>
    links.extend(
        a["href"] for a in soup.find_all("a", class_="dcr-2yd10d") if a.get("href")
    )

    # Pattern 2 – <h3 class="ifq-news-category__title"><a href="...">
    for h3 in soup.find_all("h3", class_="ifq-news-category__title"):
        a = h3.find("a", href=True)
        if a:
            links.append(a["href"])

    return links


# ───────────────────────── main ──────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser(description="Extract Guardian + Il Fatto links")
    ap.add_argument(
        "html_dir", type=pathlib.Path, help="Directory with downloaded *.html files"
    )
    ap.add_argument(
        "output_file", type=pathlib.Path, help="TXT file to write/append links"
    )
    ap.add_argument(
        "--base", default=None, help="Optional base URL for resolving relative paths"
    )
    args = ap.parse_args()

    html_files = sorted(args.html_dir.glob("**/*.html"))
    if not html_files:
        print(f"No .html files found inside {args.html_dir}")
        return

    collected: list[str] = []
    for f in tqdm(html_files, desc="Scanning"):
        for href in extract_from_file(f):
            collected.append(make_absolute(href, args.base))

    # de‑duplicate while preserving first‑seen order
    seen: set[str] = set()
    unique_links = [h for h in collected if not (h in seen or seen.add(h))]

    mode = "a" if args.output_file.exists() else "w"
    with args.output_file.open(mode, encoding="utf‑8") as out:
        out.writelines(link + "\n" for link in unique_links)

    print(
        f"✔ Added {len(unique_links)} unique links from {len(html_files)} files → {args.output_file}"
    )


if __name__ == "__main__":
    main()

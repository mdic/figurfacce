#!/usr/bin/env python3
"""
extract_links_bs.py ─ BeautifulSoup version
------------------------------------------
usage
-----
    pip install beautifulsoup4 tqdm   # ← only once
    python extract_links_bs.py pages/ links.txt --base https://www.theguardian.com
"""

from __future__ import annotations
import argparse, pathlib, urllib.parse as up
from bs4 import BeautifulSoup
from tqdm import tqdm


def extract_from_file(path: pathlib.Path, *, tag_class: str) -> list[str]:
    """Return all hrefs from <a class="tag_class"> in one HTML file."""
    html = path.read_bytes()  # raw bytes → let BS handle encoding
    soup = BeautifulSoup(html, "html.parser")  # or "lxml" if you prefer
    return [
        a.get("href") for a in soup.find_all("a", class_=tag_class) if a.get("href")
    ]


def make_absolute(href: str, base: str | None) -> str:
    """If href is relative and base is supplied, join them; otherwise return href unchanged."""
    if base and href.startswith(("/", "./")):
        return up.urljoin(base, href)
    return href


def main() -> None:
    ap = argparse.ArgumentParser(description="Extract links with BeautifulSoup")
    ap.add_argument(
        "html_dir", type=pathlib.Path, help="Directory containing *.html files"
    )
    ap.add_argument(
        "output_file", type=pathlib.Path, help="TXT file to write/append links"
    )
    ap.add_argument("--base", default=None, help="Base URL to resolve relative paths")
    ap.add_argument(
        "--class",
        dest="css_class",
        default="dcr-2yd10d",
        help='Target <a> class (default "dcr-2yd10d")',
    )
    args = ap.parse_args()

    html_files = sorted(args.html_dir.glob("**/*.html"))
    if not html_files:
        print(f"No .html files found inside {args.html_dir}")
        return

    collected: list[str] = []
    for f in tqdm(html_files, desc="Scanning"):
        hrefs = extract_from_file(f, tag_class=args.css_class)
        if hrefs:
            collected.extend(make_absolute(h, args.base) for h in hrefs)

    # dedupe but preserve discovery order
    seen: set[str] = set()
    deduped = [h for h in collected if not (h in seen or seen.add(h))]

    mode = "a" if args.output_file.exists() else "w"
    with args.output_file.open(mode, encoding="utf‑8") as out:
        for link in deduped:
            out.write(link + "\n")

    print(
        f"✔ Extracted {len(deduped)} unique links from {len(html_files)} files → {args.output_file}"
    )


if __name__ == "__main__":
    main()

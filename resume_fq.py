"""
missing_urls.py – filter out URLs already present in <doc url="…"> XMLs
-----------------------------------------------------------------------
Requirements: none beyond the Python standard library.

usage
-----
    python missing_urls.py urls.txt xml_dir/ missing_urls.txt
"""

from __future__ import annotations
import argparse, pathlib, xml.etree.ElementTree as ET
from tqdm import tqdm  # optional progress bar; pip install tqdm  (safe to remove)


# ───────────────────────── helpers ───────────────────────────────────────────
def load_txt_urls(path: pathlib.Path) -> list[str]:
    """Return a list of unique, stripped URLs from a text file."""
    seen: set[str] = set()
    urls: list[str] = []
    for line in path.read_text(encoding="utf‑8").splitlines():
        url = line.strip()
        if url and url not in seen:
            urls.append(url)
            seen.add(url)
    return urls


def collect_downloaded_urls(xml_root_dir: pathlib.Path) -> set[str]:
    """Walk xml_root_dir/**.xml and collect every root <doc url="…"> attribute."""
    downloaded: set[str] = set()
    xml_files = list(xml_root_dir.glob("**/*.xml"))

    for xf in tqdm(xml_files, desc="Scanning XMLs"):
        try:
            tree = ET.parse(xf)
            root = tree.getroot()
            url_attr = root.attrib.get("url")
            if url_attr:
                downloaded.add(url_attr.strip())
        except ET.ParseError:
            # Skip malformed XMLs but warn
            tqdm.write(f"⚠ malformed XML ignored: {xf}")

    return downloaded


# ───────────────────────── main ──────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser(
        description="Create list of URLs not found in XML archive"
    )
    ap.add_argument(
        "url_list", type=pathlib.Path, help="TXT file with one URL per line"
    )
    ap.add_argument(
        "xml_dir",
        type=pathlib.Path,
        help="Directory containing *.xml files (scanned recursively)",
    )
    ap.add_argument(
        "output_file", type=pathlib.Path, help="TXT file to write missing URLs to"
    )
    args = ap.parse_args()

    # 1. urls we want
    wanted = load_txt_urls(args.url_list)
    print(f"Loaded {len(wanted):,} URLs from {args.url_list}")

    # 2. urls already downloaded
    downloaded = collect_downloaded_urls(args.xml_dir)
    print(f"Found {len(downloaded):,} downloaded URLs inside XMLs")

    # 3. difference
    missing = [u for u in wanted if u not in downloaded]
    print(f"{len(missing):,} URLs remain to download")

    # 4. write output
    args.output_file.write_text(
        "\n".join(missing) + ("\n" if missing else ""), encoding="utf‑8"
    )
    print(f"✔ Missing‑URL list written to {args.output_file}")


if __name__ == "__main__":
    main()

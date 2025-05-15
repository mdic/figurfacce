"""
dedupe_xml_by_url.py  –  keep one XML per article URL, delete the extras
-----------------------------------------------------------------------
usage:
    python dedupe_xml_by_url.py <xml_dir> [--dry-run]

• Recursively scans <xml_dir>/*.xml
• Extracts the 'url' attribute of the root tag (<doc> or <text>)
• If the same URL appears in >1 file:
      – keeps the first file seen
      – deletes the rest (unless --dry-run)

A short report is printed at the end.
"""

from __future__ import annotations
import argparse, pathlib, xml.etree.ElementTree as ET, os, sys
from collections import defaultdict


def collect_urls(root_dir: pathlib.Path) -> dict[str, list[pathlib.Path]]:
    """Return {url: [file1, file2, …]}"""
    mapping: dict[str, list[pathlib.Path]] = defaultdict(list)
    for xml_path in root_dir.rglob("*.xml"):
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            url = root.attrib.get("url")
            print(url)
            if url:
                mapping[url].append(xml_path)
            else:
                print(f"⚠  No 'url' attr in {xml_path}", file=sys.stderr)
        except ET.ParseError as e:
            print(f"⚠  Malformed XML {xml_path}: {e}", file=sys.stderr)
    return mapping


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Delete duplicate XMLs that share the same article URL"
    )
    ap.add_argument(
        "xml_dir", type=pathlib.Path, help="Directory containing original XMLs"
    )
    ap.add_argument(
        "--dry-run", action="store_true", help="Only list duplicates, do not delete"
    )
    args = ap.parse_args()

    if not args.xml_dir.exists():
        sys.exit(f"Directory {args.xml_dir} does not exist")

    url_map = collect_urls(args.xml_dir)
    dup_count = 0
    del_files: list[pathlib.Path] = []

    for url, files in url_map.items():
        if len(files) > 1:
            dup_count += len(files) - 1
            # keep the first file, delete the others
            for extra_file in files[1:]:
                del_files.append(extra_file)

    if args.dry_run:
        print(f"\nFound {dup_count} duplicate file(s). Would delete:")
        for f in del_files:
            print("  ", f)
    else:
        for f in del_files:
            try:
                os.remove(f)
            except OSError as e:
                print(f"⚠  Could not delete {f}: {e}", file=sys.stderr)
        print(
            f"\nDeleted {dup_count} duplicate file(s). Remaining XMLs: {len(url_map)}"
        )


if __name__ == "__main__":
    main()

"""
download_range.py – numbered page crawler with curl‑cffi ≥ 0.6
--------------------------------------------------------------
• Page 1 is fetched as the bare URL when no {n} placeholder is present.
• Any pages that fail to download are listed at the end.
# 1. First page is bare URL, others get ?page=N
python download_range.py "https://example.com" 1 20 pages/

# 2. Placeholder variant – you decide how page 1 looks
python download_range.py "https://example.com/products?page={n}" 1 10 out/ -t 12
"""

from __future__ import annotations
import argparse, concurrent.futures, pathlib, urllib.parse as up
import curl_cffi
from tqdm import tqdm


# ───────────── URL generation ────────────────────────────────────────────────
def build_url(base: str, n: int) -> str:
    """
    Make the URL for page *n*.

    • With a `{n}` placeholder → simple substitution.
    • Without `{n}` → page 1 is `base`, others get “page=n” appended.
    """
    if "{n}" in base:
        return base.replace("{n}", str(n))

    if n == 1:  # bare URL for first page
        return base

    parsed = up.urlsplit(base)
    query = up.parse_qs(parsed.query, keep_blank_values=True)
    query["page"] = [str(n)]
    new_query = up.urlencode(query, doseq=True)
    return up.urlunsplit(parsed._replace(query=new_query))


# ───────────── filename helper ───────────────────────────────────────────────
def make_filename(url: str, out_dir: pathlib.Path) -> pathlib.Path:
    """Turn https://example.com?a=1&page=3 into example.com_a-1_page-3.html"""
    parsed = up.urlsplit(url)
    stem = (parsed.netloc + parsed.path).replace("/", "_").strip("_") or "index"

    qs = up.parse_qs(parsed.query)
    page = qs.get("page", [""])[0]
    if page:
        stem += f"_page-{page}"

    return out_dir / f"{stem}.html"


# ───────────── download worker ───────────────────────────────────────────────
def fetch_and_save(
    url: str,
    out_dir: pathlib.Path,
    *,
    impersonate: str,
    proxies: dict | None,
    timeout: int,
) -> str:
    r = curl_cffi.get(url, impersonate=impersonate, proxies=proxies, timeout=timeout)
    r.raise_for_status()
    dst = make_filename(url, out_dir)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(r.content)
    return str(dst)


# ───────────── main ──────────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser(description="Download numbered pages with curl‑cffi")
    ap.add_argument("base_url", help='Base URL ("{n}" placeholder optional)')
    ap.add_argument("start", type=int, help="First page number (inclusive)")
    ap.add_argument("end", type=int, help="Last page number (inclusive)")
    ap.add_argument("out_dir", type=pathlib.Path, help="Directory to save pages")
    ap.add_argument(
        "-t", "--threads", type=int, default=8, help="Parallel workers (default 8)"
    )
    ap.add_argument(
        "-i",
        "--impersonate",
        default="chrome",
        help='Impersonation string (default "chrome")',
    )
    ap.add_argument(
        "-p",
        "--proxy",
        default=None,
        help='HTTPS/SOCKS proxy, e.g. "socks://127.0.0.1:9050"',
    )
    ap.add_argument(
        "--timeout", type=int, default=30, help="Request timeout seconds (default 30)"
    )
    args = ap.parse_args()

    pages = range(args.start, args.end + 1)
    urls = {n: build_url(args.base_url, n) for n in pages}

    proxies = {"https": args.proxy} if args.proxy else None
    args.out_dir.mkdir(parents=True, exist_ok=True)

    failed: list[int] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as pool:
        futures = {
            pool.submit(
                fetch_and_save,
                url,
                args.out_dir,
                impersonate=args.impersonate,
                proxies=proxies,
                timeout=args.timeout,
            ): n
            for n, url in urls.items()
        }
        for f in tqdm(
            concurrent.futures.as_completed(futures),
            total=len(futures),
            desc="Downloading",
        ):
            n = futures[f]
            try:
                local = f.result()
                tqdm.write(f"✓ page {n} → {local}")
            except Exception as e:
                failed.append(n)
                tqdm.write(f"✗ page {n} ({e})")

    # ─── summary ──────────────────────────────────────────────────────────────
    if failed:
        failed.sort()
        print(f"\nFailed pages: {', '.join(map(str, failed))}")
    else:
        print("\nAll pages downloaded successfully 🎉")


if __name__ == "__main__":
    main()

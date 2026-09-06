from __future__ import annotations

import argparse
import html
import json
import re
import ssl
import sys
import subprocess
from functools import lru_cache
from dataclasses import dataclass, asdict
from typing import Iterable
from urllib.parse import urljoin


BASE_URL = "https://branches.pk"
COMPANY_INDEX_URL = f"{BASE_URL}/companies"


@dataclass
class BranchRecord:
    brand: str
    branch_name: str
    address: str
    phone: str
    url: str


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


@lru_cache(maxsize=None)
def fetch(url: str) -> str:
    command = ["curl.exe", "-k", "-L", "-sS", url]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return completed.stdout


def iter_company_index_pages(max_pages: int = 223) -> Iterable[tuple[int, str]]:
    for page in range(1, max_pages + 1):
        url = COMPANY_INDEX_URL if page == 1 else f"{COMPANY_INDEX_URL}&page={page}"
        yield page, fetch(url)


def find_company_page(target_aliases: list[str], max_pages: int = 223) -> tuple[str, str] | None:
    target_norms = {normalize(alias) for alias in target_aliases}
    for _, html_text in iter_company_index_pages(max_pages=max_pages):
        for match in re.finditer(
            r'<a href="(?P<href>https://branches\.pk/branches/[^"]+)"[^>]*>\s*(?P<name>[^<]+?)\s*</a>',
            html_text,
            flags=re.IGNORECASE,
        ):
            name = html.unescape(match.group("name")).strip()
            if normalize(name) in target_norms:
                return match.group("href"), name
    return None


def parse_branch_rows(page_html: str, brand: str) -> list[BranchRecord]:
    records: list[BranchRecord] = []
    row_pattern = re.compile(
        r'<tr><td><a href="(?P<url>https://branches\.pk/branch-detail/[^"]+)">(?P<branch_name>[^<]+)</a></td><td>(?P<address>.*?)</td><td>(?P<phone>.*?)</td>',
        flags=re.IGNORECASE | re.DOTALL,
    )
    for match in row_pattern.finditer(page_html):
        branch_name = html.unescape(match.group("branch_name")).strip()
        address = re.sub(r"\s+", " ", html.unescape(match.group("address")).strip())
        phone = re.sub(r"\s+", " ", html.unescape(match.group("phone")).strip())
        records.append(
            BranchRecord(
                brand=brand,
                branch_name=branch_name,
                address=address,
                phone=phone,
                url=match.group("url"),
            )
        )
    return records


def collect_branch_pages(first_page_url: str) -> list[str]:
    visited: set[str] = set()
    queue: list[str] = [first_page_url]
    pages: list[str] = []

    while queue:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)
        page_html = fetch(url)
        pages.append(page_html)

        for href in re.findall(r'href=["\']([^"\']+page=\d+[^"\']*)["\']', page_html, flags=re.IGNORECASE):
            next_url = urljoin(url, html.unescape(href))
            if next_url not in visited and next_url not in queue:
                queue.append(next_url)

    return pages


def scrape_brand(brand: str, aliases: list[str], max_index_pages: int = 223) -> dict[str, object]:
    company_page = find_company_page(aliases, max_pages=max_index_pages)
    if company_page is None:
        return {
            "brand": brand,
            "company_page": None,
            "status": "not_indexed",
            "branches": [],
        }

    company_url, canonical_name = company_page
    branch_pages = collect_branch_pages(company_url)
    records: list[BranchRecord] = []
    seen_urls: set[str] = set()
    for page_html in branch_pages:
        for record in parse_branch_rows(page_html, canonical_name):
            if record.url in seen_urls:
                continue
            seen_urls.add(record.url)
            records.append(record)

    return {
        "brand": brand,
        "company_page": company_url,
        "canonical_name": canonical_name,
        "status": "ok",
        "branches": [asdict(record) for record in records],
    }


def build_targets() -> dict[str, list[str]]:
    return {
        "leapard": [
            "Leopard Courier Service",
            "Leopards Courier Service",
            "LEOPARDS COURIER SERVICES(PVT)LTD",
            "Leopards Courier",
            "Leopard Courier",
        ],
        "TCS": [
            "TCS Courier",
            "TCS Courier Service",
            "TCS",
        ],
        "postex": [
            "Postex",
            "PostEx",
            "Post Ex",
            "Postex Courier Service",
            "PostEx Courier Service",
        ],
    }


def build_company_urls() -> dict[str, str | None]:
    return {
        "leapard": "https://branches.pk/branches/Leopard-Courier-Service",
        "TCS": "https://branches.pk/branches/TCS-Courier",
        "postex": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape courier locations from branches.pk")
    parser.add_argument("--output", help="Optional path to write JSON output")
    parser.add_argument("--max-index-pages", type=int, default=223, help="Maximum company index pages to scan")
    args = parser.parse_args()

    targets = build_targets()
    company_urls = build_company_urls()
    results = []
    for brand, aliases in targets.items():
        company_url = company_urls.get(brand)
        if company_url is None:
            results.append({
                "brand": brand,
                "company_page": None,
                "status": "not_indexed",
                "branches": [],
            })
            continue

        branch_pages = collect_branch_pages(company_url)
        records: list[BranchRecord] = []
        seen_urls: set[str] = set()
        for page_html in branch_pages:
            for record in parse_branch_rows(page_html, aliases[0]):
                if record.url in seen_urls:
                    continue
                seen_urls.add(record.url)
                records.append(record)

        results.append({
            "brand": brand,
            "company_page": company_url,
            "canonical_name": aliases[0],
            "status": "ok",
            "branches": [asdict(record) for record in records],
        })

    payload = json.dumps(results, indent=2, ensure_ascii=False)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(payload + "\n")
    else:
        sys.stdout.write(payload + "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
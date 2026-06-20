from __future__ import annotations

import argparse
import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .common import RAW_DIR, RespectfulFetcher, add_common_arguments, content_hash, short_summary, stable_id, text_lines, write_jsonl

ROOT_URL = "https://www.crashonline.org.uk/"


def parse_root_issues(html: str, base_url: str = ROOT_URL) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    issues: list[dict[str, Any]] = []
    for link in soup.find_all("a", href=True):
        label = link.get_text(" ", strip=True)
        if not re.fullmatch(r"\d{1,3}", label):
            continue
        number = label.zfill(3)
        href = urljoin(base_url, link["href"])
        if "/index.htm" not in href and not href.endswith("/"):
            continue
        issues.append({
            "issue_number": number,
            "issue_id": stable_id("issue", "crash", number),
            "index_url": href,
            "cover_date": "",
            "date_precision": "unknown",
        })
    unique: dict[str, dict[str, Any]] = {}
    for issue in issues:
        unique.setdefault(issue["issue_number"], issue)
    return list(unique.values())


def _detail_text_after_heading(heading) -> str:
    chunks = []
    for sibling in heading.next_siblings:
        if getattr(sibling, "name", None) in {"h2", "h3", "h4"}:
            break
        text = sibling.get_text(" ", strip=True) if hasattr(sibling, "get_text") else str(sibling).strip()
        if text:
            chunks.append(text)
    return " ".join(chunks)


def parse_issue_index(html: str, base_url: str, issue_number: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict[str, Any]] = []
    for heading in soup.find_all(["h3", "h4"]):
        title = " ".join(heading.get_text(" ", strip=True).split())
        if not title or title.lower() in {"features", "articles", "regulars", "guide", "reviews in this issue"}:
            continue
        link = heading.find("a", href=True)
        detail = _detail_text_after_heading(heading)
        printed_company = ""
        contributor = ""
        producer_match = re.search(r"Producer:\s*([^:]+?)(?:\s+Memory required:|\s+Retail price:|\s+Author:|$)", detail, re.I)
        author_match = re.search(r"Author:\s*([^:]+?)(?:\s+Retail price:|\s+Keyboard|$)", detail, re.I)
        if producer_match:
            printed_company = producer_match.group(1).strip()
        if author_match:
            contributor = author_match.group(1).strip()
        lower = f"{title} {detail}".lower()
        item_type = "index-only entry"
        if "producer:" in lower or "retail price:" in lower or "overall" in lower:
            item_type = "review"
        elif "news" in lower:
            item_type = "news report"
        elif "profile" in lower:
            item_type = "company profile"
        elif "interview" in lower:
            item_type = "interview"
        rows.append({
            "raw_id": stable_id("raw-source-item", "crash", issue_number, title),
            "archive": "crash",
            "record_type": "source-item",
            "source_item_id": stable_id("source-item", "crash", issue_number, title),
            "publication_id": "publication:crash",
            "issue_id": stable_id("issue", "crash", issue_number),
            "item_type": item_type,
            "title": title,
            "byline_text": "",
            "printed_company": printed_company,
            "named_contributors": ([{"name": contributor, "role_as_printed": "Author"}] if contributor else []),
            "archive_url": urljoin(base_url, link["href"]) if link else base_url,
            "original_locator": f"CRASH issue {issue_number}",
            "date": "",
            "summary": short_summary(detail or title),
            "rights_note": "Archive metadata and short summary only; link and paraphrase.",
            "accessed_at": "2026-06-18",
            "content_hash": content_hash(f"{issue_number}:{title}:{detail}"),
        })
    return rows


def run(indexes_only: bool = True, resume: bool = False, accessed_at: str = "2026-06-18") -> dict[str, int]:
    fetcher = RespectfulFetcher()
    root = fetcher.fetch(ROOT_URL, resume=resume)
    issues = parse_root_issues(root.text, root.canonical_url)
    issue_rows = []
    item_rows = []
    for issue in issues:
        issue_result = fetcher.fetch(issue["index_url"], resume=resume)
        lines = text_lines(issue_result.text)
        issue_date = ""
        for line in lines[:20]:
            match = re.search(r"Issue\s+No\.\s+\d+\s+(.+)", line, re.I)
            if match:
                issue_date = match.group(1).title()
                break
        issue["cover_date"] = issue_date
        issue["date_precision"] = "month" if issue_date else "unknown"
        issue_rows.append({
            "raw_id": stable_id("raw", "crash", issue["issue_number"]),
            "archive": "crash",
            "record_type": "issue",
            "publication_id": "publication:crash",
            "issue_id": issue["issue_id"],
            "issue_number": issue["issue_number"],
            "cover_date": issue["cover_date"],
            "date_precision": issue["date_precision"],
            "index_url": issue_result.canonical_url,
            "source_url": root.canonical_url,
            "accessed_at": accessed_at,
            "content_hash": issue_result.content_hash,
        })
        parsed_items = parse_issue_index(issue_result.text, issue_result.canonical_url, issue["issue_number"])
        for item in parsed_items:
            item["accessed_at"] = accessed_at
        item_rows.extend(parsed_items)
    out = RAW_DIR / "crash"
    write_jsonl(out / "issues.jsonl", issue_rows, sort_key="issue_id")
    write_jsonl(out / "source-items.jsonl", item_rows, sort_key="source_item_id")
    return {"issues": len(issue_rows), "source_items": len(item_rows)}


def main() -> None:
    parser = add_common_arguments(argparse.ArgumentParser(description="Ingest CRASH index metadata."))
    args = parser.parse_args()
    print(run(indexes_only=args.indexes_only, resume=args.resume, accessed_at=args.accessed_date))


if __name__ == "__main__":
    main()

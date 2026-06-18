from __future__ import annotations

import argparse
import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .common import RAW_DIR, RespectfulFetcher, add_common_arguments, content_hash, short_summary, stable_id, text_lines, write_jsonl

ROOT_URL = "https://sinclairuser.com/"
CONTENTS_URL = "https://sinclairuser.com/contents.htm"


def parse_contents_page(html: str, base_url: str = CONTENTS_URL) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    link_by_issue = {}
    for link in soup.find_all("a", href=True):
        label = " ".join(link.get_text(" ", strip=True).split())
        match = re.match(r"Issue\s+(\d+)", label, flags=re.I)
        if not match:
            continue
        link_by_issue[match.group(1).zfill(3)] = urljoin(base_url, link["href"])
    lines = text_lines(html)
    issues: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    index = 0
    while index < len(lines):
        line = lines[index]
        match = re.match(r"Issue\s+(\d+)\s*:\s*(.+)", line, flags=re.I)
        if match:
            if current:
                issues.append(current)
            number = match.group(1).zfill(3)
            date = match.group(2).strip()
            if index + 1 < len(lines) and re.fullmatch(r"\d{4}", lines[index + 1]):
                date = f"{date} {lines[index + 1]}"
                index += 1
            current = {
                "issue_number": number,
                "cover_date": date,
                "index_url": link_by_issue.get(number, urljoin(base_url, f"{number}/index.htm")),
                "label": f"Issue {int(number)} : {date}",
                "index_entries": [],
            }
        elif current:
            if line.startswith("-") and current["index_entries"]:
                current["index_entries"][-1] = f"{current['index_entries'][-1]} {line}".strip()
            elif not re.fullmatch(r"\d{4}", line):
                current["index_entries"].append(line)
        index += 1
    if current:
        issues.append(current)
    return issues


def raw_issue_records(issues: list[dict[str, Any]], *, source_url: str, digest: str, accessed_at: str) -> list[dict[str, Any]]:
    return [
        {
            "raw_id": stable_id("raw", "sinclair-user", issue["issue_number"]),
            "archive": "sinclair-user",
            "record_type": "issue",
            "publication_id": "publication:sinclair-user",
            "issue_id": stable_id("issue", "sinclair-user", issue["issue_number"]),
            "issue_number": issue["issue_number"],
            "cover_date": issue["cover_date"],
            "date_precision": "month",
            "index_url": issue["index_url"],
            "index_entries": issue.get("index_entries", []),
            "source_url": source_url,
            "accessed_at": accessed_at,
            "content_hash": digest,
        }
        for issue in issues
    ]


def raw_source_items_from_contents(issues: list[dict[str, Any]], *, accessed_at: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for issue in issues:
        for entry in issue.get("index_entries", []):
            if len(entry) < 3 or re.match(r"^[*\-:]+$", entry):
                continue
            item_type = "index-only entry"
            lower = entry.lower()
            if "review" in lower or "software scene" in lower or "soft centre" in lower:
                item_type = "review"
            elif "interview" in lower:
                item_type = "interview"
            elif lower.startswith("news") or " news" in lower:
                item_type = "news report"
            elif "profile" in lower:
                item_type = "company profile"
            elif "program" in lower or "listing" in lower:
                item_type = "type-in program"
            rows.append({
                "raw_id": stable_id("raw-source-item", "sinclair-user", issue["issue_number"], entry),
                "archive": "sinclair-user",
                "record_type": "source-item",
                "source_item_id": stable_id("source-item", "sinclair-user", issue["issue_number"], entry),
                "publication_id": "publication:sinclair-user",
                "issue_id": stable_id("issue", "sinclair-user", issue["issue_number"]),
                "item_type": item_type,
                "title": entry,
                "byline_text": "",
                "archive_url": issue["index_url"],
                "original_locator": f"Sinclair User issue {issue['issue_number']}",
                "date": issue["cover_date"],
                "summary": short_summary(entry),
                "rights_note": "Archive index metadata only; link and paraphrase.",
                "accessed_at": accessed_at,
                "content_hash": content_hash(f"{issue['issue_number']}:{entry}"),
            })
    return rows


def run(indexes_only: bool = True, resume: bool = False, accessed_at: str = "2026-06-18") -> dict[str, int]:
    fetcher = RespectfulFetcher()
    result = fetcher.fetch(CONTENTS_URL, resume=resume)
    issues = parse_contents_page(result.text, result.canonical_url)
    issue_rows = raw_issue_records(issues, source_url=result.canonical_url, digest=result.content_hash, accessed_at=accessed_at)
    item_rows = raw_source_items_from_contents(issues, accessed_at=accessed_at)
    out = RAW_DIR / "sinclair-user"
    write_jsonl(out / "issues.jsonl", issue_rows, sort_key="issue_id")
    write_jsonl(out / "source-items.jsonl", item_rows, sort_key="source_item_id")
    return {"issues": len(issue_rows), "source_items": len(item_rows)}


def main() -> None:
    parser = add_common_arguments(argparse.ArgumentParser(description="Ingest Sinclair User index metadata."))
    args = parser.parse_args()
    counts = run(indexes_only=args.indexes_only, resume=args.resume, accessed_at=args.accessed_date)
    print(counts)


if __name__ == "__main__":
    main()

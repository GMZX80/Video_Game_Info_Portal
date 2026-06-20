from __future__ import annotations

import argparse
import re
from collections import OrderedDict
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .common import (
    RAW_DIR,
    RespectfulFetcher,
    add_common_arguments,
    canonical_url,
    content_hash,
    merge_archive_inventory,
    short_summary,
    stable_id,
    text_lines,
    write_jsonl,
)

ROOT_URL = "https://sinclairuser.com/"
CONTENTS_URL = "https://sinclairuser.com/contents.htm"
ISSUE_PATH_RE = re.compile(r"/(\d{3})/index\.html?$", re.I)
ARTICLE_PATH_RE = re.compile(r"/(\d{3})/[^/]+\.html?$", re.I)
MONTH_YEAR_RE = re.compile(
    r"^(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}$",
    re.I,
)

NAVIGATION_LABELS = {
    "main contents",
    "contents",
    "news",
    "letters",
    "next month",
    "gremlin",
    "previous",
    "next",
}

STAFF_ROLES = {
    "editor",
    "deputy editor",
    "assistant editor",
    "staff writers",
    "staff writer",
    "designer",
    "editorial secretary",
    "adventure writers",
    "adventure writer",
    "helpline",
    "hardware correspondent",
    "business correspondent",
    "contributors",
    "contributor",
    "advertisement manager",
    "advertisement sales executive",
    "production assistant",
    "advertisement secretary",
    "subscriptions manager",
    "publisher",
}

SECTION_LABELS = {
    "SOFTWARE",
    "FEATURES",
    "HARDWARE",
    "QLINK",
    "LISTINGS",
    "COMPETITION",
    "REGULARS",
    "NEWS",
}


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _anchor_label(link: Any) -> str:
    label = _clean(link.get_text(" ", strip=True))
    if label:
        return label
    image = link.find("img")
    if image:
        return _clean(image.get("alt", ""))
    return ""


def _dedupe(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    result: OrderedDict[str, dict[str, Any]] = OrderedDict()
    for row in rows:
        value = str(row.get(key, ""))
        if value and value not in result:
            result[value] = row
    return list(result.values())


def discover_issue_links(html: str, base_url: str = ROOT_URL) -> list[dict[str, str]]:
    """Discover every numbered issue link from the archive home or contents page."""

    soup = BeautifulSoup(html, "html.parser")
    rows: dict[str, dict[str, str]] = {}
    for link in soup.find_all("a", href=True):
        url = canonical_url(link["href"], base_url)
        match = ISSUE_PATH_RE.search(urlparse(url).path)
        if not match:
            continue
        number = match.group(1)
        label = _anchor_label(link)
        date_match = re.search(
            r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}",
            label,
            flags=re.I,
        )
        rows[number] = {
            "issue_number": number,
            "cover_date": date_match.group(0) if date_match else "",
            "index_url": url,
            "label": label or f"Issue {int(number)}",
            "index_entries": [],
        }
    return [rows[number] for number in sorted(rows)]


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


def _merge_issue_sources(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for group in groups:
        for issue in group:
            number = issue["issue_number"]
            previous = merged.get(number, {})
            entries = previous.get("index_entries", []) or issue.get("index_entries", [])
            merged[number] = {
                **previous,
                **issue,
                "cover_date": issue.get("cover_date") or previous.get("cover_date", ""),
                "index_url": issue.get("index_url") or previous.get("index_url", ""),
                "index_entries": entries,
            }
    return [merged[number] for number in sorted(merged)]


def _parse_staff(lines: list[str]) -> dict[str, list[str]]:
    staff: dict[str, list[str]] = {}
    for index, line in enumerate(lines):
        role = line.lower().strip(":")
        if role not in STAFF_ROLES or index + 1 >= len(lines):
            continue
        names: list[str] = []
        cursor = index + 1
        while cursor < len(lines):
            candidate = lines[cursor]
            if candidate.upper() in SECTION_LABELS or candidate.lower().strip(":") in STAFF_ROLES:
                break
            if len(candidate) > 80 or candidate.lower().startswith("sinclair user is published"):
                break
            names.append(candidate)
            cursor += 1
            if role not in {"staff writers", "adventure writers", "contributors"}:
                break
        if names:
            staff[role] = names
    return staff


def _classify_item(title: str, section: str = "") -> str:
    combined = f"{section} {title}".lower()
    if "interview" in combined or "hit squad" in combined:
        return "interview"
    if "profile" in combined:
        return "company profile"
    if "listing" in combined or "program" in combined:
        return "type-in program"
    if "news" in combined:
        return "news report"
    if "competition" in combined:
        return "competition"
    if "hardware" in combined:
        return "hardware review"
    if "review" in combined or section.upper() == "SOFTWARE":
        return "review"
    if section.upper() == "FEATURES":
        return "feature"
    return "article"


def parse_issue_page(html: str, base_url: str, issue_number: str) -> dict[str, Any]:
    """Parse issue-level staff metadata and discover linked article pages."""

    soup = BeautifulSoup(html, "html.parser")
    lines = text_lines(html)
    cover_date = next((line for line in lines if MONTH_YEAR_RE.match(line)), "")
    staff = _parse_staff(lines)
    article_rows: list[dict[str, Any]] = []

    section = ""
    for element in soup.find_all(["h1", "h2", "h3", "h4", "b", "strong", "a"]):
        element_text = _clean(element.get_text(" ", strip=True))
        if element_text.upper() in SECTION_LABELS:
            section = element_text.upper()
            continue
        if element.name != "a" or not element.get("href"):
            continue
        url = canonical_url(element["href"], base_url)
        parsed = urlparse(url)
        match = ARTICLE_PATH_RE.search(parsed.path)
        if not match or match.group(1) != issue_number or parsed.path.lower().endswith("/index.htm"):
            continue
        label = _anchor_label(element)
        if not label or label.lower() in NAVIGATION_LABELS or label.lower().startswith("image:"):
            continue
        if label.lower().startswith("issue ") and "contents" in label.lower():
            continue

        parent_text = _clean(element.parent.get_text(" ", strip=True)) if element.parent else ""
        remainder = parent_text.replace(label, "", 1).strip(" -:|")
        printed_company = remainder if remainder and len(remainder) <= 80 else ""
        article_rows.append(
            {
                "title": label,
                "article_url": url,
                "item_type": _classify_item(label, section),
                "section": section,
                "printed_company": printed_company,
            }
        )

    return {
        "issue_number": issue_number,
        "cover_date": cover_date,
        "staff": staff,
        "article_links": _dedupe(article_rows, "article_url"),
    }


def _field_from_lines(lines: list[str], label: str) -> str:
    pattern = re.compile(rf"^{re.escape(label)}\s*[:\-]?\s*(.+)$", re.I)
    for line in lines:
        match = pattern.match(line)
        if match:
            return _clean(match.group(1))
    return ""


def _split_price_memory(lines: list[str]) -> tuple[str, str]:
    for line in lines:
        match = re.match(r"^Price\s+(.+?)\s+Memory\s+(.+)$", line, flags=re.I)
        if match:
            return _clean(match.group(1)), _clean(match.group(2))
    return _field_from_lines(lines, "Price"), _field_from_lines(lines, "Memory")


def parse_article_page(
    html: str,
    base_url: str,
    issue_number: str,
    *,
    item_type_hint: str = "article",
    title_hint: str = "",
    printed_company_hint: str = "",
    accessed_at: str = "2026-06-18",
) -> dict[str, Any]:
    """Extract structured metadata without storing an article's body text."""

    soup = BeautifulSoup(html, "html.parser")
    lines = text_lines(html)
    heading = soup.find(["h1", "h2"])
    title = _clean(heading.get_text(" ", strip=True)) if heading else title_hint
    if not title:
        title = _clean(soup.title.get_text(" ", strip=True)) if soup.title else "Untitled article"

    programmer = _field_from_lines(lines, "Programmer")
    program_author = _field_from_lines(lines, "Author")
    publisher = _field_from_lines(lines, "Publisher") or printed_company_hint
    price, memory = _split_price_memory(lines)
    controls = _field_from_lines(lines, "Joystick") or _field_from_lines(lines, "Controls")

    score = ""
    reviewer = ""
    for index, line in enumerate(lines):
        if re.fullmatch(r"\*{3,10}", line):
            score = f"{len(line)} stars"
            if index + 1 < len(lines):
                candidate = lines[index + 1]
                if candidate.lower() != "sinclair user" and len(candidate) <= 60:
                    reviewer = candidate
            break

    byline = ""
    for line in lines[:20]:
        match = re.match(r"^(?:By|Written by)\s+(.+)$", line, flags=re.I)
        if match:
            byline = _clean(match.group(1))
            break
    if reviewer:
        byline = reviewer

    named_contributors: list[dict[str, str]] = []
    if programmer:
        named_contributors.append({"name": programmer, "role_as_printed": "Programmer"})
    if program_author and program_author != programmer:
        named_contributors.append({"name": program_author, "role_as_printed": "Author"})

    item_type = item_type_hint
    if programmer or publisher or score:
        item_type = "review"
    elif "interview" in title.lower():
        item_type = "interview"

    date = next((line for line in reversed(lines) if MONTH_YEAR_RE.match(line)), "")
    contributor_summary = ", ".join(
        f"{row['role_as_printed']}: {row['name']}" for row in named_contributors
    )
    summary_parts = [f"{item_type.title()} from Sinclair User issue {int(issue_number)}."]
    if publisher:
        summary_parts.append(f"Printed publisher or label: {publisher}.")
    if contributor_summary:
        summary_parts.append(contributor_summary + ".")

    return {
        "raw_id": stable_id("raw-source-item", "sinclair-user", issue_number, base_url),
        "archive": "sinclair-user",
        "record_type": "source-item",
        "source_item_id": stable_id("source-item", "sinclair-user", issue_number, base_url),
        "publication_id": "publication:sinclair-user",
        "issue_id": stable_id("issue", "sinclair-user", issue_number),
        "item_type": item_type,
        "title": title,
        "byline_text": byline,
        "named_contributors": named_contributors,
        "archive_url": canonical_url(base_url),
        "original_locator": f"Sinclair User issue {int(issue_number)}",
        "date": date,
        "summary": short_summary(" ".join(summary_parts)),
        "rights_note": "Structured metadata and editorial summary only; article text is not stored.",
        "accessed_at": accessed_at,
        "content_hash": content_hash(html),
        "printed_company": publisher,
        "price": price,
        "memory": memory,
        "controls": controls,
        "score": score,
        "extraction_status": "article parsed",
    }


def raw_issue_records(issues: list[dict[str, Any]], *, source_url: str, digest: str, accessed_at: str) -> list[dict[str, Any]]:
    return [
        {
            "raw_id": stable_id("raw", "sinclair-user", issue["issue_number"]),
            "archive": "sinclair-user",
            "record_type": "issue",
            "publication_id": "publication:sinclair-user",
            "issue_id": stable_id("issue", "sinclair-user", issue["issue_number"]),
            "issue_number": issue["issue_number"],
            "cover_date": issue.get("cover_date", ""),
            "date_precision": "month" if issue.get("cover_date") else "unknown",
            "index_url": issue["index_url"],
            "index_entries": issue.get("index_entries", []),
            "staff": issue.get("staff", {}),
            "article_count": len(issue.get("article_links", [])),
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
            rows.append(
                {
                    "raw_id": stable_id("raw-source-item", "sinclair-user", issue["issue_number"], entry),
                    "archive": "sinclair-user",
                    "record_type": "source-item",
                    "source_item_id": stable_id("source-item", "sinclair-user", issue["issue_number"], entry),
                    "publication_id": "publication:sinclair-user",
                    "issue_id": stable_id("issue", "sinclair-user", issue["issue_number"]),
                    "item_type": item_type,
                    "title": entry,
                    "byline_text": "",
                    "named_contributors": [],
                    "archive_url": issue["index_url"],
                    "original_locator": f"Sinclair User issue {int(issue['issue_number'])}",
                    "date": issue.get("cover_date", ""),
                    "summary": short_summary(entry),
                    "rights_note": "Archive contents metadata only; link and paraphrase.",
                    "accessed_at": accessed_at,
                    "content_hash": content_hash(f"{issue['issue_number']}:{entry}"),
                    "extraction_status": "contents index parsed",
                }
            )
    return rows


def _inventory_row(
    url: str,
    *,
    page_type: str,
    status_code: int,
    digest: str,
    accessed_at: str,
    parse_status: str,
    parent_url: str = "",
    title: str = "",
    error: str = "",
) -> dict[str, Any]:
    return {
        "page_id": stable_id("page", "sinclair-user", url),
        "archive": "sinclair-user",
        "url": canonical_url(url),
        "canonical_url": canonical_url(url),
        "parent_url": canonical_url(parent_url) if parent_url else "",
        "page_title": title,
        "section": "sinclair-user",
        "content_type": page_type,
        "fetch_status": "fetched" if status_code == 200 else "failed",
        "http_status": status_code,
        "content_hash": digest,
        "accessed_at": accessed_at,
        "parse_status": parse_status,
        "exclusion_reason": error,
    }


def run(
    indexes_only: bool = True,
    resume: bool = False,
    accessed_at: str = "2026-06-18",
    *,
    max_issues: int = 0,
    max_pages: int = 0,
) -> dict[str, int]:
    fetcher = RespectfulFetcher()
    home = fetcher.fetch(ROOT_URL, resume=resume)
    contents = fetcher.fetch(CONTENTS_URL, resume=resume)

    contents_issues = parse_contents_page(contents.text, contents.canonical_url) if contents.status_code == 200 else []
    discovered_issues = discover_issue_links(home.text, home.canonical_url) if home.status_code == 200 else []
    issues = _merge_issue_sources(discovered_issues, contents_issues)
    if max_issues > 0:
        issues = issues[:max_issues]

    inventory = [
        _inventory_row(
            ROOT_URL,
            page_type="archive home",
            status_code=home.status_code,
            digest=home.content_hash,
            accessed_at=accessed_at,
            parse_status="issue links discovered" if home.status_code == 200 else "fetch failed",
            error=home.error,
        ),
        _inventory_row(
            CONTENTS_URL,
            page_type="contents index",
            status_code=contents.status_code,
            digest=contents.content_hash,
            accessed_at=accessed_at,
            parse_status="contents parsed" if contents.status_code == 200 else "fetch failed",
            parent_url=ROOT_URL,
            error=contents.error,
        ),
    ]

    item_rows = raw_source_items_from_contents(issues, accessed_at=accessed_at)
    article_pages_fetched = 0
    article_pages_discovered = 0
    issue_pages_fetched = 0
    failures = 0

    if not indexes_only:
        for issue in issues:
            result = fetcher.fetch(issue["index_url"], resume=resume)
            if result.status_code != 200:
                failures += 1
                inventory.append(
                    _inventory_row(
                        issue["index_url"],
                        page_type="issue index",
                        status_code=result.status_code,
                        digest=result.content_hash,
                        accessed_at=accessed_at,
                        parse_status="fetch failed",
                        parent_url=ROOT_URL,
                        error=result.error,
                    )
                )
                continue

            issue_pages_fetched += 1
            parsed = parse_issue_page(result.text, result.canonical_url, issue["issue_number"])
            issue["cover_date"] = parsed.get("cover_date") or issue.get("cover_date", "")
            issue["staff"] = parsed.get("staff", {})
            issue["article_links"] = parsed.get("article_links", [])
            article_pages_discovered += len(issue["article_links"])
            inventory.append(
                _inventory_row(
                    result.canonical_url,
                    page_type="issue index",
                    status_code=result.status_code,
                    digest=result.content_hash,
                    accessed_at=accessed_at,
                    parse_status="issue metadata and article links parsed",
                    parent_url=ROOT_URL,
                    title=f"Sinclair User issue {int(issue['issue_number'])}",
                )
            )

            for candidate in issue["article_links"]:
                if max_pages > 0 and article_pages_fetched >= max_pages:
                    inventory.append(
                        _inventory_row(
                            candidate["article_url"],
                            page_type=candidate["item_type"],
                            status_code=0,
                            digest="",
                            accessed_at=accessed_at,
                            parse_status="pending page limit",
                            parent_url=issue["index_url"],
                            title=candidate["title"],
                            error="not fetched because --max-pages limit was reached",
                        )
                    )
                    continue

                article = fetcher.fetch(candidate["article_url"], resume=resume)
                if article.status_code != 200:
                    failures += 1
                    inventory.append(
                        _inventory_row(
                            candidate["article_url"],
                            page_type=candidate["item_type"],
                            status_code=article.status_code,
                            digest=article.content_hash,
                            accessed_at=accessed_at,
                            parse_status="fetch failed",
                            parent_url=issue["index_url"],
                            title=candidate["title"],
                            error=article.error,
                        )
                    )
                    continue

                article_pages_fetched += 1
                item_rows.append(
                    parse_article_page(
                        article.text,
                        article.canonical_url,
                        issue["issue_number"],
                        item_type_hint=candidate["item_type"],
                        title_hint=candidate["title"],
                        printed_company_hint=candidate.get("printed_company", ""),
                        accessed_at=accessed_at,
                    )
                )
                inventory.append(
                    _inventory_row(
                        article.canonical_url,
                        page_type=candidate["item_type"],
                        status_code=article.status_code,
                        digest=article.content_hash,
                        accessed_at=accessed_at,
                        parse_status="structured article metadata parsed",
                        parent_url=issue["index_url"],
                        title=candidate["title"],
                    )
                )

    issue_rows = raw_issue_records(
        issues,
        source_url=contents.canonical_url,
        digest=contents.content_hash,
        accessed_at=accessed_at,
    )
    item_rows = _dedupe(item_rows, "source_item_id")
    out = RAW_DIR / "sinclair-user"
    write_jsonl(out / "issues.jsonl", issue_rows, sort_key="issue_id")
    write_jsonl(out / "source-items.jsonl", item_rows, sort_key="source_item_id")
    write_jsonl(out / "page-inventory.jsonl", inventory, sort_key="page_id")
    merge_archive_inventory("sinclair-user", inventory)
    return {
        "issues": len(issue_rows),
        "source_items": len(item_rows),
        "issue_pages_fetched": issue_pages_fetched,
        "article_pages_discovered": article_pages_discovered,
        "article_pages_fetched": article_pages_fetched,
        "failures": failures,
    }


def main() -> None:
    parser = add_common_arguments(argparse.ArgumentParser(description="Ingest Sinclair User archive metadata."))
    parser.add_argument("--max-issues", type=int, default=0, help="Optional development limit; zero means all issues.")
    parser.add_argument("--max-pages", type=int, default=0, help="Optional article-page limit; zero means all pages.")
    args = parser.parse_args()
    counts = run(
        indexes_only=args.indexes_only,
        resume=args.resume,
        accessed_at=args.accessed_date,
        max_issues=args.max_issues,
        max_pages=args.max_pages,
    )
    print(counts)


if __name__ == "__main__":
    main()

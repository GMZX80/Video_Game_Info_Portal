from __future__ import annotations

import re
from collections import OrderedDict
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .common import (
    RAW_DIR,
    RespectfulFetcher,
    canonical_url,
    content_hash,
    merge_archive_inventory,
    read_jsonl,
    short_summary,
    stable_id,
    text_lines,
    write_jsonl,
)
from .sinclair_user import parse_issue_page

ROOT_URL = "https://sinclairuser.com/"
ISSUE_LINK_RE = re.compile(r"/(\d{3}[a-z]?)/index\.html?$", re.I)
ISSUE_HEADING_RE = re.compile(r"^Issue\s+([0-9]+[a-z]?)$", re.I)
MONTH_YEAR_RE = re.compile(
    r"^(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}$",
    re.I,
)

SECTION_MARKERS = {
    "SOFTWARE",
    "COVER SMASH",
    "PREVIEWS",
    "FEATURES",
    "HARDWARE",
    "QLINK",
    "LISTINGS",
    "PRINTOUT",
    "COMPETITION",
    "COMPETITIONS",
    "REGULARS",
    "NEWS",
    "NEW FEATURE",
    "SURVEY",
    "THE YEAR 1986",
    "COIN-OP CRAZINESS",
    "NEW OWNERS START HERE!",
    "SPECIAL OFFER",
    "DIAGNOSTICS",
    "SEASONAL STUFF",
}
SOFTWARE_END_MARKERS = SECTION_MARKERS - {"SOFTWARE"}
LISTING_START_MARKERS = {"LISTINGS", "PRINTOUT"}
LISTING_END_MARKERS = SECTION_MARKERS - LISTING_START_MARKERS

NAVIGATION_TEXT = {
    "main contents",
    "contents",
    "next month",
    "gremlin",
    "previous",
    "next",
}

COMMON_COMPANIES = {
    "Activision",
    "Adventure",
    "Alpha Omega",
    "Ariolasoft",
    "Atlantis",
    "Audiogenic",
    "Beau Jolly",
    "Birdseed",
    "Black Knight",
    "Bug Byte",
    "CCS",
    "Central Solutions",
    "Code Masters",
    "Codemasters",
    "Compass",
    "Creative Sparks",
    "CRL",
    "Crusader",
    "Dented Designs",
    "Digital Precision",
    "Domark",
    "Dual Dimension",
    "Durell",
    "Electric Dreams",
    "Elite",
    "Epyx",
    "Firebird",
    "Global",
    "Gremlin",
    "Hewson",
    "Icon Software",
    "Imagine",
    "Incentive",
    "Leisure Genius",
    "Mastertronic",
    "Matand",
    "Melbourne House",
    "Micro Value",
    "Microsphere",
    "Mikro-Gen",
    "Mirrorsoft",
    "Monolith",
    "Mosaic",
    "Ocean",
    "Odin",
    "Piranha",
    "PSS",
    "Pyramide",
    "Quicksilva",
    "Rainbird",
    "Streetwise",
    "Tasman",
    "The Edge",
    "Thor",
    "Tynesoft",
    "US Gold",
    "Virgin",
    "Zeppelin Games",
}


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def display_issue_key(value: str) -> str:
    match = re.fullmatch(r"0*(\d+)([a-z]?)", value, flags=re.I)
    if not match:
        return value
    return f"{int(match.group(1))}{match.group(2).lower()}"


def discover_physical_issues(html: str, base_url: str = ROOT_URL) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    rows: dict[str, dict[str, str]] = {}
    for link in soup.find_all("a", href=True):
        url = canonical_url(link["href"], base_url)
        match = ISSUE_LINK_RE.search(urlparse(url).path)
        if not match:
            continue
        archive_key = match.group(1).lower()
        rows[archive_key] = {
            "archive_issue_key": archive_key,
            "index_url": url,
            "label": _clean(link.get_text(" ", strip=True)) or display_issue_key(archive_key),
        }
    return [rows[key] for key in sorted(rows)]


def _company_candidates() -> list[str]:
    candidates = set(COMMON_COMPANIES)
    for archive_dir in RAW_DIR.glob("*"):
        if not archive_dir.is_dir():
            continue
        for row in read_jsonl(archive_dir / "source-items.jsonl"):
            company = _clean(row.get("printed_company", ""))
            if company and 1 < len(company) <= 100:
                candidates.add(company)
    return sorted(candidates, key=lambda value: (-len(value), value.lower()))


def _split_title_company(line: str, candidates: list[str]) -> tuple[str, str, str]:
    cleaned = _clean(line)
    lower = cleaned.lower()
    for company in candidates:
        company_lower = company.lower()
        if not lower.endswith(company_lower):
            continue
        title = cleaned[: len(cleaned) - len(company)].strip(" -:|")
        if title and title.lower() != company_lower:
            return title, company, "known company suffix"
    return cleaned, "", "unseparated printed index text"


def _linked_labels(soup: BeautifulSoup, issue_key: str) -> set[str]:
    labels: set[str] = set()
    for link in soup.find_all("a", href=True):
        url = canonical_url(link["href"], ROOT_URL)
        path = urlparse(url).path.lower()
        if f"/{issue_key.lower()}/" not in path or path.endswith("/index.htm"):
            continue
        label = _clean(link.get_text(" ", strip=True))
        if label:
            labels.add(label.lower())
    return labels


def _section_lines(lines: list[str], start_markers: set[str], end_markers: set[str]) -> list[str]:
    start = -1
    for index, line in enumerate(lines):
        if line.upper() in start_markers:
            start = index + 1
            break
    if start < 0:
        return []
    result: list[str] = []
    for line in lines[start:]:
        if line.upper() in end_markers:
            break
        cleaned = _clean(line)
        if not cleaned or cleaned.lower() in NAVIGATION_TEXT:
            continue
        if cleaned.lower().startswith("image:") or cleaned.lower().startswith("issue "):
            continue
        result.append(cleaned)
    return result


def parse_unlinked_software_entries(
    html: str,
    issue_key: str,
    issue_url: str,
    cover_date: str,
    *,
    accessed_at: str,
    companies: list[str],
) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    lines = text_lines(html)
    linked = _linked_labels(soup, issue_key)
    rows: list[dict[str, Any]] = []
    for printed_line in _section_lines(lines, {"SOFTWARE"}, SOFTWARE_END_MARKERS):
        if any(printed_line.lower().startswith(label) for label in linked):
            continue
        title, company, parse_status = _split_title_company(printed_line, companies)
        item_type = "index-only entry" if company else "software index text"
        machine = "Sinclair QL" if "(QL)" in title.upper() else ""
        rows.append(
            {
                "raw_id": stable_id("raw-source-item", "sinclair-user-supplement", issue_key, printed_line),
                "archive": "sinclair-user",
                "record_type": "source-item",
                "source_item_id": stable_id("source-item", "sinclair-user-supplement", issue_key, printed_line),
                "publication_id": "publication:sinclair-user",
                "issue_id": stable_id("issue", "sinclair-user", issue_key),
                "item_type": item_type,
                "title": title,
                "byline_text": "",
                "named_contributors": [],
                "archive_url": canonical_url(issue_url),
                "original_locator": f"Sinclair User archive issue {display_issue_key(issue_key)}",
                "date": cover_date,
                "summary": short_summary(
                    f"Software contents entry from Sinclair User. Printed company or label: {company}."
                    if company
                    else "Software contents line retained for later title and company reconciliation."
                ),
                "rights_note": "Issue contents metadata only; no review or article text is stored.",
                "accessed_at": accessed_at,
                "content_hash": content_hash(f"{issue_key}:{printed_line}"),
                "printed_company": company,
                "printed_index_text": printed_line,
                "title_parse_status": parse_status,
                "machine": machine,
                "extraction_status": "unlinked issue software entry captured",
            }
        )
    return rows


def _looks_like_description(line: str) -> bool:
    lower = line.lower()
    return (
        len(line) > 55
        or line.endswith(('.', '!', '?'))
        or lower.startswith(
            (
                "a ",
                "an ",
                "the ",
                "blast ",
                "create ",
                "dice ",
                "drop ",
                "we ",
                "your ",
                "this ",
                "some ",
                "maps ",
            )
        )
    )


def parse_typein_index_entries(
    html: str,
    issue_key: str,
    issue_url: str,
    cover_date: str,
    *,
    accessed_at: str,
) -> list[dict[str, Any]]:
    lines = text_lines(html)
    section = _section_lines(lines, LISTING_START_MARKERS, LISTING_END_MARKERS)
    rows: list[dict[str, Any]] = []
    index = 0
    while index < len(section):
        title = section[index]
        description = ""
        if index + 1 < len(section) and _looks_like_description(section[index + 1]):
            description = section[index + 1]
            index += 2
        else:
            index += 1
        if len(title) > 120 or title.upper() in SECTION_MARKERS:
            continue
        rows.append(
            {
                "raw_id": stable_id("raw-source-item", "sinclair-user-typein", issue_key, title),
                "archive": "sinclair-user",
                "record_type": "source-item",
                "source_item_id": stable_id("source-item", "sinclair-user-typein", issue_key, title),
                "publication_id": "publication:sinclair-user",
                "issue_id": stable_id("issue", "sinclair-user", issue_key),
                "item_type": "type-in program",
                "title": title,
                "byline_text": "",
                "named_contributors": [],
                "archive_url": canonical_url(issue_url),
                "original_locator": f"Sinclair User archive issue {display_issue_key(issue_key)}",
                "date": cover_date,
                "summary": short_summary(
                    f"Type-in program listed in the issue contents. {description}" if description else "Type-in program listed in the issue contents."
                ),
                "rights_note": "Contents metadata only; the program listing is not stored.",
                "accessed_at": accessed_at,
                "content_hash": content_hash(f"{issue_key}:{title}:{description}"),
                "printed_company": "",
                "machine": "",
                "program_type": "game or program; requires review",
                "language": "",
                "extraction_status": "issue type-in title captured",
            }
        )
    return rows


def _printed_issue_number(lines: list[str]) -> str:
    for line in lines:
        match = ISSUE_HEADING_RE.match(line)
        if match:
            return match.group(1)
    return ""


def _submission_guidance(lines: list[str]) -> str:
    for line in lines:
        if "we pay" in line.lower() and "program" in line.lower():
            return _clean(line)
    return ""


def _inventory_row(issue: dict[str, str], result: Any, accessed_at: str, parsed_status: str) -> dict[str, Any]:
    return {
        "page_id": stable_id("page", "sinclair-user", issue["index_url"]),
        "archive": "sinclair-user",
        "url": canonical_url(issue["index_url"]),
        "canonical_url": canonical_url(result.canonical_url),
        "parent_url": ROOT_URL,
        "page_title": f"Sinclair User archive issue {display_issue_key(issue['archive_issue_key'])}",
        "section": "sinclair-user",
        "content_type": "issue index",
        "fetch_status": "fetched" if result.status_code == 200 else "failed",
        "http_status": result.status_code,
        "content_hash": result.content_hash,
        "accessed_at": accessed_at,
        "parse_status": parsed_status,
        "exclusion_reason": result.error,
    }


def supplement(*, accessed_at: str = "2026-06-19") -> dict[str, int]:
    """Capture physical issue 58a and contents entries omitted by article-link parsing."""

    fetcher = RespectfulFetcher()
    home = fetcher.fetch(ROOT_URL, resume=True)
    physical_issues = discover_physical_issues(home.text, home.canonical_url) if home.status_code == 200 else []
    companies = _company_candidates()

    out = RAW_DIR / "sinclair-user"
    existing_issues = {row["issue_id"]: row for row in read_jsonl(out / "issues.jsonl")}
    existing_items = {row["source_item_id"]: row for row in read_jsonl(out / "source-items.jsonl")}
    existing_inventory = {row["page_id"]: row for row in read_jsonl(out / "page-inventory.jsonl")}

    added_issues = 0
    software_entries = 0
    typein_entries = 0
    failures = 0
    for issue in physical_issues:
        result = fetcher.fetch(issue["index_url"], resume=True)
        if result.status_code != 200:
            failures += 1
            inventory = _inventory_row(issue, result, accessed_at, "supplement fetch failed")
            existing_inventory[inventory["page_id"]] = inventory
            continue

        lines = text_lines(result.text)
        parsed = parse_issue_page(result.text, result.canonical_url, issue["archive_issue_key"])
        printed_number = _printed_issue_number(lines)
        cover_date = parsed.get("cover_date", "") or next((line for line in lines if MONTH_YEAR_RE.match(line)), "")
        issue_id = stable_id("issue", "sinclair-user", issue["archive_issue_key"])
        previous = existing_issues.get(issue_id, {})
        if not previous:
            added_issues += 1
        existing_issues[issue_id] = {
            **previous,
            "raw_id": previous.get("raw_id", stable_id("raw", "sinclair-user", issue["archive_issue_key"])),
            "archive": "sinclair-user",
            "record_type": "issue",
            "publication_id": "publication:sinclair-user",
            "issue_id": issue_id,
            "issue_number": issue["archive_issue_key"],
            "archive_issue_key": issue["archive_issue_key"],
            "printed_issue_number": printed_number,
            "cover_date": cover_date,
            "date_precision": "month" if cover_date else "unknown",
            "index_url": canonical_url(issue["index_url"]),
            "index_entries": previous.get("index_entries", []),
            "staff": parsed.get("staff", previous.get("staff", {})),
            "article_count": previous.get("article_count", len(parsed.get("article_links", []))),
            "submission_guidance": _submission_guidance(lines),
            "source_url": ROOT_URL,
            "accessed_at": accessed_at,
            "content_hash": result.content_hash,
        }

        software = parse_unlinked_software_entries(
            result.text,
            issue["archive_issue_key"],
            result.canonical_url,
            cover_date,
            accessed_at=accessed_at,
            companies=companies,
        )
        typeins = parse_typein_index_entries(
            result.text,
            issue["archive_issue_key"],
            result.canonical_url,
            cover_date,
            accessed_at=accessed_at,
        )
        for row in [*software, *typeins]:
            if row["source_item_id"] not in existing_items:
                if row["item_type"] == "type-in program":
                    typein_entries += 1
                else:
                    software_entries += 1
            existing_items[row["source_item_id"]] = row

        inventory = _inventory_row(
            issue,
            result,
            accessed_at,
            "issue metadata, unlinked software entries and type-in titles captured",
        )
        existing_inventory[inventory["page_id"]] = inventory

    write_jsonl(out / "issues.jsonl", existing_issues.values(), sort_key="issue_id")
    write_jsonl(out / "source-items.jsonl", existing_items.values(), sort_key="source_item_id")
    write_jsonl(out / "page-inventory.jsonl", existing_inventory.values(), sort_key="page_id")
    merge_archive_inventory("sinclair-user", existing_inventory.values())
    return {
        "physical_issue_pages_discovered": len(physical_issues),
        "issues_added": added_issues,
        "unlinked_software_entries_added": software_entries,
        "typein_entries_added": typein_entries,
        "failures": failures,
    }

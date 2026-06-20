from __future__ import annotations

import argparse
import csv
import re
from collections import deque
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .common import (
    RAW_DIR,
    ROOT,
    RespectfulFetcher,
    add_common_arguments,
    canonical_url,
    content_hash,
    is_probably_binary_url,
    merge_archive_inventory,
    short_summary,
    stable_id,
    text_lines,
    write_jsonl,
)

ROOT_URL = "https://www.stairwaytohell.com/"
SEED_CATALOGUE = ROOT / "research" / "stairway-catalogue.csv"
BASE_SEEDS = [
    "https://www.stairwaytohell.com/articles/KBlake.html",
    "https://www.stairwaytohell.com/lostandfound/indexb.html",
    "https://www.stairwaytohell.com/misc/credits.html",
]
CATALOGUE_SEEDS = [
    "https://www.stairwaytohell.com/electron/homepage.html",
    "https://www.stairwaytohell.com/bbc/sthcollection.html",
]

ALLOWED_PREFIXES = (
    "/authors/",
    "/articles/",
    "/lostandfound/",
    "/misc/",
    "/electron/",
    "/bbc/",
)
EXCLUDED_PREFIXES = (
    "/bbc/disk",
    "/bbc/tape",
    "/bbc/riscos",
    "/bbc/download",
    "/electron/adfs/",
    "/music/",
    "/emulators/",
    "/downloads/",
)

DATE_RE = re.compile(
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December|Spring|Summer|Autumn|Winter)\s+\d{4}",
    re.I,
)
FROM_RE = re.compile(r"^From\s+(.+?)(?:,\s*([^:]+))?:$", re.I)
BY_RE = re.compile(r"^(?:By|Written by)\s+(.+?)(?:,\s*(.+))?$", re.I)
PERSON_ROLE_RE = re.compile(r"^(.+?)\s+\(([^()]{2,80})\)$")
STATUS_RE = re.compile(r"^STATUS\s*:\s*(.+)$", re.I)

NAVIGATION_WORDS = {
    "main",
    "home",
    "homepage",
    "browse",
    "related links",
    "alternative titles",
    "lost & found - page 1",
    "lost & found - page 2",
}


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _load_seed_metadata(path: Path = SEED_CATALOGUE) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    rows: dict[str, dict[str, str]] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            url = canonical_url(row.get("stairway_url", ""))
            if url:
                rows[url] = {key: _clean(value) for key, value in row.items()}
    return rows


def seed_urls(include_catalogues: bool = False) -> list[str]:
    metadata = _load_seed_metadata()
    rows = [*BASE_SEEDS, *metadata.keys()]
    if include_catalogues:
        rows.extend(CATALOGUE_SEEDS)
    return sorted({canonical_url(row) for row in rows if row})


def _eligible_url(url: str, *, include_catalogues: bool) -> tuple[bool, str]:
    parsed = urlparse(canonical_url(url))
    if parsed.netloc not in {"stairwaytohell.com", "www.stairwaytohell.com"}:
        return False, "external host"
    if is_probably_binary_url(url):
        return False, "binary or download file"
    path = parsed.path.lower()
    if not path.endswith((".htm", ".html", "/")):
        return False, "non-HTML path"
    if any(path.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
        return False, "download or binary archive section"
    if not any(path.startswith(prefix) for prefix in ALLOWED_PREFIXES):
        return False, "outside research sections"
    if not include_catalogues and path.startswith(("/electron/", "/bbc/")):
        return False, "catalogue crawl not requested"
    return True, ""


def discover_links(html: str, base_url: str, *, include_catalogues: bool = False) -> tuple[list[str], list[dict[str, str]]]:
    soup = BeautifulSoup(html, "html.parser")
    accepted: set[str] = set()
    excluded: list[dict[str, str]] = []
    for link in soup.find_all("a", href=True):
        href = _clean(link.get("href", ""))
        if not href or href.startswith(("mailto:", "javascript:", "#")):
            continue
        url = canonical_url(href, base_url)
        allowed, reason = _eligible_url(url, include_catalogues=include_catalogues)
        if allowed:
            accepted.add(url)
        elif urlparse(url).netloc in {"stairwaytohell.com", "www.stairwaytohell.com"} and reason:
            excluded.append({"url": url, "reason": reason})
    return sorted(accepted), excluded


def classify_page(url: str, lines: list[str], seed: dict[str, str] | None = None) -> str:
    seed = seed or {}
    seeded = seed.get("article_type", "").lower()
    if seeded:
        return seeded
    path = urlparse(url).path.lower()
    filename = path.rsplit("/", 1)[-1]
    joined = " ".join(lines[:20]).lower()
    if "/lostandfound/" in path:
        return "lost and found"
    if filename.startswith("pro-") or " profile" in joined:
        return "profile"
    if filename.startswith("por-") or "portfolio" in joined:
        return "portfolio"
    if filename.startswith("sg-") or "interview" in joined:
        return "interview"
    if filename.startswith(("mu", "eu", "ab-")) or "diary of a game" in joined:
        return "technical article"
    if "tynesoft boys club" in joined:
        return "retrospective recollection"
    if path.endswith("credits.html"):
        return "provenance note"
    if re.search(r"/electron/[a-z0-9#]\.html?$", path) or path.endswith("sthcollection.html"):
        return "game catalogue"
    return "archive article"


def _meaningful_title(lines: list[str], seed: dict[str, str] | None = None) -> str:
    if seed and seed.get("title"):
        return seed["title"]
    for line in lines[:20]:
        cleaned = _clean(line).strip("*|–—")
        if not cleaned or cleaned.lower() in NAVIGATION_WORDS or cleaned.lower().startswith("image"):
            continue
        if len(cleaned) >= 3:
            return cleaned
    return "Untitled Stairway to Hell page"


def _original_provenance(lines: list[str], seed: dict[str, str] | None = None) -> tuple[str, str, str]:
    seed = seed or {}
    publication = seed.get("original_publication", "")
    date = seed.get("publication_date", "")
    author = seed.get("author", "")

    for line in lines:
        appeared = re.search(
            r"This article appeared in the\s+(.+?)\s+edition of\s+[\"“](.+?)[\"”]",
            line,
            flags=re.I,
        )
        if appeared:
            date = date or _clean(appeared.group(1))
            publication = publication or _clean(appeared.group(2))
        byline = BY_RE.match(line)
        if byline:
            author = author or _clean(byline.group(1))
            possible_date = _clean(byline.group(2))
            if possible_date and DATE_RE.search(possible_date):
                date = date or possible_date
    return publication or "Stairway To Hell", date, author


def _named_testimony_sources(lines: list[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for line in lines:
        match = FROM_RE.match(line)
        if match:
            name = _clean(match.group(1))
            date = _clean(match.group(2))
            key = (name, date)
            if name and key not in seen:
                rows.append({"name": name, "role_as_printed": "First-hand or attributed source", "date": date})
                seen.add(key)
    return rows


def parse_stairway_page(
    html: str,
    url: str,
    *,
    seed: dict[str, str] | None = None,
    accessed_at: str = "2026-06-18",
) -> dict[str, Any]:
    """Create a page-level source record without retaining the article body."""

    lines = text_lines(html)
    title = _meaningful_title(lines, seed)
    item_type = classify_page(url, lines, seed)
    original_publication, publication_date, original_author = _original_provenance(lines, seed)
    testimony_sources = _named_testimony_sources(lines)

    if not original_author:
        for line in lines[:15]:
            match = BY_RE.match(line)
            if match:
                original_author = _clean(match.group(1))
                break

    named_contributors = testimony_sources.copy()
    if seed and seed.get("person_or_topic"):
        for person in re.split(r"\s*[;/]\s*", seed["person_or_topic"]):
            if person and person.lower() not in {"tynesoft photographs and staff recollection"}:
                named_contributors.append({"name": person, "role_as_printed": "Profile subject", "date": ""})

    summary_parts = [f"{item_type.title()} preserved by Stairway To Hell."]
    if original_publication and original_publication != "Stairway To Hell":
        summary_parts.append(f"Originally published by {original_publication}.")
    if publication_date:
        summary_parts.append(f"Date: {publication_date}.")
    if original_author:
        summary_parts.append(f"Attributed author: {original_author}.")
    if testimony_sources:
        summary_parts.append(f"Contains {len(testimony_sources)} named attributed contribution(s).")

    source_item_id = stable_id("source-item", "stairway", url)
    return {
        "raw_id": stable_id("raw-source-item", "stairway", url),
        "archive": "stairway",
        "record_type": "source-item",
        "source_item_id": source_item_id,
        "publication_id": "publication:stairway-to-hell",
        "issue_id": "",
        "item_type": item_type,
        "title": title,
        "byline_text": original_author,
        "named_contributors": named_contributors,
        "archive_url": canonical_url(url),
        "original_locator": original_publication,
        "date": publication_date,
        "summary": short_summary(" ".join(summary_parts)),
        "rights_note": "Bibliographic metadata and editorial summary only; article text and images are not copied.",
        "accessed_at": accessed_at,
        "content_hash": content_hash(html),
        "original_publication": original_publication,
        "original_author": original_author,
        "contemporary_or_retrospective": "retrospective" if item_type in {"interview", "portfolio", "retrospective recollection", "lost and found"} else "as identified by source metadata",
        "extraction_status": "page metadata parsed",
    }


def _looks_like_lost_heading(line: str) -> bool:
    cleaned = _clean(line)
    if not cleaned or len(cleaned) < 3 or len(cleaned) > 140:
        return False
    lower = cleaned.lower()
    if lower in NAVIGATION_WORDS or lower.startswith(("from ", "status:", "information and", "click here")):
        return False
    if cleaned.startswith("[") or cleaned.endswith(":"):
        return False
    letters = [char for char in cleaned if char.isalpha()]
    if not letters:
        return False
    uppercase_ratio = sum(char.isupper() for char in letters) / len(letters)
    return uppercase_ratio >= 0.75 or bool(re.search(r"\sby\s+[A-Z]", cleaned))


def parse_lost_and_found_entries(
    html: str,
    url: str,
    *,
    accessed_at: str = "2026-06-18",
) -> list[dict[str, Any]]:
    """Extract one concise record per Lost & Found heading and preserve contradictory testimony as sources."""

    lines = text_lines(html)
    headings = [index for index, line in enumerate(lines) if _looks_like_lost_heading(line)]
    rows: list[dict[str, Any]] = []
    for position, start in enumerate(headings):
        end = headings[position + 1] if position + 1 < len(headings) else len(lines)
        title_line = _clean(lines[start])
        segment = lines[start + 1 : end]
        status = ""
        for line in segment:
            match = STATUS_RE.match(line)
            if match:
                status = _clean(match.group(1))
                break

        company = ""
        company_match = re.search(r"\(([^()]{2,80})\)\s*$", title_line)
        if company_match:
            company = _clean(company_match.group(1))
        author = ""
        author_match = re.search(r"\s+by\s+(.+?)(?:\s+\([^()]+\))?$", title_line, flags=re.I)
        if author_match:
            author = _clean(author_match.group(1))
        title = re.sub(r"\s+by\s+.+$", "", title_line, flags=re.I)
        title = re.sub(r"\s+\([^()]+\)\s*$", "", title).strip()
        testimony = _named_testimony_sources(segment)
        summary = "Lost & Found catalogue record."
        if status:
            summary += f" Source status: {status}."
        if testimony:
            summary += f" Contains {len(testimony)} attributed account(s), which may disagree."

        rows.append(
            {
                "raw_id": stable_id("raw-source-item", "stairway-lost", url, title_line),
                "archive": "stairway",
                "record_type": "source-item",
                "source_item_id": stable_id("source-item", "stairway-lost", url, title_line),
                "publication_id": "publication:stairway-to-hell",
                "issue_id": "",
                "item_type": "unreleased-game record",
                "title": title or title_line,
                "byline_text": "",
                "named_contributors": [
                    *([{"name": author, "role_as_printed": "Named game author", "date": ""}] if author else []),
                    *testimony,
                ],
                "archive_url": canonical_url(url),
                "original_locator": "Stairway To Hell Lost & Found",
                "date": "",
                "summary": short_summary(summary),
                "rights_note": "Catalogue metadata only; testimony text, downloads and images are not copied.",
                "accessed_at": accessed_at,
                "content_hash": content_hash(f"{url}:{title_line}:{status}"),
                "printed_company": company,
                "source_status": status,
                "contemporary_or_retrospective": "mixed attributed sources",
                "extraction_status": "Lost & Found entry parsed",
            }
        )
    return rows


def parse_tynesoft_photo_identifications(
    html: str,
    url: str,
    *,
    accessed_at: str = "2026-06-18",
) -> list[dict[str, Any]]:
    """Capture Kevin Blake's printed photograph identifications as testimony, never as facial recognition."""

    lines = text_lines(html)
    rows: list[dict[str, Any]] = []
    current_photo = ""
    pending_position = ""
    order = 0
    for line in lines:
        photo_match = re.match(r"^Tynesoft Staff:\s*Image\s*(\d+)", line, flags=re.I)
        if photo_match:
            current_photo = f"tynesoft-staff-image-{photo_match.group(1)}"
            pending_position = ""
            order = 0
            continue
        if not current_photo:
            continue
        if line.lower() in {"bottom left", "middle right"}:
            pending_position = line
            continue
        match = PERSON_ROLE_RE.match(line)
        if not match:
            continue
        name = _clean(match.group(1))
        role = _clean(match.group(2))
        if not name or name.lower().startswith("image"):
            continue
        order += 1
        rows.append(
            {
                "photo_identification_id": stable_id("photo-identification", current_photo, order, name),
                "photo_id": stable_id("photo", current_photo),
                "source_item_id": stable_id("source-item", "stairway", url),
                "position_order": order,
                "position_description": pending_position or ("left-to-right order" if current_photo.endswith("1") else "order as printed"),
                "name_as_printed": name,
                "role_as_printed": role,
                "identification_method": "Kevin Blake retrospective caption on Stairway To Hell",
                "evidence_status": "first-person retrospective testimony",
                "verification_status": "unconfirmed pending independent corroboration",
                "accessed_at": accessed_at,
                "source_url": canonical_url(url),
                "notes": "No visual identification or facial comparison was used.",
            }
        )
        pending_position = ""
    return rows


def parse_catalogue_entries(
    html: str,
    url: str,
    *,
    accessed_at: str = "2026-06-18",
) -> list[dict[str, Any]]:
    """Conservatively extract title/company pairs from alphabetic Electron catalogue pages."""

    path = urlparse(url).path.lower()
    if not re.search(r"/electron/[a-z0-9#]\.html?$", path):
        return []
    lines = text_lines(html)
    rows: list[dict[str, Any]] = []
    ignored = {"main", "archive indexes", "browse archive", "adventures", "other software", "game cheats", "missing"}
    index = 0
    while index + 1 < len(lines):
        title = _clean(lines[index])
        company = _clean(lines[index + 1])
        letters = [char for char in title if char.isalpha()]
        uppercase = bool(letters) and sum(char.isupper() for char in letters) / len(letters) >= 0.9
        plausible_company = company and company.lower() not in ignored and len(company) <= 80 and not company.lower().startswith("image")
        if uppercase and 2 < len(title) <= 100 and plausible_company:
            rows.append(
                {
                    "raw_id": stable_id("raw-source-item", "stairway-catalogue", url, title, company),
                    "archive": "stairway",
                    "record_type": "source-item",
                    "source_item_id": stable_id("source-item", "stairway-catalogue", url, title, company),
                    "publication_id": "publication:stairway-to-hell",
                    "issue_id": "",
                    "item_type": "game catalogue entry",
                    "title": title,
                    "byline_text": "",
                    "named_contributors": [],
                    "archive_url": canonical_url(url),
                    "original_locator": "Stairway To Hell Electron catalogue",
                    "date": "",
                    "summary": f"Electron catalogue entry; printed company or label: {company}.",
                    "rights_note": "Catalogue metadata only; software and images are not copied.",
                    "accessed_at": accessed_at,
                    "content_hash": content_hash(f"{url}:{title}:{company}"),
                    "printed_company": company,
                    "machine": "Acorn Electron",
                    "extraction_status": "catalogue pair parsed",
                }
            )
            index += 2
            continue
        index += 1
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
        "page_id": stable_id("page", "stairway", url),
        "archive": "stairway",
        "url": canonical_url(url),
        "canonical_url": canonical_url(url),
        "parent_url": canonical_url(parent_url) if parent_url else "",
        "page_title": title,
        "section": urlparse(url).path.split("/")[1] if "/" in urlparse(url).path else "",
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
    max_pages: int = 0,
    include_catalogues: bool = False,
) -> dict[str, int]:
    fetcher = RespectfulFetcher()
    seed_metadata = _load_seed_metadata()
    initial = seed_urls(include_catalogues=include_catalogues)
    queue: deque[tuple[str, str]] = deque((url, "") for url in initial)
    queued = set(initial)
    visited: set[str] = set()
    source_items: list[dict[str, Any]] = []
    photo_identifications: list[dict[str, Any]] = []
    inventory: list[dict[str, Any]] = []
    failures = 0
    excluded_binary = 0

    while queue:
        if max_pages > 0 and len(visited) >= max_pages:
            break
        url, parent_url = queue.popleft()
        if url in visited:
            continue
        visited.add(url)
        result = fetcher.fetch(url, resume=resume)
        if result.status_code != 200:
            failures += 1
            inventory.append(
                _inventory_row(
                    url,
                    page_type="unknown",
                    status_code=result.status_code,
                    digest=result.content_hash,
                    accessed_at=accessed_at,
                    parse_status="fetch failed",
                    parent_url=parent_url,
                    error=result.error,
                )
            )
            continue

        lines = text_lines(result.text)
        seed = seed_metadata.get(canonical_url(url), {})
        page_type = classify_page(result.canonical_url, lines, seed)
        page_item = parse_stairway_page(result.text, result.canonical_url, seed=seed, accessed_at=accessed_at)
        source_items.append(page_item)
        if page_type == "lost and found":
            source_items.extend(parse_lost_and_found_entries(result.text, result.canonical_url, accessed_at=accessed_at))
        if "tynesoft boys club" in " ".join(lines[:15]).lower():
            photo_identifications.extend(
                parse_tynesoft_photo_identifications(result.text, result.canonical_url, accessed_at=accessed_at)
            )
        if page_type == "game catalogue":
            source_items.extend(parse_catalogue_entries(result.text, result.canonical_url, accessed_at=accessed_at))

        inventory.append(
            _inventory_row(
                result.canonical_url,
                page_type=page_type,
                status_code=result.status_code,
                digest=result.content_hash,
                accessed_at=accessed_at,
                parse_status="structured metadata parsed",
                parent_url=parent_url,
                title=page_item["title"],
            )
        )

        links, excluded = discover_links(result.text, result.canonical_url, include_catalogues=include_catalogues)
        excluded_binary += sum(1 for row in excluded if row["reason"] == "binary or download file")
        if not indexes_only:
            for link in links:
                if link not in queued and link not in visited:
                    queue.append((link, result.canonical_url))
                    queued.add(link)

    for url, parent_url in queue:
        inventory.append(
            _inventory_row(
                url,
                page_type="discovered HTML page",
                status_code=0,
                digest="",
                accessed_at=accessed_at,
                parse_status="pending page limit",
                parent_url=parent_url,
                error="not fetched because --max-pages limit was reached",
            )
        )

    source_items_by_id = {row["source_item_id"]: row for row in source_items}
    photo_by_id = {row["photo_identification_id"]: row for row in photo_identifications}
    out = RAW_DIR / "stairway"
    write_jsonl(out / "issues.jsonl", [])
    write_jsonl(out / "source-items.jsonl", source_items_by_id.values(), sort_key="source_item_id")
    write_jsonl(out / "photo-identifications.jsonl", photo_by_id.values(), sort_key="photo_identification_id")
    write_jsonl(out / "page-inventory.jsonl", inventory, sort_key="page_id")
    merge_archive_inventory("stairway", inventory)
    return {
        "issues": 0,
        "source_items": len(source_items_by_id),
        "pages_discovered": len(queued),
        "pages_fetched": len(visited),
        "photo_identifications": len(photo_by_id),
        "excluded_binary_links": excluded_binary,
        "failures": failures,
    }


def main() -> None:
    parser = add_common_arguments(argparse.ArgumentParser(description="Ingest Stairway To Hell historical metadata."))
    parser.add_argument("--max-pages", type=int, default=0, help="Optional crawl limit; zero means every discovered eligible page.")
    parser.add_argument("--include-catalogues", action="store_true", help="Include BBC/Electron HTML catalogue pages; binaries remain excluded.")
    args = parser.parse_args()
    counts = run(
        indexes_only=args.indexes_only,
        resume=args.resume,
        accessed_at=args.accessed_date,
        max_pages=args.max_pages,
        include_catalogues=args.include_catalogues,
    )
    print(counts)


if __name__ == "__main__":
    main()

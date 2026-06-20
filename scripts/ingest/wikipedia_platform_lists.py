from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode

import requests
from bs4 import BeautifulSoup, Tag

from .common import DEFAULT_USER_AGENT, ROOT, content_hash, read_jsonl, stable_id, write_jsonl

MEDIAWIKI_API = "https://en.wikipedia.org/w/api.php"
DEFAULT_CACHE_DIR = ROOT / ".cache" / "wikipedia-platform-lists"
DEFAULT_REQUEST_LOG = DEFAULT_CACHE_DIR / "request-log.jsonl"
SOURCE_SYSTEM = "wikipedia"
LICENSE = "CC BY-SA"
ZX_SPECTRUM_PAGE = "List of ZX Spectrum games"
C64_MAIN_PAGE = "List of Commodore 64 games"
C64_A_M_PAGE = "List of Commodore 64 games (A-M)"
C64_N_Z_PAGE = "List of Commodore 64 games (N-Z)"
C64_A_M_PAGE_CANONICAL = "List of Commodore 64 games (A–M)"
C64_N_Z_PAGE_CANONICAL = "List of Commodore 64 games (N–Z)"


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def wikipedia_page_url(title: str) -> str:
    return f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'), safe='()_:%E2%80%93-')}"


def wikipedia_permanent_url(title: str, revision_id: int | str) -> str:
    return f"https://en.wikipedia.org/w/index.php?title={quote(title.replace(' ', '_'), safe='()_:%E2%80%93-')}&oldid={revision_id}"


def _source_item_id(source_page_title: str, title: str) -> str:
    return stable_id("source-item", "wikipedia-platform-lists", source_page_title, title)


def _link_title(cell: Tag | None) -> str:
    if cell is None:
        return ""
    link = cell.find("a", href=True)
    if not link:
        return ""
    title = _clean_text(link.get("title", ""))
    return re.sub(r"\s+\(page does not exist\)$", "", title)


def linked_article_titles_from_html(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    titles: list[str] = []
    seen: set[str] = set()
    for link in soup.find_all("a", href=True):
        classes = set(link.get("class", []) or [])
        if "new" in classes:
            continue
        title = _clean_text(link.get("title", ""))
        href = str(link.get("href", ""))
        if not title or ":" in title or not href.startswith("/wiki/"):
            continue
        if title not in seen:
            seen.add(title)
            titles.append(title)
    return titles


def _base_row(
    *,
    title: str,
    platform: str,
    source_page_title: str,
    revision_id: int | str,
    accessed_at: str,
    wikidata_qid: str = "",
    article_title: str = "",
) -> dict[str, Any]:
    return {
        "source_system": SOURCE_SYSTEM,
        "source_item_id": _source_item_id(source_page_title, title),
        "title": title,
        "platform": platform,
        "wikipedia_article_title": article_title,
        "wikipedia_article_url": wikipedia_page_url(article_title) if article_title else "",
        "wikidata_qid": wikidata_qid,
        "source_page_title": source_page_title,
        "source_url": wikipedia_page_url(source_page_title),
        "revision_id": int(revision_id),
        "permanent_url": wikipedia_permanent_url(source_page_title, revision_id),
        "source_access_date": accessed_at,
        "license": LICENSE,
        "attribution_required": True,
        "evidence_status": "secondary seed",
        "public_claim_status": "candidate",
        "match_confidence": "candidate",
    }


def parse_zx_spectrum_rows(
    html: str,
    *,
    source_page_title: str,
    revision_id: int | str,
    linked_qids: dict[str, str] | None = None,
    accessed_at: str,
) -> list[dict[str, Any]]:
    linked_qids = linked_qids or {}
    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict[str, Any]] = []
    for table in soup.find_all("table"):
        headers = [_clean_text(th.get_text(" ", strip=True)).casefold() for th in table.find_all("th")]
        if not {"title", "publisher", "developer", "licensed from", "release date"}.issubset(set(headers)):
            continue
        for tr in table.find_all("tr")[1:]:
            cells = tr.find_all(["td", "th"])
            if len(cells) < 5:
                continue
            title = _clean_text(cells[0].get_text(" ", strip=True))
            if not title:
                continue
            article_title = _link_title(cells[0])
            row = _base_row(
                title=title,
                platform="ZX Spectrum",
                source_page_title=source_page_title,
                revision_id=revision_id,
                accessed_at=accessed_at,
                wikidata_qid=linked_qids.get(article_title or title, ""),
                article_title=article_title,
            )
            row.update({
                "publisher_as_printed": _clean_text(cells[1].get_text(" ", strip=True)),
                "developer_as_printed": _clean_text(cells[2].get_text(" ", strip=True)),
                "licensed_from_as_printed": _clean_text(cells[3].get_text(" ", strip=True)),
                "release_date_as_printed": _clean_text(cells[4].get_text(" ", strip=True)),
            })
            rows.append(row)
    return rows


def parse_c64_seed_rows(
    html: str,
    *,
    source_page_title: str,
    revision_id: int | str,
    linked_qids: dict[str, str] | None = None,
    accessed_at: str,
) -> list[dict[str, Any]]:
    linked_qids = linked_qids or {}
    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict[str, Any]] = []
    for item in soup.select("div.div-col li"):
        title_node = item.find("a") or item
        title = _clean_text(title_node.get_text(" ", strip=True))
        if not title:
            continue
        article_title = _link_title(item)
        text = _clean_text(item.get_text(" ", strip=True))
        remainder = text[len(title):].strip() if text.startswith(title) else text
        publisher = ""
        match = re.search(r"\(([^()]+)\)", remainder)
        if match:
            publisher = _clean_text(match.group(1))
        row = _base_row(
            title=title,
            platform="Commodore 64",
            source_page_title=source_page_title,
            revision_id=revision_id,
            accessed_at=accessed_at,
            wikidata_qid=linked_qids.get(article_title or title, ""),
            article_title=article_title,
        )
        row.update({
            "publisher_as_printed": publisher,
            "developer_as_printed": "",
            "licensed_from_as_printed": "",
            "release_date_as_printed": "",
        })
        rows.append(row)
    return rows


def rows_to_source_items(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items = []
    for row in rows:
        summary = f"{row['platform']} title seed from {row['source_page_title']}; secondary candidate metadata only."
        items.append({
            "source_item_id": row["source_item_id"],
            "publication_id": "publication:wikipedia",
            "issue_id": "",
            "item_type": "wikipedia platform seed",
            "title": row["title"],
            "archive_url": row["permanent_url"],
            "summary": summary,
            "rights_note": "Structured metadata only; source page is CC BY-SA and attribution is required.",
            "accessed_at": row["source_access_date"],
            "content_hash": content_hash(json.dumps(row, sort_keys=True)),
            "extraction_status": "parsed",
            "machine": row["platform"],
            "printed_company": row.get("publisher_as_printed", ""),
            "source_status": "secondary seed",
        })
    return items


def rows_to_source_assertions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    assertions: list[dict[str, Any]] = []
    for row in rows:
        base = {
            "source_item_id": row["source_item_id"],
            "source_system": SOURCE_SYSTEM,
            "subject_type": "game",
            "subject_label_as_printed": row["title"],
            "confidence": "secondary seed",
            "assertion_status": "candidate",
            "public_claim_status": "candidate",
            "evidence_status": "secondary seed",
            "date_as_printed": row.get("release_date_as_printed", ""),
            "place_as_printed": "",
            "platform_as_printed": row["platform"],
            "source_url": row["source_url"],
            "source_page_title": row["source_page_title"],
            "revision_id": row["revision_id"],
            "permanent_url": row["permanent_url"],
            "license": row["license"],
            "attribution_required": row["attribution_required"],
            "notes": "Wikipedia-derived source assertion; do not promote without corroboration.",
        }
        assertion_specs = [
            ("title_seed", "game", row["title"], ""),
            ("publisher_as_printed", "organisation", row.get("publisher_as_printed", ""), ""),
            ("developer_as_printed", "organisation", row.get("developer_as_printed", ""), ""),
            ("licensed_from_as_printed", "organisation", row.get("licensed_from_as_printed", ""), ""),
            ("release_date_as_printed", "date", row.get("release_date_as_printed", ""), ""),
        ]
        for predicate, object_type, object_label, role in assertion_specs:
            if not object_label:
                continue
            assertions.append({
                "assertion_id": stable_id("assertion", SOURCE_SYSTEM, row["source_page_title"], row["title"], predicate, object_label),
                **base,
                "predicate": predicate,
                "object_type": object_type,
                "object_label_as_printed": object_label,
                "role_as_printed": role,
            })
    return assertions


def rows_to_external_identifiers(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    identifiers: list[dict[str, Any]] = []
    for row in rows:
        if row.get("wikidata_qid"):
            identifiers.append({
                "external_id_record": stable_id("external-id", "wikidata", row["wikidata_qid"], row["title"]),
                "entity_type": "game",
                "entity_id": "",
                "source_system": "wikidata",
                "external_id": row["wikidata_qid"],
                "external_url": f"https://www.wikidata.org/wiki/{row['wikidata_qid']}",
                "match_status": "candidate",
                "match_confidence": "linked from Wikipedia list row",
                "match_method": "mediawiki pageprops wikibase_item",
                "source_item_ids": [row["source_item_id"]],
                "reviewed_by": "",
                "reviewed_at": "",
                "notes": "External ID captured from linked Wikipedia page; not automatically reconciled.",
            })
    return identifiers


class MediaWikiClient:
    def __init__(
        self,
        *,
        cache_dir: Path = DEFAULT_CACHE_DIR,
        request_log_path: Path = DEFAULT_REQUEST_LOG,
        session: requests.Session | None = None,
        sleep: Any = time.sleep,
        min_interval_seconds: float = 1.0,
    ) -> None:
        self.cache_dir = cache_dir
        self.request_log_path = request_log_path
        self.session = session or requests.Session()
        if hasattr(self.session, "headers"):
            self.session.headers.update({"User-Agent": DEFAULT_USER_AGENT})
        self.sleep = sleep
        self.min_interval_seconds = min_interval_seconds
        self.last_request_at = 0.0

    def _cache_path(self, params: dict[str, Any]) -> Path:
        return self.cache_dir / f"{content_hash(urlencode(sorted((key, str(value)) for key, value in params.items())))}.json"

    def get(self, params: dict[str, Any], *, resume: bool = True) -> dict[str, Any]:
        full_params = {"format": "json", "formatversion": "2", **params}
        cache_path = self._cache_path(full_params)
        if resume and cache_path.exists():
            return json.loads(cache_path.read_text(encoding="utf-8"))
        wait = self.min_interval_seconds - (time.monotonic() - self.last_request_at)
        if wait > 0:
            self.sleep(wait)
        response = self.session.get(MEDIAWIKI_API, params=full_params, timeout=30)
        self.last_request_at = time.monotonic()
        payload = response.json()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        self.request_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.request_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"url": MEDIAWIKI_API, "params": full_params, "status_code": response.status_code}, sort_keys=True))
            handle.write("\n")
        return payload


def fetch_linked_qids(client: MediaWikiClient, titles: list[str], *, resume: bool = True) -> dict[str, str]:
    qids: dict[str, str] = {}
    for offset in range(0, len(titles), 50):
        batch = titles[offset:offset + 50]
        if not batch:
            continue
        payload = client.get({
            "action": "query",
            "prop": "pageprops",
            "titles": "|".join(batch),
            "redirects": "1",
        }, resume=resume)
        normalised = {
            row.get("from"): row.get("to")
            for row in payload.get("query", {}).get("normalized", []) or []
        }
        redirects = {
            row.get("from"): row.get("to")
            for row in payload.get("query", {}).get("redirects", []) or []
        }
        for page in payload.get("query", {}).get("pages", []) or []:
            qid = (page.get("pageprops") or {}).get("wikibase_item", "")
            title = page.get("title", "")
            if not qid or not title:
                continue
            qids[title] = qid
            for original, target in {**normalised, **redirects}.items():
                if target == title:
                    qids[original] = qid
    return qids


def fetch_platform_list_rows(
    *,
    client: MediaWikiClient | None = None,
    accessed_at: str = "2026-06-20",
    resume: bool = True,
) -> list[dict[str, Any]]:
    client = client or MediaWikiClient()
    pages = [
        ("zx", ZX_SPECTRUM_PAGE),
        ("c64", C64_A_M_PAGE_CANONICAL),
        ("c64", C64_N_Z_PAGE_CANONICAL),
    ]
    rows: list[dict[str, Any]] = []
    for parser_kind, page_title in pages:
        payload = client.get({
            "action": "parse",
            "page": page_title,
            "prop": "text|revid",
        }, resume=resume)
        parsed = payload["parse"]
        html = parsed["text"]
        linked_qids = fetch_linked_qids(client, linked_article_titles_from_html(html), resume=resume)
        if parser_kind == "zx":
            rows.extend(parse_zx_spectrum_rows(
                html,
                source_page_title=parsed["title"],
                revision_id=parsed["revid"],
                linked_qids=linked_qids,
                accessed_at=accessed_at,
            ))
        else:
            rows.extend(parse_c64_seed_rows(
                html,
                source_page_title=parsed["title"],
                revision_id=parsed["revid"],
                linked_qids=linked_qids,
                accessed_at=accessed_at,
            ))
    return rows


def merge_raw_wikipedia_rows(rows: list[dict[str, Any]], raw_dir: Path = ROOT / "data" / "raw" / "wikipedia-platform-lists") -> dict[str, int]:
    source_items = rows_to_source_items(rows)
    assertions = rows_to_source_assertions(rows)
    identifiers = rows_to_external_identifiers(rows)
    write_jsonl(raw_dir / "issues.jsonl", [])
    write_jsonl(raw_dir / "source-items.jsonl", source_items, sort_key="source_item_id")
    write_jsonl(raw_dir / "source-assertions.jsonl", assertions, sort_key="assertion_id")
    write_jsonl(raw_dir / "external-identifiers.jsonl", identifiers, sort_key="external_id_record")
    return {"rows": len(rows), "source_items": len(source_items), "assertions": len(assertions), "external_identifiers": len(identifiers)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse Wikipedia platform game list API payloads into secondary seed records.")
    parser.add_argument("--from-jsonl", help="Optional JSONL rows already parsed from MediaWiki API output.")
    parser.add_argument("--fetch", action="store_true", help="Fetch the configured MediaWiki API pages and cache responses.")
    parser.add_argument("--no-resume", action="store_true", help="Ignore cached MediaWiki API responses.")
    parser.add_argument("--accessed-at", default="2026-06-20")
    parser.add_argument("--raw-dir", default=str(ROOT / "data" / "raw" / "wikipedia-platform-lists"))
    args = parser.parse_args()
    if args.fetch:
        rows = fetch_platform_list_rows(accessed_at=args.accessed_at, resume=not args.no_resume)
    else:
        rows = read_jsonl(Path(args.from_jsonl)) if args.from_jsonl else []
    print(merge_raw_wikipedia_rows(rows, Path(args.raw_dir)))


if __name__ == "__main__":
    main()

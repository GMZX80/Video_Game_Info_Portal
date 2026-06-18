from __future__ import annotations

import argparse
from collections import OrderedDict
from pathlib import Path
from typing import Any

from .common import CURATED_DIR, RAW_DIR, ROOT, content_hash, read_jsonl, stable_id, write_jsonl


PUBLICATIONS = [
    {
        "publication_id": "publication:sinclair-user",
        "canonical_title": "Sinclair User",
        "aliases": ["SUMO", "Sinclair User Magazine Online"],
        "publisher": "ECC Publications / later publishers",
        "start_date": "1982-04",
        "end_date": "1993-04",
        "archive_hosts": ["Sinclair User Magazine Online"],
        "notes": "Archive metadata used as evidence catalogue, not mirrored article text.",
    },
    {
        "publication_id": "publication:crash",
        "canonical_title": "CRASH",
        "aliases": ["CRASH Online Edition"],
        "publisher": "Newsfield / Europress",
        "start_date": "1984-02",
        "end_date": "1992",
        "archive_hosts": ["CRASH: The Online Edition"],
        "notes": "Online edition preserves article pages with author permissions notes.",
    },
    {
        "publication_id": "publication:zzap64",
        "canonical_title": "Zzap!64",
        "aliases": ["ZzapBible", "The Def Guide to Zzap!64"],
        "publisher": "Newsfield and later publishers",
        "start_date": "1985",
        "end_date": "2002",
        "archive_hosts": ["The Def Guide to Zzap!64"],
        "notes": "ZzapBible company field is preserved as printed and not treated as developer.",
    },
    {
        "publication_id": "publication:spot-on",
        "canonical_title": "SPOT*On",
        "aliases": ["Spectrum Opus Textorial"],
        "publisher": "Jim Grimwood / SPOT Enterprises",
        "start_date": "",
        "end_date": "",
        "archive_hosts": ["Globalnet"],
        "notes": "Secondary index of Sinclair Spectrum magazine references.",
    },
    {
        "publication_id": "publication:ttfn",
        "canonical_title": "The Type Fantastic",
        "aliases": ["TTFn"],
        "publisher": "Jim Grimwood / SPOT Enterprises",
        "start_date": "",
        "end_date": "",
        "archive_hosts": ["Globalnet"],
        "notes": "Type-in metadata index; listings are not republished.",
    },
]

PLACES = [
    ("place:newcastle-upon-tyne", "Newcastle upon Tyne", ["Newcastle"], "Tyne and Wear"),
    ("place:gateshead", "Gateshead", [], "Tyne and Wear"),
    ("place:blaydon", "Blaydon", [], "Tyne and Wear"),
    ("place:swalwell", "Swalwell", [], "Tyne and Wear"),
    ("place:ryton", "Ryton", [], "Tyne and Wear"),
    ("place:team-valley", "Team Valley", [], "Tyne and Wear"),
    ("place:sunderland", "Sunderland", [], "Tyne and Wear"),
    ("place:washington", "Washington", [], "Tyne and Wear"),
    ("place:chester-le-street", "Chester-le-Street", [], "County Durham"),
    ("place:county-durham", "County Durham", ["Durham"], "County Durham"),
    ("place:northumberland", "Northumberland", [], "Northumberland"),
    ("place:stockton-on-tees", "Stockton-on-Tees", ["Stockton"], "Teesside"),
    ("place:middlesbrough", "Middlesbrough", [], "Teesside"),
    ("place:teesside", "Teesside", [], "Teesside"),
    ("place:tyne-and-wear", "Tyne and Wear", [], "Tyne and Wear"),
]

PLATFORMS = [
    ("platform:zx-spectrum", "ZX Spectrum", ["Spectrum", "SP"]),
    ("platform:zx81", "ZX81", ["ZX-81", "81"]),
    ("platform:zx80", "ZX80", ["ZX-80", "80"]),
    ("platform:bbc-micro", "BBC Micro", ["BBC"]),
    ("platform:acorn-electron", "Acorn Electron", ["Electron"]),
    ("platform:commodore-64", "Commodore 64", ["C64"]),
    ("platform:sinclair-ql", "Sinclair QL", ["QL"]),
]


def _dedupe(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    result: OrderedDict[str, dict[str, Any]] = OrderedDict()
    for row in rows:
        value = row.get(key)
        if value and value not in result:
            result[value] = row
    return list(result.values())


def normalise(raw_dir: Path = RAW_DIR, curated_dir: Path = CURATED_DIR) -> dict[str, int]:
    issues = []
    source_items = []
    for archive_dir in sorted(raw_dir.glob("*")):
        if not archive_dir.is_dir():
            continue
        for row in read_jsonl(archive_dir / "issues.jsonl"):
            issues.append({
                "issue_id": row["issue_id"],
                "publication_id": row["publication_id"],
                "issue_number": row.get("issue_number", ""),
                "cover_date": row.get("cover_date", ""),
                "date_precision": row.get("date_precision", "unknown"),
                "volume": "",
                "cover_url": "",
                "index_url": row.get("index_url", ""),
                "rights_notes": "Issue-level index metadata only.",
            })
        for row in read_jsonl(archive_dir / "source-items.jsonl"):
            source_items.append({
                "source_item_id": row["source_item_id"],
                "publication_id": row["publication_id"],
                "issue_id": row.get("issue_id", ""),
                "item_type": row.get("item_type", "index-only entry"),
                "title": row.get("title", ""),
                "subtitle": "",
                "byline_text": row.get("byline_text", ""),
                "named_article_authors": [],
                "page_start": "",
                "page_end": "",
                "archive_url": row.get("archive_url", ""),
                "original_locator": row.get("original_locator", ""),
                "date": row.get("date", ""),
                "summary": row.get("summary", ""),
                "rights_note": row.get("rights_note", "Link and paraphrase only."),
                "accessed_at": row.get("accessed_at", "2026-06-18"),
                "content_hash": row.get("content_hash", content_hash(str(row))),
                "extraction_status": "parsed",
                "printed_company": row.get("printed_company", ""),
                "score": row.get("score", ""),
                "award": row.get("award", ""),
                "machine": row.get("machine", ""),
                "program_type": row.get("program_type", ""),
                "language": row.get("language", ""),
            })

    organisations = []
    for item in source_items:
        company = item.get("printed_company", "")
        if company:
            organisations.append({
                "organisation_id": stable_id("organisation", company),
                "canonical_name": company,
                "aliases": [],
                "organisation_type": "printed company or label",
                "legal_name": "",
                "labels": [],
                "locations": [],
                "active_dates": "",
                "founders": [],
                "sources": [item["source_item_id"]],
                "evidence_status": "candidate",
            })

    games = []
    releases = []
    for item in source_items:
        if item["item_type"] in {"review", "type-in program", "index-only entry"} and item["title"]:
            game_id = stable_id("game", item["title"])
            games.append({
                "game_id": game_id,
                "canonical_title": item["title"],
                "title_variants": [],
                "series": "",
                "initial_release_date": "",
                "genre": item.get("program_type", ""),
                "sources": [item["source_item_id"]],
            })
            platform_id = "platform:zx-spectrum" if item.get("machine") == "ZX Spectrum" else ""
            if platform_id:
                releases.append({
                    "release_id": stable_id("release", item["title"], platform_id),
                    "game_id": game_id,
                    "platform_id": platform_id,
                    "release_title": item["title"],
                    "date": item.get("date", ""),
                    "publisher": "",
                    "developer": "",
                    "label": item.get("printed_company", ""),
                    "media": item.get("file_type", ""),
                    "territory": "UK",
                    "conversion_from": "",
                    "sources": [item["source_item_id"]],
                    "evidence_status": "index-only",
                })

    write_jsonl(curated_dir / "publications.jsonl", PUBLICATIONS, sort_key="publication_id")
    write_jsonl(curated_dir / "issues.jsonl", _dedupe(issues, "issue_id"), sort_key="issue_id")
    write_jsonl(curated_dir / "source-items.jsonl", _dedupe(source_items, "source_item_id"), sort_key="source_item_id")
    write_jsonl(curated_dir / "organisations.jsonl", _dedupe(organisations, "organisation_id"), sort_key="organisation_id")
    write_jsonl(curated_dir / "games.jsonl", _dedupe(games, "game_id"), sort_key="game_id")
    write_jsonl(curated_dir / "releases.jsonl", _dedupe(releases, "release_id"), sort_key="release_id")
    write_jsonl(curated_dir / "platforms.jsonl", [
        {"platform_id": pid, "name": name, "aliases": aliases} for pid, name, aliases in PLATFORMS
    ], sort_key="platform_id")
    write_jsonl(curated_dir / "places.jsonl", [
        {"place_id": pid, "name": name, "aliases": aliases, "region": region} for pid, name, aliases, region in PLACES
    ], sort_key="place_id")
    for file_name in ["people", "credits", "claims", "evidence", "north-east-connections", "aliases", "media-assets", "photo-identifications", "relationships", "mentions"]:
        path = curated_dir / f"{file_name}.jsonl"
        if not path.exists():
            write_jsonl(path, [])
    return {
        "issues": len(_dedupe(issues, "issue_id")),
        "source_items": len(_dedupe(source_items, "source_item_id")),
        "organisations": len(_dedupe(organisations, "organisation_id")),
        "games": len(_dedupe(games, "game_id")),
        "releases": len(_dedupe(releases, "release_id")),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalise raw archive records into canonical JSONL.")
    parser.parse_args()
    print(normalise())


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
from collections import OrderedDict
from pathlib import Path
from typing import Any

from .common import CURATED_DIR, RAW_DIR, content_hash, read_jsonl, stable_id, write_jsonl


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
    {
        "publication_id": "publication:stairway-to-hell",
        "canonical_title": "Stairway To Hell",
        "aliases": ["The BBC Micro and Electron Games Archive"],
        "publisher": "Stairway To Hell archive contributors",
        "start_date": "",
        "end_date": "",
        "archive_hosts": ["Stairway To Hell"],
        "notes": "Archive host for original material and reprinted historical sources. Original magazine provenance is stored on each source item.",
    },
    {
        "publication_id": "publication:wikipedia",
        "canonical_title": "Wikipedia",
        "aliases": ["MediaWiki", "Wikipedia platform lists"],
        "publisher": "Wikimedia Foundation / volunteer contributors",
        "start_date": "",
        "end_date": "",
        "archive_hosts": ["en.wikipedia.org"],
        "notes": "Secondary seed metadata only. Rows carry CC BY-SA attribution metadata and are not promoted without corroboration.",
    },
    {
        "publication_id": "publication:wikidata",
        "canonical_title": "Wikidata",
        "aliases": ["Wikidata item statements"],
        "publisher": "Wikimedia Foundation / volunteer contributors",
        "start_date": "",
        "end_date": "",
        "archive_hosts": ["wikidata.org"],
        "notes": "Referenced statement metadata only. Claims remain source assertions until reviewed.",
    },
    {
        "publication_id": "publication:mobygames-api",
        "canonical_title": "MobyGames API",
        "aliases": ["MobyGames official API"],
        "publisher": "MobyGames",
        "start_date": "",
        "end_date": "",
        "archive_hosts": ["api.mobygames.com"],
        "notes": "Official API metadata only; no MobyGames HTML scraping.",
    },
    {
        "publication_id": "publication:world-of-spectrum",
        "canonical_title": "World of Spectrum",
        "aliases": ["WoS", "World of Spectrum API"],
        "publisher": "World of Spectrum",
        "start_date": "",
        "end_date": "",
        "archive_hosts": ["worldofspectrum.org"],
        "notes": "Structured API metadata only; no game files, scans or screenshots are downloaded.",
    },
    {
        "publication_id": "publication:zxdb",
        "canonical_title": "ZXDB",
        "aliases": ["ZX Spectrum Database"],
        "publisher": "ZXDB project contributors",
        "start_date": "",
        "end_date": "",
        "archive_hosts": ["github.com/zxdb/ZXDB"],
        "notes": "Structured database/export metadata only.",
    },
    {
        "publication_id": "publication:zxinfo",
        "canonical_title": "ZXInfo",
        "aliases": ["ZXInfo API", "ZXInfo.dk"],
        "publisher": "ZXInfo contributors",
        "start_date": "",
        "end_date": "",
        "archive_hosts": ["api.zxinfo.dk"],
        "notes": "ZXDB-backed API metadata only; binary files are out of scope.",
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

PLATFORM_BY_MACHINE = {
    "ZX Spectrum": "platform:zx-spectrum",
    "ZX81": "platform:zx81",
    "ZX80": "platform:zx80",
    "BBC Micro": "platform:bbc-micro",
    "Acorn Electron": "platform:acorn-electron",
    "Commodore 64": "platform:commodore-64",
    "Sinclair QL": "platform:sinclair-ql",
}

CREDIT_ROLE_MAP = {
    "programmer": "programmer",
    "author": "game author",
    "named game author": "game author",
    "conversion programmer": "conversion programmer",
    "graphics": "graphics",
    "artist": "artist",
    "music": "music",
    "sound": "sound",
    "designer": "designer",
    "producer": "producer",
}


def _dedupe(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    result: OrderedDict[str, dict[str, Any]] = OrderedDict()
    for row in rows:
        value = row.get(key)
        if value and value not in result:
            result[value] = row
    return list(result.values())


def _normalised_source_item(row: dict[str, Any]) -> dict[str, Any]:
    contributors = row.get("named_contributors", []) or []
    article_authors = row.get("named_article_authors", []) or []
    if row.get("byline_text") and row.get("item_type") not in {"review", "game catalogue entry"}:
        article_authors = [*article_authors, row["byline_text"]]
    return {
        "source_item_id": row["source_item_id"],
        "publication_id": row["publication_id"],
        "issue_id": row.get("issue_id", ""),
        "item_type": row.get("item_type", "index-only entry"),
        "title": row.get("title", ""),
        "subtitle": row.get("subtitle", ""),
        "byline_text": row.get("byline_text", ""),
        "named_article_authors": article_authors,
        "named_contributors": contributors,
        "page_start": row.get("page_start", ""),
        "page_end": row.get("page_end", ""),
        "archive_url": row.get("archive_url", ""),
        "original_locator": row.get("original_locator", ""),
        "original_publication": row.get("original_publication", ""),
        "original_author": row.get("original_author", ""),
        "date": row.get("date", ""),
        "summary": row.get("summary", ""),
        "rights_note": row.get("rights_note", "Link and paraphrase only."),
        "accessed_at": row.get("accessed_at", "2026-06-18"),
        "content_hash": row.get("content_hash", content_hash(str(row))),
        "extraction_status": row.get("extraction_status", "parsed"),
        "contemporary_or_retrospective": row.get("contemporary_or_retrospective", ""),
        "printed_company": row.get("printed_company", ""),
        "score": row.get("score", ""),
        "award": row.get("award", ""),
        "machine": row.get("machine", ""),
        "program_type": row.get("program_type", ""),
        "language": row.get("language", ""),
        "price": row.get("price", ""),
        "memory": row.get("memory", ""),
        "controls": row.get("controls", ""),
        "source_status": row.get("source_status", ""),
    }


def normalise(raw_dir: Path = RAW_DIR, curated_dir: Path = CURATED_DIR) -> dict[str, int]:
    issues: list[dict[str, Any]] = []
    source_items: list[dict[str, Any]] = []
    source_assertions: list[dict[str, Any]] = []
    external_identifiers: list[dict[str, Any]] = []
    raw_photo_identifications: list[dict[str, Any]] = []
    raw_media_assets: list[dict[str, Any]] = []
    for archive_dir in sorted(raw_dir.glob("*")):
        if not archive_dir.is_dir():
            continue
        for row in read_jsonl(archive_dir / "issues.jsonl"):
            issues.append(
                {
                    "issue_id": row["issue_id"],
                    "publication_id": row["publication_id"],
                    "issue_number": row.get("issue_number", ""),
                    "cover_date": row.get("cover_date", ""),
                    "date_precision": row.get("date_precision", "unknown"),
                    "volume": row.get("volume", ""),
                    "cover_url": row.get("cover_url", ""),
                    "index_url": row.get("index_url", ""),
                    "staff": row.get("staff", {}),
                    "article_count": row.get("article_count", 0),
                    "rights_notes": "Issue-level bibliographic metadata only.",
                }
            )
        for row in read_jsonl(archive_dir / "source-items.jsonl"):
            source_items.append(_normalised_source_item(row))
        source_assertions.extend(read_jsonl(archive_dir / "source-assertions.jsonl"))
        external_identifiers.extend(read_jsonl(archive_dir / "external-identifiers.jsonl"))
        raw_photo_identifications.extend(read_jsonl(archive_dir / "photo-identifications.jsonl"))
        raw_media_assets.extend(read_jsonl(archive_dir / "media-assets.jsonl"))

    source_items = _dedupe(source_items, "source_item_id")

    organisations: list[dict[str, Any]] = []
    for item in source_items:
        company = item.get("printed_company", "")
        if company:
            organisations.append(
                {
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
                }
            )

    games: list[dict[str, Any]] = []
    releases: list[dict[str, Any]] = []
    people: list[dict[str, Any]] = []
    credits: list[dict[str, Any]] = []
    mentions: list[dict[str, Any]] = []

    for item in source_items:
        game_id = ""
        release_id = ""
        if item["item_type"] in {
            "review",
            "type-in program",
            "index-only entry",
            "game catalogue entry",
            "unreleased-game record",
        } and item["title"]:
            game_id = stable_id("game", item["title"])
            games.append(
                {
                    "game_id": game_id,
                    "canonical_title": item["title"],
                    "title_variants": [],
                    "series": "",
                    "initial_release_date": "",
                    "genre": item.get("program_type", ""),
                    "sources": [item["source_item_id"]],
                }
            )
            platform_id = PLATFORM_BY_MACHINE.get(item.get("machine", ""), "")
            if platform_id:
                release_id = stable_id("release", item["title"], platform_id)
                releases.append(
                    {
                        "release_id": release_id,
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
                        "evidence_status": "index-only" if not item.get("named_contributors") else "source-named contributor",
                    }
                )

        for contributor in item.get("named_contributors", []) or []:
            name = str(contributor.get("name", "")).strip()
            role_as_printed = str(contributor.get("role_as_printed", "")).strip()
            if not name:
                continue
            person_id = stable_id("person", name)
            people.append(
                {
                    "person_id": person_id,
                    "canonical_name": name,
                    "aliases": [],
                    "disambiguation_notes": "Name preserved exactly as printed; automatic alias merging is disabled.",
                    "professional_roles": [role_as_printed] if role_as_printed else [],
                    "biography_summary": "",
                    "evidence_status": "named in source",
                    "sources": [item["source_item_id"]],
                }
            )
            mentions.append(
                {
                    "mention_id": stable_id("mention", item["source_item_id"], person_id, role_as_printed),
                    "source_item_id": item["source_item_id"],
                    "entity_type": "person",
                    "entity_id": person_id,
                    "role_as_printed": role_as_printed,
                    "date_as_printed": contributor.get("date", ""),
                }
            )
            normalised_role = CREDIT_ROLE_MAP.get(role_as_printed.lower())
            if game_id and normalised_role:
                credits.append(
                    {
                        "credit_id": stable_id("credit", item["source_item_id"], person_id, normalised_role),
                        "release_id": release_id,
                        "game_id": game_id,
                        "person_id": person_id,
                        "organisation_id": "",
                        "role": normalised_role,
                        "role_as_printed": role_as_printed,
                        "original_or_conversion": "conversion" if "conversion" in normalised_role else "unspecified",
                        "employment_status": "not inferred from credit",
                        "source_id": item["source_item_id"],
                        "confidence": "explicitly named in source metadata",
                        "notes": "A source credit does not establish employment status.",
                    }
                )

        for author in item.get("named_article_authors", []) or []:
            name = str(author).strip()
            if not name:
                continue
            person_id = stable_id("person", name)
            people.append(
                {
                    "person_id": person_id,
                    "canonical_name": name,
                    "aliases": [],
                    "disambiguation_notes": "Article author; not automatically a game contributor.",
                    "professional_roles": ["Article author"],
                    "biography_summary": "",
                    "evidence_status": "named in source",
                    "sources": [item["source_item_id"]],
                }
            )
            mentions.append(
                {
                    "mention_id": stable_id("mention", item["source_item_id"], person_id, "article-author"),
                    "source_item_id": item["source_item_id"],
                    "entity_type": "person",
                    "entity_id": person_id,
                    "role_as_printed": "Article author",
                    "date_as_printed": "",
                }
            )

    write_jsonl(curated_dir / "publications.jsonl", PUBLICATIONS, sort_key="publication_id")
    write_jsonl(curated_dir / "issues.jsonl", _dedupe(issues, "issue_id"), sort_key="issue_id")
    write_jsonl(curated_dir / "source-items.jsonl", source_items, sort_key="source_item_id")
    write_jsonl(curated_dir / "organisations.jsonl", _dedupe(organisations, "organisation_id"), sort_key="organisation_id")
    write_jsonl(curated_dir / "games.jsonl", _dedupe(games, "game_id"), sort_key="game_id")
    write_jsonl(curated_dir / "releases.jsonl", _dedupe(releases, "release_id"), sort_key="release_id")
    write_jsonl(curated_dir / "people.jsonl", _dedupe(people, "person_id"), sort_key="person_id")
    write_jsonl(curated_dir / "credits.jsonl", _dedupe(credits, "credit_id"), sort_key="credit_id")
    write_jsonl(curated_dir / "mentions.jsonl", _dedupe(mentions, "mention_id"), sort_key="mention_id")
    write_jsonl(curated_dir / "source-assertions.jsonl", _dedupe(source_assertions, "assertion_id"), sort_key="assertion_id")
    write_jsonl(curated_dir / "external-identifiers.jsonl", _dedupe(external_identifiers, "external_id_record"), sort_key="external_id_record")
    write_jsonl(
        curated_dir / "photo-identifications.jsonl",
        _dedupe(raw_photo_identifications, "photo_identification_id"),
        sort_key="photo_identification_id",
    )
    write_jsonl(
        curated_dir / "media-assets.jsonl",
        _dedupe(raw_media_assets, "media_id"),
        sort_key="media_id",
    )
    write_jsonl(
        curated_dir / "platforms.jsonl",
        [{"platform_id": pid, "name": name, "aliases": aliases} for pid, name, aliases in PLATFORMS],
        sort_key="platform_id",
    )
    write_jsonl(
        curated_dir / "places.jsonl",
        [{"place_id": pid, "name": name, "aliases": aliases, "region": region} for pid, name, aliases, region in PLACES],
        sort_key="place_id",
    )
    for file_name in ["claims", "evidence", "north-east-connections", "aliases", "relationships"]:
        path = curated_dir / f"{file_name}.jsonl"
        if not path.exists():
            write_jsonl(path, [])
    return {
        "issues": len(_dedupe(issues, "issue_id")),
        "source_items": len(source_items),
        "organisations": len(_dedupe(organisations, "organisation_id")),
        "games": len(_dedupe(games, "game_id")),
        "releases": len(_dedupe(releases, "release_id")),
        "people": len(_dedupe(people, "person_id")),
        "credits": len(_dedupe(credits, "credit_id")),
        "source_assertions": len(_dedupe(source_assertions, "assertion_id")),
        "external_identifiers": len(_dedupe(external_identifiers, "external_id_record")),
        "photo_identifications": len(_dedupe(raw_photo_identifications, "photo_identification_id")),
        "media_assets": len(_dedupe(raw_media_assets, "media_id")),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalise raw archive records into canonical JSONL.")
    parser.parse_args()
    print(normalise())


if __name__ == "__main__":
    main()

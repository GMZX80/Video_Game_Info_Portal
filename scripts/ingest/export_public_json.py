from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .common import CURATED_DIR, GENERATED_DIR, read_jsonl, write_json
from .mobygames import export_mobygames_index

PUBLIC_STATUSES = {"verified", "strongly supported"}


def _record_label_for_connection(row: dict[str, Any]) -> str:
    connection_type = (row.get("connection_type") or "").lower()
    if row.get("status") in PUBLIC_STATUSES and "developer" in connection_type:
        return "Developer verified"
    if row.get("status") in PUBLIC_STATUSES and row.get("entity_type") == "person":
        return "Verified contributor credit"
    if "publisher only" in connection_type:
        return "Publisher only"
    return "Attribution awaiting review"


def _collection_item(row: dict[str, Any]) -> dict[str, Any]:
    status_label = {
        "verified": "Verified North East connection",
        "strongly supported": "Verified North East connection",
        "probable": "Probable - under review",
        "candidate": "Candidate awaiting verification",
    }.get(row.get("status", ""), row.get("status", "Open question"))
    if row.get("status") in PUBLIC_STATUSES and "external publisher" in row.get("connection_type", ""):
        status_label = "External publisher"
    elif row.get("status") in PUBLIC_STATUSES and "conversion" in row.get("connection_type", ""):
        status_label = "North East-developed version"
    elif row.get("status") in PUBLIC_STATUSES and "heritage" in row.get("connection_type", ""):
        status_label = "Staff heritage"
    return {
        "id": row["connection_id"],
        "name": row["entity_name"],
        "entity_type": row["entity_type"],
        "connection_type": row["connection_type"],
        "why_included": row["explanatory_text"],
        "place": row.get("place_name", ""),
        "date": row.get("start_date", "") or row.get("issue_label", ""),
        "status": row["status"],
        "badge": status_label,
        "record_label": _record_label_for_connection(row),
        "source_magazine": row.get("source_magazine", ""),
        "issue": row.get("issue_label", ""),
        "source_url": row.get("source_url", ""),
        "qualification": "" if row["status"] in PUBLIC_STATUSES else "Awaiting source inspection.",
    }


def export_public_json(curated_dir: Path = CURATED_DIR, out_dir: Path = GENERATED_DIR) -> dict[str, int]:
    connections = read_jsonl(curated_dir / "north-east-connections.jsonl")
    confirmed = [_collection_item(row) for row in connections if row.get("status") in PUBLIC_STATUSES and row.get("evidence_ids")]
    probable = [_collection_item(row) for row in connections if row.get("status") == "probable"]
    candidates = [_collection_item(row) for row in connections if row.get("status") == "candidate"]
    source_items = read_jsonl(curated_dir / "source-items.jsonl")
    games = read_jsonl(curated_dir / "games.jsonl")
    releases = read_jsonl(curated_dir / "releases.jsonl")
    organisations = read_jsonl(curated_dir / "organisations.jsonl")
    people = read_jsonl(curated_dir / "people.jsonl")
    evidence = read_jsonl(curated_dir / "evidence.jsonl")
    source_assertions = read_jsonl(curated_dir / "source-assertions.jsonl")
    external_identifiers = read_jsonl(curated_dir / "external-identifiers.jsonl")
    payload = {
        "generated_at": "2026-06-18",
        "qualification": "Only verified or strongly supported connections appear in confirmed results. Publisher/index-only records are labelled as probable or candidate until record-level source inspection supports the North East claim.",
        "confirmed": sorted(confirmed, key=lambda row: (row["name"], row["connection_type"])),
        "probable": sorted(probable, key=lambda row: (row["name"], row["connection_type"])),
        "candidates": sorted(candidates, key=lambda row: (row["name"], row["connection_type"])),
    }
    write_json(out_dir / "north-east-collection.json", payload)
    source_item_label_rules = {
        "index-only entry": "Magazine index entry",
        "review": "Reviewed release",
        "type-in program": "Platform-specific release",
        "company profile": "Attribution awaiting review",
        "interview": "Attribution awaiting review",
        "feature": "Magazine index entry",
        "news report": "Magazine index entry",
    }
    game_index_scope = {
        "public_record_label": "Magazine index entry",
        "developer_status": "Attribution awaiting review",
        "note": "Game names in this index are title records generated from magazine/archive indexes. They are not complete release histories unless linked to platform-specific release evidence.",
    }
    public_releases = [
        {
            **row,
            "public_record_label": "Platform-specific release",
            "developer_status": "Developer verified" if row.get("developer") else "Attribution awaiting review",
            "publisher_status": "Publisher only" if row.get("publisher") else "Attribution awaiting review",
        }
        for row in releases
    ]
    write_json(out_dir / "source-items-index.json", {
        "label_rules": source_item_label_rules,
        "field_label_rules": {
            "printed_company": "Publisher only when populated; this field must not be read as developer verification.",
        },
        "items": source_items,
    })
    write_json(out_dir / "games-index.json", {
        "record_scope": game_index_scope,
        "games": games,
    })
    write_json(out_dir / "releases-index.json", {"releases": public_releases})
    write_json(out_dir / "people-index.json", {"people": people})
    write_json(out_dir / "organisations-index.json", {"organisations": organisations})
    write_json(out_dir / "evidence-index.json", {"evidence": evidence})
    public_assertions = [
        {
            "assertion_id": row["assertion_id"],
            "source_item_id": row.get("source_item_id", ""),
            "source_system": row.get("source_system", ""),
            "subject_type": row.get("subject_type", ""),
            "subject_label_as_printed": row.get("subject_label_as_printed", ""),
            "predicate": row.get("predicate", ""),
            "object_type": row.get("object_type", ""),
            "object_label_as_printed": row.get("object_label_as_printed", ""),
            "role_as_printed": row.get("role_as_printed", ""),
            "date_as_printed": row.get("date_as_printed", ""),
            "platform_as_printed": row.get("platform_as_printed", ""),
            "confidence": row.get("confidence", ""),
            "assertion_status": "candidate" if row.get("source_system") == "wikipedia" else row.get("assertion_status", ""),
            "public_claim_status": "candidate" if row.get("source_system") == "wikipedia" else row.get("public_claim_status", ""),
            "evidence_status": row.get("evidence_status", ""),
            "source_url": row.get("source_url", ""),
            "source_page_title": row.get("source_page_title", ""),
            "revision_id": row.get("revision_id", ""),
            "permanent_url": row.get("permanent_url", ""),
            "license": row.get("license", ""),
            "attribution_required": row.get("attribution_required", False),
            "notes": row.get("notes", ""),
        }
        for row in source_assertions
        if row.get("assertion_status") != "private"
    ]
    public_external_identifiers = [
        {
            "external_id_record": row["external_id_record"],
            "entity_type": row.get("entity_type", ""),
            "entity_id": row.get("entity_id", ""),
            "source_system": row.get("source_system", ""),
            "external_id": row.get("external_id", ""),
            "external_url": row.get("external_url", ""),
            "match_status": row.get("match_status", ""),
            "match_confidence": row.get("match_confidence", ""),
            "match_method": row.get("match_method", ""),
            "source_item_ids": row.get("source_item_ids", []),
            "notes": row.get("notes", ""),
        }
        for row in external_identifiers
    ]
    write_json(out_dir / "source-assertions-public.json", {
        "record_scope": "Candidate source assertions. These records are not canonical facts unless a separate reviewed canonical record says so.",
        "records": public_assertions,
    })
    write_json(out_dir / "external-identifiers-public.json", {
        "record_scope": "External identifiers and candidate links for reconciliation.",
        "records": public_external_identifiers,
    })
    write_json(out_dir / "games-public.json", {"games": games})
    write_json(out_dir / "people-public.json", {"people": people})
    write_json(out_dir / "organisations-public.json", {"organisations": organisations})
    write_json(out_dir / "releases-public.json", {"releases": public_releases})
    write_json(out_dir / "credits-public.json", {"credits": read_jsonl(curated_dir / "credits.jsonl")})
    write_json(out_dir / "places-public.json", {"places": read_jsonl(curated_dir / "places.jsonl")})
    write_json(out_dir / "source-trail-public.json", {"source_items": source_items, "evidence": evidence})
    mobygames = export_mobygames_index(CURATED_DIR.parent / "sources.json", out_dir / "mobygames-index.json")
    write_json(out_dir / "timeline-events.json", {"events": []})
    write_json(out_dir / "search-index.json", {
        "items": [
            {"id": row["source_item_id"], "title": row["title"], "summary": row.get("summary", ""), "url": row.get("archive_url", "")}
            for row in source_items
        ]
    })
    return {
        "confirmed": len(confirmed),
        "probable": len(probable),
        "candidates": len(candidates),
        "mobygames": len(mobygames["records"]),
        "source_assertions": len(public_assertions),
        "external_identifiers": len(public_external_identifiers),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Export public static JSON for GitHub Pages.")
    parser.parse_args()
    print(export_public_json())


if __name__ == "__main__":
    main()

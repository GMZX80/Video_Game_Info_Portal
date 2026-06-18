from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .common import CURATED_DIR, GENERATED_DIR, read_jsonl, write_json

PUBLIC_STATUSES = {"verified", "strongly supported"}


def _collection_item(row: dict[str, Any]) -> dict[str, Any]:
    status_label = {
        "verified": "Verified North East connection",
        "strongly supported": "Verified North East connection",
        "probable": "Probable — under review",
        "candidate": "Candidate awaiting verification",
    }.get(row.get("status", ""), row.get("status", "Open question"))
    if "external publisher" in row.get("connection_type", ""):
        status_label = "External publisher"
    elif "conversion" in row.get("connection_type", ""):
        status_label = "North East-developed version"
    elif "heritage" in row.get("connection_type", ""):
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
    organisations = read_jsonl(curated_dir / "organisations.jsonl")
    people = read_jsonl(curated_dir / "people.jsonl")
    evidence = read_jsonl(curated_dir / "evidence.jsonl")
    payload = {
        "generated_at": "2026-06-18",
        "qualification": "Only verified or strongly supported connections appear in confirmed results. Keyword-only records stay in candidates.",
        "confirmed": sorted(confirmed, key=lambda row: (row["name"], row["connection_type"])),
        "probable": sorted(probable, key=lambda row: (row["name"], row["connection_type"])),
        "candidates": sorted(candidates, key=lambda row: (row["name"], row["connection_type"])),
    }
    write_json(out_dir / "north-east-collection.json", payload)
    write_json(out_dir / "source-items-index.json", {"items": source_items})
    write_json(out_dir / "games-index.json", {"games": games})
    write_json(out_dir / "people-index.json", {"people": people})
    write_json(out_dir / "organisations-index.json", {"organisations": organisations})
    write_json(out_dir / "evidence-index.json", {"evidence": evidence})
    write_json(out_dir / "timeline-events.json", {"events": []})
    write_json(out_dir / "search-index.json", {
        "items": [
            {"id": row["source_item_id"], "title": row["title"], "summary": row.get("summary", ""), "url": row.get("archive_url", "")}
            for row in source_items
        ]
    })
    return {"confirmed": len(confirmed), "probable": len(probable), "candidates": len(candidates)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Export public static JSON for GitHub Pages.")
    parser.parse_args()
    print(export_public_json())


if __name__ == "__main__":
    main()

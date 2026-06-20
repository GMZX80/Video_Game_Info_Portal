from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .common import ROOT, stable_id, write_jsonl

SOURCE_SYSTEM = "world-of-spectrum"


def normalise_software_record(row: dict[str, Any], *, source_url: str = "") -> dict[str, Any]:
    title = str(row.get("Title") or row.get("title") or row.get("Software") or "").strip()
    publisher = str(row.get("Publisher") or row.get("publisher") or "").strip()
    developer = str(row.get("Developer") or row.get("developer") or "").strip()
    year = str(row.get("Year") or row.get("release_year") or row.get("year") or "").strip()
    identifier = str(row.get("ID") or row.get("id") or row.get("zxdb_id") or title).strip()
    return {
        "assertion_id": stable_id("assertion", SOURCE_SYSTEM, identifier, title),
        "source_item_id": stable_id("source-item", SOURCE_SYSTEM, identifier),
        "source_system": SOURCE_SYSTEM,
        "subject_type": "game",
        "subject_label_as_printed": title,
        "predicate": "software_metadata",
        "object_type": "software_record",
        "object_label_as_printed": title,
        "role_as_printed": "",
        "date_as_printed": year,
        "place_as_printed": "",
        "platform_as_printed": "ZX Spectrum",
        "confidence": "structured source metadata",
        "assertion_status": "candidate",
        "public_claim_status": "candidate",
        "evidence_status": "structured secondary database",
        "source_url": source_url,
        "source_page_title": "World of Spectrum software API",
        "revision_id": "",
        "permanent_url": "",
        "license": "",
        "attribution_required": False,
        "publisher_as_printed": publisher,
        "developer_as_printed": developer,
        "notes": "World of Spectrum metadata only; no game files, scans or screenshots downloaded.",
    }


def source_item_for_record(assertion: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_item_id": assertion["source_item_id"],
        "publication_id": "publication:world-of-spectrum",
        "issue_id": "",
        "item_type": "structured software database record",
        "title": assertion["subject_label_as_printed"],
        "archive_url": assertion.get("source_url", ""),
        "summary": "World of Spectrum structured metadata record; no binary or image assets mirrored.",
        "rights_note": "Structured metadata and source locator only.",
        "accessed_at": "2026-06-20",
        "content_hash": stable_id("hash", assertion["assertion_id"]),
        "extraction_status": "parsed",
        "machine": "ZX Spectrum",
        "printed_company": assertion.get("publisher_as_printed", ""),
        "source_status": "candidate",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalise World of Spectrum structured metadata without downloading files.")
    parser.add_argument("json_path", nargs="?", help="Optional JSON array of software records.")
    parser.add_argument("--raw-dir", default=str(ROOT / "data" / "raw" / "world-of-spectrum"))
    args = parser.parse_args()
    rows = json.loads(Path(args.json_path).read_text(encoding="utf-8")) if args.json_path else []
    assertions = [normalise_software_record(row) for row in rows]
    raw_dir = Path(args.raw_dir)
    write_jsonl(raw_dir / "issues.jsonl", [])
    write_jsonl(raw_dir / "source-items.jsonl", [source_item_for_record(row) for row in assertions], sort_key="source_item_id")
    write_jsonl(raw_dir / "source-assertions.jsonl", assertions, sort_key="assertion_id")
    print({"assertions": len(assertions)})


if __name__ == "__main__":
    main()

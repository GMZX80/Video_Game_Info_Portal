from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

from .common import ROOT, stable_id, write_jsonl

SOURCE_SYSTEM = "zxdb"


def normalise_zxdb_record(row: dict[str, Any], *, source_url: str = "https://github.com/zxdb/ZXDB") -> dict[str, Any]:
    identifier = str(row.get("id") or row.get("ID") or row.get("zxdb_id") or row.get("ZXDBID") or "").strip()
    title = str(row.get("title") or row.get("Title") or row.get("name") or identifier).strip()
    publisher = str(row.get("publisher") or row.get("Publisher") or "").strip()
    authors = str(row.get("authors") or row.get("Authors") or row.get("author") or "").strip()
    return {
        "assertion_id": stable_id("assertion", SOURCE_SYSTEM, identifier or title, title),
        "source_item_id": stable_id("source-item", SOURCE_SYSTEM, identifier or title),
        "source_system": SOURCE_SYSTEM,
        "subject_type": "game",
        "subject_label_as_printed": title,
        "predicate": "zxdb_metadata",
        "object_type": "software_record",
        "object_label_as_printed": title,
        "role_as_printed": authors,
        "date_as_printed": str(row.get("year") or row.get("Year") or ""),
        "place_as_printed": "",
        "platform_as_printed": "ZX Spectrum",
        "confidence": "ZXDB structured export metadata",
        "assertion_status": "candidate",
        "public_claim_status": "candidate",
        "evidence_status": "structured secondary database",
        "source_url": source_url,
        "source_page_title": "ZXDB structured export",
        "revision_id": "",
        "permanent_url": "",
        "license": "",
        "attribution_required": False,
        "publisher_as_printed": publisher,
        "notes": "ZXDB structured metadata only.",
    }


def source_item_for_record(assertion: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_item_id": assertion["source_item_id"],
        "publication_id": "publication:zxdb",
        "issue_id": "",
        "item_type": "structured software database record",
        "title": assertion["subject_label_as_printed"],
        "archive_url": assertion.get("source_url", ""),
        "summary": "ZXDB structured metadata record.",
        "rights_note": "Structured metadata and source locator only.",
        "accessed_at": "2026-06-20",
        "content_hash": stable_id("hash", assertion["assertion_id"]),
        "extraction_status": "parsed",
        "machine": "ZX Spectrum",
        "printed_company": assertion.get("publisher_as_printed", ""),
        "source_status": "candidate",
    }


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalise ZXDB structured CSV exports.")
    parser.add_argument("csv_path", nargs="?", help="Optional CSV export containing title metadata.")
    parser.add_argument("--raw-dir", default=str(ROOT / "data" / "raw" / "zxdb"))
    args = parser.parse_args()
    rows = _read_csv(Path(args.csv_path)) if args.csv_path else []
    assertions = [normalise_zxdb_record(row) for row in rows]
    raw_dir = Path(args.raw_dir)
    write_jsonl(raw_dir / "issues.jsonl", [])
    write_jsonl(raw_dir / "source-items.jsonl", [source_item_for_record(row) for row in assertions], sort_key="source_item_id")
    write_jsonl(raw_dir / "source-assertions.jsonl", assertions, sort_key="assertion_id")
    print({"assertions": len(assertions)})


if __name__ == "__main__":
    main()

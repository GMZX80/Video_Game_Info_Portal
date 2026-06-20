from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .common import ROOT, stable_id, write_jsonl

SOURCE_SYSTEM = "zxinfo"


def normalise_zxinfo_record(row: dict[str, Any], *, source_url: str = "") -> dict[str, Any]:
    identifier = str(row.get("id") or row.get("zxdb_id") or row.get("zxinfo_id") or "").strip()
    title = str(row.get("title") or row.get("name") or identifier).strip()
    publisher = str(row.get("publisher") or row.get("publisher_name") or "").strip()
    authors = row.get("authors") or row.get("author") or []
    if isinstance(authors, str):
        authors = [authors]
    return {
        "assertion_id": stable_id("assertion", SOURCE_SYSTEM, identifier or title, title),
        "source_item_id": stable_id("source-item", SOURCE_SYSTEM, identifier or title),
        "source_system": SOURCE_SYSTEM,
        "subject_type": "game",
        "subject_label_as_printed": title,
        "predicate": "zxinfo_metadata",
        "object_type": "software_record",
        "object_label_as_printed": title,
        "role_as_printed": "",
        "date_as_printed": str(row.get("year") or row.get("release_year") or ""),
        "place_as_printed": "",
        "platform_as_printed": "ZX Spectrum",
        "confidence": "ZXInfo API metadata",
        "assertion_status": "candidate",
        "public_claim_status": "candidate",
        "evidence_status": "structured secondary database",
        "source_url": source_url,
        "source_page_title": "ZXInfo API",
        "revision_id": "",
        "permanent_url": "",
        "license": "",
        "attribution_required": False,
        "publisher_as_printed": publisher,
        "authors_as_printed": authors,
        "notes": "ZXInfo API metadata only; binary download links are not mirrored.",
    }


def source_item_for_record(assertion: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_item_id": assertion["source_item_id"],
        "publication_id": "publication:zxinfo",
        "issue_id": "",
        "item_type": "structured software database record",
        "title": assertion["subject_label_as_printed"],
        "archive_url": assertion.get("source_url", ""),
        "summary": "ZXInfo structured metadata record; no binary or image assets mirrored.",
        "rights_note": "Structured metadata and source locator only.",
        "accessed_at": "2026-06-20",
        "content_hash": stable_id("hash", assertion["assertion_id"]),
        "extraction_status": "parsed",
        "machine": "ZX Spectrum",
        "printed_company": assertion.get("publisher_as_printed", ""),
        "source_status": "candidate",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalise ZXInfo structured metadata without downloading binaries.")
    parser.add_argument("json_path", nargs="?", help="Optional JSON array of ZXInfo records.")
    parser.add_argument("--raw-dir", default=str(ROOT / "data" / "raw" / "zxinfo"))
    args = parser.parse_args()
    rows = json.loads(Path(args.json_path).read_text(encoding="utf-8")) if args.json_path else []
    assertions = [normalise_zxinfo_record(row) for row in rows]
    raw_dir = Path(args.raw_dir)
    write_jsonl(raw_dir / "issues.jsonl", [])
    write_jsonl(raw_dir / "source-items.jsonl", [source_item_for_record(row) for row in assertions], sort_key="source_item_id")
    write_jsonl(raw_dir / "source-assertions.jsonl", assertions, sort_key="assertion_id")
    print({"assertions": len(assertions)})


if __name__ == "__main__":
    main()

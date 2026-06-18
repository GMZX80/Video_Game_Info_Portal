import json
import sqlite3
from pathlib import Path

from scripts.ingest.build_sqlite import build_database
from scripts.ingest.classify_north_east import classify_records
from scripts.ingest.export_public_json import export_public_json
from scripts.ingest.validate_data import validate_repository


def write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


def test_classification_requires_explicit_evidence_for_public_connection(tmp_path: Path):
    records = [
        {
            "source_item_id": "source-item:crash:001:sunderland-football",
            "title": "Sunderland match day",
            "summary": "A football reference, not development evidence.",
            "archive_url": "https://example.test/football",
        },
        {
            "source_item_id": "source-item:sinclair-user:098:tynesoft-profile",
            "title": "Tynesoft profile",
            "summary": "Tynesoft is described as a software house based in Blaydon.",
            "archive_url": "https://example.test/tynesoft",
        },
    ]

    connections = classify_records(records, seeds={"organisations": ["Tynesoft"], "places": ["Sunderland", "Blaydon"]})

    statuses = {connection["source_item_id"]: connection["status"] for connection in connections}
    assert statuses["source-item:crash:001:sunderland-football"] == "candidate"
    assert statuses["source-item:sinclair-user:098:tynesoft-profile"] == "strongly supported"


def test_build_sqlite_creates_fts_and_foreign_keys(tmp_path: Path):
    curated = tmp_path / "data" / "curated"
    db_path = tmp_path / "build" / "video-game-history.sqlite"
    write_jsonl(curated / "publications.jsonl", [{"publication_id": "publication:crash", "canonical_title": "CRASH", "aliases": []}])
    write_jsonl(curated / "issues.jsonl", [{"issue_id": "issue:crash:001", "publication_id": "publication:crash", "issue_number": "001", "cover_date": "February 1984", "date_precision": "month"}])
    write_jsonl(curated / "source-items.jsonl", [{"source_item_id": "source-item:crash:001:3d-deathchase", "publication_id": "publication:crash", "issue_id": "issue:crash:001", "item_type": "review", "title": "3D Deathchase", "archive_url": "https://example.test/deathchase", "summary": "Review metadata only.", "rights_note": "Link and paraphrase only.", "accessed_at": "2026-06-18", "content_hash": "abc"}])

    build_database(curated, db_path)

    con = sqlite3.connect(db_path)
    try:
        assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert con.execute("SELECT title FROM source_items_fts WHERE source_items_fts MATCH 'Deathchase'").fetchone()[0] == "3D Deathchase"
    finally:
        con.close()


def test_public_export_excludes_candidates_and_private_data(tmp_path: Path):
    curated = tmp_path / "data" / "curated"
    out_dir = tmp_path / "assets" / "data" / "generated"
    write_jsonl(curated / "evidence.jsonl", [{"evidence_id": "evidence:1", "source_item_id": "source-item:1", "source_locator": "Issue 1", "evidence_type": "contemporary magazine"}])
    write_jsonl(curated / "north-east-connections.jsonl", [
        {"connection_id": "connection:verified", "entity_type": "organisation", "entity_id": "organisation:tynesoft", "entity_name": "Tynesoft", "connection_type": "organisation based in North East", "place_id": "place:blaydon", "place_name": "Blaydon", "evidence_ids": ["evidence:1"], "status": "strongly supported", "confidence": "high", "explanatory_text": "Based in Blaydon.", "public_visibility": "public", "source_magazine": "Sinclair User", "issue_label": "Issue 98", "source_url": "https://example.test/tynesoft", "approved_by": None, "approved_at": None},
        {"connection_id": "connection:candidate", "entity_type": "game", "entity_id": "game:sunderland", "entity_name": "Sunderland", "connection_type": "reported connection requiring verification", "place_id": "place:sunderland", "place_name": "Sunderland", "evidence_ids": ["evidence:1"], "status": "candidate", "confidence": "low", "explanatory_text": "Keyword only.", "public_visibility": "candidate", "source_magazine": "CRASH", "issue_label": "Issue 1", "source_url": "https://example.test/candidate", "approved_by": None, "approved_at": None},
    ])

    export_public_json(curated, out_dir)
    payload = json.loads((out_dir / "north-east-collection.json").read_text(encoding="utf-8"))

    assert [item["name"] for item in payload["confirmed"]] == ["Tynesoft"]
    assert [item["name"] for item in payload["candidates"]] == ["Sunderland"]
    assert "drive.google.com" not in json.dumps(payload)


def test_validate_repository_enforces_public_connection_evidence(tmp_path: Path):
    curated = tmp_path / "data" / "curated"
    schemas = tmp_path / "data" / "schemas"
    schemas.mkdir(parents=True)
    write_jsonl(curated / "evidence.jsonl", [])
    write_jsonl(curated / "north-east-connections.jsonl", [
        {"connection_id": "connection:bad", "entity_type": "organisation", "entity_id": "organisation:bad", "entity_name": "Bad", "connection_type": "organisation based in North East", "place_id": "place:blaydon", "place_name": "Blaydon", "evidence_ids": [], "status": "verified", "confidence": "high", "explanatory_text": "Missing evidence.", "public_visibility": "public", "source_magazine": "Sinclair User", "issue_label": "Issue 1", "source_url": "https://example.test", "approved_by": None, "approved_at": None}
    ])

    failures = validate_repository(tmp_path)

    assert any("public North East connection lacks evidence" in failure for failure in failures)

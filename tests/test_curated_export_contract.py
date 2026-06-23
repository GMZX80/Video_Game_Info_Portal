import csv
import json
from pathlib import Path

import pytest

from scripts.ingest.curated_export_contract import (
    CuratedExportContractError,
    build_portal_curated_payload,
    load_curated_export_contract,
)


CONTRACT_COLUMNS = {
    "game_works": [
        "game_work_id",
        "canonical_title",
        "first_known_release_year",
        "overall_confidence",
        "evidence_id",
        "provisional_label",
    ],
    "platform_releases": [
        "platform_release_id",
        "game_work_id",
        "platform",
        "release_year",
        "evidence_confidence",
        "evidence_id",
        "provisional_label",
    ],
    "organisations": [
        "organisation_id",
        "organisation_name",
        "organisation_type",
        "location",
        "confidence",
        "evidence_id",
        "provisional_label",
    ],
    "people": [
        "person_id",
        "normalised_person_name",
        "primary_roles",
        "confidence",
        "evidence_id",
        "provisional_label",
    ],
    "platform_credits": [
        "credit_id",
        "platform_release_id",
        "game_work_id",
        "person_id",
        "person_name",
        "role",
        "platform",
        "evidence_id",
        "confidence",
        "provisional_label",
    ],
    "source_evidence": [
        "source_evidence_id",
        "source_id",
        "source_name",
        "source_url",
        "confidence",
        "claim_type",
    ],
    "dashboard_summary": ["metric", "value"],
}


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_curated_export(export_dir: Path) -> None:
    rows_by_export = {
        "game_works": [
            {
                "game_work_id": "gw:example",
                "canonical_title": "Example Game",
                "first_known_release_year": "1984",
                "overall_confidence": "medium",
                "evidence_id": "",
                "provisional_label": "reviewed_without_direct_evidence_id",
            }
        ],
        "platform_releases": [],
        "organisations": [],
        "people": [],
        "platform_credits": [],
        "source_evidence": [],
        "dashboard_summary": [{"metric": "game_works_rows", "value": "1"}],
    }
    for export_name, columns in CONTRACT_COLUMNS.items():
        write_csv(export_dir / f"{export_name}.csv", columns, rows_by_export[export_name])
        (export_dir / f"{export_name}.json").write_text(
            json.dumps(rows_by_export[export_name], indent=2) + "\n",
            encoding="utf-8",
        )
    manifest = {
        "schema_version": "curated-export-v1",
        "source_db_sha256": "abc123",
        "build_time_utc": "2026-06-23T12:00:00Z",
        "counts": {name: len(rows) for name, rows in rows_by_export.items()},
        "files": {
            name: {
                "csv": str(export_dir / f"{name}.csv"),
                "json": str(export_dir / f"{name}.json"),
                "columns": columns,
            }
            for name, columns in CONTRACT_COLUMNS.items()
        },
    }
    (export_dir / "public_export_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )


def test_loader_accepts_curated_contract_and_preserves_provisional_labels(tmp_path) -> None:
    export_dir = tmp_path / "curated"
    write_curated_export(export_dir)

    payload = load_curated_export_contract(export_dir)

    assert payload["schema_version"] == "curated-export-v1"
    assert payload["game_works"][0]["provisional_label"] == "reviewed_without_direct_evidence_id"
    assert payload["game_works"][0]["evidence_id"] == ""


def test_loader_rejects_missing_manifest(tmp_path) -> None:
    with pytest.raises(CuratedExportContractError, match="public_export_manifest.json"):
        load_curated_export_contract(tmp_path)


def test_loader_rejects_raw_snapshot_directories(tmp_path) -> None:
    raw_snapshot = tmp_path / "raw" / "google_sheets" / "2026-06-23T120000Z"
    raw_snapshot.mkdir(parents=True)
    (raw_snapshot / "snapshot_report.json").write_text("{}", encoding="utf-8")

    with pytest.raises(CuratedExportContractError, match="raw snapshot"):
        load_curated_export_contract(raw_snapshot)


def test_loader_rejects_candidate_queue_files(tmp_path) -> None:
    export_dir = tmp_path / "curated"
    write_curated_export(export_dir)
    (export_dir / "source_assertions_candidates.csv").write_text("id\ncandidate:1\n", encoding="utf-8")

    with pytest.raises(CuratedExportContractError, match="candidate"):
        load_curated_export_contract(export_dir)


def test_loader_rejects_wrong_schema_version(tmp_path) -> None:
    export_dir = tmp_path / "curated"
    write_curated_export(export_dir)
    manifest_path = export_dir / "public_export_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["schema_version"] = "older-version"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(CuratedExportContractError, match="curated-export-v1"):
        load_curated_export_contract(export_dir)


def test_loader_rejects_public_claim_without_evidence_or_provisional_label(tmp_path) -> None:
    export_dir = tmp_path / "curated"
    write_curated_export(export_dir)
    write_csv(
        export_dir / "game_works.csv",
        CONTRACT_COLUMNS["game_works"],
        [
            {
                "game_work_id": "gw:bad",
                "canonical_title": "Bad",
                "first_known_release_year": "",
                "overall_confidence": "",
                "evidence_id": "",
                "provisional_label": "",
            }
        ],
    )

    with pytest.raises(CuratedExportContractError, match="evidence_id"):
        load_curated_export_contract(export_dir)


def test_build_portal_curated_payload_writes_generated_json(tmp_path) -> None:
    export_dir = tmp_path / "curated"
    output_path = tmp_path / "assets" / "data" / "generated" / "curated-export-contract.json"
    write_curated_export(export_dir)

    payload = build_portal_curated_payload(export_dir=export_dir, output_path=output_path)

    assert payload["schema_version"] == "curated-export-v1"
    assert json.loads(output_path.read_text(encoding="utf-8")) == payload

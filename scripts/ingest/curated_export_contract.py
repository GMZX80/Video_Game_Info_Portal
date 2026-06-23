from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from scripts.ingest.common import GENERATED_DIR, write_json

SCHEMA_VERSION = "curated-export-v1"

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

CLAIM_EXPORTS = {
    "game_works",
    "platform_releases",
    "organisations",
    "people",
    "platform_credits",
}


class CuratedExportContractError(ValueError):
    """Raised when a curated export artifact is unsafe for portal consumption."""


def load_curated_export_contract(export_dir: str | Path) -> dict[str, Any]:
    root = Path(export_dir)
    _reject_raw_snapshot(root)
    _reject_candidate_queue_files(root)

    manifest_path = root / "public_export_manifest.json"
    if not manifest_path.exists():
        raise CuratedExportContractError(f"Missing required public_export_manifest.json in {root}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    schema_version = manifest.get("schema_version")
    if schema_version != SCHEMA_VERSION:
        raise CuratedExportContractError(
            f"Expected schema_version {SCHEMA_VERSION!r}, got {schema_version!r}"
        )

    exports: dict[str, list[dict[str, str]]] = {}
    for export_name, expected_columns in CONTRACT_COLUMNS.items():
        csv_path = root / f"{export_name}.csv"
        rows = _read_contract_csv(csv_path, expected_columns)
        if export_name in CLAIM_EXPORTS:
            _validate_claim_rows(export_name, rows)
        exports[export_name] = rows

    return {
        "schema_version": SCHEMA_VERSION,
        "source_db_sha256": str(manifest.get("source_db_sha256", "")),
        "build_time_utc": str(manifest.get("build_time_utc", "")),
        "counts": manifest.get("counts", {}),
        **exports,
    }


def build_portal_curated_payload(
    *,
    export_dir: str | Path,
    output_path: str | Path = GENERATED_DIR / "curated-export-contract.json",
) -> dict[str, Any]:
    payload = load_curated_export_contract(export_dir)
    write_json(Path(output_path), payload)
    return payload


def _read_contract_csv(path: Path, expected_columns: list[str]) -> list[dict[str, str]]:
    if not path.exists():
        raise CuratedExportContractError(f"Missing required export file: {path.name}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        actual_columns = list(reader.fieldnames or [])
        if actual_columns != expected_columns:
            raise CuratedExportContractError(
                f"{path.name} columns do not match {SCHEMA_VERSION}: {actual_columns}"
            )
        return [{key: str(value or "") for key, value in row.items()} for row in reader]


def _validate_claim_rows(export_name: str, rows: list[dict[str, str]]) -> None:
    for row_number, row in enumerate(rows, 2):
        if row.get("evidence_id") or row.get("provisional_label"):
            continue
        raise CuratedExportContractError(
            f"{export_name}.csv row {row_number} lacks evidence_id or provisional_label"
        )


def _reject_raw_snapshot(root: Path) -> None:
    if (root / "snapshot_report.json").exists():
        raise CuratedExportContractError(
            "Refusing raw snapshot directory; portal requires curated exports."
        )


def _reject_candidate_queue_files(root: Path) -> None:
    if not root.exists():
        return
    for path in root.iterdir():
        name = path.name.lower()
        if "candidate" in name or "staging" in name:
            raise CuratedExportContractError(
                f"Refusing candidate/staging file in curated export artifact: {path.name}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Load database curated exports for portal use.")
    parser.add_argument("--export-dir", required=True, help="Directory containing curated-export-v1 files.")
    parser.add_argument(
        "--output",
        default=str(GENERATED_DIR / "curated-export-contract.json"),
        help="Generated portal JSON output path.",
    )
    args = parser.parse_args()
    payload = build_portal_curated_payload(export_dir=args.export_dir, output_path=args.output)
    print(json.dumps({"schema_version": payload["schema_version"], "counts": payload["counts"]}, indent=2))


if __name__ == "__main__":
    main()

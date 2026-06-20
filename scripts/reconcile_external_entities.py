from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from typing import Any

from scripts.ingest.common import CURATED_DIR, REPORTS_DIR, read_jsonl

QUEUE_FIELDS = [
    "queue_id",
    "entity_type",
    "current_internal_entity",
    "current_internal_label",
    "external_record",
    "external_label",
    "source_system",
    "match_score",
    "reason",
    "conflict_notes",
    "suggested_action",
    "decision",
]

MANUAL_CREDIT_SOURCE_SYSTEMS = {"mobygames-manual-credit"}


def normalise_label(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _entity_index(rows: list[dict[str, Any]], id_field: str, label_field: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = normalise_label(str(row.get(label_field, "")))
        if key and key not in result:
            result[key] = row
    return result


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=QUEUE_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _candidate_label(assertion: dict[str, Any], entity_type: str) -> str:
    subject_type = assertion.get("subject_type")
    object_type = assertion.get("object_type")
    if subject_type == entity_type:
        return str(assertion.get("subject_label_as_printed", "")).strip()
    if object_type == entity_type:
        return str(assertion.get("object_label_as_printed", "")).strip()
    if entity_type == "game" and assertion.get("predicate") == "title_seed":
        return str(assertion.get("object_label_as_printed") or assertion.get("subject_label_as_printed", "")).strip()
    return ""


def _queue_rows(
    *,
    entity_type: str,
    assertions: list[dict[str, Any]],
    index: dict[str, dict[str, Any]],
    id_field: str,
    label_field: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen_labels: dict[str, int] = {}
    for assertion in assertions:
        label = _candidate_label(assertion, entity_type)
        key = normalise_label(label)
        if not key:
            continue
        seen_labels[key] = seen_labels.get(key, 0) + 1
        match = index.get(key)
        match_score = "0.95" if match else "0.00"
        rows.append({
            "queue_id": f"{entity_type}-{len(rows) + 1:04d}",
            "entity_type": entity_type,
            "current_internal_entity": match.get(id_field, "") if match else "",
            "current_internal_label": match.get(label_field, "") if match else "",
            "external_record": assertion.get("assertion_id", ""),
            "external_label": label,
            "source_system": assertion.get("source_system", ""),
            "match_score": match_score,
            "reason": "normalised exact label match" if match else "no canonical exact match",
            "conflict_notes": "",
            "suggested_action": "review-existing-match" if match else "review-new-candidate",
            "decision": "unresolved",
        })
    for row in rows:
        key = normalise_label(row["external_label"])
        if seen_labels.get(key, 0) > 1:
            row["conflict_notes"] = "duplicate external label; queue each row and do not merge automatically"
    return rows


def reconcile_external_entities(curated_dir: Path = CURATED_DIR, reports_dir: Path = REPORTS_DIR) -> dict[str, int]:
    assertions = [
        row
        for row in read_jsonl(curated_dir / "source-assertions.jsonl")
        if row.get("source_system") not in MANUAL_CREDIT_SOURCE_SYSTEMS
    ]
    games = _entity_index(read_jsonl(curated_dir / "games.jsonl"), "game_id", "canonical_title")
    people = _entity_index(read_jsonl(curated_dir / "people.jsonl"), "person_id", "canonical_name")
    organisations = _entity_index(read_jsonl(curated_dir / "organisations.jsonl"), "organisation_id", "canonical_name")

    game_rows = _queue_rows(entity_type="game", assertions=assertions, index=games, id_field="game_id", label_field="canonical_title")
    person_rows = _queue_rows(entity_type="person", assertions=assertions, index=people, id_field="person_id", label_field="canonical_name")
    organisation_rows = _queue_rows(entity_type="organisation", assertions=assertions, index=organisations, id_field="organisation_id", label_field="canonical_name")

    _write_csv(reports_dir / "reconciliation-queue-games.csv", game_rows)
    _write_csv(reports_dir / "reconciliation-queue-people.csv", person_rows)
    _write_csv(reports_dir / "reconciliation-queue-organisations.csv", organisation_rows)
    _write_csv(reports_dir / "reconciliation-ambiguous-people.csv", [row for row in person_rows if row["conflict_notes"]])
    _write_csv(reports_dir / "reconciliation-rejected.csv", [])

    return {
        "game_candidates": len(game_rows),
        "person_candidates": len(person_rows),
        "organisation_candidates": len(organisation_rows),
        "ambiguous_people": len([row for row in person_rows if row["conflict_notes"]]),
        "rejected": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Create external entity reconciliation queues without auto-merging.")
    parser.add_argument("--curated-dir", default=str(CURATED_DIR))
    parser.add_argument("--reports-dir", default=str(REPORTS_DIR))
    args = parser.parse_args()
    print(reconcile_external_entities(Path(args.curated_dir), Path(args.reports_dir)))


if __name__ == "__main__":
    main()

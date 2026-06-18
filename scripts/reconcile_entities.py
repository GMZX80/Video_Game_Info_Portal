from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import yaml

from scripts.ingest.common import CURATED_DIR, REPORTS_DIR, ROOT, read_jsonl

QUEUE = ROOT / "research" / "entity-resolution-queue.csv"
SEEDS = ROOT / "config" / "north-east-seeds.yml"


def normalise_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def reconcile(curated_dir: Path = CURATED_DIR, queue_path: Path = QUEUE) -> dict[str, int]:
    people = read_jsonl(curated_dir / "people.jsonl")
    organisations = read_jsonl(curated_dir / "organisations.jsonl")
    games = read_jsonl(curated_dir / "games.jsonl")
    candidates = []
    for kind, rows, name_field, id_field in [
        ("person", people, "canonical_name", "person_id"),
        ("organisation", organisations, "canonical_name", "organisation_id"),
        ("game", games, "canonical_title", "game_id"),
    ]:
        by_key: dict[str, list[dict[str, str]]] = {}
        for row in rows:
            key = normalise_name(row.get(name_field, ""))
            if key:
                by_key.setdefault(key, []).append(row)
        for key, group in by_key.items():
            if len(group) < 2:
                continue
            for left_index, left in enumerate(group):
                for right in group[left_index + 1:]:
                    candidates.append({
                        "queue_id": f"{kind}-{len(candidates)+1:04d}",
                        "entity_type": kind,
                        "left_id": left[id_field],
                        "left_name": left[name_field],
                        "right_id": right[id_field],
                        "right_name": right[name_field],
                        "match_reason": "normalised exact match",
                        "decision": "unresolved",
                        "decided_by": "",
                        "decided_at": "",
                        "notes": "Do not auto-merge people, legal organisations, labels, or similarly titled games.",
                    })
    if SEEDS.exists():
        seed_data = yaml.safe_load(SEEDS.read_text(encoding="utf-8")) or {}
        for group_name, names in (seed_data.get("ambiguous_names", {}) or {}).items():
            if not isinstance(names, list):
                continue
            for index, name in enumerate(names):
                for other in names[index + 1:]:
                    candidates.append({
                        "queue_id": f"ambiguous-{len(candidates)+1:04d}",
                        "entity_type": "person",
                        "left_id": f"person:{normalise_name(name)}",
                        "left_name": name,
                        "right_id": f"person:{normalise_name(other)}",
                        "right_name": other,
                        "match_reason": f"configured ambiguous name group {group_name}",
                        "decision": "unresolved",
                        "decided_by": "",
                        "decided_at": "",
                        "notes": "Configured ambiguous spelling/identity group; keep separate until documentary evidence resolves it.",
                    })
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["queue_id", "entity_type", "left_id", "left_name", "right_id", "right_name", "match_reason", "decision", "decided_by", "decided_at", "notes"]
    with queue_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(candidates)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with (REPORTS_DIR / "entity-collisions.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(candidates)
    return {"collisions": len(candidates)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Flag near-match entities without auto-merging them.")
    parser.parse_args()
    print(reconcile())


if __name__ == "__main__":
    main()

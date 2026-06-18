from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .common import CURATED_DIR, ROOT, SCHEMA_DIR, read_jsonl


SCHEMA_MAP = {
    "publications.jsonl": "publication.schema.json",
    "issues.jsonl": "issue.schema.json",
    "source-items.jsonl": "source-item.schema.json",
    "people.jsonl": "person.schema.json",
    "organisations.jsonl": "organisation.schema.json",
    "games.jsonl": "game.schema.json",
    "releases.jsonl": "release.schema.json",
    "credits.jsonl": "credit.schema.json",
    "claims.jsonl": "claim.schema.json",
    "evidence.jsonl": "evidence.schema.json",
    "north-east-connections.jsonl": "north-east-connection.schema.json",
}
PRIMARY_IDS = {
    "publications.jsonl": "publication_id",
    "issues.jsonl": "issue_id",
    "source-items.jsonl": "source_item_id",
    "people.jsonl": "person_id",
    "organisations.jsonl": "organisation_id",
    "games.jsonl": "game_id",
    "releases.jsonl": "release_id",
    "credits.jsonl": "credit_id",
    "claims.jsonl": "claim_id",
    "evidence.jsonl": "evidence_id",
    "north-east-connections.jsonl": "connection_id",
}


def _schema(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def validate_repository(root: Path = ROOT) -> list[str]:
    failures: list[str] = []
    curated = root / "data" / "curated"
    schemas = root / "data" / "schemas"
    all_ids: set[str] = set()
    rows_by_file: dict[str, list[dict[str, Any]]] = {}
    for file_name, schema_name in SCHEMA_MAP.items():
        rows = read_jsonl(curated / file_name)
        rows_by_file[file_name] = rows
        schema = _schema(schemas / schema_name)
        if schema:
            validator = Draft202012Validator(schema)
            for index, row in enumerate(rows, 1):
                for error in validator.iter_errors(row):
                    failures.append(f"{file_name}:{index}: schema: {error.message}")
        primary_key = PRIMARY_IDS[file_name]
        seen_in_file: set[str] = set()
        for row in rows:
            value = row.get(primary_key)
            if not isinstance(value, str) or not value:
                continue
            if value in seen_in_file:
                failures.append(f"duplicate id in {file_name}: {value}")
            seen_in_file.add(value)
            if value in all_ids:
                failures.append(f"duplicate primary id across files: {value}")
            all_ids.add(value)
    publications = {row["publication_id"] for row in rows_by_file.get("publications.jsonl", [])}
    issues = {row["issue_id"] for row in rows_by_file.get("issues.jsonl", [])}
    source_items = {row["source_item_id"] for row in rows_by_file.get("source-items.jsonl", [])}
    games = {row["game_id"] for row in rows_by_file.get("games.jsonl", [])}
    platforms = {row["platform_id"] for row in read_jsonl(curated / "platforms.jsonl")}
    evidence = {row["evidence_id"] for row in rows_by_file.get("evidence.jsonl", [])}
    for row in rows_by_file.get("issues.jsonl", []):
        if row["publication_id"] not in publications:
            failures.append(f"issue references missing publication: {row['issue_id']}")
    for row in rows_by_file.get("source-items.jsonl", []):
        if row["publication_id"] not in publications:
            failures.append(f"source item references missing publication: {row['source_item_id']}")
        if row.get("issue_id") and row["issue_id"] not in issues:
            failures.append(f"source item references missing issue: {row['source_item_id']}")
    for row in rows_by_file.get("releases.jsonl", []):
        if row["game_id"] not in games:
            failures.append(f"release references missing game: {row['release_id']}")
        if row["platform_id"] not in platforms:
            failures.append(f"release references missing platform: {row['release_id']}")
    for row in rows_by_file.get("credits.jsonl", []):
        if not row.get("source_id"):
            failures.append(f"credit lacks source: {row.get('credit_id')}")
    for row in rows_by_file.get("north-east-connections.jsonl", []):
        public = row.get("status") in {"verified", "strongly supported"} or row.get("public_visibility") == "public"
        if public and not row.get("evidence_ids"):
            failures.append(f"public North East connection lacks evidence: {row.get('connection_id')}")
        for evidence_id in row.get("evidence_ids", []):
            if evidence_id not in evidence:
                failures.append(f"North East connection references missing evidence: {row.get('connection_id')} -> {evidence_id}")
        if row.get("status") == "candidate" and row.get("public_visibility") == "public":
            failures.append(f"candidate exported as public: {row.get('connection_id')}")
    public_text = ""
    generated_dir = root / "assets" / "data" / "generated"
    for file in generated_dir.glob("*.json"):
        public_text += file.read_text(encoding="utf-8")
    if re.search(r"drive\.google\.com|docs\.google\.com|private email|phone number|full article text", public_text, re.I):
        failures.append("private or copyrighted-sensitive text leaked into public JSON")
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate canonical datastore JSONL and public invariants.")
    parser.parse_args()
    failures = validate_repository()
    if failures:
        print("Data validation failed:")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)
    print("Data validation passed.")


if __name__ == "__main__":
    main()

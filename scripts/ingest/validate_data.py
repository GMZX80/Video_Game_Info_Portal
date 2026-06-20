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
    "mentions.jsonl": "mention.schema.json",
    "relationships.jsonl": "relationship.schema.json",
    "media-assets.jsonl": "media-asset.schema.json",
    "photo-identifications.jsonl": "photo-identification.schema.json",
    "source-assertions.jsonl": "source-assertion.schema.json",
    "external-identifiers.jsonl": "external-identifier.schema.json",
    "entity-match-decisions.jsonl": "entity-match-decision.schema.json",
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
    "mentions.jsonl": "mention_id",
    "relationships.jsonl": "relationship_id",
    "media-assets.jsonl": "media_id",
    "photo-identifications.jsonl": "photo_identification_id",
    "source-assertions.jsonl": "assertion_id",
    "external-identifiers.jsonl": "external_id_record",
    "entity-match-decisions.jsonl": "decision_id",
}
PAGE_INVENTORY_SCHEMA = "page-inventory.schema.json"


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
    releases = {row["release_id"] for row in rows_by_file.get("releases.jsonl", [])}
    people = {row["person_id"] for row in rows_by_file.get("people.jsonl", [])}
    organisations = {row["organisation_id"] for row in rows_by_file.get("organisations.jsonl", [])}
    platforms = {row["platform_id"] for row in read_jsonl(curated / "platforms.jsonl")}
    evidence = {row["evidence_id"] for row in rows_by_file.get("evidence.jsonl", [])}
    media_assets = {row["media_id"] for row in rows_by_file.get("media-assets.jsonl", [])}
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
        credit_id = row.get("credit_id")
        if not row.get("source_id"):
            failures.append(f"credit lacks source: {row.get('credit_id')}")
        elif row["source_id"] not in source_items:
            failures.append(f"credit references missing source: {credit_id}")
        if row.get("person_id") and row["person_id"] not in people:
            failures.append(f"credit references missing person: {credit_id}")
        if row.get("organisation_id") and row["organisation_id"] not in organisations:
            failures.append(f"credit references missing organisation: {credit_id}")
        if row.get("game_id") and row["game_id"] not in games:
            failures.append(f"credit references missing game: {credit_id}")
        if row.get("release_id") and row["release_id"] not in releases:
            failures.append(f"credit references missing release: {credit_id}")
        if not row.get("game_id") and not row.get("release_id"):
            failures.append(f"credit lacks game or release reference: {credit_id}")
    for row in rows_by_file.get("evidence.jsonl", []):
        if row.get("source_item_id") not in source_items:
            failures.append(f"evidence references missing source: {row.get('evidence_id')}")
    for row in rows_by_file.get("claims.jsonl", []):
        for source_id in row.get("source_ids", []):
            if source_id not in source_items:
                failures.append(f"claim references missing source: {row.get('claim_id')} -> {source_id}")
    for row in rows_by_file.get("mentions.jsonl", []):
        mention_id = row.get("mention_id")
        if row.get("source_item_id") not in source_items:
            failures.append(f"mention references missing source: {mention_id}")
        if row.get("entity_type") == "person" and row.get("entity_id") not in people:
            failures.append(f"mention references missing person: {mention_id}")
        if row.get("entity_type") == "organisation" and row.get("entity_id") not in organisations:
            failures.append(f"mention references missing organisation: {mention_id}")
        if row.get("entity_type") == "game" and row.get("entity_id") not in games:
            failures.append(f"mention references missing game: {mention_id}")
    for row in rows_by_file.get("media-assets.jsonl", []):
        media_id = row.get("media_id")
        if row.get("source_item_id") and row["source_item_id"] not in source_items:
            failures.append(f"media asset references missing source: {media_id}")
    for row in rows_by_file.get("photo-identifications.jsonl", []):
        photo_identification_id = row.get("photo_identification_id")
        if row.get("media_id") not in media_assets:
            failures.append(f"photo identification references missing media: {photo_identification_id}")
        if row.get("source_item_id") not in source_items:
            failures.append(f"photo identification references missing source: {photo_identification_id}")
        if row.get("evidence_status") == "first-person retrospective testimony" and row.get("verification_status") == "verified":
            failures.append(f"photograph testimony exported as verified: {photo_identification_id}")
        if row.get("public_visibility") == "public" and row.get("verification_status") != "verified":
            failures.append(f"unverified photo identification exported publicly: {photo_identification_id}")
    for row in rows_by_file.get("source-assertions.jsonl", []):
        assertion_id = row.get("assertion_id")
        if row.get("source_item_id") not in source_items:
            failures.append(f"source assertion references missing source: {assertion_id}")
        if row.get("source_system") == "wikipedia":
            if row.get("license") != "CC BY-SA" or row.get("attribution_required") is not True:
                failures.append(f"Wikipedia assertion lacks CC BY-SA attribution metadata: {assertion_id}")
            if row.get("public_claim_status") == "confirmed" or row.get("assertion_status") == "confirmed":
                failures.append(f"Wikipedia assertion exported as confirmed fact: {assertion_id}")
    for row in rows_by_file.get("external-identifiers.jsonl", []):
        external_id_record = row.get("external_id_record")
        for source_id in row.get("source_item_ids", []):
            if source_id not in source_items:
                failures.append(f"external identifier references missing source: {external_id_record} -> {source_id}")
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
    page_schema = _schema(schemas / PAGE_INVENTORY_SCHEMA)
    if page_schema:
        validator = Draft202012Validator(page_schema)
        for path in [
            root / "data" / "raw" / "source-page-inventory.jsonl",
            *(root / "data" / "raw").glob("*/page-inventory.jsonl"),
        ]:
            for index, row in enumerate(read_jsonl(path), 1):
                for error in validator.iter_errors(row):
                    failures.append(f"{path.relative_to(root)}:{index}: schema: {error.message}")
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

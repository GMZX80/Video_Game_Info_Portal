from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .common import ROOT, stable_id, write_jsonl

COVERAGE_WARNING = "Known local coverage incomplete - MobyGames person-credit import/API reconciliation pending."
ACCEPTABLE_MANUAL_REVIEW_STATUSES = {"approved", "accepted", "reviewed", "reviewed-candidate"}

MANUAL_MOBYGAMES_FIELDS = [
    "mobygames_person_id",
    "person_name",
    "game_title",
    "mobygames_game_id",
    "platform",
    "role_as_printed",
    "source_url",
    "source_date",
    "imported_by",
    "review_status",
    "notes",
]


def _normalise(value: Any) -> str:
    return str(value or "").strip().casefold()


def _is_private_source(source_id: str, source: dict[str, Any] | None = None) -> bool:
    haystack = " ".join([
        source_id,
        str((source or {}).get("access", "")),
        str((source or {}).get("rights", "")),
        str((source or {}).get("notes", "")),
    ]).casefold()
    return "private" in haystack or "do not quote" in haystack or "do not republish" in haystack


def _source_map(sources_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row.get("id", ""): row for row in sources_data.get("sources", []) if row.get("id")}


def _public_source_trail(source_ids: list[str], sources_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    trail = []
    for source_id in source_ids:
        source = sources_by_id.get(source_id)
        if _is_private_source(source_id, source):
            continue
        if not source:
            trail.append({"source_id": source_id, "title": source_id, "url": "", "type": ""})
            continue
        trail.append({
            "source_id": source_id,
            "title": source.get("title", source_id),
            "url": source.get("url") or "",
            "type": source.get("type", ""),
            "rights": source.get("rights", ""),
        })
    return trail


def _role_normalised(role: str) -> str:
    text = _normalise(role)
    if "program" in text or "author" in text:
        return "programmer"
    if "graphic" in text or "artist" in text or "art" in text:
        return "graphics"
    if "music" in text or "sound" in text:
        return "music"
    if "review" in text:
        return "reviewer"
    if "publish" in text:
        return "publisher"
    if "develop" in text:
        return "developer"
    return text.replace(" ", "-") or "contributor"


def _local_credit_from_game(person: dict[str, Any], game: dict[str, Any]) -> dict[str, Any]:
    title = str(game.get("title", "")).strip()
    role = str(game.get("role", "")).strip()
    return {
        "credit_id": stable_id("credit", "research-person", person.get("id", ""), title, role),
        "person_id": person.get("id", ""),
        "person_name": person.get("full_name", ""),
        "game_id": stable_id("game", title),
        "game_title": title,
        "release_id": "",
        "platforms": game.get("platforms", []) or [],
        "organisation_id": "",
        "role_normalised": _role_normalised(role),
        "role_as_printed": role,
        "source_item_id": "",
        "source_ids": game.get("sources", []) or [],
        "source_system": "local-research",
        "confidence": game.get("confidence", ""),
        "evidence_status": game.get("confidence", "candidate"),
        "employment_status": "not inferred from credit",
        "notes": "Local research credit row. A credit does not establish employment.",
    }


def _candidate_assertions_for_person(person: dict[str, Any], source_assertions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    labels = {_normalise(person.get("full_name", "")), *[_normalise(alias) for alias in person.get("aliases", []) or []]}
    labels.discard("")
    def matches_printed_name(value: Any) -> bool:
        text = _normalise(value)
        if text in labels:
            return True
        parts = {_normalise(part) for part in str(value or "").replace("/", ",").replace("&", ",").split(",")}
        return bool(labels & parts)

    rows = []
    for assertion in source_assertions:
        if not matches_printed_name(assertion.get("object_label_as_printed", "")) and not matches_printed_name(assertion.get("subject_label_as_printed", "")):
            continue
        rows.append({
            "assertion_id": assertion.get("assertion_id", ""),
            "game_title": assertion.get("subject_label_as_printed", ""),
            "person_name": assertion.get("object_label_as_printed", ""),
            "predicate": assertion.get("predicate", ""),
            "role_as_printed": assertion.get("role_as_printed", "") or assertion.get("predicate", ""),
            "platform": assertion.get("platform_as_printed", ""),
            "source_system": assertion.get("source_system", ""),
            "source_url": assertion.get("permanent_url") or assertion.get("source_url", ""),
            "evidence_status": assertion.get("evidence_status", ""),
            "public_claim_status": assertion.get("public_claim_status", assertion.get("assertion_status", "")),
            "notes": assertion.get("notes", ""),
        })
    return rows


def build_people_public_records(
    people_data: dict[str, Any],
    sources_data: dict[str, Any],
    curated_credits: list[dict[str, Any]],
    source_assertions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    sources_by_id = _source_map(sources_data)
    people = []
    for person in people_data.get("people", []):
        source_ids = list(person.get("sources", []) or [])
        local_credits = [_local_credit_from_game(person, game) for game in person.get("games", []) or [] if game.get("title")]
        candidate_external_credits = _candidate_assertions_for_person(person, source_assertions)
        source_trail = _public_source_trail(source_ids, sources_by_id)
        link_only_sources = [
            source
            for source in source_trail
            if source.get("url") and not any(source.get("source_id") in credit.get("source_ids", []) for credit in local_credits)
        ]
        coverage_warning = ""
        if not local_credits and (
            person.get("id") == "phil-scott"
            or any("mobygames" in source.get("source_id", "") for source in source_trail)
        ):
            coverage_warning = COVERAGE_WARNING
        people.append({
            "person_id": person.get("id", ""),
            "canonical_name": person.get("full_name", ""),
            "aliases": person.get("aliases", []) or [],
            "roles": person.get("roles", []) or [],
            "platforms": person.get("platforms", []) or [],
            "companies": person.get("companies", []) or [],
            "confidence": person.get("confidence", ""),
            "local_credits": local_credits,
            "local_credit_count": len(local_credits),
            "candidate_external_credits": candidate_external_credits,
            "candidate_credit_count": len(candidate_external_credits),
            "source_trail": source_trail,
            "link_only_source_count": len(link_only_sources),
            "coverage_warning": coverage_warning,
            "public_notes": "Publisher, developer and employer relationships are not inferred from credits.",
        })
    return sorted(people, key=lambda row: row["canonical_name"].casefold())


def public_credits_from_people(people_public: list[dict[str, Any]]) -> list[dict[str, Any]]:
    credits: list[dict[str, Any]] = []
    for person in people_public:
        credits.extend(person.get("local_credits", []))
    return sorted(credits, key=lambda row: (row.get("person_name", ""), row.get("game_title", ""), row.get("role_as_printed", "")))


def manual_mobygames_rows_to_assertions(path: Path, *, generated_at: str) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    assertions = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if _normalise(row.get("review_status")) not in ACCEPTABLE_MANUAL_REVIEW_STATUSES:
                continue
            game_title = row.get("game_title", "").strip()
            person_name = row.get("person_name", "").strip()
            role = row.get("role_as_printed", "").strip()
            assertions.append({
                "assertion_id": stable_id("assertion", "mobygames-manual-credit", row.get("mobygames_person_id", ""), row.get("mobygames_game_id", ""), game_title, person_name, role),
                "source_item_id": stable_id("source-item", "mobygames-manual-credit", row.get("mobygames_game_id", "") or game_title),
                "source_system": "mobygames-manual-credit",
                "subject_type": "game",
                "subject_label_as_printed": game_title,
                "predicate": "credited_as",
                "object_type": "person",
                "object_label_as_printed": person_name,
                "role_as_printed": role,
                "date_as_printed": row.get("source_date", ""),
                "place_as_printed": "",
                "platform_as_printed": row.get("platform", ""),
                "confidence": "manual import pending editorial reconciliation",
                "assertion_status": "candidate",
                "public_claim_status": "candidate",
                "evidence_status": "secondary database credit",
                "source_url": row.get("source_url", ""),
                "source_page_title": "MobyGames manual person-credit import",
                "revision_id": "",
                "permanent_url": "",
                "license": "",
                "attribution_required": False,
                "notes": row.get("notes", ""),
                "generated_at": generated_at,
                "imported_by": row.get("imported_by", ""),
                "review_status": row.get("review_status", ""),
            })
    return assertions


def write_manual_import_template(path: Path = ROOT / "data" / "manual" / "mobygames-person-credit-import.csv") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANUAL_MOBYGAMES_FIELDS, lineterminator="\n")
        writer.writeheader()


def main() -> None:
    parser = argparse.ArgumentParser(description="Build local credit graph helper artefacts.")
    parser.add_argument("--manual-template", action="store_true")
    parser.add_argument("--manual-import", default=str(ROOT / "data" / "manual" / "mobygames-person-credit-import.csv"))
    parser.add_argument("--out", default=str(ROOT / "data" / "raw" / "mobygames-manual" / "source-assertions.jsonl"))
    parser.add_argument("--generated-at", default="2026-06-20")
    args = parser.parse_args()
    if args.manual_template:
        write_manual_import_template(Path(args.manual_import))
    assertions = manual_mobygames_rows_to_assertions(Path(args.manual_import), generated_at=args.generated_at)
    write_jsonl(Path(args.out), assertions, sort_key="assertion_id")
    print({"manual_assertions": len(assertions)})


if __name__ == "__main__":
    main()

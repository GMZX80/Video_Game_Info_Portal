from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from typing import Any

import yaml

from .common import CURATED_DIR, REPORTS_DIR, ROOT, content_hash, read_jsonl, stable_id, write_jsonl

DEFAULT_SEEDS = ROOT / "config" / "north-east-seeds.yml"

PLACE_IDS = {
    "newcastle": ("place:newcastle-upon-tyne", "Newcastle upon Tyne"),
    "newcastle upon tyne": ("place:newcastle-upon-tyne", "Newcastle upon Tyne"),
    "gateshead": ("place:gateshead", "Gateshead"),
    "blaydon": ("place:blaydon", "Blaydon"),
    "sunderland": ("place:sunderland", "Sunderland"),
    "stockton": ("place:stockton-on-tees", "Stockton-on-Tees"),
    "stockton-on-tees": ("place:stockton-on-tees", "Stockton-on-Tees"),
    "middlesbrough": ("place:middlesbrough", "Middlesbrough"),
    "teesside": ("place:teesside", "Teesside"),
    "tyne and wear": ("place:tyne-and-wear", "Tyne and Wear"),
}

ORG_REVIEW_HINTS = {
    "tynesoft": ("place:blaydon", "Blaydon", "publisher only - North East attribution awaiting review"),
    "microvalue": ("place:blaydon", "Blaydon", "publisher only - North East attribution awaiting review"),
    "micro value": ("place:blaydon", "Blaydon", "publisher only - North East attribution awaiting review"),
    "zeppelin": ("place:newcastle-upon-tyne", "Newcastle upon Tyne", "publisher only - North East attribution awaiting review"),
    "zeppelin games": ("place:newcastle-upon-tyne", "Newcastle upon Tyne", "publisher only - North East attribution awaiting review"),
    "reflections": ("place:newcastle-upon-tyne", "Newcastle upon Tyne", "publisher only - North East attribution awaiting review"),
    "icon software": ("place:newcastle-upon-tyne", "Newcastle upon Tyne", "publisher only - North East attribution awaiting review"),
    "audiogenic": ("place:newcastle-upon-tyne", "Newcastle upon Tyne", "publisher only - external publisher attribution awaiting review"),
    "asl": ("place:newcastle-upon-tyne", "Newcastle upon Tyne", "publisher only - external publisher attribution awaiting review"),
}


def _contains(text: str, term: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(term.lower())}(?![a-z0-9])", text.lower()) is not None


def _has_explicit_org_place_evidence(text: str, organisation: str, place: str) -> bool:
    lowered = text.lower()
    org_matches = list(re.finditer(rf"(?<![a-z0-9]){re.escape(organisation.lower())}(?![a-z0-9])", lowered))
    place_matches = list(re.finditer(rf"(?<![a-z0-9]){re.escape(place.lower())}(?![a-z0-9])", lowered))
    location_terms = re.compile(r"\b(?:based|located|situated|office|studio|team|from)\b")
    for org_match in org_matches:
        for place_match in place_matches:
            start = max(0, min(org_match.start(), place_match.start()) - 80)
            end = min(len(lowered), max(org_match.end(), place_match.end()) + 80)
            if location_terms.search(lowered[start:end]):
                return True
    return False


def _load_seeds(path: Path = DEFAULT_SEEDS) -> dict[str, list[str]]:
    if not path.exists():
        return {"organisations": [], "people": [], "places": []}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {
        "organisations": list(data.get("organisations", [])),
        "people": list(data.get("people", [])),
        "places": list(data.get("places", [])),
    }


def classify_records(records: list[dict[str, Any]], seeds: dict[str, list[str]]) -> list[dict[str, Any]]:
    connections: list[dict[str, Any]] = []
    for record in records:
        haystack = " ".join(str(record.get(field, "")) for field in ["title", "summary", "printed_company", "byline_text"])
        text = haystack.lower()
        matched_orgs = [term for term in seeds.get("organisations", []) if _contains(text, term)]
        matched_people = [term for term in seeds.get("people", []) if _contains(text, term)]
        matched_places = [term for term in seeds.get("places", []) if _contains(text, term)]
        if not (matched_orgs or matched_people or matched_places):
            continue
        first_org = matched_orgs[0] if matched_orgs else ""
        place_id = ""
        place_name = ""
        connection_type = "reported connection requiring verification"
        status = "candidate"
        confidence = "low"
        visibility = "candidate"
        if first_org and first_org.lower() in ORG_REVIEW_HINTS:
            place_id, place_name, connection_type = ORG_REVIEW_HINTS[first_org.lower()]
            explicit_place = next((place for place in matched_places if _has_explicit_org_place_evidence(haystack, first_org, place)), "")
            if explicit_place:
                place_id, place_name = PLACE_IDS.get(explicit_place.lower(), (stable_id("place", explicit_place), explicit_place))
                connection_type = "organisation based in North East"
                status = "strongly supported"
                confidence = "high"
                visibility = "public"
            else:
                status = "probable"
                confidence = "medium"
                visibility = "probable"
        elif matched_places:
            place_id, place_name = PLACE_IDS.get(matched_places[0].lower(), (stable_id("place", matched_places[0]), matched_places[0]))
        entity_name = first_org or (matched_people[0] if matched_people else record.get("title", "candidate"))
        connections.append({
            "connection_id": stable_id("connection", record.get("source_item_id", record.get("title")), entity_name, status),
            "source_item_id": record.get("source_item_id", ""),
            "entity_type": "organisation" if first_org else ("person" if matched_people else "source-item"),
            "entity_id": stable_id("organisation" if first_org else "person" if matched_people else "source-item", entity_name),
            "entity_name": entity_name,
            "connection_type": connection_type,
            "place_id": place_id,
            "place_name": place_name,
            "organisation_id": stable_id("organisation", first_org) if first_org else "",
            "start_date": "",
            "end_date": "",
            "date_precision": "unknown",
            "evidence_ids": [stable_id("evidence", record.get("source_item_id", record.get("title")))] if status in {"verified", "strongly supported", "probable"} else [],
            "status": status,
            "confidence": confidence,
            "explanatory_text": (
                f"{entity_name} and {place_name} appear with explicit location wording in the archive metadata."
                if first_org and status == "strongly supported"
                else
                f"{entity_name} appears in archive index metadata. This record is treated as publisher or label evidence only; the North East attribution still needs record-level source inspection."
                if first_org and status != "candidate"
                else "Keyword match only; requires source inspection before public inclusion."
            ),
            "public_visibility": visibility,
            "source_magazine": record.get("publication_id", "").replace("publication:", "").replace("-", " ").title(),
            "issue_label": record.get("original_locator", ""),
            "source_url": record.get("archive_url", ""),
            "approved_by": None,
            "approved_at": None,
        })
    return connections


def classify(curated_dir: Path = CURATED_DIR, seeds_path: Path = DEFAULT_SEEDS) -> dict[str, int]:
    seeds = _load_seeds(seeds_path)
    source_items = read_jsonl(curated_dir / "source-items.jsonl")
    connections = classify_records(source_items, seeds)
    evidence = []
    claims = []
    for connection in connections:
        if not connection["evidence_ids"]:
            continue
        evidence_id = connection["evidence_ids"][0]
        evidence.append({
            "evidence_id": evidence_id,
            "source_item_id": connection["source_item_id"],
            "source_locator": connection["issue_label"],
            "evidence_type": "archive index",
            "contemporary_or_retrospective": "secondary index",
            "quote": "",
            "rights_note": "No long quotation stored.",
        })
        claims.append({
            "claim_id": stable_id("claim", connection["connection_id"]),
            "subject_type": connection["entity_type"],
            "subject_id": connection["entity_id"],
            "statement": connection["explanatory_text"],
            "source_ids": [connection["source_item_id"]],
            "source_locator": connection["issue_label"],
            "evidence_type": "archive index",
            "contemporary_or_retrospective": "secondary index",
            "confidence": connection["confidence"],
            "review_status": connection["status"],
            "contradiction_notes": "",
            "public_visibility": connection["public_visibility"],
        })
    write_jsonl(curated_dir / "north-east-connections.jsonl", connections, sort_key="connection_id")
    write_jsonl(curated_dir / "evidence.jsonl", evidence, sort_key="evidence_id")
    write_jsonl(curated_dir / "claims.jsonl", claims, sort_key="claim_id")
    write_reports(connections)
    return {
        "connections": len(connections),
        "confirmed": len([row for row in connections if row["status"] in {"verified", "strongly supported"}]),
        "candidates": len([row for row in connections if row["status"] == "candidate"]),
    }


def write_reports(connections: list[dict[str, Any]]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = ["connection_id", "entity_name", "connection_type", "place_name", "status", "confidence", "source_magazine", "issue_label", "source_url"]
    for file_name, predicate in [
        ("north-east-confirmed.csv", lambda row: row["status"] in {"verified", "strongly supported"}),
        ("north-east-candidates.csv", lambda row: row["status"] == "candidate"),
        ("manual-review-queue.csv", lambda row: row["status"] in {"candidate", "probable", "unresolved", "disputed"}),
    ]:
        with (REPORTS_DIR / file_name).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            for row in connections:
                if predicate(row):
                    writer.writerow({field: row.get(field, "") for field in fieldnames})


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify North East candidates from canonical source items.")
    parser.add_argument("--seeds", default=str(DEFAULT_SEEDS))
    args = parser.parse_args()
    print(classify(seeds_path=Path(args.seeds)))


if __name__ == "__main__":
    main()

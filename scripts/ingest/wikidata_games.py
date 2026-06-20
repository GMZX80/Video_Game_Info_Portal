from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .common import ROOT, stable_id, write_jsonl

PROPERTY_PREDICATES = {
    "P400": "platform",
    "P577": "publication_date",
    "P178": "developer",
    "P123": "publisher",
    "P136": "genre",
    "P495": "country_of_origin",
    "P856": "official_website",
}


def _label(entity: dict[str, Any]) -> str:
    return str((entity.get("labels", {}).get("en", {}) or {}).get("value") or entity.get("id", "")).strip()


def _datavalue(snak: dict[str, Any]) -> Any:
    return ((snak.get("datavalue") or {}).get("value"))


def _value_to_text(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("id") or value.get("time") or value.get("text") or value.get("amount") or value)
    return str(value or "")


def _reference_values(statement: dict[str, Any]) -> list[dict[str, list[str]]]:
    references: list[dict[str, list[str]]] = []
    for reference in statement.get("references", []) or []:
        packed: dict[str, list[str]] = {}
        for property_id, snaks in (reference.get("snaks") or {}).items():
            values = [_value_to_text(_datavalue(snak)) for snak in snaks if _datavalue(snak) is not None]
            if values:
                packed[property_id] = values
        if packed:
            references.append(packed)
    return references


def wikidata_game_assertions(entity: dict[str, Any], *, generated_at: str) -> list[dict[str, Any]]:
    qid = entity.get("id", "")
    subject_label = _label(entity)
    assertions: list[dict[str, Any]] = []
    for property_id, predicate in PROPERTY_PREDICATES.items():
        for index, statement in enumerate(entity.get("claims", {}).get(property_id, []) or [], 1):
            references = _reference_values(statement)
            if not references:
                continue
            value = _value_to_text(_datavalue(statement.get("mainsnak", {})))
            if not value:
                continue
            assertions.append({
                "assertion_id": stable_id("assertion", "wikidata", qid, property_id, index, value),
                "source_item_id": stable_id("source-item", "wikidata", qid),
                "source_system": "wikidata",
                "subject_type": "game",
                "subject_label_as_printed": subject_label,
                "predicate": predicate,
                "object_type": "wikidata_item" if value.startswith("Q") else "literal",
                "object_label_as_printed": value,
                "role_as_printed": "",
                "date_as_printed": value if predicate == "publication_date" else "",
                "place_as_printed": value if predicate == "country_of_origin" else "",
                "platform_as_printed": value if predicate == "platform" else "",
                "confidence": "referenced Wikidata statement",
                "assertion_status": "candidate",
                "public_claim_status": "candidate",
                "evidence_status": "secondary seed",
                "source_url": f"https://www.wikidata.org/wiki/{qid}",
                "source_page_title": qid,
                "revision_id": "",
                "permanent_url": "",
                "license": "CC0",
                "attribution_required": False,
                "references": references,
                "notes": "Wikidata-derived source assertion; inspect references before promotion.",
                "generated_at": generated_at,
            })
    return assertions


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert Wikidata game entity JSON into referenced source assertions.")
    parser.add_argument("entity_json", help="Path to a Wikidata entity JSON object.")
    parser.add_argument("--out", default=str(ROOT / "data" / "raw" / "wikidata-games" / "source-assertions.jsonl"))
    parser.add_argument("--generated-at", default="2026-06-20")
    args = parser.parse_args()
    entity = json.loads(Path(args.entity_json).read_text(encoding="utf-8"))
    assertions = wikidata_game_assertions(entity, generated_at=args.generated_at)
    out = Path(args.out)
    write_jsonl(out, assertions, sort_key="assertion_id")
    print({"assertions": len(assertions), "out": str(out)})


if __name__ == "__main__":
    main()

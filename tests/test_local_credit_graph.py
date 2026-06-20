import csv
import json
from pathlib import Path

from scripts.ingest.common import write_jsonl
from scripts.ingest.export_public_json import export_public_json
from scripts.ingest.local_credit_graph import (
    COVERAGE_WARNING,
    build_people_public_records,
    manual_mobygames_rows_to_assertions,
)
from scripts.ingest.mobygames import discover_mobygames_sources
from scripts.ingest.mobygames_api import mobygames_credit_payload_to_assertions


def test_mobygames_link_records_do_not_masquerade_as_imported_credits():
    records = discover_mobygames_sources([
        {
            "id": "mobygames-phil-scott",
            "title": "Phil Scott person page",
            "type": "Credits database",
            "url": "https://www.mobygames.com/person/54278/phil-scott/",
            "access": "public web",
            "rights": "Link and paraphrase only",
            "notes": "Secondary career lead.",
        }
    ])

    assert records[0]["record_type"] == "person"
    assert "credit_id" not in records[0]
    assert "role_normalised" not in records[0]


def test_mobygames_api_credit_payload_creates_candidate_source_assertions():
    assertions = mobygames_credit_payload_to_assertions(
        {
            "game_id": 123,
            "title": "Trolls",
            "platform": "Amiga",
            "credits": [
                {
                    "person_id": 54278,
                    "person_name": "Phil Scott",
                    "role": "Graphics",
                    "source_url": "https://api.mobygames.com/v1/games/123/platforms/19",
                }
            ],
        },
        generated_at="2026-06-20",
    )

    assert len(assertions) == 1
    assert assertions[0]["source_system"] == "mobygames-api"
    assert assertions[0]["predicate"] == "credited_as"
    assert assertions[0]["subject_label_as_printed"] == "Trolls"
    assert assertions[0]["object_label_as_printed"] == "Phil Scott"
    assert assertions[0]["role_as_printed"] == "Graphics"
    assert assertions[0]["assertion_status"] == "candidate"
    assert assertions[0]["evidence_status"] == "secondary database credit"


def test_manual_mobygames_import_requires_acceptable_review_status(tmp_path: Path):
    csv_path = tmp_path / "mobygames-person-credit-import.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
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
            ],
        )
        writer.writeheader()
        writer.writerow({
            "mobygames_person_id": "54278",
            "person_name": "Phil Scott",
            "game_title": "Trolls",
            "mobygames_game_id": "123",
            "platform": "Amiga",
            "role_as_printed": "Graphics",
            "source_url": "https://www.mobygames.com/game/trolls",
            "source_date": "2026-06-20",
            "imported_by": "Codex fixture",
            "review_status": "approved",
            "notes": "Fixture row.",
        })
        writer.writerow({
            "mobygames_person_id": "54278",
            "person_name": "Phil Scott",
            "game_title": "Unreviewed Game",
            "mobygames_game_id": "999",
            "platform": "Amiga",
            "role_as_printed": "Graphics",
            "source_url": "https://www.mobygames.com/game/unreviewed",
            "source_date": "2026-06-20",
            "imported_by": "Codex fixture",
            "review_status": "pending",
            "notes": "Must not import.",
        })

    assertions = manual_mobygames_rows_to_assertions(csv_path, generated_at="2026-06-20")

    assert len(assertions) == 1
    assert assertions[0]["subject_label_as_printed"] == "Trolls"
    assert assertions[0]["object_label_as_printed"] == "Phil Scott"
    assert assertions[0]["assertion_status"] == "candidate"
    assert assertions[0]["evidence_status"] == "secondary database credit"


def test_phil_scott_without_imported_local_credits_gets_coverage_warning():
    records = build_people_public_records(
        {
            "people": [
                {
                    "id": "phil-scott",
                    "full_name": "Phil Scott",
                    "aliases": ["Philip Scott"],
                    "companies": [{"name": "Tynesoft", "relationship": "Graphics/programming career lead", "status": "Probable"}],
                    "roles": ["Contributor"],
                    "platforms": [],
                    "games": [],
                    "sources": ["mobygames-phil-scott"],
                    "confidence": "Probable",
                }
            ]
        },
        {"sources": [{"id": "mobygames-phil-scott", "title": "Phil Scott person page", "url": "https://www.mobygames.com/person/54278/phil-scott/", "type": "Credits database"}]},
        [],
        [],
    )

    phil = records[0]
    assert phil["local_credit_count"] == 0
    assert phil["coverage_warning"] == COVERAGE_WARNING
    assert phil["link_only_source_count"] == 1


def test_phil_scott_fixture_credits_render_multiple_local_game_rows():
    records = build_people_public_records(
        {
            "people": [
                {
                    "id": "phil-scott",
                    "full_name": "Phil Scott",
                    "aliases": ["Philip Scott"],
                    "companies": [{"name": "Tynesoft", "relationship": "Graphics/programming career lead", "status": "Probable"}],
                    "roles": ["Contributor"],
                    "platforms": ["Amiga"],
                    "games": [
                        {"title": "Trolls", "role": "Graphics", "platforms": ["Amiga"], "sources": ["mobygames-trolls"], "confidence": "Secondary database credit"},
                        {"title": "Winter Olympiad '88", "role": "Developer as printed", "platforms": ["ZX Spectrum"], "sources": ["source-item:wikipedia"], "confidence": "Candidate"},
                    ],
                    "sources": ["mobygames-phil-scott", "mobygames-trolls"],
                    "confidence": "Probable",
                }
            ]
        },
        {"sources": []},
        [],
        [],
    )

    phil = records[0]
    assert phil["local_credit_count"] == 2
    assert [row["game_title"] for row in phil["local_credits"]] == ["Trolls", "Winter Olympiad '88"]
    assert all(row["employment_status"] == "not inferred from credit" for row in phil["local_credits"])


def test_public_export_includes_research_people_credit_graph_without_private_testimony(tmp_path: Path):
    curated = tmp_path / "data" / "curated"
    out_dir = tmp_path / "assets" / "data" / "generated"
    write_jsonl(curated / "north-east-connections.jsonl", [])
    write_jsonl(curated / "source-items.jsonl", [])
    write_jsonl(curated / "games.jsonl", [])
    write_jsonl(curated / "releases.jsonl", [])
    write_jsonl(curated / "people.jsonl", [])
    write_jsonl(curated / "organisations.jsonl", [])
    write_jsonl(curated / "evidence.jsonl", [])
    write_jsonl(curated / "credits.jsonl", [])
    write_jsonl(curated / "places.jsonl", [])
    write_jsonl(curated / "source-assertions.jsonl", [])
    write_jsonl(curated / "external-identifiers.jsonl", [])
    (tmp_path / "data").mkdir(exist_ok=True)
    (tmp_path / "data" / "people.json").write_text(json.dumps({
        "people": [{
            "id": "phil-scott",
            "full_name": "Phil Scott",
            "aliases": ["Philip Scott"],
            "companies": [],
            "roles": ["Contributor"],
            "platforms": [],
            "games": [],
            "sources": ["private-phil-scott-testimony", "mobygames-phil-scott"],
            "confidence": "Probable",
        }]
    }), encoding="utf-8")
    (tmp_path / "data" / "sources.json").write_text(json.dumps({
        "sources": [
            {"id": "private-phil-scott-testimony", "title": "Private testimony", "url": None, "access": "private source held outside repository"},
            {"id": "mobygames-phil-scott", "title": "Phil Scott person page", "url": "https://www.mobygames.com/person/54278/phil-scott/", "type": "Credits database"},
        ]
    }), encoding="utf-8")

    export_public_json(curated, out_dir)

    payload = json.loads((out_dir / "people-public.json").read_text(encoding="utf-8"))
    assert payload["people"][0]["canonical_name"] == "Phil Scott"
    assert payload["people"][0]["coverage_warning"] == COVERAGE_WARNING
    exported_text = json.dumps(payload).lower()
    assert "private-phil-scott-testimony" not in exported_text
    assert "private source held outside repository" not in exported_text

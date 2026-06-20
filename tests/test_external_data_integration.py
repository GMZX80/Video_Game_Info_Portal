import csv
import json
from pathlib import Path

from scripts.ingest.common import read_jsonl, write_jsonl
from scripts.ingest.export_public_json import export_public_json
from scripts.ingest.mobygames_api import (
    MobyGamesApiClient,
    MobyGamesApiMissingKey,
    normalise_mobygames_game,
    normalise_mobygames_platform_detail,
    sanitize_mobygames_url,
    write_missing_key_reports,
)
from scripts.ingest.wikipedia_platform_lists import (
    parse_c64_seed_rows,
    parse_zx_spectrum_rows,
    rows_to_external_identifiers,
    rows_to_source_assertions,
)
from scripts.ingest.wikidata_games import wikidata_game_assertions
from scripts.reconcile_external_entities import reconcile_external_entities


ZX_TABLE_HTML = """
<table class="wikitable sortable">
  <tr>
    <th>Title</th><th>Publisher</th><th>Developer</th><th>Licensed from</th><th>Release date</th>
  </tr>
  <tr>
    <td><i><a href="/wiki/Football_Manager_(1982_video_game)" title="Football Manager (1982 video game)">Football Manager</a></i></td>
    <td><a href="/wiki/Addictive_Games" title="Addictive Games">Addictive Games</a></td>
    <td><a href="/wiki/Kevin_Toms" title="Kevin Toms">Kevin Toms</a></td>
    <td></td>
    <td>1982</td>
  </tr>
  <tr>
    <td><i>Colin the Cleaner</i></td>
    <td>IJK Software</td>
    <td><a href="/wiki/Tynesoft" title="Tynesoft">Tynesoft</a></td>
    <td></td>
    <td>1987</td>
  </tr>
</table>
"""


C64_LIST_HTML = """
<h2 id="A">A</h2>
<div class="div-col">
  <ul>
    <li><i><a href="/wiki/Action_Biker" title="Action Biker">Action Biker</a></i></li>
    <li><i><a href="/w/index.php?title=Ambiguous_Game&amp;action=edit&amp;redlink=1" class="new" title="Ambiguous Game (page does not exist)">Ambiguous Game</a></i> (Mastertronic)</li>
  </ul>
</div>
"""


def test_mobygames_client_requires_env_key_and_writes_missing_key_reports(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("MOBYGAMES_API_KEY", raising=False)
    client = MobyGamesApiClient(cache_dir=tmp_path / "cache", request_log_path=tmp_path / "requests.jsonl")

    try:
        client.request_json("/games", {"title": "Football Manager"})
    except MobyGamesApiMissingKey as exc:
        assert "MOBYGAMES_API_KEY" in str(exc)
    else:
        raise AssertionError("expected missing key error")

    write_missing_key_reports(tmp_path / "reports", generated_at="2026-06-20")

    coverage = (tmp_path / "reports" / "mobygames-api-coverage.md").read_text(encoding="utf-8")
    failures = (tmp_path / "reports" / "mobygames-api-failures.csv").read_text(encoding="utf-8")
    assert "MobyGames API key missing" in coverage
    assert "missing_api_key" in failures


def test_mobygames_request_cache_and_logs_never_store_api_key(tmp_path: Path, monkeypatch):
    class Response:
        status_code = 200
        headers = {"content-type": "application/json"}
        url = "https://api.mobygames.com/v1/games?api_key=SECRET&title=Football"

        def json(self):
            return {"games": [{"game_id": 1, "title": "Football Manager"}]}

    class Session:
        def __init__(self):
            self.calls = []

        def get(self, url, timeout):
            self.calls.append(url)
            return Response()

    monkeypatch.setenv("MOBYGAMES_API_KEY", "SECRET")
    session = Session()
    client = MobyGamesApiClient(
        cache_dir=tmp_path / "cache",
        request_log_path=tmp_path / "requests.jsonl",
        session=session,
        sleep=lambda seconds: None,
    )

    assert client.request_json("/games", {"title": "Football"})["games"][0]["game_id"] == 1
    assert client.request_json("/games", {"title": "Football"}, resume=True)["games"][0]["game_id"] == 1

    assert len(session.calls) == 1
    assert "SECRET" in session.calls[0]
    stored_text = "\n".join(path.read_text(encoding="utf-8") for path in tmp_path.rglob("*") if path.is_file())
    assert "SECRET" not in stored_text
    assert "api_key=" not in sanitize_mobygames_url(session.calls[0])


def test_mobygames_normalisers_strip_copied_body_and_preserve_release_company_roles():
    game = normalise_mobygames_game(
        "Football Manager",
        {
            "game_id": 99,
            "title": "Football Manager",
            "alternate_titles": [{"title": "Football Manager 1"}],
            "description": "Do not export copied body text.",
            "moby_url": "https://www.mobygames.com/game/99/football-manager/",
            "platforms": [{"platform_id": 41, "platform_name": "ZX Spectrum", "first_release_date": "1982"}],
            "genres": [{"genre_name": "Sports"}],
            "moby_score": 3.7,
            "num_votes": 12,
            "sample_cover": {"image": "https://example.test/cover.jpg"},
            "sample_screenshots": [{"image": "https://example.test/shot.jpg"}],
        },
        source_url="https://api.mobygames.com/v1/games?title=Football+Manager",
        generated_at="2026-06-20T12:00:00Z",
    )

    assert game["match_confidence"] == 1.0
    assert game["match_reason"] == "normalised title exact match"
    assert "description" not in game
    assert "sample_cover" not in game
    assert "sample_screenshots" not in game

    detail = normalise_mobygames_platform_detail(
        99,
        41,
        {
            "platform_name": "ZX Spectrum",
            "releases": [
                {
                    "release_date": "1982",
                    "countries": ["United Kingdom"],
                    "companies": [{"company_id": 1, "company_name": "Addictive Games", "role": "Published by"}],
                }
            ],
            "attributes": [{"attribute_name": "Joystick"}],
            "ratings": [{"rating_system_name": "VRC"}],
        },
        source_url="https://api.mobygames.com/v1/games/99/platforms/41",
    )

    assert detail["release_companies"][0]["role"] == "Published by"
    assert detail["release_countries"] == ["United Kingdom"]


def test_wikipedia_zx_rows_become_source_assertions_without_promoting_developer():
    rows = parse_zx_spectrum_rows(
        ZX_TABLE_HTML,
        source_page_title="List of ZX Spectrum games",
        revision_id=1359444555,
        linked_qids={
            "Football Manager (1982 video game)": "Q54679",
            "Kevin Toms": "Q6392657",
            "Tynesoft": "Q7851466",
        },
        accessed_at="2026-06-20",
    )

    assert len(rows) == 2
    assert rows[0]["platform"] == "ZX Spectrum"
    assert rows[0]["wikidata_qid"] == "Q54679"
    assert rows[1]["developer_as_printed"] == "Tynesoft"
    assert rows[1]["evidence_status"] == "secondary seed"
    assert rows[1]["public_claim_status"] == "candidate"
    assert rows[1]["license"] == "CC BY-SA"
    assert rows[1]["attribution_required"] is True

    assertions = rows_to_source_assertions(rows)
    developer_assertions = [row for row in assertions if row["predicate"] == "developer_as_printed"]
    assert developer_assertions[0]["assertion_status"] == "candidate"
    assert developer_assertions[0]["notes"] == "Wikipedia-derived source assertion; do not promote without corroboration."


def test_wikipedia_c64_rows_parse_title_seeds_and_external_ids():
    rows = parse_c64_seed_rows(
        C64_LIST_HTML,
        source_page_title="List of Commodore 64 games (A-M)",
        revision_id=1358813372,
        linked_qids={"Action Biker": "Q4676742"},
        accessed_at="2026-06-20",
    )

    assert [row["title"] for row in rows] == ["Action Biker", "Ambiguous Game"]
    assert rows[0]["wikidata_qid"] == "Q4676742"
    assert rows[0]["platform"] == "Commodore 64"
    assert rows[1]["publisher_as_printed"] == "Mastertronic"
    assert rows[1]["public_claim_status"] == "candidate"

    identifiers = rows_to_external_identifiers(rows)
    assert identifiers[0]["source_system"] == "wikidata"
    assert identifiers[0]["external_id"] == "Q4676742"
    assert identifiers[0]["match_status"] == "candidate"


def test_wikidata_statements_require_references_before_source_assertions():
    entity = {
        "id": "Q54679",
        "labels": {"en": {"value": "Football Manager"}},
        "claims": {
            "P400": [
                {
                    "mainsnak": {"datavalue": {"value": {"id": "Q853547"}}},
                    "references": [{"snaks": {"P854": [{"datavalue": {"value": "https://example.test/ref"}}]}}],
                }
            ],
            "P123": [
                {
                    "mainsnak": {"datavalue": {"value": {"id": "Q999"}}},
                    "references": [],
                }
            ],
        },
    }

    assertions = wikidata_game_assertions(entity, generated_at="2026-06-20")

    assert len(assertions) == 1
    assert assertions[0]["source_system"] == "wikidata"
    assert assertions[0]["subject_label_as_printed"] == "Football Manager"
    assert assertions[0]["predicate"] == "platform"
    assert assertions[0]["references"][0]["P854"] == ["https://example.test/ref"]


def test_public_export_includes_external_seed_records_but_not_confirmed_facts(tmp_path: Path):
    curated = tmp_path / "data" / "curated"
    out_dir = tmp_path / "assets" / "data" / "generated"
    write_jsonl(curated / "north-east-connections.jsonl", [])
    write_jsonl(curated / "source-items.jsonl", [])
    write_jsonl(curated / "games.jsonl", [])
    write_jsonl(curated / "releases.jsonl", [])
    write_jsonl(curated / "people.jsonl", [])
    write_jsonl(curated / "organisations.jsonl", [])
    write_jsonl(curated / "evidence.jsonl", [])
    write_jsonl(curated / "source-assertions.jsonl", [
        {
            "assertion_id": "assertion:wikipedia:colin-the-cleaner:developer",
            "source_item_id": "source-item:wikipedia-platform-lists:colin-the-cleaner",
            "source_system": "wikipedia",
            "subject_type": "game",
            "subject_label_as_printed": "Colin the Cleaner",
            "predicate": "developer_as_printed",
            "object_type": "organisation",
            "object_label_as_printed": "Tynesoft",
            "role_as_printed": "",
            "date_as_printed": "1987",
            "place_as_printed": "",
            "platform_as_printed": "ZX Spectrum",
            "confidence": "secondary seed",
            "assertion_status": "candidate",
            "public_claim_status": "candidate",
            "evidence_status": "secondary seed",
            "source_url": "https://en.wikipedia.org/wiki/List_of_ZX_Spectrum_games",
            "source_page_title": "List of ZX Spectrum games",
            "revision_id": 1359444555,
            "permanent_url": "https://en.wikipedia.org/w/index.php?title=List_of_ZX_Spectrum_games&oldid=1359444555",
            "license": "CC BY-SA",
            "attribution_required": True,
            "notes": "Wikipedia-derived source assertion; do not promote without corroboration.",
        }
    ])
    write_jsonl(curated / "external-identifiers.jsonl", [])

    export_public_json(curated, out_dir)

    payload = json.loads((out_dir / "source-assertions-public.json").read_text(encoding="utf-8"))
    assert payload["records"][0]["public_claim_status"] == "candidate"
    assert payload["records"][0]["license"] == "CC BY-SA"
    assert "confirmed" not in json.dumps(payload).lower()
    assert "article body" not in json.dumps(payload).lower()


def test_external_reconciliation_queues_duplicates_without_merging(tmp_path: Path):
    curated = tmp_path / "data" / "curated"
    reports = tmp_path / "reports"
    write_jsonl(curated / "games.jsonl", [
        {"game_id": "game:football-manager", "canonical_title": "Football Manager", "title_variants": [], "sources": []}
    ])
    write_jsonl(curated / "people.jsonl", [])
    write_jsonl(curated / "organisations.jsonl", [])
    write_jsonl(curated / "source-assertions.jsonl", [
        {
            "assertion_id": "assertion:wikipedia:football-manager:title",
            "source_item_id": "source-item:wikipedia:football-manager",
            "source_system": "wikipedia",
            "subject_type": "game",
            "subject_label_as_printed": "Football Manager",
            "predicate": "title_seed",
            "object_type": "game",
            "object_label_as_printed": "Football Manager",
            "confidence": "secondary seed",
            "assertion_status": "candidate",
            "public_claim_status": "candidate",
        },
        {
            "assertion_id": "assertion:wikipedia:football-manager-duplicate:title",
            "source_item_id": "source-item:wikipedia:football-manager-duplicate",
            "source_system": "wikipedia",
            "subject_type": "game",
            "subject_label_as_printed": "Football Manager",
            "predicate": "title_seed",
            "object_type": "game",
            "object_label_as_printed": "Football Manager",
            "confidence": "secondary seed",
            "assertion_status": "candidate",
            "public_claim_status": "candidate",
        },
    ])
    write_jsonl(curated / "external-identifiers.jsonl", [])

    counts = reconcile_external_entities(curated, reports)

    assert counts["game_candidates"] == 2
    with (reports / "reconciliation-queue-games.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2
    assert {row["suggested_action"] for row in rows} == {"review-existing-match"}
    assert all(row["decision"] == "unresolved" for row in rows)

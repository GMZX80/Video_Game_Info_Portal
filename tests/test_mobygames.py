import json
from pathlib import Path

from scripts.ingest.mobygames import (
    MOBYGAMES_ATTRIBUTION,
    build_api_url,
    discover_mobygames_sources,
    export_mobygames_index,
    parse_mobygames_url,
)
from scripts.ingest.common import ROOT


def _keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _keys(child)


def test_parse_mobygames_url_classifies_core_record_shapes():
    credits = parse_mobygames_url("https://www.mobygames.com/game/485/command-conquer-red-alert/credits/dos/")
    assert credits.record_type == "game credits page"
    assert credits.numeric_id == "485"
    assert credits.slug == "command-conquer-red-alert"
    assert credits.platform_slug == "dos"

    person = parse_mobygames_url("https://www.mobygames.com/person/54278/phil-scott/")
    assert person.record_type == "person"
    assert person.numeric_id == "54278"
    assert person.slug == "phil-scott"

    company = parse_mobygames_url("https://www.mobygames.com/company/4615/tynesoft-computer-software/")
    assert company.record_type == "company"
    assert company.slug == "tynesoft-computer-software"

    slug_only_game = parse_mobygames_url("https://www.mobygames.com/game/trolls")
    assert slug_only_game.record_type == "game"
    assert slug_only_game.numeric_id == ""
    assert slug_only_game.slug == "trolls"


def test_discovers_all_registered_mobygames_sources_as_public_evidence_records():
    data = json.loads((ROOT / "data" / "sources.json").read_text(encoding="utf-8"))

    records = discover_mobygames_sources(data["sources"])

    assert len(records) == 25
    assert all(record["attribution"] == MOBYGAMES_ATTRIBUTION for record in records)
    assert all(record["rights_note"] == "Link and paraphrase only" for record in records)
    assert {record["record_type"] for record in records} >= {"person", "company", "game", "game credits page"}
    assert any(record["source_id"] == "mobygames-phil-scott" and record["title"] == "Phil Scott person page" for record in records)
    assert any(record["source_id"] == "mobygames-tynesoft" and record["record_type"] == "company" for record in records)
    assert any(record["source_id"] == "mobygames-red-alert-credits" and record["platform_slug"] == "dos" for record in records)


def test_exports_mobygames_index_without_private_or_copied_body_fields(tmp_path: Path):
    out_path = tmp_path / "mobygames-index.json"

    payload = export_mobygames_index(ROOT / "data" / "sources.json", out_path)

    exported = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload == exported
    assert exported["attribution"] == MOBYGAMES_ATTRIBUTION
    assert exported["source_policy"] == "Official API or curated source register only; no page scraping."
    assert exported["records"][0]["source_id"].startswith("mobygames-")
    text = json.dumps(exported).lower()
    assert "private-phil-scott-testimony" not in text
    assert "private first-hand" not in text
    assert not {"sample_cover", "sample_screenshots", "description"} & set(_keys(exported))


def test_build_api_url_uses_official_api_and_urlencodes_query_values():
    url = build_api_url(
        "/games",
        "A+B key",
        {
            "title": "Command & Conquer",
            "format": "brief",
            "platform": ["2", "6"],
        },
    )

    assert url.startswith("https://api.mobygames.com/v1/games?")
    assert "api_key=A%2BB+key" in url
    assert "title=Command+%26+Conquer" in url
    assert "format=brief" in url
    assert "platform=2" in url
    assert "platform=6" in url

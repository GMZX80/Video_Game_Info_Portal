import json
from dataclasses import replace
from pathlib import Path

from scripts.build_narrative_site import (
    build_narrative_site,
    load_content,
    load_evidence_context,
    validate_content,
)


def test_narrative_content_validates_against_public_evidence():
    records = load_content()
    failures = validate_content(records, load_evidence_context())

    assert failures == []
    assert {record.metadata["profile_kind"] for record in records if "profile_kind" in record.metadata} >= {
        "person",
        "studio",
        "game",
    }
    assert any(record.route == "stories/code-through-the-letterbox" for record in records)


def test_narrative_dist_routes_and_search_index(tmp_path: Path):
    result = build_narrative_site(tmp_path)

    required_routes = [
        "index.html",
        "phase-0/index.html",
        "stories/index.html",
        "stories/code-through-the-letterbox/index.html",
        "people/gary-partis/index.html",
        "studios/tynesoft/index.html",
        "games/oxo/index.html",
        "games/doctor-who-and-the-mines-of-terror/index.html",
        "games/super-gran/index.html",
        "research/corrections/index.html",
        "contribute/index.html",
        "talk/index.html",
        "search/index.html",
        "assets/data/generated/narrative-search-index.json",
    ]
    for route in required_routes:
        assert (tmp_path / route).exists(), route

    story_html = (tmp_path / "stories/code-through-the-letterbox/index.html").read_text(encoding="utf-8")
    game_html = (tmp_path / "games/super-gran/index.html").read_text(encoding="utf-8")
    search_index = json.loads((tmp_path / "assets/data/generated/narrative-search-index.json").read_text(encoding="utf-8"))

    assert result["records"] == len(search_index["items"])
    assert "Evidence within reach" in story_html
    assert "evidence-drawer" in story_html
    assert "Magazine index entry" in game_html
    assert "Reviewed release" not in game_html

    generated_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in tmp_path.rglob("*")
        if path.is_file() and path.suffix in {".html", ".js", ".json", ".css"}
    )
    assert 'href="/assets/' not in generated_text
    assert 'src="/assets/' not in generated_text
    assert "drive.google.com" not in generated_text


def test_narrative_validation_rejects_missing_source():
    record = load_content()[0]
    bad_record = replace(
        record,
        path=Path("content/stories/bad.md"),
        metadata={
            **record.metadata,
            "id": "story:bad",
            "route": "stories/bad",
            "linked_source_ids": ["source:missing"],
        },
    )

    failures = validate_content([bad_record], load_evidence_context())

    assert any("missing linked source source:missing" in failure for failure in failures)

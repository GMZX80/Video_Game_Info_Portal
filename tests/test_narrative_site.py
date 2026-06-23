from pathlib import Path

from scripts.build_narrative_site import build_narrative_site


def test_narrative_homepage_is_talk_focused(tmp_path: Path):
    build_narrative_site(tmp_path)
    homepage_html = (tmp_path / "index.html").read_text(encoding="utf-8")

    assert "Newcastle’s Impact on the Global Video Game Industry" in homepage_html
    assert "Access the talk materials" in homepage_html
    assert "Professor Graham Morgan" in homepage_html
    assert "Search the public archive" not in homepage_html
    assert "North East collection" not in homepage_html
    assert "Phase 0 narrative archive" not in homepage_html


def test_narrative_build_keeps_required_supporting_routes(tmp_path: Path):
    build_narrative_site(tmp_path)

    required_routes = [
        "index.html",
        "talk/index.html",
        "search/index.html",
        "research/corrections/index.html",
        "sources/mobygames/index.html",
        "assets/data/generated/narrative-search-index.json",
        "assets/data/generated/public-search-index.json",
        "assets/data/generated/mobygames-index.json",
    ]
    for route in required_routes:
        assert (tmp_path / route).exists(), route

from scripts.ingest.sinclair_supplement import (
    discover_physical_issues,
    parse_typein_index_entries,
    parse_unlinked_software_entries,
)
from scripts.ingest.stairway_supplement import parse_tynesoft_group_captions


def test_discover_physical_issues_preserves_second_issue_58():
    html = """
    <a href="058/index.htm">58</a>
    <a href="058a/index.htm">58a</a>
    <a href="059/index.htm">59</a>
    """

    rows = discover_physical_issues(html)

    assert [row["archive_issue_key"] for row in rows] == ["058", "058a", "059"]


def test_unlinked_software_entry_keeps_printed_label_separate():
    html = """
    <h2>SOFTWARE</h2>
    <p><a href="linked.htm">LINKED GAME</a> Hewson</p>
    <p>UNLINKED GAME Tynesoft</p>
    <h2>FEATURES</h2>
    """

    rows = parse_unlinked_software_entries(
        html,
        "058a",
        "https://sinclairuser.com/058a/index.htm",
        "February 1987",
        accessed_at="2026-06-19",
        companies=["Tynesoft", "Hewson"],
    )

    unlinked = next(row for row in rows if row["title"] == "UNLINKED GAME")
    assert unlinked["printed_company"] == "Tynesoft"
    assert unlinked["issue_id"] == "issue:sinclair-user:058a"


def test_typein_contents_store_title_not_program_listing():
    html = """
    <h2>LISTINGS</h2>
    <p>STAR CHASER</p>
    <p>A short arcade program for the Spectrum.</p>
    <h2>REGULARS</h2>
    """

    rows = parse_typein_index_entries(
        html,
        "058a",
        "https://sinclairuser.com/058a/index.htm",
        "February 1987",
        accessed_at="2026-06-19",
    )

    assert rows[0]["title"] == "STAR CHASER"
    assert rows[0]["item_type"] == "type-in program"
    assert "arcade program" in rows[0]["summary"].lower()
    assert "listing" not in rows[0]


def test_tynesoft_group_caption_is_recorded_as_testimony():
    html = """
    <p>Tynesoft Staff: Image 1</p>
    <p>Left to right as follows ...</p>
    <p>Phil Scott (Artist/Programmer)</p>
    <p>Steve Tall (Atari/Amiga Programmer)</p>
    <p>Tynesoft Staff: Image 2</p>
    <p>Bottom left</p>
    <p>Brian Jobling (Atari and other 8-bit programmer)</p>
    """

    identities, media = parse_tynesoft_group_captions(html)

    assert [row["primary_name_as_printed"] for row in identities] == [
        "Phil Scott",
        "Steve Tall",
        "Brian Jobling",
    ]
    assert identities[0]["evidence_status"] == "first-person retrospective testimony"
    assert identities[0]["public_visibility"] == "research-only"
    assert "No visual identification" in identities[0]["notes"]
    assert len(media) == 2
    assert media[0]["permission_status"] == "not established"

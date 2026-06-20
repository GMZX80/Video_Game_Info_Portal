from scripts.ingest.sinclair_supplement import (
    discover_physical_issues,
    parse_typein_index_entries,
    parse_unlinked_software_entries,
)
from scripts.ingest.stairway_supplement import parse_tynesoft_group_captions
from scripts.ingest.archive_postprocess import parse_tynesoft_caption_testimony


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


def test_tynesoft_caption_parser_handles_actual_stairway_html_structure():
    html = """
    <p><center><font>Tynesoft Staff: Image
    1<br><a href="img/article-kblake/Tynesoft1.jpg">Click here for larger image</a></font></center></p>
    <p><font>Left to right as follows ...</font></p>
    <p><b><font>Mike Landruff</font></b><font> aka <b>Mikbox 'I have the girth'</b>
    <i>(Artist)</i><br>Settled down now.</font></p>
    <p><b><font>Bruce Nesbitt</font></b><font> <i>(Programmer)</i><br>
    More recently co-authored Z.<br><br>
    <b>Paul Drummond</b> <i>(Artist)<br></i>After Tynesoft worked for Flair.</font></p>
    <p><b><font>Phil Scott</font></b><font> <i>(Artist/Programmer)<br></i>A mere child in this pic.</font></p>
    <p><center><font>Tynesoft Staff: Image
    2<br></font><a href="img/article-kblake/Tynesoft2.jpg">Click here for larger image</a></center></p>
    <p><font>Bottom left<br></font><b><font>Brian Jobling</font></b><font>
    <i>(Atari and other 8-bit programmer)<br></i>Went on to own Zepplin Games.<br><br>
    </font><font>Middle Right<br></font><b><font>Julian Jameson</font></b><font>
    <i>(C16 programmer)</i><br>Known for Cannon Fodder.</font></p>
    """

    identities, media = parse_tynesoft_caption_testimony(
        html,
        "https://www.stairwaytohell.com/articles/KBlake.html",
        accessed_at="2026-06-19",
    )

    assert [row["name_as_printed"] for row in identities] == [
        "Mike Landruff",
        "Bruce Nesbitt",
        "Paul Drummond",
        "Phil Scott",
        "Brian Jobling",
        "Julian Jameson",
    ]
    assert [row["role_as_printed"] for row in identities] == [
        "Artist",
        "Programmer",
        "Artist",
        "Artist/Programmer",
        "Atari and other 8-bit programmer",
        "C16 programmer",
    ]
    assert identities[-2]["position_description"] == "Bottom left"
    assert identities[-1]["position_description"] == "Middle Right"
    assert identities[0]["verification_status"] == "unconfirmed pending independent corroboration"
    assert len(media) == 2

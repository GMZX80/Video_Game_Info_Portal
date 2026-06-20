from scripts.ingest.crash import parse_issue_index as parse_crash_issue_index
from scripts.ingest.globalnet import parse_ttf_typeins
from scripts.ingest.sinclair_user import (
    discover_issue_links,
    parse_article_page,
    parse_contents_page,
    parse_issue_page,
)
from scripts.ingest.stairway import (
    discover_links as discover_stairway_links,
    parse_catalogue_entries,
    parse_lost_and_found_entries,
    parse_stairway_page,
    parse_tynesoft_photo_identifications,
)
from scripts.ingest.zzap64 import parse_games_page


def test_parse_sinclair_contents_extracts_issue_and_entries():
    html = """
    <a href="001/index.htm">Issue 1 : April 1982</a>
    Sinclairvoyance - Let's begin with a look ahead
    Software Scene
    <a href="002/index.htm">Issue 2 : May 1982</a>
    Hardware World
    """

    issues = parse_contents_page(html, "https://sinclairuser.com/contents.htm")

    assert issues[0]["issue_number"] == "001"
    assert issues[0]["cover_date"] == "April 1982"
    assert "Software Scene" in issues[0]["index_entries"]
    assert issues[1]["index_url"] == "https://sinclairuser.com/002/index.htm"


def test_discover_sinclair_issue_links_finds_homepage_issue_grid():
    html = """
    <a href="001/index.htm">1</a>
    <a href="133/index.htm">[133]</a>
    <a href="contents.htm">Contents</a>
    """

    issues = discover_issue_links(html, "https://sinclairuser.com/")

    assert [row["issue_number"] for row in issues] == ["001", "133"]
    assert issues[1]["index_url"] == "https://sinclairuser.com/133/index.htm"


def test_parse_sinclair_issue_page_discovers_articles_and_staff():
    html = """
    <h2>Issue 50</h2><p>May 1986</p>
    <p>Editor</p><p>Bill Scolding</p>
    <h3>SOFTWARE</h3>
    <p><a href="quaztrn.htm">QUAZATRON</a> Hewson</p>
    <p><a href="index.htm">Issue 50 Contents</a></p>
    """

    issue = parse_issue_page(html, "https://sinclairuser.com/050/index.htm", "050")

    assert issue["cover_date"] == "May 1986"
    assert issue["staff"]["editor"] == ["Bill Scolding"]
    assert issue["article_links"] == [
        {
            "title": "QUAZATRON",
            "article_url": "https://sinclairuser.com/050/quaztrn.htm",
            "item_type": "review",
            "section": "SOFTWARE",
            "printed_company": "Hewson",
        }
    ]


def test_parse_sinclair_article_keeps_reviewer_and_programmer_separate():
    html = """
    <h1>Quazatron</h1>
    <p>A review body which is deliberately not retained by the parser.</p>
    <p>Publisher Hewson</p>
    <p>Programmer Steve Turner</p>
    <p>Price £8.95 Memory 48K</p>
    <p>Joystick Kempston, Sinclair, Cursor</p>
    <p>*****</p><p>Chris Bourne</p>
    <p>Sinclair User</p><p>May 1986</p>
    """

    item = parse_article_page(html, "https://sinclairuser.com/050/quaztrn.htm", "050")

    assert item["title"] == "Quazatron"
    assert item["printed_company"] == "Hewson"
    assert item["named_contributors"] == [{"name": "Steve Turner", "role_as_printed": "Programmer"}]
    assert item["byline_text"] == "Chris Bourne"
    assert item["price"] == "£8.95"
    assert item["memory"] == "48K"
    assert item["score"] == "5 stars"
    assert "review body" not in item["summary"].lower()


def test_parse_crash_issue_index_keeps_reviewers_and_programmers_separate():
    html = """
    <h2>Issue No. 1 FEBRUARY 1984</h2>
    <h3><a href="deathchase.htm">3D DEATHCHASE</a></h3>
    <p>Producer: Micromega<br>Author: Mervyn Estcourt<br>Retail price: £6.95</p>
    <h3><a href="news.htm">NEWS INPUT</a></h3>
    <p>A brief round-up for the month</p>
    """

    items = parse_crash_issue_index(html, "https://www.crashonline.org.uk/01/index.htm", "001")

    review = next(item for item in items if item["title"] == "3D DEATHCHASE")
    assert review["item_type"] == "review"
    assert review["printed_company"] == "Micromega"
    assert review["named_contributors"] == [{"name": "Mervyn Estcourt", "role_as_printed": "Author"}]
    assert review["byline_text"] == ""


def test_parse_zzap_games_page_extracts_structured_game_rows():
    html = """
    <table>
    <tr><th>Title</th><th>Publisher</th><th>Best Score</th><th>Medal</th><th>Reviews</th></tr>
    <tr><td><a href="/game/elite">Elite</a></td><td>Firebird</td><td>97%</td><td>Gold Medal</td><td>1</td></tr>
    </table>
    """

    rows = parse_games_page(html, "https://www.zzap64.co.uk/games")

    assert rows == [
        {
            "title": "Elite",
            "company": "Firebird",
            "best_score": "97%",
            "award": "Gold Medal",
            "reviews_count": 1,
            "url": "https://www.zzap64.co.uk/game/elite",
        }
    ]


def test_parse_globalnet_typeins_maps_codes_without_listing_text():
    html = """
    <table>
    <tr><th>TITLE<br><i>ARTICLE</i></th><th>AUTHOR</th><th>ISSUE</th><th>PAGE</th><th>FILE</th><th>COMP</th><th>PROG</th><th>LANG</th><th>INFO</th><th>YYMM</th></tr>
    <tr><td><a href="su8408.zip">A Day At the Races</a></td><td>Andrew Bird</td><td>Aug'84</td><td>71</td><td>TZX</td><td>SP</td><td>G</td><td>B</td><td>Y</td><td>8408</td></tr>
    </table>
    """

    rows = parse_ttf_typeins(html, "http://www.users.globalnet.co.uk/~jg27paw4/type-ins/sincuser/su_names.htm")

    assert rows[0]["title"] == "A Day At the Races"
    assert rows[0]["machine"] == "ZX Spectrum"
    assert rows[0]["program_type"] == "game"
    assert rows[0]["language"] == "BASIC"
    assert "listing" not in rows[0]


def test_parse_stairway_profile_preserves_original_publication():
    html = """
    <p>GARY PARTIS</p><p>Profile, A&amp;B March 1987</p>
    <p>This page contains an article body which is not retained.</p>
    <p>This article appeared in the March 1987 edition of "A &amp; B Computing".</p>
    """

    item = parse_stairway_page(html, "https://www.stairwaytohell.com/authors/gpartis/PRO-GPartis.html")

    assert item["item_type"] == "profile"
    assert item["original_publication"] == "A & B Computing"
    assert item["date"] == "March 1987"
    assert "article body" not in item["summary"].lower()


def test_parse_stairway_tynesoft_caption_as_testimony_not_visual_id():
    html = """
    <p>Tynesoft Staff: Image 1</p>
    <p>Left to right as follows ...</p>
    <p>Mike Landruff (Artist)</p>
    <p>Phil Scott (Artist/Programmer)</p>
    """

    rows = parse_tynesoft_photo_identifications(
        html,
        "https://www.stairwaytohell.com/articles/KBlake.html",
    )

    assert [row["name_as_printed"] for row in rows] == ["Mike Landruff", "Phil Scott"]
    assert rows[0]["verification_status"] == "unconfirmed pending independent corroboration"
    assert "No visual identification" in rows[0]["notes"]


def test_parse_stairway_lost_and_found_keeps_status_and_named_author():
    html = """
    <p>LOST AND FOUND</p>
    <p>PILLAGE by Peter Scott (AUDIOGENIC)</p>
    <p>From A &amp; B Computing, November 1987:</p>
    <p>Article text not retained.</p>
    <p>STATUS: LOST</p>
    <p>SINISTAR by Peter Johnson (ATARISOFT)</p>
    <p>STATUS: FOUND</p>
    """

    rows = parse_lost_and_found_entries(html, "https://www.stairwaytohell.com/lostandfound/indexb.html")
    pillage = next(row for row in rows if row["title"] == "PILLAGE")

    assert pillage["printed_company"] == "AUDIOGENIC"
    assert pillage["source_status"] == "LOST"
    assert pillage["named_contributors"][0]["name"] == "Peter Scott"
    assert "Article text" not in pillage["summary"]


def test_stairway_link_discovery_excludes_downloads_and_binaries():
    html = """
    <a href="/authors/gpartis/PRO-GPartis.html">Profile</a>
    <a href="/downloads/game.zip">Download</a>
    <a href="https://example.com/external.html">External</a>
    """

    links, excluded = discover_stairway_links(
        html,
        "https://www.stairwaytohell.com/articles/index.html",
        include_catalogues=False,
    )

    assert links == ["https://www.stairwaytohell.com/authors/gpartis/PRO-GPartis.html"]
    assert any(row["reason"] == "binary or download file" for row in excluded)


def test_parse_stairway_electron_catalogue_pairs_title_and_label():
    html = """
    <p>main | archive indexes | browse archive</p>
    <p>PSYCASTRIA</p><p>Audiogenic</p>
    <p>PSYCASTRIA 2</p><p>Atlantis (RR)</p>
    """

    rows = parse_catalogue_entries(html, "https://www.stairwaytohell.com/electron/p.html")

    assert rows[0]["title"] == "PSYCASTRIA"
    assert rows[0]["printed_company"] == "Audiogenic"
    assert rows[0]["machine"] == "Acorn Electron"

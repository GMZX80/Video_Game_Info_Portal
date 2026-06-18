from scripts.ingest.crash import parse_issue_index as parse_crash_issue_index
from scripts.ingest.globalnet import parse_ttf_typeins
from scripts.ingest.sinclair_user import parse_contents_page
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

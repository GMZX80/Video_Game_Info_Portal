from __future__ import annotations

import argparse
import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .common import RAW_DIR, RespectfulFetcher, add_common_arguments, content_hash, short_summary, stable_id, write_jsonl

ROOT_URL = "https://www.zzap64.co.uk/"
GAMES_URL = "https://www.zzap64.co.uk/games"
REVIEWS_URL = "https://www.zzap64.co.uk/cgi-bin/displayallreviews.pl"
FEATURES_URL = "https://www.zzap64.co.uk/cgi-bin/displayallfeatures.pl"


def parse_games_page(html: str, base_url: str = GAMES_URL) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict[str, Any]] = []
    for tr in soup.find_all("tr"):
        cells = [" ".join(cell.get_text(" ", strip=True).split()) for cell in tr.find_all(["td", "th"])]
        if len(cells) < 5 or cells[0].lower() == "title":
            continue
        link = tr.find("a", href=True)
        try:
            reviews_count = int(re.search(r"\d+", cells[4]).group(0)) if re.search(r"\d+", cells[4]) else 0
        except ValueError:
            reviews_count = 0
        rows.append({
            "title": cells[0],
            "company": cells[1],
            "best_score": cells[2],
            "award": cells[3],
            "reviews_count": reviews_count,
            "url": urljoin(base_url, link["href"]) if link else base_url,
        })
    return rows


def parse_link_list(html: str, base_url: str, item_type: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for link in soup.find_all("a", href=True):
        title = " ".join(link.get_text(" ", strip=True).split())
        match = re.match(r"(\d+)\s*-\s*(.+)", title)
        if not match:
            continue
        rows.append({
            "issue_number": match.group(1).zfill(3),
            "title": match.group(2),
            "item_type": item_type,
            "url": urljoin(base_url, link["href"]),
        })
    return rows


def run(indexes_only: bool = True, resume: bool = False, accessed_at: str = "2026-06-18") -> dict[str, int]:
    fetcher = RespectfulFetcher()
    games_result = fetcher.fetch(GAMES_URL, resume=resume)
    review_result = fetcher.fetch(REVIEWS_URL, resume=resume)
    features_result = fetcher.fetch(FEATURES_URL, resume=resume)
    games = parse_games_page(games_result.text, games_result.canonical_url)
    reviews = parse_link_list(review_result.text, review_result.canonical_url, "review")
    features = parse_link_list(features_result.text, features_result.canonical_url, "feature")
    issue_numbers = sorted({row["issue_number"] for row in [*reviews, *features]})
    issue_rows = [
        {
            "raw_id": stable_id("raw", "zzap64", issue_number),
            "archive": "zzap64",
            "record_type": "issue",
            "publication_id": "publication:zzap64",
            "issue_id": stable_id("issue", "zzap64", issue_number),
            "issue_number": issue_number,
            "cover_date": "",
            "date_precision": "unknown",
            "index_url": ROOT_URL,
            "source_url": ROOT_URL,
            "accessed_at": accessed_at,
            "content_hash": content_hash(issue_number),
        }
        for issue_number in issue_numbers
    ]
    item_rows = []
    for game in games:
        item_rows.append({
            "raw_id": stable_id("raw-source-item", "zzap64", "game", game["title"]),
            "archive": "zzap64",
            "record_type": "source-item",
            "source_item_id": stable_id("source-item", "zzap64", "game", game["title"]),
            "publication_id": "publication:zzap64",
            "issue_id": "",
            "item_type": "review",
            "title": game["title"],
            "byline_text": "",
            "printed_company": game["company"],
            "archive_url": game["url"],
            "original_locator": "ZzapBible game index",
            "date": "",
            "summary": short_summary(f"{game['title']} listed with company field {game['company']} and best score {game['best_score']}."),
            "rights_note": "Structured game-index metadata only; company field is not treated as developer.",
            "accessed_at": accessed_at,
            "content_hash": content_hash(str(game)),
            "score": game["best_score"],
            "award": game["award"],
        })
    for row in [*reviews, *features]:
        item_rows.append({
            "raw_id": stable_id("raw-source-item", "zzap64", row["issue_number"], row["title"]),
            "archive": "zzap64",
            "record_type": "source-item",
            "source_item_id": stable_id("source-item", "zzap64", row["issue_number"], row["title"]),
            "publication_id": "publication:zzap64",
            "issue_id": stable_id("issue", "zzap64", row["issue_number"]),
            "item_type": row["item_type"],
            "title": row["title"],
            "byline_text": "",
            "archive_url": row["url"],
            "original_locator": f"Zzap!64 issue {row['issue_number']}",
            "date": "",
            "summary": short_summary(row["title"]),
            "rights_note": "Archive index metadata only; link and paraphrase.",
            "accessed_at": accessed_at,
            "content_hash": content_hash(str(row)),
        })
    out = RAW_DIR / "zzap64"
    write_jsonl(out / "issues.jsonl", issue_rows, sort_key="issue_id")
    write_jsonl(out / "source-items.jsonl", item_rows, sort_key="source_item_id")
    return {"issues": len(issue_rows), "source_items": len(item_rows), "games": len(games)}


def main() -> None:
    parser = add_common_arguments(argparse.ArgumentParser(description="Ingest Zzap!64/ZzapBible metadata."))
    args = parser.parse_args()
    print(run(indexes_only=args.indexes_only, resume=args.resume, accessed_at=args.accessed_date))


if __name__ == "__main__":
    main()

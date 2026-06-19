from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from typing import Any

from .common import CURATED_DIR, ROOT, read_jsonl

DEFAULT_DB = ROOT / "build" / "video-game-history.sqlite"
SCHEMA_VERSION = 2


def _json(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def build_database(curated_dir: Path = CURATED_DIR, db_path: Path = DEFAULT_DB) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    try:
        con.execute("PRAGMA foreign_keys = ON")
        con.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        con.execute("INSERT INTO metadata VALUES ('schema_version', ?)", (str(SCHEMA_VERSION),))

        con.execute("CREATE TABLE publications (publication_id TEXT PRIMARY KEY, canonical_title TEXT NOT NULL, payload TEXT NOT NULL)")
        con.execute("CREATE TABLE issues (issue_id TEXT PRIMARY KEY, publication_id TEXT NOT NULL REFERENCES publications(publication_id), issue_number TEXT, cover_date TEXT, date_precision TEXT, payload TEXT NOT NULL)")
        con.execute("CREATE TABLE source_items (source_item_id TEXT PRIMARY KEY, publication_id TEXT NOT NULL REFERENCES publications(publication_id), issue_id TEXT REFERENCES issues(issue_id), item_type TEXT NOT NULL, title TEXT NOT NULL, archive_url TEXT, summary TEXT, payload TEXT NOT NULL)")
        con.execute("CREATE TABLE people (person_id TEXT PRIMARY KEY, canonical_name TEXT NOT NULL, evidence_status TEXT, payload TEXT NOT NULL)")
        con.execute("CREATE TABLE organisations (organisation_id TEXT PRIMARY KEY, canonical_name TEXT NOT NULL, organisation_type TEXT, evidence_status TEXT, payload TEXT NOT NULL)")
        con.execute("CREATE TABLE games (game_id TEXT PRIMARY KEY, canonical_title TEXT NOT NULL, payload TEXT NOT NULL)")
        con.execute("CREATE TABLE releases (release_id TEXT PRIMARY KEY, game_id TEXT NOT NULL REFERENCES games(game_id), platform_id TEXT, release_title TEXT, evidence_status TEXT, payload TEXT NOT NULL)")
        con.execute("CREATE TABLE credits (credit_id TEXT PRIMARY KEY, game_id TEXT REFERENCES games(game_id), release_id TEXT REFERENCES releases(release_id), person_id TEXT REFERENCES people(person_id), role TEXT, role_as_printed TEXT, source_id TEXT NOT NULL REFERENCES source_items(source_item_id), confidence TEXT, payload TEXT NOT NULL)")
        con.execute("CREATE TABLE mentions (mention_id TEXT PRIMARY KEY, source_item_id TEXT NOT NULL REFERENCES source_items(source_item_id), entity_type TEXT, entity_id TEXT, role_as_printed TEXT, payload TEXT NOT NULL)")
        con.execute("CREATE TABLE media_assets (media_id TEXT PRIMARY KEY, source_item_id TEXT REFERENCES source_items(source_item_id), media_type TEXT, title TEXT, permission_status TEXT, payload TEXT NOT NULL)")
        con.execute("CREATE TABLE photo_identifications (photo_identification_id TEXT PRIMARY KEY, photo_id TEXT, media_id TEXT REFERENCES media_assets(media_id), source_item_id TEXT NOT NULL REFERENCES source_items(source_item_id), name_as_printed TEXT, role_as_printed TEXT, verification_status TEXT, payload TEXT NOT NULL)")
        con.execute("CREATE TABLE evidence (evidence_id TEXT PRIMARY KEY, source_item_id TEXT REFERENCES source_items(source_item_id), evidence_type TEXT, payload TEXT NOT NULL)")
        con.execute("CREATE TABLE north_east_connections (connection_id TEXT PRIMARY KEY, source_item_id TEXT, entity_type TEXT, entity_id TEXT, entity_name TEXT, status TEXT, public_visibility TEXT, payload TEXT NOT NULL)")

        con.execute("CREATE VIRTUAL TABLE source_items_fts USING fts5(title, summary, archive_url, content='source_items', content_rowid='rowid')")
        con.execute("CREATE VIRTUAL TABLE people_fts USING fts5(canonical_name, content='people', content_rowid='rowid')")
        con.execute("CREATE VIRTUAL TABLE games_fts USING fts5(canonical_title, content='games', content_rowid='rowid')")

        for row in read_jsonl(curated_dir / "publications.jsonl"):
            con.execute("INSERT INTO publications VALUES (?, ?, ?)", (row["publication_id"], row["canonical_title"], _json(row)))

        issue_ids: set[str] = set()
        for row in read_jsonl(curated_dir / "issues.jsonl"):
            issue_ids.add(row["issue_id"])
            con.execute(
                "INSERT INTO issues VALUES (?, ?, ?, ?, ?, ?)",
                (
                    row["issue_id"],
                    row["publication_id"],
                    row.get("issue_number", ""),
                    row.get("cover_date", ""),
                    row.get("date_precision", ""),
                    _json(row),
                ),
            )

        for row in read_jsonl(curated_dir / "source-items.jsonl"):
            issue_id = row.get("issue_id", "") or None
            if issue_id and issue_id not in issue_ids:
                issue_id = None
            con.execute(
                "INSERT INTO source_items VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    row["source_item_id"],
                    row["publication_id"],
                    issue_id,
                    row["item_type"],
                    row["title"],
                    row.get("archive_url", ""),
                    row.get("summary", ""),
                    _json(row),
                ),
            )
            rowid = con.execute("SELECT rowid FROM source_items WHERE source_item_id = ?", (row["source_item_id"],)).fetchone()[0]
            con.execute(
                "INSERT INTO source_items_fts(rowid, title, summary, archive_url) VALUES (?, ?, ?, ?)",
                (rowid, row["title"], row.get("summary", ""), row.get("archive_url", "")),
            )

        for row in read_jsonl(curated_dir / "people.jsonl"):
            con.execute(
                "INSERT INTO people VALUES (?, ?, ?, ?)",
                (row["person_id"], row["canonical_name"], row.get("evidence_status", ""), _json(row)),
            )
            rowid = con.execute("SELECT rowid FROM people WHERE person_id = ?", (row["person_id"],)).fetchone()[0]
            con.execute("INSERT INTO people_fts(rowid, canonical_name) VALUES (?, ?)", (rowid, row["canonical_name"]))

        for row in read_jsonl(curated_dir / "organisations.jsonl"):
            con.execute(
                "INSERT INTO organisations VALUES (?, ?, ?, ?, ?)",
                (
                    row["organisation_id"],
                    row["canonical_name"],
                    row.get("organisation_type", ""),
                    row.get("evidence_status", ""),
                    _json(row),
                ),
            )

        for row in read_jsonl(curated_dir / "games.jsonl"):
            con.execute("INSERT INTO games VALUES (?, ?, ?)", (row["game_id"], row["canonical_title"], _json(row)))
            rowid = con.execute("SELECT rowid FROM games WHERE game_id = ?", (row["game_id"],)).fetchone()[0]
            con.execute("INSERT INTO games_fts(rowid, canonical_title) VALUES (?, ?)", (rowid, row["canonical_title"]))

        for row in read_jsonl(curated_dir / "releases.jsonl"):
            con.execute(
                "INSERT INTO releases VALUES (?, ?, ?, ?, ?, ?)",
                (
                    row["release_id"],
                    row["game_id"],
                    row.get("platform_id", ""),
                    row.get("release_title", ""),
                    row.get("evidence_status", ""),
                    _json(row),
                ),
            )

        for row in read_jsonl(curated_dir / "credits.jsonl"):
            con.execute(
                "INSERT INTO credits VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    row["credit_id"],
                    row.get("game_id", "") or None,
                    row.get("release_id", "") or None,
                    row.get("person_id", "") or None,
                    row.get("role", ""),
                    row.get("role_as_printed", ""),
                    row["source_id"],
                    row.get("confidence", ""),
                    _json(row),
                ),
            )

        for row in read_jsonl(curated_dir / "mentions.jsonl"):
            con.execute(
                "INSERT INTO mentions VALUES (?, ?, ?, ?, ?, ?)",
                (
                    row["mention_id"],
                    row["source_item_id"],
                    row.get("entity_type", ""),
                    row.get("entity_id", ""),
                    row.get("role_as_printed", ""),
                    _json(row),
                ),
            )

        for row in read_jsonl(curated_dir / "media-assets.jsonl"):
            con.execute(
                "INSERT INTO media_assets VALUES (?, ?, ?, ?, ?, ?)",
                (
                    row["media_id"],
                    row.get("source_item_id", "") or None,
                    row.get("media_type", ""),
                    row.get("title", ""),
                    row.get("permission_status", ""),
                    _json(row),
                ),
            )

        for row in read_jsonl(curated_dir / "photo-identifications.jsonl"):
            con.execute(
                "INSERT INTO photo_identifications VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    row["photo_identification_id"],
                    row.get("photo_id", ""),
                    row.get("media_id", "") or None,
                    row["source_item_id"],
                    row.get("name_as_printed", ""),
                    row.get("role_as_printed", ""),
                    row.get("verification_status", ""),
                    _json(row),
                ),
            )

        for row in read_jsonl(curated_dir / "evidence.jsonl"):
            con.execute(
                "INSERT INTO evidence VALUES (?, ?, ?, ?)",
                (row["evidence_id"], row.get("source_item_id", "") or None, row.get("evidence_type", ""), _json(row)),
            )

        for row in read_jsonl(curated_dir / "north-east-connections.jsonl"):
            con.execute(
                "INSERT INTO north_east_connections VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    row["connection_id"],
                    row.get("source_item_id", ""),
                    row["entity_type"],
                    row["entity_id"],
                    row["entity_name"],
                    row["status"],
                    row["public_visibility"],
                    _json(row),
                ),
            )

        con.execute("CREATE INDEX idx_source_items_publication ON source_items(publication_id)")
        con.execute("CREATE INDEX idx_credits_person ON credits(person_id)")
        con.execute("CREATE INDEX idx_credits_game ON credits(game_id)")
        con.execute("CREATE INDEX idx_photo_name ON photo_identifications(name_as_printed)")
        con.execute("CREATE INDEX idx_ne_status ON north_east_connections(status)")
        con.commit()
    finally:
        con.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Build deterministic SQLite database from canonical JSONL.")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    args = parser.parse_args()
    build_database(CURATED_DIR, Path(args.db))
    print(Path(args.db))


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from typing import Any

from .common import CURATED_DIR, ROOT, read_jsonl

DEFAULT_DB = ROOT / "build" / "video-game-history.sqlite"
SCHEMA_VERSION = 1


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
        con.execute("CREATE TABLE source_items (source_item_id TEXT PRIMARY KEY, publication_id TEXT NOT NULL REFERENCES publications(publication_id), issue_id TEXT, item_type TEXT NOT NULL, title TEXT NOT NULL, archive_url TEXT, summary TEXT, payload TEXT NOT NULL)")
        con.execute("CREATE TABLE evidence (evidence_id TEXT PRIMARY KEY, source_item_id TEXT REFERENCES source_items(source_item_id), evidence_type TEXT, payload TEXT NOT NULL)")
        con.execute("CREATE TABLE north_east_connections (connection_id TEXT PRIMARY KEY, source_item_id TEXT, entity_type TEXT, entity_id TEXT, entity_name TEXT, status TEXT, public_visibility TEXT, payload TEXT NOT NULL)")
        con.execute("CREATE VIRTUAL TABLE source_items_fts USING fts5(title, summary, archive_url, content='source_items', content_rowid='rowid')")
        for row in read_jsonl(curated_dir / "publications.jsonl"):
            con.execute("INSERT INTO publications VALUES (?, ?, ?)", (row["publication_id"], row["canonical_title"], _json(row)))
        issue_ids = set()
        for row in read_jsonl(curated_dir / "issues.jsonl"):
            issue_ids.add(row["issue_id"])
            con.execute("INSERT INTO issues VALUES (?, ?, ?, ?, ?, ?)", (row["issue_id"], row["publication_id"], row.get("issue_number", ""), row.get("cover_date", ""), row.get("date_precision", ""), _json(row)))
        for row in read_jsonl(curated_dir / "source-items.jsonl"):
            issue_id = row.get("issue_id", "")
            if issue_id and issue_id not in issue_ids:
                issue_id = ""
            con.execute("INSERT INTO source_items VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (row["source_item_id"], row["publication_id"], issue_id, row["item_type"], row["title"], row.get("archive_url", ""), row.get("summary", ""), _json(row)))
            rowid = con.execute("SELECT rowid FROM source_items WHERE source_item_id = ?", (row["source_item_id"],)).fetchone()[0]
            con.execute("INSERT INTO source_items_fts(rowid, title, summary, archive_url) VALUES (?, ?, ?, ?)", (rowid, row["title"], row.get("summary", ""), row.get("archive_url", "")))
        for row in read_jsonl(curated_dir / "evidence.jsonl"):
            con.execute("INSERT INTO evidence VALUES (?, ?, ?, ?)", (row["evidence_id"], row.get("source_item_id", "") or None, row.get("evidence_type", ""), _json(row)))
        for row in read_jsonl(curated_dir / "north-east-connections.jsonl"):
            con.execute("INSERT INTO north_east_connections VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (row["connection_id"], row.get("source_item_id", ""), row["entity_type"], row["entity_id"], row["entity_name"], row["status"], row["public_visibility"], _json(row)))
        con.execute("CREATE INDEX idx_source_items_publication ON source_items(publication_id)")
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

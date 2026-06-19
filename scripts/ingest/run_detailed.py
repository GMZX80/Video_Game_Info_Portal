from __future__ import annotations

import argparse
import sqlite3
from datetime import date

from . import sinclair_user, stairway
from .build_sqlite import DEFAULT_DB, build_database
from .classify_north_east import classify
from .common import CURATED_DIR, REPORTS_DIR, ROOT
from .export_public_json import export_public_json
from .normalise import normalise
from .validate_data import validate_repository
from scripts.reconcile_entities import reconcile


def _write_report(sinclair: dict[str, int], stairway_counts: dict[str, int], normalised: dict[str, int]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Detailed Sinclair User and Stairway To Hell ingest",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        "## Sinclair User",
        "",
        f"- Issues represented: {sinclair.get('issues', 0)}",
        f"- Issue pages fetched: {sinclair.get('issue_pages_fetched', 0)}",
        f"- Article pages discovered: {sinclair.get('article_pages_discovered', 0)}",
        f"- Article pages fetched: {sinclair.get('article_pages_fetched', 0)}",
        f"- Source items: {sinclair.get('source_items', 0)}",
        f"- Failures: {sinclair.get('failures', 0)}",
        "",
        "## Stairway To Hell",
        "",
        f"- Pages fetched: {stairway_counts.get('pages_fetched', 0)}",
        f"- Pages pending because of a limit: {stairway_counts.get('pages_discovered', 0)}",
        f"- Source items: {stairway_counts.get('source_items', 0)}",
        f"- Photograph-caption testimonies: {stairway_counts.get('photo_identifications', 0)}",
        f"- Download links excluded: {stairway_counts.get('excluded_binary_links', 0)}",
        f"- Failures: {stairway_counts.get('failures', 0)}",
        "",
        "## Canonical output",
        "",
        f"- Source items: {normalised.get('source_items', 0)}",
        f"- People named in sources: {normalised.get('people', 0)}",
        f"- Explicit source-linked credits: {normalised.get('credits', 0)}",
        f"- Photograph-caption testimonies: {normalised.get('photo_identifications', 0)}",
        "",
        "The repository stores structured metadata and source locators rather than complete articles or software files.",
    ]
    (REPORTS_DIR / "deep-ingest-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(*, resume: bool, max_pages: int, include_catalogues: bool) -> dict[str, object]:
    sinclair = sinclair_user.run(indexes_only=False, resume=resume, max_pages=max_pages)
    stairway_counts = stairway.run(
        indexes_only=False,
        resume=resume,
        max_pages=max_pages,
        include_catalogues=include_catalogues,
    )
    normalised = normalise()
    classified = classify()
    reconciled = reconcile()
    build_database(CURATED_DIR, DEFAULT_DB)
    exported = export_public_json()
    validation_failures = validate_repository(ROOT)
    _write_report(sinclair, stairway_counts, normalised)
    if validation_failures:
        raise SystemExit("\n".join(validation_failures))
    connection = sqlite3.connect(DEFAULT_DB)
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        connection.close()
    return {
        "sinclair_user": sinclair,
        "stairway": stairway_counts,
        "normalise": normalised,
        "classify": classified,
        "reconcile": reconciled,
        "export": exported,
        "sqlite_integrity": integrity,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run detailed Sinclair User and Stairway To Hell metadata capture.")
    parser.add_argument("--resume", action="store_true", help="Reuse cached responses where available.")
    parser.add_argument("--max-pages", type=int, default=0, help="Optional per-archive page limit; zero means no limit.")
    parser.add_argument("--include-catalogues", action="store_true", help="Include Stairway BBC and Electron HTML catalogue pages.")
    args = parser.parse_args()
    print(run(resume=args.resume, max_pages=args.max_pages, include_catalogues=args.include_catalogues))


if __name__ == "__main__":
    main()

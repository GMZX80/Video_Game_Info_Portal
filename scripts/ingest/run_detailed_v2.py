from __future__ import annotations

import argparse
import sqlite3
from datetime import date

from scripts.reconcile_entities import reconcile

from . import sinclair_supplement, sinclair_user, stairway, stairway_supplement
from .build_sqlite import DEFAULT_DB, build_database
from .classify_north_east import classify
from .common import CURATED_DIR, REPORTS_DIR, ROOT
from .export_public_json import export_public_json
from .normalise import normalise
from .validate_data import validate_repository


def _write_report(results: dict[str, object]) -> None:
    sinclair = results["sinclair_user"]
    sinclair_extra = results["sinclair_supplement"]
    stairway_counts = results["stairway"]
    stairway_extra = results["stairway_supplement"]
    normalised = results["normalise"]
    physical_issues = sinclair_extra.get("physical_issue_pages_discovered", sinclair.get("issues", 0))
    lines = [
        "# Detailed Sinclair User and Stairway To Hell ingest",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        "## Sinclair User",
        f"- Physical issue pages discovered: {physical_issues}",
        f"- Previously omitted issues added: {sinclair_extra.get('issues_added', 0)}",
        f"- Article pages fetched: {sinclair.get('article_pages_fetched', 0)}",
        f"- Unlinked software entries added: {sinclair_extra.get('unlinked_software_entries_added', 0)}",
        f"- Type-in titles added: {sinclair_extra.get('typein_entries_added', 0)}",
        f"- Remaining failures: {sinclair_extra.get('failures', 0)}",
        "",
        "## Stairway To Hell",
        f"- Pages fetched: {stairway_counts.get('pages_fetched', 0)}",
        f"- Pages pending because of a page limit: {stairway_extra.get('pages_pending', 0)}",
        f"- Source items after cleanup: {stairway_extra.get('source_items', 0)}",
        f"- Photograph-caption testimonies: {stairway_extra.get('photo_identifications', 0)}",
        f"- Catalogue navigation rows removed: {stairway_extra.get('catalogue_navigation_rows_removed', 0)}",
        f"- Download directories reclassified: {stairway_extra.get('download_directories_reclassified', 0)}",
        f"- Remaining failures: {stairway_extra.get('remaining_failures', 0)}",
        "",
        "## Canonical output",
        f"- Source items: {normalised.get('source_items', 0)}",
        f"- Games: {normalised.get('games', 0)}",
        f"- Releases: {normalised.get('releases', 0)}",
        f"- People named in sources: {normalised.get('people', 0)}",
        f"- Explicit source-linked credits: {normalised.get('credits', 0)}",
        f"- Photograph-caption testimonies: {normalised.get('photo_identifications', 0)}",
        f"- Media metadata records: {results.get('curated_media', 0)}",
        "",
        "Only structured metadata and source locators are retained.",
    ]
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "deep-ingest-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(*, resume: bool, max_pages: int, include_catalogues: bool) -> dict[str, object]:
    accessed_at = date.today().isoformat()
    sinclair = sinclair_user.run(
        indexes_only=False,
        resume=resume,
        accessed_at=accessed_at,
        max_pages=max_pages,
    )
    sinclair_extra = sinclair_supplement.supplement(accessed_at=accessed_at)
    stairway_counts = stairway.run(
        indexes_only=False,
        resume=resume,
        accessed_at=accessed_at,
        max_pages=max_pages,
        include_catalogues=include_catalogues,
    )
    stairway_extra = stairway_supplement.supplement(accessed_at=accessed_at)
    normalised = normalise()
    curated_media = stairway_supplement.merge_curated_media()
    classified = classify()
    reconciled = reconcile()
    build_database(CURATED_DIR, DEFAULT_DB)
    exported = export_public_json()
    validation_failures = validate_repository(ROOT)
    results = {
        "sinclair_user": sinclair,
        "sinclair_supplement": sinclair_extra,
        "stairway": stairway_counts,
        "stairway_supplement": stairway_extra,
        "normalise": normalised,
        "curated_media": curated_media,
        "classify": classified,
        "reconcile": reconciled,
        "export": exported,
    }
    _write_report(results)
    if validation_failures:
        raise SystemExit("\n".join(validation_failures))
    connection = sqlite3.connect(DEFAULT_DB)
    try:
        results["sqlite_integrity"] = connection.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        connection.close()
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the supplemented detailed archive metadata capture.")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-pages", type=int, default=0)
    parser.add_argument("--include-catalogues", action="store_true")
    args = parser.parse_args()
    print(run(resume=args.resume, max_pages=args.max_pages, include_catalogues=args.include_catalogues))


if __name__ == "__main__":
    main()

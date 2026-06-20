from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path

from scripts.ingest import crash, globalnet, sinclair_user, zzap64
from scripts.ingest.build_sqlite import DEFAULT_DB, build_database
from scripts.ingest.classify_north_east import classify
from scripts.ingest.common import CURATED_DIR, RAW_DIR, REPORTS_DIR, ROOT, read_jsonl, write_jsonl
from scripts.ingest.export_public_json import export_public_json
from scripts.ingest.local_credit_graph import manual_mobygames_rows_to_assertions, manual_mobygames_rows_to_source_items
from scripts.ingest.normalise import normalise
from scripts.ingest.validate_data import validate_repository
from scripts.reconcile_external_entities import reconcile_external_entities
from scripts.reconcile_entities import reconcile


def _write_empty_csv(path: Path, fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()


def _write_reports(fetch_counts: dict[str, dict[str, int]], normalise_counts: dict[str, int], classify_counts: dict[str, int]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Magazine Datastore Ingest Summary",
        "",
        "Generated: 2026-06-18",
        "",
        "| Archive | Issues | Source items | Games/type-ins |",
        "| --- | ---: | ---: | ---: |",
    ]
    for archive in sorted(fetch_counts):
        counts = fetch_counts[archive]
        lines.append(f"| {archive} | {counts.get('issues', 0)} | {counts.get('source_items', 0)} | {counts.get('games', counts.get('typeins', 0))} |")
    lines.extend([
        "",
        f"Canonical issues: {normalise_counts.get('issues', 0)}",
        f"Canonical source items: {normalise_counts.get('source_items', 0)}",
        f"Canonical games: {normalise_counts.get('games', 0)}",
        f"Canonical releases: {normalise_counts.get('releases', 0)}",
        f"North East candidates: {classify_counts.get('candidates', 0)}",
        f"Verified/strongly supported North East connections: {classify_counts.get('confirmed', 0)}",
        "",
        "Images, scans, complete article text, complete listings and long quotations were not copied.",
    ])
    (REPORTS_DIR / "ingest-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    coverage = [
        "# Site Coverage",
        "",
        "Normal CI validates committed canonical JSONL and generated public JSON. External archive crawling is manual.",
        "",
        "- Sinclair User: contents/index metadata via SUMO.",
        "- CRASH: root issue list plus issue index pages.",
        "- Zzap!64: ZzapBible first game-index page plus review/feature link indexes; `/fullissues` is not crawled.",
        "- Globalnet: SPOT plain data zip and TTFn Sinclair User type-in table.",
        "",
        "Known gap: broad review coverage is index-level where archive pages do not expose structured data without deeper article inspection.",
    ]
    (REPORTS_DIR / "site-coverage.md").write_text("\n".join(coverage) + "\n", encoding="utf-8")
    (REPORTS_DIR / "copyright-and-rights-notes.md").write_text(
        "# Copyright And Rights Notes\n\n"
        "This repository stores bibliographic metadata, short summaries and source locators. "
        "It does not store full article transcriptions, full review bodies, complete type-in listings, magazine scans, screenshots or copied advertisements.\n",
        encoding="utf-8",
    )
    _write_empty_csv(REPORTS_DIR / "parse-failures.csv", ["archive", "url", "reason"])
    _write_empty_csv(REPORTS_DIR / "unresolved-credits.csv", ["source_item_id", "title", "reason"])


def _build_manual_mobygames_import(generated_at: str = "2026-06-20") -> dict[str, int]:
    assertions = manual_mobygames_rows_to_assertions(
        ROOT / "data" / "manual" / "mobygames-person-credit-import.csv",
        generated_at=generated_at,
    )
    source_items = manual_mobygames_rows_to_source_items(
        ROOT / "data" / "manual" / "mobygames-person-credit-import.csv",
        generated_at=generated_at,
    )
    raw_dir = RAW_DIR / "mobygames-manual"
    write_jsonl(raw_dir / "source-items.jsonl", source_items, sort_key="source_item_id")
    write_jsonl(raw_dir / "source-assertions.jsonl", assertions, sort_key="assertion_id")
    for file_name in ["issues.jsonl", "external-identifiers.jsonl"]:
        path = raw_dir / file_name
        if not path.exists():
            write_jsonl(path, [])
    return {"source_items": len(source_items), "source_assertions": len(assertions)}


def build_all(skip_fetch: bool = False, resume: bool = False) -> dict[str, object]:
    manual_import_counts = _build_manual_mobygames_import()
    fetch_counts: dict[str, dict[str, int]] = {}
    if not skip_fetch:
        fetch_counts["sinclair-user"] = sinclair_user.run(indexes_only=True, resume=resume)
        fetch_counts["crash"] = crash.run(indexes_only=True, resume=resume)
        fetch_counts["zzap64"] = zzap64.run(indexes_only=True, resume=resume)
        fetch_counts["globalnet"] = globalnet.run(indexes_only=True, resume=resume)
    else:
        for archive_dir in RAW_DIR.glob("*"):
            if archive_dir.is_dir():
                fetch_counts[archive_dir.name] = {
                    "issues": len(read_jsonl(archive_dir / "issues.jsonl")),
                    "source_items": len(read_jsonl(archive_dir / "source-items.jsonl")),
                }
    normalise_counts = normalise()
    classify_counts = classify()
    reconcile_counts = reconcile()
    external_reconcile_counts = reconcile_external_entities()
    build_database(CURATED_DIR, DEFAULT_DB)
    export_counts = export_public_json()
    failures = validate_repository(ROOT)
    _write_reports(fetch_counts, normalise_counts, classify_counts)
    if failures:
        for failure in failures:
            print(failure)
        raise SystemExit(1)
    con = sqlite3.connect(DEFAULT_DB)
    try:
        integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        con.close()
    return {
        "fetch": fetch_counts,
        "normalise": normalise_counts,
        "manual_mobygames_import": manual_import_counts,
        "classify": classify_counts,
        "reconcile": reconcile_counts,
        "external_reconcile": external_reconcile_counts,
        "export": export_counts,
        "sqlite_integrity": integrity,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the datastore ingest/build/export validation pipeline.")
    parser.add_argument("--skip-fetch", action="store_true", help="Use committed raw JSONL and do not crawl external archives.")
    parser.add_argument("--resume", action="store_true", help="Reuse cached external responses where possible.")
    args = parser.parse_args()
    print(build_all(skip_fetch=args.skip_fetch, resume=args.resume))


if __name__ == "__main__":
    main()

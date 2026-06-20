from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
CURATED_DIR = ROOT / "data" / "curated"
REPORTS_DIR = ROOT / "reports"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSONL: {exc}") from exc
    return rows


EXPORT_DIR = ROOT / "data" / "google-sheet-export"
GENERATED_AT = date.today().isoformat()
BATCH_NAME = f"repo-curated-jsonl-export-{GENERATED_AT}"

GAME_HEADERS = [
    "Game_Record_ID",
    "Game Title",
    "Series / Franchise",
    "Platform / Release",
    "Release Year / Date",
    "Developer / Studio as printed",
    "Publisher / Label as printed",
    "UK development role",
    "UK city / region",
    "People / credits captured",
    "People / credits pending",
    "Primary source system",
    "Primary source URL",
    "Secondary source system",
    "Secondary source URL",
    "Evidence status",
    "Review status",
    "Import batch",
    "Rights / access notes",
    "Notes",
]

PEOPLE_SUMMARY_HEADERS = [
    "Person",
    "Aliases",
    "Known / candidate UK studio links",
    "Games currently local",
    "Roles currently local",
    "Evidence status",
    "Source URL",
    "Gap / next action",
]

STUDIO_HEADERS = [
    "Studio / Publisher",
    "Type",
    "City/Region",
    "Country",
    "Active / Founded",
    "Representative games / relevance",
    "Evidence status",
    "Primary source URL",
    "Notes",
]

SOURCE_EVIDENCE_HEADERS = [
    "Source_Item_ID",
    "Source system",
    "Publication",
    "Issue",
    "Item type",
    "Title",
    "Date",
    "Machine",
    "Printed company",
    "Named contributors",
    "Archive URL",
    "Extraction status",
    "Rights / access notes",
    "Accessed at",
    "Content hash",
]

LOCAL_CREDIT_HEADERS = [
    "Credit_Record_ID",
    "Person",
    "Person_ID",
    "Game_Record_ID",
    "Game Title",
    "Release_ID",
    "Platform / Release",
    "Role",
    "Role as printed",
    "Original or conversion",
    "Employment status",
    "Evidence status",
    "Review status",
    "Source system",
    "Source URL",
    "Source item ID",
    "Confidence",
    "Notes",
]

SOURCE_ASSERTION_HEADERS = [
    "Assertion_ID",
    "Source system",
    "Subject type",
    "Subject",
    "Predicate",
    "Object type",
    "Object as printed",
    "Platform as printed",
    "Date as printed",
    "Evidence status",
    "Assertion status",
    "Public claim status",
    "Source URL",
    "Permanent URL",
    "License",
    "Attribution required",
    "Notes",
    "Source item ID",
]

IMPORT_LOG_HEADERS = ["Timestamp", "Batch", "Action", "Rows", "Source", "Notes"]
RECONCILIATION_HEADERS = ["Issue_ID", "Severity", "Status", "Entity", "Source", "Notes"]
PLATFORM_ALIAS_HEADERS = ["Platform_ID", "Name", "Alias", "Notes"]
ALIAS_HEADERS = ["Entity_ID", "Canonical name", "Alias", "Source URL", "Evidence status", "Notes"]
ENRICHMENT_HEADERS = [
    "Record_ID",
    "Title",
    "Platform",
    "Source system",
    "Source URL",
    "Evidence status",
    "Review status",
    "Notes",
]


PUBLICATION_LABELS = {
    "publication:crash": "CRASH",
    "publication:mobygames-api": "MobyGames API",
    "publication:sinclair-user": "Sinclair User",
    "publication:spot-on": "SPOT*On / GlobalNet",
    "publication:stairway-to-hell": "Stairway To Hell",
    "publication:ttfn": "The Type Fantastic / GlobalNet",
    "publication:wikidata": "Wikidata",
    "publication:wikipedia": "Wikipedia",
    "publication:world-of-spectrum": "World of Spectrum",
    "publication:zxdb": "ZXDB",
    "publication:zxinfo": "ZXInfo",
    "publication:zzap64": "Zzap!64",
}

MAGAZINE_PUBLICATIONS = {
    "publication:crash",
    "publication:sinclair-user",
    "publication:zzap64",
    "publication:ttfn",
}

NOISY_TITLE_STOPLIST = {
    "and",
    "found",
    "links",
    "lost",
    "related",
    "re-release",
    "renamed",
    "titles",
    "unknown",
    "way",
    "working",
}


@dataclass(frozen=True)
class DataStore:
    games: list[dict[str, Any]]
    releases: list[dict[str, Any]]
    credits: list[dict[str, Any]]
    people: list[dict[str, Any]]
    organisations: list[dict[str, Any]]
    source_items: list[dict[str, Any]]
    source_assertions: list[dict[str, Any]]
    issues: list[dict[str, Any]]
    platforms: list[dict[str, Any]]


def _text(value: Any, *, limit: int = 500) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        value = "; ".join(str(item) for item in value if item not in {None, ""})
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1].rstrip()}..."


def _join(values: Iterable[Any], *, limit: int = 8, text_limit: int = 500) -> str:
    seen: list[str] = []
    for value in values:
        text = _text(value)
        if text and text not in seen:
            seen.append(text)
    if len(seen) > limit:
        shown = seen[:limit]
        shown.append(f"+{len(seen) - limit} more")
        return _text("; ".join(shown), limit=text_limit)
    return _text("; ".join(seen), limit=text_limit)


def _looks_like_title(value: Any) -> bool:
    title = _text(value)
    lowered = title.casefold()
    if not title or lowered in NOISY_TITLE_STOPLIST:
        return False
    if any(ord(char) < 32 for char in title):
        return False
    if len(re.sub(r"[^A-Za-z0-9]", "", title)) < 2:
        return False
    if re.match(r"^[,;:.]", title):
        return False
    if lowered.endswith(" by") or lowered.endswith(" maintained") or lowered.startswith("games for "):
        return False
    return True


def _should_export_game(game: dict[str, Any], sources: list[dict[str, Any]], releases: list[dict[str, Any]]) -> bool:
    if not _looks_like_title(game.get("canonical_title", "")):
        return False
    if releases:
        return True
    if not sources:
        return False
    primary = sources[0]
    publication_id = str(primary.get("publication_id", ""))
    source_item_id = str(primary.get("source_item_id", ""))
    item_type = str(primary.get("item_type", ""))
    if publication_id in {"publication:spot-on", "publication:ttfn", "publication:zzap64"}:
        return True
    if "stairway-lost" in source_item_id:
        return False
    if item_type in {"review", "type-in program", "game catalogue entry"}:
        return True
    if item_type == "index-only entry" and (
        primary.get("machine") or primary.get("printed_company") or primary.get("program_type") or primary.get("named_contributors")
    ):
        return True
    return False


def _load() -> DataStore:
    return DataStore(
        games=read_jsonl(CURATED_DIR / "games.jsonl"),
        releases=read_jsonl(CURATED_DIR / "releases.jsonl"),
        credits=read_jsonl(CURATED_DIR / "credits.jsonl"),
        people=read_jsonl(CURATED_DIR / "people.jsonl"),
        organisations=read_jsonl(CURATED_DIR / "organisations.jsonl"),
        source_items=read_jsonl(CURATED_DIR / "source-items.jsonl"),
        source_assertions=read_jsonl(CURATED_DIR / "source-assertions.jsonl"),
        issues=read_jsonl(CURATED_DIR / "issues.jsonl"),
        platforms=read_jsonl(CURATED_DIR / "platforms.jsonl"),
    )


def _write_csv(path: Path, headers: list[str], rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({header: _text(row.get(header, "")) for header in headers})
            count += 1
    return count


def _write_chunked_csv(path_stem: str, headers: list[str], rows: list[dict[str, Any]], *, chunk_size: int = 1000) -> int:
    for stale in EXPORT_DIR.glob(f"{path_stem}_part_*.csv"):
        stale.unlink()
    header_path = EXPORT_DIR / f"{path_stem}_header.csv"
    _write_csv(header_path, headers, [])
    parts = 0
    for index in range(0, len(rows), chunk_size):
        chunk = rows[index : index + chunk_size]
        part_path = EXPORT_DIR / f"{path_stem}_part_{parts + 1:03d}.csv"
        with part_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore", lineterminator="\n")
            for row in chunk:
                writer.writerow({header: _text(row.get(header, "")) for header in headers})
        parts += 1
    return parts


def _source_system(source: dict[str, Any] | None) -> str:
    if not source:
        return ""
    return PUBLICATION_LABELS.get(str(source.get("publication_id", "")), str(source.get("publication_id", "")))


def _evidence_status(source: dict[str, Any] | None) -> str:
    if not source:
        return "Candidate / unresolved"
    publication_id = str(source.get("publication_id", ""))
    if publication_id == "publication:wikipedia":
        return "Title-only seed"
    if publication_id in MAGAZINE_PUBLICATIONS:
        return "Confirmed from contemporary magazine evidence"
    if publication_id in {"publication:world-of-spectrum", "publication:zxdb", "publication:zxinfo", "publication:mobygames-api"}:
        return "Confirmed from official API"
    return "Secondary database evidence"


def _platform_hint(game: dict[str, Any], releases: list[dict[str, Any]], source: dict[str, Any] | None, platform_names: dict[str, str]) -> str:
    platforms = [platform_names.get(row.get("platform_id", ""), row.get("platform_id", "")) for row in releases]
    if platforms:
        return _join(platforms)
    machine = _text((source or {}).get("machine", ""))
    if machine:
        return machine
    sources = game.get("sources", []) or []
    source_blob = " ".join(str(item) for item in sources)
    if "globalnet-spot" in source_blob or "globalnet-ttfn" in source_blob or "sinclair-user" in source_blob or "crash" in source_blob:
        return "ZX Spectrum / Sinclair family"
    if "stairway" in source_blob:
        return "BBC Micro / Acorn Electron"
    if "zzap64" in source_blob:
        return "Commodore 64"
    return ""


def _build_game_rows(data: DataStore) -> list[dict[str, Any]]:
    source_by_id = {row["source_item_id"]: row for row in data.source_items}
    platform_names = {row["platform_id"]: row.get("name", row["platform_id"]) for row in data.platforms}
    releases_by_game: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for release in data.releases:
        releases_by_game[release.get("game_id", "")].append(release)
    credits_by_game: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for credit in data.credits:
        credits_by_game[credit.get("game_id", "")].append(credit)
    people_by_id = {row["person_id"]: row for row in data.people}
    rows: list[dict[str, Any]] = []
    for game in sorted(data.games, key=lambda row: str(row.get("canonical_title", "")).casefold()):
        source_ids = [str(item) for item in game.get("sources", []) or []]
        sources = [source_by_id[item] for item in source_ids if item in source_by_id]
        primary = sources[0] if sources else None
        secondary = sources[1] if len(sources) > 1 else None
        releases = releases_by_game.get(game.get("game_id", ""), [])
        if sources and all(source.get("publication_id") == "publication:wikipedia" for source in sources):
            continue
        if not _should_export_game(game, sources, releases):
            continue
        credits = credits_by_game.get(game.get("game_id", ""), [])
        captured = [
            people_by_id.get(credit.get("person_id", ""), {}).get("canonical_name", credit.get("person_id", ""))
            for credit in credits
        ]
        rows.append(
            {
                "Game_Record_ID": game.get("game_id", ""),
                "Game Title": game.get("canonical_title", ""),
                "Series / Franchise": game.get("series", ""),
                "Platform / Release": _platform_hint(game, releases, primary, platform_names),
                "Release Year / Date": game.get("initial_release_date", "") or _join(row.get("date", "") for row in releases),
                "Developer / Studio as printed": _join(row.get("developer", "") for row in releases),
                "Publisher / Label as printed": _join(
                    row.get("publisher", "") or row.get("label", "") for row in releases
                ),
                "UK development role": "Local repository source record; do not infer development role from publisher/label",
                "UK city / region": "Unknown unless sourced",
                "People / credits captured": _join(captured, limit=5) if captured else "None captured at local credit-row level",
                "People / credits pending": "Needs reviewed person-credit import / source-page review",
                "Primary source system": _source_system(primary),
                "Primary source URL": (primary or {}).get("archive_url", ""),
                "Secondary source system": _source_system(secondary),
                "Secondary source URL": (secondary or {}).get("archive_url", ""),
                "Evidence status": _evidence_status(primary),
                "Review status": "Auto-imported",
                "Import batch": BATCH_NAME,
                "Rights / access notes": (primary or {}).get("rights_note", "Metadata only; no binaries, images, scans or long text copied."),
                "Notes": _text(
                    "Generated from data/curated/games.jsonl. Source IDs: " + _join(source_ids, limit=4),
                    limit=500,
                ),
            }
        )
    return rows


def _build_local_credit_rows(data: DataStore) -> list[dict[str, Any]]:
    source_by_id = {row["source_item_id"]: row for row in data.source_items}
    people_by_id = {row["person_id"]: row for row in data.people}
    game_by_id = {row["game_id"]: row for row in data.games}
    release_by_id = {row["release_id"]: row for row in data.releases}
    platform_names = {row["platform_id"]: row.get("name", row["platform_id"]) for row in data.platforms}
    rows: list[dict[str, Any]] = []
    for credit in sorted(data.credits, key=lambda row: str(row.get("credit_id", ""))):
        source = source_by_id.get(credit.get("source_id", ""))
        person = people_by_id.get(credit.get("person_id", ""))
        game = game_by_id.get(credit.get("game_id", ""))
        release = release_by_id.get(credit.get("release_id", ""))
        rows.append(
            {
                "Credit_Record_ID": credit.get("credit_id", ""),
                "Person": (person or {}).get("canonical_name", credit.get("person_id", "")),
                "Person_ID": credit.get("person_id", ""),
                "Game_Record_ID": credit.get("game_id", ""),
                "Game Title": (game or {}).get("canonical_title", ""),
                "Release_ID": credit.get("release_id", ""),
                "Platform / Release": platform_names.get((release or {}).get("platform_id", ""), ""),
                "Role": credit.get("role", ""),
                "Role as printed": credit.get("role_as_printed", ""),
                "Original or conversion": credit.get("original_or_conversion", ""),
                "Employment status": credit.get("employment_status", "not inferred from credit"),
                "Evidence status": "Candidate / unresolved",
                "Review status": "Needs manual review",
                "Source system": _source_system(source),
                "Source URL": (source or {}).get("archive_url", ""),
                "Source item ID": credit.get("source_id", ""),
                "Confidence": credit.get("confidence", ""),
                "Notes": credit.get("notes", "A source credit does not establish employment status."),
            }
        )
    return rows


def _build_people_summary_rows(data: DataStore, local_credit_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in local_credit_rows:
        grouped[row["Person_ID"]].append(row)
    people_by_id = {row["person_id"]: row for row in data.people}
    rows: list[dict[str, Any]] = []
    for person_id, credits in sorted(grouped.items(), key=lambda item: item[1][0]["Person"].casefold()):
        person = people_by_id.get(person_id, {})
        rows.append(
            {
                "Person": credits[0]["Person"],
                "Aliases": _join(person.get("aliases", []), limit=5),
                "Known / candidate UK studio links": "",
                "Games currently local": _join((row["Game Title"] for row in credits if row.get("Game Title")), limit=8),
                "Roles currently local": _join((row["Role as printed"] or row["Role"] for row in credits), limit=6),
                "Evidence status": "Candidate / unresolved",
                "Source URL": credits[0].get("Source URL", ""),
                "Gap / next action": "Review person-name parsing and source context before promoting beyond candidate/local rows.",
            }
        )
    return rows


def _build_studio_rows(data: DataStore) -> list[dict[str, Any]]:
    source_by_id = {row["source_item_id"]: row for row in data.source_items}
    rows: list[dict[str, Any]] = []
    for organisation in sorted(data.organisations, key=lambda row: str(row.get("canonical_name", "")).casefold()):
        name = _text(organisation.get("canonical_name", ""))
        if not name or name.isdigit():
            continue
        primary = None
        for source_id in organisation.get("sources", []) or []:
            if source_id in source_by_id:
                primary = source_by_id[source_id]
                break
        rows.append(
            {
                "Studio / Publisher": name,
                "Type": organisation.get("organisation_type", "printed company or label"),
                "City/Region": _join(organisation.get("locations", []), limit=3),
                "Country": "Unknown unless sourced",
                "Active / Founded": organisation.get("active_dates", ""),
                "Representative games / relevance": "",
                "Evidence status": "Candidate / unresolved",
                "Primary source URL": (primary or {}).get("archive_url", ""),
                "Notes": "Printed label/company evidence only; publisher, label and developer roles must be reviewed separately.",
            }
        )
    return rows


def _build_source_evidence_rows(data: DataStore) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in sorted(data.source_items, key=lambda row: str(row.get("source_item_id", ""))):
        contributors = []
        for contributor in source.get("named_contributors", []) or []:
            if isinstance(contributor, dict):
                contributors.append(
                    _join([contributor.get("name", ""), contributor.get("role_as_printed", "")], limit=2)
                )
            else:
                contributors.append(str(contributor))
        rows.append(
            {
                "Source_Item_ID": source.get("source_item_id", ""),
                "Source system": _source_system(source),
                "Publication": source.get("publication_id", ""),
                "Issue": source.get("issue_id", ""),
                "Item type": source.get("item_type", ""),
                "Title": source.get("title", ""),
                "Date": source.get("date", ""),
                "Machine": source.get("machine", ""),
                "Printed company": source.get("printed_company", ""),
                "Named contributors": _join(contributors, limit=8),
                "Archive URL": source.get("archive_url", ""),
                "Extraction status": source.get("extraction_status", ""),
                "Rights / access notes": source.get("rights_note", ""),
                "Accessed at": source.get("accessed_at", ""),
                "Content hash": source.get("content_hash", ""),
            }
        )
    return rows


def _build_source_assertion_rows(data: DataStore) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for assertion in sorted(data.source_assertions, key=lambda row: str(row.get("assertion_id", ""))):
        rows.append(
            {
                "Assertion_ID": assertion.get("assertion_id", ""),
                "Source system": assertion.get("source_system", ""),
                "Subject type": assertion.get("subject_type", ""),
                "Subject": assertion.get("subject_label_as_printed", ""),
                "Predicate": assertion.get("predicate", ""),
                "Object type": assertion.get("object_type", ""),
                "Object as printed": assertion.get("object_label_as_printed", ""),
                "Platform as printed": assertion.get("platform_as_printed", ""),
                "Date as printed": assertion.get("date_as_printed", ""),
                "Evidence status": "Title-only seed" if assertion.get("predicate") == "title_seed" else "Secondary database evidence",
                "Assertion status": assertion.get("assertion_status", ""),
                "Public claim status": assertion.get("public_claim_status", ""),
                "Source URL": assertion.get("source_url", ""),
                "Permanent URL": assertion.get("permanent_url", ""),
                "License": assertion.get("license", ""),
                "Attribution required": assertion.get("attribution_required", ""),
                "Notes": assertion.get("notes", ""),
                "Source item ID": assertion.get("source_item_id", ""),
            }
        )
    return rows


def _build_reconciliation_rows(data: DataStore) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for issue in sorted(data.issues, key=lambda row: str(row.get("issue_id", ""))):
        rows.append(
            {
                "Issue_ID": issue.get("issue_id", ""),
                "Severity": "Review",
                "Status": "Open",
                "Entity": issue.get("publication_id", ""),
                "Source": issue.get("index_url", "") or issue.get("source_url", ""),
                "Notes": issue.get("rights_notes", "Bibliographic/source issue metadata."),
            }
        )
    if not rows:
        rows.append(
            {
                "Issue_ID": "reconciliation:manual-review-queue",
                "Severity": "Review",
                "Status": "Open",
                "Entity": "repo reconciliation reports",
                "Source": "reports/reconciliation-queue-*.csv",
                "Notes": "Review generated reconciliation queues before promoting candidates.",
            }
        )
    return rows


def _build_alias_rows(rows: list[dict[str, Any]], id_key: str, name_key: str = "canonical_name") -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in rows:
        for alias in row.get("aliases", []) or []:
            result.append(
                {
                    "Entity_ID": row.get(id_key, ""),
                    "Canonical name": row.get(name_key, ""),
                    "Alias": alias,
                    "Source URL": "",
                    "Evidence status": row.get("evidence_status", "Candidate / unresolved"),
                    "Notes": "Alias exported from local curated JSONL; review before merging identities.",
                }
            )
    return result


def _build_platform_alias_rows(data: DataStore) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for platform in data.platforms:
        aliases = platform.get("aliases", []) or [""]
        for alias in aliases:
            rows.append(
                {
                    "Platform_ID": platform.get("platform_id", ""),
                    "Name": platform.get("name", ""),
                    "Alias": alias,
                    "Notes": "Local platform alias.",
                }
            )
    return rows


def _build_enrichment_rows(data: DataStore, *, group: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in data.source_items:
        publication_id = str(source.get("publication_id", ""))
        machine = str(source.get("machine", ""))
        include = False
        platform = machine
        if group == "bbc" and (publication_id == "publication:stairway-to-hell" or machine in {"BBC Micro", "Acorn Electron"}):
            include = True
            platform = machine or "BBC Micro / Acorn Electron"
        elif group == "c64" and (publication_id == "publication:zzap64" or machine == "Commodore 64"):
            include = True
            platform = machine or "Commodore 64"
        elif group == "wos" and publication_id in {"publication:world-of-spectrum", "publication:zxdb", "publication:zxinfo"}:
            include = True
            platform = machine or "ZX Spectrum"
        elif group == "magazine" and publication_id in MAGAZINE_PUBLICATIONS:
            include = True
            platform = machine
        if include:
            rows.append(
                {
                    "Record_ID": source.get("source_item_id", ""),
                    "Title": source.get("title", ""),
                    "Platform": platform,
                    "Source system": _source_system(source),
                    "Source URL": source.get("archive_url", ""),
                    "Evidence status": _evidence_status(source),
                    "Review status": "Auto-imported",
                    "Notes": "Metadata only; no binaries, images, scans or long text copied.",
                }
            )
    if group == "wos" and not rows:
        rows.append(
            {
                "Record_ID": "wos-api:pending",
                "Title": "World of Spectrum API enrichment pending",
                "Platform": "ZX Spectrum",
                "Source system": "World of Spectrum / ZXDB / ZXInfo",
                "Source URL": "https://worldofspectrum.org/using-the-api/software",
                "Evidence status": "Needs API review",
                "Review status": "Needs manual review",
                "Notes": "The live workbook contains quick-list rows; no additional WoS API rows are committed in local JSONL yet.",
            }
        )
    return sorted(rows, key=lambda row: (row["Source system"], row["Title"], row["Record_ID"]))


def _write_report(counts: dict[str, int]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Google Sheet Population Export",
        "",
        f"Generated: {GENERATED_AT}",
        "",
        "This export is designed for the live Google Sheet. It stores structured metadata only: no binaries, images, scans, full article text or long quotations.",
        "",
        "| CSV | Rows |",
        "| --- | ---: |",
    ]
    for name, count in sorted(counts.items()):
        lines.append(f"| `{name}` | {count} |")
    lines.extend(
        [
            "",
            "## MobyGames status",
            "",
            "No `MOBYGAMES_API_KEY` is stored in this repository. Use the official API adapter only; do not scrape MobyGames HTML. If the API cannot return person-credit coverage, use the reviewed manual CSV route in `data/manual/mobygames-person-credit-import.csv`.",
            "",
            "## Phil Scott status",
            "",
            "The generated local credit CSV does not create a Phil Scott game credit row because the curated local `credits.jsonl` contains no Phil Scott credit record. Existing Phil Scott evidence remains candidate/secondary until a permitted API or reviewed manual source supplies local rows.",
        ]
    )
    (REPORTS_DIR / "google-sheet-population.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def export() -> dict[str, int]:
    data = _load()
    game_rows = _build_game_rows(data)
    local_credit_rows = _build_local_credit_rows(data)
    people_rows = _build_people_summary_rows(data, local_credit_rows)
    studio_rows = _build_studio_rows(data)
    source_evidence_rows = _build_source_evidence_rows(data)
    source_assertion_rows = _build_source_assertion_rows(data)
    reconciliation_rows = _build_reconciliation_rows(data)

    counts = {
        "repo_games_master_import.csv": _write_csv(EXPORT_DIR / "repo_games_master_import.csv", GAME_HEADERS, game_rows),
        "repo_local_credits.csv": _write_csv(EXPORT_DIR / "repo_local_credits.csv", LOCAL_CREDIT_HEADERS, local_credit_rows),
        "repo_people_credits_import.csv": _write_csv(EXPORT_DIR / "repo_people_credits_import.csv", PEOPLE_SUMMARY_HEADERS, people_rows),
        "repo_studios_publishers_import.csv": _write_csv(EXPORT_DIR / "repo_studios_publishers_import.csv", STUDIO_HEADERS, studio_rows),
        "source_evidence.csv": _write_csv(EXPORT_DIR / "source_evidence.csv", SOURCE_EVIDENCE_HEADERS, source_evidence_rows),
        "source_assertions.csv": _write_csv(EXPORT_DIR / "source_assertions.csv", SOURCE_ASSERTION_HEADERS, source_assertion_rows),
        "import_log.csv": _write_csv(
            EXPORT_DIR / "import_log.csv",
            IMPORT_LOG_HEADERS,
            [
                {
                    "Timestamp": GENERATED_AT,
                    "Batch": BATCH_NAME,
                    "Action": "Exported repository curated JSONL for Google Sheet import",
                    "Rows": len(game_rows) + len(local_credit_rows) + len(source_evidence_rows) + len(source_assertion_rows),
                    "Source": "data/curated/*.jsonl",
                    "Notes": "Metadata only; no MobyGames HTML scraping; person credits remain source-linked candidates unless reviewed.",
                },
                {
                    "Timestamp": GENERATED_AT,
                    "Batch": "mobygames-api",
                    "Action": "Checked repository/API route",
                    "Rows": 0,
                    "Source": "scripts/ingest/mobygames_api.py",
                    "Notes": "Requires MOBYGAMES_API_KEY; current export uses no live API key.",
                },
            ],
        ),
        "reconciliation_issues.csv": _write_csv(EXPORT_DIR / "reconciliation_issues.csv", RECONCILIATION_HEADERS, reconciliation_rows),
        "platform_aliases.csv": _write_csv(EXPORT_DIR / "platform_aliases.csv", PLATFORM_ALIAS_HEADERS, _build_platform_alias_rows(data)),
        "publisher_aliases.csv": _write_csv(EXPORT_DIR / "publisher_aliases.csv", ALIAS_HEADERS, _build_alias_rows(data.organisations, "organisation_id")),
        "people_aliases.csv": _write_csv(EXPORT_DIR / "people_aliases.csv", ALIAS_HEADERS, _build_alias_rows(data.people, "person_id")),
        "game_title_aliases.csv": _write_csv(EXPORT_DIR / "game_title_aliases.csv", ALIAS_HEADERS, _build_alias_rows(data.games, "game_id", "canonical_title")),
        "bbc_page_enrichment.csv": _write_csv(EXPORT_DIR / "bbc_page_enrichment.csv", ENRICHMENT_HEADERS, _build_enrichment_rows(data, group="bbc")),
        "c64_enrichment.csv": _write_csv(EXPORT_DIR / "c64_enrichment.csv", ENRICHMENT_HEADERS, _build_enrichment_rows(data, group="c64")),
        "wos_api_enrichment.csv": _write_csv(EXPORT_DIR / "wos_api_enrichment.csv", ENRICHMENT_HEADERS, _build_enrichment_rows(data, group="wos")),
        "magazine_evidence.csv": _write_csv(EXPORT_DIR / "magazine_evidence.csv", ENRICHMENT_HEADERS, _build_enrichment_rows(data, group="magazine")),
    }
    counts["repo_games_master_import chunks"] = _write_chunked_csv("repo_games_master_import", GAME_HEADERS, game_rows)
    counts["source_evidence chunks"] = _write_chunked_csv("source_evidence", SOURCE_EVIDENCE_HEADERS, source_evidence_rows)
    counts["source_assertions chunks"] = _write_chunked_csv("source_assertions", SOURCE_ASSERTION_HEADERS, source_assertion_rows)
    _write_report(counts)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Export source-backed Google Sheet CSVs from curated JSONL.")
    parser.parse_args()
    counts = export()
    for name, count in sorted(counts.items()):
        print(f"{name}: {count}")


if __name__ == "__main__":
    main()

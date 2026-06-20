from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from scripts.ingest.common import GENERATED_DIR, ROOT
from scripts.ingest.mobygames import export_mobygames_index

CONTENT_DIR = ROOT / "content"
TEMPLATE_DIR = ROOT / "templates" / "narrative"
DEFAULT_DIST = ROOT / "dist"
SEARCH_INDEX = GENERATED_DIR / "narrative-search-index.json"
PUBLIC_SEARCH_INDEX = GENERATED_DIR / "public-search-index.json"

REQUIRED_FRONT_MATTER = {
    "id",
    "title",
    "standfirst",
    "story_type",
    "content_level",
    "route",
    "linked_entity_ids",
    "linked_source_ids",
    "linked_claim_ids",
    "editorial_status",
    "fact_check_status",
    "media_permission_status",
    "author",
    "reviewer",
    "last_reviewed",
    "publication_date",
    "update_date",
    "related_content",
}

PUBLIC_EDITORIAL_STATUSES = {"public-prototype", "published"}
PUBLIC_FACT_STATUSES = {"checked", "checked-with-open-questions"}
PUBLIC_MEDIA_STATUSES = {"no-restricted-media", "approved-public"}
PUBLIC_RECORD_LABELS = {
    "Magazine index entry",
    "Reviewed release",
    "Platform-specific release",
    "Verified contributor credit",
    "Publisher only",
    "Developer verified",
    "Attribution awaiting review",
}
PRIVATE_PATTERNS = re.compile(
    r"(drive\.google|docs\.google|private message|full private|student marks|assessment feedback|exam record|1YL4Kg6Bd797QOPTH9Oo0Phc-gUc5Y4RT)",
    re.IGNORECASE,
)


@dataclass
class ContentRecord:
    path: Path
    metadata: dict[str, Any]
    body: str
    html: str

    @property
    def route(self) -> str:
        return str(self.metadata["route"]).strip("/")

    @property
    def url(self) -> str:
        return f"{self.route}/" if self.route else ""


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _split_front_matter(text: str, path: Path) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        raise ValueError(f"{path} is missing YAML front matter")
    _, front_matter, body = text.split("---", 2)
    metadata = yaml.safe_load(front_matter) or {}
    return metadata, body.strip()


def markdown_to_html(body: str) -> str:
    return markdown.markdown(
        body,
        extensions=["extra", "smarty", "sane_lists"],
        output_format="html5",
    )


def load_content(content_dir: Path = CONTENT_DIR) -> list[ContentRecord]:
    records: list[ContentRecord] = []
    for path in sorted(content_dir.glob("*/*.md")):
        metadata, body = _split_front_matter(path.read_text(encoding="utf-8"), path)
        records.append(ContentRecord(path=path, metadata=metadata, body=body, html=markdown_to_html(body)))
    return records


def load_evidence_context() -> dict[str, dict[str, Any]]:
    assets = {
        "sources": _read_json(ROOT / "assets" / "data" / "sources.json")["sources"],
        "people": _read_json(ROOT / "assets" / "data" / "people.json")["people"],
        "organisations": _read_json(ROOT / "assets" / "data" / "organisations.json")["organisations"],
        "games": _read_json(ROOT / "assets" / "data" / "games.json")["games"],
        "places": _read_json(ROOT / "assets" / "data" / "places.json")["places"],
        "events": _read_json(ROOT / "assets" / "data" / "events.json")["events"],
        "claims": _read_json(ROOT / "assets" / "data" / "claims.json")["claims"],
        "photos": _read_json(ROOT / "assets" / "data" / "photos.json")["photos"],
        "generated_games": _read_json(ROOT / "assets" / "data" / "generated" / "games-index.json")["games"],
        "generated_sources": _read_json(ROOT / "assets" / "data" / "generated" / "source-items-index.json")["items"],
    }

    sources = {row["id"]: row for row in assets["sources"]}
    sources.update({row["source_item_id"]: row for row in assets["generated_sources"]})

    claims = {row["id"]: row for row in assets["claims"]}
    claims.update({row["claim_id"]: row for row in _read_jsonl(ROOT / "data" / "curated" / "claims.jsonl")})

    entities: dict[str, Any] = {}
    for key in ["people", "organisations", "games", "places", "events"]:
        for row in assets[key]:
            entities[row["id"]] = row
    for row in assets["generated_games"]:
        entities[row["game_id"]] = row

    photos = {row["id"]: row for row in assets["photos"]}
    return {"sources": sources, "claims": claims, "entities": entities, "photos": photos}


def validate_content(records: list[ContentRecord], context: dict[str, dict[str, Any]]) -> list[str]:
    failures: list[str] = []
    ids: set[str] = set()
    routes: set[str] = set()
    for record in records:
        metadata = record.metadata
        missing = REQUIRED_FRONT_MATTER - metadata.keys()
        if missing:
            failures.append(f"{record.path}: missing front matter {sorted(missing)}")
            continue
        content_id = metadata["id"]
        route = record.route
        if content_id in ids:
            failures.append(f"duplicate content id: {content_id}")
        ids.add(content_id)
        if route in routes:
            failures.append(f"duplicate route: {route}")
        routes.add(route)

        if metadata["editorial_status"] not in PUBLIC_EDITORIAL_STATUSES:
            failures.append(f"{record.path}: editorial_status is not public: {metadata['editorial_status']}")
        if metadata["fact_check_status"] not in PUBLIC_FACT_STATUSES:
            failures.append(f"{record.path}: fact_check_status is not publishable: {metadata['fact_check_status']}")
        if metadata["media_permission_status"] not in PUBLIC_MEDIA_STATUSES:
            failures.append(f"{record.path}: media_permission_status is not publishable: {metadata['media_permission_status']}")
        if PRIVATE_PATTERNS.search(record.body) or PRIVATE_PATTERNS.search(json.dumps(metadata, default=str)):
            failures.append(f"{record.path}: private or restricted data pattern found")

        for entity_id in metadata.get("linked_entity_ids", []):
            if entity_id not in context["entities"]:
                failures.append(f"{record.path}: missing linked entity {entity_id}")
        for source_id in metadata.get("linked_source_ids", []):
            if source_id not in context["sources"]:
                failures.append(f"{record.path}: missing linked source {source_id}")
        for claim_id in metadata.get("linked_claim_ids", []):
            if claim_id not in context["claims"]:
                failures.append(f"{record.path}: missing linked claim {claim_id}")

        for quote in metadata.get("quotes", []) or []:
            if not quote.get("source_id") or quote["source_id"] not in context["sources"]:
                failures.append(f"{record.path}: quote lacks valid source_id")
            if quote.get("permission_status") != "quotation-approved":
                failures.append(f"{record.path}: quote lacks quotation-approved permission")

        for media_id in metadata.get("media", []) or []:
            photo = context["photos"].get(media_id)
            if not photo:
                failures.append(f"{record.path}: missing media record {media_id}")
                continue
            permission = photo.get("permission_status") or photo.get("public_identification_status", "")
            if not re.search(r"approved|public|permission|provisional|under verification", permission, re.IGNORECASE):
                failures.append(f"{record.path}: media record {media_id} lacks acceptable public status")

        if metadata.get("profile_kind") == "game" and not metadata.get("game_tier"):
            failures.append(f"{record.path}: game page missing game_tier")
        if metadata.get("profile_kind") == "game" and not metadata.get("record_level"):
            failures.append(f"{record.path}: game page missing record_level")
        for label in metadata.get("public_record_labels", []) or []:
            if label not in PUBLIC_RECORD_LABELS:
                failures.append(f"{record.path}: invalid public_record_label {label}")

    return failures


def _asset_prefix(route: str) -> str:
    route = route.strip("/")
    if not route:
        return ""
    return "../" * len(route.split("/"))


def _write_route(dist_dir: Path, route: str, html: str) -> None:
    target = dist_dir / route.strip("/") / "index.html" if route.strip("/") else dist_dir / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")


def _records_by_type(records: list[ContentRecord]) -> dict[str, list[ContentRecord]]:
    groups: dict[str, list[ContentRecord]] = {}
    for record in records:
        top = record.route.split("/", 1)[0]
        groups.setdefault(top, []).append(record)
    for items in groups.values():
        items.sort(key=lambda item: item.metadata["title"])
    return groups


def _linked_sources(record: ContentRecord, context: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [context["sources"][source_id] for source_id in record.metadata.get("linked_source_ids", []) if source_id in context["sources"]]


def _linked_claims(record: ContentRecord, context: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [context["claims"][claim_id] for claim_id in record.metadata.get("linked_claim_ids", []) if claim_id in context["claims"]]


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _page_context(route: str, **kwargs: Any) -> dict[str, Any]:
    return {
        "route": route.strip("/"),
        "asset_prefix": _asset_prefix(route),
        "canonical_base": "https://gmzx80.github.io/Video_Game_Info_Portal/",
        **kwargs,
    }


def export_search_index(records: list[ContentRecord], out_path: Path = SEARCH_INDEX) -> list[dict[str, Any]]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    items = [
        {
            "id": record.metadata["id"],
            "title": record.metadata["title"],
            "standfirst": record.metadata["standfirst"],
            "route": record.url,
            "mode": record.metadata.get("mode", "story"),
            "content_level": record.metadata["content_level"],
            "story_type": record.metadata["story_type"],
            "entities": record.metadata.get("linked_entity_ids", []),
            "sources": record.metadata.get("linked_source_ids", []),
            "claims": record.metadata.get("linked_claim_ids", []),
            "evidence_status": record.metadata["fact_check_status"],
        }
        for record in records
    ]
    out_path.write_text(
        json.dumps({"generated_at": "2026-06-18", "items": items}, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    return items


def _flatten_terms(*values: Any) -> list[str]:
    terms: list[str] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, str):
            value = value.strip()
            if value:
                terms.append(value)
        elif isinstance(value, dict):
            terms.extend(_flatten_terms(*value.values()))
        elif isinstance(value, (list, tuple, set)):
            terms.extend(_flatten_terms(*value))
        else:
            text = str(value).strip()
            if text:
                terms.append(text)
    return terms


def _short_text(value: Any, limit: int = 220) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else f"{text[:limit - 1].rstrip()}…"


def _search_item(
    *,
    item_id: str,
    title: str,
    kind: str,
    summary: str = "",
    route: str = "",
    url: str = "",
    status: str = "",
    labels: list[str] | None = None,
    search_terms: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": item_id,
        "title": _short_text(title, 120),
        "kind": kind,
        "summary": _short_text(summary),
        "route": route,
        "url": url,
        "status": status,
        "labels": labels or [],
        "search_terms": _flatten_terms(title, summary, kind, status, labels or [], search_terms or []),
    }


def _append_search_item(items: list[dict[str, Any]], seen: set[str], item: dict[str, Any]) -> None:
    if not item["id"] or not item["title"] or item["id"] in seen:
        return
    seen.add(item["id"])
    items.append(item)


def _reasonable_person_name(name: str) -> bool:
    words = name.split()
    return 1 <= len(words) <= 8 and len(name) <= 90 and not name.endswith(".")


def _entity_routes(records: list[ContentRecord]) -> dict[str, str]:
    routes: dict[str, str] = {}
    for record in records:
        for entity_id in record.metadata.get("linked_entity_ids", []) or []:
            routes.setdefault(entity_id, record.url)
    return routes


def _public_url(row: dict[str, Any]) -> str:
    url = row.get("url") or row.get("source_url") or row.get("archive_url") or ""
    return url if isinstance(url, str) and url.startswith(("http://", "https://")) else ""


def _append_public_catalogue_records(
    items: list[dict[str, Any]],
    seen: set[str],
    records: list[ContentRecord],
) -> None:
    routes = _entity_routes(records)
    public_specs = [
        ("assets/data/sources.json", "sources", "Public source record", "id", "title"),
        ("assets/data/people.json", "people", "Public person record", "id", "name"),
        ("assets/data/organisations.json", "organisations", "Public organisation record", "id", "name"),
        ("assets/data/games.json", "games", "Public game record", "id", "title"),
        ("assets/data/places.json", "places", "Public place record", "id", "name"),
        ("assets/data/events.json", "events", "Public event record", "id", "title"),
        ("assets/data/claims.json", "claims", "Public claim record", "id", "claim"),
        ("assets/data/relationships.json", "relationships", "Public relationship record", "id", "label"),
        ("assets/data/photos.json", "photos", "Public photo record", "id", "caption"),
    ]
    for relative_path, key, kind, id_field, title_field in public_specs:
        data = _read_json(ROOT / relative_path)
        for row in data.get(key, []):
            row_id = str(row.get(id_field, "")).strip()
            if not row_id:
                continue
            title = row.get(title_field) or row.get("title") or row.get("name") or row_id
            summary = row.get("summary") or row.get("detail") or row.get("notes") or row.get("role") or row.get("type", "")
            labels = _flatten_terms(
                row.get("type", ""),
                row.get("category", ""),
                row.get("evidence", ""),
                row.get("publication", ""),
                row.get("geography", ""),
                row.get("region", ""),
            )[:6]
            _append_search_item(items, seen, _search_item(
                item_id=f"public:{key}:{row_id}",
                title=title,
                kind=kind,
                summary=summary,
                route=routes.get(row_id, ""),
                url=_public_url(row),
                status=row.get("evidence") or row.get("status") or row.get("type", ""),
                labels=labels,
                search_terms=[
                    row.get("id", ""),
                    row.get("author", ""),
                    row.get("publication", ""),
                    row.get("date", ""),
                    row.get("period", ""),
                    row.get("platforms", []),
                    row.get("filters", []),
                    row.get("sources", []),
                    row.get("from", ""),
                    row.get("to", ""),
                    row.get("subject_id", ""),
                    row.get("contradiction_notes", ""),
                    row.get("unresolved", ""),
                    row.get("public_location", ""),
                ],
            ))


def _append_research_people(
    items: list[dict[str, Any]],
    seen: set[str],
) -> None:
    people_data = _read_json(ROOT / "data" / "people.json")
    for row in people_data.get("people", []):
        name = row.get("full_name", "")
        if not _reasonable_person_name(name):
            continue
        companies = row.get("companies", []) or []
        company_terms = [
            f"{company.get('name', '')} {company.get('relationship', '')} {company.get('status', '')}"
            for company in companies
        ]
        public_source_ids = [
            source for source in row.get("sources", [])
            if isinstance(source, str) and "private" not in source.lower()
        ]
        _append_search_item(items, seen, _search_item(
            item_id=f"research:people:{row['id']}",
            title=name,
            kind="Research person record",
            summary="Research person record with cautious evidence status; public sources are linked where available.",
            status=row.get("confidence", ""),
            labels=row.get("roles", []),
            search_terms=[
                row.get("id", ""),
                row.get("aliases", []),
                company_terms,
                row.get("platforms", []),
                row.get("games", []),
                public_source_ids,
            ],
        ))


def _append_research_sources(
    items: list[dict[str, Any]],
    seen: set[str],
) -> None:
    sources_data = _read_json(ROOT / "data" / "sources.json")
    for row in sources_data.get("sources", []):
        url = _public_url(row)
        if not url:
            continue
        _append_search_item(items, seen, _search_item(
            item_id=f"research:sources:{row['id']}",
            title=row.get("title", row["id"]),
            kind="Research source record",
            summary=row.get("notes", ""),
            url=url,
            status=row.get("type", ""),
            labels=[row.get("access", ""), row.get("rights", "")],
            search_terms=[row.get("id", ""), row.get("type", ""), row.get("access", "")],
        ))


def _append_mobygames_source_records(
    items: list[dict[str, Any]],
    seen: set[str],
) -> None:
    mobygames = _read_json(GENERATED_DIR / "mobygames-index.json")
    for row in mobygames.get("records", []):
        _append_search_item(items, seen, _search_item(
            item_id=row["id"],
            title=row["title"],
            kind="MobyGames source record",
            summary=f"{row.get('record_type', 'source').title()} evidence link. {row.get('notes', '')}",
            route="sources/mobygames/",
            url=row.get("url", ""),
            status=row.get("record_type", ""),
            labels=[row.get("public_record_label", ""), row.get("attribution", "")],
            search_terms=[
                row.get("source_id", ""),
                row.get("source_type", ""),
                row.get("slug", ""),
                row.get("numeric_id", ""),
                row.get("platform_slug", ""),
                row.get("attribution", ""),
                row.get("rights_note", ""),
                row.get("search_terms", []),
            ],
        ))


def _append_external_seed_records(
    items: list[dict[str, Any]],
    seen: set[str],
) -> None:
    assertions_path = GENERATED_DIR / "source-assertions-public.json"
    identifiers_path = GENERATED_DIR / "external-identifiers-public.json"
    if assertions_path.exists():
        assertions = _read_json(assertions_path)
        for row in assertions.get("records", []):
            title = row.get("subject_label_as_printed") or row.get("object_label_as_printed", "")
            _append_search_item(items, seen, _search_item(
                item_id=row["assertion_id"],
                title=title,
                kind="External source assertion",
                summary=(
                    f"{row.get('source_system', '').title()} {row.get('predicate', '')} assertion. "
                    "Candidate seed only; requires corroboration before canonical use."
                ),
                url=row.get("permanent_url") or row.get("source_url", ""),
                status=row.get("public_claim_status") or row.get("assertion_status", ""),
                labels=[
                    row.get("source_system", ""),
                    row.get("evidence_status", ""),
                    row.get("platform_as_printed", ""),
                    row.get("license", ""),
                ],
                search_terms=[
                    row.get("subject_type", ""),
                    row.get("subject_label_as_printed", ""),
                    row.get("predicate", ""),
                    row.get("object_type", ""),
                    row.get("object_label_as_printed", ""),
                    row.get("role_as_printed", ""),
                    row.get("date_as_printed", ""),
                    row.get("source_page_title", ""),
                    row.get("revision_id", ""),
                    row.get("notes", ""),
                ],
            ))
    if identifiers_path.exists():
        identifiers = _read_json(identifiers_path)
        for row in identifiers.get("records", []):
            _append_search_item(items, seen, _search_item(
                item_id=row["external_id_record"],
                title=row.get("external_id", ""),
                kind="External identifier",
                summary="Candidate external identifier for reconciliation.",
                url=row.get("external_url", ""),
                status=row.get("match_status", ""),
                labels=[row.get("source_system", ""), row.get("entity_type", "")],
                search_terms=[
                    row.get("entity_id", ""),
                    row.get("match_confidence", ""),
                    row.get("match_method", ""),
                    row.get("source_item_ids", []),
                    row.get("notes", ""),
                ],
            ))


def _append_local_credit_graph_records(
    items: list[dict[str, Any]],
    seen: set[str],
    records: list[ContentRecord],
) -> None:
    people_path = GENERATED_DIR / "people-public.json"
    if not people_path.exists():
        return
    routes = _entity_routes(records)
    payload = _read_json(people_path)
    for person in payload.get("people", []):
        name = person.get("canonical_name", "")
        if not name:
            continue
        local_count = int(person.get("local_credit_count", 0) or 0)
        candidate_count = int(person.get("candidate_credit_count", 0) or 0)
        warning = person.get("coverage_warning", "")
        summary = warning or f"Local credit graph with {local_count} local credit rows and {candidate_count} candidate external credit assertions."
        _append_search_item(items, seen, _search_item(
            item_id=f"local-person-credit-graph:{person.get('person_id', '')}",
            title=name,
            kind="Local person credit graph",
            summary=summary,
            route=routes.get(person.get("person_id", ""), ""),
            status=person.get("confidence", ""),
            labels=person.get("roles", []),
            search_terms=[
                person.get("aliases", []),
                person.get("companies", []),
                person.get("platforms", []),
                person.get("local_credits", []),
                person.get("candidate_external_credits", []),
                person.get("source_trail", []),
                person.get("public_notes", ""),
            ],
        ))
        for credit in person.get("local_credits", []) or []:
            title = f"{credit.get('person_name', name)} - {credit.get('game_title', '')}"
            _append_search_item(items, seen, _search_item(
                item_id=credit.get("credit_id", ""),
                title=title,
                kind="Local credit row",
                summary=f"{credit.get('role_as_printed', '')} on {credit.get('game_title', '')}. A credit does not establish employment.",
                status=credit.get("evidence_status", ""),
                labels=[credit.get("role_normalised", ""), credit.get("source_system", ""), *credit.get("platforms", [])],
                search_terms=[
                    credit.get("person_id", ""),
                    credit.get("source_ids", []),
                    credit.get("employment_status", ""),
                    credit.get("notes", ""),
                ],
            ))


def export_public_search_index(records: list[ContentRecord], out_path: Path = PUBLIC_SEARCH_INDEX) -> list[dict[str, Any]]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    items: list[dict[str, Any]] = []
    seen: set[str] = set()

    for record in records:
        _append_search_item(items, seen, _search_item(
            item_id=record.metadata["id"],
            title=record.metadata["title"],
            kind="Story",
            summary=record.metadata["standfirst"],
            route=record.url,
            status=record.metadata["fact_check_status"],
            labels=record.metadata.get("public_record_labels", []),
            search_terms=[
                record.metadata.get("mode", ""),
                record.metadata.get("content_level", ""),
                record.metadata.get("story_type", ""),
                record.metadata.get("linked_entity_ids", []),
                record.metadata.get("linked_source_ids", []),
                record.metadata.get("linked_claim_ids", []),
            ],
        ))

    _append_public_catalogue_records(items, seen, records)
    _append_research_people(items, seen)
    _append_research_sources(items, seen)
    _append_mobygames_source_records(items, seen)
    _append_external_seed_records(items, seen)
    _append_local_credit_graph_records(items, seen, records)

    north_east = _read_json(GENERATED_DIR / "north-east-collection.json")
    collection_groups: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for bucket in ["confirmed", "probable", "candidates"]:
        for row in north_east.get(bucket, []):
            key = (row["name"], row.get("badge", ""), row.get("record_label", ""), row.get("entity_type", ""))
            group = collection_groups.setdefault(key, {
                "row": row,
                "count": 0,
                "terms": [],
                "connection_types": set(),
            })
            group["count"] += 1
            group["terms"].extend(_flatten_terms(
                row.get("place", ""),
                row.get("issue", ""),
                row.get("source_magazine", ""),
                row.get("connection_type", ""),
                row.get("source_url", ""),
                bucket,
            ))
            group["connection_types"].add(row.get("connection_type", ""))

    for (name, badge, record_label, entity_type), group in collection_groups.items():
        row = group["row"]
        count_note = f" {group['count']} matching collection records share this public label." if group["count"] > 1 else ""
        slug = re.sub(r"[^a-z0-9]+", "-", f"{name}-{badge}-{record_label}-{entity_type}".casefold()).strip("-")
        _append_search_item(items, seen, _search_item(
            item_id=f"north-east-search:{slug}",
            title=name,
            kind="North East collection record",
            summary=f"{row.get('why_included', '')}{count_note}",
            route="north-east-collection.html",
            url=row.get("source_url", ""),
            status=badge,
            labels=[record_label, entity_type, *sorted(value for value in group["connection_types"] if value)],
            search_terms=group["terms"],
        ))

    source_items = _read_json(GENERATED_DIR / "source-items-index.json")["items"]
    for row in source_items:
        _append_search_item(items, seen, _search_item(
            item_id=row["source_item_id"],
            title=row["title"],
            kind="Magazine/source record",
            summary=row.get("summary", ""),
            url=row.get("archive_url", ""),
            status=row.get("item_type", ""),
            labels=[row.get("original_locator", ""), row.get("printed_company", ""), row.get("machine", "")],
            search_terms=[
                row.get("publication_id", ""),
                row.get("program_type", ""),
                row.get("named_article_authors", []),
                row.get("named_contributors", []),
                row.get("original_author", ""),
                row.get("subtitle", ""),
            ],
        ))

    games = _read_json(GENERATED_DIR / "games-index.json")["games"]
    for row in games:
        _append_search_item(items, seen, _search_item(
            item_id=row["game_id"],
            title=row["canonical_title"],
            kind="Game index record",
            summary="Game title generated from public magazine and archive indexes. Treat as an index record until linked evidence is inspected.",
            status="Magazine index entry",
            labels=[row.get("genre", ""), row.get("series", "")],
            search_terms=[row.get("title_variants", []), row.get("sources", [])],
        ))

    releases = _read_json(GENERATED_DIR / "releases-index.json")["releases"]
    for row in releases:
        _append_search_item(items, seen, _search_item(
            item_id=row["release_id"],
            title=row["release_title"],
            kind="Platform-specific release",
            summary="Release-level record with platform, publisher and developer evidence kept source-specific.",
            status=row.get("evidence_status", ""),
            labels=[row.get("public_record_label", ""), row.get("developer_status", ""), row.get("publisher_status", "")],
            search_terms=[
                row.get("platform_id", ""),
                row.get("publisher", ""),
                row.get("developer", ""),
                row.get("label", ""),
                row.get("territory", ""),
                row.get("sources", []),
            ],
        ))

    people = _read_json(GENERATED_DIR / "people-index.json")["people"]
    for row in people:
        name = row["canonical_name"]
        if not _reasonable_person_name(name):
            continue
        _append_search_item(items, seen, _search_item(
            item_id=row["person_id"],
            title=name,
            kind="Person index record",
            summary=row.get("biography_summary") or row.get("disambiguation_notes", ""),
            status=row.get("evidence_status", ""),
            labels=row.get("professional_roles", []),
            search_terms=[row.get("aliases", []), row.get("sources", [])],
        ))

    organisations = _read_json(GENERATED_DIR / "organisations-index.json")["organisations"]
    for row in organisations:
        _append_search_item(items, seen, _search_item(
            item_id=row["organisation_id"],
            title=row["canonical_name"],
            kind="Organisation index record",
            summary=row.get("organisation_type", ""),
            status=row.get("evidence_status", ""),
            labels=[row.get("organisation_type", ""), row.get("legal_name", "")],
            search_terms=[row.get("aliases", []), row.get("locations", []), row.get("sources", [])],
        ))

    items.sort(key=lambda item: (item["kind"], item["title"].casefold(), item["id"]))
    out_path.write_text(
        json.dumps({"generated_at": "2026-06-20", "items": items}, separators=(",", ":"), sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    return items


def build_narrative_site(dist_dir: Path = DEFAULT_DIST, export_public_json: bool = True) -> dict[str, int]:
    records = load_content()
    context = load_evidence_context()
    failures = validate_content(records, context)
    if failures:
        raise SystemExit("\n".join(failures))

    mobygames_index = (
        export_mobygames_index()
        if export_public_json
        else _read_json(GENERATED_DIR / "mobygames-index.json")
    )
    env = _env()
    groups = _records_by_type(records)
    search_items = export_search_index(records) if export_public_json else []
    public_search_items = export_public_search_index(records) if export_public_json else []
    if export_public_json:
        for source in [SEARCH_INDEX, PUBLIC_SEARCH_INDEX, GENERATED_DIR / "mobygames-index.json"]:
            generated_dest = dist_dir / "assets" / "data" / "generated" / source.name
            generated_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, generated_dest)

    common = {
        "records": records,
        "groups": groups,
        "search_items": search_items,
        "collection_counts": _read_json(ROOT / "assets" / "data" / "generated" / "north-east-collection.json"),
        "mobygames_index": mobygames_index,
    }

    route_pages = [
        ("", "homepage.html", {"title": "Newcastle's Video Game Technology Lab", "body_class": "home"}),
        ("phase-0", "phase.html", {"title": "Phase 0", "body_class": "phase"}),
        ("stories", "listing.html", {"title": "Stories", "section": "stories", "body_class": "listing"}),
        ("people", "listing.html", {"title": "People", "section": "people", "body_class": "listing"}),
        ("studios", "listing.html", {"title": "Studios", "section": "studios", "body_class": "listing"}),
        ("games", "listing.html", {"title": "Games", "section": "games", "body_class": "listing"}),
        ("places", "listing.html", {"title": "Places", "section": "places", "body_class": "listing"}),
        ("magazines", "listing.html", {"title": "Magazines", "section": "magazines", "body_class": "listing"}),
        ("timeline", "timeline.html", {"title": "Timeline", "body_class": "explore"}),
        ("lineages", "lineages.html", {"title": "Lineages", "body_class": "explore"}),
        ("collections", "listing.html", {"title": "Collections", "section": "collections", "body_class": "listing"}),
        ("research", "research.html", {"title": "Research", "body_class": "evidence"}),
        ("research/corrections", "corrections.html", {"title": "Corrections Log", "body_class": "evidence"}),
        ("sources/mobygames", "mobygames.html", {"title": "MobyGames Evidence Index", "body_class": "evidence"}),
        ("contribute", "contribute.html", {"title": "Contribute", "body_class": "evidence"}),
        ("talk", "talk.html", {"title": "Talk", "body_class": "talk"}),
        ("search", "search.html", {"title": "Search", "body_class": "search"}),
    ]
    for route, template_name, page in route_pages:
        html = env.get_template(template_name).render(**_page_context(route, **common, **page))
        _write_route(dist_dir, route, html)

    for record in records:
        template_name = "game.html" if record.metadata.get("profile_kind") == "game" else (
            "story.html" if record.route.startswith("stories/") else "profile.html"
        )
        html = env.get_template(template_name).render(
            **_page_context(
                record.route,
                record=record,
                title=record.metadata["title"],
                body_class=record.metadata.get("mode", "story"),
                linked_sources=_linked_sources(record, context),
                linked_claims=_linked_claims(record, context),
                **common,
            )
        )
        _write_route(dist_dir, record.route, html)

    return {
        "records": len(records),
        "routes": len(route_pages) + len(records),
        "search_items": len(search_items),
        "public_search_items": len(public_search_items),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the narrative route-directory site into dist.")
    parser.add_argument("--dist", default=str(DEFAULT_DIST))
    args = parser.parse_args()
    print(build_narrative_site(Path(args.dist)))


if __name__ == "__main__":
    main()

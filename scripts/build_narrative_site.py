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

CONTENT_DIR = ROOT / "content"
TEMPLATE_DIR = ROOT / "templates" / "narrative"
DEFAULT_DIST = ROOT / "dist"
SEARCH_INDEX = GENERATED_DIR / "narrative-search-index.json"

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


def build_narrative_site(dist_dir: Path = DEFAULT_DIST, export_public_json: bool = True) -> dict[str, int]:
    records = load_content()
    context = load_evidence_context()
    failures = validate_content(records, context)
    if failures:
        raise SystemExit("\n".join(failures))

    env = _env()
    groups = _records_by_type(records)
    search_items = export_search_index(records) if export_public_json else []
    if export_public_json:
        generated_dest = dist_dir / "assets" / "data" / "generated" / "narrative-search-index.json"
        generated_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SEARCH_INDEX, generated_dest)

    common = {
        "records": records,
        "groups": groups,
        "search_items": search_items,
        "collection_counts": _read_json(ROOT / "assets" / "data" / "generated" / "north-east-collection.json"),
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

    return {"records": len(records), "routes": len(route_pages) + len(records), "search_items": len(search_items)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the narrative route-directory site into dist.")
    parser.add_argument("--dist", default=str(DEFAULT_DIST))
    args = parser.parse_args()
    print(build_narrative_site(Path(args.dist)))


if __name__ == "__main__":
    main()

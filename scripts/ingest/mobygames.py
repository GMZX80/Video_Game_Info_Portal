from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse

from .common import GENERATED_DIR, ROOT, write_json

MOBYGAMES_ATTRIBUTION = "Data by MobyGames.com"
MOBYGAMES_SOURCE_POLICY = "Official API or curated source register only; no page scraping."
MOBYGAMES_HOSTS = {"mobygames.com", "www.mobygames.com"}
MOBYGAMES_API_BASE = "https://api.mobygames.com/v1"
MOBYGAMES_GENERATED_AT = "2026-06-20"


@dataclass(frozen=True)
class MobyGamesUrl:
    url: str
    record_type: str
    numeric_id: str = ""
    slug: str = ""
    platform_slug: str = ""


def parse_mobygames_url(url: str) -> MobyGamesUrl:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host not in MOBYGAMES_HOSTS:
        return MobyGamesUrl(url=url, record_type="external")

    parts = [part for part in parsed.path.split("/") if part]
    if not parts:
        return MobyGamesUrl(url=url, record_type="site")

    section = parts[0]
    if section not in {"game", "person", "company"}:
        return MobyGamesUrl(url=url, record_type=section)

    numeric_id = ""
    slug = ""
    detail_parts: list[str] = []
    if len(parts) > 1:
        if parts[1].isdigit():
            numeric_id = parts[1]
            slug = parts[2] if len(parts) > 2 else ""
            detail_parts = parts[3:]
        else:
            slug = parts[1]
            detail_parts = parts[2:]

    if section == "game" and detail_parts[:1] == ["credits"]:
        platform_slug = detail_parts[1] if len(detail_parts) > 1 else ""
        return MobyGamesUrl(
            url=url,
            record_type="game credits page",
            numeric_id=numeric_id,
            slug=slug,
            platform_slug=platform_slug,
        )

    return MobyGamesUrl(
        url=url,
        record_type={"game": "game", "person": "person", "company": "company"}[section],
        numeric_id=numeric_id,
        slug=slug,
    )


def _load_sources(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("sources", [])


def _is_mobygames_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.netloc.lower() in MOBYGAMES_HOSTS


def build_api_url(endpoint: str, api_key: str, params: dict[str, Any] | None = None) -> str:
    endpoint_path = "/" + endpoint.strip("/")
    query_items: list[tuple[str, str]] = [("api_key", api_key)]
    for key, value in (params or {}).items():
        values = value if isinstance(value, (list, tuple)) else [value]
        for item in values:
            query_items.append((key, str(item)))
    return f"{MOBYGAMES_API_BASE}{endpoint_path}?{urlencode(query_items)}"


def discover_mobygames_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in sources:
        url = row.get("url") or ""
        if not isinstance(url, str) or not _is_mobygames_url(url):
            continue
        parsed = parse_mobygames_url(url)
        records.append({
            "id": f"mobygames:{row['id']}",
            "source_id": row["id"],
            "title": row.get("title", row["id"]),
            "url": url,
            "record_type": parsed.record_type,
            "numeric_id": parsed.numeric_id,
            "slug": parsed.slug,
            "platform_slug": parsed.platform_slug,
            "source_type": row.get("type", ""),
            "access": row.get("access", ""),
            "rights_note": "Link and paraphrase only",
            "notes": row.get("notes", ""),
            "attribution": MOBYGAMES_ATTRIBUTION,
            "public_record_label": "MobyGames source",
            "search_terms": [
                row.get("id", ""),
                row.get("title", ""),
                row.get("type", ""),
                row.get("notes", ""),
                parsed.record_type,
                parsed.numeric_id,
                parsed.slug,
                parsed.platform_slug,
            ],
        })
    return sorted(records, key=lambda record: record["source_id"])


def export_mobygames_index(
    sources_path: Path = ROOT / "data" / "sources.json",
    out_path: Path = GENERATED_DIR / "mobygames-index.json",
) -> dict[str, Any]:
    records = discover_mobygames_sources(_load_sources(sources_path))
    payload = {
        "generated_at": MOBYGAMES_GENERATED_AT,
        "attribution": MOBYGAMES_ATTRIBUTION,
        "source_policy": MOBYGAMES_SOURCE_POLICY,
        "record_scope": (
            "Curated MobyGames links from the project source register. "
            "This is an evidence index, not a MobyGames data mirror."
        ),
        "records": records,
    }
    write_json(out_path, payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Export curated MobyGames source records for the public site.")
    parser.add_argument("--sources", default=str(ROOT / "data" / "sources.json"))
    parser.add_argument("--out", default=str(GENERATED_DIR / "mobygames-index.json"))
    args = parser.parse_args()
    print(export_mobygames_index(Path(args.sources), Path(args.out)))


if __name__ == "__main__":
    main()

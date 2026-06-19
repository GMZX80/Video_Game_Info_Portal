from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .common import (
    CURATED_DIR,
    RAW_DIR,
    REPORTS_DIR,
    RespectfulFetcher,
    canonical_url,
    content_hash,
    merge_archive_inventory,
    read_jsonl,
    stable_id,
    text_lines,
    write_jsonl,
)

TYNESOFT_ARTICLE_URL = "https://www.stairwaytohell.com/articles/KBlake.html"
ROLE_LINE_RE = re.compile(r"^(.+?)\s+\(([^()]{2,100})\)$")
IMAGE_RE = re.compile(r"^Tynesoft Staff:\s*Image\s*(\d+)$", re.I)

FALSE_CATALOGUE_TITLES = {
    "ARCHIVE INDEXES",
    "BBC GAMES ARCHIVE",
    "BBC MICRO AND ELECTRON GAMES",
    "BROWSE ARCHIVE",
    "ELECTRON",
    "GAME CHEATS",
    "MAIN",
    "MISSING",
    "OTHER SOFTWARE",
    "UEF TAPE IMAGES",
}
FALSE_CATALOGUE_COMPANY_MARKERS = {
    "ARCHIVE INDEX",
    "BROWSE ARCHIVE",
    "DISK IMAGE",
    "GAME CHEATS",
    "OTHER SOFTWARE",
    "TAPE IMAGE",
    "UEF TAPE IMAGE",
}


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _primary_name(name_as_printed: str) -> str:
    name = re.split(r"\s+aka\s+", name_as_printed, maxsplit=1, flags=re.I)[0]
    name = re.sub(r"\s+'[^']+'\s*$", "", name)
    return _clean(name)


def parse_tynesoft_group_captions(
    html: str,
    url: str = TYNESOFT_ARTICLE_URL,
    *,
    accessed_at: str = "2026-06-19",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Parse Kevin Blake's two group-photo captions as retrospective testimony.

    This parser uses only printed caption text. It performs no visual comparison,
    face recognition or inference from appearance.
    """

    lines = text_lines(html)
    identifications: list[dict[str, Any]] = []
    media_assets: list[dict[str, Any]] = []
    current_image = ""
    current_order = 0
    pending_position = ""
    source_item_id = stable_id("source-item", "stairway", url)

    for line in lines:
        image_match = IMAGE_RE.match(line)
        if image_match:
            image_number = image_match.group(1)
            current_image = f"tynesoft-staff-image-{image_number}"
            current_order = 0
            pending_position = ""
            date_note = "c. 1987, according to Kevin Blake's recollection" if image_number == "1" else "c. 1987; source says the second image is related to the first"
            media_assets.append(
                {
                    "media_id": stable_id("media", current_image),
                    "media_type": "photograph",
                    "title": f"Tynesoft Staff Image {image_number}",
                    "source_item_id": source_item_id,
                    "source_url": canonical_url(url),
                    "original_context": "Tynesoft Boys Club Part One",
                    "date_as_reported": date_note,
                    "photographer_as_reported": "Kevin Blake, uncertain recollection" if image_number == "1" else "not independently established",
                    "rights_holder": "unknown",
                    "permission_status": "not established",
                    "public_use_status": "research metadata only",
                    "notes": "The image itself is not copied by the ingest process.",
                }
            )
            continue

        if not current_image:
            continue
        if line.startswith("Follow up from David Croft") or line.startswith("Photos from Gary Partis"):
            current_image = ""
            continue
        if line.lower() in {"bottom left", "middle right"}:
            pending_position = line
            continue

        role_match = ROLE_LINE_RE.match(line)
        if not role_match:
            continue
        name_as_printed = _clean(role_match.group(1))
        role_as_printed = _clean(role_match.group(2))
        if not name_as_printed or name_as_printed.lower().startswith("image"):
            continue

        current_order += 1
        primary_name = _primary_name(name_as_printed)
        identifications.append(
            {
                "photo_identification_id": stable_id(
                    "photo-identification",
                    current_image,
                    current_order,
                    name_as_printed,
                ),
                "photo_id": stable_id("photo", current_image),
                "media_id": stable_id("media", current_image),
                "source_item_id": source_item_id,
                "position_order": current_order,
                "position_description": pending_position or "left-to-right order as printed by Kevin Blake",
                "name_as_printed": name_as_printed,
                "primary_name_as_printed": primary_name,
                "role_as_printed": role_as_printed,
                "identification_method": "Kevin Blake retrospective caption on Stairway To Hell",
                "evidence_status": "first-person retrospective testimony",
                "verification_status": "unconfirmed pending independent corroboration",
                "public_visibility": "research-only",
                "accessed_at": accessed_at,
                "source_url": canonical_url(url),
                "notes": "No visual identification, face recognition or comparison by appearance was used.",
            }
        )
        pending_position = ""

    return identifications, media_assets


def _is_false_catalogue_navigation(row: dict[str, Any]) -> bool:
    if row.get("item_type") != "game catalogue entry":
        return False
    title = _clean(row.get("title", "")).upper()
    company = _clean(row.get("printed_company", "")).upper()
    if title in FALSE_CATALOGUE_TITLES:
        return True
    if any(marker in company for marker in FALSE_CATALOGUE_COMPANY_MARKERS):
        return True
    if company in {"#", "A-Z", "0-9"}:
        return True
    return False


def _is_excluded_download_directory(url: str) -> bool:
    path = urlparse(url).path.lower()
    if not path.endswith("/"):
        return False
    if not path.startswith(("/bbc/", "/electron/")):
        return False
    return any(marker in path for marker in ("/archive/", "/other/", "/uefarchive/", "/disk", "/tape"))


def _write_photo_audit(identifications: list[dict[str, Any]], removed_catalogue_rows: list[dict[str, Any]]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Tynesoft photograph identification audit",
        "",
        "The records below reproduce names and roles from Kevin Blake's retrospective Stairway To Hell caption. They are testimony records, not facial identifications and not independently verified facts.",
        "",
        "| Photograph | Position | Name as printed | Role as printed | Status |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in identifications:
        lines.append(
            f"| {row['photo_id']} | {row['position_description']} {row['position_order']} | {row['name_as_printed']} | {row['role_as_printed']} | {row['verification_status']} |"
        )
    lines.extend(
        [
            "",
            "## Known spelling conflicts requiring direct confirmation",
            "",
            "- Stairway prints **Mike Landruff**; first-hand testimony reported to the project owner uses **Mike Landreth**. These remain separate unresolved spellings.",
            "- Stairway prints **Julian Jameson**; first-hand testimony reported to the project owner uses a Julien/Julian variant. No automatic merge is permitted.",
            "- Stairway prints **Bruce Nesbitt**; a one-t spelling has also been reported. The printed caption is preserved without resolving identity by appearance.",
            "",
            "## Catalogue cleanup",
            "",
            f"Removed {len(removed_catalogue_rows)} obvious navigation or archive-heading rows that had been misread as game/company pairs.",
            "",
            "No private message text is reproduced in this report.",
        ]
    )
    (REPORTS_DIR / "tynesoft-photo-identification-audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def supplement(*, accessed_at: str = "2026-06-19") -> dict[str, int]:
    """Apply post-crawl corrections and capture Tynesoft group captions."""

    out = RAW_DIR / "stairway"
    fetcher = RespectfulFetcher()
    article = fetcher.fetch(TYNESOFT_ARTICLE_URL, resume=True)

    identifications: list[dict[str, Any]] = []
    media_assets: list[dict[str, Any]] = []
    if article.status_code == 200:
        identifications, media_assets = parse_tynesoft_group_captions(
            article.text,
            article.canonical_url,
            accessed_at=accessed_at,
        )

    source_items = read_jsonl(out / "source-items.jsonl")
    removed_catalogue_rows = [row for row in source_items if _is_false_catalogue_navigation(row)]
    retained_source_items = [row for row in source_items if not _is_false_catalogue_navigation(row)]

    inventory = read_jsonl(out / "page-inventory.jsonl")
    reclassified_directories = 0
    for row in inventory:
        if row.get("fetch_status") == "failed" and _is_excluded_download_directory(row.get("url", "")):
            row["fetch_status"] = "excluded"
            row["content_type"] = "excluded binary/download directory"
            row["parse_status"] = "deliberately excluded"
            row["exclusion_reason"] = "binary or software archive directory; metadata crawl does not enter it"
            reclassified_directories += 1

    existing_identifications = {
        row["photo_identification_id"]: row
        for row in read_jsonl(out / "photo-identifications.jsonl")
    }
    for row in identifications:
        existing_identifications[row["photo_identification_id"]] = row

    existing_media = {
        row["media_id"]: row
        for row in read_jsonl(out / "media-assets.jsonl")
        if row.get("media_id")
    }
    for row in media_assets:
        existing_media[row["media_id"]] = row

    write_jsonl(out / "source-items.jsonl", retained_source_items, sort_key="source_item_id")
    write_jsonl(
        out / "photo-identifications.jsonl",
        existing_identifications.values(),
        sort_key="photo_identification_id",
    )
    write_jsonl(out / "media-assets.jsonl", existing_media.values(), sort_key="media_id")
    write_jsonl(out / "page-inventory.jsonl", inventory, sort_key="page_id")
    merge_archive_inventory("stairway", inventory)
    _write_photo_audit(identifications, removed_catalogue_rows)

    pending_pages = sum(1 for row in inventory if row.get("parse_status") == "pending page limit")
    remaining_failures = sum(1 for row in inventory if row.get("fetch_status") == "failed")
    return {
        "photo_identifications": len(existing_identifications),
        "media_assets": len(existing_media),
        "catalogue_navigation_rows_removed": len(removed_catalogue_rows),
        "download_directories_reclassified": reclassified_directories,
        "pages_pending": pending_pages,
        "remaining_failures": remaining_failures,
        "source_items": len(retained_source_items),
    }


def merge_curated_media(curated_dir: Path = CURATED_DIR) -> int:
    """Merge research-safe raw media metadata after canonical normalisation."""

    existing = {
        row["media_id"]: row
        for row in read_jsonl(curated_dir / "media-assets.jsonl")
        if row.get("media_id")
    }
    for archive_dir in RAW_DIR.glob("*"):
        if not archive_dir.is_dir():
            continue
        for row in read_jsonl(archive_dir / "media-assets.jsonl"):
            if row.get("media_id"):
                existing[row["media_id"]] = row
    write_jsonl(curated_dir / "media-assets.jsonl", existing.values(), sort_key="media_id")
    return len(existing)

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from .common import (
    CURATED_DIR,
    RAW_DIR,
    REPORTS_DIR,
    RespectfulFetcher,
    canonical_url,
    read_jsonl,
    stable_id,
    text_lines,
    write_jsonl,
)

TYNESOFT_ARTICLE_URL = "https://www.stairwaytohell.com/articles/KBlake.html"

# These lines are preserved in an unresolved research queue rather than treated
# as game records. The issue pages often put a publisher on a separate line.
SOFTWARE_TEXT_ITEM_TYPES = {"software index text"}

IMAGE_COMBINED_RE = re.compile(r"Tynesoft\s+Staff\s*:\s*Image\s*(\d+)", re.I)
IMAGE_ONLY_RE = re.compile(r"^Image\s*(\d+)$", re.I)
ROLE_RE = re.compile(r"^(.+?)\s*\(([^()]{2,120})\)\s*$")
PAREN_ROLE_RE = re.compile(r"^\(([^()]{2,120})\)\s*$")
POSITION_LABELS = ("Bottom left", "Middle Right")


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _primary_name(name_as_printed: str) -> str:
    name = re.split(r"\s+aka\s+", name_as_printed, maxsplit=1, flags=re.I)[0]
    name = re.sub(r"\s+'[^']+'\s*$", "", name)
    return _clean(name)


def _normalise_caption_lines(html: str) -> list[str]:
    """Join line breaks that old HTML uses inside headings or role captions."""

    source = [_clean(line) for line in text_lines(html) if _clean(line)]
    result: list[str] = []
    index = 0
    while index < len(source):
        line = source[index]
        if line.lower().rstrip(":") == "tynesoft staff" and index + 1 < len(source):
            image_match = IMAGE_ONLY_RE.match(source[index + 1])
            if image_match:
                result.append(f"Tynesoft Staff: Image {image_match.group(1)}")
                index += 2
                continue
        if index + 1 < len(source) and not ROLE_RE.match(line):
            role_match = PAREN_ROLE_RE.match(source[index + 1])
            if role_match and len(line) <= 140:
                result.append(f"{line} ({role_match.group(1)})")
                index += 2
                continue
        result.append(line)
        index += 1
    return result


def _role_text_after_name(name_tag: Any) -> str:
    role_tag = name_tag.find_next("i")
    if not role_tag or role_tag.find_parent("p") != name_tag.find_parent("p"):
        return ""
    return _clean(role_tag.get_text(" ", strip=True)).strip("() ")


def _is_alias_name_tag(name_tag: Any) -> bool:
    previous_parts: list[str] = []
    sibling = name_tag.previous_sibling
    while sibling is not None:
        if getattr(sibling, "name", None) == "b":
            break
        if isinstance(sibling, str):
            previous_parts.append(sibling)
        elif hasattr(sibling, "get_text"):
            previous_parts.append(sibling.get_text(" ", strip=True))
        sibling = sibling.previous_sibling
    previous = _clean(" ".join(reversed(previous_parts))).lower()
    return previous.endswith("aka") or previous.endswith("aka:")


def _position_before_name(paragraph_text: str, name: str, pending_position: str) -> str:
    name_index = paragraph_text.find(name)
    if name_index < 0:
        return pending_position
    candidates = [
        label
        for label in POSITION_LABELS
        if (index := paragraph_text.lower().rfind(label.lower(), 0, name_index)) >= 0
    ]
    return candidates[-1] if candidates else pending_position


def parse_tynesoft_caption_testimony(
    html: str,
    url: str = TYNESOFT_ARTICLE_URL,
    *,
    accessed_at: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Parse printed caption testimony without identifying anyone by appearance."""

    soup = BeautifulSoup(html, "html.parser")
    source_item_id = stable_id("source-item", "stairway", url)
    identities: list[dict[str, Any]] = []
    media: list[dict[str, Any]] = []
    current_image = ""
    current_order = 0
    pending_position = ""

    for paragraph in soup.find_all("p"):
        paragraph_text = _clean(paragraph.get_text(" ", strip=True))
        image_match = IMAGE_COMBINED_RE.search(paragraph_text)
        if image_match:
            image_number = image_match.group(1)
            current_image = f"tynesoft-staff-image-{image_number}"
            current_order = 0
            pending_position = ""
            image_link = next(
                (
                    canonical_url(link.get("href", ""), url)
                    for link in paragraph.find_all("a", href=True)
                    if "tynesoft" in link.get("href", "").lower()
                ),
                "",
            )
            if not any(row["media_id"] == stable_id("media", current_image) for row in media):
                media.append(
                    {
                        "media_id": stable_id("media", current_image),
                        "media_type": "photograph",
                        "title": f"Tynesoft Staff Image {image_number}",
                        "source_item_id": source_item_id,
                        "source_url": canonical_url(url),
                        "source_page": canonical_url(url),
                        "original_caption": f"Tynesoft Staff: Image {image_number}",
                        "original_context": "Tynesoft Boys Club Part One",
                        "date_as_reported": "c. 1987, according to Kevin Blake's retrospective caption",
                        "photographer_as_reported": "Kevin Blake recalls taking Image 1; Image 2 is not independently established",
                        "rights_holder": "unknown",
                        "permission_status": "not established",
                        "archive_host": "Stairway To Hell",
                        "image_url": image_link,
                        "local_project_copy_exists": False,
                        "public_use_status": "research metadata only",
                        "public_export_status": "withheld - rights not established",
                        "notes": "The ingest records caption evidence only and does not copy the photograph.",
                    }
                )
            continue

        if not current_image:
            continue
        lower = paragraph_text.lower()
        if lower.startswith("follow up from david croft") or lower.startswith("photos from gary partis"):
            current_image = ""
            continue

        for label in POSITION_LABELS:
            if lower == label.lower():
                pending_position = label
                break

        for name_tag in paragraph.find_all("b"):
            if _is_alias_name_tag(name_tag):
                continue
            name_as_printed = _clean(name_tag.get_text(" ", strip=True))
            role_as_printed = _role_text_after_name(name_tag)
            if not name_as_printed or not role_as_printed:
                continue
            if name_as_printed.lower().startswith(("image", "click here")):
                continue

            current_order += 1
            position = _position_before_name(paragraph_text, name_as_printed, pending_position)
            identities.append(
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
                    "position_description": position or "left-to-right order as printed by Kevin Blake",
                    "name_as_printed": name_as_printed,
                    "primary_name_as_printed": _primary_name(name_as_printed),
                    "role_as_printed": role_as_printed,
                    "identification_method": "Kevin Blake retrospective caption on Stairway To Hell",
                    "evidence_status": "first-person retrospective testimony",
                    "evidence_type": "caption testimony",
                    "verification_status": "unconfirmed pending independent corroboration",
                    "corroboration_status": "uncorroborated",
                    "public_visibility": "research-only",
                    "accessed_at": accessed_at,
                    "source_url": canonical_url(url),
                    "editorial_notes": "No visual identification, facial recognition or comparison by appearance was used.",
                    "notes": "No visual identification, facial recognition or comparison by appearance was used.",
                }
            )
            pending_position = ""

    return identities, media


def clean_sinclair_supplement() -> dict[str, int]:
    """Move ambiguous issue-page prose out of canonical source-item input."""

    path = RAW_DIR / "sinclair-user" / "source-items.jsonl"
    rows = read_jsonl(path)
    retained: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    for row in rows:
        if row.get("archive") == "sinclair-user" and row.get("item_type") in SOFTWARE_TEXT_ITEM_TYPES:
            unresolved.append(row)
        else:
            retained.append(row)
    write_jsonl(path, retained, sort_key="source_item_id")
    write_jsonl(
        RAW_DIR / "sinclair-user" / "unresolved-software-lines.jsonl",
        unresolved,
        sort_key="source_item_id",
    )
    return {
        "source_items_retained": len(retained),
        "unresolved_software_lines_preserved": len(unresolved),
    }


def capture_tynesoft_photo_testimony(*, accessed_at: str) -> dict[str, int]:
    fetcher = RespectfulFetcher()
    result = fetcher.fetch(TYNESOFT_ARTICLE_URL, resume=True)
    if result.status_code != 200:
        return {"photo_identifications": 0, "media_assets": 0, "fetch_failures": 1}

    identities, media = parse_tynesoft_caption_testimony(
        result.text,
        result.canonical_url,
        accessed_at=accessed_at,
    )
    raw_dir = RAW_DIR / "stairway"
    existing_ids = {
        row["photo_identification_id"]: row
        for row in read_jsonl(raw_dir / "photo-identifications.jsonl")
        if row.get("photo_identification_id")
    }
    existing_media = {
        row["media_id"]: row
        for row in read_jsonl(raw_dir / "media-assets.jsonl")
        if row.get("media_id")
    }
    for row in identities:
        existing_ids[row["photo_identification_id"]] = row
    for row in media:
        existing_media[row["media_id"]] = row
    write_jsonl(
        raw_dir / "photo-identifications.jsonl",
        existing_ids.values(),
        sort_key="photo_identification_id",
    )
    write_jsonl(raw_dir / "media-assets.jsonl", existing_media.values(), sort_key="media_id")
    return {
        "photo_identifications": len(existing_ids),
        "media_assets": len(existing_media),
        "fetch_failures": 0,
    }


def merge_curated_media(curated_dir: Path = CURATED_DIR) -> int:
    rows: dict[str, dict[str, Any]] = {
        row["media_id"]: row
        for row in read_jsonl(curated_dir / "media-assets.jsonl")
        if row.get("media_id")
    }
    for archive_dir in RAW_DIR.glob("*"):
        if not archive_dir.is_dir():
            continue
        for row in read_jsonl(archive_dir / "media-assets.jsonl"):
            if row.get("media_id"):
                rows[row["media_id"]] = row
    write_jsonl(curated_dir / "media-assets.jsonl", rows.values(), sort_key="media_id")
    return len(rows)


def write_audit(
    photo_results: dict[str, int],
    sinclair_results: dict[str, int],
) -> None:
    identities = sorted(
        read_jsonl(RAW_DIR / "stairway" / "photo-identifications.jsonl"),
        key=lambda row: (row.get("media_id", ""), int(row.get("position_order", 0) or 0), row.get("name_as_printed", "")),
    )
    media_assets = sorted(read_jsonl(RAW_DIR / "stairway" / "media-assets.jsonl"), key=lambda row: row.get("media_id", ""))
    lines = [
        "# Archive post-processing audit",
        "",
        "## Tynesoft group photograph captions",
        "",
        "These are Kevin Blake's retrospective printed identifications. They are not facial identifications and remain unconfirmed pending corroboration.",
        "",
        "| Photograph | Position | Name as printed | Role as printed | Status |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in identities:
        lines.append(
            f"| {row.get('photo_id', '')} | {row.get('position_description', '')} {row.get('position_order', '')} | {row.get('name_as_printed', '')} | {row.get('role_as_printed', '')} | {row.get('verification_status', '')} |"
        )
    lines.extend(
        [
            "",
            "### Unresolved spellings",
            "",
            "- Stairway prints **Mike Landruff**; project testimony also records **Mike Landreth**. Do not merge without documentary confirmation.",
            "- Stairway prints **Julian Jameson**; Julien/Julian and Jameson/Jamieson variants remain unresolved.",
            "- Stairway prints **Bruce Nesbitt**; a one-t variant has also been reported.",
            "",
            "## Sinclair issue-page prose",
            "",
            f"Moved {sinclair_results.get('unresolved_software_lines_preserved', 0)} ambiguous software-section lines to `data/raw/sinclair-user/unresolved-software-lines.jsonl` instead of presenting them as game records.",
            "",
            "No private-message text or copyrighted article body is reproduced here.",
        ]
    )
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "archive-postprocess-audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    photo_lines = [
        "# Tynesoft photograph identification audit",
        "",
        "Generated: 2026-06-19",
        "",
        "Source inspected: https://www.stairwaytohell.com/articles/KBlake.html",
        "",
        "The parser records Kevin Blake's retrospective caption testimony only. It does not perform visual identification, facial recognition or comparison by appearance, and it does not copy or republish the photographs.",
        "",
        "## Photographs located",
        "",
        "| Media ID | Original caption | Image URL | Permission status | Public export status |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in media_assets:
        photo_lines.append(
            f"| {row.get('media_id', '')} | {row.get('original_caption', '')} | {row.get('image_url', '')} | {row.get('permission_status', '')} | {row.get('public_export_status', '')} |"
        )
    photo_lines.extend(
        [
            "",
            "## Caption testimony records",
            "",
            "| Photograph | Position | Name as printed | Role as printed | Evidence status | Verification status |",
            "| --- | ---: | --- | --- | --- | --- |",
        ]
    )
    for row in identities:
        photo_lines.append(
            f"| {row.get('media_id', '')} | {row.get('position_description', '')} {row.get('position_order', '')} | {row.get('name_as_printed', '')} | {row.get('role_as_printed', '')} | {row.get('evidence_status', '')} | {row.get('verification_status', '')} |"
        )
    photo_lines.extend(
        [
            "",
            "## Names requiring spelling or identity resolution",
            "",
            "- Stairway prints **Mike Landruff**; project testimony also records **Mike Landreth**. Do not merge without documentary confirmation.",
            "- Stairway prints **Julian Jameson**; Julien/Julian and Jameson/Jamieson variants remain unresolved.",
            "- Stairway prints **Bruce Nesbitt**; a one-t variant has also been reported.",
            "- **Sparky** and **Baldrick** are caption names or nicknames and require identity resolution before any person merge.",
            "- **Dave Mann** is printed with an alias in the caption; the primary printed name is preserved and no alias merge is automatic.",
            "",
            "## Corroboration and rights questions",
            "",
            "- Corroborated by another source: 0 records.",
            "- Rights holder: unknown for both media records.",
            "- Photographer: Image 1 is attributed to Kevin Blake's recollection; Image 2 is not independently established.",
            "- Permission status: not established.",
            "- Local project copy: none recorded by the ingest.",
            "- Public export: all media and identification records are withheld from public export pending rights and editorial approval.",
            "",
            "## Records withheld from public export",
            "",
            f"- Media records withheld: {len(media_assets)}.",
            f"- Photo-identification records withheld: {len(identities)}.",
            "- Private message text is not reproduced.",
        ]
    )
    (REPORTS_DIR / "tynesoft-photo-identification-audit.md").write_text("\n".join(photo_lines) + "\n", encoding="utf-8")

from __future__ import annotations

import argparse
import io
import re
import zipfile
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .common import RAW_DIR, RespectfulFetcher, add_common_arguments, content_hash, short_summary, stable_id, write_jsonl

ROOT_URL = "http://www.users.globalnet.co.uk/~jg27paw4/"
SPOT_DATA_URL = "http://www.users.globalnet.co.uk/~jg27paw4/spot-on/spotdata.zip"
TTFN_URL = "http://www.users.globalnet.co.uk/~jg27paw4/type-ins/typehome.htm"
TTFN_SINCLAIR_USER_URL = "http://www.users.globalnet.co.uk/~jg27paw4/type-ins/sincuser/su_names.htm"

MACHINES = {
    "80": "ZX80",
    "81": "ZX81",
    "SP": "ZX Spectrum",
    "QL": "Sinclair QL",
    "SC": "SAM Coupé",
}
PROGRAM_TYPES = {
    "A": "adventure",
    "B": "business",
    "D": "domestic",
    "E": "educational",
    "G": "game",
    "U": "utility",
}
LANGUAGES = {
    "B": "BASIC",
    "C": "machine code",
    "D": "BASIC and machine code",
    "F": "Forth",
}


def parse_ttf_typeins(html: str, base_url: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    raw_lines = [line.strip() for line in html.splitlines() if line.strip().upper().startswith("<TR><TD")]
    parsed_lines = []
    for line in raw_lines:
        parts = re.split(r"<T[DH][^>]*>", line, flags=re.I)[1:]
        if len(parts) >= 10:
            parsed_lines.append(parts[:10])
    if not parsed_lines:
        soup = BeautifulSoup(html, "html.parser")
        for tr in soup.find_all("tr"):
            cells = tr.find_all("td")
            if len(cells) >= 10:
                parsed_lines.append([str(cell) for cell in cells[:10]])
    for cells in parsed_lines:
        title_soup = BeautifulSoup(cells[0], "html.parser")
        title = " ".join(title_soup.get_text(" ", strip=True).split())
        if not title or title.upper() == "TITLE":
            continue
        link = title_soup.find("a", href=True)
        cleaned = [" ".join(BeautifulSoup(cell, "html.parser").get_text(" ", strip=True).split()) for cell in cells]
        comp = cleaned[5]
        prog = cleaned[6]
        lang = cleaned[7]
        row = {
            "title": title,
            "author": cleaned[1],
            "issue": cleaned[2],
            "page": cleaned[3],
            "file_type": cleaned[4],
            "machine": MACHINES.get(comp, comp),
            "program_type": PROGRAM_TYPES.get(prog, prog),
            "language": LANGUAGES.get(lang, lang),
            "information": cleaned[8],
            "sort_date": cleaned[9],
            "url": urljoin(base_url, link["href"]) if link else base_url,
        }
        rows.append(row)
    return rows


def _read_unl(zip_file: zipfile.ZipFile, name: str) -> list[dict[str, str]]:
    text = zip_file.read(name).decode("latin-1")
    lines = [line.rstrip("\n") for line in text.splitlines() if line and line != "*"]
    if not lines:
        return []
    header = lines[0].split("\t")
    rows = []
    for line in lines[1:]:
        values = line.split("\t")
        rows.append({header[index]: values[index] if index < len(values) else "" for index in range(len(header))})
    return rows


def parse_spot_zip(content: bytes) -> dict[str, list[dict[str, str]]]:
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        return {
            "publishers": _read_unl(zf, "FPUBLR.UNL"),
            "games": _read_unl(zf, "FGAMES.UNL"),
            "references": _read_unl(zf, "FREFS.UNL"),
            "magazines": _read_unl(zf, "FMAGZNE.UNL"),
            "features": _read_unl(zf, "FEATURE.UNL"),
        }


def run(indexes_only: bool = True, resume: bool = False, accessed_at: str = "2026-06-18") -> dict[str, int]:
    fetcher = RespectfulFetcher()
    root = fetcher.fetch(ROOT_URL, resume=resume)
    ttfn = fetcher.fetch(TTFN_SINCLAIR_USER_URL, resume=resume)
    typeins = parse_ttf_typeins(ttfn.text, ttfn.canonical_url)

    # SPOT publishes plain data files in a small zip; use that instead of crawling every index page.
    response = requests.get(SPOT_DATA_URL, headers={"User-Agent": fetcher.user_agent}, timeout=30)
    response.raise_for_status()
    spot = parse_spot_zip(response.content)
    publishers = {row.get("FPPUBL") or row.get("fppubl") or row.get("FPPUBL", ""): row for row in spot["publishers"]}

    issue_keys = set()
    source_items: list[dict[str, Any]] = []
    for game in spot["games"]:
        title = game.get("FGNAME", "").lstrip("-")
        if not title:
            continue
        publisher_code = game.get("FGPUBL", "")
        publisher = publishers.get(publisher_code, {}).get("FPPNAME", publisher_code)
        source_items.append({
            "raw_id": stable_id("raw-source-item", "globalnet-spot", title, publisher),
            "archive": "globalnet",
            "record_type": "source-item",
            "source_item_id": stable_id("source-item", "globalnet-spot", title, publisher),
            "publication_id": "publication:spot-on",
            "issue_id": "",
            "item_type": "index-only entry",
            "title": title,
            "byline_text": "",
            "printed_company": publisher,
            "archive_url": SPOT_DATA_URL,
            "original_locator": f"SPOT FGAMES link {game.get('FGLINK', '')}",
            "date": "",
            "summary": short_summary(f"SPOT index entry for {title}; publisher/label code resolves to {publisher}."),
            "rights_note": "Plain index metadata only; no article text or listing copied.",
            "accessed_at": accessed_at,
            "content_hash": content_hash(str(game)),
        })
    for typein in typeins:
        issue_keys.add(typein["issue"])
        source_items.append({
            "raw_id": stable_id("raw-source-item", "globalnet-ttfn", typein["title"], typein["issue"]),
            "archive": "globalnet",
            "record_type": "source-item",
            "source_item_id": stable_id("source-item", "globalnet-ttfn", typein["title"], typein["issue"]),
            "publication_id": "publication:ttfn",
            "issue_id": stable_id("issue", "ttfn", typein["issue"]),
            "item_type": "type-in program",
            "title": typein["title"],
            "byline_text": typein["author"],
            "archive_url": typein["url"],
            "original_locator": f"TTFn Sinclair User {typein['issue']} p.{typein['page']}",
            "date": typein["issue"],
            "summary": short_summary(f"{typein['program_type']} type-in for {typein['machine']} by {typein['author']}; language {typein['language']}."),
            "rights_note": "Type-in metadata only; program listing/archive is not republished.",
            "accessed_at": accessed_at,
            "content_hash": content_hash(str(typein)),
            "machine": typein["machine"],
            "program_type": typein["program_type"],
            "language": typein["language"],
        })
    issue_rows = [
        {
            "raw_id": stable_id("raw", "ttfn", issue),
            "archive": "globalnet",
            "record_type": "issue",
            "publication_id": "publication:ttfn",
            "issue_id": stable_id("issue", "ttfn", issue),
            "issue_number": issue,
            "cover_date": issue,
            "date_precision": "month",
            "index_url": TTFN_SINCLAIR_USER_URL,
            "source_url": root.canonical_url,
            "accessed_at": accessed_at,
            "content_hash": content_hash(issue),
        }
        for issue in sorted(issue_keys)
    ]
    out = RAW_DIR / "globalnet"
    write_jsonl(out / "issues.jsonl", issue_rows, sort_key="issue_id")
    write_jsonl(out / "source-items.jsonl", source_items, sort_key="source_item_id")
    return {"issues": len(issue_rows), "source_items": len(source_items), "typeins": len(typeins)}


def main() -> None:
    parser = add_common_arguments(argparse.ArgumentParser(description="Ingest Globalnet SPOT/TTFn metadata."))
    args = parser.parse_args()
    print(run(indexes_only=args.indexes_only, resume=args.resume, accessed_at=args.accessed_date))


if __name__ == "__main__":
    main()

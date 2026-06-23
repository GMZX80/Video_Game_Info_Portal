from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

from scripts.ingest.common import GENERATED_DIR, ROOT
from scripts.build_narrative_site import build_narrative_site

DIST_DIR = ROOT / "dist"
REPORT_PATH = ROOT / "reports" / "pages-artifact-review.md"

PUBLIC_FILES = [
    ".nojekyll",
    "north-east-collection.html",
]

PUBLIC_DIRS = [
    "assets/audio",
    "assets/css",
    "assets/js",
    "assets/images",
    "assets/data",
]

ALLOWED_TALK_MATERIAL_RE = re.compile(
    r"https://docs\.google\.com/"
    r"(?:"
    r"presentation/d/154QbvfKc_mh-K1zHwEbyMIeHZ28M4hsKQ4y6Hia_GRo/(?:edit\?usp=sharing|export/(?:pptx|pdf))"
    r"|"
    r"document/d/1bfkJmsrgpgvMog3NB9gUeV9_FSe3r0g9RsaCEcqAzds/(?:edit\?usp=sharing|export\?format=(?:pdf|docx))"
    r")"
)

BLOCKED_TOP_LEVEL = {
    ".cache",
    "build",
    "data",
    "reports",
    "scripts",
    "tests",
}

ALLOWED_PUBLIC_RESEARCH_ROUTES = {
    "research/index.html",
    "research/corrections/index.html",
}


def _strip_allowed_talk_material_links(text: str) -> str:
    return ALLOWED_TALK_MATERIAL_RE.sub("", text)


def _copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _copy_dir(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)


def _dist_files(dist_dir: Path) -> list[str]:
    return sorted(path.relative_to(dist_dir).as_posix() for path in dist_dir.rglob("*") if path.is_file())


def _validate_dist(dist_dir: Path) -> list[str]:
    failures: list[str] = []
    files = _dist_files(dist_dir)
    file_set = set(files)

    for required in [
        ".nojekyll",
        "index.html",
        "north-east-collection.html",
        "phase-0/index.html",
        "stories/index.html",
        "stories/code-through-the-letterbox/index.html",
        "people/index.html",
        "people/gary-partis/index.html",
        "studios/index.html",
        "studios/tynesoft/index.html",
        "games/index.html",
        "games/oxo/index.html",
        "games/doctor-who-and-the-mines-of-terror/index.html",
        "games/super-gran/index.html",
        "places/index.html",
        "places/blaydon/index.html",
        "magazines/index.html",
        "magazines/sinclair-user/index.html",
        "timeline/index.html",
        "lineages/index.html",
        "collections/index.html",
        "collections/north-east-collection/index.html",
        "research/index.html",
        "research/corrections/index.html",
        "sources/mobygames/index.html",
        "contribute/index.html",
        "talk/index.html",
        "search/index.html",
        "assets/css/site.css",
        "assets/audio/how-newcastle-bedroom-coders-changed-global-technology.m4a",
        "assets/js/site.js",
        "assets/js/narrative.js",
        "assets/js/north-east-collection.js",
        "assets/data/generated/north-east-collection.json",
        "assets/data/generated/mobygames-index.json",
        "assets/data/generated/narrative-search-index.json",
        "assets/data/generated/public-search-index.json",
        "assets/images/favicon.svg",
        "assets/images/graham-morgan-speaker.jpg",
        "assets/images/newcastle-crt-hero.webp",
    ]:
        if required not in file_set:
            failures.append(f"missing required public artefact: {required}")

    for file_name in files:
        top_level = file_name.split("/", 1)[0]
        if top_level in BLOCKED_TOP_LEVEL:
            failures.append(f"blocked source path was copied into dist: {file_name}")
        if top_level == "research" and file_name not in ALLOWED_PUBLIC_RESEARCH_ROUTES:
            failures.append(f"raw research path was copied into dist: {file_name}")
        if file_name.endswith(".sqlite") or file_name.endswith(".db"):
            failures.append(f"database file was copied into dist: {file_name}")

    text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in dist_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in {".css", ".csv", ".html", ".js", ".json", ".md", ".txt", ".yml"}
    )
    if 'href="/assets/' in text or 'src="/assets/' in text or "fetch('/assets/" in text or 'fetch("/assets/' in text:
        failures.append("root-relative /assets/ path found in dist")
    google_audit_text = _strip_allowed_talk_material_links(text)
    if "drive.google.com" in google_audit_text or "docs.google.com" in google_audit_text:
        failures.append("private Google Drive URL leaked into dist")
    return failures


def _write_report(dist_dir: Path, failures: list[str]) -> None:
    files = _dist_files(dist_dir)
    generated = sorted(path.relative_to(ROOT).as_posix() for path in GENERATED_DIR.glob("*.json"))
    lines = [
        "# Pages Artefact Review",
        "",
        "Generated: 2026-06-18",
        "",
        "The production GitHub Pages artefact is built from `dist/` only.",
        "",
        "## Included Files",
        "",
        *[f"- `{file_name}`" for file_name in files],
        "",
        "## Required Content Checks",
        "",
        f"- `index.html`: {'yes' if 'index.html' in files else 'no'}",
        f"- `north-east-collection.html`: {'yes' if 'north-east-collection.html' in files else 'no'}",
        f"- required CSS and JavaScript: {'yes' if {'assets/css/site.css', 'assets/js/site.js', 'assets/js/narrative.js', 'assets/js/north-east-collection.js'}.issubset(set(files)) else 'no'}",
        f"- generated public JSON: {'yes' if all(file_name.replace('assets/data/generated/', '') in {path.name for path in GENERATED_DIR.glob('*.json')} for file_name in files if file_name.startswith('assets/data/generated/')) and bool(generated) else 'no'}",
        f"- required images: {'yes' if any(file_name.startswith('assets/images/') for file_name in files) else 'no'}",
        f"- `.nojekyll`: {'yes' if '.nojekyll' in files else 'no'}",
        f"- root-relative `/assets/` paths: {'no' if not failures else 'see validation notes'}",
        "",
        "## Excluded Source Material",
        "",
        "- `raw/`, `curated/`, `research/`, `reports/`, `scripts/`, `tests/`, caches, SQLite files and unresolved private notes are not copied.",
        "",
        "## Validation Notes",
        "",
    ]
    if failures:
        lines.extend(f"- {failure}" for failure in failures)
    else:
        lines.append("- No Pages artefact boundary failures found.")
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_dist(dist_dir: Path = DIST_DIR) -> list[str]:
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(parents=True)

    for file_name in PUBLIC_FILES:
        _copy_file(ROOT / file_name, dist_dir / file_name)
    for dir_name in PUBLIC_DIRS:
        _copy_dir(ROOT / dir_name, dist_dir / dir_name)

    build_narrative_site(dist_dir)
    _copy_file(ROOT / "index.html", dist_dir / "index.html")

    failures = _validate_dist(dist_dir)
    _write_report(dist_dir, failures)
    if failures:
        raise SystemExit("\n".join(failures))
    return _dist_files(dist_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a clean GitHub Pages dist artefact.")
    parser.parse_args()
    for file_name in build_dist():
        print(file_name)


if __name__ == "__main__":
    main()

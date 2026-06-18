from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser

import requests


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
CURATED_DIR = DATA_DIR / "curated"
SCHEMA_DIR = DATA_DIR / "schemas"
CACHE_DIR = ROOT / ".cache" / "magazine-ingest"
REPORTS_DIR = ROOT / "reports"
GENERATED_DIR = ROOT / "assets" / "data" / "generated"
DEFAULT_ACCESSED_AT = "2026-06-18"
DEFAULT_USER_AGENT = "VideoGameHistoryResearchBot/0.1 (+https://github.com/GMZX80/Video_Game_Info_Portal)"


def slugify(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = text.replace("&", " and ")
    text = re.sub(r"['’]", "", text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "unknown"


def stable_id(prefix: str, *parts: Any) -> str:
    return ":".join([prefix, *(slugify(part) for part in parts)])


def content_hash(content: str | bytes) -> str:
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def canonical_url(url: str, base_url: str | None = None) -> str:
    joined = urljoin(base_url or "", url)
    parsed = urlparse(joined)
    query = urlencode(sorted(parse_qsl(parsed.query, keep_blank_values=True)))
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    return urlunparse((scheme, netloc, path, "", query, ""))


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


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]], *, sort_key: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    materialised = list(rows)
    if sort_key:
        materialised.sort(key=lambda row: str(row.get(sort_key, "")))
    with path.open("w", encoding="utf-8") as handle:
        for row in materialised:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


class FetchManifest:
    def __init__(self, path: Path):
        self.path = path
        self.records: dict[str, dict[str, Any]] = read_json(path, {})

    def _key(self, url: str) -> str:
        return canonical_url(url)

    def seen(self, url: str) -> bool:
        return self._key(url) in self.records

    def get(self, url: str) -> dict[str, Any] | None:
        return self.records.get(self._key(url))

    def record(self, url: str, status_code: int, digest: str, canonical: str, **extra: Any) -> None:
        self.records[self._key(url)] = {
            "url": self._key(url),
            "status_code": status_code,
            "content_hash": digest,
            "canonical_url": canonical_url(canonical),
            **extra,
        }
        write_json(self.path, self.records)


@dataclass
class FetchResult:
    url: str
    canonical_url: str
    status_code: int
    text: str
    content_hash: str
    from_cache: bool


class RespectfulFetcher:
    def __init__(
        self,
        cache_dir: Path = CACHE_DIR,
        *,
        user_agent: str = DEFAULT_USER_AGENT,
        delay_seconds: float = 1.0,
        timeout: int = 20,
    ):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.manifest = FetchManifest(cache_dir / "manifest.json")
        self.user_agent = user_agent
        self.delay_seconds = delay_seconds
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        self.last_fetch_by_host: dict[str, float] = {}
        self.robots: dict[str, RobotFileParser | None] = {}

    def _cache_path(self, url: str) -> Path:
        return self.cache_dir / f"{content_hash(canonical_url(url))}.html"

    def _robots_for(self, url: str) -> RobotFileParser | None:
        parsed = urlparse(url)
        root = f"{parsed.scheme}://{parsed.netloc}"
        if root in self.robots:
            return self.robots[root]
        robots_url = urljoin(root, "/robots.txt")
        parser = RobotFileParser()
        parser.set_url(robots_url)
        try:
            response = self.session.get(robots_url, timeout=self.timeout)
            if response.status_code >= 400:
                self.robots[root] = None
                return None
            parser.parse(response.text.splitlines())
            self.robots[root] = parser
        except Exception:
            self.robots[root] = None
        return self.robots[root]

    def allowed(self, url: str) -> bool:
        robots = self._robots_for(url)
        if robots is None:
            return True
        return robots.can_fetch(self.user_agent, url)

    def _rate_limit(self, url: str) -> None:
        host = urlparse(url).netloc
        previous = self.last_fetch_by_host.get(host)
        if previous is not None:
            wait = self.delay_seconds - (time.monotonic() - previous)
            if wait > 0:
                time.sleep(wait)
        self.last_fetch_by_host[host] = time.monotonic()

    def fetch(self, url: str, *, resume: bool = False) -> FetchResult:
        url = canonical_url(url)
        cache_path = self._cache_path(url)
        if resume and cache_path.exists():
            text = cache_path.read_text(encoding="utf-8", errors="replace")
            record = self.manifest.get(url) or {}
            return FetchResult(url, record.get("canonical_url", url), record.get("status_code", 200), text, content_hash(text), True)
        if not self.allowed(url):
            digest = content_hash("")
            self.manifest.record(url, 0, digest, url, blocked_by_robots=True)
            return FetchResult(url, url, 0, "", digest, False)
        self._rate_limit(url)
        response = self.session.get(url, timeout=self.timeout)
        text = response.text
        digest = content_hash(text)
        if response.ok and "text/html" in response.headers.get("content-type", "text/html"):
            cache_path.write_text(text, encoding="utf-8")
        self.manifest.record(url, response.status_code, digest, response.url)
        return FetchResult(url, canonical_url(response.url), response.status_code, text, digest, False)


def add_common_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument("--indexes-only", action="store_true", help="Fetch and parse index-level data only.")
    parser.add_argument("--resume", action="store_true", help="Reuse cached responses where available.")
    parser.add_argument("--accessed-date", default=DEFAULT_ACCESSED_AT)
    return parser


def text_lines(html: str) -> list[str]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    return [line.strip() for line in soup.get_text("\n").splitlines() if line.strip()]


def short_summary(text: str, max_length: int = 240) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= max_length:
        return cleaned
    return cleaned[: max_length - 1].rstrip() + "…"

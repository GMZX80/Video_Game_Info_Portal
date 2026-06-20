from __future__ import annotations

import argparse
import csv
import json
import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests

from .common import DEFAULT_USER_AGENT, REPORTS_DIR, ROOT, content_hash, stable_id, write_json
from .mobygames import MOBYGAMES_API_BASE, build_api_url

DEFAULT_CACHE_DIR = ROOT / ".cache" / "mobygames-api"
DEFAULT_REQUEST_LOG = DEFAULT_CACHE_DIR / "request-log.jsonl"
DEFAULT_GENERATED_AT = "2026-06-20"
DEFAULT_HOURLY_QUOTA = 720


class MobyGamesApiError(RuntimeError):
    pass


class MobyGamesApiMissingKey(MobyGamesApiError):
    pass


def sanitize_mobygames_url(url: str) -> str:
    parsed = urlparse(url)
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() != "api_key"
    ]
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(query), ""))


def _normalise_title(value: str) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _cache_key(endpoint: str, params: dict[str, Any] | None) -> str:
    pairs: list[tuple[str, str]] = []
    for key, value in sorted((params or {}).items()):
        for item in _as_list(value):
            pairs.append((key, str(item)))
    return content_hash(f"{endpoint.strip('/')}?{urlencode(pairs)}")


class MobyGamesApiClient:
    def __init__(
        self,
        *,
        cache_dir: Path = DEFAULT_CACHE_DIR,
        request_log_path: Path = DEFAULT_REQUEST_LOG,
        api_key_env: str = "MOBYGAMES_API_KEY",
        session: requests.Session | None = None,
        sleep: Any = time.sleep,
        min_interval_seconds: float = 1.0,
        hourly_quota: int = DEFAULT_HOURLY_QUOTA,
        timeout: int = 30,
    ) -> None:
        self.cache_dir = cache_dir
        self.request_log_path = request_log_path
        self.api_key_env = api_key_env
        self.session = session or requests.Session()
        if hasattr(self.session, "headers"):
            self.session.headers.update({"User-Agent": DEFAULT_USER_AGENT})
        self.sleep = sleep
        self.min_interval_seconds = min_interval_seconds
        self.hourly_quota = hourly_quota
        self.timeout = timeout
        self.last_request_at = 0.0
        self.request_times: list[float] = []

    @property
    def api_key(self) -> str:
        value = os.environ.get(self.api_key_env, "").strip()
        if not value:
            raise MobyGamesApiMissingKey(f"{self.api_key_env} is required for live MobyGames API requests")
        return value

    def _cache_path(self, endpoint: str, params: dict[str, Any] | None) -> Path:
        return self.cache_dir / f"{_cache_key(endpoint, params)}.json"

    def _rate_limit(self) -> None:
        now = time.monotonic()
        self.request_times = [item for item in self.request_times if now - item < 3600]
        if len(self.request_times) >= self.hourly_quota:
            raise MobyGamesApiError(f"MobyGames hourly quota exhausted: {self.hourly_quota} requests/hour")
        wait = self.min_interval_seconds - (now - self.last_request_at)
        if wait > 0:
            self.sleep(wait)
        self.last_request_at = time.monotonic()
        self.request_times.append(self.last_request_at)

    def _log(self, row: dict[str, Any]) -> None:
        self.request_log_path.parent.mkdir(parents=True, exist_ok=True)
        safe = {
            **row,
            "url": sanitize_mobygames_url(str(row.get("url", ""))),
            "final_url": sanitize_mobygames_url(str(row.get("final_url", ""))),
        }
        with self.request_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(safe, ensure_ascii=False, sort_keys=True))
            handle.write("\n")

    def request_json(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        *,
        resume: bool = True,
        retries: int = 2,
    ) -> dict[str, Any]:
        cache_path = self._cache_path(endpoint, params)
        if resume and cache_path.exists():
            self._log({
                "endpoint": endpoint,
                "params": params or {},
                "status_code": 200,
                "from_cache": True,
                "url": f"{MOBYGAMES_API_BASE}/{endpoint.strip('/')}",
            })
            return json.loads(cache_path.read_text(encoding="utf-8"))

        api_key = self.api_key
        url = build_api_url(endpoint, api_key, params)
        last_error = ""
        for attempt in range(max(1, retries)):
            self._rate_limit()
            response = self.session.get(url, timeout=self.timeout)
            status_code = int(getattr(response, "status_code", 0))
            final_url = str(getattr(response, "url", url))
            self._log({
                "endpoint": endpoint,
                "params": params or {},
                "status_code": status_code,
                "from_cache": False,
                "attempt": attempt + 1,
                "url": url,
                "final_url": final_url,
            })
            if status_code == 429 and attempt + 1 < retries:
                retry_after = getattr(response, "headers", {}).get("retry-after")
                try:
                    wait = float(retry_after) if retry_after else 1.0
                except ValueError:
                    wait = 1.0
                self.sleep(max(1.0, wait))
                continue
            if status_code >= 400:
                try:
                    last_error = json.dumps(response.json(), sort_keys=True)
                except Exception:
                    last_error = f"HTTP {status_code}"
                break
            payload = response.json()
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
            return payload
        raise MobyGamesApiError(last_error or "MobyGames API request failed")


def _match_confidence(query_title: str, candidate_title: str) -> tuple[float, str]:
    if _normalise_title(query_title) == _normalise_title(candidate_title):
        return 1.0, "normalised title exact match"
    query_words = set(query_title.casefold().split())
    candidate_words = set(candidate_title.casefold().split())
    if query_words and query_words <= candidate_words:
        return 0.8, "query words contained in candidate title"
    if _normalise_title(query_title) in _normalise_title(candidate_title):
        return 0.7, "normalised query substring match"
    overlap = len(query_words & candidate_words) / max(len(query_words | candidate_words), 1)
    return round(overlap * 0.65, 3), "token overlap"


def normalise_mobygames_game(
    query_title: str,
    game: dict[str, Any],
    *,
    source_url: str,
    generated_at: str,
) -> dict[str, Any]:
    title = str(game.get("title", "")).strip()
    confidence, reason = _match_confidence(query_title, title)
    return {
        "candidate_id": stable_id("mobygames-match", query_title, game.get("game_id", "")),
        "source_system": "mobygames",
        "moby_game_id": game.get("game_id", ""),
        "query_title": query_title,
        "title": title,
        "alternate_titles": [
            row.get("title", "")
            for row in game.get("alternate_titles", []) or []
            if isinstance(row, dict) and row.get("title")
        ],
        "moby_url": game.get("moby_url", ""),
        "platforms": game.get("platforms", []) or [],
        "first_release_dates": [
            row.get("first_release_date", "")
            for row in game.get("platforms", []) or []
            if isinstance(row, dict) and row.get("first_release_date")
        ],
        "genres": [
            row.get("genre_name", "")
            for row in game.get("genres", []) or []
            if isinstance(row, dict) and row.get("genre_name")
        ],
        "moby_score": game.get("moby_score"),
        "num_votes": game.get("num_votes"),
        "api_source_url": sanitize_mobygames_url(source_url),
        "source_timestamp": generated_at,
        "match_confidence": confidence,
        "match_reason": reason,
        "match_status": "candidate" if confidence < 1.0 else "probable",
    }


def normalise_mobygames_platform_detail(
    game_id: int | str,
    platform_id: int | str,
    detail: dict[str, Any],
    *,
    source_url: str,
) -> dict[str, Any]:
    companies: list[dict[str, Any]] = []
    countries: list[str] = []
    release_dates: list[str] = []
    for release in detail.get("releases", []) or []:
        if not isinstance(release, dict):
            continue
        release_dates.extend(str(release.get("release_date", "")).splitlines()[:1] if release.get("release_date") else [])
        countries.extend(str(country) for country in release.get("countries", []) or [])
        for company in release.get("companies", []) or []:
            if isinstance(company, dict):
                companies.append({
                    "company_id": company.get("company_id", ""),
                    "company_name": company.get("company_name", ""),
                    "role": company.get("role", ""),
                })
    return {
        "source_system": "mobygames",
        "moby_game_id": game_id,
        "platform_id": platform_id,
        "platform_name": detail.get("platform_name", ""),
        "first_release_date": detail.get("first_release_date", ""),
        "release_dates": sorted({item for item in release_dates if item}),
        "release_countries": sorted({item for item in countries if item}),
        "release_companies": companies,
        "attributes": [
            row.get("attribute_name", "")
            for row in detail.get("attributes", []) or []
            if isinstance(row, dict) and row.get("attribute_name")
        ],
        "ratings": detail.get("ratings", []) or [],
        "moby_url": detail.get("moby_url", ""),
        "api_source_url": sanitize_mobygames_url(source_url),
        "evidence_status": "official API metadata",
    }


def write_missing_key_reports(reports_dir: Path = REPORTS_DIR, *, generated_at: str = DEFAULT_GENERATED_AT) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "mobygames-api-coverage.md").write_text(
        "\n".join([
            "# MobyGames API Coverage",
            "",
            f"Generated: {generated_at}",
            "",
            "MobyGames API key missing. Set `MOBYGAMES_API_KEY` locally or as a GitHub Actions secret for live imports.",
            "",
            "The adapter uses the official API only. It does not scrape MobyGames HTML pages.",
            "",
            "Current API documentation exposes game search and game/platform release endpoints. Person-credit import remains a limitation unless an authorised API endpoint, licensed export, or manual CSV is supplied.",
        ]) + "\n",
        encoding="utf-8",
    )
    (reports_dir / "mobygames-api-limits.md").write_text(
        "\n".join([
            "# MobyGames API Limits",
            "",
            f"Generated: {generated_at}",
            "",
            "- API key source: `MOBYGAMES_API_KEY` environment variable only.",
            "- Maximum request rate: 1 request per second.",
            "- Non-commercial hourly quota tracked by the adapter: 720 requests per hour.",
            "- 429 responses are retried after waiting.",
            "- Request logs redact the API key.",
        ]) + "\n",
        encoding="utf-8",
    )
    for filename, fieldnames, row in [
        ("mobygames-title-matches.csv", ["query_title", "moby_game_id", "title", "match_confidence", "match_reason", "match_status"], None),
        ("mobygames-unresolved-matches.csv", ["query_title", "reason"], None),
        ("mobygames-api-failures.csv", ["endpoint", "status", "reason"], {"endpoint": "all", "status": "missing_api_key", "reason": "MOBYGAMES_API_KEY not set"}),
    ]:
        with (reports_dir / filename).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            if row:
                writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run MobyGames API title discovery without scraping HTML.")
    parser.add_argument("--reports-dir", default=str(REPORTS_DIR))
    parser.add_argument("--generated-at", default=DEFAULT_GENERATED_AT)
    args = parser.parse_args()
    if not os.environ.get("MOBYGAMES_API_KEY"):
        write_missing_key_reports(Path(args.reports_dir), generated_at=args.generated_at)
        print("MobyGames API key missing; wrote limitation reports.")
        return
    print("MobyGames API key available. Use adapter methods from a curated seed script for live imports.")


if __name__ == "__main__":
    main()

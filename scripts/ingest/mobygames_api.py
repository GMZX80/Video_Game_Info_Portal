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

from .common import DEFAULT_USER_AGENT, REPORTS_DIR, ROOT, content_hash, read_json, read_jsonl, stable_id, write_json, write_jsonl
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


def mobygames_credit_payload_to_assertions(payload: dict[str, Any], *, generated_at: str) -> list[dict[str, Any]]:
    """Convert authorised API credit-like payloads to candidate source assertions.

    The current adapter does not assume that the public API provides complete
    person-credit lists. This helper is deliberately narrow: if a permitted API
    response or fixture supplies credit rows, they enter the local graph as
    secondary database assertions awaiting review.
    """

    game_id = payload.get("game_id", "")
    title = str(payload.get("title", "")).strip()
    platform = str(payload.get("platform", "")).strip()
    assertions: list[dict[str, Any]] = []
    for credit in payload.get("credits", []) or []:
        if not isinstance(credit, dict):
            continue
        person_name = str(credit.get("person_name", "")).strip()
        role = str(credit.get("role", "") or credit.get("role_as_printed", "")).strip()
        if not title or not person_name or not role:
            continue
        source_url = sanitize_mobygames_url(str(credit.get("source_url", "") or payload.get("source_url", "")))
        assertions.append({
            "assertion_id": stable_id("assertion", "mobygames-api-credit", game_id, platform, person_name, role),
            "source_item_id": stable_id("source-item", "mobygames-api-credit", game_id or title, platform or "all"),
            "source_system": "mobygames-api",
            "subject_type": "game",
            "subject_label_as_printed": title,
            "predicate": "credited_as",
            "object_type": "person",
            "object_label_as_printed": person_name,
            "role_as_printed": role,
            "date_as_printed": str(credit.get("date", "") or payload.get("release_date", "")),
            "place_as_printed": "",
            "platform_as_printed": platform,
            "confidence": "MobyGames API credit payload; pending editorial reconciliation",
            "assertion_status": "candidate",
            "public_claim_status": "candidate",
            "evidence_status": "secondary database credit",
            "source_url": source_url,
            "source_page_title": "MobyGames API credit payload",
            "revision_id": "",
            "permanent_url": "",
            "license": "",
            "attribution_required": False,
            "notes": "MobyGames API-derived credit assertion; does not establish employment.",
            "generated_at": generated_at,
            "external_person_id": credit.get("person_id", ""),
            "external_game_id": game_id,
        })
    return assertions


def _seed_counts(
    *,
    sources_path: Path = ROOT / "data" / "sources.json",
    people_path: Path = ROOT / "data" / "people.json",
    games_path: Path = ROOT / "data" / "curated" / "games.jsonl",
) -> dict[str, int]:
    sources = read_json(sources_path, {"sources": []}).get("sources", [])
    people = read_json(people_path, {"people": []}).get("people", [])
    games = read_jsonl(games_path)
    return {
        "mobygames_source_links": sum(1 for row in sources if "mobygames.com" in str(row.get("url", ""))),
        "people": len(people),
        "games": len(games),
    }


def initialise_raw_dir(raw_dir: Path = ROOT / "data" / "raw" / "mobygames") -> None:
    write_jsonl(raw_dir / "issues.jsonl", [])
    write_jsonl(raw_dir / "source-items.jsonl", [])
    write_jsonl(raw_dir / "source-assertions.jsonl", [])
    write_jsonl(raw_dir / "external-identifiers.jsonl", [])


def write_missing_key_reports(
    reports_dir: Path = REPORTS_DIR,
    *,
    generated_at: str = DEFAULT_GENERATED_AT,
    seed_counts: dict[str, int] | None = None,
) -> None:
    seed_counts = seed_counts or _seed_counts()
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
            f"Seeded MobyGames source links available locally: {seed_counts.get('mobygames_source_links', 0)}",
            f"People seed rows available locally: {seed_counts.get('people', 0)}",
            f"Game title seed rows available locally: {seed_counts.get('games', 0)}",
            "",
            "Current API documentation exposes game search and game/platform release endpoints. Person-credit import remains a limitation unless an authorised API endpoint, licensed export, or manual CSV is supplied.",
        ]) + "\n",
        encoding="utf-8",
    )
    (reports_dir / "mobygames-person-credit-coverage.md").write_text(
        "\n".join([
            "# MobyGames Person Credit Coverage",
            "",
            f"Generated: {generated_at}",
            "",
            "No MobyGames person-credit rows were imported in this run.",
            "",
            "Reason: MobyGames API key missing or person-credit endpoint coverage not available to this adapter.",
            "",
            "Permitted fallback: populate `data/manual/mobygames-person-credit-import.csv` and keep rows as secondary database credit assertions until reviewed.",
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
        ("mobygames-unresolved-people.csv", ["person_name", "reason"], {"person_name": "all", "reason": "MOBYGAMES_API_KEY not set; person-credit import not run"}),
        ("mobygames-unresolved-games.csv", ["game_title", "reason"], {"game_title": "all", "reason": "MOBYGAMES_API_KEY not set; title reconciliation not run"}),
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
    parser.add_argument("--resume", action="store_true", help="Reuse cached MobyGames API responses where available.")
    parser.add_argument("--dry-run", action="store_true", help="Report seed counts and initialise raw files without making API requests.")
    parser.add_argument("--sources", default=str(ROOT / "data" / "sources.json"))
    parser.add_argument("--people", default=str(ROOT / "data" / "people.json"))
    parser.add_argument("--games", default=str(ROOT / "data" / "curated" / "games.jsonl"))
    parser.add_argument("--raw-dir", default=str(ROOT / "data" / "raw" / "mobygames"))
    args = parser.parse_args()
    seed_counts = _seed_counts(sources_path=Path(args.sources), people_path=Path(args.people), games_path=Path(args.games))
    initialise_raw_dir(Path(args.raw_dir))
    if args.dry_run:
        write_missing_key_reports(Path(args.reports_dir), generated_at=args.generated_at, seed_counts=seed_counts)
        print({"dry_run": True, **seed_counts})
        return
    if not os.environ.get("MOBYGAMES_API_KEY"):
        write_missing_key_reports(Path(args.reports_dir), generated_at=args.generated_at, seed_counts=seed_counts)
        print("MobyGames API key missing; wrote limitation reports.")
        return
    print({"mobygames_api_key_available": True, "resume": args.resume, **seed_counts})


if __name__ == "__main__":
    main()

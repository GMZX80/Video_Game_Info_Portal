from pathlib import Path

from scripts.ingest.common import (
    FetchManifest,
    canonical_url,
    content_hash,
    stable_id,
)


def test_stable_id_is_deterministic_and_human_readable():
    assert stable_id("source-item", "Sinclair User", "098", "Beverly Hills Cop Review") == (
        "source-item:sinclair-user:098:beverly-hills-cop-review"
    )


def test_canonical_url_normalises_scheme_host_and_fragment():
    assert canonical_url("HTTP://Example.COM/path/index.htm?b=2&a=1#section") == (
        "http://example.com/path/index.htm?a=1&b=2"
    )


def test_content_hash_is_sha256_hex():
    assert content_hash("Crash Online") == "08fbba56930c3952999d094e1b95394da530ddd261b737c0d2518c4921aeb492"


def test_fetch_manifest_records_and_restores_entries(tmp_path: Path):
    manifest_path = tmp_path / "manifest.json"
    manifest = FetchManifest(manifest_path)
    manifest.record("https://example.test/a", 200, "abc123", "https://example.test/a")

    restored = FetchManifest(manifest_path)

    assert restored.get("https://example.test/a")["content_hash"] == "abc123"
    assert restored.seen("https://example.test/a")

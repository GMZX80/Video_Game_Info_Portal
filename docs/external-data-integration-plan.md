# External Data Integration Plan

Generated: 2026-06-20

## Goal

Extend the static research database from index mentions toward resolved historical entities while keeping every external record evidence-backed, legally safe, and deployable on GitHub Pages.

## Implemented Slice

- Added official-API-only MobyGames tooling in `scripts/ingest/mobygames_api.py`.
- Added MediaWiki API based Wikipedia platform-list ingestion in `scripts/ingest/wikipedia_platform_lists.py`.
- Added referenced Wikidata statement parsing in `scripts/ingest/wikidata_games.py`.
- Added structured metadata adapters for World of Spectrum, ZXDB, and ZXInfo.
- Added `source-assertions.jsonl` and `external-identifiers.jsonl` as curated companion datasets.
- Added static public exports for candidate source assertions and external IDs.
- Added external reconciliation queue generation in `scripts/reconcile_external_entities.py`.

## Data Flow

1. External adapters fetch or parse structured metadata only.
2. Raw adapter outputs live under `data/raw/<source-system>/`.
3. `scripts.ingest.normalise` preserves external source items, source assertions, and external IDs into `data/curated/`.
4. `scripts.reconcile_external_entities` writes review queues rather than merging candidates.
5. `scripts.ingest.export_public_json` exports compact public candidate records.
6. `scripts.build_narrative_site` adds candidate assertions and external IDs to public search.

## Current Seed Import

Wikipedia platform lists were fetched through the MediaWiki API and committed as structured raw metadata:

- ZX Spectrum rows: 1,995
- Commodore 64 rows: 2,183
- Raw Wikidata QID captures: 2,536
- Curated external identifiers after deterministic de-duplication: 1,896
- Curated external source assertions after de-duplication: 10,589

## MobyGames

The MobyGames adapter requires `MOBYGAMES_API_KEY` from the environment. It has cache, resume mode, request logging, one-request-per-second pacing, hourly quota tracking, and 429 retry handling. No key is logged or written to cache.

No live MobyGames API import was run in this branch because no API key was available.

## Next Steps

- Run MobyGames seeded title discovery with `MOBYGAMES_API_KEY`.
- Add manual or licensed MobyGames person-credit CSV import if API coverage remains insufficient.
- Add configured live fetch commands for WoS, ZXDB, and ZXInfo once exact endpoint/export URLs are selected.
- Review the generated reconciliation queues and promote only corroborated records.

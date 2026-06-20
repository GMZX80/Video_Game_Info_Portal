# Local Credit Graph Audit

Generated: 2026-06-20

## Summary

The previous public search was shallow for Phil Scott because the project had a research person record and MobyGames links, but no local Phil Scott credit rows. `scripts/ingest/mobygames.py` still correctly preserves a link-only MobyGames evidence index; imported credits now require `scripts/ingest/mobygames_api.py`, a permitted API payload, or the reviewed manual CSV path.

## Audited Files

- `data/people.json`
- `data/sources.json`
- `data/curated/people.jsonl`
- `data/curated/credits.jsonl`
- `data/curated/games.jsonl`
- `data/curated/releases.jsonl`
- `assets/data/generated/mobygames-index.json`
- `assets/data/generated/public-search-index.json`
- `scripts/ingest/mobygames.py`
- `scripts/build_narrative_site.py`

## Current Counts

- Research people in `data/people.json`: 22
- Research people with empty `games` lists: 9
- Local explicit curated credits in `data/curated/credits.jsonl`: 80
- Local research credit rows exported from `data/people.json`: 37
- Public credit rows in `credits-public.json`: 117
- Source records in `data/sources.json`: 59
- Link-only source records with URLs: 57
- MobyGames link-only source records: 25
- Public search records: 39,891

## Phil Scott Findings

- Local research record: `data/people.json` has `id: phil-scott`, alias `Philip Scott`, an empty direct `games` list, and two reviewed candidate source assertion IDs.
- Local public person graph: `assets/data/generated/people-public.json` now includes Phil Scott.
- Local confirmed credit rows: 0.
- Local candidate credit rows: 2, for `Trolls` and `Winter Olympiad '88`.
- Candidate external credit assertions: 2, from the reviewed manual MobyGames row for `Trolls` and the Wikipedia ZX Spectrum list row for `Winter Olympiad '88`.
- Link-only local sources: 2 public links in the person graph.
- Public route: `people/phil-scott/`.

## Why Search Was Limited

Phil Scott appeared mainly through:

- the research person record;
- the MobyGames person-page link;
- the Trolls MobyGames link;
- source/search terms copied from link records.

Those records are useful provenance but not enough for a full bibliography. Search now also includes a `Local person credit graph` result and two `Local credit row` results, all labelled as candidate/secondary rather than confirmed.

## MobyGames Status

MobyGames API tooling is implemented in `scripts/ingest/mobygames_api.py`. It reads `MOBYGAMES_API_KEY` from the environment, supports cache/resume/dry-run behavior, initializes `data/raw/mobygames/`, and redacts API keys from logs.

No MobyGames API key was available in this run. No API-backed MobyGames person-credit rows were imported.

Manual fallback path:

- `data/manual/mobygames-person-credit-import.csv`
- reviewed rows become candidate `secondary database credit` source assertions and matching source items;
- pending rows are ignored.

One reviewed manual row is currently imported for Phil Scott on `Trolls`. It remains a candidate secondary database credit and does not establish employment.

## Public Search Assembly

Public search is assembled in `scripts/build_narrative_site.py` by combining stories, public asset catalogues, research people/source records, MobyGames link records, external assertions, external IDs, North East collection records, generated source items, games, releases, people, organisations, and now local person credit graph records.

## Guardrails

- A MobyGames URL-only source record does not create a credit.
- Publisher/developer/employer relationships remain separate.
- A credit does not establish employment.
- Private testimony is not exported publicly.
- Wikipedia and Wikidata records remain candidate seed assertions unless reviewed.

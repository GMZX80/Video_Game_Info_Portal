# MobyGames Evidence Integration Plan

Generated: 2026-06-20

## Goal

Bring MobyGames into the public archive as a structured evidence layer, without scraping MobyGames pages, copying long descriptions, mirroring images, or presenting MobyGames data as original site content.

## Source Boundary

MobyGames is treated as a link-and-paraphrase source. The public site may show source titles, source types, MobyGames URLs, short project-authored notes, relationship labels, and explicit attribution. It must not publish copied game descriptions, review text, player reviews, screenshots, cover scans, or bulk database dumps.

The implementation must use the official API only when a `MOBYGAMES_API_KEY` is provided. Normal CI and Pages builds must remain deterministic and must not call MobyGames.

Every public output that exposes generated MobyGames records must include this attribution:

`Data by MobyGames.com`

## Phase 1 Scope

This branch ships the foundation:

- discover every existing MobyGames source already registered in `data/sources.json`;
- normalise those records into `assets/data/generated/mobygames-index.json`;
- classify each record as a game, game credits page, person, company, or other MobyGames source;
- include all generated MobyGames records in `public-search-index.json`;
- expose a public `/sources/mobygames/` route summarising the MobyGames evidence layer;
- add validation guards for attribution, no scraping, no copied descriptions, and no private testimony leakage.

## Phase 2 Scope

With an API key and explicit usage approval, the optional ingester can enrich seeded game records through the official API. It should cache responses under a committed or reviewable generated layer only after editorial review, preserve MobyGames URLs, and keep descriptions/images out of the public site unless a later rights review permits them.

## Architecture

- `scripts/ingest/mobygames.py`: deterministic source discovery and optional API client helpers.
- `scripts/ingest/export_public_json.py`: exports `mobygames-index.json` during the normal public JSON build.
- `scripts/build_narrative_site.py`: adds MobyGames index records to browser search.
- `templates/narrative/mobygames.html`: public evidence-route template.
- `tests/test_mobygames.py`: unit coverage for URL parsing and public index shape.
- `tests/test_narrative_site.py` and `tools/validate-site.mjs`: integration and deployment guardrails.

## Success Criteria

- `node tools/validate-site.mjs` fails if MobyGames generated output lacks attribution.
- Search finds existing MobyGames-linked entities such as `Phil Scott`, `Tynesoft Computer Software company page`, and `Command & Conquer: Red Alert`.
- The site has a real user-facing MobyGames route at `/sources/mobygames/`.
- No public generated JSON includes private testimony identifiers, copied MobyGames descriptions, screenshots, cover image URLs, or scraped-page markers.
- Local and CI builds work without `MOBYGAMES_API_KEY`.

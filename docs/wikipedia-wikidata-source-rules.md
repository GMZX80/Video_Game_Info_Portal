# Wikipedia And Wikidata Source Rules

Generated: 2026-06-20

## Status

Wikipedia platform lists and linked Wikidata identifiers are secondary discovery sources. They help find titles and candidate relationships; they are not final authorities for credits.

## Wikipedia

Wikipedia rows must remain candidate records unless corroborated by stronger sources. The importer stores structured metadata only:

- title
- platform
- publisher as printed
- developer as printed
- licensed-from as printed
- release date as printed
- article URL where linked
- Wikidata QID where available
- source page title
- source URL
- revision ID and permanent URL
- CC BY-SA attribution metadata

No article prose is copied into public JSON.

## Wikidata

Wikidata statements become source assertions only when references are present in the statement. Unreferenced statements are ignored by `scripts/ingest/wikidata_games.py`.

Suggested properties currently mapped:

- `P400`: platform
- `P577`: publication date
- `P178`: developer
- `P123`: publisher
- `P136`: genre
- `P495`: country of origin
- `P856`: official website

## Promotion

Promotion from Wikipedia/Wikidata source assertion to canonical fact requires source review and, where appropriate, corroboration from stronger source families such as original credits, manuals, packaging, contemporary magazines, official structured exports, or MobyGames API metadata.

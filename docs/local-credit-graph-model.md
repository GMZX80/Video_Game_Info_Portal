# Local Credit Graph Model

Generated: 2026-06-20

## Purpose

The local credit graph lets the static GitHub Pages site search structured local records instead of relying on outbound source links alone.

## Record Types

- Source item: bibliographic or database record kept locally with a source URL/locator.
- Source assertion: one atomic claim from one source, such as `credited_as`, `programmed_by`, `published_by`, `developer_as_printed`, or `article_written_by`.
- Credit row: a reviewed local row connecting a person or organisation to a game/release role.
- External identifier: a candidate link to an external database identifier.
- Entity match decision: a review record for a candidate match.

## Promotion Rules

Source assertions do not become confirmed facts automatically. A reviewer must promote or reject them. Publisher, developer, employer, and credit relationships are separate. A credit does not establish employment.

## MobyGames

MobyGames URL-only records remain link-only evidence. `scripts/ingest/mobygames_api.py` can convert permitted API credit payloads into candidate source assertions, but it does not scrape HTML. When person-credit API coverage is unavailable, reviewed rows can be added through `data/manual/mobygames-person-credit-import.csv`.

## Public Export

`assets/data/generated/people-public.json` now exports local person credit graph records from `data/people.json`, excluding private testimony. `credits-public.json` combines curated explicit credits and local research credit rows. `public-search-index.json` includes local person credit graph records and local credit rows.

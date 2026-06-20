# Google Sheet Population Export

Generated: 2026-06-21

This export is designed for the live Google Sheet. It stores structured metadata only: no binaries, images, scans, full article text or long quotations.

| CSV | Rows |
| --- | ---: |
| `bbc_page_enrichment.csv` | 801 |
| `c64_enrichment.csv` | 2322 |
| `game_title_aliases.csv` | 0 |
| `import_log.csv` | 2 |
| `magazine_evidence.csv` | 3169 |
| `people_aliases.csv` | 0 |
| `platform_aliases.csv` | 10 |
| `publisher_aliases.csv` | 0 |
| `reconciliation_issues.csv` | 329 |
| `repo_games_master_import.csv` | 7419 |
| `repo_local_credits.csv` | 80 |
| `repo_people_credits_import.csv` | 64 |
| `repo_studios_publishers_import.csv` | 2096 |
| `source_assertions.csv` | 10589 |
| `source_evidence.csv` | 15424 |
| `wos_api_enrichment.csv` | 1 |

## MobyGames status

No `MOBYGAMES_API_KEY` is stored in this repository. Use the official API adapter only; do not scrape MobyGames HTML. If the API cannot return person-credit coverage, use the reviewed manual CSV route in `data/manual/mobygames-person-credit-import.csv`.

## Phil Scott status

The generated local credit CSV does not create a Phil Scott game credit row because the curated local `credits.jsonl` contains no Phil Scott credit record. Existing Phil Scott evidence remains candidate/secondary until a permitted API or reviewed manual source supplies local rows.

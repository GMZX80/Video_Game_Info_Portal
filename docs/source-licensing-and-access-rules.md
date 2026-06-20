# Source Licensing And Access Rules

Generated: 2026-06-20

## Global Rules

- Do not scrape MobyGames HTML pages. Use the official API or curated link-only/manual records.
- Do not commit API keys. MobyGames live imports must read `MOBYGAMES_API_KEY` from the environment.
- Do not copy full article bodies, reviews, scans, screenshots, cover art, photographs, type-in listings, ROMs, tape images, disk images, or binary game files.
- Store structured metadata, identifiers, source URLs, locators, short summaries, and evidence/assertion records only.
- Preserve source-specific uncertainty. A secondary database row is not a canonical game credit.

## Source Families

| Source | Access method | Public export | Notes |
| --- | --- | --- | --- |
| MobyGames | Official API only | Structured metadata and links | Person credits are not imported unless the API or licensed/manual data permits. |
| Wikipedia | MediaWiki API | Candidate seed metadata with CC BY-SA attribution | No article prose is copied. |
| Wikidata | Entity JSON/SPARQL-style structured data | Referenced candidate assertions | Unreferenced statements are ignored by the parser. |
| World of Spectrum | Structured API/metadata only | Candidate metadata | No files, scans, screenshots, or inlays downloaded. |
| ZXDB | Official repository/export | Candidate metadata | Use structured export, not page scraping. |
| ZXInfo | API metadata | Candidate metadata | Binary download links are not mirrored. |
| Sinclair User, CRASH, Zzap!64, Globalnet | Existing archive metadata tooling | Bibliographic metadata and short summaries | Reviewer, author, publisher, programmer roles remain distinct. |
| Stairway To Hell | Existing careful archive tooling | Metadata/testimony records | Photo captions remain testimony, not verified identities. |

## Attribution

Wikipedia-derived rows carry:

- `source_system: wikipedia`
- source page title
- source URL
- revision ID and permanent URL
- `license: CC BY-SA`
- `attribution_required: true`
- `evidence_status: secondary seed`
- `public_claim_status: candidate`

Wikidata rows carry source item IDs, referenced statement data, and `license: CC0`.

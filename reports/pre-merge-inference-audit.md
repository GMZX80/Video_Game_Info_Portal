# Pre-Merge Inference Audit

Generated: 2026-06-18

## Scope

Searched canonical JSONL and public JSON for inference paths that would overstate evidence before PR #1 is merged.

## Findings

| Inference risk | Result | Action |
| --- | --- | --- |
| Article byline became a game credit | No credit records exist in `data/curated/credits.jsonl`; byline text is stored only on source items. | No demotion needed. |
| Reviewer became programmer | No reviewer/programmer role mapping exists; no public contributor credits are generated. | No demotion needed. |
| Publisher became developer | `data/curated/releases.jsonl` has 248 releases and 0 developer fields populated; public releases now label developer status as `Attribution awaiting review`. | Added public release labels. |
| Label became legal company | Zeppelin and Zeppelin Games are retained as separate names in the North East review queue; no legal successor or company-merge claim is exported from magazine index evidence. | Kept out of confirmed results. |
| Keyword proximity became location evidence | 11 keyword/name/place leads remain `candidate`; Stockton-derived records are not treated as Stockton-on-Tees evidence. | Kept candidates out of confirmed results. |
| Person credit became employment evidence | Canonical magazine datastore has 0 person records and 0 credits; the separate research validator continues to block inferred Tynesoft employment claims. | No public biographies added. |
| Staff heritage became legal continuity | Static Phase 0 relationships still require dashed display for staff/heritage/uncertain relationships; no generated magazine relationship asserts legal continuity. | Existing validator retained. |
| Game title aliases merged without platform/date support | `data/curated/games.jsonl` has 0 populated `title_variants`; game index scope now states title records are magazine/index records, not complete release histories. | Added public scope note. |

## Correction Made

The classifier previously marked known North East organisation names as `strongly supported` when a magazine source only supplied index or publisher/label metadata. That was an inference problem. The audit demoted those rows:

- confirmed before audit: 75
- confirmed after audit: 0
- probable after audit: 94
- candidates after audit: 11
- records promoted: 0

All North East public cards now include `record_label`. Current North East labels are:

- `Publisher only`: 94 probable rows
- `Attribution awaiting review`: 11 candidate rows

## Commands / Checks Used

- Counted `data/curated/credits.jsonl`, `data/curated/releases.jsonl`, `data/curated/north-east-connections.jsonl`, `data/curated/games.jsonl`, `data/curated/organisations.jsonl`, and `data/curated/people.jsonl`.
- Searched `data/curated` and `assets/data/generated` for byline, reviewer, programmer, developer, publisher, legal successor, staff heritage, employee, aliases, location and keyword patterns.
- Regenerated public JSON with `python -m scripts.build_all --skip-fetch`.

## Residual Risk

This audit checks the current generated data model. It does not resolve the underlying history of each company or person; it prevents the public site from presenting those unresolved links as confirmed.

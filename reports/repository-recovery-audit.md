# Repository recovery audit

Generated: 2026-06-20

## Branch state audited

- Main SHA: `d2c62a2e90a10715b888b3910c72efe3e2e77a44`
- PR #1 branch: `codex/magazine-evidence-datastore`
- PR #1 audited head before this repair: `dc92e41fa1e92013a934457cecb3281f7012ddfc`
- PR #2 branch: `codex/narrative-revamp-foundation`
- PR #2 audited head: `8160d77ee280b587934c9a5ad54259d4667d6511`
- PR #1 merge base with main: `d2c62a2e90a10715b888b3910c72efe3e2e77a44`
- PR #2 merge base with PR #1: `46dfe223359acbefffee847324eec563a3ba983f`
- PR #2 is missing 29 PR #1 commits after that merge base.

## Workflow files

- `.github/workflows/pages.yml` builds committed data, builds `dist/`, validates generated files, and deploys only `dist/`.
- `.github/workflows/validate.yml` now runs pull-request validation without external crawls and has `validation-${{ github.ref }}` concurrency cancellation.
- The detailed archive refresh is now manual-only through `workflow_dispatch` with `refresh_detailed_archives: true`.
- `.github/deep-archive-request` was obsolete trigger state and has been removed.

## Generated-files-current failure

The failing PR #1 check was reproduced from the GitHub Actions log and locally.

Root cause:

- `python -m scripts.build_all --skip-fetch` was deterministic.
- The committed `reports/ingest-summary.md` was stale.
- The stale report still described the pre-deep-ingest state: 72 Sinclair User issues, 681 Sinclair source items, 9,775 canonical source items, 7,896 games and 248 releases.
- A fresh build from committed raw data produced the deep-ingest report state.

Initial fresh-build diff:

- Only `reports/ingest-summary.md` changed.
- No repeated timestamp, hash, ordering or traversal-order nondeterminism was found in that first reproduction.

The failure was not fixed by disabling validation. The generated report and canonical outputs were regenerated from the committed inputs.

## Detailed-ingest findings

The advertised detailed runner was broken: `scripts/ingest/run_detailed.py` imported missing `run_detailed_v2`.

Repair:

- Replaced `run_detailed.py` with the supported detailed entry point.
- Wired Sinclair User detailed crawl, Sinclair supplement, Stairway crawl, Stairway supplement, archive post-processing, canonical rebuild, media merge and audit writing.
- Kept `sinclair_supplement.py` and `stairway_supplement.py` as support modules, not competing runner entry points.

Detailed run performed:

```text
python -m scripts.ingest.run_detailed --resume --include-catalogues --accessed-date 2026-06-19
```

Result highlights:

- Sinclair User: 132 numbered issue pages fetched by the base detailed crawl, 578 article pages discovered and fetched, zero fetch failures.
- Sinclair supplement: 133 physical issue pages discovered, issue `058a` preserved, 3,845 unlinked software-section entries found, 73 type-in entries found, zero supplement failures.
- Post-processing: 3,801 ambiguous Sinclair software-section prose rows moved to `data/raw/sinclair-user/unresolved-software-lines.jsonl` instead of being published as complete source/game records.
- Stairway: 76 pages fetched, 801 retained source items after cleanup, 27 catalogue navigation rows removed, three download directories reclassified as deliberately excluded, one genuine remaining failed page.
- Remaining Stairway failure: `https://www.stairwaytohell.com/electron/homrpage.html` returned 404.

## Corrected canonical counts

After separating unresolved Sinclair prose from canonical source items:

- Source items: 11,271
- Games: 8,467
- Platform releases: 715
- People: 361
- Explicit source-linked credits: 80
- Media records: 2
- Photograph identification testimony records: 14
- North East confirmed or strongly supported: 0
- North East probable: 147
- North East candidates: 65

The earlier 15,072 source-item count included unresolved Sinclair issue-page prose that is now retained for review but not exported as confirmed source/game evidence.

## Data safety checks

- Added schemas for mentions, relationships, media assets, photo identifications and page inventory rows.
- Added referential checks for credits, evidence, claims, mentions, media assets, photo identifications, issues and releases.
- Added invariants preventing first-person photograph testimony from being exported as verified without approval.
- Public JSON and `dist/` validation still reject private Google Drive material and sensitive private/admin text.

## Generated dates and ordering

- Generated reports and JSON continue to use stable source dates such as `2026-06-18` and `2026-06-19`.
- No use of `date.today()`, current time, `datetime.now()` or `utcnow()` was found in the generation path.
- JSONL and generated JSON writers sort keys and use deterministic row sort keys where supported.

## Duplicate or obsolete files

- Broken `run_detailed.py` compatibility stub was replaced.
- `.github/deep-archive-request` was removed.
- Top-level `scripts/build_sqlite.py`, `scripts/classify_north_east.py`, `scripts/export_public_json.py`, `scripts/normalise.py` and `scripts/validate_data.py` are compatibility wrappers over `scripts.ingest.*`, not independent pipelines.
- `sinclair_supplement.py`, `stairway_supplement.py` and `archive_postprocess.py` are support modules called by the single detailed runner.

## PR #2 relationship

PR #2 is stacked on PR #1 at `46dfe223359acbefffee847324eec563a3ba983f`. It must be rebased or merged onto the repaired PR #1/main state after PR #1 lands, otherwise it will retain stale datastore counts and duplicate datastore commits in its diff.

## Working tree and ignored files

Ignored local build/runtime directories observed:

- `.cache/`
- `.pytest_cache/`
- `.venv/`
- `build/`
- `dist/`

These are not part of the committed public artifact.

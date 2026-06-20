# Archive Adapters

Adapters live under `scripts/ingest/` and use a shared respectful fetcher with caching, resumable requests, `robots.txt` handling, per-host rate limiting, retries, content hashes, fetch status and canonical URLs.

## Index-level commands

```bash
python -m scripts.ingest.sinclair_user --indexes-only --resume
python -m scripts.ingest.crash --indexes-only --resume
python -m scripts.ingest.zzap64 --indexes-only --resume
python -m scripts.ingest.globalnet --indexes-only --resume
python -m scripts.ingest.stairway --indexes-only --resume
```

## Detailed Sinclair User and Stairway capture

```bash
python -m scripts.ingest.run_detailed --resume
```

Add Stairway's BBC and Electron HTML catalogue pages while still excluding software downloads and binary images:

```bash
python -m scripts.ingest.run_detailed --resume --include-catalogues
```

Use a bounded development run before a full refresh:

```bash
python -m scripts.ingest.run_detailed --max-pages 25
```

`--max-pages` applies separately to Sinclair User article pages and Stairway pages. A value of zero means no explicit limit.

## Sinclair User

The index-level adapter inventories the archive home and contents pages. This fixes the previous assumption that `contents.htm` alone represented the full physical issue run.

Detailed mode then:

1. discovers numbered issue links from the archive home page;
2. fetches each issue page;
3. records issue date, staff roles and linked article pages;
4. follows relevant review, interview, profile, feature, news, hardware and listing pages;
5. extracts structured fields such as publisher, programmer, price, memory, controls, rating and reviewer when printed;
6. keeps article authors, reviewers and game contributors as distinct relationships;
7. stores an editorial metadata summary rather than the article body.

The issue and article page inventory is written to:

- `data/raw/sinclair-user/page-inventory.jsonl`
- `data/raw/source-page-inventory.jsonl`

## Stairway To Hell

The Stairway adapter begins with the curated source catalogue in `research/stairway-catalogue.csv`, the Tynesoft article, Lost & Found and the archive credits page. In detailed mode it follows eligible internal HTML links in the following research sections:

- author profiles, portfolios and interviews;
- historical and technical articles;
- Lost & Found and unreleased-game records;
- provenance and credits pages;
- optional BBC and Electron HTML catalogue pages.

It deliberately excludes:

- disk and tape images;
- UEF, SSD, DSD, ADF, TZX, ZIP and other binary downloads;
- ROMs, audio files and executables;
- complete magazine scans;
- full-resolution image collections.

The adapter preserves the distinction between an original magazine and Stairway as archive host. It also stores Kevin Blake's Tynesoft photograph captions as retrospective identification testimony, not as visual identification or independently verified fact.

Stairway output is written to:

- `data/raw/stairway/source-items.jsonl`
- `data/raw/stairway/photo-identifications.jsonl`
- `data/raw/stairway/page-inventory.jsonl`
- `data/raw/source-page-inventory.jsonl`

## Other adapters

CRASH imports the root issue list and issue index pages.

Zzap!64 imports ZzapBible game, review and feature indexes while respecting the `/fullissues` robots exclusion.

Globalnet imports the live SPOT plain-data index and TTFn type-in tables. Program listings and archive files are not republished; only metadata is catalogued.

## Coverage and failure handling

Every detailed fetch receives an inventory outcome:

- fetched and parsed;
- failed;
- blocked by `robots.txt`;
- deliberately excluded;
- discovered but pending because of a page limit.

If a section is unavailable, record the failed URL rather than fabricating a record. Any later Wayback fallback must preserve the original live URL, archive URL and snapshot timestamp as separate fields.

# Detailed Sinclair User and Stairway To Hell capture

The first datastore import was intentionally conservative. It recorded magazine issue and contents indexes, but it did not inspect most individual Sinclair User articles and it represented Stairway To Hell through a small hand-curated source catalogue only.

This detailed capture adds page-level evidence while retaining the project's copyright and historical safeguards.

## Research goals

The detailed process is intended to answer questions that an issue index alone cannot answer:

- Who is explicitly named as programmer, author, conversion programmer, reviewer or article writer?
- Which company is printed as publisher or label?
- Which platform-specific release is being discussed?
- What issue and date supplied the evidence?
- Is a source contemporary or retrospective?
- Does a photograph caption identify someone, and who supplied that identification?
- Are later recollections consistent with contemporary profiles and credits?

The process does **not** infer employment from a game credit, a developer from a publisher field, or a North East development location from a nearby company name.

## Running the capture

Create a Python environment and install the repository requirements, then run:

```bash
python -m scripts.ingest.run_detailed --resume
```

To include Stairway's BBC Micro and Acorn Electron HTML catalogue pages:

```bash
python -m scripts.ingest.run_detailed --resume --include-catalogues
```

For a short parser and network check:

```bash
python -m scripts.ingest.run_detailed --max-pages 25
```

A complete external refresh is deliberately separate from ordinary CI. Normal validation uses the committed raw and canonical records and does not repeatedly request archival websites.

## Sinclair User method

The adapter now uses two layers of issue discovery:

1. the numbered issue grid on the archive homepage;
2. the historic `contents.htm` index.

The two sources are merged by issue number. This avoids treating the partial contents index as the complete physical run.

Detailed mode then visits each issue page and records:

- issue number and cover date;
- editorial staff and named contributors;
- software, feature, hardware, listing and regular-section links;
- article URL and issue relationship;
- printed company or label where it appears beside a linked item.

Individual article pages are parsed only for structured metadata. Depending on the page, fields may include:

- title;
- article type;
- article writer or reviewer;
- programmer or author as explicitly printed;
- publisher or label as explicitly printed;
- price;
- memory requirement;
- controls;
- rating;
- archive URL and issue locator.

The article body is not saved. The source record contains a short editorial summary generated only from structured fields.

## Stairway To Hell method

The Stairway adapter begins with the project's curated source list and several historically important seed pages. It then follows eligible internal HTML links in research-relevant sections.

The adapter distinguishes:

- contemporary magazine profiles;
- contemporary technical articles;
- retrospective interviews;
- first-person portfolios;
- retrospective recollections;
- development diaries;
- game catalogue entries;
- Lost & Found and unreleased-game records;
- photograph and caption records;
- provenance and credits pages.

Where Stairway republishes a magazine article, the original publication, author and date are preserved separately from Stairway's role as archive host.

## Photograph identifications

The Tynesoft photograph parser records names only when they are printed in Kevin Blake's retrospective caption. These records are stored as:

> First-person retrospective identification testimony — unconfirmed pending independent corroboration.

No facial recognition, visual comparison or inference from appearance is used.

A public identification should be promoted only after its position, name and source have been reviewed and, where possible, corroborated by another participant or contemporary caption.

## Lost & Found records

Lost & Found pages may contain several accounts of the same unreleased project. The ingest stores:

- title;
- named author where printed;
- company or label where printed;
- archive status such as `LOST` or `FOUND`;
- named testimony sources;
- source URL.

It does not store the recollection text. Contradictory accounts remain separate evidence rather than being silently reconciled.

## Exclusions

The detailed crawl does not download or commit:

- complete magazine articles;
- full program listings;
- magazine scans;
- screenshots or photograph collections;
- UEF, SSD, DSD, ADF, TZX, TAP or ROM files;
- ZIP, 7z or other software archives;
- disk or tape images;
- audio files or executables.

Links to these resources may be counted as deliberately excluded in the coverage report.

## Page inventory

Every requested or discovered research page receives an outcome in:

```text
data/raw/source-page-inventory.jsonl
```

Archive-specific inventories are also generated under:

```text
data/raw/sinclair-user/page-inventory.jsonl
data/raw/stairway/page-inventory.jsonl
```

Possible outcomes include:

- fetched and parsed;
- failed;
- blocked by `robots.txt`;
- deliberately excluded;
- discovered but pending because of a page limit.

The project should not describe an archive as completely captured unless every discovered relevant HTML page has a recorded outcome.

## Canonical integration

After fetching, the detailed runner:

1. normalises raw records into canonical JSONL;
2. creates people records from explicitly printed names;
3. creates credits only from explicit game-related roles;
4. keeps article writers and reviewers separate from game credits;
5. imports photograph-caption testimony;
6. reruns North East candidate classification;
7. rebuilds SQLite and public JSON;
8. validates the repository;
9. writes `reports/deep-ingest-summary.md`.

## Review rules

Detailed ingestion increases the amount of evidence; it does not automatically increase certainty.

New records should remain candidates until a curator has checked:

- the exact source page;
- the role as printed;
- the platform version;
- the company relationship;
- the geographic claim;
- whether the source is contemporary or retrospective;
- whether a similarly named person or organisation could be involved.

## GitHub Actions refresh

The repository includes a controlled refresh workflow. It is separate from ordinary pull-request validation because it performs external requests and may take a substantial amount of time.

The refresh workflow:

- runs parser tests first;
- performs the detailed capture at a respectful request rate;
- rebuilds canonical and public outputs;
- validates the static site;
- commits changed metadata back to the research branch.

The workflow must be reviewed before it is enabled on `main`, particularly its page limit, duration and permission to commit generated metadata.

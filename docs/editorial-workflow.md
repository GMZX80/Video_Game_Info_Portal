# Editorial Workflow

The North East workflow is:

```text
discovered -> candidate -> source inspected -> entity reconciled -> claim recorded -> evidence assessed -> approved or rejected -> public export
```

Entity reconciliation is intentionally cautious:

```bash
python -m scripts.reconcile_entities
```

The queue is written to `research/entity-resolution-queue.csv`; decisions are not auto-applied. Preserve original printed spellings, distinguish legal organisations from labels, and keep similarly titled games separate unless platform/date evidence resolves them.

To add a game credit, add a `credits.jsonl` row with the printed role, mapped role only when justified, source ID, confidence, and notes. A review byline is not a game credit.

To add a photograph identification, record the source page, printed caption, issue/date, photographer if known, and evidence basis. Do not visually identify extra faces or expose uncited identifications.

After edits, regenerate and validate:

```bash
python -m scripts.build_all --skip-fetch
node tools/validate-site.mjs
```

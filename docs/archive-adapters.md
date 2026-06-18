# Archive Adapters

Adapters live under `scripts/ingest/` and use a shared respectful fetcher with cache, resume, robots handling, per-host rate limiting, content hashes, fetch status, and canonical URLs.

Commands:

```bash
python -m scripts.ingest.sinclair_user --indexes-only --resume
python -m scripts.ingest.crash --indexes-only --resume
python -m scripts.ingest.zzap64 --indexes-only --resume
python -m scripts.ingest.globalnet --indexes-only --resume
```

Sinclair User imports the SUMO contents/index page.

CRASH imports the root issue list and issue index pages.

Zzap!64 imports ZzapBible/game and review/feature indexes, while respecting the `/fullissues` robots exclusion.

Globalnet imports the live SPOT plain data zip and TTFn type-in tables. Listings and zip contents are not republished; only metadata is catalogued.

If a section is unavailable, record the failed URL in reports rather than fabricating records. Wayback fallback should preserve both original live URL and snapshot timestamp.

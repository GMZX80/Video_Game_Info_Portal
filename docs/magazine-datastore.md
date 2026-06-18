# Magazine Evidence Datastore

The datastore uses canonical JSON Lines as the version-controlled source of truth. Each row is one JSON object with a stable identifier, so reviews can inspect textual diffs without resolving binary database conflicts.

The generated SQLite database lives at `build/video-game-history.sqlite` and is reproducible:

```bash
python -m scripts.build_sqlite
```

The public site never opens SQLite. Browser-facing data is exported to `assets/data/generated/`:

```bash
python -m scripts.export_public_json
```

Run the full local build from committed raw records with:

```bash
python -m scripts.build_all --skip-fetch
```

Run a fresh external refresh manually with:

```bash
python -m scripts.build_all --resume
```

External crawling is intentionally not part of normal CI.

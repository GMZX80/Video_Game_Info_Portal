# Publishing with GitHub Pages

The repository includes a GitHub Actions workflow at `.github/workflows/pages.yml`.
Every push to `main` publishes the static site to:

`https://gmzx80.github.io/Video_Game_Info_Portal/`

The first run uses `actions/configure-pages` to enable Pages automatically. If an
organisation or account policy prevents automatic enablement, select **GitHub
Actions** under **Settings → Pages → Build and deployment** once, then re-run the
workflow.

## Local preview

```bash
python3 -m http.server 8000
```

Open `http://localhost:8000`.

## Pre-publish validation

```bash
node tools/validate-site.mjs
```

This checks required Phase 0 editorial beats, relative internal assets, source
references and the Pages workflow before the next push to `main`.

# Newcastle’s Video Game Technology Lab

## Phase 0 — From Play to Pay

A living personal, regional and technical history of Newcastle University’s Game Technology Lab.

Phase 0 follows the chain of developments that made the later laboratory possible:

- experimental electronic and computer play;
- Ralph Baer, the pioneer patents and the raster television;
- the arrival of affordable programmable computers in British homes and schools;
- Clive Sinclair, the ZX80, ZX81 and ZX Spectrum;
- BASIC, Z80 machine code and software distributed through printed listings;
- the transformation of bedroom coding, schools, clubs and freelance work into commercial games production;
- Tynesoft, Icon/Audiogenic, Reflections, Teesside and the emergence of a North East development network;
- later lineages as a short bridge into the Game Technology Lab story.

The intended public site is:

**https://gmzx80.github.io/Video_Game_Info_Portal/**

## Why this is a living document

This repository is both a public history and the source material for a one-hour talk. It is designed to grow phase by phase while preserving citations, image provenance, talk cues and interactive demonstrations.

Current status: **Phase 0, draft 0.2**.

## Repository structure

```text
.
├── index.html                 # Phase 0 public page
├── assets/
│   ├── css/site.css           # CRT-inspired visual system
│   ├── data/                  # Sources, claims, places, organisations, people, games, events and relationships
│   ├── js/site.js             # JSON loading, timeline, map, lineage view, talk mode and demonstrations
│   └── images/                # Project and archival images
├── docs/
│   └── US3728480-brown-box-patent.pdf
├── research/
│   ├── editorial-method.md
│   ├── north-east-source-register.csv
│   ├── north-east-claims-register.csv
│   ├── unresolved-questions.md
│   └── incoming/supplied-north-east-timeline.html
├── tools/
│   └── validate-site.mjs      # Static content, asset and workflow checks
├── DEPLOY.md                  # GitHub Pages publishing instructions
└── .nojekyll                  # Publish the static files unchanged
```

## Local preview

The site contains only static HTML, CSS and JavaScript. From the repository root:

```bash
python -m http.server 8000
```

Then open `http://localhost:8000`.

## Validation

Run the static validation pass before publishing:

```bash
node tools/validate-site.mjs
```

The script checks required Phase 0 content, relative internal asset paths, timeline source references and the GitHub Pages workflow.

## Google Sheet export

The live UK game-development spreadsheet can be populated from committed, source-backed CSV exports:

```bash
python3 -m scripts.export_google_sheet_seed
```

The exporter reads `data/curated/*.jsonl`, writes metadata-only CSV files to `data/google-sheet-export/`, and updates `reports/google-sheet-population.md`. It does not fetch external pages, does not scrape MobyGames HTML, and does not copy binaries, screenshots, scans or long article text. If a MobyGames person-credit import is needed, set `MOBYGAMES_API_KEY` locally for the official API route or use the reviewed template at `data/manual/mobygames-person-credit-import.csv`.

## Interaction

- Filter the historical timeline by global origins, UK context, North East, sub-region, company, people, games, technology, business, confirmed and uncertain material.
- Select an event to see its act, evidence status, detail and sources.
- Explore the schematic regional map, organisation profiles, people/practice section, relationship view and national comparison table.
- Use the Spectrum-inspired type-in demonstration to run, break and deliberately damage a short BASIC listing.
- Select stages in the publishing pipeline to explore how code becomes a commercial product.
- Switch to **Talk mode** for larger presentation-oriented typography. The `T` key also toggles the mode.
- Use the browser’s print command to produce a simplified document view.

## Research foundation

The opening patent argument draws particularly on Graham Morgan and Jeffrey K. Lee’s Newcastle University technical report, *Controversy in Video Game Invention: The Infallible Pioneer Patents*, together with Graham Morgan’s CSC3224 teaching archive.

The public page includes a full source catalogue. Material taken from private teaching documents is labelled as author archive material rather than given a public link. The `research/` directory records source provenance, claim status and unresolved historical questions.

## Image provenance

- Newcastle CRT hero: project artwork created for this history.
- Ralph Baer portrait: Michael Schilling, CC BY-SA 3.0.
- Magnavox Odyssey product photograph: Evan-Amos, public domain.
- Patent drawing: public-domain United States patent record.
- Tynesoft group photographs: supplied by Graham Morgan; names, dates and detailed provenance are still being researched.

No project-wide reuse licence has yet been assigned. Individual third-party materials retain their own stated terms.

## Planned phases

- **Phase 0 — From Play to Pay:** origins, UK home computing and Tynesoft.
- **Phase 1 — Building the Game Technology Lab:** the research, teaching, rooms, machines, people and industry relationships behind the 2008 lab.
- Later phases will follow the lab’s projects, collaborations, students, publications and influence.

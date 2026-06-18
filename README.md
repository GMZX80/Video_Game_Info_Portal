# Newcastle’s Video Game Technology Lab

## Phase 0 — From Play to Pay

A living personal, regional and technical history of Newcastle University’s Game Technology Lab.

Phase 0 follows the chain of developments that made the later laboratory possible:

- experimental electronic and computer play;
- Ralph Baer, the pioneer patents and the raster television;
- the arrival of affordable programmable computers in British homes and schools;
- Clive Sinclair, the ZX80, ZX81 and ZX Spectrum;
- BASIC, Z80 machine code and software distributed through printed listings;
- the transformation of bedroom coding into a commercial games industry;
- Tynesoft and the emergence of a North East development community.

The intended public site is:

**https://gmzx80.github.io/Video_Game_Info_Portal/**

## Why this is a living document

This repository is both a public history and the source material for a one-hour talk. It is designed to grow phase by phase while preserving citations, image provenance, talk cues and interactive demonstrations.

Current status: **Phase 0, draft 0.1**.

## Repository structure

```text
.
├── index.html                 # Phase 0 public page
├── assets/
│   ├── css/site.css           # CRT-inspired visual system
│   ├── js/data.js             # Timeline and source data
│   ├── js/site.js             # Timeline, talk mode and demonstrations
│   └── images/                # Project and archival images
├── docs/
│   └── US3728480-brown-box-patent.pdf
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

## Interaction

- Filter the historical timeline by origins, home computers, code culture, business and the North East.
- Select an event to see its display, access and commercial significance, sources and talk cue.
- Use the Spectrum-inspired type-in demonstration to run, break and deliberately damage a short BASIC listing.
- Select stages in the publishing pipeline to explore how code becomes a commercial product.
- Switch to **Talk mode** for larger presentation-oriented typography. The `T` key also toggles the mode.
- Use the browser’s print command to produce a simplified document view.

## Research foundation

The opening patent argument draws particularly on Graham Morgan and Jeffrey K. Lee’s Newcastle University technical report, *Controversy in Video Game Invention: The Infallible Pioneer Patents*, together with Graham Morgan’s CSC3224 teaching archive.

The public page includes a full source catalogue. Material taken from private teaching documents is labelled as author archive material rather than given a public link.

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

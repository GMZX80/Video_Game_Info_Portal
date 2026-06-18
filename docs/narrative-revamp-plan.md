# Narrative Revamp Plan

Generated: 2026-06-18

## Goal

Rebuild the public site as a narrative-first Phase 0 history while keeping the magazine datastore, canonical JSONL, generated SQLite, claims, source registers and public JSON exports as the evidence infrastructure.

The governing principle is: narrative first; evidence always within reach.

## Public Modes

The first narrative-foundation pull request creates four connected public modes:

| Mode | Route | Purpose |
| --- | --- | --- |
| Story | `/`, `/stories/`, `/stories/<slug>/` | Long-form, character-led narrative features. |
| Explore | `/people/`, `/studios/`, `/games/`, `/places/`, `/magazines/`, `/timeline/`, `/lineages/`, `/collections/` | Browse people, studios, games, places and magazine records without making the database the opening experience. |
| Evidence | `/research/`, `/research/corrections/` | Explain sources, uncertainty, corrections, permissions and contribution routes. |
| Talk | `/talk/` | A projection-friendly sequence generated from the same content model. |

Story is the default. Explore and Evidence remain visible, but they support the public reading experience rather than replacing it.

## Information Architecture

Generate route-directory pages so GitHub Pages can serve direct refreshes:

- `/`
- `/phase-0/`
- `/stories/`
- `/people/`
- `/studios/`
- `/games/`
- `/places/`
- `/magazines/`
- `/timeline/`
- `/lineages/`
- `/collections/`
- `/research/`
- `/research/corrections/`
- `/contribute/`
- `/talk/`
- `/search/`

The legacy North East Collection route remains available as `north-east-collection.html` for compatibility, but the new route-based collection entry is `/collections/`.

## Phase 0 Story Spine

The full Phase 0 narrative remains planned as:

1. Prologue: A Photograph from Blaydon
2. Chapter 1: The Wrong Question
3. Chapter 2: Britain Switches On
4. Chapter 3: Code Through the Letterbox
5. Chapter 4: Before the Studios
6. Chapter 5: Blaydon Becomes a Software Town
7. Chapter 6: Eighteen and Shipping Games
8. Chapter 7: One Game, Many Machines
9. Chapter 8: The Tynesoft Generation
10. Chapter 9: New Companies from Old Knowledge
11. Chapter 10: Reflections Before Driver
12. Chapter 11: A Parallel Road Through Teesside
13. Chapter 12: Britain Was a Network Too
14. Epilogue: Why a Game Technology Lab Became Possible

The first pull request implements a small foundation slice. Because the Blaydon photograph story still needs stronger rights and identification records, the exemplar story is `Code Through the Letterbox`.

## First PR Scope

This branch implements:

- the five editorial planning documents;
- a Markdown plus YAML front matter content model;
- a static page generator;
- route-directory output into `dist/`;
- revised navigation around Story, Explore, Evidence and Talk;
- a redesigned generated homepage;
- a Phase 0 hub;
- Story, Explore, Evidence and Talk entry points;
- one exemplar long-form story;
- one exemplar person profile;
- one exemplar studio profile;
- three exemplar game pages, one for each public game tier;
- source notes and evidence drawers;
- a public corrections page;
- structured GitHub issue templates;
- build, content, route, leakage and static validation.

It does not attempt to write every story, fill every person page, or resolve photograph identifications.

## Exemplar Content

| Content | Route | Level |
| --- | --- | --- |
| Code Through the Letterbox | `/stories/code-through-the-letterbox/` | Flagship narrative story |
| Gary Partis | `/people/gary-partis/` | Curated profile |
| Tynesoft | `/studios/tynesoft/` | Curated studio profile |
| OXO | `/games/oxo/` | Tier 1: full narrative game story |
| Doctor Who and the Mines of Terror | `/games/doctor-who-and-the-mines-of-terror/` | Tier 2: enriched profile |
| Super Gran | `/games/super-gran/` | Tier 3: archive index record |

## Build Architecture

1. Existing ingest/build commands continue to generate canonical data and public JSON.
2. `scripts/build_narrative_site.py` reads Markdown content, validates front matter, resolves public sources/claims/entities and renders route-directory HTML.
3. `scripts/build_dist.py` copies public assets, invokes the narrative generator into `dist/`, copies compatibility routes and blocks private/source-only material.
4. GitHub Pages uploads only `dist/`.

## Validation Architecture

Validation is split across Python tests and the Node site validator:

- content schema and front matter;
- missing entity IDs;
- missing source IDs;
- missing claim IDs;
- quote provenance;
- photograph permission status;
- route generation;
- root-relative asset paths;
- private data leakage;
- direct refresh-safe `index.html` routes;
- public label and content-level checks;
- existing datastore/schema tests.

## Roadmap For Later Pull Requests

1. Tynesoft package: rights-cleared photo treatment, Blaydon story, company chronology, products and unresolved identifications.
2. Magazines and games: richer magazine issue pages, review profiles and platform-specific release pages.
3. People and careers: carefully fact-checked person pages with verified credits and non-employment caveats.
4. Studios and lineages: studio profile expansion with legal continuity separated from staff heritage.
5. Teesside and national context: a separate Teesside orbit and "Britain Was a Network Too" expansion.
6. Talk mode polish: final projection sequence, presenter notes and print export.

## Open Editorial Questions

- Which Tynesoft photograph permissions are explicit enough for publication beyond cautious captions?
- Which private testimony has explicit quotation permission?
- Which records can move from probable to confirmed after record-level source inspection?
- Which early Reflections facts can be supported by contemporary magazine or official records?
- Which later Phase 1 bridge facts about Graham Morgan should be included without constructing unsupported personal chronology?

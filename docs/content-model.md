# Content Model

Generated: 2026-06-18

## Directory Structure

Narrative content lives in:

```text
content/
  stories/
  people/
  studios/
  games/
  places/
  magazines/
  collections/
```

Content is Markdown with YAML front matter. Canonical evidence remains in existing JSON, JSONL and research registers. Do not duplicate source facts in prose metadata.

## Required Front Matter

Every content file must include:

```yaml
id: story-code-letterbox
title: Code Through the Letterbox
standfirst: A short public summary.
story_type: flagship-narrative
content_level: Flagship narrative story
route: stories/code-through-the-letterbox
linked_entity_ids:
  - event-code-paper
linked_source_ids:
  - gazzard-typeins
linked_claim_ids:
  - claim-paper-code-network
editorial_status: public-prototype
fact_check_status: checked
media_permission_status: no-restricted-media
author: Codex
reviewer: Graham Morgan
last_reviewed: 2026-06-18
publication_date: 2026-06-18
update_date: 2026-06-18
related_content:
  - games/doctor-who-and-the-mines-of-terror
```

## Optional Front Matter

```yaml
mode: story
profile_kind: person
game_tier: "Tier 2: Enriched profile"
record_level: Enriched archive record
public_record_labels:
  - Platform-specific release
  - Publisher only
deck_label: Chapter 3
media:
  - tynesoft-team-group
quotes: []
open_questions:
  - What source would move this from probable to confirmed?
```

## Public Content Levels

| Level | Use |
| --- | --- |
| Flagship narrative story | Long-form chapter or prologue. |
| Curated profile | Person, studio, place, magazine or collection page with selected evidence. |
| Enriched archive record | A game or source record with context and clear limits. |
| Index-only archive record | A public pointer to an indexed record, not a complete history. |

## Game Page Tiers

| Tier | Meaning |
| --- | --- |
| Tier 1: Full narrative game story | A game has enough evidence for a story-led page. |
| Tier 2: Enriched profile | A game has useful context but not a full narrative. |
| Tier 3: Archive index record | A game is present as an index/source record only. |

Every game page must display both `game_tier` and `record_level`.

## Static Generator Outputs

The narrative generator creates:

- route-directory HTML in `dist/`;
- `assets/data/generated/narrative-search-index.json`;
- source drawers on pages with linked evidence;
- a public corrections route;
- a talk route generated from the same content model.

## Validation

The generator validates:

- required front matter;
- duplicate content IDs;
- duplicate routes;
- missing entity IDs;
- missing source IDs;
- missing claim IDs;
- private-data leakage;
- incomplete editorial and fact-check statuses;
- unapproved media states;
- generated route files.

The validator deliberately treats the content model as a publication gate, not just a template convenience.

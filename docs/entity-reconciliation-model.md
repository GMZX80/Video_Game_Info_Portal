# Entity Reconciliation Model

Generated: 2026-06-20

## Principle

External records create assertions and review queues. They do not overwrite canonical people, games, organisations, releases, credits, or North East classifications.

## Stages

1. Discover: adapters create source items, source assertions, and external identifiers.
2. Reconcile: deterministic matching writes CSV queues with suggested actions.
3. Promote: a reviewer creates or edits canonical records only after corroboration.

## New Files

- `data/curated/source-assertions.jsonl`
- `data/curated/external-identifiers.jsonl`
- `reports/reconciliation-queue-games.csv`
- `reports/reconciliation-queue-people.csv`
- `reports/reconciliation-queue-organisations.csv`
- `reports/reconciliation-ambiguous-people.csv`
- `reports/reconciliation-rejected.csv`

## Matching Behavior

Exact normalised label matches are queued as `review-existing-match`. Missing exact matches are queued as `review-new-candidate`. Duplicate external labels are flagged in `conflict_notes` and are not merged automatically.

## Credit Safety

A source assertion can say that a row prints a developer, publisher, role, or date. It does not become a `credit` record until a reviewer promotes it with source context. A credit does not establish employment.

# Person Credit Coverage Gap

Generated: 2026-06-20

## Current Gap

The canonical `credits.jsonl` file still contains 80 explicit source-linked credits. The new external integration improves discovery but deliberately does not auto-promote Wikipedia, Wikidata, MobyGames links, or secondary database rows into credits.

## Why Phil Scott Was Sparse

Before this branch, public search relied mostly on internal research records, curated source links, and magazine/source records. The site had MobyGames links for Phil Scott and Trolls, but not a licensed/API person-credit import.

## What Changed

- Wikipedia platform-list assertions are now searchable as candidate source assertions.
- MobyGames official-API tooling exists but did not run live because `MOBYGAMES_API_KEY` was not available.
- External source assertions and identifiers now have reconciliation queues.

## People Requiring Review

| Person | Current route |
| --- | --- |
| Phil Scott | Review curated MobyGames links, Wikipedia seed assertions, internal research person record, and manual/licensed people-credit sources. |
| Kevin Blake | Reconcile existing internal sources and Stairway evidence before creating or expanding credits. |
| Gary Partis | Existing public person page and source trail remain primary; use external assertions only as candidate leads. |
| Peter Scott | Keep distinct from Phil Scott unless reviewed evidence proves a relationship or identity link. |
| Dave Croft | Use Stairway and magazine/source records carefully, preserving article author versus game credit. |
| Brian Jobling | Needs source-level corroboration before any new canonical credit. |
| Martin Edmondson | Needs external identifier review and stronger source corroboration before promotion. |
| Nicholas Chamberlain | Needs source-level corroboration before any new canonical credit. |
| Peter Johnson | Needs disambiguation and source-level corroboration before any new canonical credit. |

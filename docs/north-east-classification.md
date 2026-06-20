# North East Classification

A keyword match is only a candidate. A record enters the confirmed North East Collection only when a source explicitly supports the connection.

Public statuses are:

- `verified`
- `strongly supported`

Research-only or separated statuses are:

- `probable`
- `candidate`
- `disputed`
- `rejected`
- `unresolved`

Use precise public wording: “worked at Tynesoft in Blaydon” is better than “North East developer” when the evidence only supports the former.

To approve a candidate, update `data/curated/north-east-connections.jsonl` with evidence IDs, a precise connection type, `public_visibility`, and `approved_by`/`approved_at` only when approval has actually happened. Do not invent Graham approval.

To reject a false match, keep the connection out of public exports by setting `status` to `rejected` and recording the reason in `explanatory_text` or the manual review queue.

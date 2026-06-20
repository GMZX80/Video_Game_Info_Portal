# North East post-ingest audit

Generated: 2026-06-20

## Summary

The post-ingest classification remains deliberately conservative.

| State | Count | Notes |
| --- | ---: | --- |
| Confirmed | 0 | No record has claim-specific evidence strong enough for confirmed public status. |
| Strongly supported | 0 | No current record was promoted to strongly supported. |
| Probable | 147 | Mostly publisher or label appearances requiring record-level inspection. |
| Candidate | 65 | Keyword or catalogue matches requiring source inspection. |
| Disputed | 0 | No disputed claim is currently modelled as a public North East connection. |
| Rejected | 0 | Rejections remain represented by omission or unresolved queues, not public claims. |

## Main correction

The detailed Sinclair User supplement found 3,845 unlinked software-section entries. A review of their structure showed that many were not safe to publish as complete game/source records: some are headings, descriptive prose, section labels, malformed title/company combinations, machine labels or unresolved contents text.

Post-processing moved 3,801 ambiguous `software index text` rows into:

```text
data/raw/sinclair-user/unresolved-software-lines.jsonl
```

This preserves the research lead while preventing those lines from creating public game records or North East claims.

## Promotions

No record was promoted to confirmed or strongly supported status.

Reason: the deeper ingest added more evidence but did not add claim-specific proof for development location, employment, legal succession or verified personal biography.

## Demotions and removals

- Probable public records fell from 191 to 147 after unresolved Sinclair prose was removed from canonical source items.
- Candidate records fell from 66 to 65.
- 44 generated claims/evidence rows tied to unresolved prose were removed from canonical output.
- Confirmed and strongly supported counts remained at zero.

## Claim-specific rules retained

The classifier continues to keep these claims separate:

- published by Tynesoft;
- programmed by a named individual;
- developed in Blaydon;
- worked at Tynesoft;
- freelance work for Tynesoft;
- North East office;
- later staff heritage;
- legal company successor.

A publisher or label field is not treated as developer evidence. A credit is not employment evidence. Staff heritage is not legal succession.

## Remaining backlog

- Review the 3,801 unresolved Sinclair software lines and classify them as probable game index entry, software title with printed publisher or label, article heading, listing heading, navigation, unresolved contents text or rejected parse.
- Inspect the 147 probable records source by source before any public promotion.
- Resolve the 65 candidates, especially keyword-only place/name collisions.
- Corroborate Tynesoft photograph-caption testimony before any person identification is public or verified.
- Resolve spelling and identity questions for Mike Landruff/Landreth, Julian/Julien Jameson/Jamieson, Bruce Nesbitt/Nesbit, Sparky, Baldrick and Dave Mann/Chris Robson.

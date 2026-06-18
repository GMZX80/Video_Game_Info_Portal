# Research Method

This project is an evidence catalogue, not a mirror of magazine archives. Store bibliographic metadata, source locators, short summaries, structured fields, and very short snippets only when essential.

Do not store complete article bodies, full review text, complete type-in listings, scans, screenshots, copied adverts, private contact details, Google Drive IDs, student/admin material, or unsupported allegations.

Every material public assertion should be represented as a claim linked to evidence. Evidence can be a contemporary magazine, original credit/manual/ad/news item, company record, first-person interview, retrospective recollection, archive index, secondary database, or inferred relationship. Inferred relationships are never displayed as confirmed facts.

When adding a manual source, add or update a row in `data/curated/source-items.jsonl`, record evidence in `data/curated/evidence.jsonl`, and run:

```bash
python -m scripts.validate_data
python -m scripts.export_public_json
```

# Story Fact-Checking

Generated: 2026-06-18

## Rule

A published narrative page must have enough evidence for every material claim. If the evidence is incomplete, the page must say so.

## Material Claims

A material claim includes:

- a person role;
- a company role;
- a game credit;
- a date;
- a place connection;
- a legal relationship;
- a staff relationship;
- a quotation;
- a photograph identification;
- a rights or permission statement;
- a claim that a record is confirmed.

## Validation Requirements

The static generator and tests must fail a published narrative page when:

- a referenced entity is missing;
- a referenced source is missing;
- a referenced claim is missing;
- a material claim has no evidence link;
- a quotation has no source and permission status;
- a photograph lacks acceptable permission status;
- private data is referenced;
- fact-check status is incomplete;
- editorial-review status is incomplete;
- disputed material is presented as certain.

## Accepted Public Statuses

For this first PR, public pages may use:

- `editorial_status: public-prototype`
- `fact_check_status: checked`
- `media_permission_status: no-restricted-media`
- `media_permission_status: approved-public`

Pages with `draft`, `unchecked`, `private`, `permission-needed` or `internal-review` must not be generated into public `dist/`.

## Source Notes

Source notes should be unobtrusive:

- short superscript-style links or compact buttons in the article surface;
- a source drawer near the end of the page;
- no raw database IDs in the main paragraph text;
- source IDs may appear in technical metadata and validation reports.

## Quotations

Direct quotations require:

- source ID;
- quotation permission status;
- quotation text length within copyright limits;
- redaction notes where needed;
- public status.

Private messages from Phil Scott or any other participant are research leads unless an explicit publication-permission record exists. Do not publish full private messages or private quotations without that record.

## Disputed And Unresolved Material

Use disputed or unresolved material only with clear labels:

- `The evidence does not yet establish...`
- `This remains a research lead.`
- `This is first-person recollection rather than contemporary documentation.`
- `This source supports publication, not employment.`

Never use unresolved material to fill a narrative gap.

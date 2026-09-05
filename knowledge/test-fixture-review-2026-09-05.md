---
title: Source Fixture Review
language: en
created: 2026-09-05
updated: 2026-09-05
related: [testing, project-review-2026-09-05, journal]
---


> Historical review snapshot. The implemented follow-up is recorded in [Technical remediation](technical-remediation-2026-09-05.md); [Status](status.md) owns the current findings and next steps. Original observations below retain their review date.
# Source Fixture Review — 2026-09-05

Twenty complete MediaWiki source texts now support one hundred explicit field expectations. All texts were checked against their raw BLOB records and normalized stage-02 rows. Positive expectations carry exact source-line selectors; notes explain nulls and the chosen citation scope. The earlier truncated `text`, parser-derived `existing` values and LLM `needed` hints were replaced.

The restored sample reveals twenty rule/expectation mismatches: eleven null outputs against non-null expectations and nine differing populated outputs. They include source-role and Unicode defects, but also field-selection and normalization questions. They are not twenty independently proven product data errors. The source expectations below use the documented fixture scope; the observed values describe unchanged production code at `1902abc`. `.github/extraction-baseline.json` records them as regression limits, not correct answers. All remain red in the semantic diagnostics.

Two subsequent blind source reviews and an independent test review qualify this inventory in [[independent-evaluation-2026-09-05]]. Five of the twenty rule mismatches already exactly match the expected values in the shipped frontend through frozen enrichment. Multiple-publication cases need scoped expectations; a first-citation scalar is not a ratified universal model contract.

| Page | Field | Current scoped fixture expectation | Existing extractor output |
|---|---|---|---|
| 4303 | publisher | Binoza | null |
| 4303 | translator | Iso Velikanović | Iso Velikanovi |
| 4303 | language | Serbo-Croatian | null |
| 1800 | publisher | Pechat Far | Translated by Dimitŭr Stoevski. 1st edition |
| 1800 | translator | Dimitŭr Stoevski | Dimit |
| 5746 | publisher | null | Juventud |
| 5746 | translator | the Editorial Juventud | Alfredo Cahn |
| 2866 | location | Chalfont St Giles | null |
| 5082 | publisher | Bibliothèque principale de la Ville de Namur | null |
| 1891 | publisher | Kavkazskiĭ Krai | null |
| 1891 | translator | null | R. Gal |
| 4445 | publisher | Hochschulverl. | null |
| 4445 | location | Freiburg im Breisgau | Freiburg |
| 4376 | publisher | Skoglunds Bokförlag | null |
| 533 | language | Estonian | null |
| 1999 | publisher | Österreichische Verlagsanstalt | Peter Lang Verlag |
| 1999 | page_count | null | 425 |
| 4209 | publisher | Nasionale Pers Beperk | null |
| 4209 | translator | Hymne Weiss | null |
| 4209 | language | Afrikaans | null |

## Scope and remaining work

These are source-text extraction checks, not a proof that flat page-level fields correctly model every edition. Bibliographic fields follow the first cited item, with explicit notes for ambiguous volume translators and multiple places. Language here tests category extraction; it does not read a film’s body-language label or bind a category language to an edition. The complete source and review notes are in `tests/test_sample_20.json`.

Prioritize confirmed source-role defects, Unicode translator names, page locators versus extent, and language coverage. Resolve selection-dependent expectations at publication/contribution scope before treating them as correction targets. Each fix needs a fresh comparison across the corpus, regenerated downstream artifacts, gate validation, and removal of its resolved baseline cases. A broader stratified sample and browser acceptance checks remain necessary.

## Verification

The strict default suite passed 521 tests without skips in 20.73 seconds. The semantic suite ran 170 assertions: 133 passed and 37 failed (twenty rule-extraction cases above plus seventeen existing frontend cases). JUnit reports are in the ignored `test-results/` directory. Python compilation and `git diff --check` passed. No live LLM call, production parser edit, source-data edit or product-artifact regeneration occurred. The pinned uv/Ruff checks remain unavailable locally; a further pinned Ruff download attempt timed out.

---
title: Independent Source and Test Evaluation
language: en
created: 2026-09-05
updated: 2026-09-05
related: [testing, test-fixture-review-2026-09-05, project-review-2026-09-05, journal]
---


> Historical review snapshot. The implemented follow-up is recorded in [Technical remediation](technical-remediation-2026-09-05.md); [Status](status.md) owns the current findings and next steps. Original observations below retain their review date.
# Independent Source and Test Evaluation — 2026-09-05

The project remains approximately **6/10 as a finished research product**. The independent reviews strengthen the diagnosis, but do not complete the model, correct production data or establish frontend acceptance. The observed **37 failing semantic assertions are not 37 demonstrated product data errors**: they mix two pipeline layers, factual defects and unresolved field-selection contracts.

## Review method and evidence

At the operator's request, three separate agents reviewed bounded tasks. Two received only the same twenty complete source texts and source identifiers, without current expected values, failure baselines, parser output or one another's findings. A third inspected the tests and compared rule results with the shipped frontend data. These are separate model reviews, not independent human expert adjudication or a statistical accuracy study. Source agreement supports a finding; it does not ratify an ambiguous interpretation.

Preserved evidence:

- [Source-only input](evaluations/2026-09-05/source-only.json)
- [Blind source review A](evaluations/2026-09-05/source-review-a.json)
- [Blind source review B](evaluations/2026-09-05/source-review-b.json)
- [Independent test review](evaluations/2026-09-05/test-review.md)
- [Rule/frontend comparison for all twenty observed mismatches](evaluations/2026-09-05/rule-vs-frontend.json)
- [Five owner acceptance cases](evaluations/2026-09-05/owner-evaluation.md)
- [Evidence hashes and verification manifest](evaluations/2026-09-05/manifest.json)

Both source reviews cover all twenty page IDs and five requested fields. Their evidence snippets were checked against the supplied full source texts. This verifies literal support, not the correctness of every assigned bibliographic role. No external authority lookup or live enrichment API call was performed.

## What the source reviews agree on

| Case | Shared source conclusion | Implication |
|---|---|---|
| 1800 | The 1947 and 1960 editions have different publishers and extents. | Preserve separately scoped edition fields; a page scalar cannot express both. |
| 5746 | Editorial Juventud and Alfredo Cahn translate different cited publications. Editorial Juventud is not explicitly credited as publisher here. | Distinguish a role error from selection of a valid value belonging to another publication. |
| 1891 | R. Gal’perina, V. Levik and P. S. Bernshteĭn have three scoped translation credits; N. Vysotskaia is editor. | Preserve contribution roles. A blank scalar does not establish absence of translators. |
| 4445 | The German book and Arabic article are different publications; both language contexts are explicit. | Do not combine one publication's imprint with the other publication's language. Their work relationship requires separate review. |
| 1999 | Both named publishers belong to real cited books; p. 425 is a reference locator. | The publisher discrepancy is scope dependent; treating 425 as book extent is a source-role error. |
| 4209 | Both Bloemfontein and Kaapstad occur in the imprint; Hymne Weiss is the translation credit. | Retain both places and preserve the differently scoped Hymme spelling in the evidence. |
| 4473 / 72 | The film explicitly says Chechen; German on page 72 is contextual inference. | Separate body evidence, category evidence and inference. Do not silently correct the source from prior knowledge. |

The reviewers use different representations for absence and pagination. Review A keeps contribution ranges outside a numbered-book-extent value; review B records typed ranges and derived inclusive spans alongside an unavailable scalar. Review B also explicitly distinguishes `pp. ??` on page 6005 from an unstated field. These are useful modeling distinctions, not evidence of contradictory source facts. Neither review approves flattening all these states into an unexplained null.

The existing ratified work/edition decision already requires decomposition of multi-edition pages. The remaining owner evaluation concerns concrete publication boundaries, contribution roles, provenance and usable presentation. A universal “first citation wins” rule is not ratified by these reviews.

## What the test review changes

**Five of the twenty rule mismatches already exactly match the fixture in the shipped frontend**, through frozen enrichment: publisher on pages 4303, 5082, 4376 and 4209, and translator on page 4209. Page 4445's publisher is populated with a punctuation difference; page 1891's publisher is populated but has an encoding defect. The other thirteen comparison cases still match the rule output, but several remain scope dependent. The full comparison is preserved above; these observations do not justify a corpus-wide error percentage.

The independent review found two concrete technical weaknesses:

1. `tests/test_semantic.py` does not enforce the frontend reference fixture's recorded hash or exact page inventory. Removing a currently passing page can silently reduce the seventy assertions to sixty-three. The extraction fixture's hash guard exists; the frontend fixture's guard needs equivalent protection.
2. Its title comparison accepts any suffix after the expected prefix. An invented title suffix passes both the default guard and semantic diagnosis. Legitimate title variants need explicit source-reviewed alternatives or narrowly specified normalization.

**Subsequent implementation:** both weaknesses are now closed. Collection validates the hash and exact page/field inventory, and titles use exact equality or an explicit source-backed variant. Six isolated fixture mutations and three invented-title mutations demonstrate rejection; both source-backed title forms for page 285 pass. The stale workflow comment about legacy skips was removed. The preserved reviewer report remains an unchanged snapshot of the pre-fix state. See [[testing]] for the current maintenance contract.

Resolved baseline cases currently emit warnings and require manual retirement. Until removed, the same previously wrong value could return without becoming a new failure. Exact source-line selectors prove occurrence but do not independently validate publication boundaries or contributor roles.

The test reviewer reproduced **157 focused passing tests without skips**, and **133 passing / 37 failing semantic assertions without skips**. Collection confirmed 521 default-selected tests. The earlier complete strict run remains **521 passed, zero skips**; it was not rerun for this documentation-only review. Pinned uv/Ruff checks and the full pinned reproduction run remain unverified locally.

## Owner evaluation and next implementation order

The [owner worksheet](evaluations/2026-09-05/owner-evaluation.md) proposes a 20–30 minute review: four concrete bibliographic cases and one real search-to-citation task, including a narrow screen or keyboard use. A useful response is `case number: accept / change / unclear`, with the first confusing result and the expected behavior. This evaluates domain usefulness; it is not approval of the whole release.

Next implementation order:

1. **Completed:** close the fixture hash/inventory and title-comparison gaps with mutation checks that demonstrate the old false passes now fail; remove the stale CI comment.
2. Express source expectations at publication/contribution scope. Preserve page categories separately from edition languages and distinguish missing, unknown, multiple and contested values. Use owner feedback to settle the concrete acceptance cases without reopening the ratified decomposition principle.
3. Correct confirmed source-role, Unicode and category-coverage defects. For each correction, inspect changes across the corpus, rebuild downstream artifacts, run affected tests and both gates, and retire resolved baseline cases after review. Do not change ambiguous expected values merely to make tests green.
4. Add a fresh, held-out stratified source sample and browser acceptance checks for search/filter routing, edition selection, source evidence, correction persistence, export, mobile navigation and keyboard access. Measure performance and accessibility against explicit acceptance targets before release.

No parser, test expectation, frozen decision or generated product artifact was changed in this independent-review round. Earlier descriptions of the twenty mismatch observations as twenty proven extraction defects are qualified by this review; historical journal entries remain preserved.

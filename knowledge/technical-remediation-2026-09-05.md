---
title: Technical Remediation — 5 September 2026
status: implementation-record
language: en
created: 2026-09-05
updated: 2026-09-05
---

# Technical remediation

This record follows the [completion review](project-review-2026-09-05.md) and [independent evaluation](independent-evaluation-2026-09-05.md). The operator authorized autonomous technical repairs, test refactoring, documentation consolidation and an interactive Explore dashboard. Raw inputs and released scholarly decisions were not changed. The verification below describes the local implementation before the subsequently authorized [controlled closeout](journal.md#2026-09-05--session-34-controlled-closeout). [Current status](status.md) owns the present handoff and remaining acceptance work.

## Source-reviewed parser changes

Two parser versions were evaluated directly on every unchanged stage-02 source row. The [summary](evaluations/2026-09-05/parser-summary.json) records input/code hashes and the [compact change inventory](evaluations/2026-09-05/parser-changes.json) preserves IDs, source hashes, before/after values and exact evidence. Source text is reconstructible from the unchanged stage-02 input rather than repeated for every field.

| Field | Rule-level changes | Published value changes | Interpretation |
|---|---:|---:|---|
| Translator | 536 | 343 | 202 Unicode completions, 330 removed trailing prose, four preserved final initials at the same selected credit |
| Numbered extent | 95 | 95 | remove explicit reference/annotation or discontinuous locators |
| Language label | 57 | 57 | 27 Estonian, 22 Serbo-Croatian, eight Afrikaans source-category gaps |

Rule changes affect 677 pages. Existing normalization had already corrected some translator strings, so rule counts are not published-change counts. No translator occurrence was switched, no missing translator scalar was newly filled, and no existing published language was overwritten. The language additions include 55 bibliography pages and two category pages. Registered codes were added for Afrikaans and historical Serbo-Croatian; the latter retains the broad source designation rather than guessing a modern constituent language. [IANA's BCP-47 registry](https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry) records `sh` as the macrolanguage subtag.

Independent review caught an unsafe prototype truncation of the irregular source credit “Anna. S. Kulisher”. A generic period-followed-by-initial guard now retains the legacy value for that uncertain boundary. The remaining malformed credit is documented, not ratified as correct. [Parser review](evaluations/2026-09-05/parser-review.json) records this and other scope limits.

Six rule assertions now meet their unchanged source expectation: translator/language on page 4303, translator on 1800, language on 533 and 4209, and extent on 1999. They were removed from the allowed-failure inventory. Page 1891 now retains “R. Gal’perina”, but that credit belongs to a contribution and does not certify the whole volume. Page 285 now cleanly retains “Alzir Hella and Olivier Bournac”, but it remains a French credit against a German-publication fixture scope. Both semantic expectations stay red; reviewed partial improvements are explicit baseline history entries.

## References and RDF

Stage 04 no longer appends display decoration to redirect data. Stage 05 resolves literal page-title aliases and chains with cycle/missing-target protection. The final map contains 3,549 aliases. Across 1,213 See-reference occurrences, technical unresolved counts fell from 120 to 12, with no newly unresolved occurrence. The error ratchet is lowered accordingly.

The [independent published-change review](evaluations/2026-09-05/published-change-review.json) validates the added aliases against source chains and distinguishes mechanical resolution from meaning. The original “Maria Stuart” redirect points to an apparently unrelated review; 26 references now follow that source link. This is a documented upstream anomaly for adjudication, not proof that every newly resolved link is correct.

Edition page-summary fields and contested source-text/match-mode fields now have JSON-LD context mappings. Ten previously missing vocabulary terms are registered. Fifteen RDF tests check exact expanded literals, child links, zero/null behaviour and registration; JSON presence alone cannot detect silently dropped RDF fields. Both gate graphs and vocabulary pages were regenerated through the responsible pipeline stages.

## Test and curation contracts

The frontend semantic fixture's byte hash, exact page IDs and field inventory are checked before collection. Explicit source-title variants replace the old generic prefix comparison. Isolated mutation cases exercise edited expectations, removed/replaced/duplicate pages and missing fields, including cases with a recomputed hash.

The complete twenty-page extraction sample keeps one hundred explicit expectations and source selectors. Shared source/export fixtures, indexed lookup, one integration build per corpus and deep-copy isolation reduce redundant work. Every Node behaviour file and shipped JS module is discovered automatically. Required inputs cannot silently disappear from strict runs.

Field corrections require a versioned object and a patch array, positive integer page IDs and timezone-aware timestamps. Replay orders actual instants. Malformed records or unknown targets produce failure before frontend persistence; malformed envelopes and empty/missing frontend collections also fail. Reconciliation-only documents remain valid inputs to their separate layer. `oldValue` drift remains a reported warning under authoritative replay. This does not close canonical provenance/correction propagation.

No mismatch tolerance was widened. Coverage was rebaselined only for source-reviewed extent removal and language/reference improvements. Thirty-one remaining semantic failures span different layers and unresolved scalar contracts; they are not thirty-one proven product errors.

## Interface and knowledge refactoring

The first frontend repair restored complete multiple-value and missing-language handover, URL reload/back state, mobile header navigation, one visible Results h1 and readable badges. Queue key handlers now belong to the replaced list, so repeated render cycles do not multiply actions. [Browser evidence before the dashboard](evaluations/2026-09-05/browser-before-dashboard.json) verifies 320/390/1280-pixel layouts and exact matching IDs.

The requested dashboard now replaces the dense multicolour default timeline with linked selection/coverage cards, a neutral decade histogram, language/type rankings, validated year controls and an entry preview. Map and Connections retain the shared selection. Every count describes source-page entries, not a complete publication census. The old timeline's chart modes and milestone overlay were removed from the overview, with obsolete CSS/comments cleaned up.

Independent review found conflicting/malformed restored date filters and focus loss on reset. Both are corrected and independently rechecked. Date selection rejects undated entries when bounds are active; normalized saved URLs and Results produce identical IDs. Chart buttons and range submission preserve keyboard focus. Neutral marks meet 3.28:1 contrast against the ranking track; selected burgundy exceeds 10:1. [Final browser QA](evaluations/2026-09-05/dashboard-browser-qa.json) and [desktop](evaluations/2026-09-05/dashboard-1440.png)/[mobile](evaluations/2026-09-05/dashboard-320.png) views preserve the result.

Maintained guides now have distinct responsibilities, with [Status](status.md) as the single current evidence/work list. Historical reviews and journal entries retain their dates, and issue templates are labelled proposals. Two directory READMEs are English and aligned with actual runner and patch behaviour. [Documentation ownership](documentation.md) lists the complete Markdown treatment and update rules.

## Verification record

The complete frozen production run passed, followed by a dependent rebuild after adding missing language-code mappings. Gate 1 and Gate 2 passed SHACL, exact evidence/ID contracts and same-run deterministic rebuild. The source corpus hash remains unchanged. The final no-op patch replay also passed.

The final locked environment was installed successfully with uv 0.12.5. Final strict default result: **615 passed, zero skips, 174 deselected**. Semantic result: **139 passed / 31 retained failing assertions**. All **53 Node tests** and **15 module syntax checks** pass. Ruff 0.16.4 check/format, the full pre-commit hook set, Python compilation and whitespace checks pass. Six RDFLib deprecation warnings remain in the Python suite.

The full frozen production run under locked uv passed in 176.4 seconds and reproduced all 117 compared deterministic data/vocabulary files byte-identically against the reviewed system-runtime build. No model call occurred. Both gate validators passed. [Validation](evaluations/2026-09-05/validation.json), [reproduction result](evaluations/2026-09-05/pinned-reproduction.json) and [artifact hashes](evaluations/2026-09-05/reproduction-hashes.json) preserve the exact scope. This local evidence does not claim that remote CI has run.

The final CI follow-up closes the earlier committed-evidence gap. `verify_committed_evidence.py` compares stable gate manifests with HEAD and validates every referenced file, including ignored candidates/queues. Twenty-two mutation tests cover changed/missing evidence and the narrow timestamp allowance. The real reviewed local snapshot passes. Both reviewed manifests belong in the same commit as the corresponding code, inputs and artifacts. The historical evaluation files retain their pre-closeout Git state; remote execution is recorded separately by GitHub Actions.

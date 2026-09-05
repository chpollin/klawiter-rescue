> Historical independent test review. Machine-local file links and line numbers below refer to the reviewed workspace snapshot. Use the portable [consolidated evaluation](../../independent-evaluation-2026-09-05.md) and [current test guide](../../testing.md) for navigation and follow-up status.

# Independent review of the test refactoring

Reviewed on 2026-09-05 against working-tree changes over commit `1902abc`. This review preserved all source, test, fixture and product files. It did not read the source-review-a/b reports, run the production pipeline, install dependencies, or make network/model calls.

The refactor materially strengthens regression detection: known failures are matched by page, field and observed value rather than by an interchangeable failure count; missing committed inputs fail; all 100 extraction fields, including 42 null expectations, receive assertions; fixture texts are compared with complete stage-02 rows. The result is a better regression gate, not proof of product accuracy. Two executable guard gaps remain, and the error inventory needs clearer separation between source facts, scalar selection policies and gaps already filled downstream.

## Prioritized findings

### P2 — The semantic oracle hash is recorded but never enforced

Location: [tests/test_semantic.py:44](C:/Users/chris/Documents/GitHub/klawiter-rescue/tests/test_semantic.py:44), [tests/conftest.py:181](C:/Users/chris/Documents/GitHub/klawiter-rescue/tests/conftest.py:181), [.github/semantic-baseline.json:5](C:/Users/chris/Documents/GitHub/klawiter-rescue/.github/semantic-baseline.json:5).

The guard validates known-case count, uniqueness, and membership, but never checks `groundTruthSha256`, the oracle's page count, or unique page IDs. In contrast, extraction fixtures have a hash and 20-page check at [tests/test_real_entries.py:53](C:/Users/chris/Documents/GitHub/klawiter-rescue/tests/test_real_entries.py:53).

Two read-only, in-memory probes reproduced the consequence:

- Replacing `semantic_baseline['groundTruthSha256']` with `incorrect hash` still passes the real guard with current data.
- Removing page 33, which has no baseline mismatches, still passes. This silently reduces semantic coverage from 70 to 63 assertions without changing the baseline or producing a warning.

A changed oracle can therefore weaken or delete passing checks without triggering the promised reviewed-baseline boundary. Verify the committed oracle's byte hash in a blocking default test; validate its expected page/field inventory and unique IDs. Add focused tests for a changed hash and removal of a previously passing page. The hash does not establish review quality, but it prevents accidental drift without an explicit paired change.

### P2 — The frontend guard accepts arbitrary title suffixes

Location: [tests/test_semantic.py:23](C:/Users/chris/Documents/GitHub/klawiter-rescue/tests/test_semantic.py:23).

`_field_ok` treats every title beginning with the expected string as correct. A read-only mutation changing page 33 from `Legenden` to `Legenden completely invented trailing text` passes the default guard; it also satisfies the exact same comparator used by semantic diagnosis. The guard only freezes values after this comparator has decided they are wrong, so page/field/value matching cannot protect this case.

This is a retained limitation from the pre-refactor code, not a regression introduced by this refactor. It nevertheless limits the current claim that new or changed wrong values fail. Use exact source-reviewed title expectations, or an explicit per-fixture list of justified accepted variants. Keep prefix-only checks separately named if they serve a deliberate title-stem contract. Add a negative suffix case to the guard tests.

### P2 — Do not promote scalar selection choices into factual error counts or the correction contract

Location: [knowledge/testing.md:61](C:/Users/chris/Documents/GitHub/klawiter-rescue/knowledge/testing.md:61), [knowledge/testing.md:63](C:/Users/chris/Documents/GitHub/klawiter-rescue/knowledge/testing.md:63), [knowledge/test-fixture-review-2026-09-05.md:11](C:/Users/chris/Documents/GitHub/klawiter-rescue/knowledge/test-fixture-review-2026-09-05.md:11).

The notes disclose the chosen scope, which is good. However, calling all twenty cases existing rule defects and directing correction of the whole inventory is stronger than the evidence supports. A source selector proves that a value occurs in a cited role; it does not establish which of several valid records must become the page's scalar value.

Concrete examples:

- [tests/test_sample_20.json:180](C:/Users/chris/Documents/GitHub/klawiter-rescue/tests/test_sample_20.json:180): page 5746 names both the Editorial Juventud and Alfredo Cahn as translators of different references. Choosing the first is a selection policy; `Alfredo Cahn` is not an invented or incorrectly transcribed translator. Treating Juventud as a publisher is a different, source-role problem.
- [tests/test_sample_20.json:689](C:/Users/chris/Documents/GitHub/klawiter-rescue/tests/test_sample_20.json:689): page 1999 genuinely names both Österreichische Verlagsanstalt and Peter Lang Verlag for distinct books. Selecting the first is not equivalent to proving Peter Lang is factually false. The `425` page count is independently a locator-versus-extent problem.
- [tests/test_sample_20.json:451](C:/Users/chris/Documents/GitHub/klawiter-rescue/tests/test_sample_20.json:451): page 4445 combines the first German item's imprint and extent with the first category's Arabic language. This is honestly documented as a function test, but it is not a coherent bibliographic record.
- [tests/test_sample_20.json:738](C:/Users/chris/Documents/GitHub/klawiter-rescue/tests/test_sample_20.json:738): page 4209 names Bloemfontein and Kaapstad. The expected final comma-separated place is explicitly justified by current extractor behavior. It is a compatibility choice, not evidence that the other place should be discarded.

The ratified direction is work/edition decomposition, not a newly ratified universal first-citation scalar rule: see [knowledge/production-readiness.md:45](C:/Users/chris/Documents/GitHub/klawiter-rescue/knowledge/production-readiness.md:45) and [knowledge/data.md:50](C:/Users/chris/Documents/GitHub/klawiter-rescue/knowledge/data.md:50). Keep these compatibility-function assertions if useful, but label source-role/transcription/absence facts separately from ordering and scalar-selection expectations. Give multi-record cases explicit record/edition or citation scope before using their failures as production correction requirements. This is a scope/interpretation defect in the inventory, not a reason to discard the restored source texts or relax genuine source-fact assertions.

## Rule-stage mismatches versus published results

The production contract deliberately allows frozen LLM gap filling. A regex miss is not automatically a published defect. Reading the current [docs/data/klawiter.json](C:/Users/chris/Documents/GitHub/klawiter-rescue/docs/data/klawiter.json) shows five of the twenty cases already equal the fixture downstream, all with `llm` field provenance. Two more have populated publisher values that differ from the exact source spelling. The other thirteen retain the rule output; some remain subject to the scope distinction above.

| Page | Field | Rule output | Current frontend output | Assessment against this fixture |
|---|---|---|---|---|
| 4303 | publisher | null | Binoza | Already filled correctly by LLM |
| 4303 | translator | Iso Velikanovi | Iso Velikanovi | Truncated name persists |
| 4303 | language | null | null | Category language still missing |
| 1800 | publisher | Translated by Dimitŭr Stoevski. 1st edition | Same | Prose misclassified as publisher |
| 1800 | translator | Dimit | Dimit | Truncated name persists |
| 5746 | publisher | Juventud | Juventud | Translator/publisher role issue |
| 5746 | translator | Alfredo Cahn | Alfredo Cahn | Valid second-reference translator; scalar-scope issue |
| 2866 | location | null | null | Fixture's journal-address location remains absent; validate its intended bibliographic role |
| 5082 | publisher | null | Bibliothèque principale de la Ville de Namur | Already filled correctly by LLM |
| 1891 | publisher | null | KavkazskiÄ­ Krai | Filled by LLM with corrupted spelling; fixture says Kavkazskiĭ Krai |
| 1891 | translator | R. Gal | R. Gal | Truncation persists; null expectation additionally selects volume-wide scope |
| 4445 | publisher | null | Hochschulverl | Filled by LLM; differs from Hochschulverl. only in final punctuation |
| 4445 | location | Freiburg | Freiburg | Source says Freiburg im Breisgau; truncation/normalization distinction needs explicit contract |
| 4376 | publisher | null | Skoglunds Bokförlag | Already filled correctly by LLM |
| 533 | language | null | null | Category language still missing |
| 1999 | publisher | Peter Lang Verlag | Peter Lang Verlag | Valid second-book publisher; scalar-scope issue |
| 1999 | page count | 425 | 425 | Citation locator incorrectly published as extent |
| 4209 | publisher | null | Nasionale Pers Beperk | Already filled correctly by LLM |
| 4209 | translator | null | Hymne Weiss | Already filled correctly by LLM |
| 4209 | language | null | null | Category language still missing |

Do not report the twenty rule mismatches as twenty new product errors, or assume all fifteen exact frontend disagreements are factual errors. Prioritize surviving role errors, Unicode truncation/corruption, locator-as-extent, and documented missing category languages. Parser completeness improvements for the five already-filled fields can still be useful, but are a different priority. No conclusion here authorizes replacing a valid multi-record source with a first-reference scalar.

## Reasonable design choices and remaining limits

- Exact known-case allowances are a defensible initial inventory against unchanged production code. The two replacement-failure probes in each guard cover both movement to another page and a changed wrong value. A known missing value cannot become a new fabricated value silently.
- Improvements produce warnings, not a mandatory baseline update ([tests/test_semantic.py:60](C:/Users/chris/Documents/GitHub/klawiter-rescue/tests/test_semantic.py:60), [tests/test_real_entries.py:100](C:/Users/chris/Documents/GitHub/klawiter-rescue/tests/test_real_entries.py:100)). Until a resolved case is manually removed, its old wrong value can recur and pass. This is documented policy, not an automatic ratchet; enforce baseline retirement in the correction package if lasting protection is required.
- Positive selector checks verify exact text spans and substring inclusion, not the bibliographic role or uniqueness of the expected value. Null selectors are supported by prose notes rather than machine-verifiable absence proofs. That is acceptable for a reviewed fixture but does not replace independent domain review.
- [tests/test_source_tables.py:22](C:/Users/chris/Documents/GitHub/klawiter-rescue/tests/test_source_tables.py:22) proves equality with stage-02 rows and source IDs. It does not independently reopen the raw BLOB or recompute `rawTextSha256` on every test run. Documentation currently describes the direct BLOB check as a restoration-time action; keep that distinction.
- Shared edition builds use deep copies before overlays. The reconciliation refactor retains the full corpus build and expands occurrence completeness from five subjects to every subject; the reduced unresolved-decision inputs preserve all occurrences for a real person and publisher. These are reasonable performance changes, not evidence of removed corpus coverage.
- The Node bridge discovers the stated seven behavior files and fifteen shipped modules. Syntax and isolated JavaScript logic tests do not establish browser/DOM acceptance; the current documentation states this limit accurately.
- `--require-test-inputs` fails for missing Node and stage CSVs; the isolated tests verify missing/malformed committed JSON and the local/strict/CI runtime paths. It is not a universal no-skips option: optional LLM imports can still skip collection if unavailable, and local non-strict mode intentionally skips missing runtime inputs. These do not falsify the reported observed zero-skips run.
- The semantic CI step's `continue-on-error` is defensible because the same comparison is protected by the blocking default guard. It remains diagnostic evidence, not a green semantic acceptance gate. The workflow's line 10 comment about remaining legacy sample skips is stale and should be removed.

## Verification performed

All commands used the existing system Python 3.11.9 environment, not the unavailable pinned uv environment.

- `python -m pytest -q tests/test_real_entries.py tests/test_semantic.py tests/test_source_tables.py tests/test_test_inputs.py --require-test-inputs`: **157 passed, 170 deselected, no skips**, 10.12 seconds.
- `python -X utf8 -m pytest -q -m semantic --require-test-inputs --tb=no`: **133 passed, 37 failed, 525 deselected, no skips**, 3.27 seconds. The failures match the twenty extraction and seventeen frontend baseline cases.
- `python -X utf8 -m pytest --collect-only -q --require-test-inputs`: **521 selected of 695 collected, 174 deselected**. This independently confirms the reported inventory, not execution of all 521 tests in this review.
- Read-only in-memory guard probes confirmed acceptance of a bogus semantic hash, removal of passing page 33, and an invented suffix on page 33's title.

The reported previous full run of 521 passes is consistent with current collection and the focused execution, but was not repeated here. The 170 semantic assertions, 37 failures, restored ten legacy checks, explicit null coverage, and this environment's zero-skips behavior are substantiated. Pinned lint/format checks, the full pipeline, gate validators and CI execution remain outside this review's verification scope.

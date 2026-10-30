---
title: Test State after the October Fixes
project:
  name: Klawiter Bibliography
  repository: https://github.com/chpollin/klawiter-rescue
method:
  name: Promptotyping
  url: https://lisa.gerda-henkel-stiftung.de/digitale_geschichte_pollin
status: complete
language: en
created: 2026-10-30
updated: 2026-10-30
related: [testing, independent-evaluation-2026-09-05, technical-remediation-2026-09-05]
---

> Dated test snapshot. [Testing](../knowledge/testing.md) owns the commands and the baseline contract; [Status](../knowledge/status.md) owns the current findings. The figures below hold for the run date only.

# Test State — 2026-10-30

The semantic suite now has **152 passing and 18 failing assertions** out of the same 170, against **133 passing and 37 failing** in the [independent evaluation of 2026-09-05](independent-evaluation-2026-09-05.md). Both oracles are byte-identical to that date: `tests/wiki_ground_truth.json` and `tests/test_sample_20.json` are unchanged since `d345ee6`, and the recorded hashes in both baselines are the same. The delta therefore reflects pipeline and frontend changes, not edited expectations. As on 2026-09-05, the failing assertions are not a count of demonstrated data errors; several are unresolved field-selection contracts at publication scope.

## Run conditions

- Commit `9d7d11a`, run on 2026-10-30, Windows, Node v24.20.0, uv-managed Python environment of the repository.
- A parallel session had uncommitted work in `pipeline/export_tei.py`, `data/output/tei/`, `docs/acceptance/`, `pipeline/acceptance.py`, `tests/acceptance_view.test.js` and `tests/fixtures/acceptance-report.json` at run time. The runs read this working tree.
- The production run (`pipeline/run_pipeline.py`) was not executed first, so the suites checked the generated outputs as present in the working tree. No live LLM call was made.

## Results

| Suite | Command | Result |
|---|---|---|
| Semantic | `python -m uv run pytest -q -m semantic --require-test-inputs` | 152 passed, 18 failed, 0 skipped, 1047 deselected |
| Default | `python -m uv run pytest -q --require-test-inputs` | 1042 passed, 5 errors, 0 failed, 0 skipped, 170 deselected, 10 warnings |
| Node | `node --test tests/*.test.js` | 187 passed, 0 failed, 0 skipped |

The default suite now collects 1047 tests, against 521 on 2026-09-05 and 615 after the remediation of the same day. Its exact semantic regression guard passes, so every remaining semantic failure carries exactly the page, field and value recorded in `.github/semantic-baseline.json` or `.github/extraction-baseline.json`.

### In progress at run time

- **Default suite, 5 errors**, all at fixture setup in `tests/test_tei_export.py`: `export_tei.build(...)` now returns an `Element` without `.write()` (`AttributeError`). This module was being edited by the parallel session; the errors are not counted as regressions.
- **Node, 17 of the 187 tests** come from the untracked `tests/acceptance_view.test.js` of the same work; all pass.

## Semantic delta against 2026-09-05

The 37 failures of 2026-09-05 were twenty rule-extraction cases ([rule/frontend comparison](evaluations/2026-09-05/rule-vs-frontend.json)) and seventeen frontend cases (`.github/semantic-baseline.json` at `d345ee6`).

**Rule extraction, now passing (13):** 4303 publisher, translator and language; 1800 publisher and translator; 5082 publisher; 1891 publisher; 4445 publisher; 4376 publisher; 533 language; 1999 extent; 4209 publisher and language.

**Rule extraction, still failing (7):**

- 5746 publisher: `Juventud`, expected none; Editorial Juventud is credited as translator, not imprint.
- 5746 translator: `Alfredo Cahn`, expected `the Editorial Juventud`; Cahn belongs to the second reference.
- 2866 location: none, expected `Chalfont St Giles` from the journal address.
- 1891 translator: `R. Gal’perina`, expected none; translators are scoped to contributions, not the volume.
- 4445 location: `Freiburg`, expected `Freiburg im Breisgau`.
- 1999 publisher: `Peter Lang Verlag`, expected `Österreichische Verlagsanstalt` of the first listed book.
- 4209 translator: none, expected `Hymne Weiss`.

**Frontend, now passing (7):** 285 translator; 409 publisher; 1166 title and year; 1308 title; 1667 publisher; 6342 location.

**Frontend, still failing (10), with current value against expectation:**

- 285 location: none against `Leipzig` (was `Stockholm` on 2026-09-05).
- 285 pageCount: 100 against none.
- 1308 pageCount: 23 against none.
- 1667 year, location, pageCount: 1919, `Wien`, 54 against none for each.
- 4133 title: `Ghanim, Emad M. / Ġānim, ʿImād M.`, the page title instead of the thesis title.
- 4535 language: none against `German`.
- 5487 title: `Leporella / Catalan` against `Leporella` (was a full citation string on 2026-09-05).
- 6342 publisher: `Bloch Erden Veralg` against `Bloch Erden Verlag`, a transposed letter (was `Insel Verlag`).

**Frontend, newly failing (1):** 4133 location, none against `Marburg`. It entered the baseline with `71a0fe0` (2026-10-24), which leaves flat fields that no rule binds as gaps.

Net change: extraction 20 → 7, frontend 17 → 11, total 37 → 18.

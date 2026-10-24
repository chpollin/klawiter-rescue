// The review rules of the card workbench on invented values, no print text:
// on which card a key may act, which values "all right" may confirm, the typed
// value a correction carries, and that a candidate is never called a match.
// The server side of the same rules is _review.check (test_print_objects.py).
// Usage: node pipeline/print_volumes/viewer/check_review.mjs; exits 1 on a failure.

import assert from "node:assert/strict";
import { WIKI_STATUS, acceptsKeys, candidates, cardLines, confirmable, correctionValue, findPassage, isInherited, shownIndices, valueName, wikiState } from "./render.js";

const checks = [];
const check = (name, fn) => checks.push([name, fn]);

check("keys act only on the focused, visible, settled card", () => {
  const ready = { loading: false, busy: false, connected: true, focusWithin: true, inView: true };
  assert.equal(acceptsKeys(ready), true);
  for (const key of Object.keys(ready)) {
    const broken = { ...ready, [key]: !ready[key] };
    assert.equal(acceptsKeys(broken), false, `a key acts with ${key} ${broken[key]}`);
  }
});

const row = (index, field, value, source = "I/F/12") => ({ index, field, value, source, start: index, end: index + 1, node: {} });
const all = [
  row(0, "title", "Der Weg"),
  row(1, "extent.raw", "120/(3)p."),
  row(2, "extent.parts[0].text", "120"),
  row(3, "extent.parts[1].text", "(3)"),
  row(4, "references[0].address", "F 61"),
  row(5, "references[0].kind", "see"),
  row(6, "types[0]", "book_edition"),
  row(7, "imprints[0].year_bracketed", true),
].map((r) => ({ ...r, label: valueName(r.field) }));

check("a card shows every value once, sub-values included", () => {
  const shown = shownIndices(cardLines(all)).sort((a, b) => a - b);
  assert.deepEqual(shown, all.map((r) => r.index));
});

check("all right confirms only undecided values the card displays", () => {
  const decided = new Map([[0, {}]]);
  const displayed = new Set([0, 1, 4, 6, 7]);
  assert.deepEqual(confirmable(all, decided, displayed).map((r) => r.index), [1, 4, 6, 7]);
});

check("a correction carries the type _review.check requires", () => {
  assert.equal(correctionValue("imprints[0].year_bracketed", "[1950]"), true);
  assert.equal(correctionValue("imprints[0].circa", "ca."), true);
  assert.equal(correctionValue("imprints[0].year", "(1950)"), 1950);
  assert.equal(correctionValue("imprints[0].year", "o. J."), null);
  assert.equal(correctionValue("persons[0].roles[0]", "Tr.", "translator"), "translator");
  assert.equal(correctionValue("persons[0].roles[0]", "Tr.", ""), null);
  assert.equal(correctionValue("title", "Der Weg"), "Der Weg");
});

check("an inherited value is the one whose passage lies in another record", () => {
  assert.equal(isInherited(row(0, "inherited.imprints[0].place", "Wien", "I/F/1"), { entry: "I/F/12" }), true);
  assert.equal(isInherited(row(0, "title", "Der Weg"), { entry: "I/F/12" }), false);
});

check("a typed passage is found inside the object nearest the value", () => {
  const text = "Wien 1950. 12 Der Weg. Wien: Verlag, 1950.";
  assert.deepEqual(findPassage(text, "Wien", 30, [11, text.length]), [23, 27]);
  assert.deepEqual(findPassage(text, " 1950 ", 0, [11, text.length]), [37, 41]);
  assert.equal(findPassage(text, "Graz", 0, [0, text.length]), null);
});

check("the wiki projection names candidates, never matches", () => {
  const concordance = {
    links: {
      "I/F/12#1": { same: [{ claim: "claim:a", state: "proposed", route: "field-match", page: 5, target: "klawiter:publication/5-1984-a" }, { claim: "claim:b", state: "proposed", route: "field-match", page: 5, target: "klawiter:publication/5-1984-a" }] },
      "I/F/13": { cand: [{ claim: "claim:c", state: "proposed", route: "title-year", page: 7, target: "klawiter:entry/7" }] },
    },
  };
  const own = wikiState(concordance, "I/F/12#1", "I/F/12");
  assert.equal(own.status, "fields");
  assert.deepEqual(candidates(own).map((c) => [c.page, c.claims.length, c.state]), [[5, 2, "proposed"]]);
  assert.equal(wikiState(concordance, "I/F/13#1", "I/F/13").status, "title-year");
  assert.equal(wikiState(concordance, "I/F/14#1", "I/F/14").status, "none");
  for (const [, short, long] of Object.values(WIKI_STATUS)) assert.doesNotMatch(`${short} ${long}`, /match(?!es)|linked|in wiki/i);
});

let failed = 0;
for (const [name, fn] of checks) {
  try {
    fn();
    console.log(`OK ${name}`);
  } catch (e) {
    failed += 1;
    console.error(`FEHLER ${name}: ${e.message}`);
  }
}
process.exit(failed ? 1 : 0);

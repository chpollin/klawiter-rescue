// The review rules of the card workbench on invented values, no print text:
// on which card a key may act, which values "all right" may confirm and when
// a value counts as displayed, the typed value a correction carries, that a
// reviewer sees only their own decisions, that a message names its object,
// and that a candidate is never called a match.
// The server side of the same rules is _review.check (test_print_objects.py).
// Usage: node pipeline/print_volumes/viewer/check_review.mjs; exits 1 on a failure.

import assert from "node:assert/strict";
import {
  METHOD_LABEL,
  ROUTE_LABEL,
  WIKI_STATUS,
  about,
  acceptsKeys,
  candidateRoute,
  candidates,
  cardLines,
  claimsShown,
  confirmable,
  correctionValue,
  effective,
  findPassage,
  inSight,
  isInherited,
  objectName,
  objectReview,
  ownDecisions,
  shownIndices,
  valueName,
  wikiState,
} from "./render.js";

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
  // Route and method names, and every line the drawer builds from them.
  for (const label of [...Object.values(ROUTE_LABEL), ...Object.values(METHOD_LABEL)]) assert.doesNotMatch(label, /match/i);
  for (const c of candidates(own)) assert.doesNotMatch(candidateRoute(c), /match|claim:/i);
  assert.equal(candidateRoute({ route: "alignment", score: 0.5 }), "text alignment, score 0.50");
  assert.equal(candidateRoute({ route: "title-year", method: "title-year" }), "title and year", "a route is said once");
  assert.doesNotMatch(candidateRoute({ route: "unknown-route", method: "unknown-method" }), /unknown/);
  for (const key of ["align", "same", "cand"]) assert.doesNotMatch(claimsShown(key, 5, 12), /match|-/i);
});

check("a value counts as displayed only inside every clip around it", () => {
  const viewport = { top: 0, left: 0, bottom: 500, right: 1440 };
  const column = { top: 100, left: 900, bottom: 450, right: 1440 };
  const box = (top, height = 20) => ({ top, bottom: top + height, left: 950, right: 1000, width: 50, height });
  assert.equal(inSight(box(200), [viewport, column]), true);
  assert.equal(inSight(box(460), [viewport, column]), false, "scrolled below its column");
  assert.equal(inSight(box(90), [viewport, column]), false, "cut by the column top");
  assert.equal(inSight(box(520), [viewport]), false, "below the viewport");
  assert.equal(inSight(box(200, 0), [viewport]), false, "no box");
});

check("a reviewer sees only their own decisions", () => {
  const log = [
    { id: "d1", reviewer: "first", object: "I/F/12#1" },
    { id: "d2", reviewer: "second", object: "I/F/12#1" },
    { id: "d3", reviewer: "first second", object: "I/F/12#1" },
  ];
  assert.deepEqual(ownDecisions(log, "second").map((d) => d.id), ["d2"]);
  assert.deepEqual(ownDecisions(log, ""), [], "no name, no decisions");
});

check("an adjudication never stands in for a reviewer's value decision", () => {
  const target = { path: "title", value: "Der Weg", span: [0, 7], source: "I/F/12" };
  const sha = "0".repeat(64);
  const log = [
    { id: "d1", reviewer: "third", object: "I/F/12#1", decision: "confirm", target, entry_sha256: sha },
    { id: "d2", reviewer: "third", object: "I/F/12#1", decision: "adjudicate", target, settles: ["x1", "x2"], adopts: "x1", entry_sha256: sha },
  ];
  const active = effective(log);
  assert.equal(active.size, 2, "both stay in force under their own keys");
  const rowsShown = [{ index: 0, field: "title", value: "Der Weg", start: 0, end: 7, source: "I/F/12" }];
  const state = objectReview({ id: "I/F/12#1" }, rowsShown, active, sha);
  assert.equal(state.byIndex.get(0)?.id, "d1");
  assert.equal(state.own.length + state.stale.length, 0);
});

check("a message names the object it concerns", () => {
  assert.equal(objectName({ address: "F 61", id: "I/F/61#1" }, { kind: "entry" }), "F 61");
  assert.equal(objectName({ address: "", id: "I/F/61#2", part: "F" }, { kind: "entry" }), "unnumbered object I/F/61#2");
  assert.equal(objectName({ address: "", id: "I/F/h1#1", part: "F" }, { kind: "header" }), "Header F");
  assert.equal(about("F 61", "Saved", "title right"), "Saved on F 61, title right.");
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

// Coverage check of the card workbench over all JSON-LD chunks: every value of
// every object gets a row, a complete provenance chain, a readable name, a
// PDF page, and exactly one token on its card, so that no value can be decided
// or confirmed unseen; and the wiki projection never names a candidate a match.
// The same objects also go through the record desk's print adapter
// (records-print.js) and the shared card (docs/js/record-card.js, run in a vm
// context as the browser runs it): every value of the card has one visible
// chain button under the row that names its key, its panel id resolves, its
// chain shows the six steps with the exact passage, and no hidden element or
// bare data-provenance-for stands for a value (tests/lib/visible.cjs).
// Usage: node pipeline/print_volumes/viewer/check_render.mjs [data/print/derived/viewer]
// Exits 1 if any object fails.

import { existsSync, readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";
import { cardModel, chainRows } from "./records-print.js";
import { WIKI_STATUS, candidateRoute, candidates as candidatesOf, cardLines, chain, chainComplete, fieldLabel, indexGraph, pdfHref, rows, shownIndices, valueName, valueText, wikiState } from "./render.js";

const CODE = /[[\]._]/;

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "../../..");
const { chainButtons, ids, markersWithoutButton, visibleText } = createRequire(import.meta.url)(join(root, "tests/lib/visible.cjs"));
const context = vm.createContext({});
vm.runInContext(readFileSync(join(root, "docs/js/record-card.js"), "utf8"), context);
const RecordCard = vm.runInContext("RecordCard", context);
const STEPS = ["Value", "Passage", "Record", "Source file", "Producer", "State"];
const fallback = resolve(here, "../../../data/print/derived/viewer");
const dir = resolve(process.argv[2] ?? (existsSync(join(here, "index.json")) ? here : fallback));
const index = JSON.parse(readFileSync(join(dir, "index.json"), "utf8"));
const concordance = existsSync(join(dir, "wiki_concordance.json")) ? JSON.parse(readFileSync(join(dir, "wiki_concordance.json"), "utf8")) : null;
const chunks = [...new Set(index.map((o) => o.chunk))];
const inIndex = new Set(index.map((o) => o.id));
const rowOf = new Map(index.map((o) => [o.id, o]));
const siblings = new Map();
for (const o of index) siblings.set(o.entry, [...(siblings.get(o.entry) ?? []), o.id]);

let objects = 0;
let values = 0;
let cardChains = 0;

// One object through the adapter and the shared card, read as a reader sees it.
function checkRecordCard(object, byId, all) {
  const m = cardModel({ entry: rowOf.get(object.id), object, byId, concordance, siblings: siblings.get(object.entry) });
  const html = RecordCard.card(m);
  const buttons = chainButtons(html);
  const panels = ids(html);
  const byChain = chainRows(m);
  const bare = markersWithoutButton(html);
  if (bare.length) fail(`${object.id}: data-provenance-for without a visible chain button (${[...new Set(bare)].join(", ")})`);
  if (buttons.length !== all.length) fail(`${object.id}: Records card shows ${buttons.length} chain buttons for ${all.length} values`);
  const seen = new Set();
  for (const b of buttons) {
    const hit = byChain.get(b.controls);
    if (!hit) {
      fail(`${object.id}: chain button ${b.controls} belongs to no value`);
      continue;
    }
    if (seen.has(b.controls)) fail(`${object.id}: two buttons control ${b.controls}`);
    seen.add(b.controls);
    if (!panels.has(b.controls)) fail(`${object.id}: aria-controls ${b.controls} leads to no panel`);
    if (b.key !== hit.r.key) fail(`${object.id}: chain ${b.controls} stands under "${b.key}", its row is "${hit.r.key}"`);
    if (!b.word) fail(`${object.id}: chain ${b.controls} has no visible producer word`);
    const v = hit.r.values[hit.i];
    const steps = visibleText(RecordCard.chain(m, hit.r, hit.i));
    for (const step of STEPS) if (!steps.includes(step)) fail(`${object.id} ${v.field}: chain lacks the step ${step}`);
    const passage = RecordCard.passage(m, v);
    if (!passage.located || passage.text !== all.find((r) => r.index === v.index)?.exact) fail(`${object.id} ${v.field}: chain passage is not the exact passage`);
    cardChains += 1;
  }
  const indices = new Set([...byChain.values()].map(({ r, i }) => r.values[i].index));
  if (indices.size !== all.length) fail(`${object.id}: card model holds ${indices.size} of ${all.length} values`);
  if (m.relation.state !== "proposed") fail(`${object.id}: relation in state ${m.relation.state}`);
  for (const page of m.wiki.candidates) {
    for (const href of [page.href, ...page.routes.map((r) => r.href).filter(Boolean)]) if (!href.startsWith("#entry=")) fail(`${object.id}: wiki link ${href} leaves the app`);
  }
}
let failures = 0;
const fail = (message) => {
  failures += 1;
  if (failures <= 50) console.error(`FEHLER ${message}`);
};
for (const chunk of chunks) {
  const text = readFileSync(join(dir, chunk), "utf8");
  const doc = JSON.parse(text);
  const { byId, objects: nodes } = indexGraph(doc);
  // An independent count: every value node as written in the file.
  const written = (text.match(/"kp:Value"/g) || []).length;
  let listed = 0;
  for (const object of nodes) {
    objects += 1;
    if (!inIndex.has(object.id)) fail(`${object.id} is missing from the index`);
    const all = rows(object);
    listed += all.length;
    for (const row of all) {
      if (!chainComplete(chain(object, row, byId))) fail(`${object.id} ${row.field}: incomplete chain`);
      const { heading, label } = fieldLabel(row.field);
      if (!label || CODE.test(label) || CODE.test(heading) || CODE.test(valueName(row.field))) fail(`${object.id} ${row.field}: label "${heading}" / "${label}"`);
      if (/types\[\d+\]$/.test(row.field) && valueText(row).includes("_")) fail(`${object.id} ${row.field}: type shown as code`);
      const source = byId.get(row.source);
      if (!source?.volume || !Number.isInteger(source.pdfPage) || !pdfHref(source.volume, source.pdfPage).endsWith(`#page=${source.pdfPage}`)) {
        fail(`${object.id} ${row.field}: no PDF page`);
      }
    }
    // The card shows every value exactly once.
    const shown = shownIndices(cardLines(all)).sort((a, b) => a - b);
    if (shown.length !== all.length || shown.some((n, i) => n !== i)) fail(`${object.id}: card shows ${shown.length} of ${all.length} values`);
    checkRecordCard(object, byId, all);
  }
  values += listed;
  if (listed !== written) fail(`${chunk}: ${written} values written, ${listed} shown`);
}
if (objects !== index.length) fail(`index lists ${index.length} objects, chunks hold ${objects}`);
let candidates = 0;
if (concordance) {
  for (const o of index) {
    const w = wikiState(concordance, o.id, o.entry);
    if (!WIKI_STATUS[w.status]) fail(`${o.id}: wiki status ${w.status}`);
    for (const c of [...w.align, ...w.same, ...w.cand]) {
      candidates += 1;
      if (c.state !== "proposed") fail(`${o.id}: wiki claim ${c.claim} in state ${c.state}`);
    }
    for (const c of candidatesOf(w)) if (/match|claim:/i.test(candidateRoute(c))) fail(`${o.id}: route of wiki page ${c.page} reads "${candidateRoute(c)}"`);
  }
}
console.log(
  `${failures ? "FEHLER" : "OK"} ${objects} objects, ${values} values shown once each with their chains and PDF pages; ${cardChains} visible chains on the Records cards; ${concordance ? `${candidates} wiki candidates, all proposed` : "no wiki concordance"}; failures ${failures}`
);
process.exit(failures ? 1 : 0);

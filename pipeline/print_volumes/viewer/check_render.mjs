// Coverage check of the card workbench over all JSON-LD chunks: every value of
// every object gets a row, a complete provenance chain, a readable name, a
// PDF page, and exactly one token on its card, so that no value can be decided
// or confirmed unseen; and the wiki projection never names a candidate a match.
// Usage: node pipeline/print_volumes/viewer/check_render.mjs [data/print/derived/viewer]
// Exits 1 if any object fails.

import { existsSync, readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { WIKI_STATUS, candidateRoute, candidates as candidatesOf, cardLines, chain, chainComplete, fieldLabel, indexGraph, pdfHref, rows, shownIndices, valueName, valueText, wikiState } from "./render.js";

const CODE = /[[\]._]/;

const here = dirname(fileURLToPath(import.meta.url));
const fallback = resolve(here, "../../../data/print/derived/viewer");
const dir = resolve(process.argv[2] ?? (existsSync(join(here, "index.json")) ? here : fallback));
const index = JSON.parse(readFileSync(join(dir, "index.json"), "utf8"));
const concordance = existsSync(join(dir, "wiki_concordance.json")) ? JSON.parse(readFileSync(join(dir, "wiki_concordance.json"), "utf8")) : null;
const chunks = [...new Set(index.map((o) => o.chunk))];
const inIndex = new Set(index.map((o) => o.id));

let objects = 0;
let values = 0;
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
  `OK ${objects} objects, ${values} values shown once each with their chains and PDF pages; ${concordance ? `${candidates} wiki candidates, all proposed` : "no wiki concordance"}; failures ${failures}`
);
process.exit(failures ? 1 : 0);

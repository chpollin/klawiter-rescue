// Coverage check of the print viewer over all JSON-LD chunks: every value of
// every object gets a row, every row a complete provenance chain and a
// readable label, so that no schema path reaches the page.
// Usage (from data/print/derived/viewer): node check_render.mjs
// Exits 1 if any object's rows, chains or labels are incomplete.

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chain, chainComplete, fieldLabel, indexGraph, rows, valueText } from "./render.js";

const CODE = /[[\]._]/;

const here = dirname(fileURLToPath(import.meta.url));
const index = JSON.parse(readFileSync(join(here, "index.json"), "utf8"));
const chunks = [...new Set(index.map((o) => o.chunk))];
const inIndex = new Set(index.map((o) => o.id));

let objects = 0;
let values = 0;
let failures = 0;
for (const chunk of chunks) {
  const text = readFileSync(join(here, chunk), "utf8");
  const doc = JSON.parse(text);
  const { byId, objects: nodes } = indexGraph(doc);
  // An independent count: every value node as written in the file.
  const written = (text.match(/"kp:Value"/g) || []).length;
  let listed = 0;
  for (const object of nodes) {
    objects += 1;
    if (!inIndex.has(object.id)) {
      failures += 1;
      console.error(`FEHLER ${object.id} is missing from the index`);
    }
    const shown = rows(object);
    listed += shown.length;
    for (const row of shown) {
      if (!chainComplete(chain(object, row, byId))) {
        failures += 1;
        console.error(`FEHLER ${object.id} ${row.field}: incomplete chain`);
      }
      const { heading, label } = fieldLabel(row.field);
      if (!label || CODE.test(label) || CODE.test(heading)) {
        failures += 1;
        console.error(`FEHLER ${object.id} ${row.field}: label "${heading}" / "${label}"`);
      }
      if (/types\[\d+\]$/.test(row.field) && valueText(row).includes("_")) {
        failures += 1;
        console.error(`FEHLER ${object.id} ${row.field}: type shown as code`);
      }
    }
  }
  values += listed;
  if (listed !== written) {
    failures += 1;
    console.error(`FEHLER ${chunk}: ${written} values written, ${listed} shown`);
  }
}
if (objects !== index.length) {
  failures += 1;
  console.error(`FEHLER index lists ${index.length} objects, chunks hold ${objects}`);
}
console.log(`OK ${objects} objects, ${values} values shown with their chains; failures ${failures}`);
process.exit(failures ? 1 : 0);

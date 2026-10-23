// Node test of the lab's browser rules; runs with `node pipeline/lab/test_lab_js.mjs`,
// no npm dependency. fold() is checked against fold_samples.json, the file the
// Python test checks fold_search against, so both folds stay in step.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import { fold } from '../../docs/lab/js/lab.js';
import {
  editionStateText, originLabel, placeStateParts, placeStateText, printPaneState,
} from '../../docs/lab/js/labels.js';

const samples = JSON.parse(readFileSync(new URL('./fold_samples.json', import.meta.url), 'utf8'));
for (const { input, expected } of samples.samples) {
  assert.equal(fold(input), expected, `fold(${JSON.stringify(input)})`);
}

// The three print-pane cases of S6.1.
assert.equal(printPaneState(false, null).kind, 'not-compared');
assert.equal(printPaneState(true, null).kind, 'no-match');
assert.equal(printPaneState(true, null).sentence, 'Compared locally, no match found.');
assert.equal(printPaneState(true, { print: [] }).kind, 'no-match');
assert.equal(printPaneState(true, { print: [{ printId: 'A2/F/p357l21' }] }).kind, 'matches');

// Label mapping: short producer beside the state word, warning and scope visible.
const confirmed = {
  place: 'Praha', qid: 'Q1085', state: 'confirmed', warning: null,
  producer: 'independent LLM agents against source and Wikidata, adjudicated by the main LLM agent under operator delegation, no person',
  producerShort: 'LLM agent, delegated', decision: { storedAction: 'confirm' },
};
assert.equal(placeStateText(confirmed),
  "Wikidata link Q1085: confirmed, LLM agent, delegated, for the name 'Praha', not for this publication");
const low = { ...confirmed, place: 'Nicosia, Cyprus', qid: 'Q3856', warning: 'no source occurrence' };
assert.equal(placeStateParts(low).warning, 'no source occurrence');
assert.match(placeStateText(low, 'this record'), /confirmed, warning: no source occurrence, LLM agent, delegated, .*not for this record$/);
assert.equal(placeStateText({ place: 'Praha', decision: null }), 'Praha: no Wikidata decision recorded, no link');
const contested = { ...confirmed, qid: null, state: 'contested', producerShort: 'LLM agent, delegated' };
assert.equal(placeStateParts(contested).state, 'contested');
for (const text of [placeStateText(confirmed), placeStateText(low)]) {
  assert.ok(!text.includes('·'), 'no middle dots in UI text');
  assert.ok(text.includes('LLM agent'), 'agent producers name the LLM agent');
}
assert.equal(editionStateText({ state: 'confirmed', producerShort: 'LLM agent', date: '2026-08-21' }), 'confirmed, LLM agent (2026-08-21)');
assert.equal(originLabel('regex'), 'rule');
assert.equal(originLabel('llm'), 'LLM gap fill');
assert.equal(originLabel('missing'), null);

console.log(`ok ${samples.samples.length} fold samples, print-pane cases, label mapping`);

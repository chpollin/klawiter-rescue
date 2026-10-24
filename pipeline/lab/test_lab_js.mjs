// Node test of the lab's browser rules; runs with `node pipeline/lab/test_lab_js.mjs`,
// no npm dependency. fold() is checked against fold_samples.json, the file the
// Python test checks fold_search against, so both folds stay in step. Fixture
// values are cut from the prepared lab data (pages 279, 340, 4456, 5357 and the
// search rows of lab-work/249, 281, 774 and 6820).
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import { fold } from '../../docs/lab/js/lab.js';
import {
  editionStateText, originLabel, placeStateParts, placeStateText, printPaneState, provenanceSteps,
} from '../../docs/lab/js/labels.js';
import { editionsByLanguage, labelLanguage, pageRank, rankWorks } from '../../docs/lab/js/editions.js';

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
const AGENT = 'LLM agent, delegated, no person';
const confirmed = {
  place: 'Praha', qid: 'Q1085', state: 'confirmed', warning: null,
  producer: 'independent LLM agents against source and Wikidata, adjudicated by the main LLM agent under operator delegation, no person',
  producerShort: AGENT, decision: { storedAction: 'confirm' },
};
assert.equal(placeStateText(confirmed),
  "Wikidata link Q1085: confirmed, LLM agent, delegated, no person, for the name 'Praha', not for this publication");
const low = { ...confirmed, place: 'Nicosia, Cyprus', qid: 'Q3856', warning: 'no source occurrence' };
assert.equal(placeStateParts(low).warning, 'no source occurrence');
assert.match(placeStateText(low, 'this record'), /confirmed, warning: no source occurrence, LLM agent, delegated, no person, .*not for this record$/);
assert.equal(placeStateText({ place: 'Praha', decision: null }), 'Praha: no Wikidata decision recorded, no link');
const contested = { ...confirmed, qid: null, state: 'contested' };
assert.equal(placeStateParts(contested).state, 'contested');
for (const text of [placeStateText(confirmed), placeStateText(low)]) {
  assert.ok(!text.includes('·'), 'no middle dots in UI text');
  assert.ok(text.includes('LLM agent') && text.includes('no person'), 'agent producers name the LLM agent and no person');
}
assert.equal(editionStateText({ state: 'confirmed', producerShort: AGENT, date: '2026-08-21' }), 'confirmed, LLM agent, delegated, no person (2026-08-21)');
assert.equal(originLabel('regex'), 'rule');
assert.equal(originLabel('llm'), 'LLM gap fill');
assert.equal(originLabel('missing'), null);

// Search order (S1.1): the work whose own title equals the query comes before
// works found only through an anchor page title.
const work = (id, t, v, u, members) => ({ id, t, v, u, k: fold(t), m: members.map(m => [m, fold(m)]) });
const works = [
  work('lab-work/249', 'Brennendes Geheimnis. Erzählung', true, 56, ['Schachnovelle und andere Erzählungen']),
  work('lab-work/774', 'Der Amokläufer', true, 65, ['Schachnovelle * Brief einer Unbekannten * Der Amokläufer']),
  work('lab-work/6820', 'Schachnovelle', true, 72, ['Schachnovelle (VIST)']),
  work('lab-work/281', 'Schachnovelle und andere Erzählungen', false, 2, ['Schachnovelle und andere Erzählungen']),
];
assert.deepEqual(rankWorks(works, fold('Schachnovelle')).map(w => w.id),
  ['lab-work/6820', 'lab-work/281', 'lab-work/774', 'lab-work/249'], 'member-only matches: larger work first');
assert.equal(pageRank({ kt: 'schachnovelle' }, 'schachnovelle'), 0);
assert.equal(pageRank({ kt: 'shakhmatayin novel', kb: 'schachnovelle' }, 'schachnovelle'), 4);
assert.equal(pageRank({ kt: 'shakhmatayin novel' }, 'schachnovelle'), null);

// Editions by language (S1.2) on rows of lab-work/6820 as works.json holds them.
const pub340 = { id: 'klawiter:publication/340-1973-a', year: 1973, imprint: '“Hayastan” Hratarakch‘ut‘yun, Yerevan', language: 'Armenian' };
const schach = {
  anchor: { members: [{ pageId: 6820, title: 'Schachnovelle (VIST)', language: 'German', publications: null, allYears: [1888, 1892, 2019] }, { pageId: 279, title: 'Schachnovelle', language: 'German', publications: [
    { id: 'klawiter:publication/279-1942-a', year: 1942, imprint: 'Pigmalión, Buenos Aires', language: 'German' }] }] },
  linkedByCompiler: {
    translationsByLanguage: { Armenian: { rows: [{ pageId: 5357, title: 'Byuzandioni arumě', language: 'Armenian', publications: null, allYears: [1973, 1974, 1986] }] } },
    germanPagesLinkingTheAnchor: { rows: [{ pageId: 258, title: 'Erstes Erlebnis. Vier Geschichten aus Kinderland', language: 'German', publications: [{ id: 'klawiter:publication/258-1911-a', year: 1911, imprint: 'Insel-Verlag, Leipzig', language: 'German' }] }] },
    adaptationsAndReadings: { count: { pages: 0 } },
    secondaryLiteratureAndOther: { count: { pages: 7 } },
  },
  citingTitleInBrackets: { byEntryType: {
    fiction: { Armenian: { rows: [{ pageId: 340, title: 'Shakhmatayin novel', language: 'Armenian', publications: [pub340] }] } },
    film: { 'language not recorded': { rows: [{ pageId: 4456, title: 'The Royal Game / Film', language: null, publications: [{ id: 'klawiter:publication/4456-1964-a', year: 1964, language: null }] }] } },
  },
  possiblySameTitle: { count: { pages: 0, publications: 0 }, rows: [] } },
  listedAsText: { sources: [{ pageId: 4916, germanReprints: [], languages: [
    { language: 'Armenian', text: '"Shakhmatayin novel" in Mardkut‘yan asteghayin zhamerě' },
    { language: 'Basque', text: 'Xake nobela [Pomplona, 1999], No. 2, pp. (14)-(104)' }] }] },
};
const zweig = new Set(['fiction', 'historical-study']);
const ed = editionsByLanguage(schach, zweig);
assert.deepEqual(ed.rows.map(r => r.language), ['German', 'Armenian']);
const arm = ed.rows[1];
assert.equal(arm.units.length, 2, 'one publication and one page without breakdown');
assert.equal(arm.pages, 2);
assert.equal(arm.first, 1973);
assert.equal(arm.last, 1973, 'page years without breakdown do not enter first and last year');
assert.equal(arm.publications, 1);
assert.equal(arm.withoutBreakdown, 1);
assert.deepEqual(arm.basis, { anchor: 0, linked: 1, brackets: 1 });
assert.equal(arm.textLines.length, 1);
assert.deepEqual(ed.textOnly.map(l => l.language), ['Basque']);
assert.equal(ed.leftOut.otherTypesInBrackets, 1, 'the film page is left out and counted');
assert.equal(ed.total, 3);
assert.deepEqual(ed.leftOut.anchorsWithoutBreakdown.map(a => a.pageId), [6820], 'the VIST work page is no edition');
assert.equal(ed.rows[0].first, 1942, 'a German page that only names the work page is no edition');
assert.equal(ed.leftOut.germanPagesNamingTheWorkPage, 1);
const filtered = editionsByLanguage(schach, zweig, { lang: 'Armenian', from: 1980, to: null });
assert.equal(filtered.shown, 1);
assert.deepEqual(filtered.rows.map(r => r.language), ['Armenian']);
assert.equal(labelLanguage('Croatian (Serbo-Croatian)'), 'croatian');

// Page 426 (lab-work/54) records no publication language; the page language
// Croatian stands in, marked. Page 413 (lab-work/7460) cites a variant title and
// stays out of the table, but the Chinese line says that such a page exists.
const ungeduld = {
  ...schach,
  anchor: { members: [] },
  linkedByCompiler: { ...schach.linkedByCompiler, translationsByLanguage: {}, germanPagesLinkingTheAnchor: { rows: [] } },
  citingTitleInBrackets: { byEntryType: { fiction: { Croatian: { rows: [{ pageId: 426, title: 'Nestrpljivo srce', language: 'Croatian', publications: [{ id: 'klawiter:publication/426-1956-a', year: 1956, imprint: 'Matica Srpska, Novi Sad', language: null }] }] } } },
    possiblySameTitle: { count: { pages: 1, publications: 26 }, rows: [{ pageId: 413, title: 'Yige mosheng nüren de laixin / Volume', language: 'Chinese', publications: [] }] } },
  listedAsText: { sources: [{ pageId: 7460, germanReprints: [], languages: [{ language: 'Chinese', text: 'Yige mosheng nüren de laixin' }] }] },
};
const ung = editionsByLanguage(ungeduld, zweig);
assert.deepEqual(ung.rows.map(r => r.language), ['Croatian']);
assert.ok(ung.rows[0].units[0].languageFromPage);
assert.equal(ung.textOnly[0].variantPages, 1);
assert.equal(ung.leftOut.possiblySameTitle.pages, 1);

// Provenance chain (S2.6) of the translator of page 340: an LLM gap fill in the
// page-level record, read by rule in the publication layer.
const meta = {
  llm: { model: 'gemini-3.1-flash-lite-preview', frozenAt: '2026-08-21T17:51:38.288166+00:00' },
  llmNotStored: 'per-record prompt and raw response not stored, prompt template hash recorded',
  texts: {
    source: 'plain text the pipeline derived from the wiki page',
    restored: 'the page is published from the last human revision before a Redirect fixer overwrite',
    noValue: 'no value recorded, a gap in the source and a value not extracted are not yet distinguished',
    verificationNotFound: 'the automatic check did not find this value in the raw text; the check covers page-level values only',
  },
};
const occ = { parts: [{ part: 'Lili Poghosyan', occurrences: [{ start: 115, end: 129, publicationId: pub340.id, own: true }], noExactOccurrence: false }], noExactOccurrence: false };
const pubField = { value: 'Lili Poghosyan', origin: 'regex', occurrences: occ };
const page340 = {
  pageId: 340, source: { textId: 40823, restoredRevision: null },
  publications: [{ id: pub340.id, year: 1973, fields: { translators: [pubField] } }],
};
const recordField = { value: 'Lili Poghosyan', origin: 'llm', occurrences: occ, verification: 'found', boundary: { parts: [{ part: 'Lili Poghosyan', result: 'pass', heldBy: [] }] } };
const chain = steps => steps.map(s => `${s.step}: ${s.text}`).join('\n');
const recordChain = chain(provenanceSteps({ kind: 'record', label: 'Translator', field: recordField, page: page340, pd: null, pubFieldKey: 'translators', print: { kind: 'compared' }, meta }));
assert.match(recordChain, /^Source: Wiki page 340, text 40823/);
assert.match(recordChain, /LLM gap fill: .*gemini-3\.1-flash-lite-preview.*frozen on 2026-08-21/);
assert.match(recordChain, /publication layer reads the same value by rule in the passage of the 1973 publication/);
assert.match(recordChain, /Verification stage of the pipeline: found this value/);
assert.match(recordChain, /Checked by: No person has checked this value\./);
assert.ok(!/confidence|score/i.test(recordChain), 'no confidence values');
const pubChain = chain(provenanceSteps({
  kind: 'publication', label: 'Translator', field: pubField, page: page340, pub: page340.publications[0], pd: null, agree: ['translator', 0], meta,
  print: { kind: 'compared', value: { field: 'translator', index: 0, value: 'Lili Poghosyan', foundIn: [] }, entries: [] },
}));
assert.match(pubChain, /Extraction rule of the publication layer, from the passage of the 1973 publication/);
assert.match(pubChain, /Not found in exactly this form in the matched print entries/);
assert.match(pubChain, /not run, it covers page-level values only/);
const published = provenanceSteps({ kind: 'publication', label: 'Translator', field: pubField, page: page340, pub: page340.publications[0], pd: null, meta, print: { kind: 'not-compared' } });
assert.match(published.at(-2).text, /Not compared with the print volumes/);
const placeChain = chain(provenanceSteps({
  kind: 'publication', label: 'Place', field: { value: 'Yerevan', origin: 'regex' }, page: page340, pub: page340.publications[0],
  pd: { ...confirmed, place: 'Yerevan', qid: 'Q1953' }, meta, print: { kind: 'not-compared' },
}));
assert.match(placeChain, /Wikidata link Q1953: confirmed, LLM agent, delegated, no person, for the name 'Yerevan', not for this publication/);
assert.match(placeChain, /LLM agents \(Wikidata link of the place name only\)/);
const gapChain = chain(provenanceSteps({
  kind: 'record', label: 'Translator', page: page340, pd: null, meta, print: { kind: 'not-compared' },
  field: { value: null, origin: 'missing', verificationCandidate: { value: 'Jorgi Doksani' } },
}));
assert.match(gapChain, /reported "Jorgi Doksani" in the raw text while the record is empty; no rule and no person adopted it/);

console.log(`ok ${samples.samples.length} fold samples, print-pane cases, label mapping, search order, editions by language, provenance chain`);

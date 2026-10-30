/**
 * Pins the shared record card (docs/js/record-card.js) and the wiki card
 * that renders through it (docs/js/detail.js).
 *
 * One component draws a wiki record and a print object, so both models give
 * the same regions in the same order and the same row anatomy. Every value
 * names its producer on a visible button whose aria-controls leads to that
 * value's chain, and the chain shows its steps as text. A gap reads in words
 * by its kind, never as a first match, and every model string is escaped.
 * All values below are invented; no print text enters this file.
 */
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const read = file => fs.readFileSync(path.join(__dirname, '..', 'docs', 'js', file), 'utf8');

function cardOnly() {
  const ctx = { console };
  vm.createContext(ctx);
  vm.runInContext(read('record-card.js'), ctx);
  return vm.runInContext('RecordCard', ctx);
}

const STEPS = ['Value', 'Passage', 'Record', 'Source file', 'Producer', 'State'];

const visible = html => html.replace(/<[^>]*>/g, ' ').replace(/&amp;/g, '&').replace(/&lt;/g, '<')
  .replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/\s+/g, ' ').trim();

/** The regions of a card in document order. */
const regions = html => [...html.matchAll(/data-region="([^"]+)"/g)].map(m => m[1]);

/** Each row as its key and the shape of its values: label, value spans, buttons, slots. */
function anatomy(html) {
  return [...html.matchAll(/<div class="meta-row rc-row"([^>]*)>([\s\S]*?)(?=<div class="meta-row rc-row"|<\/div><\/section>)/g)]
    .map(m => ({
      provenanceFor: /data-provenance-for="/.test(m[1]),
      label: /^<div class="meta-label"/.test(m[2]),
      values: (m[2].match(/class="rc-value/g) || []).length,
      buttons: (m[2].match(/<button type="button" class="prov-badge rc-producer-btn/g) || []).length,
      slots: (m[2].match(/<div class="rc-chain" id="[^"]+" role="group"[^>]*hidden><\/div>/g) || []).length,
    }));
}

function value(text, producer, passage, extra = {}) {
  return Object.assign({ text, producer, state: 'not-reviewed',
    chain: { passage, record: { id: 'x:record/1', sign: 'Invented record' },
      sourceFile: { file: 'invented.xml', sha256: 'ab'.repeat(32) }, producer: { words: 'invented rule' } } },
  extra);
}

function wikiModel() {
  const text = 'Invented title. Nowhere: Invented House, 1901. Translated by A. Person.';
  return {
    kind: 'wiki', id: 'klawiter:entry/999001', permalink: '#entry=999001',
    sourceSign: { label: 'Wiki page 999001', pageId: 999001 }, title: 'Invented title', type: 'Book',
    relation: { state: 'proposed', words: 'no print candidate' },
    review: { state: 'not-reviewed', producer: 'no person', contested: false },
    snippet: 'Nowhere: Invented House, 1901',
    groups: [{ heading: 'Page fields', rows: [
      { key: 'places', label: 'Place of publication', idBase: 'w-places',
        values: [value('Nowhere', 'rule', { textStart: 17, textEnd: 24 })] },
      { key: 'publisher', label: 'Publisher', idBase: 'w-publisher',
        values: [value('Invented House', 'rule', { gap: 'not-located', reason: 'occurs 2 times' })] },
    ] }],
    sourceText: { text, marks: [{ start: 17, end: 24, key: 'places', valueIndex: 0, id: 'mark-w-places-0' }] },
  };
}

function printModel() {
  const text = 'Invented entry text: Somewhere, Imaginary Press 1902. 120 pp.';
  return {
    kind: 'print', id: 'X/Z/1#1', permalink: '#print=X%2FZ%2F1%231',
    sourceSign: { label: 'Print volume X', volume: 'X', pdfPage: 7 }, title: 'Invented entry',
    type: 'Book', relation: { state: 'proposed', route: 'title', words: 'wiki candidate' },
    review: { state: 'open', producer: 'no person', contested: true },
    snippet: 'Somewhere, Imaginary Press 1902',
    groups: [{ heading: 'Imprint', rows: [
      { key: 'place', label: 'Place', idBase: 'p-place',
        values: [value('Somewhere', 'rule', { textStart: 21, textEnd: 30 })] },
      { key: 'publisher', label: 'Publisher', idBase: 'p-publisher',
        values: [value('Imaginary Press', 'llm', { textStart: 32, textEnd: 47 })] },
    ] }],
    sourceText: { text, marks: [{ start: 21, end: 30, key: 'place', valueIndex: 0 }] },
  };
}

test('a wiki and a print model render the same regions and the same row anatomy', () => {
  const RecordCard = cardOnly();
  const wiki = RecordCard.card(wikiModel());
  const print = RecordCard.card(printModel());
  assert.deepStrictEqual(regions(wiki), ['head', 'values', 'source']);
  assert.deepStrictEqual(regions(print), regions(wiki));
  const rows = [anatomy(wiki), anatomy(print)];
  assert.strictEqual(rows[0].length, 2);
  assert.deepStrictEqual(rows[1], rows[0]);
  for (const row of rows[0]) {
    assert.deepStrictEqual(row, { provenanceFor: true, label: true, values: 1, buttons: 1, slots: 1 });
  }
  // The slip has its two lines and three marks on both sources.
  for (const m of [wikiModel(), printModel()]) {
    const slip = RecordCard.slip(m);
    assert.match(slip, /class="rc-slip-line"/);
    assert.match(slip, /class="rc-slip-snippet"/);
    assert.match(slip, /class="rc-sign rc-sign-/);
    assert.match(slip, /class="rc-relation"/);
    assert.match(slip, /class="rc-review"/);
    assert.doesNotMatch(slip, /prov-badge|meta-row/, 'no value or chain on a slip');
  }
  assert.match(RecordCard.slip(printModel()), /contested/);
  assert.match(RecordCard.slip(printModel()), /wiki candidate, title<span class="rc-state-word">, proposed/);
});

test('every value button leads through aria-controls to its chain with every step as text', () => {
  const RecordCard = cardOnly();
  for (const m of [wikiModel(), printModel()]) {
    const html = RecordCard.card(m);
    const ids = [...html.matchAll(/<button type="button" class="prov-badge[^"]*"[^>]*aria-controls="([^"]+)"/g)]
      .map(x => x[1]);
    assert.strictEqual(ids.length, 2);
    for (const id of ids) {
      // The slot it controls is in the card, empty until opened.
      assert.match(html, new RegExp(`<div class="rc-chain" id="${id}"[^>]*hidden></div>`));
      const row = m.groups[0].rows.find(r => r.values.some((v, i) => RecordCard.chainId(r, v, i) === id));
      const i = row.values.findIndex((v, k) => RecordCard.chainId(row, v, k) === id);
      const panel = RecordCard.chain(m, row, i);
      assert.match(panel, new RegExp(`^<div class="rc-chain" id="${id}"`));
      assert.doesNotMatch(panel, /\shidden[\s>]/);
      const text = visible(panel);
      for (const step of STEPS) assert.match(text, new RegExp(`(^| )${step} \\S`), `${step} in ${id}`);
    }
  }
  // A located passage quotes the displayed text by its offsets.
  const m = printModel();
  assert.match(visible(RecordCard.chain(m, m.groups[0].rows[0], 0)),
    /Passage “?Somewhere”? characters 21–30 of the source text/);
  // The producer word of an LLM value reads as such, at the weight of a rule.
  assert.match(RecordCard.row(m.groups[0].rows[1]), /rc-producer-llm[^>]*><svg class="rc-producer-icon"[\s\S]*?<\/svg><span class="rc-producer">LLM-enriched</);
  // Each kind of evidence carries its family, so print and wiki group alike.
  assert.strictEqual(RecordCard.producerFamily('llm'), 'llm');
  assert.strictEqual(RecordCard.producerFamily('compiler'), 'rule');
  assert.strictEqual(RecordCard.producerFamily('inherited'), 'derived');
  assert.strictEqual(RecordCard.producerFamily('unknown-kind'), 'rule');
  assert.match(RecordCard.row(m.groups[0].rows[1]), /rc-family-llm" title="Proposed by a language model/);
});

test('each gap kind reads in its own words, and none quotes a first match', () => {
  const RecordCard = cardOnly();
  const text = 'An invented text in which the value Nowhere occurs, and Nowhere again.';
  const m = { kind: 'wiki', id: 'x', sourceText: { text } };
  const said = passage => visible(RecordCard.chain(m, { key: 'k', label: 'K',
    values: [value('Nowhere', 'rule', passage)] }, 0));
  assert.match(said({ gap: 'not-located', reason: 'occurs 2 times' }),
    /Passage passage not located \(occurs 2 times\)/);
  assert.match(said({ gap: 'rule', rule: 'statement-bindings' }), /Passage gap by rule: statement-bindings/);
  assert.match(said({ gap: 'source' }), /Passage not given in the source/);
  assert.match(said({ gap: 'category' }), /Passage category link in the wiki markup/);
  assert.match(said({ gap: 'derived', reason: 'read from the year' }), /Passage derived from another value/);
  // No offsets and no gap kind is still a gap, and an unknown kind is not
  // promoted to a located passage.
  assert.match(said({}), /Passage passage not located/);
  assert.match(said({ gap: 'invented-kind' }), /Passage passage not located/);
  // Offsets outside the displayed text locate nothing.
  assert.match(said({ textStart: 500, textEnd: 507 }), /passage not located \(its offsets leave the displayed text\)/);
  for (const passage of [{}, { gap: 'not-located' }, { gap: 'rule' }, { gap: 'source' }]) {
    assert.doesNotMatch(RecordCard.chain(m, { key: 'k', label: 'K', values: [value('Nowhere', 'rule', passage)] }, 0),
      /<q /, 'a gap quotes no passage');
  }
});

test('every model string is escaped, and only adapter markup passes as markup', () => {
  const RecordCard = cardOnly();
  const evil = '<img src=x onerror=alert(1)>"\'&';
  const m = {
    kind: 'print', id: evil, permalink: `javascript:${evil}`, title: evil, type: evil, snippet: evil,
    sourceSign: { label: evil, volume: evil, pdfPage: evil },
    relation: { state: evil, route: evil, words: evil }, review: { state: evil, producer: evil, contested: true },
    groups: [{ heading: evil, state: evil, producer: evil, rows: [{ key: evil, label: evil, help: evil,
      values: [Object.assign(value(evil, evil, { textStart: 0, textEnd: 5, scope: evil }), {
        chainId: evil, href: evil, producerWord: evil, stateText: evil,
        chain: { passage: { textStart: 0, textEnd: 5, scope: evil, markId: evil },
          record: { id: evil, type: evil, sign: evil, textId: evil, revisionNote: evil, extra: [evil],
            block: { start: 0, end: 5, sha256: evil } },
          sourceFile: { file: evil, sha256: evil }, producer: { words: evil, rule: evil, model: evil } } })] }] }],
    sourceText: { text: `${evil} and more`, marks: [{ start: 0, end: 5, key: evil, id: evil }] },
  };
  const row = m.groups[0].rows[0];
  const out = RecordCard.card(m) + RecordCard.slip(m) + RecordCard.chain(m, row, 0);
  assert.doesNotMatch(out, /<img/);
  assert.doesNotMatch(out, /onerror=alert\(1\)>/);
  // Every quote inside an attribute is an entity, so no attribute breaks out.
  for (const attr of out.matchAll(/\s[\w-]+="([^"]*)"/g)) assert.doesNotMatch(attr[1], /[<>]/);
  // An id is reduced to safe characters, so aria-controls and id still pair.
  const id = RecordCard.chainId(row, row.values[0], 0);
  assert.match(id, /^[A-Za-z0-9_-]+$/);
  assert.match(out, new RegExp(`aria-controls="${id}"`));
  assert.match(out, new RegExp(`<div class="rc-chain" id="${id}"`));
  // Markup an adapter built stays markup; that is the declared trust boundary.
  const trusted = RecordCard.row({ key: 'k', label: 'K', values: [{ text: 'a', html: '<a href="#x">a</a>' }] });
  assert.match(trusted, /<a href="#x">a<\/a>/);
  assert.strictEqual(RecordCard.escape(0), '0');
  assert.strictEqual(RecordCard.escape(null), '');
});

// --- The wiki card through detail.js -----------------------------------------

function detailCtx(entry, publications) {
  const ctx = {
    console,
    document: { querySelectorAll: () => [], addEventListener() {}, getElementById: () => null },
    App: {
      state: { editMode: false, singleEntry: true, query: '' },
      entries: [entry], entryMap: new Map([[entry.sourcePageId, entry]]), titleMap: new Map(),
      data: { redirects: {}, _meta: { llmEnrichment: { model: 'invented-model', promptSha256: 'cd'.repeat(32),
        frozenAt: '2001-02-03T00:00:00Z' } } },
    },
    Edit: {
      FIELD_LABELS: {}, pending: () => undefined, entryStatus: () => ({ status: 'unreviewed', pending: false }),
      triageHints: () => [], evidence: () => null, editionClaimsFor: () => [], authorityClaimsFor: () => [],
      openClaimOnValue: () => null, locationReconciliation: () => null, agentReconciliation: () => null,
    },
  };
  vm.createContext(ctx);
  for (const file of ['constants.js', 'utils.js', 'record-card.js', 'detail.js']) vm.runInContext(read(file), ctx);
  const Detail = vm.runInContext('Detail', ctx);
  if (publications) {
    Detail._pubCache.set(entry.sourcePageId, { status: 'ready', publications, nameVariants: [] });
  }
  return Detail;
}

function flatEntry() {
  return {
    '@id': 'klawiter:entry/999002', '@type': ['schema:Book'], sourcePageId: 999002, sourceTextId: 11,
    sourceBlobId: 12, pageNamespace: 0, entryType: 'fiction', title: 'Invented flat page', year: 1903,
    location: 'Nowhere', publisher: '', translator: '', categories: ['Invented Category'],
    fullBibliographicEntry: 'Nowhere, 1903. An invented line. Done.',
    fieldEvidence: { location: [{ value: 'Nowhere', textStart: 0, textEnd: 7 }] },
    revisionDates: { firstRevisionId: 5, firstRevisionTimestamp: '2001-01-01T00:00:00Z',
      lastRevisionId: 9, lastRevisionTimestamp: '2002-02-02T00:00:00Z' },
    ruleGaps: [{ gapField: 'publisher', gapRule: 'invented-binding' }],
    translationStatements: [{ language: 'Invented', container: 'An invented title', place: 'Elsewhere',
      year: 1950, sourceSlice: { start: 900, end: 950, sha256: 'ef'.repeat(32) } }],
    _provenance: { location: 'regex', publisher: 'rule-gap', translator: 'missing', year: 'llm',
      categories: 'regex', title: 'regex' },
  };
}

function chainsOf(Detail, html) {
  return [...html.matchAll(/<button type="button" class="prov-badge[^"]*"[^>]*aria-controls="([^"]+)"/g)]
    .map(m => ({ id: m[1], text: visible(Detail.chainHtml(m[1])) }));
}

test('every value of a wiki card opens its own chain, and no hidden marker stands in for one', () => {
  const entry = flatEntry();
  const Detail = detailCtx(entry);
  const html = Detail.renderInline(entry);
  assert.doesNotMatch(html, /<[^>]+\shidden[^>]*data-(?:key|provenance-for)=/, 'no hidden marker');
  assert.doesNotMatch(html, /<span hidden/);
  // Every data-provenance-for row holds a visible producer button of its own.
  const rows = [...html.matchAll(/<div class="meta-row rc-row"[^>]*data-provenance-for="([^"]+)"[^>]*>([\s\S]*?)<\/div><div class="meta-value">([\s\S]*?)<\/div>(?=<div class="rc-chain"|<\/div>)/g)];
  assert.ok(rows.length >= 6);
  for (const row of rows) assert.match(row[3], /class="prov-badge rc-producer-btn/, row[1]);
  const chains = chainsOf(Detail, html);
  assert.strictEqual(new Set(chains.map(c => c.id)).size, chains.length, 'one chain id per value');
  for (const { id, text } of chains) {
    for (const step of STEPS) assert.match(text, new RegExp(`(^| )${step} \\S`), `${step} in ${id}`);
    assert.match(text, /klawiter:entry\/999002/);
    assert.match(text, /Text ID 11, Blob ID 12/);
    assert.match(text, /revisions 5 of 2001-01-01 to 9 of 2002-02-02/);
  }
  const by = key => chains.filter(c => c.id.includes(`-${key}-`)).map(c => c.text);
  // A recorded offset locates the value; a category says where it lives.
  assert.match(by('location')[0], /Passage “?Nowhere”? characters 0–7 of the source text/);
  assert.match(html, /<mark class="rc-mark" id="mark-chain-999002-page-location-0"/);
  assert.match(by('categories')[0], /Passage category link in the wiki markup \(a \[\[Category:…\]\] link/);
  // A gap the binding rule made reads apart from a gap in the source.
  assert.match(by('publisher')[0], /Passage gap by rule: invented-binding/);
  assert.match(html, /Not recorded, gap by rule<\/span> <span class="field-sub" data-key="ruleGaps">invented-binding/);
  assert.match(by('translator')[0], /Passage not given in the source/);
  // The year carries no offset, so it is not located, whatever the text holds.
  assert.match(by('year')[0], /Passage passage not located/);
  assert.match(by('year')[0], /Producer LLM-enriched ?: .*model invented-model, frozen 2001-02-03, prompt cdcd…cdcd/);
  // A translation statement is a row with its chain, its raw offsets in words.
  assert.match(html, /data-key="translationStatements"[^>]*><div class="meta-label"[^>]*>Translation</);
  assert.match(by('translationStatements')[0],
    /Passage passage not located \(raw wiki text characters 900–950, not mapped to the displayed text\)/);
  // The source identifiers name the revisions visibly.
  assert.match(html, /<span data-key="revisionDates">Revisions 5 of 2001-01-01 to 9 of 2002-02-02<\/span>/);
});

test('a publication keeps its place and publisher rows and adds the imprint as the source words it', () => {
  const entry = Object.assign(flatEntry(), { publicationCount: 1, pageKind: 'single-publication',
    fullBibliographicEntry: 'Nowhere: Invented House, 1903. 99p.' });
  const pub = { id: 'klawiter:publication/999002-1903', year: 1903, imprint: 'Nowhere: Invented House',
    places: ['Nowhere'], publisher: 'Invented House', extent: { raw: '99p.', numbered: 99 },
    sourceSlice: { start: 40, end: 80, textStart: 0, textEnd: 35, sha256: '12'.repeat(32) },
    valueSpans: { publisher: [{ value: 'Invented House', textStart: 9, textEnd: 23 }] },
    provenance: { year: 'regex', imprint: 'regex', places: 'regex', publisher: 'regex', extent: 'regex' } };
  const Detail = detailCtx(entry, [pub]);
  const html = Detail.renderInline(entry);
  const block = html.slice(html.indexOf('aria-label="Publication 1"'));
  assert.match(block, />Imprint \(as in source\)<\/div><div class="meta-value"><span class="rc-value">Nowhere: Invented House</);
  assert.match(block, />Place of publication</);
  assert.match(block, />Publisher</);
  const chains = chainsOf(Detail, html);
  const text = key => chains.find(c => c.id.includes(`-pub0-${key}-`)).text;
  assert.match(text('publisher'), /Passage “?Invented House”? characters 9–23 of the source text/);
  // Without its own span a publication value names the passage it lies in.
  assert.match(text('places'),
    /Passage passage not located within the block of 1903, characters 0–35/);
  assert.match(text('places'), /publication 1903 klawiter:publication\/999002-1903/);
  assert.match(text('places'), /block characters 0–35 of the source text, raw characters 40–80, 1212…1212/);
  assert.match(block, />Passage<\/div><div class="meta-value"><span class="rc-value"><span class="field-sub">characters 0–35 of the source text</);
});

test('a chain opens on its button, closes on Escape and returns the focus', () => {
  const entry = flatEntry();
  const listeners = { click: [], keydown: [] };
  const elements = new Map();
  const make = (id) => ({ id, hidden: true, innerHTML: '', attrs: { 'aria-expanded': 'false', 'aria-controls': id },
    getAttribute(name) { return this.attrs[name]; }, setAttribute(name, v) { this.attrs[name] = String(v); },
    closest() { return null; }, focus() { focused = this; } });
  let focused = null;
  const ctx = {
    console,
    document: {
      addEventListener(type, fn) { (listeners[type] = listeners[type] || []).push(fn); },
      querySelectorAll: () => [],
      getElementById: id => elements.get(id) || null,
      querySelector: sel => { const m = /aria-controls="([^"]+)"/.exec(sel); return m ? elements.get(`btn:${m[1]}`) : null; },
    },
    App: { state: { editMode: false, singleEntry: true }, entries: [entry], entryMap: new Map(),
      titleMap: new Map(), data: { redirects: {} } },
    Edit: { FIELD_LABELS: {}, pending: () => undefined, entryStatus: () => ({ status: 'unreviewed', pending: false }),
      triageHints: () => [], evidence: () => null, editionClaimsFor: () => [], authorityClaimsFor: () => [],
      openClaimOnValue: () => null },
  };
  vm.createContext(ctx);
  for (const file of ['constants.js', 'utils.js', 'record-card.js', 'detail.js']) vm.runInContext(read(file), ctx);
  const Detail = vm.runInContext('Detail', ctx);
  const html = Detail.renderInline(entry);
  const id = /aria-controls="([^"]+)"/.exec(html)[1];
  const panel = make(id);
  panel.closest = sel => (sel.startsWith('.rc-chain') && !panel.hidden ? panel : null);
  const btn = make(id);
  btn.closest = sel => (sel.startsWith('button.rc-producer-btn') ? btn : null);
  elements.set(id, panel);
  elements.set(`btn:${id}`, btn);

  const click = target => listeners.click.forEach(fn => fn({ target, preventDefault() {} }));
  click(btn);
  assert.strictEqual(panel.hidden, false);
  assert.strictEqual(btn.getAttribute('aria-expanded'), 'true');
  for (const step of STEPS) assert.match(visible(panel.innerHTML), new RegExp(`(^| )${step} `));

  let stopped = false;
  const inside = { closest: sel => (sel.startsWith('.rc-chain') ? panel : null) };
  listeners.keydown.forEach(fn => fn({ key: 'Escape', target: inside, preventDefault() {},
    stopPropagation() { stopped = true; } }));
  assert.strictEqual(panel.hidden, true);
  assert.strictEqual(btn.getAttribute('aria-expanded'), 'false');
  assert.strictEqual(focused, btn, 'the focus returns to the value\'s button');
  assert.ok(stopped, 'the Escape does not also close the card');
  click(btn);
  assert.strictEqual(panel.hidden, false, 'it opens again');
  click(btn);
  assert.strictEqual(panel.hidden, true, 'and closes on its button');
});

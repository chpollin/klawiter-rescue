/**
 * Pins the print adapter of the record desk
 * (pipeline/print_volumes/viewer/records-print.js) on a synthetic JSON-LD
 * chunk with invented values (tests/fixtures/print-synthetic.jsonld), so no
 * print text enters the repository.
 *
 * The adapter turns a print object into the card model the shared card
 * (docs/js/record-card.js) draws. Every value gets one chain with its exact
 * passage, the record, the source file and the producer; every wiki link is
 * an in-app hash; the relation is a proposal; candidates stand once per wiki
 * page with the words that agreed; and the drawn card holds one visible
 * chain button per value under the row that names its key
 * (tests/lib/visible.cjs).
 */
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { pathToFileURL } = require('node:url');
const { chainButtons, ids, markersWithoutButton, visibleText } = require('./lib/visible.cjs');

const ROOT = path.join(__dirname, '..');
const VIEWER = path.join(ROOT, 'pipeline', 'print_volumes', 'viewer');
const FIXTURE = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'print-synthetic.jsonld'), 'utf8'));
const STEPS = ['Value', 'Passage', 'Record', 'Source file', 'Producer', 'State'];

const load = file => import(pathToFileURL(path.join(VIEWER, file)).href);

function recordCard() {
  const ctx = {};
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(path.join(ROOT, 'docs', 'js', 'record-card.js'), 'utf8'), ctx);
  return vm.runInContext('RecordCard', ctx);
}

const CONCORDANCE = {
  links: {
    'X/Z/1#1': {
      align: [{ claim: 'claim:inv-4', state: 'proposed', route: 'alignment', page: 9002, score: 0.8, method: 'shingle-alignment' }],
      same: [{ claim: 'claim:inv-1', state: 'proposed', route: 'field-match', page: 9001, target: 'klawiter:publication/9001-1901-a',
        relation: 'samePublicationAs', secondField: ['place'], secondFieldValues: ['somewhere'], method: 'title-year-field' }],
      cand: [{ claim: 'claim:inv-3', state: 'proposed', route: 'title-year', page: 9001, target: 'klawiter:entry/9001', method: 'title-year' }],
    },
  },
  pages: {
    9001: { title: 'Invented Title', place: 'Somewhere', publisher: 'Imaginary House', year: 1901 },
    9002: { title: 'Another Invented Page', year: 1950 },
  },
  pubs: { 'klawiter:publication/9001-1901-a': { title: 'Invented Title', place: 'Somewhere', year: 1901, extent: ['120'], translator: ['A. Nobody'] } },
  wikiOnlyPages: [],
};

const CHUNK = '../jsonld/X/Z-1.jsonld';
const INDEX = [
  { id: 'X/Z/1#1', entry: 'X/Z/1', volume: 'I', part: 'Z', address: 'Z 1', page: 7, title: 'Invented Title', snippet: 'Somewhere 1901', types: ['book_edition'], chunk: CHUNK, review: true, search: 'invented title somewhere 1901' },
  { id: 'X/Z/1#2', entry: 'X/Z/1', volume: 'I', part: 'Z', address: '', page: 7, title: 'Invented Sequel', snippet: 'Anywhere 1903', types: [], chunk: CHUNK, review: false, search: 'invented sequel anywhere 1903' },
  { id: 'X/Z/2#1', entry: 'X/Z/2', volume: 'I', part: 'Z', address: 'Z 2', page: 7, title: 'Second <Invented> & Title', snippet: 'Elsewhere 1902', types: [], chunk: CHUNK, review: false, search: 'second invented title elsewhere 1902' },
  { id: 'X/index/1#1', entry: 'X/index/1', volume: 'I', part: 'Index A', address: '', page: 90, title: '', snippet: 'Invented term', types: [], chunk: CHUNK, review: false, search: 'invented term' },
];

async function models() {
  const P = await load('records-print.js');
  const R = await load('render.js');
  const { byId, objects } = R.indexGraph(FIXTURE);
  const siblings = new Map();
  for (const o of INDEX) siblings.set(o.entry, [...(siblings.get(o.entry) || []), o.id]);
  const out = new Map();
  for (const object of objects) {
    const entry = INDEX.find(o => o.id === object.id);
    out.set(object.id, { object, rows: R.rows(object), m: P.cardModel({ entry, object, byId, concordance: CONCORDANCE, siblings: siblings.get(object.entry) }) });
  }
  return { P, R, byId, out };
}

test('the fixture is synthetic and self-consistent: every passage is its record slice', async () => {
  const { R, byId, out } = await models();
  assert.strictEqual(out.size, 4);
  for (const { object, rows } of out.values()) {
    for (const row of rows) {
      assert.strictEqual(byId.get(row.source).text.slice(row.start, row.end), row.exact, `${object.id} ${row.field}`);
      assert.ok(R.chainComplete(R.chain(object, row, byId)), `${object.id} ${row.field} chain`);
    }
  }
});

test('every value has one chain with its exact passage, record, source file and producer', async () => {
  const { P, out } = await models();
  for (const { object, rows, m } of out.values()) {
    const chains = P.chainRows(m);
    assert.strictEqual(chains.size, rows.length, `${object.id}: one chain per value`);
    const indices = [...chains.values()].map(({ r, i }) => r.values[i].index).sort((a, b) => a - b);
    assert.deepStrictEqual(indices, rows.map(r => r.index), `${object.id}: each value once`);
    for (const { r, i } of chains.values()) {
      const v = r.values[i];
      const row = rows.find(x => x.index === v.index);
      assert.strictEqual(v.chain.passage.text, row.exact);
      assert.strictEqual(v.chain.passage.textStart, row.start);
      assert.strictEqual(v.chain.record.id, row.source);
      assert.strictEqual(v.chain.sourceFile.file, 'invented-volume.pdf');
      assert.ok(v.chain.producer.rule.startsWith('invented'), `${v.field}: the plan's label names the rule`);
    }
  }
  const first = out.get('X/Z/1#1').m;
  const word = v => v.producerWord || v.producer;
  const values = [...P.chainRows(first).values()].map(({ r, i }) => r.values[i]);
  assert.strictEqual(word(values.find(v => v.field === 'references[0].address')), 'compiler');
  assert.strictEqual(values.find(v => v.field === 'types[0]').derivedFrom, 'the passage by its rule');
  assert.strictEqual(values.find(v => v.field === 'title').derivedFrom, undefined);
});

test('the head carries the title, the type values are a row, and an untyped apparatus item names its kind', async () => {
  const { out } = await models();
  const first = out.get('X/Z/1#1').m;
  assert.strictEqual(first.titleValue.text, 'Invented Title');
  assert.strictEqual(first.type, null, 'type values stand in their row, not again as a badge');
  const keys = first.groups[0].rows.map(r => r.key);
  assert.deepStrictEqual(keys, ['types', 'imprints', 'extent', 'references', 'inherited']);
  assert.strictEqual(out.get('X/index/1#1').m.type, 'index entry');
  assert.strictEqual(out.get('X/index/1#1').m.groups[0].rows[0].key, 'term');
});

test('links are in-app hashes, and every relation is proposed', async () => {
  const { out } = await models();
  const first = out.get('X/Z/1#1').m;
  assert.strictEqual(first.permalink, '#print=X%2FZ%2F1%231');
  for (const { m } of out.values()) assert.strictEqual(m.relation.state, 'proposed');
  assert.strictEqual(first.relation.words, 'Text candidate');
  assert.strictEqual(out.get('X/Z/2#1').m.relation.words, 'No candidate');
  const hrefs = first.wiki.candidates.flatMap(c => [c.href, ...c.routes.map(r => r.href).filter(Boolean)]);
  assert.deepStrictEqual(hrefs, ['#entry=9002', '#entry=9001', '#entry=9001&pub=9001-1901-a']);
  const target = first.groups[0].rows.find(r => r.key === 'references').values[0];
  assert.match(target.html, /href="#print=X%2FZ%2F2%231"/, 'an address target leads to its object in-app');
  const unresolved = out.get('X/index/1#1').m.groups[0].rows.find(r => r.key === 'references').values[0];
  assert.match(unresolved.html, /Z 12 unresolved/);
});

test('candidates stand once per wiki page, in route order, with the words that agreed', async () => {
  const { out } = await models();
  const pages = out.get('X/Z/1#1').m.wiki.candidates;
  assert.deepStrictEqual(pages.map(p => p.page), [9002, 9001], 'the text alignment leads');
  const page = pages[1];
  assert.deepStrictEqual(page.routes.map(r => r.route), ['field-match', 'title-year']);
  assert.ok(page.routes.every(r => r.state === 'proposed'));
  assert.deepStrictEqual(page.routes[0].agreeing, ['somewhere']);
  assert.match(page.routes[0].words, /agreeing on the place/);
  assert.doesNotMatch(page.routes.map(r => r.words).join(' '), /match|claim:/i);
  assert.deepStrictEqual(page.routes[0].fields, [['Title', 'Invented Title'], ['Imprint', 'Somewhere, 1901'], ['Extent', '120'], ['Translator', 'A. Nobody']]);
  assert.deepStrictEqual(page.fields.map(([k]) => k), ['Title', 'Imprint']);
});

test('an inherited value names its own record and is not marked in the entry text', async () => {
  const { out } = await models();
  const m = out.get('X/Z/1#1').m;
  const inherited = m.groups[0].rows.find(r => r.key === 'inherited').values[0];
  assert.strictEqual(inherited.own, false);
  assert.strictEqual(inherited.chain.record.id, 'X/Z/h1');
  assert.strictEqual(inherited.chain.passage.markId, null);
  assert.match(inherited.chain.passage.scope, /X\/Z\/h1/);
  assert.ok(m.sourceText.marks.every(mk => mk.key !== 'inherited.title'));
});

test('the source text marks the object as a block and its own passages inside it', async () => {
  const { out } = await models();
  const first = out.get('X/Z/1#1').m;
  const second = out.get('X/Z/1#2').m;
  assert.strictEqual(first.position, 'object 1 of 2 in the entry');
  assert.strictEqual(second.position, 'object 2 of 2 in the entry');
  const [block, ...marks] = second.sourceText.marks;
  assert.deepStrictEqual([block.kind, block.start, block.end, block.label], ['block', 53, 84, 'Object 2 of 2']);
  assert.ok(marks.every(mk => mk.start >= 53 && mk.end <= 84 && mk.id.startsWith('mark-')));
  assert.ok(!first.sourceText.marks.some(mk => mk.key === 'types[0]'), 'a value spanning the whole object marks nothing');
});

test('the shared card draws one visible chain button per value under the row that names its key', async () => {
  const RecordCard = recordCard();
  const { P, out } = await models();
  for (const { object, rows, m } of out.values()) {
    const html = RecordCard.card(m);
    const buttons = chainButtons(html);
    const chains = P.chainRows(m);
    const panels = ids(html);
    assert.strictEqual(buttons.length, rows.length, `${object.id}: one button per value`);
    assert.deepStrictEqual(markersWithoutButton(html), [], `${object.id}: no marker without its button`);
    for (const b of buttons) {
      const hit = chains.get(b.controls);
      assert.ok(hit, `${object.id}: ${b.controls} belongs to a value`);
      assert.strictEqual(b.key, hit.r.key);
      assert.ok(panels.has(b.controls));
      assert.ok(b.word, 'the producer word is visible');
      const steps = visibleText(RecordCard.chain(m, hit.r, hit.i));
      for (const step of STEPS) assert.ok(steps.includes(step), `${object.id}: ${step}`);
      assert.ok(RecordCard.passage(m, hit.r.values[hit.i]).located, 'the passage is located, never a first match');
    }
    assert.deepStrictEqual([...html.matchAll(/data-region="([^"]+)"/g)].map(x => x[1]), ['head', 'values', 'source']);
  }
});

test('every string of the print data is escaped before it reaches the card', async () => {
  const RecordCard = recordCard();
  const { out } = await models();
  const m = out.get('X/Z/2#1').m;
  const html = RecordCard.card(m);
  assert.ok(!html.includes('<Invented>') && !html.includes('<Elsewhere>'), 'no markup from the data');
  assert.ok(html.includes('Second &lt;Invented&gt; &amp; Title'), 'the title, escaped by the card');
  const place = m.groups[0].rows.find(r => r.key === 'imprints').values[0];
  assert.strictEqual(place.html, '&lt;Elsewhere&gt;', 'a value row, escaped by the adapter');
});

test('the visible predicate refuses hidden markers and lends no key from a wrapper', () => {
  const hidden = '<div data-provenance-for="a" hidden><button class="prov-badge" aria-controls="c1">rule</button></div>';
  assert.deepStrictEqual(chainButtons(hidden), []);
  assert.deepStrictEqual(markersWithoutButton('<span data-provenance-for="b"></span>'), ['b']);
  const nested = '<section data-provenance-for="outer"><div data-provenance-for="inner"><button class="prov-badge" aria-controls="c2">rule</button></div></section>';
  assert.deepStrictEqual(chainButtons(nested).map(b => b.key), ['inner']);
  const wrapped = '<section data-provenance-for="outer"><div><button class="prov-badge" aria-controls="c3">rule</button></div><div data-provenance-for="row"></div></section>';
  assert.deepStrictEqual(chainButtons(wrapped).map(b => b.key), ['outer']);
  assert.deepStrictEqual(markersWithoutButton(wrapped), ['row']);
});

test('load, list and model read the review server once, chunks by their own address', async () => {
  const P = await load('records-print.js');
  P.reset();
  const origin = 'http://invented.test';
  const asked = [];
  const answer = body => ({ ok: true, status: 200, json: async () => JSON.parse(JSON.stringify(body)) });
  const served = {
    [`${origin}/viewer/index.json`]: INDEX,
    [`${origin}/viewer/vocab.json`]: { roles: [], types: [], languages: [], missingFields: [] },
    [`${origin}/viewer/wiki_concordance.json`]: CONCORDANCE,
    [`${origin}/jsonld/X/Z-1.jsonld`]: FIXTURE,
  };
  const get = async url => {
    asked.push(String(url));
    return served[String(url)] ? answer(served[String(url)]) : { ok: false, status: 404, json: async () => ({}) };
  };
  assert.throws(() => P.list(), /load\(\) first/);
  assert.deepStrictEqual(await P.load({ origin, fetch: get }), { objects: 4 });
  await P.load({ origin, fetch: get });
  assert.strictEqual(asked.length, 3, 'the index, vocabulary and concordance load once');
  assert.deepStrictEqual(P.list({ q: 'Sequel' }).map(s => s.id), ['X/Z/1#2']);
  assert.deepStrictEqual(P.list({ review: 'sample' }).map(s => s.id), ['X/Z/1#1']);
  assert.deepStrictEqual(P.list({ wiki: 'text' }).map(s => s.id), ['X/Z/1#1']);
  assert.deepStrictEqual(P.list({ part: 'Index A' }).map(s => s.id), ['X/index/1#1']);
  const slip = P.list({ q: 'invented title' })[0];
  assert.deepStrictEqual([slip.sourceSign.label, slip.sourceSign.pdfPage, slip.relation.state, slip.review.state], ['Main volume', 7, 'proposed', 'open']);
  const m = await P.model('X/Z/1#2');
  assert.strictEqual(m.title, 'Invented Sequel');
  await P.model('X/Z/2#1');
  assert.strictEqual(asked.filter(u => u.endsWith('Z-1.jsonld')).length, 1, 'a chunk loads once');
  assert.strictEqual(await P.model('X/Z/9#1'), null);
  P.reset();
  await assert.rejects(P.load({ origin: 'http://elsewhere.test', fetch: get }), /index\.json: 404/);
  P.reset();
});

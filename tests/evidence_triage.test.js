/**
 * Runnable check for the edit-layer logic added in increments 2 and 3:
 * evidence-span matching (Edit._findValueSpan / _findPageCountSpan /
 * _snippetAround / evidence) and triage-hint bundling and ordering
 * (Edit.triageHints / triageRank).
 *
 * docs/js/edit.js is loaded into a bare VM context with a stubbed App, so
 * this pins the logic without a browser. Run directly (node
 * tests/evidence_triage.test.js) or via pytest (tests/test_frontend_logic.py).
 */
'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const src = fs.readFileSync(path.join(__dirname, '..', 'docs', 'js', 'edit.js'), 'utf8');

function makeContext(entries, pendingEdits) {
  const context = {
    App: {
      state: { editMode: true, pendingEdits: pendingEdits || {} },
      entryMap: new Map((entries || []).map(e => [e.sourcePageId, e])),
    },
    esc: s => String(s),
    console,
  };
  vm.createContext(context);
  vm.runInContext(src + '\n;this.Edit = Edit;', context);
  return context;
}

let failures = 0;
function test(name, fn) {
  try {
    fn();
    console.log(`ok   ${name}`);
  } catch (err) {
    failures++;
    console.error(`FAIL ${name}\n     ${err.message}`);
  }
}

const { Edit } = makeContext();

// --- _findValueSpan ---

test('finds exact value', () => {
  const s = Edit._findValueSpan('Published by Insel-Verlag, Leipzig.', 'Insel-Verlag');
  assert.ok(s);
  assert.strictEqual(s.index, 13);
  assert.strictEqual(s.count, 1);
});

test('is case-insensitive and whitespace-tolerant across newlines', () => {
  const s = Edit._findValueSpan('by INSEL-\n  verlag Leipzig', 'Insel- Verlag');
  assert.ok(s);
  assert.strictEqual(s.index, 3);
});

test('escapes regex metacharacters in the value', () => {
  const s = Edit._findValueSpan('S. Fischer (Verlag) [1946]', 'S. Fischer (Verlag)');
  assert.ok(s);
  assert.strictEqual(s.index, 0);
});

test('counts multiple occurrences (multi-edition ambiguity)', () => {
  const s = Edit._findValueSpan('Leipzig ... later also Leipzig', 'Leipzig');
  assert.ok(s);
  assert.strictEqual(s.count, 2);
});

test('returns null when value absent or empty', () => {
  assert.strictEqual(Edit._findValueSpan('some text', 'Weimar'), null);
  assert.strictEqual(Edit._findValueSpan('some text', ''), null);
  assert.strictEqual(Edit._findValueSpan('', 'Weimar'), null);
});

// --- _findPageCountSpan ---

test('matches a digit-bounded literal page count', () => {
  const s = Edit._findPageCountSpan('Dedication 1922. 295/(2)p. edition', 295);
  assert.ok(s);
  // must not match inside "1922"
  assert.strictEqual(s.index, 17);
});

test('does not match the number inside a longer number', () => {
  assert.strictEqual(Edit._findPageCountSpan('printed 1295 copies', 295), null);
});

test('accepts the N/(M)p. summation like verify.py', () => {
  const s = Edit._findPageCountSpan('A new edition. 285/(3)p. [series]', 288);
  assert.ok(s);
  assert.strictEqual(s.match === undefined, true); // span, not snippet
});

test('accepts pp. X-Y ranges like verify.py', () => {
  const s = Edit._findPageCountSpan('Der Amokläufer, pp. (9)-86', 78);
  assert.ok(s);
});

test('returns null when no page-count evidence exists', () => {
  assert.strictEqual(Edit._findPageCountSpan('no numbers here', 100), null);
});

// --- _snippetAround ---

test('snippet carries ellipses and the exact match', () => {
  const text = 'word '.repeat(30) + 'Insel-Verlag' + ' tail'.repeat(30);
  const span = Edit._findValueSpan(text, 'Insel-Verlag');
  const snip = Edit._snippetAround(text, span);
  assert.strictEqual(snip.match, 'Insel-Verlag');
  assert.ok(snip.before.startsWith('…'));
  assert.ok(snip.after.endsWith('…'));
});

test('snippet has no ellipses when the whole text fits', () => {
  const text = 'Published by Insel-Verlag, Leipzig.';
  const snip = Edit._snippetAround(text, Edit._findValueSpan(text, 'Insel-Verlag'));
  assert.strictEqual(snip.before, 'Published by ');
  assert.strictEqual(snip.after, ', Leipzig.');
});

// --- evidence (field-level entry point) ---

test('evidence falls back to the triage-detected raw value for a missing field', () => {
  const entry = {
    sourcePageId: 7,
    translator: null,
    fullBibliographicEntry: 'Übers. von Felix Braun. Wien 1927.',
  };
  const ctx = makeContext([entry]);
  ctx.Edit.triage = { '7': { detectable: { translator: 'Felix Braun' } } };
  const ev = ctx.Edit.evidence(entry, 'translator');
  assert.ok(ev);
  assert.strictEqual(ev.match, 'Felix Braun');
});

test('evidence returns null when nothing is locatable (fallback = full source)', () => {
  const entry = { sourcePageId: 8, publisher: 'Phantom', fullBibliographicEntry: 'no such name here' };
  const ctx = makeContext([entry]);
  assert.strictEqual(ctx.Edit.evidence(entry, 'publisher'), null);
});

// --- triageHints ordering and suppression ---

function hintEntry() {
  return {
    sourcePageId: 42,
    publisher: 'X', location: 'Y', translator: null, pageCount: null,
    _provenance: { publisher: 'llm', location: 'regex', translator: 'missing', pageCount: 'missing' },
    fullBibliographicEntry: 'text',
  };
}

test('hints are ordered by signal class: verify flags before provenance classes', () => {
  const entry = hintEntry();
  const ctx = makeContext([entry]);
  ctx.Edit.triage = { '42': {
    notInSource: ['location'],
    detectable: { translator: 'Felix Braun' },
  } };
  const hints = ctx.Edit.triageHints(entry);
  assert.strictEqual(JSON.stringify(hints.map(h => h.rank)), '[1,2,3,4]');
  assert.strictEqual(JSON.stringify(hints.map(h => h.field)),
    JSON.stringify(['location', 'translator', 'publisher', 'pageCount']));
});

test('census anomaly ranks first', () => {
  const entry = hintEntry();
  const ctx = makeContext([entry]);
  ctx.Edit.triage = { '42': { census: 'Quellseitig geleerte Seite', notInSource: ['location'] } };
  const hints = ctx.Edit.triageHints(entry);
  assert.strictEqual(hints[0].rank, 0);
  assert.strictEqual(hints[0].field, null);
});

test('a pending editor action suppresses that field\'s hints', () => {
  const entry = hintEntry();
  const pending = { 42: { location: { action: 'correct' }, publisher: { action: 'accept' } } };
  const ctx = makeContext([entry], pending);
  ctx.Edit.triage = { '42': { notInSource: ['location'] } };
  const fields = ctx.Edit.triageHints(entry).map(h => h.field);
  assert.ok(!fields.includes('location'));
  assert.ok(!fields.includes('publisher'));
});

test('editor provenance suppresses that field\'s hints', () => {
  const entry = hintEntry();
  entry._provenance.publisher = 'editor';
  const ctx = makeContext([entry]);
  const fields = ctx.Edit.triageHints(entry).map(h => h.field);
  assert.ok(!fields.includes('publisher'));
});

test('an approved (human-verified) entry carries no hints', () => {
  const entry = hintEntry();
  entry.review = { status: 'approved' };
  const ctx = makeContext([entry]);
  ctx.Edit.triage = { '42': { notInSource: ['location'] } };
  assert.strictEqual(ctx.Edit.triageHints(entry).length, 0);
});

test('triageRank: most urgent class present; 9 when clean', () => {
  const entry = hintEntry();
  const clean = { sourcePageId: 43, _provenance: { publisher: 'regex', location: 'regex', translator: 'regex', pageCount: 'regex' } };
  const ctx = makeContext([entry, clean]);
  ctx.Edit.triage = { '42': { notInSource: ['location'] } };
  assert.strictEqual(ctx.Edit.triageRank(42), 1);
  assert.strictEqual(ctx.Edit.triageRank(43), 9);
});

if (failures) {
  console.error(`\n${failures} failure(s)`);
  process.exit(1);
}
console.log('\nall checks passed');

/**
 * Pins the session-state contract of the EIL edit layer and the read-layout
 * promises that go with it (docs/js/edit.js, docs/js/detail.js):
 *
 * - a pending correction is what the editable field shows, with the dataset
 *   value beside it as the superseded one;
 * - an unsaved field action makes the entry "edited", never "approved", which
 *   stays reserved for the dataset review projection;
 * - the read layout carries the review chip and opens the source when the
 *   source is all the expansion has;
 * - a category link filters by that category, not by the entry type;
 * - the contested-claim index answers the same question the former linear
 *   scan did.
 */
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function read(file) {
  return fs.readFileSync(path.join(__dirname, '..', 'docs', 'js', file), 'utf8');
}

/** Load modules into one shared realm, as the browser's global scope does. */
function load(files, extra = {}) {
  const ctx = Object.assign({ console }, extra);
  vm.createContext(ctx);
  for (const file of files) vm.runInContext(read(file), ctx);
  return ctx;
}

function detailCtx(entry, pendingEdits = {}) {
  const ctx = load(['constants.js', 'utils.js', 'detail.js'], {
    App: {
      state: { editMode: true, pendingEdits },
      entries: [entry],
      entryMap: new Map([[entry.sourcePageId, entry]]),
      titleMap: new Map(),
      data: { redirects: {} },
    },
    Edit: {
      FIELD_LABELS: { publisher: 'Publisher', location: 'Location' },
      pending: (pid, field) => (pendingEdits[pid] || {})[field],
      entryStatus: pid => (pendingEdits[pid] && Object.keys(pendingEdits[pid]).length
        ? { status: 'edited', pending: true }
        : { status: 'unreviewed', pending: false }),
      triageHints: () => [],
      evidence: () => null,
      editionClaimsFor: () => [],
      authorityClaimsFor: () => [],
      locationReconciliation: () => null,
      agentReconciliation: () => null,
    },
  });
  return vm.runInContext('Detail', ctx);
}

test('a pending correction is rendered, with the replaced value beside it', () => {
  const entry = { sourcePageId: 7, title: 'T', publisher: 'Insel' };
  const pending = { 7: { publisher: { action: 'correct', oldValue: 'Insel', newValue: 'Insel-Verlag' } } };
  const html = detailCtx(entry, pending)._editableValue('publisher', entry);
  assert.match(html, />Insel-Verlag</, 'the corrected value is what the field shows');
  assert.match(html, /field-superseded[^>]*>Insel</, 'the replaced value stays visible');
  assert.match(html, /data-original="Insel"/, 'the classification key stays the dataset value');
  assert.match(html, /role="textbox"/);
  assert.match(html, /aria-label="Publisher"/);
});

test('an empty field offers an explicit Add control, not only a placeholder', () => {
  const entry = { sourcePageId: 7, title: 'T' };
  const html = detailCtx(entry)._editableValue('location', entry);
  assert.match(html, /data-act="add-focus"/);
  assert.match(html, /\+ Add Location/);
});

test('an unsaved edit reads as Edited, never as Expert-reviewed', () => {
  const entry = { sourcePageId: 7, title: 'T', publisher: 'Insel' };
  const pending = { 7: { publisher: { action: 'accept', oldValue: 'Insel', newValue: 'Insel' } } };
  const html = detailCtx(entry, pending)._reviewChip(entry);
  assert.match(html, /review-edited/);
  assert.match(html, />Edited/);
  assert.doesNotMatch(html, /Expert-reviewed/);
});

test('Edit.entryStatus reserves approved for the dataset projection', () => {
  const ctx = load(['edit.js'], { App: { state: { pendingEdits: { 7: { publisher: {} } } } } });
  const Edit = vm.runInContext('Edit', ctx);
  // JSON comparison: objects from a vm realm fail deepStrictEqual's identity check.
  assert.strictEqual(JSON.stringify(Edit.entryStatus(7)), '{"status":"edited","pending":true}');
  assert.strictEqual(JSON.stringify(Edit.entryStatus(8)), '{"status":"unreviewed","pending":false}');
});

test('a load failure is held in state instead of degrading to an empty dataset', () => {
  const ctx = load(['edit.js'], { App: { state: { pendingEdits: {} } } });
  const Edit = vm.runInContext('Edit', ctx);
  assert.strictEqual(Edit.triageFailed, false);
  assert.strictEqual(Edit.reconciliationFailed, false);
});

test('the contested-claim index answers what the linear scan answered', () => {
  const ctx = load(['edit.js'], { App: { state: { pendingEdits: {} } } });
  const Edit = vm.runInContext('Edit', ctx);
  const byName = { claimId: 'c1', subject: { name: 'Varna' }, sourceEvidence: [] };
  const byPage = { claimId: 'c2', subject: { name: 'Sofia' }, sourceEvidence: [{ sourcePageId: '299' }] };
  const both = { claimId: 'c3', subject: { name: 'Varna' }, sourceEvidence: [{ sourcePageId: 299 }] };
  Edit.contestedAuthorityClaims = [byName, byPage, both];
  const ids = Edit.authorityClaimsFor({ sourcePageId: 299, location: 'Varna' })
    .map(c => c.claimId).sort();
  assert.strictEqual(ids.join(','), 'c1,c2,c3', 'no claim is lost and none is duplicated');
  assert.strictEqual(
    Edit.authorityClaimsFor({ sourcePageId: 1, location: 'Wien' }).length, 0
  );
});

test('a category link filters by the category, not by the entry type', () => {
  const entry = {
    sourcePageId: 7, title: 'T', entryType: 'fiction',
    categories: ['Fiction / Volumes (French)'],
  };
  const html = detailCtx(entry)._buildEditContent(entry);
  assert.match(html, /href="#category=Fiction%20%2F%20Volumes%20\(French\)"/);
  assert.doesNotMatch(html, /href="#type=/);
});

test('the read layout carries the review chip and opens a lone source', () => {
  const entry = { sourcePageId: 7, title: 'T', fullBibliographicEntry: 'Klawiter raw text.' };
  const html = detailCtx(entry)._buildReadContent(entry);
  assert.match(html, /review-chip/);
  assert.match(html, /<details class="detail-source-details" open>/);
});

test('a read layout with further sections leaves the source collapsed', () => {
  const entry = {
    sourcePageId: 7, title: 'T', translator: 'Alzir Hella',
    fullBibliographicEntry: 'Klawiter raw text.',
  };
  const html = detailCtx(entry)._buildReadContent(entry);
  assert.match(html, /<details class="detail-source-details">/);
});

test('the playground resolves an entry from the playground route', () => {
  const entry = { sourcePageId: 42, title: 'Schachnovelle' };
  const ctx = load(['constants.js', 'jsonld-playground.js'], {
    App: { entryMap: new Map([[42, entry]]), entries: [entry] },
    location: { hash: '#data/playground/42' },
    document: { getElementById: () => null, addEventListener() {}, querySelectorAll: () => [] },
  });
  const P = vm.runInContext('JsonldPlayground', ctx);
  assert.strictEqual(P._entryFromHash(), entry);
  ctx.location.hash = '#data/playground';
  assert.strictEqual(P._entryFromHash(), null);
  ctx.location.hash = '#data';
  assert.strictEqual(P._entryFromHash(), null);
  ctx.location.hash = '#data/playground/999';
  assert.strictEqual(P._entryFromHash(), null);
});

test('the playground reads the entry-type list from the shared constant', () => {
  const ctx = load(['constants.js', 'jsonld-playground.js'], {
    App: { entries: [] },
    location: { hash: '' },
    document: { getElementById: () => null, addEventListener() {}, querySelectorAll: () => [] },
  });
  const P = vm.runInContext('JsonldPlayground', ctx);
  assert.strictEqual(P.ABOUT_ZWEIG_TYPES, undefined, 'no second copy of the list');
  assert.ok(!('author' in P._toCompactJsonld({ entryType: 'secondary-literature' })));
  assert.ok('author' in P._toCompactJsonld({ entryType: 'fiction' }));
});

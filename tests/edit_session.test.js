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

test('a claim reaches a page through the value it names or the text that carries it', () => {
  const ctx = load(['edit.js'], { App: { state: { pendingEdits: {} } } });
  const Edit = vm.runInContext('Edit', ctx);
  const byName = { claimId: 'c1', subject: { name: 'Varna' }, sourceEvidence: [] };
  const byPage = { claimId: 'c2', subject: { name: 'Sofia' }, sourceEvidence: [{ sourcePageId: '299' }] };
  const both = { claimId: 'c3', subject: { name: 'Varna' }, sourceEvidence: [{ sourcePageId: 299 }] };
  const compound = { claimId: 'c4', subject: { name: 'Sofija, Varna' },
    sourceEvidence: [{ sourcePageId: 299 }] };
  Edit.contestedAuthorityClaims = [byName, byPage, both, compound];
  const page = { sourcePageId: 299, location: 'Varna', fullBibliographicEntry: 'Sofia, 1950' };
  const ids = Edit.authorityClaimsFor(page).map(c => c.claimId).sort();
  assert.strictEqual(ids.join(','), 'c1,c2,c3', 'no claim is lost and none is duplicated');
  // An evidence page whose text does not carry the subject is not reached.
  assert.strictEqual(Edit.authorityClaimsFor({ ...page, fullBibliographicEntry: '' })
    .map(c => c.claimId).sort().join(','), 'c1,c3');
  assert.strictEqual(
    Edit.authorityClaimsFor({ sourcePageId: 1, location: 'Wien' }).length, 0
  );
  // A place of a publication counts like the flat place.
  assert.strictEqual(Edit.authorityClaimsFor({ sourcePageId: 1, location: 'Wien',
    publicationPlaces: ['Wien', 'Varna'] }).length, 2);
  // The value a claim contests is the one its subject names word for word.
  assert.strictEqual(Edit.openClaimOnValue(page, 'Varna').claimId, 'c1');
  assert.strictEqual(Edit.openClaimOnValue(page, 'Sofija'), null);
  byName.decisionStatus = 'decided';
  assert.strictEqual(Edit.openClaimOnValue(page, 'Varna').claimId, 'c3');
});

test('a decided claim stays readable where it applies and contests no value', () => {
  // Pages 1725 and 1799 print "Nauka i izkustvo, Sofija / DPK St.
  // Dobrev-Strandzhata, Varna"; the decided compound claim names that line.
  const ctx = load(['edit.js'], { App: { state: { pendingEdits: {} } } });
  const Edit = vm.runInContext('Edit', ctx);
  const decided = { claimId: 'd', entityType: 'location', decisionStatus: 'decided',
    subject: { name: 'Sofija, Varna' },
    sourceEvidence: [{ sourcePageId: 1725,
      sourceText: "'''[1966]: Nauka i izkustvo, Sofija / DPK St. Dobrev-Strandzhata, Varna'''" }] };
  const withheld = { claimId: 's', entityType: 'source-revision', decisionStatus: 'open',
    subject: { '@id': 'klawiter:entry/670', name: 'Le chandelier enterré' },
    sourceEvidence: [{ sourcePageId: 1725, sourceText: '#REDIRECT [[Der begrabene Leuchter]]' }] };
  Edit.contestedAuthorityClaims = [withheld];
  Edit.decidedAuthorityClaims = [decided];
  const page = { sourcePageId: 1725, location: 'Sofija', publicationPlaces: ['Sofija', 'Varna'],
    fullBibliographicEntry: '[1966]: Nauka i izkustvo, Sofija / DPK St. Dobrev-Strandzhata, Varna\n' };
  assert.strictEqual(Edit.authorityClaimsFor(page).map(c => c.claimId).join(','), 'd');
  assert.strictEqual(Edit.openClaimOnValue(page, 'Sofija'), null);
  // Without the evidence line in its text the page is not reached.
  assert.strictEqual(Edit.authorityClaimsFor({ ...page, fullBibliographicEntry: 'Sofija' }).length, 0);
  // A withheld redirect is found by its page or its title, never by a place.
  assert.strictEqual(Edit.sourceRevisionClaim(670), withheld);
  assert.strictEqual(Edit.sourceRevisionClaim(null, 'Le chandelier enterré'), withheld);
  assert.strictEqual(Edit.sourceRevisionClaim(35, 'Maria Stuart'), null);
});

test('edit mode marks a candidate the recorded decision rejected', () => {
  // Yanji: the matcher proposed Q956 (Beijing), the review corrected it to
  // Q713362 and named Q956 as rejected.
  const entry = { sourcePageId: 363, title: 'Ciweige jingdian xiaoshuo', location: 'Yanji' };
  const review = {
    candidates: [
      { qid: 'Q956', label: 'Beijing', uri: 'http://www.wikidata.org/entity/Q956', score: 83 },
      { qid: 'Q713362', label: 'Yanji', uri: 'http://www.wikidata.org/entity/Q713362' },
    ],
    decision: { action: 'correct', qid: 'Q713362', rejectedQid: 'Q956' },
    publishable: null,
  };
  const ctx = load(['constants.js', 'utils.js', 'detail.js'], {
    App: { state: { editMode: true, pendingEdits: {} }, entries: [entry],
      entryMap: new Map([[363, entry]]), titleMap: new Map(), data: { redirects: {} } },
    Edit: { locationReconciliation: () => review, pendingLocationDecision: () => undefined },
  });
  const html = vm.runInContext('Detail', ctx)._authorityCell(entry, 'location');
  const beijing = html.slice(html.indexOf('Beijing'), html.indexOf('</li>', html.indexOf('Beijing')));
  assert.match(beijing, /candidate-rejected[^>]*>rejected</);
  assert.match(beijing, />Confirm instead</);
  const yanji = html.slice(html.indexOf('Yanji (Q713362)'));
  assert.match(yanji, /candidate-accepted[^>]*>accepted</);
});

test('edit mode keeps the publications and scopes the table to the page record', () => {
  const entry = {
    sourcePageId: 1800, title: 'Romanŭt na edin zhivot. Balzak',
    publisher: 'Pechat Far', location: 'Sofija', pageCount: 500,
    pageKind: 'edition-page', publicationCount: 2,
    publications: [
      { id: 'a', year: 1947, publisher: 'Pechat Far', places: ['Sofija'],
        editionStatement: '1st edition', provenance: {} },
      { id: 'b', year: 1960, publisher: 'Narodna Kultura', places: ['Sofija'],
        editionStatement: '2nd revised edition', provenance: {} },
    ],
  };
  const html = detailCtx(entry)._buildEditContent(entry);

  // Both imprints stay readable, so an accepted page value is never read as
  // a decision about the publication the card no longer shows.
  assert.match(html, /1947 · 1st edition/);
  assert.match(html, /1960 · 2nd revised edition/);
  assert.match(html, />Narodna Kultura</);
  assert.match(html, />Page record</);
  assert.match(html, /page with 2 publications/);
  // Editing happens in the page record alone; the publication blocks above it
  // carry no editable cell.
  const record = html.slice(html.indexOf('page-record'));
  assert.strictEqual((html.match(/contenteditable/g) || []).length,
    (record.match(/contenteditable/g) || []).length);
  assert.match(record, /Publisher[\s\S]*?contenteditable/);
  // Every editable row says what an edit here applies to.
  assert.match(html, /title="[^"]*applies to the page record[^"]*"/);
});

test('a page without publications keeps the page record as its only table', () => {
  const entry = { sourcePageId: 7, title: 'T', publisher: 'Insel', location: 'Leipzig' };
  const html = detailCtx(entry)._buildEditContent(entry);
  assert.match(html, />Page record</);
  assert.doesNotMatch(html, /publication-heading/);
  assert.doesNotMatch(html, /page with/, 'a scope line without several publications says nothing');
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

// The review state moved into the card head, where it stands beside type and
// page kind; tests/entry_card.test.js pins it there.
test('the read layout opens a lone source', () => {
  const entry = { sourcePageId: 7, title: 'T', fullBibliographicEntry: 'Klawiter raw text.' };
  const html = detailCtx(entry)._buildReadContent(entry);
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

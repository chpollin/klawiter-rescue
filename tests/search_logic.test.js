/**
 * Pins the search behaviour of the results view.
 *
 * Diacritics: the corpus is full of transliterations, so an index without a
 * folding charset answers "Zoscenko" with nothing while "Zoščenko" is right
 * there. Highlighting: marking has to run on the raw title and escaping on the
 * segments, or a query with an apostrophe never matches and a query like "amp"
 * cuts an entity in half. Facet counting: a facet counts against the other
 * filters, never against its own, or its alternatives vanish on selection.
 */
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const DOCS = path.join(__dirname, '..', 'docs');
const FlexSearch = require(path.join(DOCS, 'vendor', 'flexsearch.bundle.min.js'));

function loadUtils(name) {
  const ctx = { console };
  vm.createContext(ctx);
  for (const file of ['constants.js', 'utils.js']) {
    vm.runInContext(fs.readFileSync(path.join(DOCS, 'js', file), 'utf8'), ctx);
  }
  return vm.runInContext(name, ctx);
}

function loadApp() {
  const location = { hash: '', pathname: '/', hostname: 'localhost' };
  const ctx = {
    window: { location, addEventListener() {} },
    document: { addEventListener() {}, getElementById() { return null; } },
    location,
    history: { replaceState() {}, pushState() {} },
    URLSearchParams,
    FlexSearch,
    console,
  };
  vm.createContext(ctx);
  // Plain scripts sharing one global scope: app.js reads the label tables of
  // constants.js and the helpers of utils.js.
  for (const file of ['constants.js', 'utils.js']) {
    vm.runInContext(fs.readFileSync(path.join(DOCS, 'js', file), 'utf8'), ctx);
  }
  const source = fs.readFileSync(path.join(DOCS, 'js', 'app.js'), 'utf8');
  return vm.runInContext(source + '\nApp', ctx);
}

const SAMPLE = [
  { sourcePageId: 1, title: 'Zoščenko, Mixail', entryType: 'fiction', language: 'Russian' },
  { sourcePageId: 2, title: "L'amour de la vie", entryType: 'fiction', language: 'French' },
  { sourcePageId: 3, title: 'Marie Antoinette', entryType: 'essay', language: 'German' },
  { sourcePageId: 4, title: 'Sternstunden', entryType: 'essay', language: 'French' },
];

test('the index folds diacritics, so a plain spelling finds the transliteration', () => {
  const App = loadApp();
  App.entries = SAMPLE;
  App.buildIndex();
  assert.strictEqual(JSON.stringify(App.index.search('Zoscenko')), '[0]');
  // The exact spelling keeps working, and an unrelated word still misses.
  assert.strictEqual(JSON.stringify(App.index.search('Zoščenko')), '[0]');
  assert.strictEqual(JSON.stringify(App.index.search('Hamburg')), '[]');
});

test('highlighting marks the raw text and escapes the segments', () => {
  const hlEsc = loadUtils('hlEsc');

  // An apostrophe in the query used to be compared against &#39; and never hit.
  assert.strictEqual(hlEsc("L'amour", "l'amour"), "<mark>L&#39;amour</mark>");

  // "amp" must not find the escaping of "&" and tear the entity apart.
  assert.strictEqual(hlEsc('Fischer & Co.', 'amp'), 'Fischer &amp; Co.');
  assert.strictEqual(hlEsc('Fischer & Co.', 'fischer'), '<mark>Fischer</mark> &amp; Co.');

  // Angle brackets stay escaped inside and outside a mark.
  assert.strictEqual(hlEsc('<b>Zweig</b>', 'zweig'),
    '&lt;b&gt;<mark>Zweig</mark>&lt;/b&gt;');

  // No query, single-letter words and empty text: escape only.
  assert.strictEqual(hlEsc('Fischer & Co.', ''), 'Fischer &amp; Co.');
  assert.strictEqual(hlEsc('Fischer & Co.', 'a'), 'Fischer &amp; Co.');
  assert.strictEqual(hlEsc(null, 'zweig'), '');
});

test('a query below the minimum length runs no search', () => {
  const App = loadApp();
  App.entries = SAMPLE;
  App.state.query = 'z';
  assert.strictEqual(App._queryBase().length, SAMPLE.length);
  assert.strictEqual(App.index, null, 'no index built for a one-character query');

  App.state.query = 'zweig';
  App._queryBase();
  assert.ok(App.index, 'a real query builds the index');
});

test('a facet counts against the other filters, not against its own', () => {
  const App = loadApp();
  App.entries = SAMPLE;
  App.state.query = '';
  App.state.filters = { type: 'fiction' };
  App._filterBase = SAMPLE;

  // Type: counted without the type filter, so both types stay selectable.
  const types = new Set(App.facetCandidates('type').map(e => e.entryType));
  assert.strictEqual(types.size, 2);

  // Language: counted with the type filter applied, so it drills down.
  const langs = App.facetCandidates('language').map(e => e.language).sort();
  assert.strictEqual(JSON.stringify(langs), JSON.stringify(['French', 'Russian']));
});

test('the result label resolves the same labels the chips do', () => {
  const App = loadApp();
  App.state.query = '';
  App.state.filters = { type: 'fiction', period: 'lifetime', category: 'Fiction / Volumes' };
  App._searchCapped = false;

  const label = App._resultsLabel(3);
  assert.ok(label.includes('Fiction'), label);
  // The period used to reach the label as its raw key while the chip showed
  // the readable name.
  assert.ok(label.includes('Lifetime (1881–1942)'), label);
  // The category was missing from the label entirely.
  assert.ok(label.includes('Fiction / Volumes'), label);
  assert.ok(label.endsWith('3 results'), label);

  // A capped search says so instead of reading as a complete count.
  App._searchCapped = true;
  assert.ok(App._resultsLabel(5000).includes('first 5,000 matches'));
});

test('the clear-all chip appears only from the second active filter on', () => {
  const App = loadApp();
  App.state.query = '';
  App.state.filters = { type: 'fiction' };
  assert.strictEqual(App._activeFilters().length, 1);

  App.state.query = 'zweig';
  assert.strictEqual(App._activeFilters().length, 2);

  // A decade supersedes a stale range, matching yearBounds, so the two never
  // show up as two separate filters.
  App.state.query = '';
  App.state.filters = { decade: '1930', years: '1900-1910' };
  assert.strictEqual(JSON.stringify(App._activeFilters().map(f => f.key)), '["decade"]');
});

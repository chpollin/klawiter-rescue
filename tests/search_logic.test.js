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

/** App plus the facet sidebar, which counts through App's axis values. */
function loadFacets() {
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
  for (const file of ['constants.js', 'utils.js', 'app.js', 'facets.js']) {
    vm.runInContext(fs.readFileSync(path.join(DOCS, 'js', file), 'utf8'), ctx);
  }
  return vm.runInContext('({ App, Facets })', ctx);
}

// Two real pages of the holding whose publications disagree with the flat
// fields: page 1800 has a 1947 and a 1960 edition, page 4445 a German book of
// 2000 and an Arabic article of 2015 published in Rabat.
const PUBLICATION_PAGES = [
  { sourcePageId: 1800, entryType: 'historical-study',
    title: 'Romanŭt na edin zhivot. Balzak',
    year: 1947, language: 'Bulgarian', location: 'Sofija', timePeriod: 'post-wwii',
    pageKind: 'edition-page', publicationCount: 2,
    publicationYears: [1947, 1960], publicationLanguages: ['Bulgarian'],
    publicationPlaces: ['Sofija'] },
  { sourcePageId: 4445, entryType: 'secondary-literature',
    title: 'Al-Bāḥ, Muḥammad / El-bah, Mohammed',
    year: 2000, language: 'Arabic', location: 'Freiburg', timePeriod: 'late-20c',
    pageKind: 'author-page', publicationCount: 2,
    publicationYears: [2000, 2015], publicationLanguages: ['German', 'Arabic'],
    publicationPlaces: ['Freiburg im Breisgau', 'Rabat'] },
];

test('a page belongs to every year, language and place of its publications', () => {
  const { App, Facets } = loadFacets();
  const keep = (entry, filters) => App._matchesFilters(entry, filters, App.yearBounds(filters));
  const [editionPage, authorPage] = PUBLICATION_PAGES;

  // The 1960 edition of page 1800 is a publication of that page; the flat year
  // names its first edition alone, so the page used to be missing here.
  assert.strictEqual(keep(editionPage, { years: '1960-1960' }), true);
  assert.strictEqual(keep(authorPage, { years: '1960-1960' }), false);
  // A page carrying a German and an Arabic publication is under both.
  assert.strictEqual(keep(authorPage, { language: 'German' }), true);
  assert.strictEqual(keep(authorPage, { language: 'Arabic' }), true);
  assert.strictEqual(keep(editionPage, { language: 'German' }), false);
  // The place of the article's container is a place of the page.
  assert.strictEqual(keep(authorPage, { location: 'Rabat' }), true);
  assert.strictEqual(keep(authorPage, { location: 'Freiburg' }), false);
  // Two publication years, two periods.
  assert.strictEqual(keep(authorPage, { period: 'late-20c' }), true);
  assert.strictEqual(keep(authorPage, { period: 'contemporary' }), true);
  assert.strictEqual(keep(editionPage, { period: 'post-wwii' }), true);
  // A range spanning neither year is not met by one year above and one below.
  assert.strictEqual(keep(authorPage, { years: '2005-2010' }), false);

  // The facet counts what the filter selects, value by value.
  for (const [filterKey, field] of [['language', 'language'], ['location', 'location'],
    ['period', 'timePeriod']]) {
    const counts = Facets._counts(PUBLICATION_PAGES, field, filterKey);
    for (const [value, count] of Object.entries(counts)) {
      assert.strictEqual(
        App._applyFilterSet(PUBLICATION_PAGES, { [filterKey]: value }).length, count,
        `${filterKey}=${value}`);
    }
  }
  const languages = Facets._counts(PUBLICATION_PAGES, 'language', 'language');
  assert.strictEqual(languages.German, 1);
  assert.strictEqual(languages.Arabic, 1);
  assert.strictEqual(languages.Bulgarian, 1);
  const places = Facets._counts(PUBLICATION_PAGES, 'location', 'location');
  assert.strictEqual(places.Rabat, 1);
  assert.strictEqual(places['Freiburg im Breisgau'], 1);
  assert.strictEqual(places.Freiburg, undefined, 'the flat place gives way to the layer');
});

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

  // The label is the heading of the view: the count first, then what was
  // asked for. A filtered set counts entries, a query counts results.
  const label = App._resultsLabel(3);
  assert.ok(label.startsWith('3 entries · '), label);
  assert.ok(label.includes('Fiction'), label);
  // The period used to reach the label as its raw key while the chip showed
  // the readable name.
  assert.ok(label.includes('Lifetime (1881–1942)'), label);
  // The category was missing from the label entirely.
  assert.ok(label.includes('Fiction / Volumes'), label);

  App.state.query = 'schachnovelle';
  assert.strictEqual(App._resultsLabel(411),
    '411 results for “schachnovelle” · Fiction · Lifetime (1881–1942) · Fiction / Volumes');

  // Without query and filters the view is the whole catalogue, not a selection.
  App.state.query = '';
  App.state.filters = {};
  assert.strictEqual(App._resultsLabel(4751), 'All 4,751 entries');
  assert.strictEqual(App._resultsLabel(1), 'All 1 entry');

  // A capped search says so instead of reading as a complete count.
  App.state.query = 'zweig';
  App._searchCapped = true;
  assert.ok(App._resultsLabel(5000).includes('first 5,000 matches'));
});

test('the review facet reads the review state of an entry, absence included', () => {
  const App = loadApp();
  const verified = { review: { status: 'agent_verified' } };
  const contested = { review: { status: 'contested' } };
  const undecided = {};
  const flagged = { review: { status: 'agent_verified' }, reviewFlags: [{ code: 'encoding-repaired' }] };

  // The arrays come out of the script context, so they are compared as text.
  assert.strictEqual(JSON.stringify(App.reviewValues(verified)), '["agent_verified"]');
  assert.strictEqual(JSON.stringify(App.reviewValues(undecided)), '["unreviewed"]');
  // An open flag is an axis of its own, so a flagged entry counts twice.
  assert.strictEqual(JSON.stringify(App.reviewValues(flagged)),
    '["agent_verified","open-flags"]');

  assert.strictEqual(App.reviewLabel('agent_verified'), 'Agent verified');
  assert.strictEqual(App.reviewLabel('unreviewed'), 'Unreviewed');
  assert.strictEqual(App.reviewLabel('open-flags'), 'Open review flags');

  const kept = (entry, value) => App._matchesFilters(entry, { review: value }, null);
  assert.strictEqual(kept(undecided, 'unreviewed'), true);
  assert.strictEqual(kept(verified, 'unreviewed'), false);
  assert.strictEqual(kept(contested, 'contested'), true);
  assert.strictEqual(kept(flagged, 'open-flags'), true);
  assert.strictEqual(kept(verified, 'open-flags'), false);

  // The facet is addressable, so a hash reproduces the selection.
  assert.strictEqual(
    JSON.stringify(App.filtersFromParams(new URLSearchParams('review=unreviewed'))),
    '{"review":"unreviewed"}');
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

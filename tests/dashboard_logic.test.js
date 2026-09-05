/** Source-page counts, linked selections and the accessible range/result paths. */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function loadDashboard() {
  const location = { hash: '', pathname: '/', hostname: 'localhost' };
  const ctx = {
    window: { location, addEventListener() {} }, location, URLSearchParams, console,
    history: { replaceState() {}, pushState() {} },
    document: { addEventListener() {}, getElementById() { return null; } },
  };
  vm.createContext(ctx);
  for (const file of ['constants.js', 'utils.js', 'app.js', 'explore.js', 'explore-timeline.js']) {
    vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'docs', 'js', file), 'utf8'), ctx);
  }
  const result = vm.runInContext('({ App, Explore, dashboard: ExploreTimeline })', ctx);
  result.Explore._onFilterChange = () => {
    result.dashboard.entries = result.Explore.getFiltered();
  };
  return { ...result, location };
}

const rows = [
  { sourcePageId: 1, title: 'First', year: 1930, language: 'German', entryType: 'fiction' },
  { sourcePageId: 2, title: 'Second', year: 1939, language: 'French', entryType: 'fiction' },
  { sourcePageId: 3, title: 'Third', year: 1950, language: 'German', entryType: 'essay' },
  { sourcePageId: 4, title: 'Undated', year: null, language: 'French', entryType: 'essay' },
  { sourcePageId: 5, title: 'No language', year: 1951, language: null, entryType: 'fiction' },
  { sourcePageId: 6, title: 'No metadata', entryType: 'essay' },
];
const plain = value => JSON.parse(JSON.stringify(value));

test('coverage counts source entries and retains undated and unrecorded language gaps', () => {
  const { dashboard } = loadDashboard();
  assert.deepEqual(plain(dashboard.coverage(rows)), {
    total: 6, dated: 4, undated: 2, languages: 2, missingLanguage: 2,
  });
  assert.deepEqual(plain(dashboard.decadeCounts(rows)), [[1930, 2], [1940, 0], [1950, 2]]);
  assert.deepEqual(plain(dashboard.coverage([])), {
    total: 0, dated: 0, undated: 0, languages: 0, missingLanguage: 0,
  });
  assert.deepEqual(plain(dashboard.decadeCounts(rows.filter(row => !row.year))), []);
});

test('language and decade controls narrow one selection while leaving alternatives reachable', () => {
  const { Explore, dashboard } = loadDashboard();
  Explore.entries = rows;
  const click = dataset => dashboard.onClick({ target: { closest() {
    return { dataset, hasAttribute() { return false; } };
  } } });
  click({ dashboardFacet: 'languages', value: 'German' });
  click({ dashboardDecade: '1930' });
  assert.deepEqual(plain(dashboard.entries.map(row => row.sourcePageId)), [1]);
  assert.deepEqual(plain(dashboard.contextForYears().map(row => row.sourcePageId)), [1, 3]);
  assert.deepEqual(plain(Explore.facetCounts('languages')), [['French', 1], ['German', 1]]);
  click({ dashboardDecade: '1930' });
  assert.deepEqual(plain(dashboard.entries.map(row => row.sourcePageId)), [1, 3]);
});

test('year form rejects reversed bounds and excludes undated rows with an upper bound only', () => {
  const { Explore, dashboard } = loadDashboard();
  Explore.entries = rows;
  let validity = '', reports = 0;
  const from = { value: '1960' };
  const to = { value: '1930', setCustomValidity(message) { validity = message; }, reportValidity() { reports++; } };
  const event = { preventDefault() {}, currentTarget: { elements: { from, to } } };
  dashboard.applyRange(event);
  assert.match(validity, /end year/);
  assert.equal(reports, 1);
  assert.deepEqual(plain(Explore.filters.yearRange), [null, null]);
  from.value = '';
  to.value = '1939';
  dashboard.applyRange(event);
  assert.equal(validity, '');
  assert.deepEqual(plain(dashboard.entries.map(row => row.sourcePageId)), [1, 2]);
  assert.equal(Explore.filters.decade, null);
});

test('preview truncation never truncates the View all result selection', () => {
  const { App, Explore, dashboard, location } = loadDashboard();
  Explore.entries = rows;
  dashboard.entries = rows;
  const html = dashboard.previewHtml(rows);
  assert.equal((html.match(/class="dashboard-entry-link"/g) || []).length, 5);
  assert.match(html, /View all 6 entries/);
  dashboard.openResults();
  assert.equal(location.hash, 'browse=1');
  Explore.filters.languages = ['French', 'Not recorded'];
  dashboard.entries = Explore.getFiltered();
  dashboard.openResults();
  const filters = App.filtersFromParams(new URLSearchParams(location.hash));
  assert.deepEqual(plain(App._applyFilterSet(rows, filters).map(row => row.sourcePageId)), [2, 4, 5, 6]);
});

test('empty selection preview is explicit and cannot open a misleading result list', () => {
  const { dashboard } = loadDashboard();
  assert.match(dashboard.previewHtml([]), /No entries match these filters/);
  assert.match(dashboard.previewHtml([]), /data-dashboard-results disabled/);
});

test('a restored dashboard URL replaces stale session filters', () => {
  const { Explore } = loadDashboard();
  Explore.filters.languages = ['German'];
  Explore.filters.types = ['essay'];
  Explore.filters.country = 'AT';
  Explore.filters.yearRange = [1930, 1939];
  Explore.setMode = mode => { Explore.mode = mode; };
  Explore.restoreFromHash('timeline', new URLSearchParams('language=French'));
  assert.deepEqual(plain(Explore.filters.languages), ['French']);
  assert.deepEqual(plain(Explore.filters.types), []);
  assert.deepEqual(plain(Explore.filters.yearRange), [null, null]);
  assert.equal(Explore.filters.country, null);
});

test('restored malformed or conflicting date filters agree with the range UI and results', () => {
  const { App, Explore } = loadDashboard();
  Explore.entries = rows;
  Explore.setMode = mode => { Explore.mode = mode; };
  const cases = [
    ['years=1930-1939&decade=1950', [null, null], 1950, [3, 5]],
    ['years=abc-1939', [null, 1939], null, [1, 2]],
    ['decade=bad', [null, null], null, [1, 2, 3, 4, 5, 6]],
    ['years=1960-1930', [null, null], null, [1, 2, 3, 4, 5, 6]],
    ['years=1930x-1950&decade=1935', [null, 1950], null, [1, 2, 3]],
  ];
  for (const [query, years, decade, ids] of cases) {
    Explore.restoreFromHash('timeline', new URLSearchParams(query));
    assert.deepEqual(plain(Explore.filters.yearRange), years, query);
    assert.equal(Explore.filters.decade, decade, query);
    assert.deepEqual(plain(Explore.getFiltered().map(row => row.sourcePageId)), ids, query);
    const filters = App.filtersFromParams(new URLSearchParams(Explore._resultParams()));
    assert.deepEqual(plain(App._applyFilterSet(rows, filters).map(row => row.sourcePageId)), ids, query);
  }
});

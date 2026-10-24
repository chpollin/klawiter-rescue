/**
 * Pins what the Overview and the text pages say about the data (docs/js/home.js,
 * docs/js/pages.js).
 *
 * An entry is a wiki page, not a publication; a place spelling is not a place;
 * the year range follows the records. The authority links rest on decisions by
 * LLM agents under the operator's delegation, and the text pages say so
 * instead of letting a state word imply a human review.
 */
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function read(file) {
  return fs.readFileSync(path.join(__dirname, '..', 'docs', 'js', file), 'utf8');
}

function ctxWith(files, data) {
  const ctx = {
    console,
    setTimeout: () => 0,
    window: { scrollTo() {} },
    document: { addEventListener() {}, getElementById: () => null },
    App: { state: { query: '' }, data },
    JsonldPlayground: { init() {} },
  };
  vm.createContext(ctx);
  for (const file of ['constants.js', 'utils.js', ...files]) vm.runInContext(read(file), ctx);
  return ctx;
}

const records = [
  { sourcePageId: 35, year: 1815, language: 'German', location: 'Wien',
    locationSameAs: 'http://www.wikidata.org/entity/Q1741', sourceRevision: { action: 'restore' } },
  { sourcePageId: 36, year: 1930, language: 'German', location: 'Vienna',
    locationSameAs: 'http://www.wikidata.org/entity/Q1741' },
  { sourcePageId: 37, year: 2020, language: 'Danish', location: 'København, 1948' },
  { sourcePageId: 38, language: 'Danish' },
];

test('the Overview places the wiki types in the sections and shows print counts only from the local structure', () => {
  const ctx = ctxWith(['home.js'], { entries: records, _meta: {} });
  const Home = vm.runInContext('Home', ctx);
  const counts = { fiction: 7, essay: 3, 'collected-works': 2, film: 1, newspaper: 1 };
  const flat = html => html.replace(/\s+/g, ' ');
  const published = flat(Home.table(counts, ['newspaper'], null));
  // Without the print structure the table holds the 1991 contents and the wiki.
  assert.match(published, /Contents/);
  assert.doesNotMatch(published, /Main volume|source-year">1999/);
  assert.match(published, /F 1&ndash;723/);
  // A type over two adjacent sections spans both rows; essays stand at C, H points up.
  assert.match(published, /rowspan="2" data-label="Wiki"><button[^>]*data-type="collected-works"/);
  assert.match(published, /&uarr; C/);
  assert.match(published, /Only in the wiki/);
  assert.match(published, /data-type="newspaper"/);

  const print = {
    viewer: 'http://127.0.0.1:8767/viewer/index.html',
    volumes: { I: { F: { kind: 'body', entries: 720, highest: 723 }, 'Index A': { kind: 'index', entries: 9 } } },
    totals: { I: { entries: 720, objects: 900, values: 5000 } },
  };
  const local = flat(Home.table(counts, [], print));
  assert.match(local, /href="http:\/\/127\.0\.0\.1:8767\/viewer\/index\.html#\/\?v=I&amp;part=F"[^>]*>720</);
  assert.match(local, /720 entries in section F of Main volume, numbered up to 723/);
  // A section the volume lacks is a dash, not an empty cell.
  assert.match(local, /No section A in Main volume/);
  // No figure is written into the page code.
  assert.doesNotMatch(read('home.js'), /1815|2020|4,758/);
});

test('About and Data say who decided the authority links and which pages are restored', () => {
  const ctx = ctxWith(['pages.js'], { entries: records, _meta: { ns0Count: 4, languageCount: 2 } });
  const Pages = vm.runInContext('Pages', ctx);
  const flat = html => html.replace(/\s+/g, ' ');
  const about = flat(Pages.about());
  const note = 'Place and work authority links were decided by LLM agents under delegation '
    + 'by the operator and are revisable; no human review of them has been released yet.';
  assert.ok(about.includes(note), 'About names the producer of the authority links');
  assert.ok(flat(Pages.data()).includes(note), 'Data names it in the data model');
  // The methodology no longer says every page is its latest revision.
  assert.match(about, /takes the latest revision\. 1 pages use a restored earlier revision instead/);
  assert.match(about, /Source revision/);
});

test('About reads the redirect map size from the data, and Data names its quality link for its target', () => {
  const ctx = ctxWith(['pages.js'], { entries: records, _meta: { ns0Count: 4, redirectCount: 1523 } });
  const Pages = vm.runInContext('Pages', ctx);
  const about = Pages.about().replace(/\s+/g, ' ');
  assert.match(about, /a map of 1,523 alternative titles/);
  assert.doesNotMatch(read('pages.js'), /1,546/);
  // The Help names the Explore views by their tabs and the Review facet.
  assert.match(about, /three views: Overview, .*; Map, .*; and Connections/);
  assert.match(about, /period, location and review state/);
  // The anchor leaves the page for the workbench, so it says so.
  assert.match(Pages.data(), /<a href="#data\/quality">Data Quality workbench<\/a>/);
});

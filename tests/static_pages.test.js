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

test('the Overview counts wiki pages, place spellings and linked places, and years from the records', () => {
  const ctx = ctxWith(['home.js'], { entries: records, _meta: {} });
  const Home = vm.runInContext('Home', ctx);
  const stats = Home.stats(records);
  assert.strictEqual(stats.entries, 4);
  assert.strictEqual(stats.placeSpellings, 3);
  // Wien and Vienna are one authority place; the mis-parse links nowhere.
  assert.strictEqual(stats.linkedPlaces, 1);
  assert.deepStrictEqual([stats.minYear, stats.maxYear], [1815, 2020]);

  const text = Home.introText(stats).replace(/\s+/g, ' ');
  assert.match(text, /^4 entries \(wiki pages\) on publications/);
  assert.match(text, /1 places of publication linked to Wikidata among 3 place spellings, 1815&ndash;2020/);
  assert.doesNotMatch(text, /\d publications by/);

  // A repaired year extraction moves the range; nothing is written down.
  const repaired = Home.stats(records.filter(row => row.year !== 1815));
  assert.match(Home.introText(repaired), /1930&ndash;2020/);
  assert.doesNotMatch(read('home.js'), /1815|2020/);
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

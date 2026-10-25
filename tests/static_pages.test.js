/**
 * Pins what the Overview, the Documentation page and the help say about the
 * data (docs/js/home.js, docs/js/pages.js).
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
    URLSearchParams,
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
  const ctx = ctxWith(['record-card.js', 'records.js', 'home.js'], { entries: records, _meta: {} });
  const Home = vm.runInContext('Home', ctx);
  const counts = { fiction: 7, essay: 3, 'collected-works': 2, film: 1, newspaper: 1 };
  const flat = html => html.replace(/\s+/g, ' ');
  const published = flat(Home.table(counts, ['newspaper'], null));
  // Without the print structure the table holds the 1991 contents and the wiki.
  assert.match(published, /Contents/);
  assert.doesNotMatch(published, /Main volume|source-year">1999/);
  assert.match(published, /F 1&ndash;723/);
  // A head names the unit of its column; the address form is its tooltip.
  assert.match(published, /<span class="source-unit">numbers<\/span>/);
  assert.match(published, /title="Wiki pages of the entry type [^"]*page 448"/);
  // What a column's counts open is said once, in its head.
  assert.match(published, /<span class="source-unit">pages · open in Records<\/span>/);
  assert.doesNotMatch(published, /class="target"/);
  assert.doesNotMatch(published, /source-address/);
  // A type over two adjacent sections spans both rows; the bracket has words.
  assert.match(published, /rowspan="2" title="One wiki type, Collected Works, covers sections A and B" data-label="Wiki \(A and B\)"><button[^>]*data-type="collected-works"/);
  // Every wiki count names the list it opens.
  assert.match(published, /aria-label="Open the 7 wiki pages of type Fiction \(section F\) in Records"/);
  assert.match(published, /aria-label="Open the 2 wiki pages of type Collected Works \(sections A and B\) in Records"/);
  assert.match(published, /aria-label="Open the 3 wiki pages of type Essays \(sections C and H\) in Records"/);
  // Essays stand at C; H points up and says so.
  assert.match(published, /title="Essays belong to sections C and H and are counted at C\. Open the 3 wiki pages of type Essays in Records"[^>]*>&uarr; C</);
  assert.match(published, /Only in the wiki/);
  assert.match(published, /data-type="newspaper"/);
  // One legend line for the bracket and the pointer, which no head explains;
  // no bars.
  // Where the table stacks and its heads are hidden, one item names the targets.
  assert.match(published, /<ul class="home-legend"[^>]*><li class="legend-targets">wiki counts open their records<\/li><li class="legend-covers">.*one wiki type covers two sections.*&uarr; C<\/span> counted at section C/);
  assert.doesNotMatch(published, /opens print cards|catalogue|count-bar/);

  const print = {
    viewer: 'http://127.0.0.1:8767/viewer/index.html',
    volumes: {
      I: { F: { kind: 'body', entries: 720, highest: 723 }, 'Index A': { kind: 'index', entries: 9 } },
      A2: { F: { kind: 'body', entries: 40 } },
    },
    totals: { I: { entries: 720, objects: 900, values: 5000 } },
  };
  // On a server where Records shows no print records a print count is text,
  // not a dead link.
  Home.printReady = false;
  const plain = flat(Home.table(counts, [], print));
  assert.doesNotMatch(plain, /viewer\/index\.html|src=print/);
  assert.match(plain, /<span class="print-count" title="720 entries of section F of the main volume, numbered up to 723">720<\/span>/);
  assert.match(plain, /<span class="source-unit">entries<\/span>/);
  assert.doesNotMatch(plain, /entries · open in Records/);
  // The working file says what it is in its head.
  assert.match(plain, /<span class="source-year">working file to 2009<\/span>/);
  assert.match(plain, /title="Entries of the Addendum II working file, cited by addresses such as FA2 3"/);

  // Where Records shows print records, a count of entries opens the entries
  // of its section in Records, never the objects they hold.
  Home.printReady = true;
  const local = flat(Home.table(counts, [], print));
  assert.match(local, /href="#records&amp;src=print&amp;vol=I&amp;part=F&amp;unit=entry"[^>]*>720</);
  assert.match(local, /href="#records&amp;src=print&amp;vol=I&amp;kind=index&amp;unit=entry"[^>]*>9</);
  assert.doesNotMatch(local, /viewer\/|cards\.html/);
  assert.match(local, /aria-label="Open the 720 entries of section F of the main volume in Records \(numbered up to 723\)"/);
  assert.match(local, /aria-label="Open the 9 index entries of the main volume \(Index A\) in Records"/);
  assert.match(local, /<span class="source-unit">entries · open in Records<\/span>/);
  assert.match(local, /<li class="legend-targets">print and wiki counts open their records<\/li>/);
  // A section the volume lacks is a dash, not an empty cell.
  assert.match(local, /No section A in the main volume/);
  // No figure is written into the page code.
  assert.doesNotMatch(read('home.js'), /1815|2020|4,758/);
});

test('the Documentation page says once who decided the authority links and which pages are restored', () => {
  const ctx = ctxWith(['pages.js'], { entries: records, _meta: { ns0Count: 4, languageCount: 2 } });
  const Pages = vm.runInContext('Pages', ctx);
  const flat = html => html.replace(/\s+/g, ' ');
  const docs = flat(Pages.docs());
  const note = 'Place and work authority links were decided by LLM agents under delegation '
    + 'by the operator and are revisable; no human review of them has been released yet.';
  // About and Data each said it; on one page it stands once, with the states.
  assert.strictEqual(docs.split(note).length - 1, 1, 'the producer of the authority links, said once');
  assert.match(docs, /<section id="sec-states">.*Place and work authority links were decided/);
  // The methodology no longer says every page is its latest revision.
  assert.match(docs, /takes the latest revision\. 1 pages use a restored earlier revision instead/);
  assert.match(docs, /Source revision/);
  // The compiler's life dates and the licence stand once each.
  assert.strictEqual(docs.split('(1930&ndash;2021)').length - 1, 1);
  assert.strictEqual(docs.split('licenses/by/4.0/').length - 1, 1);
});

test('the Documentation page holds three parts with a section navigation', () => {
  const ctx = ctxWith(['pages.js'], { entries: records, _meta: { ns0Count: 4, redirectCount: 1523 } });
  const Pages = vm.runInContext('Pages', ctx);
  const docs = Pages.docs().replace(/\s+/g, ' ');
  assert.match(docs, /a map of 1,523 alternative titles/);
  assert.doesNotMatch(read('pages.js'), /1,546/);
  // Every section the navigation names exists, in the order of its part.
  const ids = [...docs.matchAll(/<section id="sec-([a-z]+)"/g)].map(m => m[1]);
  assert.deepStrictEqual(ids, ['project', 'origin', 'imprint', 'citation', 'licence',
    'method', 'pipeline', 'model', 'states', 'limitations',
    'data', 'downloads', 'spec', 'playground', 'quality']);
  for (const part of Pages.DOCS_PARTS) {
    assert.match(docs, new RegExp(`<a class="docs-toc-part" href="#docs/${part.id}">`));
    for (const [id] of part.sections) {
      assert.match(docs, new RegExp(`<a href="#docs/${id}">`), id);
    }
  }
  // A list of links claims no current section; a select did and went stale.
  assert.doesNotMatch(docs, /<select/);
  // Help is no section of the page any more.
  assert.doesNotMatch(docs, /sec-help|Reporting an error/);
  // Links point at the new addresses; the workbench keeps its own.
  assert.doesNotMatch(docs, /href="#about|href="#data"/);
  assert.match(docs, /<a href="#data\/quality">Data Quality workbench<\/a>/);
});

test('the help names the Explore views and the Review facet, and links to the new addresses', () => {
  const ctx = ctxWith(['pages.js'], { entries: records, _meta: {} });
  const Pages = vm.runInContext('Pages', ctx);
  const help = Pages.help().replace(/\s+/g, ' ');
  for (const heading of ['Search, browse, filter', 'Entry details and export', 'Explore and data quality', 'Reporting an error']) {
    assert.ok(help.includes(`<h3>${heading}</h3>`), heading);
  }
  assert.match(help, /three views: Overview, .*; Map, .*; and Connections/);
  assert.match(help, /period, location and review state/);
  assert.match(help, /<a href="#docs\/downloads">Downloads<\/a> in the Documentation/);
  // The workbench and the issue tracker are described once, in the Documentation.
  assert.match(help, /<a href="#docs\/quality">its section in the Documentation<\/a>/);
  assert.match(help, /<a href="#docs\/licence">Licence and contact<\/a>/);
  assert.doesNotMatch(help, /field completeness|github\.com/);
  assert.doesNotMatch(help, /href="#data"|href="#about/);
});

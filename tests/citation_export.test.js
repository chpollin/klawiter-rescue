/**
 * Pins what a citation exported from a card describes (docs/js/export.js).
 *
 * A source page can document several publications, so a citation has to name
 * the one the reader chose. Where the publication layer is loaded it is the
 * source of the citation; the flat compatibility fields answer only while it
 * is not, because they can join the imprint of one publication to the language
 * of another.
 */
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function read(file) {
  return fs.readFileSync(path.join(__dirname, '..', 'docs', 'js', file), 'utf8');
}

/** Export with the globals it reads, and downloadBlob captured. */
function exportCtx(entry, publications, claims) {
  const captured = [];
  const location = {
    protocol: 'https:', hostname: 'chpollin.github.io',
    origin: 'https://chpollin.github.io', pathname: '/klawiter-rescue/',
  };
  const ctx = {
    console, location, captured,
    document: { querySelectorAll: () => [], addEventListener() {},
      getElementById: () => null, querySelector: () => null },
    navigator: {},
    App: {
      state: { editMode: false, singleEntry: true, query: '' },
      entries: Array.isArray(entry) ? entry : [entry],
      entryMap: new Map((Array.isArray(entry) ? entry : [entry])
        .map(row => [row.sourcePageId, row])),
      titleMap: new Map(),
      data: { redirects: {} },
    },
    Edit: {
      FIELD_LABELS: {}, pending: () => undefined,
      entryStatus: () => ({ status: 'unreviewed', pending: false }),
      triageHints: () => [], evidence: () => null,
      editionClaimsFor: () => [], authorityClaimsFor: () => claims || [],
      locationReconciliation: () => null, agentReconciliation: () => null,
    },
  };
  vm.createContext(ctx);
  for (const file of ['constants.js', 'utils.js', 'detail.js', 'export.js']) {
    vm.runInContext(read(file), ctx);
  }
  vm.runInContext(
    'downloadBlob = (content, filename, type) => captured.push({ content, filename, type });',
    ctx
  );
  const Detail = vm.runInContext('Detail', ctx);
  if (publications) {
    const rows = Array.isArray(entry) ? entry : [entry];
    for (const row of rows) {
      const pubs = Array.isArray(entry) ? publications[row.sourcePageId] : publications;
      if (pubs) {
        Detail._pubCache.set(row.sourcePageId,
          { status: 'ready', publications: pubs, nameVariants: [] });
      }
    }
  }
  return { Export: vm.runInContext('Export', ctx), captured };
}

function editionEntry() {
  return {
    sourcePageId: 1800,
    entryType: 'historical-study',
    title: 'Romanŭt na edin zhivot. Balzak',
    year: 1947,
    // The flat projection joined the translation statement into the publisher.
    publisher: 'Translated by Dimitŭr Stoevski. 1st edition',
    location: 'Sofija',
    language: 'Bulgarian',
    pageCount: 500,
    translator: 'Dimitŭr Stoevski',
    publicationCount: 2,
    pageKind: 'edition-page',
  };
}

function editions() {
  return [
    {
      id: 'klawiter:publication/1800-1947-a', year: 1947,
      title: 'Romanŭt na edin zhivot. Balzak',
      publisher: 'Pechat Far', places: ['Sofija'],
      language: 'Bulgarian', languageCode: 'bg',
      editionStatement: '1st edition',
      extent: { raw: '500p.', numbered: 500 },
      series: 'Biblioteka Zlatni zŭrna', seriesVolume: 'XII',
      credits: [{ role: 'translator', name: 'Dimitŭr Stoevski', creditLabel: 'Translated by' }],
    },
    {
      id: 'klawiter:publication/1800-1960-a', year: 1960,
      title: 'Romanŭt na edin zhivot. Balzak',
      publisher: 'Narodna Kultura', places: ['Sofija'],
      language: 'Bulgarian', languageCode: 'bg',
      editionStatement: '2nd revised edition',
      extent: { raw: '383/(1)p.', numbered: 383, unnumbered: 1 },
      credits: [{ role: 'translator', name: 'Dimitŭr Stoevski', creditLabel: 'Translated by' }],
    },
  ];
}

test('a publication is cited with its own imprint, extent and credits', () => {
  const { Export, captured } = exportCtx(editionEntry(), editions());
  Export.bibtex(1800, 0);
  const bib = captured[0].content;

  assert.match(bib, /@book\{klawiter1800-1947-a,/);
  assert.match(bib, /publisher = \{Pechat Far\}/);
  assert.match(bib, /address = \{Sofija\}/);
  assert.match(bib, /edition = \{1st edition\}/);
  // pagetotal is a number of pages; the notation of the source is prose and
  // goes to the note, which this citation carries anyway.
  assert.match(bib, /pagetotal = \{500\}/);
  assert.match(bib, /note = \{[^}]*Extent: 500p\./);
  assert.match(bib, /translator = \{Dimitŭr Stoevski\}/);
  assert.match(bib, /note = \{[^}]*Translated by Dimitŭr Stoevski/, 'the source wording stays');
  assert.match(bib, /series = \{Biblioteka Zlatni zŭrna\}/);
  // The misparse of the flat field must not reach a citation any more.
  assert.doesNotMatch(bib, /publisher = \{Translated by/);
  assert.strictEqual(captured[0].filename, 'klawiter-1800-1947-a.bib');
});

test('the two editions of one page are cited apart', () => {
  const { Export, captured } = exportCtx(editionEntry(), editions());
  Export.bibtex(1800, 1);
  const second = captured[0].content;
  assert.match(second, /publisher = \{Narodna Kultura\}/);
  assert.match(second, /edition = \{2nd revised edition\}/);
  assert.match(second, /pagetotal = \{383\}/);
  assert.match(second, /note = \{[^}]*Extent: 383\/\(1\)p\./);
  assert.doesNotMatch(second, /Pechat Far/);
});

test('the author follows the grouping of the Overview, and an author page its title', () => {
  // historical-study sits under Works, so it is a text by Zweig. It used to be
  // in a hand-kept "about Zweig" list and lost its author to it.
  const own = exportCtx(editionEntry(), editions());
  own.Export.bibtex(1800, 0);
  assert.match(own.captured[0].content, /author = \{Zweig, Stefan\}/);
  assert.doesNotMatch(own.captured[0].content, /keywords = \{Stefan Zweig\}/);

  // An author page carries the name of the author as its title, and every
  // publication listed on it is that author's.
  const authorPage = {
    sourcePageId: 4445, entryType: 'secondary-literature', pageKind: 'author-page',
    title: 'Al-Bāḥ, Muḥammad / El-bah, Mohammed', publicationCount: 2,
  };
  const book = {
    id: 'klawiter:publication/4445-2000-a', year: 2000,
    title: 'Frauen- und Männerbilder in den Novellen von Stefan Zweig',
    publisher: 'Hochschulverl.', places: ['Freiburg im Breisgau'], language: 'German',
    extent: { raw: '168p.', numbered: 168 },
  };
  const page = exportCtx(authorPage, [book]);
  page.Export.bibtex(4445, 0);
  assert.match(page.captured[0].content, /author = \{Al-Bāḥ, Muḥammad \/ El-bah, Mohammed\}/);
  // The page is about Zweig, so he stays the keyword rather than the author.
  assert.match(page.captured[0].content, /keywords = \{Stefan Zweig\}/);

  // A page about Zweig that names no author carries none.
  const about = { ...authorPage, pageKind: 'single-publication', title: 'Stefan Zweig heute' };
  const secondary = exportCtx(about, [book]);
  secondary.Export.bibtex(4445, 0);
  assert.doesNotMatch(secondary.captured[0].content, /author = /);
  assert.match(secondary.captured[0].content, /keywords = \{Stefan Zweig\}/);
});

test('a contested place is cited in full and says that the assignment is open', () => {
  // Page 4209: the imprint reads "Nasionale Pers Beperk, Bloemfontein,
  // Kaapstad (Capetown)" and the place claim is open in reconciliation.json.
  const entry = {
    sourcePageId: 4209, entryType: 'fiction', title: "Vreemdes in 'n vreemde wêreld",
    location: 'Kaapstad (Capetown)', publicationCount: 1, pageKind: 'single-publication',
  };
  const pub = {
    id: 'klawiter:publication/4209-1947-a', year: 1947,
    title: "Vreemdes in 'n vreemde wêreld", publisher: 'Nasionale Pers Beperk',
    places: ['Bloemfontein', 'Kaapstad (Capetown)'], language: 'Afrikaans',
    extent: { raw: '160p.', numbered: 160 },
    credits: [{ role: 'translator', name: 'Hymne Weiss',
      creditLabel: 'Translated with a foreword and preface by' }],
  };
  const claims = [{ claimId: 'klawiter:claim/reconciliation/location/e5742c35b57192e9',
    entityType: 'location', claimStatus: 'contested', decisionStatus: 'open' }];

  const { Export, captured } = exportCtx(entry, [pub], claims);
  Export.bibtex(4209, 0);
  const bib = captured[0].content;
  assert.match(bib, /address = \{Bloemfontein, Kaapstad \(Capetown\)\}/);
  assert.match(bib, /note = \{[^}]*Place authority assignment contested/);

  captured.length = 0;
  Export.ris(4209, 0);
  const ris = captured[0].content;
  assert.match(ris, /CY {2}- Bloemfontein/);
  assert.match(ris, /CY {2}- Kaapstad \(Capetown\)/);
  assert.match(ris, /N1 {2}- Place authority assignment contested/);

  // Without an open claim the citation says nothing about the assignment.
  const settled = exportCtx(entry, [pub]);
  settled.Export.bibtex(4209, 0);
  assert.doesNotMatch(settled.captured[0].content, /contested/);
});

test('the batch export writes one citation per publication', async () => {
  const edition = editionEntry();
  const flatOnly = {
    sourcePageId: 4711, entryType: 'fiction', title: 'Schachnovelle',
    year: 1942, publisher: 'Pigmalión', location: 'Buenos Aires',
  };
  const { Export, captured } = exportCtx([edition, flatOnly],
    { 1800: editions() });

  const seen = [];
  const count = await Export.batchBibtex([edition, flatOnly], state => seen.push(state));
  const bib = captured[0].content;
  // Two editions of page 1800 and the flat citation of the page without a
  // publication file; the flat record alone dropped the 1960 edition.
  assert.strictEqual(count, 3);
  assert.match(bib, /klawiter1800-1947-a/);
  assert.match(bib, /klawiter1800-1960-a/);
  assert.match(bib, /Narodna Kultura/);
  assert.match(bib, /@book\{klawiter4711,/);
  assert.strictEqual(captured[0].filename, 'klawiter-results.bib');
  // The button is told what to say: progress while loading, then the number of
  // citations, which is not the number of exported pages.
  assert.strictEqual(seen.at(-1).citations, 3);
  assert.ok(seen.some(state => state.total === 2), JSON.stringify(seen));
});

test('the page export of a multi-publication page collects every publication', () => {
  const { Export, captured } = exportCtx(editionEntry(), editions());
  Export.bibtex(1800);
  const all = captured[0].content;
  assert.match(all, /klawiter1800-1947-a/);
  assert.match(all, /klawiter1800-1960-a/);
  assert.match(all, /Pechat Far/);
  assert.match(all, /Narodna Kultura/);
  assert.strictEqual(captured[0].filename, 'klawiter-1800.bib');
});

test('a single publication replaces the flat values once its file is loaded', () => {
  const entry = editionEntry();
  entry.publicationCount = 1;
  entry.pageKind = 'single-publication';
  const one = [editions()[0]];

  const loaded = exportCtx(entry, one);
  loaded.Export.bibtex(1800);
  assert.match(loaded.captured[0].content, /publisher = \{Pechat Far\}/);
  assert.strictEqual(loaded.captured[0].filename, 'klawiter-1800.bib');

  // Without the page file the flat compatibility fields answer, as before.
  const flat = exportCtx(entry, null);
  flat.Export.bibtex(1800);
  assert.match(flat.captured[0].content, /publisher = \{Translated by Dimit/);
});

test('an article is cited as an article, with its container', () => {
  const entry = {
    sourcePageId: 4445, entryType: 'secondary-literature',
    title: 'Al-Bāḥ, Muḥammad', year: 2000, publicationCount: 2, pageKind: 'author-page',
  };
  const article = {
    id: 'klawiter:publication/4445-2015-a', year: 2015,
    title: 'Ṣūrat al-marʾah waʾl-rajul', language: 'Arabic',
    container: { title: 'Al-Balāghah waʾl-naqd al-ʿarabī', place: 'Rabat',
      issue: '3', pages: '71-79' },
    online: { url: 'http://platform.almanhal.com/Article/Preview.aspx?ID=60445',
      note: 'shortened preview version' },
  };
  const { Export, captured } = exportCtx(entry, [article]);

  Export.bibtex(4445, 0);
  const bib = captured[0].content;
  assert.match(bib, /@article\{/);
  assert.match(bib, /journaltitle = \{Al-Balāghah waʾl-naqd al-ʿarabī\}/);
  assert.match(bib, /number = \{3\}/);
  assert.match(bib, /pages = \{71-79\}/);
  assert.match(bib, /address = \{Rabat\}/);
  // A page about an author is not authored by Zweig.
  assert.doesNotMatch(bib, /author = \{Zweig/);
  assert.match(bib, /keywords = \{Stefan Zweig\}/);

  captured.length = 0;
  Export.ris(4445, 0);
  const ris = captured[0].content;
  assert.match(ris, /TY {2}- JOUR/);
  assert.match(ris, /T2 {2}- Al-Balāghah waʾl-naqd al-ʿarabī/);
  assert.match(ris, /IS {2}- 3/);
  assert.match(ris, /SP {2}- 71/);
  assert.match(ris, /EP {2}- 79/);
  assert.match(ris, /UR {2}- https:\/\/chpollin\.github\.io\/klawiter-rescue\/#entry=4445/);
  assert.strictEqual(captured[0].filename, 'klawiter-4445-2015-a.ris');
});

test('RIS carries the credits of the publication by their role', () => {
  const entry = editionEntry();
  const pub = editions()[0];
  pub.credits = [
    { role: 'translator', name: 'Dimitŭr Stoevski', creditLabel: 'Translated by' },
    { role: 'editor', name: 'N. Vysotskaia', creditLabel: 'Edited by' },
  ];
  const { Export, captured } = exportCtx(entry, [pub]);
  Export.ris(1800, 0);
  const ris = captured[0].content;
  assert.match(ris, /A2 {2}- Dimitŭr Stoevski/);
  assert.match(ris, /A3 {2}- N\. Vysotskaia/);
  assert.match(ris, /ET {2}- 1st edition/);
  assert.match(ris, /N1 {2}- Extent: 500p\./);
});

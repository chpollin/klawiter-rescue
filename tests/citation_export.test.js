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
  return { Export: vm.runInContext('Export', ctx), captured, ctx };
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

test('Zweig is the author of his own texts only, and an author page names its author', () => {
  // historical-study sits under Works, so it is a text by Zweig. It used to be
  // in a hand-kept "about Zweig" list and lost its author to it.
  const own = exportCtx(editionEntry(), editions());
  own.Export.bibtex(1800, 0);
  assert.match(own.captured[0].content, /author = \{Zweig, Stefan\}/);
  assert.doesNotMatch(own.captured[0].content, /keywords = \{Stefan Zweig\}/);

  // An author page carries the name of the author as its title, and every
  // publication listed on it is that author's. What follows " / " is a second
  // spelling of the name, not part of it.
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
  assert.match(page.captured[0].content, /author = \{Al-Bāḥ, Muḥammad\},/);
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
  // Kaapstad (Capetown)". A claim applies to the place it names word for
  // word, here one component of the imprint.
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
    entityType: 'location', claimStatus: 'contested', decisionStatus: 'open',
    subject: { name: 'Kaapstad (Capetown)' } }];

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

  // Without an open claim the citation says nothing about the assignment,
  // and neither does it for a decided claim or one naming the compound line.
  const settled = exportCtx(entry, [pub]);
  settled.Export.bibtex(4209, 0);
  assert.doesNotMatch(settled.captured[0].content, /contested/);
  for (const other of [{ ...claims[0], decisionStatus: 'decided' },
    { ...claims[0], subject: { name: 'Bloemfontein, Kaapstad' } }]) {
    const quiet = exportCtx(entry, [pub], [other]);
    quiet.Export.bibtex(4209, 0);
    assert.doesNotMatch(quiet.captured[0].content, /contested/);
  }
});

test('the contested note stands only at the edition whose place the claim names', () => {
  // Page 1725 has editions from Sofija and one from Varna; a claim on the
  // Varna assignment is no statement about a Sofija edition.
  const entry = {
    sourcePageId: 1725, entryType: 'historical-study', title: 'Magelan',
    location: 'Sofija', publicationCount: 2, pageKind: 'edition-page',
  };
  const pubs = [
    { id: 'klawiter:publication/1725-1946-a', year: 1946, title: 'Magelan',
      publisher: 'Biser', places: ['Sofija'] },
    { id: 'klawiter:publication/1725-1966-a', year: 1966, title: 'Magelan',
      publisher: 'DPK St. Dobrev-Strandzhata', places: ['Varna'] },
  ];
  const claims = [{ claimId: 'c', entityType: 'location', decisionStatus: 'open',
    subject: { name: 'Varna' } }];
  const { Export, captured } = exportCtx(entry, pubs, claims);
  Export.bibtex(1725, 0);
  Export.bibtex(1725, 1);
  assert.doesNotMatch(captured[0].content, /contested/);
  assert.match(captured[1].content, /Place authority assignment contested/);
});

test('a citation waits for the claims instead of citing a contested place as settled', async () => {
  const entry = { sourcePageId: 4819, entryType: 'secondary-literature',
    title: 'Adam Lux', location: 'Saint-Aignan', year: 1993 };
  const { Export, captured, ctx } = exportCtx(entry, null, []);
  // Nothing loaded yet: the shared loader brings the claims in.
  ctx.Edit.reconciliation = null;
  let loads = 0;
  ctx.App._ensureReconciliation = () => {
    loads++;
    ctx.Edit.reconciliation = {};
    ctx.Edit.authorityClaimsFor = () => [{ claimId: 'c', entityType: 'location',
      decisionStatus: 'open', subject: { name: 'Saint-Aignan' } }];
    return Promise.resolve();
  };
  await Export.bibtex(4819);
  assert.strictEqual(loads, 1);
  assert.match(captured[0].content, /Place authority assignment contested/);

  // The batch export reads them as well, whether or not a card was opened.
  ctx.Edit.reconciliation = null;
  await Export.batchBibtex([entry]);
  assert.strictEqual(loads, 2);
  assert.match(captured[1].content, /Place authority assignment contested/);
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
  // Classic BibTeX styles read the container from `journal` alone.
  assert.match(bib, /\n {2}journal = \{Al-Balāghah waʾl-naqd al-ʿarabī\}/);
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
  // The address names the article, not only the page it is listed on.
  assert.match(ris, /^UR {2}- https:\/\/chpollin\.github\.io\/klawiter-rescue\/#entry=4445&pub=4445-2015-a$/m);
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
  // The RIS specification and Zotero's RIS translator read A4 as the
  // translator. The editor of a book is A3 there, whose A2 Zotero reads as
  // the series editor; the editor of a journal article is A2.
  assert.match(ris, /^A4 {2}- Dimitŭr Stoevski$/m);
  assert.match(ris, /^A3 {2}- N\. Vysotskaia$/m);
  assert.doesNotMatch(ris, /^A2 /m);
  assert.match(ris, /ET {2}- 1st edition/);
  assert.match(ris, /N1 {2}- Extent: 500p\./);

  const article = { ...pub, container: { title: 'Plamŭk', issue: '3', pages: '1-9' } };
  const journal = exportCtx(entry, [article]);
  journal.Export.ris(1800, 0);
  assert.match(journal.captured[0].content, /^TY {2}- JOUR$/m);
  assert.match(journal.captured[0].content, /^A2 {2}- N\. Vysotskaia$/m);
});

test('the translators of contained texts are cited, the other credits by role', () => {
  // Page 1891: the volume credits an editor and an illustrator, its two
  // contributions three translators.
  const entry = {
    sourcePageId: 1891, entryType: 'historical-study', title: 'Mariia Stiuart * Kazanova',
    publicationCount: 1, pageKind: 'single-publication',
  };
  const pub = {
    id: 'klawiter:publication/1891-1993-a', year: 1993, title: 'Mariia Stiuart * Kazanova',
    publisher: 'Kavkazskiĭ Krai', places: ['Stavropol’'],
    extent: { raw: '444/(3)p.', numbered: 444, unnumbered: 3 },
    credits: [
      { role: 'editor', name: 'N. Vysotskaia', creditLabel: 'Edited by' },
      { role: 'illustrator', name: 'I. L. Prostitov', creditLabel: 'Illustrated by' },
    ],
    contributions: [
      { title: 'Mariia Stiuart', pages: '(7)-(370)', credits: [
        { role: 'translator', name: 'R. Gal’perina', creditLabel: 'Translated by' },
        { role: 'translator', name: 'V. Levik', creditLabel: 'Verses translated by' },
      ] },
      { title: 'Kazanova', pages: '(371)-(445)', credits: [
        { role: 'translator', name: 'P. S. Bernshteĭn', creditLabel: 'Translated by' },
      ] },
    ],
  };
  const { Export, captured } = exportCtx(entry, [pub]);
  Export.bibtex(1891, 0);
  const bib = captured[0].content;
  assert.match(bib, /translator = \{R\. Gal’perina and V\. Levik and P\. S\. Bernshteĭn\}/);
  assert.match(bib, /editor = \{N\. Vysotskaia\}/);
  assert.match(bib, /illustrator = \{I\. L\. Prostitov\}/);
  // The wording keeps which text each translator worked on.
  assert.match(bib, /Mariia Stiuart: Translated by R\. Gal’perina, Verses translated by V\. Levik/);
  Export.ris(1891, 0);
  const ris = captured[1].content;
  assert.strictEqual((ris.match(/^A4 {2}- /gm) || []).length, 3);
  assert.match(ris, /^A3 {2}- N\. Vysotskaia$/m);
});

test('the series number is a number, said once, and the note of the source is cited', () => {
  const entry = { sourcePageId: 4445, entryType: 'secondary-literature',
    title: 'Al-Bāḥ, Muḥammad', pageKind: 'author-page', publicationCount: 2 };
  const book = {
    id: 'klawiter:publication/4445-2000-a', year: 2000,
    title: 'Frauen- und Männerbilder in den Novellen von Stefan Zweig',
    publisher: 'Hochschulverl.', places: ['Freiburg im Breisgau'],
    extent: { raw: '168p.', numbered: 168 },
    series: 'Hochschulsammlung Philosophie. Literaturwissenschaft, 16', seriesVolume: '16',
    note: "This volume was originally the author's 1999 PhD thesis",
  };
  const { Export, captured } = exportCtx(entry, [book]);
  Export.bibtex(4445, 0);
  Export.ris(4445, 0);
  const [bib, ris] = captured.map(item => item.content);
  // The series wording already ends with its number, so no field repeats it.
  assert.doesNotMatch(bib, /volume = /);
  assert.doesNotMatch(bib, /\n {2}number = /);
  assert.match(ris, /^T2 {2}- Hochschulsammlung Philosophie\. Literaturwissenschaft, 16$/m);
  assert.doesNotMatch(ris, /^M1 /m);
  assert.doesNotMatch(ris, /Series number/);
  assert.match(bib, /note = \{[^}]*originally the author's 1999 PhD thesis/);
  assert.match(ris, /^N1 {2}- This volume was originally/m);

  const numbered = { ...book, series: 'Biblioteka Zlatni zŭrna', seriesVolume: '8' };
  const other = exportCtx(entry, [numbered]);
  other.Export.bibtex(4445, 0);
  other.Export.ris(4445, 0);
  assert.match(other.captured[0].content, /\n {2}number = \{8\}/);
  assert.doesNotMatch(other.captured[0].content, /volume = /);
  assert.match(other.captured[1].content, /^T2 {2}- Biblioteka Zlatni zŭrna$/m);
  assert.match(other.captured[1].content, /^M1 {2}- 8$/m);
});

test('every publication is cited under an address of its own', () => {
  const { Export, captured } = exportCtx(editionEntry(), editions());
  Export.bibtex(1800);
  const all = captured[0].content;
  for (const slug of ['1800-1947-a', '1800-1960-a']) {
    assert.ok(all.includes(`url = {https://chpollin.github.io/klawiter-rescue/#entry=1800&pub=${slug}}`),
      slug);
  }
});

test('translation and foreword pages are cited under the author the page is indexed by', () => {
  // Page 792: Zweig translated the novel and wrote its afterword and foreword.
  const translation = {
    sourcePageId: 792, entryType: 'translation', pageKind: 'single-publication',
    title: 'Barbusse, Henri', publicationCount: 1, translator: 'Stefan Zweig',
  };
  const translated = {
    id: 'klawiter:publication/792-1932-a', year: 1932,
    title: 'Die Schutzflehenden. Der Roman einer Vorkriegsjugend',
    publisher: 'Rascher Verlag', places: ['Zürich/Leipzig/Stuttgart'],
    extent: { raw: '247p.', numbered: 247 },
    credits: [
      { role: 'translator', name: 'Stefan Zweig', creditLabel: 'Translated with an afterword by' },
      { role: 'translator', name: 'Stefan Zweig', creditLabel: 'Translated with a foreword by' },
    ],
  };
  const bib = exportCtx(translation, [translated]);
  bib.Export.bibtex(792, 0);
  const cited = bib.captured[0].content;
  assert.match(cited, /author = \{Barbusse, Henri\}/);
  // One person credited twice in one role is one translator; both wordings
  // stay in the note.
  assert.match(cited, /translator = \{Stefan Zweig\},/);
  assert.match(cited, /Translated with an afterword by Stefan Zweig; Translated with a foreword by/);
  assert.doesNotMatch(cited, /Contains a translation/);
  bib.captured.length = 0;
  bib.Export.ris(792, 0);
  assert.strictEqual((bib.captured[0].content.match(/^A4 {2}- Stefan Zweig$/gm) || []).length, 1);
  assert.match(bib.captured[0].content, /^AU {2}- Barbusse, Henri$/m);

  // Page 4418: the qualifier after " / " (a language) is not part of the name,
  // and Zweig's preface stays a contributor credit.
  const foreword = {
    sourcePageId: 4418, entryType: 'foreword', pageKind: 'single-publication',
    title: 'Relgis, Eugen / French', publicationCount: 1,
  };
  const prefaced = {
    id: 'klawiter:publication/4418-1939-a', year: 1939,
    title: 'Miron-le-sourd. Voix en sourdine. Roman', publisher: 'G. Mignolet Éditeur',
    places: ['Paris'], extent: { raw: '222p.', numbered: 222 },
    credits: [
      { role: 'translator', name: 'S. Pavès', creditLabel: 'Translated by' },
      { role: 'contributor', name: 'Stefan Zweig', creditLabel: 'Preface by' },
    ],
  };
  const fw = exportCtx(foreword, [prefaced]);
  fw.Export.bibtex(4418, 0);
  assert.match(fw.captured[0].content, /author = \{Relgis, Eugen\}/);
  assert.match(fw.captured[0].content, /Preface by Stefan Zweig/);

  // Without a credit naming Zweig, the page's section keeps his part visible.
  const flat = exportCtx({
    sourcePageId: 6446, entryType: 'foreword', title: 'Dickens, Charles / Ausgewählte Romane und Novellen',
    translator: 'Leo Feld and Erwin Krauss', year: 1910,
  }, null);
  flat.Export.bibtex(6446);
  assert.match(flat.captured[0].content, /author = \{Dickens, Charles\}/);
  assert.match(flat.captured[0].content, /note = \{Translated by Leo Feld and Erwin Krauss; Contains a foreword or afterword by Stefan Zweig\}/);
});

test('collected works stay Zweig\'s, reception pages carry no author', () => {
  const collected = exportCtx({
    sourcePageId: 12, entryType: 'collected-works',
    title: 'Das Geheimnis des künstlerischen Schaffens. Essays', year: 1984,
  }, null);
  collected.Export.bibtex(12);
  assert.match(collected.captured[0].content, /author = \{Zweig, Stefan\}/);

  const reception = exportCtx({
    sourcePageId: 1435, entryType: 'secondary-literature',
    title: 'Stefan Zweig 1881-1981. Aufsätze und Dokumente', year: 1981,
  }, null);
  reception.Export.bibtex(1435);
  assert.doesNotMatch(reception.captured[0].content, /author = /);
  assert.match(reception.captured[0].content, /keywords = \{Stefan Zweig\}/);
});

test('a page title without the form of a name is no author', () => {
  const { Export } = exportCtx({ sourcePageId: 1, entryType: 'fiction' }, null);
  const author = title => Export._author({ entryType: 'secondary-literature', pageKind: 'author-page', title });
  // Pages 2530, 1973 and 6840: a list marker, a heading and a book title.
  assert.strictEqual(author('[1]'), '');
  assert.strictEqual(author('Essays:'), '');
  assert.strictEqual(author("Stefan Zweig. L'Esprit européen en exil"), '');
  // Several people in shorthand do not split into names reliably.
  assert.strictEqual(author('Mann, Erika and Klaus'), '');
  assert.strictEqual(author('Finkenzeller, Roswin; Ziehr, Wilhelm; Bührer, Emil M.'), '');
  // Particles, apostrophes, parentheses and transliteration marks are names.
  assert.strictEqual(author("'Abbūd, 'Abduh / Abboud, Abdo"), "'Abbūd, 'Abduh");
  assert.strictEqual(author('Djevdet (Cevdet), Abdullah'), 'Djevdet (Cevdet), Abdullah');
  assert.strictEqual(author('Al-ʿUnayzī, Shawqī'), 'Al-ʿUnayzī, Shawqī');
  assert.strictEqual(author('Camões, Luís Vaz de'), 'Camões, Luís Vaz de');
  // A translation page titled by a periodical citation names nobody either.
  assert.strictEqual(Export._author({ entryType: 'translation',
    title: '"Juninacht" in Deutsche Dichtung [Berlin], 31 [March 1902], p. 254' }), '');
});

test('a publication that names its own author is cited under that author', () => {
  // Page 4916: the German graphic novel of 2016 on the Schachnovelle page, a
  // work of its own since the decision of 2026-09-22.
  const entry = {
    sourcePageId: 4916, entryType: 'fiction', pageKind: 'edition-page',
    title: 'Schachnovelle / Volume', publicationCount: 25,
  };
  const graphicNovel = {
    id: 'klawiter:publication/4916-2016-b', year: 2016,
    title: 'Die Schachnovelle nach Stefan Zweig', publisher: 'Knesebeck GmbH & Co. Verlag',
    places: ['München'], language: 'German', extent: { raw: '120p.', numbered: 120 },
    credits: [
      { role: 'author', name: 'Thomas Humeau', creditLabel: 'A graphic novel by' },
      { role: 'translator', name: 'Anja Kootz', creditLabel: 'adapted into German by' },
    ],
  };
  const { Export, captured } = exportCtx(entry, [graphicNovel]);
  Export.bibtex(4916, 0);
  const bib = captured[0].content;
  assert.match(bib, /author = \{Thomas Humeau\}/);
  assert.doesNotMatch(bib, /Zweig, Stefan/);
  assert.match(bib, /translator = \{Anja Kootz\}/);
  assert.doesNotMatch(bib, /series = /);
  captured.length = 0;
  Export.ris(4916, 0);
  assert.match(captured[0].content, /^AU {2}- Thomas Humeau$/m);
  assert.match(captured[0].content, /^A4 {2}- Anja Kootz$/m);
});

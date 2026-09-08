/**
 * Pins the entry card as a review form (docs/js/app.js, docs/js/detail.js).
 *
 * The permalink route #entry=<pid> shows exactly one entry, so the card there
 * is read as a record to check rather than as a hit to scan: the head carries
 * type and title, every value stands once and named in the field block, and
 * the Klawiter source stays open underneath as the authority the fields were
 * structured from. In a result list the head keeps the facet triade that
 * carries the filter logic and the source stays collapsed.
 */
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function read(file) {
  return fs.readFileSync(path.join(__dirname, '..', 'docs', 'js', file), 'utf8');
}

/** The Edit surface the card calls, with the case under test on top. */
function editStub(overrides = {}) {
  return Object.assign({
    FIELD_LABELS: {},
    pending: () => undefined,
    entryStatus: () => ({ status: 'unreviewed', pending: false }),
    triageHints: () => [],
    evidence: () => null,
    editionClaimsFor: () => [],
    authorityClaimsFor: () => [],
    locationReconciliation: () => null,
    agentReconciliation: () => null,
  }, overrides);
}

/** Detail with the globals it reads from the shared browser scope. */
function detailCtx(entry, state = {}, extra = {}) {
  const ctx = Object.assign({
    console,
    document: { querySelectorAll: () => [], addEventListener() {}, getElementById: () => null },
    App: {
      state: Object.assign({ editMode: false, singleEntry: false, query: '' }, state),
      entries: [entry],
      entryMap: new Map([[entry.sourcePageId, entry]]),
      titleMap: new Map(),
      data: { redirects: {} },
    },
    Edit: editStub(),
  }, extra);
  vm.createContext(ctx);
  for (const file of ['constants.js', 'utils.js', 'detail.js']) vm.runInContext(read(file), ctx);
  return vm.runInContext('Detail', ctx);
}

/** App with the stubs the render path needs, plus constants and utils. */
function appCtx() {
  const location = { hash: '', pathname: '/', hostname: 'localhost' };
  const elements = {};
  const ctx = {
    console,
    URLSearchParams,
    setTimeout: () => 0,
    window: { location, addEventListener() {} },
    location,
    history: { replaceState() {}, pushState() {} },
    elements,
    document: {
      addEventListener() {},
      getElementById(id) {
        if (!elements[id]) {
          elements[id] = { textContent: '', innerHTML: '', style: {},
            classList: { add() {}, remove() {}, toggle() {} } };
        }
        return elements[id];
      },
      querySelectorAll() { return []; },
    },
    // The head reads the review state through Detail, so the real module
    // answers here rather than a second copy of its rules.
    Edit: { entryStatus: () => ({ status: 'unreviewed', pending: false }), pending: () => undefined },
  };
  vm.createContext(ctx);
  for (const file of ['constants.js', 'utils.js', 'detail.js']) vm.runInContext(read(file), ctx);
  const App = vm.runInContext(read('app.js') + '\nApp', ctx);
  return { App, ctx };
}

/** One page carrying a single publication, in the shape the projection has. */
function sampleEntry() {
  return {
    sourcePageId: 1800,
    sourceTextId: 38039,
    sourceBlobId: 4,
    entryType: 'historical-study',
    title: 'Romanŭt na edin zhivot. Balzak',
    year: 1947,
    language: 'Bulgarian',
    languageCode: 'bg',
    location: 'Sofija',
    locationSameAs: 'http://www.wikidata.org/entity/Q472',
    publisher: 'Pechat Far',
    pageCount: 500,
    translator: 'Dimitŭr Stoevski',
    categories: ['Historical Studies / Volumes (Bulgarian)'],
    fullBibliographicEntry: '[1947]: Pechat Far, Sofija\n\nTranslated by Dimitŭr Stoevski. '
      + '1st edition. 500p. Illustrated.',
    review: { status: 'agent_verified', fields: { location: 'confirm' } },
    _provenance: { publisher: 'regex', location: 'regex', translator: 'regex', pageCount: 'regex' },
  };
}

test('the permalink route opens the source, a result list leaves it collapsed', () => {
  const entry = sampleEntry();
  const open = detailCtx(entry, { singleEntry: true })._buildReadContent(entry);
  assert.match(open, /<details class="detail-source-details" open>/);

  const listed = detailCtx(entry, { singleEntry: false })._buildReadContent(entry);
  assert.match(listed, /<details class="detail-source-details">/);
});

test('the entry route sets the single-entry state, a result list clears it', () => {
  const { App, ctx } = appCtx();
  const entry = sampleEntry();
  App.entries = [entry];
  App.entryMap = new Map([[1800, entry]]);
  App.filtered = [];
  App.showView = (v) => { App.state.view = v; };
  App.renderChips = () => {};
  App.sortEntries = () => {};
  App.applySortFromParams = () => {};
  ctx.Facets = { render() {} };

  App._lastHash = null;
  ctx.location.hash = '#entry=1800';
  App.handleRoute();
  assert.strictEqual(App.state.singleEntry, true);

  App._lastHash = null;
  ctx.location.hash = '#browse';
  App.handleRoute();
  assert.strictEqual(App.state.singleEntry, false);
});

test('the single-entry head carries type and title, the list head the facet triade', () => {
  const { App } = appCtx();
  const entry = sampleEntry();

  App.state.singleEntry = true;
  const single = App.renderCard(entry);
  assert.match(single, /class="badge"/, 'the entry type stays in the head');
  assert.match(single, /Romanŭt na edin zhivot/);
  assert.doesNotMatch(single, /card-meta-text/, 'no unlabelled year, language or place');
  assert.doesNotMatch(single, /card-secondary/, 'no generated head sentence');
  // The review state belongs to the record, and it stands in the head line.
  assert.match(single, /review-chip/);
  assert.match(single, /Agent-verified/);

  App.state.singleEntry = false;
  const listed = App.renderCard(entry);
  assert.match(listed, /card-meta-text/, 'the facet triade carries the filter logic in a list');
  assert.match(listed, /card-secondary/);
});

test('the field block names every value it shows', () => {
  const entry = sampleEntry();
  const html = detailCtx(entry, { singleEntry: true })._buildReadContent(entry);

  for (const label of ['Year of publication', 'Language', 'Place of publication',
    'Publisher', 'Translator', 'Categories']) {
    assert.match(html, new RegExp(`>${label}`), `${label} is named`);
  }
  assert.match(html, /Extent/);
  // Each value once in the block, and once more only in the quoted source.
  assert.strictEqual((html.match(/Pechat Far/g) || []).length, 2);
  assert.strictEqual((html.match(/1947/g) || []).length, 2);
  // The place keeps its name; the authority link is an addition, not the value.
  assert.match(html, /Place of publication[\s\S]*?Sofija/);
  assert.doesNotMatch(html, /Sofija on Wikidata/);
  assert.match(html, /wikidata-link[^>]*>Wikidata</);
});

test('the extent quotes the source notation and keeps the numbered extent beside it', () => {
  const entry = sampleEntry();
  entry.pageCount = 444;
  entry.fullBibliographicEntry = 'Edited by N. Vysotskaia. 444/(3)p. [Istoricheskie romani]';
  const html = detailCtx(entry)._buildReadContent(entry);
  assert.match(html, /444\/\(3\)p\./, 'the source notation is the value');
  assert.match(html, /Extent \(as in source\)/);

  // Without a derivable notation the record's numbered extent stands alone.
  const plain = sampleEntry();
  plain.pageCount = 168;
  plain.fullBibliographicEntry = 'A source text without an extent token.';
  const plainHtml = detailCtx(plain)._buildReadContent(plain);
  assert.match(plainHtml, /Extent \(numbered\)/);
  assert.match(plainHtml, />168 pp\.</);
});

test('a field the provenance layer calls missing is shown as such, never as a placeholder', () => {
  const entry = sampleEntry();
  delete entry.translator;
  entry._provenance.translator = 'missing';
  const html = detailCtx(entry)._buildReadContent(entry);
  assert.match(html, /Translator/);
  assert.match(html, /prov-missing/);
  assert.match(html, /Not recorded/);
  assert.doesNotMatch(html, /add value|unknown translator/i);
});

test('the per-field review mark follows the review object and nothing else', () => {
  const entry = sampleEntry();
  const html = detailCtx(entry)._buildReadContent(entry);
  assert.match(html, /Place of publication[\s\S]*?field-review-confirm[^>]*>confirmed</);
  // Only the location is decided in this record, so no other field claims one.
  assert.strictEqual((html.match(/field-review-/g) || []).length, 1);
});

test('the source identifiers stand at the source block, not in a card foot', () => {
  const entry = sampleEntry();
  const html = detailCtx(entry, { singleEntry: true })._buildReadContent(entry);
  const start = html.indexOf('<details class="detail-source-details"');
  const source = html.slice(start, html.indexOf('</details>', start));
  assert.match(source, /Page ID: 1800/);
  assert.match(source, /Text ID: 38039/);
  assert.match(source, /Blob: 4/);
  assert.strictEqual((html.match(/Page ID/g) || []).length, 1);
});

test('an address in the source text stays reachable', () => {
  const entry = sampleEntry();
  entry.fullBibliographicEntry =
    'Published online: http://platform.almanhal.com/Article/Preview.aspx?ID=60445';
  const html = detailCtx(entry)._buildReadContent(entry);
  assert.match(html, /<a href="http:\/\/platform\.almanhal\.com\/Article\/Preview\.aspx\?ID=60445"/);
});

test('a page carrying several publications says so instead of implying one', () => {
  const entry = sampleEntry();
  entry.allYears = [1947, 1960];
  const html = detailCtx(entry, { singleEntry: true })._buildReadContent(entry);
  assert.match(html, /more than one publication/);

  const single = detailCtx(sampleEntry(), { singleEntry: true })._buildReadContent(sampleEntry());
  assert.doesNotMatch(single, /more than one publication/);
});

// --- Publication layer ------------------------------------------------------
// The record carries one entry per publication of the source page, so the card
// stops joining the imprint of one publication to the language of another.

/** Page 1800 in the shape of the publication contract: two editions. */
function editionPage() {
  const entry = sampleEntry();
  entry.pageKind = 'edition-page';
  entry.publicationCount = 2;
  entry.publicationYears = [1947, 1960];
  entry.publications = [
    {
      id: 'klawiter:publication/1800-1947-a',
      year: 1947, yearRaw: '1947',
      title: 'Romanŭt na edin zhivot. Balzak',
      publisher: 'Pechat Far',
      places: ['Sofija'],
      language: 'Bulgarian', languageCode: 'bg',
      editionStatement: '1st edition',
      extent: { raw: '500p.', numbered: 500 },
      series: 'Biblioteka Zlatni zŭrna. Godina XII, premiia',
      credits: [{ role: 'translator', name: 'Dimitŭr Stoevski', creditLabel: 'Translated by' }],
      sourceSlice: { start: 0, end: 60, sha256: 'a' },
      provenance: { publisher: 'regex', extent: 'regex' },
    },
    {
      id: 'klawiter:publication/1800-1960-a',
      year: 1960, yearRaw: '1960',
      title: 'Romanŭt na edin zhivot. Balzak',
      publisher: 'Narodna Kultura',
      places: ['Sofija'],
      language: 'Bulgarian', languageCode: 'bg',
      editionStatement: '2nd revised edition',
      extent: { raw: '383/(1)p.', numbered: 383, unnumbered: 1 },
      credits: [{ role: 'translator', name: 'Dimitŭr Stoevski', creditLabel: 'Translated by' }],
      sourceSlice: { start: 60, end: 120, sha256: 'b' },
      provenance: { publisher: 'regex' },
    },
  ];
  entry.nameVariants = [];
  return entry;
}

/** Page 1891: one publication whose contributions carry their own credits. */
function contributionPage() {
  const entry = sampleEntry();
  entry.sourcePageId = 1891;
  entry.title = 'Mariia Stiuart * Kazanova';
  entry.pageKind = 'single-publication';
  entry.publicationCount = 1;
  entry.publications = [{
    id: 'klawiter:publication/1891-1993-a',
    year: 1993, yearRaw: '1993',
    title: 'Mariia Stiuart * Kazanova',
    publisher: 'Kavkazskiĭ Krai',
    places: ['Stavropol’'],
    language: 'Russian', languageCode: 'ru',
    extent: { raw: '444/(3)p.', numbered: 444, unnumbered: 3 },
    credits: [
      { role: 'editor', name: 'N. Vysotskaia', creditLabel: 'Edited by' },
      { role: 'illustrator', name: 'I. L. Prostitov', creditLabel: 'Illustrated by' },
    ],
    contributions: [
      {
        title: 'Mariia Stiuart', pages: '(7)-(370)',
        credits: [
          { role: 'translator', name: 'R. Gal’perina', creditLabel: 'Translated by' },
          { role: 'translator', name: 'V. Levik', creditLabel: 'Verses translated by' },
        ],
      },
      {
        title: 'Kazanova', pages: '(371)-(445)',
        credits: [{ role: 'translator', name: 'P. S. Bernshteĭn', creditLabel: 'Translated by' }],
      },
    ],
    reviewFlags: [{
      code: 'contents-pagination-exceeds-extent',
      detail: 'The contents end at page 445, the stated numbered extent is 444.',
    }],
    provenance: { extent: 'regex' },
  }];
  return entry;
}

test('a page with publications renders one named block per publication', () => {
  const entry = editionPage();
  const html = detailCtx(entry, { singleEntry: true })._buildReadContent(entry);

  assert.match(html, /1947 · 1st edition/);
  assert.match(html, /1960 · 2nd revised edition/);
  assert.match(html, />Pechat Far</);
  assert.match(html, />Narodna Kultura</);
  // Each publication keeps its own extent in the notation of the source.
  assert.match(html, /500p\./);
  assert.match(html, /383\/\(1\)p\./);
  assert.match(html, /383 numbered, 1 unnumbered/);
  // The first-match caution belongs to the flat projection and is gone here.
  assert.doesNotMatch(html, /first match in the source text/);
});

test('credits name their role, and a contribution keeps its own credits', () => {
  const entry = contributionPage();
  const html = detailCtx(entry, { singleEntry: true })._buildReadContent(entry);

  assert.match(html, /Editor[\s\S]*?N\. Vysotskaia/);
  assert.match(html, /Illustrator[\s\S]*?I\. L\. Prostitov/);
  // The verse translator belongs to the Maria Stuart contribution, not to the
  // publication, and the scalar translator field cannot say that.
  const contents = html.slice(html.indexOf('Mariia Stiuart</span>'));
  const maria = contents.slice(0, contents.indexOf('Kazanova</span>'));
  assert.match(maria, /V\. Levik/);
  assert.doesNotMatch(contents.slice(contents.indexOf('Kazanova</span>')), /V\. Levik/);
});

test('a credit phrase beyond the plain role is visible, not only in the tooltip', () => {
  const entry = contributionPage();
  const html = detailCtx(entry, { singleEntry: true })._buildReadContent(entry);

  // "Verses translated by" says more than the role Translator, so what it
  // adds stands after the name and the whole phrase stays in the tooltip.
  assert.match(html, /V\. Levik<\/span> <span class="field-sub">\(verses\)<\/span>/);
  assert.match(html, /title="Verses translated by"/);
  // "Translated by" adds nothing to the role, so nothing is repeated there.
  assert.doesNotMatch(html, /Gal’perina<\/span> <span class="field-sub">/);
  assert.doesNotMatch(html, /\(translated\)/);
});

test('a review flag reads as a hint in plain words', () => {
  const entry = contributionPage();
  const html = detailCtx(entry, { singleEntry: true })._buildReadContent(entry);
  assert.match(html, /review-flag/);
  assert.match(html, /The contents end at page 445, the stated numbered extent is 444\./);
});

test('name variants stand as a block of their own without asserting identity', () => {
  const entry = sampleEntry();
  entry.pageKind = 'single-publication';
  entry.publicationCount = 1;
  entry.publications = [{ id: 'p', year: 1947, publisher: 'Nasionale Pers Beperk',
    places: ['Bloemfontein', 'Kaapstad (Capetown)'], provenance: {} }];
  entry.nameVariants = [{
    name: 'Hymme Weiss', variantOf: 'Hymne Weiss', status: 'unresolved',
    sourceContext: 'Voorwoord [Hymme Weiss, Pretoria, 25 January, 1944], p. (5)',
  }];
  const html = detailCtx(entry, { singleEntry: true })._buildReadContent(entry);
  assert.match(html, /Name variants in source/);
  assert.match(html, /Hymme Weiss/);
  assert.match(html, /Hymne Weiss/);
  assert.match(html, /unresolved/);
  // Both places of the imprint survive, which the flat single place could not.
  assert.match(html, /Bloemfontein, Kaapstad \(Capetown\)/);
});

test('a contested place is marked at the value and leads to its claim', () => {
  const claim = {
    claimId: 'klawiter:claim/reconciliation/location/e5742c35',
    entityType: 'location',
    subject: { name: 'Bloemfontein, Kaapstad' },
    interpretations: [], sourceEvidence: [], reviewHistory: [],
  };
  const entry = sampleEntry();
  entry.pageKind = 'single-publication';
  entry.publicationCount = 1;
  entry.publications = [{ id: 'p', year: 1947, publisher: 'Nasionale Pers Beperk',
    places: ['Bloemfontein', 'Kaapstad (Capetown)'], provenance: {} }];
  const html = detailCtx(entry, { singleEntry: true },
    { Edit: editStub({ authorityClaimsFor: () => [claim] }) })._buildReadContent(entry);

  const anchor = 'claim-1800-klawiter-claim-reconciliation-location-e5742c35';
  assert.match(html, new RegExp(`class="contested-mark"[\\s\\S]*?href="#${anchor}"`));
  assert.match(html, new RegExp(`id="${anchor}"`), 'the claim block answers to that address');

  // The claim names two places of this imprint; a page whose place it does
  // not name carries no mark.
  const other = sampleEntry();
  const otherHtml = detailCtx(other, { singleEntry: true },
    { Edit: editStub({ authorityClaimsFor: () => [claim] }) })._buildReadContent(other);
  assert.match(otherHtml, /Place of publication[\s\S]*?Sofija/);
  assert.doesNotMatch(otherHtml, /contested-mark/);
});

test('a page file is fetched when the record carries no inline publications', async () => {
  const entry = sampleEntry();
  entry.pageKind = 'edition-page';
  entry.publicationCount = 2;
  const calls = [];
  const doc = {
    publications: [
      { id: 'a', year: 1947, publisher: 'Pechat Far', places: ['Sofija'], provenance: {} },
      { id: 'b', year: 1960, publisher: 'Narodna Kultura', places: ['Sofija'], provenance: {} },
    ],
    nameVariants: [],
  };
  const Detail = detailCtx(entry, { singleEntry: true }, {
    fetch: (url) => {
      calls.push(url);
      return Promise.resolve({ ok: true, json: () => Promise.resolve(doc) });
    },
  });

  const first = Detail._buildReadContent(entry);
  assert.match(first, /field-loading/, 'the load is visible while it runs');
  assert.deepStrictEqual(calls, ['data/publications/1800.json']);

  await Detail._pubCache.get(1800).promise;
  const second = Detail._buildReadContent(entry);
  assert.match(second, />Narodna Kultura</);
  assert.doesNotMatch(second, /field-loading/);
  assert.strictEqual(calls.length, 1, 'one page file per page and session');
});

test('a failed page file leaves the card standing on the flat fields', async () => {
  const entry = sampleEntry();
  entry.pageKind = 'edition-page';
  entry.publicationCount = 2;
  const Detail = detailCtx(entry, { singleEntry: true }, {
    fetch: () => Promise.resolve({ ok: false, status: 404 }),
  });

  Detail._buildReadContent(entry);
  await Detail._pubCache.get(1800).promise;
  const html = Detail._buildReadContent(entry);
  assert.match(html, /field-error/);
  assert.match(html, /404/);
  // The flat projection still carries the card: no crash, no empty card.
  assert.match(html, /Year of publication/);
  assert.match(html, /Full bibliographic entry/);
});

test('the head names the page kind and counts its publications', () => {
  const { App } = appCtx();
  App.state.singleEntry = true;

  const author = sampleEntry();
  author.pageKind = 'author-page';
  author.publicationCount = 2;
  const authorHtml = App.renderCard(author);
  assert.match(authorHtml, /Author page, 2 publications/);
  assert.match(authorHtml, /card-title-label/, 'the title of an author page is an author name');

  const edition = sampleEntry();
  edition.pageKind = 'edition-page';
  edition.publicationCount = 2;
  assert.match(App.renderCard(edition), /Edition page, 2 editions/);

  const single = sampleEntry();
  single.pageKind = 'single-publication';
  single.publicationCount = 1;
  const singleHtml = App.renderCard(single);
  assert.doesNotMatch(singleHtml, /Edition page|Author page/);
  assert.doesNotMatch(singleHtml, /card-title-label/);
});

test('a result list replaces the triade of a multi-publication page with its count', () => {
  const { App } = appCtx();
  App.state.singleEntry = false;

  const edition = sampleEntry();
  edition.pageKind = 'edition-page';
  edition.publicationCount = 2;
  const html = App.renderCard(edition);
  assert.match(html, />2 editions</);
  assert.doesNotMatch(html, />1947</, 'no triade that describes no publication');
  assert.doesNotMatch(html, /card-secondary/);

  const single = sampleEntry();
  single.pageKind = 'single-publication';
  single.publicationCount = 1;
  const singleHtml = App.renderCard(single);
  assert.match(singleHtml, /card-meta-text/);
  assert.match(singleHtml, /card-secondary/);
});

test('the source text marks the block a publication was read from', () => {
  const entry = editionPage();
  const text = entry.fullBibliographicEntry;
  entry.publications[0].sourceSlice = { start: 0, end: 60, textStart: 0, textEnd: 26 };
  entry.publications[1].sourceSlice = { start: 60, end: 120, textStart: 26, textEnd: text.length };
  const html = detailCtx(entry, { singleEntry: true })._buildReadContent(entry);
  assert.strictEqual((html.match(/class="source-slice"/g) || []).length, 2);

  // Offsets into the raw source rather than into the shipped text would mark
  // the wrong passage, so a slice without the text offsets marks nothing.
  const plain = editionPage();
  const plainHtml = detailCtx(plain, { singleEntry: true })._buildReadContent(plain);
  assert.doesNotMatch(plainHtml, /source-slice/);
});

test('per-publication citation buttons appear only where there are several', () => {
  const several = detailCtx(editionPage(), { singleEntry: true })
    ._buildReadContent(editionPage());
  assert.strictEqual((several.match(/publication-actions/g) || []).length, 2);
  assert.match(several, /data-export="bibtex" data-pid="1800" data-index="1"/);
  assert.match(several, /Cite all \(BibTeX\)/, 'the page bar says what it collects');

  const one = contributionPage();
  const oneHtml = detailCtx(one, { singleEntry: true })._buildReadContent(one);
  assert.doesNotMatch(oneHtml, /publication-actions/);
  assert.match(oneHtml, /Cite \(BibTeX\)/);
});

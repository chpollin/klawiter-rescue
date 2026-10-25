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
    // The rule itself is pinned in edit_session.test.js; here it only has to
    // follow the claims the case supplies.
    openClaimOnValue(entry, value) {
      return this.authorityClaimsFor(entry).find(claim => claim.decisionStatus !== 'decided'
        && claim.subject && claim.subject.name === value) || null;
    },
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
  for (const file of ['constants.js', 'utils.js', 'record-card.js', 'detail.js']) vm.runInContext(read(file), ctx);
  return vm.runInContext('Detail', ctx);
}

/**
 * The markup of the values at rest: each value's producer button and its
 * empty chain panel taken out (record_card.test.js pins both), so a pin
 * reads the values, their wrappers and their marks.
 */
function atRest(html) {
  return html
    .replace(/<button type="button" class="prov-badge[^"]*"[^>]*>[\s\S]*?<\/button>/g, '')
    .replace(/<div class="rc-chain"[^>]*><\/div>/g, '');
}

/** App with the stubs the render path needs, plus constants and utils. */
function appCtx() {
  const location = { hash: '', pathname: '/', hostname: 'localhost' };
  // A redirect replaces the history entry; the stub lands where it points.
  location.replace = (url) => { location.hash = url; };
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
  for (const file of ['constants.js', 'utils.js', 'record-card.js', 'detail.js']) vm.runInContext(read(file), ctx);
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
    review: { status: 'proposed', reviewed_by: 'independent-verification-agent',
      producer: 'llm-agent',
      basis: 'proposed by LLM agents, source occurrence checked, no person',
      fields: { location: 'confirm' }, fieldStates: { location: 'proposed' } },
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
  ctx.location.hash = '#records';
  App.handleRoute();
  assert.strictEqual(App.state.singleEntry, false);
});

test('the single-entry head carries type and title, the list head the facet triade', () => {
  const { App } = appCtx();
  const entry = sampleEntry();

  App.state.singleEntry = true;
  const single = App.renderCard(entry);
  // The head is the shared one of record-card.js: the identifier is the
  // permalink, the type the one type badge.
  assert.match(single, /<a class="rc-id" href="#entry=1800">klawiter:entry\/1800<\/a>/);
  assert.match(single, /<span class="badge rc-type">Historical Studies<\/span>/, 'the entry type stays in the head');
  assert.strictEqual((single.match(/class="badge/g) || []).length, 1, 'the type stands once');
  assert.match(single, /<h2 class="rc-title" id="head-title-1800" lang="bg-Latn" dir="auto">/);
  assert.match(single, /data-provenance-for="title">Romanŭt na edin zhivot\. Balzak<button type="button" class="prov-badge/);
  assert.doesNotMatch(single, /card-meta-text/, 'no unlabelled year, language or place');
  assert.doesNotMatch(single, /card-secondary/, 'no generated head sentence');
  // The review state belongs to the record, and it stands in the head line
  // naming what the decision covers and who made it: the place authority,
  // nothing else, proposed by agents.
  assert.match(single, /<span class="rc-review">Place authority proposed, by LLM agents, source occurrence checked, no person<\/span>/);
  // The open head holds a link and buttons, so it is no button itself.
  const header = single.slice(single.indexOf('<div class="card-header'));
  const tag = header.slice(0, header.indexOf('>') + 1);
  assert.doesNotMatch(tag, /role="button"|aria-expanded/);
  assert.match(tag, /role="group"\s+aria-labelledby="head-title-1800"/);
  assert.doesNotMatch(header.slice(0, header.indexOf('<div class="card-nav')), /role="button"/);

  App.state.singleEntry = false;
  const listed = App.renderCard(entry);
  assert.match(listed, /card-meta-text/, 'the facet triade carries the filter logic in a list');
  assert.match(listed, /card-secondary/);
  // A closed result is the button that opens it, and holds no control.
  const closed = listed.slice(listed.indexOf('<div class="card-header'), listed.indexOf('<div class="card-nav'));
  assert.match(closed, /role="button" aria-expanded="false"\s+aria-controls="card-detail-1800"/);
  assert.doesNotMatch(closed, /<button|<a /);
  assert.doesNotMatch(closed, /data-provenance-for/, 'no marker without its chain');
  // Its card closes through a button of its own, shown while it is open.
  assert.match(listed, /data-act="card-close" hidden>Close</);
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
  // The state says it; a badge beside "Not recorded" repeated it.
  assert.match(html, /Not recorded/);
  assert.doesNotMatch(html, /prov-missing/);
  assert.doesNotMatch(html, /add value|unknown translator/i);
});

test('the per-field review mark follows the review object and nothing else', () => {
  const entry = sampleEntry();
  const html = detailCtx(entry)._buildReadContent(entry);
  assert.match(html, /Place of publication[\s\S]*?field-review-confirm">[^]*?<\/span>link proposed</);
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

  assert.match(html, /1947, 1st edition/);
  assert.match(html, /1960, 2nd revised edition/);
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
  assert.match(atRest(html), /Bloemfontein<\/span>, <span class="rc-value">Kaapstad \(Capetown\)<\/span>/);
});

test('a contested place is marked at the value it names and leads to its claim', () => {
  const claim = {
    claimId: 'klawiter:claim/reconciliation/location/e5742c35',
    entityType: 'location',
    decisionStatus: 'open',
    subject: { name: 'Kaapstad (Capetown)' },
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
  // The mark follows the value it contests, not the list of the imprint.
  assert.match(atRest(html), new RegExp(
    `Bloemfontein</span>, <span class="rc-value">Kaapstad \\(Capetown\\) <a class="contested-mark"[\\s\\S]*?href="#${anchor}"`));
  assert.match(html, new RegExp(`id="${anchor}"`), 'the claim block answers to that address');

  // A compound subject names no single value, so it marks none; its block
  // still stands on the page that carries it (page 4209).
  const compound = { ...claim, subject: { name: 'Bloemfontein, Kaapstad' } };
  const compoundHtml = detailCtx(entry, { singleEntry: true },
    { Edit: editStub({ authorityClaimsFor: () => [compound] }) })._buildReadContent(entry);
  assert.doesNotMatch(compoundHtml, /contested-mark/);
  assert.match(compoundHtml, /Contested place assignment, decision open/);

  // A page whose place the claim does not name carries no mark.
  const other = sampleEntry();
  const otherHtml = detailCtx(other, { singleEntry: true },
    { Edit: editStub({ authorityClaimsFor: () => [claim] }) })._buildReadContent(other);
  assert.match(otherHtml, /Place of publication[\s\S]*?Sofija/);
  assert.doesNotMatch(otherHtml, /contested-mark/);
});

test('a page with an open claim does not read as plainly unreviewed', () => {
  const entry = sampleEntry();
  delete entry.review;
  const claim = { claimId: 'c', entityType: 'location', decisionStatus: 'open',
    subject: { name: 'Bloemfontein, Kaapstad' } };
  const Detail = detailCtx(entry, {}, { Edit: editStub({ authorityClaimsFor: () => [claim] }) });
  assert.match(Detail._reviewChip(entry),
    /class="review-claim-note">Open place claim<\/span><\/span>$/);
  const quiet = detailCtx(entry, {}, { Edit: editStub() });
  // Unreviewed is the default the result list states once, so it is no chip.
  assert.strictEqual(quiet._reviewChip(entry), '');
});

test('the place decision and its authority link stand at the decided value alone', () => {
  // Page 3324 lists fourteen places; its decision concerns Wien.
  const entry = sampleEntry();
  entry.location = 'Wien';
  entry.locationSameAs = 'http://www.wikidata.org/entity/Q1741';
  entry.allLocations = ['Wien', 'Basel', 'Tokyo'];
  const html = detailCtx(entry)._buildReadContent(entry);
  assert.match(atRest(html), /Wien <a class="wikidata-link"[\s\S]*?Wikidata<\/a> <span class="field-review field-review-confirm">[^]*?link proposed<\/span><span class="decision-producer">, [^]*?LLM agents, source occurrence checked, no person<\/span><\/span>, <span class="rc-value">Basel<\/span>, <span class="rc-value">Tokyo</);
  assert.doesNotMatch(html, /Place of publication<span class="field-review/);

  // A publication row reads the same decision (its field is `places`, the
  // decision's is `location`) wherever it shows the decided value.
  const pages = editionPage();
  const pubHtml = detailCtx(pages, { singleEntry: true })._buildReadContent(pages);
  assert.strictEqual((pubHtml.match(/field-review-confirm/g) || []).length, 2);
});

test('a page-level review flag stands at the field it names', () => {
  // Page 428: the translator value was restored from misread UTF-8 bytes.
  const flag = { code: 'encoding-repaired', field: 'translator',
    detail: 'The enrichment value reached the cache as a misreading of UTF-8 bytes.' };
  const flat = sampleEntry();
  flat.reviewFlags = [flag];
  const html = detailCtx(flat)._buildReadContent(flat);
  assert.match(atRest(html), />Translator[\s\S]*?Dimitŭr Stoevski<\/span><\/div><\/div><p class="review-flag"[\s\S]*?misreading of UTF-8 bytes/);

  const layered = contributionPage();
  layered.translator = 'V. Levik';
  layered.reviewFlags = [flag];
  const layeredHtml = detailCtx(layered, { singleEntry: true })._buildReadContent(layered);
  // With the publication layer it stands under the Credits row of the
  // publication that credits the flagged name, not in the page fields.
  const start = layeredHtml.indexOf('<section class="detail-section publication');
  const block = layeredHtml.slice(start);
  assert.match(block, /Credits<\/div>[\s\S]*?<p class="review-flag"[^>]*>[\s\S]*?misreading of UTF-8 bytes[\s\S]*?Contents<\/div>/);
  assert.doesNotMatch(layeredHtml.slice(0, start), /misreading/);
});

test('a publication names whether its edition is confirmed or proposed', () => {
  const entry = editionPage();
  entry.publications[0].reviewStatus = 'confirmed';
  entry.publications[1].reviewStatus = 'proposed';
  const html = atRest(detailCtx(entry, { singleEntry: true })._buildReadContent(entry));
  // The heading label is one value with its chain, and the edition state follows it.
  assert.match(html, /1947, 1st edition<\/span> <span class="publication-status publication-status-confirmed"[^>]*>edition confirmed</);
  assert.match(html, /1960, 2nd revised edition<\/span> <span class="publication-status publication-status-proposed"[^>]*>edition proposed</);
  // An edition the agentic sample reviewed names that review beside its state.
  entry.publications[1].reviewDecision = 'confirm';
  entry.publications[1].reviewProducer = 'llm-agent';
  const reviewed = detailCtx(entry, { singleEntry: true })._buildReadContent(entry);
  assert.match(reviewed, /publication-status-proposed"[^>]*no person has checked it\.[^>]*>edition proposed[\s\S]*?LLM agent review[^<]*no person</);
  // Records built before the graph carried the state say nothing.
  assert.doesNotMatch(detailCtx(editionPage())._buildReadContent(editionPage()), /publication-status/);
});

test('an edition claim stands in the block of the publication it concerns', () => {
  // Page 4916: the decided work identity is about the 2016 graphic novel.
  const entry = editionPage();
  entry.sourcePageId = 4916;
  entry.publications[0].id = 'klawiter:publication/4916-2016-b';
  entry.publications[1].id = 'klawiter:publication/4916-2019-a';
  const claim = {
    claimId: 'klawiter:claim/work-binding/4916-2016-b', decisionStatus: 'decided',
    subject: 'klawiter:edition/4916-2016-b',
    interpretations: [{ label: 'Adaptation work', status: 'accepted', basis: 'b', proposedObject: 'x' }],
    reviewHistory: [], source: { sourcePageId: 4916, selector: [1, 2], sliceSha256: 'f' },
  };
  const html = detailCtx(entry, { singleEntry: true },
    { Edit: editStub({ editionClaimsFor: () => [claim] }) })._buildReadContent(entry);
  const first = html.indexOf('aria-label="Publication 1"');
  const second = html.indexOf('aria-label="Publication 2"');
  const decided = html.indexOf('Work identity decided');
  assert.ok(first < decided && decided < second, 'inside the first publication block');
  assert.strictEqual((html.match(/Work identity decided/g) || []).length, 1);
});

test('the source block of a publication is named and marked as a whole', () => {
  const entry = editionPage();
  const text = entry.fullBibliographicEntry;
  entry.publications[0].sourceSlice = { textStart: 0, textEnd: 26 };
  entry.publications[1].sourceSlice = { textStart: 28, textEnd: text.length };
  const html = detailCtx(entry, { singleEntry: true })._buildReadContent(entry);
  assert.match(html, /<span class="source-slice"><span class="source-slice-label">1947, 1st edition<\/span>/);
  assert.match(html, /<span class="source-slice"><span class="source-slice-label">1960, 2nd revised edition<\/span>/);
});

test('a publication route marks its block, a filter marks the publications it selects', () => {
  const entry = editionPage();
  const routed = detailCtx(entry, { singleEntry: true, publicationId: '1800-1960-a' })
    ._buildReadContent(entry);
  assert.match(routed, /class="detail-section publication publication-target" id="publication-1800-1800-1960-a"/);
  assert.strictEqual((routed.match(/publication-target/g) || []).length, 1);

  // Page 4445 under a language filter: the Arabic article matches, the German
  // book does not, and the card says which one the filter found.
  const app = (matches) => ({ App: {
    state: { editMode: false, singleEntry: false, query: '' },
    entries: [entry], entryMap: new Map([[entry.sourcePageId, entry]]),
    titleMap: new Map(), data: { redirects: {} }, publicationMatches: matches,
  } });
  const html = detailCtx(entry, {}, app(pub => pub.year === 1960))._buildReadContent(entry);
  const second = html.slice(html.indexOf('aria-label="Publication 2"') - 200);
  assert.match(second, /publication-match/);
  assert.strictEqual((html.match(/matches the filter/g) || []).length, 1);
  // A filter every publication answers, or none at all, marks nothing.
  for (const answer of [() => true, () => null]) {
    const none = detailCtx(entry, {}, app(answer))._buildReadContent(entry);
    assert.doesNotMatch(none, /matches the filter/);
  }
});

test('a failed claim file is said where the claims would stand', () => {
  const entry = sampleEntry();
  const html = detailCtx(entry, {}, { Edit: editStub({ reconciliationFailed: true,
    reconciliationError: 'HTTP 404' }) })._buildReadContent(entry);
  assert.match(html, /contested claims\s+could not be loaded \(HTTP 404\)/);
});

test('a joint imprint keeps each publisher with its place, a series keeps its gloss', () => {
  // Page 1725, the edition of 1966, and page 5039.
  const entry = editionPage();
  entry.publications[1].imprints = [
    { publisher: 'Nauka i izkustvo', place: 'Sofija' },
    { publisher: 'DPK St. Dobrev-Strandzhata', place: 'Varna' },
  ];
  entry.publications[1].places = ['Sofija', 'Varna'];
  entry.publications[1].publisher = 'Nauka i izkustvo';
  entry.publications[0].series = 'Tvorba národov';
  entry.publications[0].seriesGloss = 'The Formation of Nations';
  const html = detailCtx(entry, { singleEntry: true })._buildReadContent(entry);
  const second = html.slice(html.indexOf('aria-label="Publication 2"'));
  assert.match(second, />Imprint</);
  // The decision and the authority link of Sofija stay at Sofija.
  assert.match(atRest(second), /Nauka i izkustvo, Sofija <a class="wikidata-link"[\s\S]*?<\/span><\/span> \/ <span class="rc-value">DPK St\. Dobrev-Strandzhata, Varna</);
  assert.doesNotMatch(second.slice(0, second.indexOf('</section>')), />Publisher</);
  assert.match(html, /Tvorba národov <span class="field-sub"[^>]*>\(The Formation of Nations\)</);
});

test('a rejection reads as a rejection, and the chip names the scope the record states', () => {
  const entry = sampleEntry();
  entry.review = { status: 'reviewed', reviewed_by: 'main-instance',
    fields: { location: 'reject' }, scope: ['location'] };
  const chip = detailCtx(entry)._reviewChip(entry);
  assert.match(chip, /review-reviewed/);
  assert.match(chip, />Place authority candidate rejected<span class="decision-producer">, /);
  assert.doesNotMatch(chip, /Unreviewed|verified/);
  // The stated scope wins over the keys of the decisions.
  entry.review = { status: 'confirmed', reviewed_by: 'Editor (SZD)', producer: 'person',
    fields: { location: 'confirm', publisher: 'reject' }, scope: ['location', 'publisher'] };
  assert.match(detailCtx(entry)._reviewChip(entry), />Place authority and publisher confirmed<span class="decision-producer">, <span class="visually-hidden">decided by <\/span>person/);
});

test('a contested edition says so in its heading', () => {
  const entry = editionPage();
  entry.publications[0].reviewStatus = 'contested';
  const html = detailCtx(entry, { singleEntry: true })._buildReadContent(entry);
  assert.match(html, /publication-status-contested[^>]*>edition contested</);
});

test('a restored page states the revision it is published from and why', () => {
  // Page 35, Maria Stuart: the Redirect fixer overwrote the compiler's page.
  const entry = sampleEntry();
  entry.sourceRevision = {
    decisionId: 'source-revision/35/restore-human-revision',
    action: 'restore-human-revision',
    reason: 'The Redirect fixer revision replaced a content page with a redirect.',
    humanRevision: { revisionId: 33251, timestamp: '2017-09-25T20:31:36Z', actor: 'Klawiter',
      textId: 32391 },
    fixerRevisions: [{ revisionId: 33773, timestamp: '2017-10-08T20:25:29Z',
      comment: '[[Al-Sulṭānī, Fāḍil]] has been moved' }],
    decidedBy: 'decided by the main instance after delegation',
  };
  const html = detailCtx(entry)._buildReadContent(entry);
  assert.match(html, /Source revision<\/span>\s+Published from revision 33251 by Klawiter of 2017-09-25\. The Redirect fixer revision replaced a content page/);
  assert.match(html, /Revision 33773, 2017-10-08: \[\[Al-Sulṭānī, Fāḍil\]\] has been moved/);
  assert.match(html, /title="source-revision\/35\/restore-human-revision Decided by the main instance/);
  assert.ok(html.indexOf('Source revision') < html.indexOf('detail-source-details'));
  assert.doesNotMatch(detailCtx(sampleEntry())._buildReadContent(sampleEntry()), /Source revision/);
});

test('a reference leads to its page, or to the claim that withholds its redirect', () => {
  const claim = { claimId: 'klawiter:claim/source-revision/670', entityType: 'source-revision',
    decisionStatus: 'open', subject: { '@id': 'klawiter:entry/670', name: 'Le chandelier enterré' },
    interpretations: [{ label: 'The page redirects to Der begrabene Leuchter' }],
    sourceEvidence: [{ sourcePageId: 670, sourceTextId: 1, sourceValue: '#REDIRECT [[X]]',
      sourceTextSha256: 'ab'.repeat(32) }],
    reviewHistory: [{ decidedBy: 'main-instance', action: 'unresolved', basis: 'revisable',
      evidence: ['data/reconciliation/source-revision-decisions.json',
        'zweig_revision 1 by Redirect fixer'] }] };
  const entry = sampleEntry();
  const Detail = detailCtx(entry, {}, {
    App: { state: { editMode: false }, entries: [entry], entryMap: new Map([[1800, entry]]),
      titleMap: new Map([['Maria Stuart', 35]]), data: { redirects: {} } },
    Edit: editStub({ sourceRevisionClaim: (pid, title) =>
      (title === 'Le chandelier enterré' || pid === 670 ? claim : null) }),
  });
  assert.strictEqual(Detail.makeLink('Maria Stuart'), '<a href="#entry=35">Maria Stuart</a>');
  assert.match(Detail.makeLink('Le chandelier enterré'),
    /<a href="#entry=670">Le chandelier enterré<\/a> <span class="field-sub">redirect withheld,\s+open claim<\/span>/);
  assert.strictEqual(Detail.makeLink('Nowhere'), 'Nowhere');
  const block = Detail.withheldRedirectBlock(claim);
  assert.match(block, /Le chandelier enterré: redirect\s+withheld, decision open/);
  assert.match(block, /zweig_revision 1 by Redirect fixer/);
  assert.doesNotMatch(block, /source-revision-decisions\.json/);
  // The history names the producer the card head names, not the raw role.
  assert.match(block, /<li title="main-instance">LLM agent: left unresolved <span class="field-sub">\(revisable\)/);
});

test('an authority claim history reads in plain words, the role in its tooltip', () => {
  const entry = sampleEntry();
  const claim = { claimId: 'c', entityType: 'location', decisionStatus: 'open',
    subject: { name: 'Wien' }, interpretations: [], sourceEvidence: [],
    reviewHistory: [{ decisionId: 'location/Wien/unresolved', action: 'unresolved',
      decidedBy: 'independent-verification-agent' }] };
  const Detail = detailCtx(entry, {}, { Edit: editStub({ authorityClaimsFor: () => [claim] }) });
  const history = Detail._authorityHistory(claim);
  assert.strictEqual(history, '<li title="independent-verification-agent, location/Wien/unresolved">'
    + 'LLM agent: left unresolved</li>');
  assert.doesNotMatch(history, />independent-verification-agent/);
});

test('a publication route keeps the page and names the publication', () => {
  const { App, ctx } = appCtx();
  const entry = sampleEntry();
  App.entries = [entry];
  App.entryMap = new Map([[1800, entry]]);
  App.showView = (v) => { App.state.view = v; };
  App.renderChips = () => {};
  ctx.Facets = { render() {} };

  App._lastHash = null;
  ctx.location.hash = '#entry=1800&pub=1800-1960-a';
  App.handleRoute();
  assert.strictEqual(App.state.singleEntry, true);
  assert.strictEqual(App.state.publicationId, '1800-1960-a');

  App._lastHash = null;
  ctx.location.hash = '#records';
  App.handleRoute();
  assert.strictEqual(App.state.publicationId, null);
});

test('a filtered list names the publication of a page that matched', () => {
  // Page 4445 carries a German book of 2000 and an Arabic article of 2015.
  const { App, ctx } = appCtx();
  const Detail = vm.runInContext('Detail', ctx);
  const entry = {
    sourcePageId: 4445, entryType: 'secondary-literature', title: 'Al-Bāḥ, Muḥammad',
    pageKind: 'author-page', publicationCount: 2, publicationYears: [2000, 2015],
    publicationLanguages: ['German', 'Arabic'], publicationPlaces: ['Freiburg im Breisgau', 'Rabat'],
  };
  App.entryMap = new Map([[4445, entry]]);
  App.state.singleEntry = false;
  App.state.filters = { language: 'Arabic' };

  // Before the page file is in, the line names the value that answered.
  Detail._pubCache.set(4445, { status: 'loading' });
  assert.match(App.cardMeta(entry), /class="card-meta-text card-match">matching Arabic</);

  Detail._pubCache.set(4445, { status: 'ready', nameVariants: [], publications: [
    { id: 'klawiter:publication/4445-2000-a', year: 2000, language: 'German',
      places: ['Freiburg im Breisgau'] },
    { id: 'klawiter:publication/4445-2015-a', year: 2015, language: 'Arabic',
      container: { title: 'Al-Balāghah', place: 'Rabat' } },
  ] });
  assert.match(App.cardMeta(entry), />matching 2015, Arabic, Rabat</);
  assert.strictEqual(App.publicationMatches({ year: 2000, language: 'German' }), false);

  // Without a filter on a publication axis the line keeps its count alone.
  App.state.filters = { type: 'secondary-literature' };
  assert.doesNotMatch(App.cardMeta(entry), /card-match/);
  assert.strictEqual(App.publicationMatches({ year: 2000 }), null);
});

test('the review facet names the fields its decisions cover', () => {
  const { App } = appCtx();
  App.entries = [sampleEntry()];
  assert.strictEqual(App.reviewLabel('proposed'), 'Place authority proposed');
  assert.strictEqual(App.reviewLabel('unreviewed'), 'Unreviewed');
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

test('a decision names its producer as visible text, and an agent is never a person', () => {
  // Page 468, København: decided by the independent verification agent. Every
  // place decision is by LLM agents, so each stands as a proposal.
  const entry = sampleEntry();
  const Detail = detailCtx(entry);
  for (const by of ['independent-verification-agent', 'main-instance']) {
    assert.strictEqual(Detail.decisionProducer({ status: 'proposed', reviewed_by: by }),
      'LLM agent', by);
  }
  assert.strictEqual(Detail.decisionProducer(entry.review),
    'LLM agents, source occurrence checked, no person');
  // A person reaches the review object only through a released human patch.
  assert.strictEqual(Detail.decisionProducer({ status: 'approved', reviewed_by: 'Editor (SZD)' }),
    'person');
  assert.strictEqual(Detail.decisionProducer({ status: 'proposed', reviewed_by: 'someone' }),
    'unclassified decider someone');

  const html = Detail._buildReadContent(entry);
  const place = html.slice(html.indexOf('>Place of publication'), html.indexOf('>Publisher'));
  // The state word stays; the producer stands beside it outside any title.
  assert.match(place, />link proposed<\/span><span class="decision-producer">, /);
  assert.match(place.replace(/<[^>]*>/g, ''),
    /link proposed, by LLM agents, source occurrence checked, no person/);
  assert.doesNotMatch(place, />confirmed</);
  assert.doesNotMatch(place, /by <\/span>person/);
  // On the desk every value names its producer, rule extraction too, after
  // the decision on the authority link it does not class.
  assert.match(place, /no person<\/span><button type="button" class="prov-badge rc-producer-btn rc-producer-rule"[^>]*><span class="rc-producer">rule<\/span>/);
  entry._provenance.location = 'llm';
  const llmPlace = Detail._buildReadContent(entry);
  assert.match(llmPlace.slice(llmPlace.indexOf('>Place of publication'), llmPlace.indexOf('>Publisher')),
    /<button type="button" class="prov-badge rc-producer-btn rc-producer-llm"[^>]*><span class="rc-producer">LLM-enriched<\/span>/);
  assert.doesNotMatch(place, /title="Reviewed decision/);

  // The review chip names the producer visibly too, not only in its tooltip.
  assert.match(Detail._reviewChip(entry).replace(/<[^>]*>/g, ''),
    /Place authority proposed, by LLM agents, source occurrence checked, no person/);
});

test('a place decision carries the same subdued weight as an edition proposal', () => {
  const css = fs.readFileSync(path.join(__dirname, '..', 'docs', 'css', 'styles.css'), 'utf8');
  const rule = selector => {
    const match = new RegExp(`(?:^|\n)${selector.replace('.', '\.')}[^{]*\{([^}]*)\}`).exec(css);
    return match ? match[1] : '';
  };
  const review = rule('.field-review');
  assert.doesNotMatch(review, /uppercase|background|font-weight:\s*[6-9]00/);
  assert.match(review, /font-size:\s*0\.75rem/);
  assert.match(rule('.publication-status'), /font-size:\s*0\.75rem/);
});

test('a result line carries data, and only a contested state as one marker word', () => {
  const { App, ctx } = appCtx();
  // Page 1800 carries a place authority decided by an agent: a state of the
  // card, which the list line does not repeat.
  const entry = sampleEntry();
  const line = App.listMeta(entry);
  for (const value of ['1947', 'Bulgarian', 'Sofija', 'Historical Studies', 'Pechat Far, 500 pp.']) {
    assert.ok(line.includes(value), `${value} stands in the line`);
  }
  assert.doesNotMatch(line, /review-chip|agent-verified|LLM agent|card-marker/);

  // Page 4819, Adam Lux: the place authority stays contested.
  entry.review = { status: 'contested', reviewed_by: 'independent-verification-agent',
    fields: { location: 'unresolved' }, scope: ['location'] };
  assert.match(App.listMeta(entry), /<span class="card-marker" title="Place authority contested, decision open\. [^"]+">contested<span\s+class="visually-hidden">: place authority contested, decision open<\/span><\/span>/);

  // An open authority claim on an otherwise unreviewed page reads the same way.
  ctx.Edit = editStub({ authorityClaimsFor: () => [{ claimId: 'c', entityType: 'location',
    decisionStatus: 'open', subject: { name: 'Sofija' } }] });
  const open = sampleEntry();
  delete open.review;
  assert.match(App.listMeta(open), /title="Open place claim\. [^"]+">contested</);

  // The head of the full card keeps the decision and its producer.
  ctx.Edit = editStub();
  App.state.singleEntry = true;
  assert.match(App.renderCard(sampleEntry()), /class="rc-review">Place authority proposed, by LLM agents/);
});

test('beside the reading pane the first result stands as a full card on arrival', () => {
  const { App, ctx } = appCtx();
  ctx.Edit = Object.assign(editStub(), { cardHint: () => '' });
  ctx.window.matchMedia = () => ({ matches: true });
  const first = sampleEntry();
  const second = Object.assign(sampleEntry(), { sourcePageId: 1801, title: 'Second' });
  App.entries = [first, second];
  App.entryMap = new Map([[1800, first], [1801, second]]);
  App.filtered = [first, second];

  App.renderResults();
  const list = ctx.elements['results-list'].innerHTML;
  const pane = ctx.elements['reading-pane'];
  assert.strictEqual(App.state.selectedId, 1800);
  assert.strictEqual(pane.hidden, false);
  // The pane card carries the ids the edit layer and the late renders find.
  assert.match(pane.innerHTML, /<article class="pane-card" id="card-1800" data-pid="1800"/);
  assert.match(pane.innerHTML, /id="card-detail-1800"/);
  // The pane head is the shared head, labelled for the pane card.
  assert.match(pane.innerHTML, /aria-labelledby="pane-title-1800"/);
  assert.match(pane.innerHTML, /<h2 class="rc-title" id="pane-title-1800"/);
  assert.match(pane.innerHTML, /Year of publication/);
  assert.match(pane.innerHTML, /class="rc-review">Place authority proposed, by /);
  // The list holds a title and a value line per result, and no card.
  assert.strictEqual((list.match(/aria-controls="reading-pane"/g) || []).length, 2);
  assert.doesNotMatch(list, /card-detail|id="card-|review-chip|rc-head/);
  assert.match(list, /card-secondary/);
  assert.strictEqual(App.cardMeta(first), App.listMeta(first),
    'the edit layer rewrites a list line through cardMeta');

  // A new list starts at its first result; a rerender of the same list keeps
  // the choice.
  App.selectEntry(1801);
  App.renderResults();
  assert.strictEqual(App.state.selectedId, 1801);

  // The permalink route keeps its single card and no pane.
  App.state.singleEntry = true;
  App.filtered = [first];
  App.renderResults();
  assert.strictEqual(pane.hidden, true);
  assert.match(ctx.elements['results-list'].innerHTML, /id="card-detail-1800"/);
});

test('the default state of the values is said once, behind a disclosure at the heading', () => {
  const html = fs.readFileSync(path.join(__dirname, '..', 'docs', 'index.html'), 'utf8');
  const statement = /Unless a value is marked, it was extracted by rule\s+from the source text and has not been reviewed\./g;
  assert.strictEqual((html.match(statement) || []).length, 1);
  assert.match(html, /<h1 id="results-count"[^>]*><\/h1>\s*(?:<!--[\s\S]*?-->\s*)?<details id="list-defaults" class="results-info">\s*<summary aria-label="About the values"/);
  assert.doesNotMatch(html, /<p id="list-defaults"/);
  for (const file of fs.readdirSync(path.join(__dirname, '..', 'docs', 'js'))) {
    assert.doesNotMatch(read(file), /extracted by rule from the source text and has not been reviewed/, file);
  }
});

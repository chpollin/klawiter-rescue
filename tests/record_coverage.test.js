/**
 * Every field of every record has a place in its rendered card, and every
 * value read from a source passage shows its provenance chain.
 *
 * The card is rendered as the permalink route renders it (App.renderCard and
 * Detail.renderInline, read layout, publication file loaded) for every
 * namespace-0 record of docs/data/klawiter.json. A field is placed where its
 * value is visible outside the quoted source, in a tooltip only, or where the
 * card marks its row with data-key="<field>"; the quoted source places only
 * the source text and its identifiers, because it holds almost every value
 * verbatim. A value has a source passage where it occurs in the source text
 * (a publication value inside its own passage), and it shows its chain where
 * the card carries data-provenance-for="<field>" (in a publication block,
 * "<field>" of that publication).
 *
 * The current gaps are pinned in record_coverage_expected.json, as the
 * semantic baseline pins its known failures: the test fails when a field
 * appears that has no declared place, when a gap grows, and when a gap closes
 * without the expectation being lowered with it. After a deliberate change,
 * RECORD_COVERAGE_WRITE=1 node --test tests/record_coverage.test.js rewrites
 * the expectation from the measurement; review its diff before committing.
 *
 * The visible text of a card outside the quoted source must also hold none of
 * the tokens a failed stringification leaves ("[object Object]", "undefined",
 * "NaN"). The cards that still do are pinned under renderedGarbage in the same
 * file, by record count, token count and the field row they appear in; the
 * pin is lowered when the renderer is fixed and fails when it grows.
 */
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const ROOT = path.join(__dirname, '..');
const read = file => fs.readFileSync(path.join(ROOT, 'docs', 'js', file), 'utf8');
const EXPECTED_PATH = path.join(__dirname, 'record_coverage_expected.json');
const EXPECTED = JSON.parse(fs.readFileSync(EXPECTED_PATH, 'utf8'));

function cardContext(data) {
  const location = { hash: '', pathname: '/', hostname: 'localhost' };
  const element = () => ({ textContent: '', innerHTML: '', style: {},
    classList: { add() {}, remove() {}, toggle() {} } });
  const ctx = {
    console, URLSearchParams, setTimeout: () => 0,
    window: { location, addEventListener() {} },
    location,
    history: { replaceState() {}, pushState() {} },
    document: { addEventListener() {}, getElementById: element, querySelectorAll: () => [] },
    // Claims and session state are not record fields; the stub keeps them empty.
    Edit: {
      FIELD_LABELS: {}, pending: () => undefined,
      entryStatus: () => ({ status: 'unreviewed', pending: false }),
      triageHints: () => [], evidence: () => null, editionClaimsFor: () => [],
      authorityClaimsFor: () => [], openClaimOnValue: () => null,
      locationReconciliation: () => null, agentReconciliation: () => null,
      sourceRevisionClaim: () => null,
    },
  };
  vm.createContext(ctx);
  for (const file of ['constants.js', 'utils.js', 'detail.js']) vm.runInContext(read(file), ctx);
  const App = vm.runInContext(`${read('app.js')}\nApp`, ctx);
  App.data = data;
  App.entries = data.entries.filter(e => e.pageNamespace === 0);
  App.entryMap = new Map(App.entries.map(e => [e.sourcePageId, e]));
  App.titleMap = new Map(App.entries.map(e => [e.title, e.sourcePageId]));
  App.state.singleEntry = true;
  App.state.isLocal = false;
  ctx.App = App;
  return { App, Detail: vm.runInContext('Detail', ctx) };
}

const ENTITIES = { amp: '&', lt: '<', gt: '>', quot: '"', '#39': "'", nbsp: ' ' };
const decode = s => s.replace(/&(#x[0-9a-f]+|#\d+|\w+);/gi, (m, name) => {
  if (ENTITIES[name] !== undefined) return ENTITIES[name];
  if (name[0] === '#') {
    return String.fromCodePoint(name[1].toLowerCase() === 'x' ? parseInt(name.slice(2), 16) : Number(name.slice(1)));
  }
  return m;
});
const visible = html => decode(html.replace(/<[^>]*>/g, ' '));
const attributes = html => decode([...html.matchAll(/\s(?:title|href|aria-label)="([^"]*)"/g)]
  .map(m => m[1]).join(' '));
// Layout joins and splits values (a contents item's pages, an imprint), so a
// value is compared on its letters and digits alone.
const loose = s => String(s).normalize('NFC').toLowerCase().replace(/[^\p{L}\p{N}]+/gu, '');

/** Where one value stands: 'visible', 'tooltip' or null. */
function placeOf(value, region) {
  const needle = loose(value);
  if (!needle) return 'visible';
  if (region.text.includes(needle)) return 'visible';
  if (region.attrs.includes(needle)) return 'tooltip';
  return null;
}

function region(html) {
  return { html, text: loose(visible(html)), attrs: loose(attributes(html)) };
}

// Tokens of a failed stringification, as values and not as part of a word.
const GARBAGE_RE = /\[object Object\]|\bundefined\b|\bNaN\b/g;

/** The data-key row a position of the card html stands in, the last one opened before it. */
function rowKeyAt(html, index) {
  const keys = [...html.slice(0, index).matchAll(/data-key="([^"]*)"/g)];
  return keys.length ? keys[keys.length - 1][1] : '(no data-key)';
}

const marked = (html, key) => html.includes(`data-key="${key}"`);
const chained = (html, key) => chainedKeys(html).has(key);

// The card is read as a reader sees it: an element with the hidden attribute
// and everything inside it is gone before any value or marker is matched, so a
// hidden span cannot stand in for a field the card does not show.
const VOID_TAGS = new Set(['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr']);
const TAG_RE = /<(\/?)([a-zA-Z][\w-]*)((?:"[^"]*"|'[^']*'|[^>"'])*)>/g;

/** Every element of the html with the offsets of its opening tag and its end. */
function elements(html) {
  const found = [];
  const stack = [];
  for (const m of html.matchAll(TAG_RE)) {
    const tag = m[2].toLowerCase();
    const after = m.index + m[0].length;
    if (m[1]) {
      const at = stack.map(el => el.tag).lastIndexOf(tag);
      if (at === -1) continue;
      for (const el of stack.splice(at)) el.end = after;
    } else {
      const el = { tag, attrs: m[3], start: m.index, end: html.length };
      found.push(el);
      if (!VOID_TAGS.has(tag) && !m[3].trimEnd().endsWith('/')) stack.push(el);
      else el.end = after;
    }
  }
  return found;
}

const hasAttr = (el, name) => new RegExp(`(^|\\s)${name}(\\s|=|$)`).test(el.attrs);

function stripHidden(html) {
  let out = '';
  let at = 0;
  for (const el of elements(html)) {
    if (!hasAttr(el, 'hidden') || el.start < at) continue;
    out += html.slice(at, el.start);
    at = el.end;
  }
  return out + html.slice(at);
}

const chainCache = new Map();
/**
 * The keys whose chain a reader can see: an element that carries
 * data-provenance-for="<key>" and holds a provenance badge. Rule extraction
 * and a missing value show no badge, so they disclose no chain.
 */
function chainedKeys(html) {
  if (!chainCache.has(html)) {
    if (chainCache.size > 64) chainCache.clear();
    const keys = new Set();
    for (const el of elements(html)) {
      const key = /data-provenance-for="([^"]*)"/.exec(el.attrs);
      if (key && html.slice(el.start, el.end).includes('prov-badge')) keys.add(key[1]);
    }
    chainCache.set(html, keys);
  }
  return chainCache.get(html);
}

/** The weakest place over several values: every value must stand somewhere. */
function placeOfAll(values, where) {
  let result = 'visible';
  for (const value of values) {
    const place = placeOf(value, where);
    if (place === null) return null;
    if (place === 'tooltip') result = 'tooltip';
  }
  return result;
}

const strings = list => (Array.isArray(list) ? list : []).filter(v => v != null && v !== '');

/**
 * The place of every record field. `fields` is the card without the quoted
 * source, `source` the quoted source with its identifier line, `card` both.
 * A derived field stands where the field it is derived from stands.
 */
const RECORD_PLACES = {
  '@id': (e, r) => (marked(r.card.html, '@id') ? 'visible' : placeOf(e['@id'], r.fields)),
  '@type': (e, r) => (marked(r.card.html, '@type') ? 'visible' : placeOfAll(e['@type'], r.fields)),
  entryType: (e, r, ctx) => placeOf(ctx.ENTRY_TYPE_LABELS[e.entryType] || e.entryType, r.fields),
  sourcePageId: (e, r) => placeOf(`Page ID: ${e.sourcePageId}`, r.source),
  sourceTextId: (e, r) => placeOf(`Text ID: ${e.sourceTextId}`, r.source),
  sourceBlobId: (e, r) => placeOf(`Blob: ${e.sourceBlobId}`, r.source),
  // The bibliography views hold namespace 0 alone, so the card's existence states it.
  pageNamespace: () => 'visible',
  fullBibliographicEntry: (e, r) => (r.source.html.includes('detail-source-details') ? 'visible' : null),
  title: (e, r) => placeOf(e.title, r.fields),
  originalTitle: (e, r) => placeOf(e.originalTitle, r.fields),
  year: (e, r) => placeOf(e.year, r.fields),
  allYears: (e, r) => (marked(r.card.html, 'allYears') ? 'visible' : placeOfAll(e.allYears, r.fields)),
  timePeriod: (e, r, ctx) => (marked(r.card.html, 'timePeriod') ? 'visible'
    : placeOf(ctx.PERIOD_LABELS[e.timePeriod] || e.timePeriod, r.fields)),
  publisher: (e, r) => placeOf(e.publisher, r.fields),
  location: (e, r) => placeOf(e.location, r.fields),
  allLocations: (e, r) => placeOfAll(e.allLocations, r.fields),
  language: (e, r) => placeOf(e.language, r.fields),
  languageCode: (e, r) => placeOf(e.languageCode, r.fields),
  translator: (e, r) => placeOf(e.translator, r.fields),
  pageCount: (e, r) => placeOf(e.pageCount, r.fields),
  categories: (e, r) => placeOfAll(e.categories, r.fields),
  mainCategory: (e, r) => (marked(r.card.html, 'mainCategory') ? 'visible' : placeOf(e.mainCategory, r.fields)),
  contentItems: (e, r) => placeOfAll(e.contentItems, r.fields),
  seeAlso: (e, r) => placeOfAll(e.seeAlso, r.fields),
  reprints: (e, r) => placeOfAll(e.reprints, r.fields),
  translations: (e, r) => placeOfAll(e.translations, r.fields),
  translationStatements: (e, r) => (marked(r.card.html, 'translationStatements') ? 'visible' : null),
  locationSameAs: (e, r) => (r.fields.html.includes(`href="${e.locationSameAs}"`) ? 'visible' : null),
  review: (e, r) => (/class="(review-chip|field-review)/.test(r.card.html) || marked(r.card.html, 'review')
    ? 'visible' : null),
  reviewFlags: (e, r) => placeOfAll(e.reviewFlags.map(flag => flag.detail || flag.code), r.fields),
  sourceRevision: (e, r) => placeOf(`revision ${e.sourceRevision.humanRevision.revisionId}`, r.fields),
  pageKind: (e, r, ctx) => (ctx.App.PAGE_KIND_LABELS[e.pageKind]
    ? placeOf(ctx.App.PAGE_KIND_LABELS[e.pageKind], r.fields)
    : (marked(r.card.html, 'pageKind') ? 'visible' : null)),
  publicationCount: (e, r) => placeOf(e.publicationCount, r.fields),
  // The unions stand where each publication's own value stands.
  publicationYears: (e, r) => placeOfAll(e.publicationYears, r.publications),
  publicationPlaces: (e, r) => placeOfAll(e.publicationPlaces, r.publications),
  publicationLanguages: (e, r) => placeOfAll(e.publicationLanguages, r.publications),
  publicationReviewFlags: (e, r) => (marked(r.card.html, 'publicationReviewFlags')
    || r.publications.html.includes('review-flag') ? 'visible' : null),
  wikiPageKind: (e, r) => (marked(r.card.html, 'wikiPageKind') ? 'visible' : null),
  wikiPageKindRule: (e, r) => (marked(r.card.html, 'wikiPageKindRule') ? 'visible' : null),
  wikiPageKindEvidence: (e, r) => (marked(r.card.html, 'wikiPageKindEvidence') ? 'visible' : null),
  printAddressCitations: (e, r) => placeOfAll(
    e.printAddressCitations.flatMap(c => [c.printAddress, c.passageText]), r.fields),
  // Every reported class is a step of a chain, so the field stands where the chains do.
  _provenance: (e, r) => (Object.entries(e._provenance).every(([key, cls]) =>
    cls === 'missing' || e[key] == null || e[key] === '' || chained(r.card.html, key)) ? 'visible' : null),
};

/** The place of every publication field, inside that publication's block. */
const PUBLICATION_PLACES = {
  id: (p, b) => (marked(b.html, 'id') ? 'visible' : placeOf(p.id, b)),
  year: (p, b) => placeOf(p.year, b),
  yearRaw: (p, b) => placeOf(p.yearRaw, b),
  // A title equal to the page title stands as the title of the card.
  title: (p, b, e, r) => placeOf(p.title, p.title === e.title ? r.card : b),
  imprint: (p, b) => (marked(b.html, 'imprint') ? 'visible' : placeOf(p.imprint, b)),
  imprints: (p, b) => placeOfAll(p.imprints.flatMap(i => strings([i.publisher, i.place])), b),
  publisher: (p, b) => placeOf(p.publisher, b),
  places: (p, b) => placeOfAll(p.places, b),
  language: (p, b) => placeOf(p.language, b),
  languageCode: (p, b) => placeOf(p.languageCode, b),
  editionStatement: (p, b) => placeOf(p.editionStatement, b),
  extent: (p, b) => placeOfAll(strings([p.extent.raw, p.extent.numbered, p.extent.unnumbered]), b),
  series: (p, b) => placeOf(p.series, b),
  seriesVolume: (p, b) => placeOf(p.seriesVolume, b),
  seriesGloss: (p, b) => placeOf(p.seriesGloss, b),
  note: (p, b) => placeOf(p.note, b),
  credits: (p, b) => placeOfAll(p.credits.map(c => c.name), b),
  contributions: (p, b) => placeOfAll(p.contributions.flatMap(c =>
    strings([c.title, c.pages, ...(c.credits || []).map(k => k.name)])), b),
  container: (p, b) => placeOfAll(strings([p.container.title, p.container.place,
    p.container.issue, p.container.pages]), b),
  online: (p, b) => placeOf(p.online.url, b),
  reviewFlags: (p, b) => placeOfAll(p.reviewFlags.map(f => f.detail || f.code), b),
  editionId: (p, b) => placeOf(p.editionId, b),
  reviewStatus: (p, b) => placeOf(`edition ${p.reviewStatus}`, b),
  reviewDecision: (p, b) => placeOf(p.reviewDecision, b),
  reviewProducer: (p, b) => (p.reviewProducer === 'llm-agent' ? placeOf('LLM agent review', b) : placeOf(p.reviewProducer, b)),
  sourceSlice: (p, b) => (marked(b.html, 'sourceSlice') ? 'visible' : null),
  provenance: (p, b) => (Object.keys(p.provenance).every(key => chained(b.html, key)) ? 'visible' : null),
};

// Values a reader can find in the source text, per layer.
const RECORD_VALUES = ['title', 'originalTitle', 'year', 'publisher', 'location', 'translator', 'pageCount'];
const PUBLICATION_VALUES = {
  publisher: p => strings([p.publisher]),
  places: p => strings(p.places),
  credits: p => (p.credits || []).map(c => c.name),
  extent: p => strings([p.extent && p.extent.raw]),
  editionStatement: p => strings([p.editionStatement]),
  series: p => strings([p.series]),
  title: p => strings([p.title]),
};

const isEmpty = v => v == null || v === '' || (Array.isArray(v) && !v.length)
  || (typeof v === 'object' && !Array.isArray(v) && !Object.keys(v).length);

function tally(map, key, place) {
  const row = map[key] || (map[key] = { records: 0, tooltipOnly: 0, absent: 0 });
  row.records += 1;
  if (place === 'tooltip') row.tooltipOnly += 1;
  if (place === null) row.absent += 1;
}

const sorted = obj => JSON.parse(JSON.stringify(obj, (k, v) => (v && typeof v === 'object' && !Array.isArray(v)
  ? Object.fromEntries(Object.entries(v).sort(([a], [b]) => a.localeCompare(b))) : v)));

function measure() {
  const data = JSON.parse(fs.readFileSync(path.join(ROOT, 'docs', 'data', 'klawiter.json'), 'utf8'));
  const card = cardContext(data);
  const { App, Detail } = card;
  const ctx = { App };
  const constants = vm.createContext({});
  vm.runInContext(read('constants.js'), constants);
  ctx.ENTRY_TYPE_LABELS = vm.runInContext('ENTRY_TYPE_LABELS', constants);
  ctx.PERIOD_LABELS = vm.runInContext('PERIOD_LABELS', constants);

  const report = { records: 0, publications: 0, undeclared: {}, recordFields: {},
    publicationFields: {}, garbage: { records: 0, tokens: {}, fields: {} }, chains: { recordValues: 0, recordWithoutChain: 0,
      publicationValues: 0, publicationWithoutChain: 0 } };
  const examples = {};
  const note = (key, pid) => { (examples[key] = examples[key] || []).length < 3 && examples[key].push(pid); };

  for (const entry of App.entries) {
    const pid = entry.sourcePageId;
    let side = null;
    if (Number(entry.publicationCount) > 0) {
      side = JSON.parse(fs.readFileSync(path.join(ROOT, 'docs', 'data', 'publications', `${pid}.json`), 'utf8'));
      Detail._pubCache.set(pid, { status: 'ready', publications: side.publications || [],
        nameVariants: side.nameVariants || [] });
    }
    const html = stripHidden(App.renderCard(entry) + Detail.renderInline(entry));
    const cut = html.indexOf('<details class="detail-source-details"');
    const end = html.indexOf('<div class="action-bar">');
    const sourceHtml = cut === -1 ? '' : html.slice(cut, end === -1 ? undefined : end);
    const fieldsHtml = cut === -1 ? html : html.slice(0, cut) + (end === -1 ? '' : html.slice(end));
    const sections = [...fieldsHtml.matchAll(/<section class="detail-section publication[\s\S]*?<\/section>/g)].map(m => m[0]);
    const r = { card: region(html), fields: region(fieldsHtml), source: region(sourceHtml),
      publications: region(sections.join(' ')) };
    report.records += 1;

    const hits = [...fieldsHtml.matchAll(GARBAGE_RE)].filter(m => {
      // Only text counts; an attribute value or a tag name is not visible.
      const before = fieldsHtml.slice(0, m.index);
      return before.lastIndexOf('<') <= before.lastIndexOf('>');
    });
    if (hits.length) {
      report.garbage.records += 1;
      note('renderedGarbage', pid);
      const fieldsHere = new Set();
      for (const m of hits) {
        report.garbage.tokens[m[0]] = (report.garbage.tokens[m[0]] || 0) + 1;
        fieldsHere.add(rowKeyAt(fieldsHtml, m.index));
      }
      for (const key of fieldsHere) report.garbage.fields[key] = (report.garbage.fields[key] || 0) + 1;
    }

    for (const [key, value] of Object.entries(entry)) {
      if (isEmpty(value)) continue;
      const place = RECORD_PLACES[key];
      if (!place) { report.undeclared[`record.${key}`] = (report.undeclared[`record.${key}`] || 0) + 1; continue; }
      const where = place(entry, r, ctx);
      tally(report.recordFields, key, where);
      if (where === null) note(`record.${key}`, pid);
    }

    const text = entry.fullBibliographicEntry || '';
    const looseText = loose(text);
    for (const key of RECORD_VALUES) {
      if (isEmpty(entry[key]) || !looseText.includes(loose(entry[key]))) continue;
      report.chains.recordValues += 1;
      if (!chained(fieldsHtml, key)) report.chains.recordWithoutChain += 1;
    }

    const publications = side ? side.publications || [] : [];
    publications.forEach((pub, i) => {
      report.publications += 1;
      const block = region(sections[i] || '');
      for (const [key, value] of Object.entries(pub)) {
        if (isEmpty(value)) continue;
        const place = PUBLICATION_PLACES[key];
        if (!place) { report.undeclared[`publication.${key}`] = (report.undeclared[`publication.${key}`] || 0) + 1; continue; }
        const where = place(pub, block, entry, r);
        tally(report.publicationFields, key, where);
        if (where === null) note(`publication.${key}`, pid);
      }
      const slice = pub.sourceSlice || {};
      const passage = Number.isFinite(slice.textStart) && Number.isFinite(slice.textEnd)
        ? loose(text.slice(slice.textStart, slice.textEnd)) : '';
      for (const [key, values] of Object.entries(PUBLICATION_VALUES)) {
        for (const value of values(pub)) {
          if (!passage || !passage.includes(loose(value))) continue;
          report.chains.publicationValues += 1;
          if (!chained(block.html, key)) report.chains.publicationWithoutChain += 1;
        }
      }
    });
    if (side && (side.nameVariants || []).length) {
      const where = placeOfAll(side.nameVariants.map(v => v.name), r.fields);
      tally(report.publicationFields, 'nameVariants', where);
    }
  }
  return { report, examples };
}

test('every record field has a place in the card and every sourced value its chain', () => {
  const { report, examples } = measure();
  assert.deepStrictEqual(report.undeclared, {},
    `fields without a declared place in the card: ${JSON.stringify(report.undeclared)}`);
  const gaps = r => Object.fromEntries(Object.entries(r)
    .filter(([, row]) => row.absent || row.tooltipOnly)
    .map(([key, row]) => [key, { absent: row.absent, tooltipOnly: row.tooltipOnly }])
    .sort(([a], [b]) => a.localeCompare(b)));
  const actual = {
    recordFieldGaps: gaps(report.recordFields),
    publicationFieldGaps: gaps(report.publicationFields),
    chains: report.chains,
  };
  const garbage = sorted(report.garbage);
  if (process.env.RECORD_COVERAGE_WRITE === '1') {
    fs.writeFileSync(EXPECTED_PATH, `${JSON.stringify({ ...EXPECTED, gaps: actual,
      renderedGarbage: sorted(report.garbage) }, null, 1)}
`);
    return;
  }
  assert.deepStrictEqual(actual, EXPECTED.gaps,
    `the card coverage differs from tests/record_coverage_expected.json.\n`
    + `actual ${JSON.stringify(actual, null, 1)}\nexamples (page ids) ${JSON.stringify(examples)}`);
});

test('no card shows a failed stringification outside the quoted source, beyond the pinned cards', () => {
  const { report, examples } = measure();
  assert.deepStrictEqual(sorted(report.garbage), EXPECTED.renderedGarbage,
    `cards render [object Object], undefined or NaN differently from renderedGarbage in `
    + `tests/record_coverage_expected.json; lower it when the renderer is fixed.
`
    + `actual ${JSON.stringify(report.garbage)}
examples (page ids) ${JSON.stringify(examples.renderedGarbage)}`);
});

test('a hidden element places no field and discloses no chain', () => {
  const card = '<div class="meta-row" data-key="year" data-provenance-for="year"><span class="prov-badge prov-llm">LLM-enriched</span></div>'
    + '<div class="meta-row" data-key="title" data-provenance-for="title">A title</div>'
    + '<span hidden data-key="allYears"></span><span hidden data-provenance-for="timePeriod"><i class="prov-badge"></i></span>'
    + '<div hidden><span data-key="seeAlso" data-provenance-for="seeAlso" class="prov-badge"></span></div>';
  const html = stripHidden(card);
  assert.ok(marked(html, 'year') && marked(html, 'title'));
  assert.ok(!marked(html, 'allYears') && !marked(html, 'seeAlso'));
  assert.ok(chained(html, 'year'), 'a visible badge discloses the chain');
  assert.ok(!chained(html, 'title'), 'a row without a badge discloses no chain');
  assert.ok(!chained(html, 'timePeriod') && !chained(html, 'seeAlso'), 'hidden markers disclose no chain');
  assert.ok(!visible(html).includes('hidden'));
});

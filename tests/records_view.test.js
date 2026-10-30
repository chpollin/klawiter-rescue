/**
 * Pins the Records view (docs/js/records.js and its routes in docs/js/app.js).
 *
 * Records replaces the wiki catalogue. Its list lives under #records, and the
 * old #browse and a bare #q= land there by replace, so Back skips the old
 * form and every other parameter rides along; the record addresses that
 * citations carry keep their form. Back from a card returns to the place in
 * the list it was opened from. Print records exist only on this computer, so
 * a static host makes no print request and names no print record. A count of
 * the start page opens Records in its own unit, and the category pages whose
 * text carries bibliographic values reach a card like any other record.
 *
 * Every print value below is invented; no print text enters the repository.
 */
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const DOCS = path.join(__dirname, '..', 'docs');
const FlexSearch = require(path.join(DOCS, 'vendor', 'flexsearch.bundle.min.js'));

function read(file) {
  return fs.readFileSync(path.join(DOCS, 'js', file), 'utf8');
}

/** A DOM element as far as the render paths touch one. */
function element(id) {
  const classes = new Set();
  return {
    id, innerHTML: '', textContent: '', hidden: false, style: {}, dataset: {}, value: '',
    attrs: {}, focused: 0,
    classList: {
      add: c => classes.add(c), remove: c => classes.delete(c), contains: c => classes.has(c),
      toggle(c, on) {
        const want = on === undefined ? !classes.has(c) : !!on;
        if (want) classes.add(c); else classes.delete(c);
        return want;
      },
    },
    setAttribute(k, v) { this.attrs[k] = String(v); },
    getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; },
    removeAttribute(k) { delete this.attrs[k]; },
    hasAttribute(k) { return k in this.attrs; },
    addEventListener() {},
    focus() { this.focused += 1; },
    // A child asked for by selector, kept so a test can read what was set on it.
    children: {},
    querySelector(sel) {
      if (sel === 'h1') return null;
      if (!this.children[sel]) this.children[sel] = element(sel);
      return this.children[sel];
    },
    querySelectorAll() { return []; },
    insertAdjacentElement() {},
    insertAdjacentHTML() {},
  };
}

/**
 * The reader in one shared realm, as the browser's global scope has it, with
 * a history that keeps a state per entry and a fetch that records each URL.
 */
function desk({ hostname = 'localhost', responses = {} } = {}) {
  const location = { hash: '', pathname: '/', hostname, href: 'http://h/' };
  const stack = [{ hash: '', state: null }];
  let at = 0;
  const calls = [];
  const history = {
    get state() { return stack[at].state; },
    pushState(state, title, url) {
      stack.splice(at + 1);
      stack.push({ hash: url, state });
      at += 1;
      location.hash = url;
      calls.push(['push', url]);
    },
    replaceState(state, title, url) {
      stack[at] = { hash: url === location.href ? stack[at].hash : url, state };
      if (url !== location.href) location.hash = url;
      calls.push(['replace', url]);
    },
    back() {
      at -= 1;
      location.hash = stack[at].hash;
    },
  };
  // A link to a hash is a new history entry without a state.
  const follow = (hash) => {
    stack.splice(at + 1);
    stack.push({ hash, state: null });
    at += 1;
    location.hash = hash;
  };
  location.replace = (url) => {
    stack[at] = { hash: url, state: null };
    location.hash = url;
    calls.push(['location.replace', url]);
  };
  const elements = {};
  const fetched = [];
  // The header controls every view toggles; no list element is found unless a test says so.
  const plain = sel => (sel === '.header-search' || sel === '.sort-label' ? element(sel) : null);
  const ctx = {
    console, URLSearchParams, FlexSearch,
    setTimeout: () => 0,
    location, history, historyCalls: calls,
    window: { location, addEventListener() {}, scrollY: 0, scrolled: [],
      scrollTo(x, y) { this.scrolled.push(y); } },
    elements,
    document: {
      title: '',
      activeElement: null,
      addEventListener() {},
      getElementById(id) {
        if (!elements[id]) elements[id] = element(id);
        return elements[id];
      },
      querySelector(sel) { return (ctx.queried || plain)(sel); },
      querySelectorAll() { return []; },
      createElement: () => element('created'),
    },
    fetch(url, opts) {
      fetched.push(`${(opts && opts.method) || 'GET'} ${url}`);
      const body = responses[url];
      if (body === undefined) return Promise.resolve({ ok: false, status: 404, json: () => Promise.reject(new Error('404')) });
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) });
    },
    fetched,
    Edit: {
      reconciliation: {}, entryStatus: () => ({ status: 'unreviewed', pending: false }),
      pending: () => undefined, authorityClaimsFor: () => [], editionClaimsFor: () => [],
      openClaimOnValue: () => null, cardHint: () => '', triageHints: () => [], evidence: () => null,
      locationReconciliation: () => null, agentReconciliation: () => null, FIELD_LABELS: {},
    },
    Facets: { render() {} },
    Pages: { render() {}, isShown: () => false },
    JsonldPlayground: { init() {} },
  };
  vm.createContext(ctx);
  for (const file of ['constants.js', 'utils.js', 'record-card.js', 'records.js', 'app.js', 'home.js', 'detail.js']) {
    vm.runInContext(read(file), ctx);
  }
  const App = vm.runInContext('App', ctx);
  const Records = vm.runInContext('Records', ctx);
  const Home = vm.runInContext('Home', ctx);
  // The dynamic import of the print adapter never runs in this realm.
  Records._import = () => { throw new Error('no dynamic import in the vm path'); };
  return { ctx, App, Records, Home, follow, route(hash) {
    location.hash = hash;
    App._lastHash = null;
    App.handleRoute();
  } };
}

function entry(pid, extra = {}) {
  return Object.assign({ sourcePageId: pid, pageNamespace: 0, entryType: 'fiction',
    title: `Record ${pid}`, fullBibliographicEntry: `Text of record ${pid}.` }, extra);
}

function withEntries(env, entries) {
  env.App.data = { entries, redirects: {}, _meta: {} };
  env.App.entries = entries.filter(e => env.App.admitsRecord(e));
  env.App.entryMap = new Map(env.App.entries.map(e => [e.sourcePageId, e]));
  env.App.titleMap = new Map();
}

test('the old list addresses land on #records by replace, keeping every parameter', () => {
  const env = desk();
  withEntries(env, [entry(1), entry(2, { entryType: 'essay' })]);
  const calls = env.ctx.historyCalls;
  for (const [old, target] of [
    ['#browse', '#records'],
    ['#browse&sort=title', '#records&sort=title'],
    // Explore hands its whole selection over as #browse=1.
    ['#browse=1', '#records'],
    ['#browse&type=fiction&language=German&sort=year-desc', '#records&type=fiction&language=German&sort=year-desc'],
    ['#q=zweig', '#records&q=zweig'],
    ['#q=amok&type=fiction&sort=title', '#records&q=amok&type=fiction&sort=title'],
  ]) {
    calls.length = 0;
    env.route(old);
    assert.strictEqual(env.ctx.location.hash, target, old);
    // The old address gives way in place: nothing is pushed, so Back skips it.
    assert.deepStrictEqual(calls, [['location.replace', target]], old);
  }

  // The new address renders the list and only normalizes it.
  calls.length = 0;
  env.route('#records&type=fiction');
  assert.strictEqual(env.App.state.view, 'results');
  assert.strictEqual(env.App.state.records, true);
  assert.deepStrictEqual(JSON.parse(JSON.stringify(env.App.state.filters)), { type: 'fiction' });
  assert.ok(calls.every(([kind]) => kind === 'replace'), JSON.stringify(calls));
  assert.strictEqual(env.ctx.location.hash, '#records&type=fiction');

  // The whole list is an address of its own.
  env.route('#records');
  assert.strictEqual(env.App.state.view, 'results');
  assert.strictEqual(env.App.filtered.length, 2);
});

test('the record addresses and a cited facet hash keep their form', () => {
  const env = desk();
  withEntries(env, [entry(1, { review: { status: 'proposed' } }), entry(2)]);
  const calls = env.ctx.historyCalls;

  calls.length = 0;
  env.route('#category=Fiction');
  assert.strictEqual(env.ctx.location.hash, '#category=Fiction');
  assert.deepStrictEqual(calls, [], 'a cited facet hash is neither replaced nor normalized');
  assert.strictEqual(env.App.state.view, 'results');

  env.route('#review=proposed');
  assert.strictEqual(env.ctx.location.hash, '#review=proposed');
  assert.strictEqual(env.App.filtered.length, 1);

  // A choice made on such a list writes the canonical form.
  env.App.setFilter('type', 'fiction');
  assert.match(env.ctx.location.hash, /^#records&review=proposed&type=fiction$/);

  calls.length = 0;
  env.route('#entry=2');
  assert.strictEqual(env.ctx.location.hash, '#entry=2');
  assert.strictEqual(env.App.state.singleEntry, true);
  assert.ok(!calls.some(([kind]) => kind === 'location.replace'));

  // A permalink with a query keeps its route; the query does not redirect it.
  env.route('#entry=2&q=amok');
  assert.strictEqual(env.ctx.location.hash, '#entry=2&q=amok');

  env.App.data.redirects = { 'Old Name': 2 };
  env.route('#title=Old%20Name');
  assert.strictEqual(env.ctx.location.hash, 'entry=2');
});

test('Back returns to the card that was open and to the place in the list', () => {
  const env = desk();
  const records = [entry(1), entry(2), entry(3)];
  withEntries(env, records);
  const { App, Records, ctx } = env;
  const opened = [];
  const header = element('header');
  App.openCard = pid => opened.push(pid);
  App._listHeader = pid => (pid === 3 ? header : null);

  env.route('#records');
  // The reader opens the third card, scrolls to it and follows a link in it.
  ctx.queried = sel => (sel.includes('card-expanded') ? { dataset: { pid: '3' } } : element(sel));
  ctx.window.scrollY = 640;
  Records.saveSnapshot();
  assert.deepStrictEqual(JSON.parse(JSON.stringify(ctx.history.state.records)),
    { scrollY: 640, page: 0, printPage: 0, openPid: 3, printId: null });
  env.follow('#entry=1');
  App.handleRoute();
  assert.strictEqual(App.state.singleEntry, true);
  assert.deepStrictEqual(opened, [1], 'the permalink opens its own card');

  // Back: the list renders again, its card opens and the page scrolls back.
  ctx.queried = null;
  ctx.window.scrolled.length = 0;
  ctx.history.back();
  App.handleRoute();
  assert.strictEqual(App.state.view, 'results');
  assert.strictEqual(App.state.singleEntry, false);
  assert.deepStrictEqual(opened, [1, 3]);
  assert.ok(ctx.window.scrolled.includes(640), JSON.stringify(ctx.window.scrolled));
  assert.ok(header.focused > 0, 'the focus returns to the card it left');

  // A fresh visit of the same address starts at its top with no card open.
  ctx.window.scrolled.length = 0;
  env.follow('#records');
  App._lastHash = null;
  App.handleRoute();
  assert.deepStrictEqual(opened, [1, 3]);
  assert.ok(!ctx.window.scrolled.includes(640));
});

test('Back to a list paged further renders its pages again before the card opens', () => {
  const env = desk();
  const records = Array.from({ length: 120 }, (_, i) => entry(i + 1));
  withEntries(env, records);
  const { App, Records, ctx } = env;
  const opened = [];
  App.openCard = pid => opened.push(pid);
  App._listHeader = () => null;
  env.route('#records');
  App.state.page = 2;   // the reader loaded the third page
  ctx.queried = sel => (sel.includes('card-expanded') ? { dataset: { pid: '117' } } : element(sel));
  Records.saveSnapshot();
  env.follow('#entry=5');
  App.handleRoute();
  ctx.queried = null;
  ctx.history.back();
  App.handleRoute();
  assert.strictEqual(App.state.page, 2);
  const list = ctx.elements['results-list'].innerHTML;
  assert.match(list, /data-pid="117"/, 'the third page stands again');
  assert.deepStrictEqual(opened, [5, 117]);
});

/** A rendered start page and Records list, as a reader of the host sees them. */
async function shown(env) {
  withEntries(env, [entry(1, { publicationCount: 2 }), entry(2)]);
  env.App.data._meta = { publicationCoverage: { pages: 1, publications: 2 } };
  env.route('');
  await env.Home.loadPrint();
  env.Home.render(env.App.entries);
  const home = env.ctx.elements['view-home'].innerHTML;
  env.route('#records');
  await env.Records.probePrint();
  env.Records.afterRender(null);
  const records = ['records-source', 'records-print', 'results-count', 'results-list']
    .map(id => env.ctx.elements[id].innerHTML + env.ctx.elements[id].textContent).join('');
  return { home, records, all: home + records };
}

// What would hint at local print data: its addresses, its server, a source
// control, or a count of print records. The start page's sentence on how print
// entries and wiki pages meet describes the bibliography and stays.
const PRINT_HINT = /\/viewer|\/review|\/print\b|review_server|print records?|\d print (?:objects?|entr(?:y|ies))|records-source-set|src=print|Print cards/i;

test('a static host makes no print request and names no print record', async () => {
  const env = desk({ hostname: 'chpollin.github.io' });
  const html = (await shown(env)).all;
  assert.deepStrictEqual(env.ctx.fetched, [], 'not even the print structure is asked for');
  assert.doesNotMatch(html, PRINT_HINT);
  assert.strictEqual(env.ctx.elements['records-source'].hidden, true);
  assert.strictEqual(env.ctx.elements['records-print'].hidden, true);

  // An address that asks for print shows the wiki records and writes none.
  env.route('#records&src=print&vol=I');
  assert.strictEqual(env.Records.state.source, 'wiki');
  assert.strictEqual(env.ctx.location.hash, '#records');

  // A print permalink resolves to nothing, in words that name no print source.
  env.route('#print=X%2FA%2F1%231');
  await new Promise(resolve => setImmediate(resolve));
  const list = env.ctx.elements['results-list'];
  assert.match(list.innerHTML, /missing-page-message/);
  const words = list.children['.missing-page-message'].textContent;
  assert.strictEqual(words, 'This record address does not resolve here.');
  assert.doesNotMatch(list.innerHTML + words + env.ctx.elements['results-count'].textContent, PRINT_HINT);
  assert.deepStrictEqual(env.ctx.fetched, []);

  // The page source itself carries no local address or print control.
  const index = fs.readFileSync(path.join(DOCS, 'index.html'), 'utf8');
  assert.doesNotMatch(index, /\/viewer|\/review|\/print\b|cards\.html/);
  assert.doesNotMatch(read('app.js'), /cards\.html|Print cards/);
});

test('on localhost each print step asks only after the one before it answered', async () => {
  // A fresh clone on a plain static server: no structure file.
  let env = desk();
  let html = await shown(env);
  assert.deepStrictEqual(env.ctx.fetched, ['GET local/print-structure.json']);
  assert.doesNotMatch(html.all, PRINT_HINT);

  // A static server with the structure file but without the review server:
  // the start page shows the print counts of that file as text, as before,
  // and Records shows the wiki alone.
  env = desk({ responses: { 'local/print-structure.json': { volumes: {}, totals: {} } } });
  html = await shown(env);
  assert.deepStrictEqual(env.ctx.fetched, ['GET local/print-structure.json', 'GET /review/status']);
  assert.doesNotMatch(html.records, PRINT_HINT);
  assert.doesNotMatch(html.home, /src=print|\/viewer|entries · open in Records/);
  assert.strictEqual(env.ctx.elements['records-source'].hidden, true);

  // The review server without a print index imports nothing.
  env = desk({ responses: { 'local/print-structure.json': { volumes: {}, totals: {} },
    '/review/status': { recording: false } } });
  let imported = 0;
  env.Records._import = () => { imported += 1; return Promise.resolve({}); };
  await shown(env);
  assert.deepStrictEqual(env.ctx.fetched,
    ['GET local/print-structure.json', 'GET /review/status', 'HEAD /viewer/index.json']);
  assert.strictEqual(imported, 0);
  assert.strictEqual(env.Records.print.status, 'unavailable');
});

/** A print adapter over invented objects: two entries, three objects. */
function printModule(seen) {
  const objects = [
    { kind: 'print', id: 'X/F/1#1', entry: 'X/F/1', title: 'Invented title one' },
    { kind: 'print', id: 'X/F/1#2', entry: 'X/F/1', title: 'Invented title two' },
    { kind: 'print', id: 'X/F/2#1', entry: 'X/F/2', title: 'Invented title three' },
  ];
  return {
    loaded: 0,
    load() { this.loaded += 1; return Promise.resolve(); },
    list(filter) { seen.push(JSON.parse(JSON.stringify(filter))); return objects; },
    model(id) {
      const o = objects.find(x => x.id === id);
      return o ? Object.assign({
        titleValue: { text: o.title, producer: 'rule', chain: { passage: { gap: 'source' } } },
        groups: [{ rows: [{ key: 'year', label: 'Year',
          values: [{ text: '1901', producer: 'rule', chain: { passage: { gap: 'not-located' } } }] }] }],
      }, o) : null;
    },
  };
}

async function printDesk(seen) {
  const structure = { volumes: { I: { F: { kind: 'body', entries: 2 } } },
    totals: { I: { numbered: 2, unnumbered: 0, publications: 3, other: 0, values: 9 } } };
  const env = desk({ responses: { 'local/print-structure.json': structure,
    '/review/status': { recording: true }, '/viewer/index.json': [] } });
  const mod = printModule(seen);
  env.Records._import = (url) => {
    assert.strictEqual(url, '/viewer/records-print.js');
    return Promise.resolve(mod);
  };
  withEntries(env, [entry(1, { publicationCount: 2 }), entry(2, { publicationCount: 1 }), entry(3)]);
  env.App.data._meta = { publicationCoverage: { pages: 2, publications: 3 } };
  assert.strictEqual(await env.Records.probePrint(), true);
  return { env, mod, structure };
}

test('a start-page count opens Records in its own unit', async () => {
  const seen = [];
  const { env, mod, structure } = await printDesk(seen);
  const { App, Records, Home } = env;
  await Home.loadPrint();
  assert.strictEqual(Home.printReady, true);
  const counts = { fiction: 3 };
  const model = Home.model(App.entries, counts, structure);
  const table = Home.table(counts, [], structure);

  // A count of print entries opens the entries; a count of objects the objects.
  assert.match(table, /href="#records&amp;src=print&amp;vol=I&amp;part=F&amp;unit=entry"[^>]*>2</);
  assert.match(model, /href="#records&amp;src=print&amp;unit=entry"><b>2<\/b> numbered/);
  assert.match(model, /href="#records&amp;src=print"><b>3<\/b> publications/);
  // A count of values has no list to open.
  assert.match(model, /<b>9<\/b> values with passage/);
  assert.doesNotMatch(model, /<a[^>]*><b>9<\/b>/);

  const hrefOf = (html, re) => re.exec(html)[1].replace(/&amp;/g, '&');
  const entriesHref = hrefOf(table, /href="(#records[^"]*part=F[^"]*)"/);
  env.route('');
  assert.strictEqual(App.state.view, 'home');
  env.route(entriesHref);
  assert.strictEqual(Records.state.source, 'print');
  assert.strictEqual(Records.state.unit, 'entry');
  // Followed from the start page, the list draws its slips although the view
  // switches only after the list rendered.
  await new Promise(resolve => setImmediate(resolve));
  await new Promise(resolve => setImmediate(resolve));
  const section = env.ctx.elements['records-print'];
  assert.strictEqual(section.hidden, false);
  assert.strictEqual((section.innerHTML.match(/class="records-slip"/g) || []).length, 2);
  assert.match(section.innerHTML, /2 objects in this entry/);
  assert.strictEqual(env.ctx.elements['results-count'].textContent, '2 print entries: Main volume, section F');
  const entries = await Records.printItems('');
  assert.strictEqual(entries.length, 2, 'two entries, not their three objects');
  assert.strictEqual(entries[0].count, 2);
  assert.deepStrictEqual(seen.at(-1), { q: '', volume: 'I', part: 'F', kind: '' });
  assert.strictEqual(Records._countLabel(entries.length), '2 print entries: Main volume, section F');
  // The address the list writes back keeps its unit.
  App.updateURL(false);
  assert.strictEqual(App._lastHash, 'records&src=print&vol=I&part=F&unit=entry');

  env.route(hrefOf(model, /href="(#records&amp;src=print)"/));
  const objects = await Records.printItems('');
  assert.strictEqual(objects.length, 3);
  assert.strictEqual(Records._countLabel(objects.length), '3 print objects');
  assert.strictEqual(mod.loaded, 1, 'the print index loads once');

  // A slip that names no entry is never counted as one.
  assert.throws(() => Records.groupByUnit([{ id: 'X/F/3#1' }], 'entry'), /names no entry/);
  assert.strictEqual(Records.groupByUnit([{ id: 'X/F/3#1' }], 'object').length, 1);

  // A count of wiki pages opens those pages, and the publications of the wiki
  // open the pages that carry them.
  assert.match(model, /<a href="#records"><b>3<\/b> pages<\/a>/);
  assert.match(model, /<b>3<\/b> publications on <a href="#records&amp;layer=publication"><b>2<\/b> pages<\/a>/);
  env.route('#records&layer=publication');
  assert.strictEqual(App.filtered.length, 2);
  assert.match(App._resultsLabel(App.filtered.length), /^2 entries: with publications$/);
});

test('an address that asks for print keeps asking until this computer has answered', async () => {
  const structure = { volumes: {}, totals: {} };
  const env = desk({ responses: { 'local/print-structure.json': structure,
    '/review/status': { recording: true }, '/viewer/index.json': [] } });
  env.Records._import = () => Promise.resolve(printModule([]));
  withEntries(env, [entry(1)]);
  // The route arrives before the answer: the wiki stands, the address stays.
  env.route('#records&src=print&vol=I&unit=entry');
  assert.strictEqual(env.Records.state.source, 'wiki');
  assert.strictEqual(env.ctx.location.hash, '#records&src=print&vol=I&unit=entry');
  // The answer routes it again, to the print records it asked for.
  env.App._watchPrint();
  await env.Records.probePrint();
  await new Promise(resolve => setImmediate(resolve));
  assert.strictEqual(env.Records.state.source, 'print');
  assert.strictEqual(env.Records.state.unit, 'entry');
  assert.strictEqual(env.ctx.location.hash, '#records&src=print&vol=I&unit=entry');

  // Where the answer is no, the request leaves the address.
  const none = desk();
  withEntries(none, [entry(1)]);
  await none.Records.probePrint();
  none.route('#records&src=print&vol=I');
  assert.strictEqual(none.ctx.location.hash, '#records');
});

test('a print record has its own address and a card drawn by the shared component', async () => {
  const seen = [];
  const { env } = await printDesk(seen);
  const id = 'X/F/1#2';
  assert.strictEqual(env.Records.printHash(id), '#print=X%2FF%2F1%232');
  env.route(env.Records.printHash(id));
  await new Promise(resolve => setImmediate(resolve));
  await new Promise(resolve => setImmediate(resolve));
  const card = env.ctx.elements['results-list'].innerHTML;
  assert.match(card, /<article class="rc-card" data-kind="print" data-record="X\/F\/1#2">/);
  assert.match(card, /<a class="rc-id" href="#print=X%2FF%2F1%232">X\/F\/1#2<\/a>/);
  assert.match(card, /Invented title two/);
  assert.strictEqual(env.ctx.elements['results-count'].textContent, 'Permalink — 1 print record');
  // Its chains, the title's in the head among them, are where the shared
  // chain handler finds them, so no producer button is dead.
  const Detail = vm.runInContext('Detail', env.ctx);
  const chainIds = [...card.matchAll(/aria-controls="([^"]+)"/g)].map(m => m[1]);
  assert.strictEqual(chainIds.length, 2);
  assert.match(Detail.chainHtml(chainIds[0]), /not given in the source/);
  assert.match(Detail.chainHtml(chainIds[1]), /passage not located/);

  // The list of a print source draws slips that lead to that address.
  env.route('#records&src=print');
  await new Promise(resolve => setImmediate(resolve));
  await new Promise(resolve => setImmediate(resolve));
  const section = env.ctx.elements['records-print'];
  assert.strictEqual(section.hidden, false);
  assert.match(section.innerHTML, /href="#print=X%2FF%2F1%231"/);
  assert.strictEqual((section.innerHTML.match(/class="records-slip"/g) || []).length, 3);
  assert.match(env.ctx.elements['records-source'].innerHTML, /value="print" checked/);
  assert.strictEqual(env.ctx.elements['results-list'].innerHTML, '', 'no wiki list beside a print-only source');
});

test('category pages whose text carries bibliographic values reach a card and the search', () => {
  const env = desk();
  const { App } = env;
  // The criterion, on invented pages.
  assert.strictEqual(App.admitsRecord(entry(1)), true);
  assert.strictEqual(App.admitsRecord({ pageNamespace: 14, title: 'Fiction', fullBibliographicEntry: '' }), false);
  assert.strictEqual(App.admitsRecord({ pageNamespace: 14, title: 'A history',
    fullBibliographicEntry: 'A history' }), false, 'a heading only');
  assert.strictEqual(App.admitsRecord({ pageNamespace: 14, title: '',
    fullBibliographicEntry: 'Category:Fiction' }), false, 'a damaged self-reference');
  assert.strictEqual(App.admitsRecord({ pageNamespace: 14, title: 'Dramas / Volumes (X)',
    fullBibliographicEntry: '[1968]: Invented Press, Nowhere', year: 1968 }), true);
  assert.strictEqual(App.admitsRecord({ pageNamespace: 8, title: 'Main',
    fullBibliographicEntry: '* navigation', year: 2000 }), false, 'infrastructure pages stay out');

  // The real holding: exactly the category pages the data reach audit named.
  const data = JSON.parse(fs.readFileSync(path.join(DOCS, 'data', 'klawiter.json'), 'utf8'));
  const admitted = data.entries.filter(e => App.admitsRecord(e) && e.pageNamespace !== 0)
    .map(e => e.sourcePageId).sort((a, b) => a - b);
  assert.deepStrictEqual(admitted, [919, 1396, 1495, 2185, 3374, 3516, 3787, 4567, 4590, 7437, 7438]);
  assert.strictEqual(data.entries.filter(e => App.admitsRecord(e) && e.pageNamespace === 0).length,
    data.entries.filter(e => e.pageNamespace === 0).length);

  App.data = data;
  App.entries = data.entries.filter(e => App.admitsRecord(e));
  App.entryMap = new Map(App.entries.map(e => [e.sourcePageId, e]));
  App.titleMap = new Map(App.entries.filter(e => e.title && e.pageNamespace === 0).map(e => [e.title, e.sourcePageId]));
  const Detail = vm.runInContext('Detail', env.ctx);
  App.state.singleEntry = true;
  for (const pid of admitted) {
    const e = App.entryMap.get(pid);
    const html = App.renderCard(e) + Detail.renderInline(e);
    assert.match(html, new RegExp(`Wiki page ${pid}<`), pid);
    assert.match(html, /<span class="badge rc-type">Category page<\/span>/, pid);
    assert.match(html, /Klawiter source/, pid);
    assert.doesNotMatch(html, /\[object Object\]|undefined</, pid);
  }

  // Page 7437 is found by a word of its own text.
  App.state.singleEntry = false;
  App.buildIndex();
  App.state.query = 'heqqide';
  assert.ok(App._queryBase().some(e => e.sourcePageId === 7437));
});

test('a cited print address opens its entry by exact address, and an absent one says why', async () => {
  const env = desk();
  const { Records } = env;
  const models = [
    { id: 'I/G/131#1', entry: 'I/G/131', address: 'G 131', volume: 'I', part: 'G' },
    { id: 'I/G/65#1', entry: 'I/G/65', address: 'G 65', volume: 'I', part: 'G' },
  ];
  Records.print = { status: 'available', module: { load() {}, list: () => models, model() {} }, structure: {} };
  Records._load = Promise.resolve();

  const cite = { printAddress: 'G 131', printVolume: 'main-volume', printSection: 'G', citationTarget: 'entry' };
  const href = Records.printCitationHref(cite);
  assert.strictEqual(href, '#records&src=print&vol=I&part=G&unit=entry&addr=G%20131');
  Records.fromParams(new URLSearchParams(href.slice('#records&'.length)));
  const hits = await Records.printItems('');
  assert.strictEqual(hits.map(h => h.model.id).join(), 'I/G/131#1', 'a record that only mentions it is no hit');

  // A section citation opens the section, and a host without print links nothing.
  assert.doesNotMatch(Records.printCitationHref({ ...cite, citationTarget: 'section' }), /addr=/);
  Records.state.address = 'H 670';
  assert.match(Records._emptyWords(), /No print record of the .* carries the address H 670\. The wiki may cite it in another numbering/);
  Records.print = { status: 'unavailable', module: null, structure: null };
  assert.strictEqual(Records.printCitationHref(cite), '');
});

/**
 * Pins the URL contract of docs/js/app.js and the title language attributes
 * that go with the rendered cards.
 *
 * Route guard: history.replaceState in updateURL fires no hashchange, so
 * updateURL must keep _lastHash in sync. Without it, every return to the start
 * view after filtering (logo click, clearing the last filter chip, emptying
 * the search) is swallowed by the guard as "unchanged hash".
 *
 * Sort state: the selected order is part of the hash, so reload and back
 * reproduce it, while the default order leaves the hash clean.
 */
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function loadAppCtx() {
  const location = { hash: '', pathname: '/', hostname: 'localhost' };
  // A redirect replaces the history entry; the stub records where it lands.
  location.replace = (url) => { location.hash = url; };
  const calls = [];
  const ctx = {
    window: { location, addEventListener() {} },
    document: { addEventListener() {}, getElementById() { return null; },
      querySelectorAll() { return []; } },
    location,
    history: {
      replaceState(a, b, url) { calls.push(['replace', url]); },
      pushState(a, b, url) { calls.push(['push', url]); },
    },
    historyCalls: calls,
    URLSearchParams,
    console,
  };
  vm.createContext(ctx);
  const source = fs.readFileSync(
    path.join(__dirname, '..', 'docs', 'js', 'app.js'),
    'utf8'
  );
  // Top-level `const App` never reaches the context object; evaluate the
  // identifier as the script's completion value instead.
  const App = vm.runInContext(source + '\nApp', ctx);
  return { App, ctx };
}

function loadApp() {
  return loadAppCtx().App;
}

// constants.js and utils.js are plain script files sharing one global scope;
// evaluating both in a context gives access to titleAttrs.
function loadUtils() {
  const ctx = { console };
  vm.createContext(ctx);
  for (const file of ['constants.js', 'utils.js']) {
    vm.runInContext(
      fs.readFileSync(path.join(__dirname, '..', 'docs', 'js', file), 'utf8'),
      ctx
    );
  }
  return vm.runInContext('titleAttrs', ctx);
}

test('title attributes mark romanized titles with the -Latn subtag', () => {
  const titleAttrs = loadUtils();

  // Klawiter transliterated non-Latin scripts; the script subtag keeps a
  // screen reader from voicing Latin letters with Arabic phonetics.
  assert.strictEqual(
    titleAttrs({ languageCode: 'ar' }, 'Al-Umm al-ʿāshiqah'),
    ' lang="ar-Latn" dir="auto"'
  );
  // A title actually written in its own script keeps the bare code.
  assert.strictEqual(
    titleAttrs({ languageCode: 'he' }, 'מרי אנטואנט'),
    ' lang="he" dir="auto"'
  );
  // Latin-script languages never get a subtag.
  assert.strictEqual(
    titleAttrs({ languageCode: 'de' }, 'Sternstunden der Menschheit'),
    ' lang="de" dir="auto"'
  );
  // No or malformed code: direction only.
  assert.strictEqual(titleAttrs({}, 'Untitled'), ' dir="auto"');
  assert.strictEqual(titleAttrs({ languageCode: 'Deutsch' }, 'x'), ' dir="auto"');
  assert.strictEqual(titleAttrs(null, null), ' dir="auto"');
});

test('updateURL keeps the route guard in sync with the replaced hash', () => {
  const App = loadApp();
  App._lastHash = '';

  App.state.query = 'zweig';
  App.state.filters = { type: 'fiction' };
  App.updateURL();
  // Every list is written under Records.
  assert.strictEqual(App._lastHash, 'records&q=zweig&type=fiction');

  // Clearing query and filters replaces the hash with '': the guard must
  // treat the next explicit navigation to '' as already-current state, and
  // a later navigation to a REAL hash as a change.
  App.state.query = '';
  App.state.filters = {};
  App.updateURL();
  assert.strictEqual(App._lastHash, '');
});

test('the sort state travels in the hash, the default one does not', () => {
  const App = loadApp();
  App.state.query = 'zweig';
  App.state.filters = {};

  App.state.sort = 'relevance';
  App.updateURL();
  assert.strictEqual(App._lastHash, 'records&q=zweig');

  App.state.sort = 'year-desc';
  App.updateURL();
  assert.strictEqual(App._lastHash, 'records&q=zweig&sort=year-desc');

  // The whole list keeps its marker, so a sorted list survives a reload.
  App.state.query = '';
  App.state.records = true;
  App.state.sort = 'title';
  App.updateURL();
  assert.strictEqual(App._lastHash, 'records&sort=title');
});

test('a hash sort value round-trips and unknown values fall back', () => {
  const App = loadApp();
  App.state.query = '';
  App.state.filters = { type: 'fiction' };
  App.state.records = false;
  App.state.sort = 'year-asc';
  App.updateURL();

  const back = new URLSearchParams(App._lastHash);
  assert.strictEqual(App.sortFromParams(back), 'year-asc');
  assert.strictEqual(back.get('type'), 'fiction');

  assert.strictEqual(App.sortFromParams(new URLSearchParams('')), 'relevance');
  assert.strictEqual(App.sortFromParams(new URLSearchParams('sort=chaos')), 'relevance');
});

test('the triage sort is only honoured while edit mode is on', () => {
  const App = loadApp();
  const params = new URLSearchParams('sort=triage');
  App.state.editMode = false;
  assert.strictEqual(App.sortFromParams(params), 'relevance');
  App.state.editMode = true;
  assert.strictEqual(App.sortFromParams(params), 'triage');
});

test('only a hash-addressable result list writes the sort back to the URL', () => {
  const App = loadApp();
  App.state.view = 'results';
  App.state.query = '';
  App.state.filters = {};
  App.state.records = false;
  // Workbench lists derive from artifacts and carry no hash of their own.
  assert.strictEqual(App.isAddressableResults(), false);
  App.state.records = true;
  assert.strictEqual(App.isAddressableResults(), true);
  App.state.records = false;
  App.state.query = 'zweig';
  assert.strictEqual(App.isAddressableResults(), true);
  App.state.view = 'stats';
  assert.strictEqual(App.isAddressableResults(), false);
});

test('the old deep links resolve to their place in the Documentation page', () => {
  const App = loadApp();
  // The single pages of the first layout, then the About and Data pages and
  // their section anchors: every published hash keeps working.
  for (const [old, target] of [
    ['methodology', 'docs/method'],
    ['imprint', 'docs/imprint'],
    ['jsonld', 'docs/playground'],
    ['about', 'docs'],
    ['about/methodology', 'docs/method'],
    ['about/imprint', 'docs/imprint'],
    ['about/unknown', 'docs'],
    ['data', 'docs/data'],
    ['data/model', 'docs/model'],
    ['data/spec', 'docs/spec'],
    ['data/downloads', 'docs/downloads'],
    ['data/playground', 'docs/playground'],
    // The card's playground link carries the page id along.
    ['data/playground/42', 'docs/playground/42'],
    ['data/unknown', 'docs/data'],
    ['quality', 'data/quality'],
  ]) {
    assert.strictEqual(App._legacyTarget(old), target, old);
  }
  // The workbench keeps its address, and the new page is no legacy route.
  assert.strictEqual(App.QUALITY_ROUTE, 'data/quality');
  assert.strictEqual(App._legacyTarget('data/quality'), null);
  assert.strictEqual(App._legacyTarget('docs'), null);
  assert.strictEqual(App._legacyTarget('docs/method'), null);
  // Help is a dialog now, not a section a hash could land on.
  assert.deepStrictEqual([...App.HELP_ROUTES], ['help', 'about/help']);
});

test('a legacy hash replaces its history entry rather than rendering', () => {
  const { App, ctx } = loadAppCtx();
  let rendered = false;
  ctx.Pages = { render() { rendered = true; }, isShown: () => false };
  App._lastHash = null;
  ctx.location.hash = '#methodology';
  App.handleRoute();
  assert.strictEqual(ctx.location.hash, '#docs/method');
  assert.strictEqual(rendered, false);

  App._lastHash = null;
  ctx.location.hash = '#about/imprint';
  App.handleRoute();
  assert.strictEqual(ctx.location.hash, '#docs/imprint');

  App._lastHash = null;
  ctx.location.hash = '#data/playground/42';
  App.handleRoute();
  assert.strictEqual(ctx.location.hash, '#docs/playground/42');

  // The workbench hash takes the same path, so it never reaches the branch
  // that would render it under its old address.
  App._lastHash = null;
  ctx.location.hash = '#quality';
  App.handleRoute();
  assert.strictEqual(ctx.location.hash, '#data/quality');
});

test('the workbench route renders the workbench, not the Documentation page', () => {
  const { App, ctx } = loadAppCtx();
  const seen = [];
  App.showView = (v) => { App.state.view = v; };
  App._resetSearchState = () => {};
  ctx.Curate = { render() { seen.push('curate'); } };
  ctx.Pages = { render(slug) { seen.push(slug); }, isShown: () => false };
  App._lastHash = null;
  ctx.location.hash = '#data/quality';
  App.handleRoute();
  assert.deepStrictEqual(seen, ['curate']);
  assert.strictEqual(ctx.location.hash, '#data/quality');
});

test('a Documentation hash carries an optional section suffix', () => {
  const { App, ctx } = loadAppCtx();
  const seen = [];
  let shown = false;
  App.showView = (v) => { App.state.view = v; };
  App._scrollToSection = (s) => seen.push(`scroll:${s}`);
  App._focusViewStart = () => seen.push('focus');
  ctx.window.scrollTo = () => seen.push('top');
  ctx.Pages = { render(slug) { seen.push(slug); shown = true; }, isShown: () => shown };

  App._lastHash = null;
  ctx.location.hash = '#docs/method';
  App.handleRoute();
  assert.deepStrictEqual(seen, ['docs', 'scroll:method']);

  // A move to another section of the page already shown scrolls only, so the
  // page is not drawn again under the reader.
  seen.length = 0;
  ctx.location.hash = '#docs/downloads';
  App.handleRoute();
  assert.deepStrictEqual(seen, ['scroll:downloads']);

  seen.length = 0;
  ctx.location.hash = '#docs';
  App.handleRoute();
  assert.deepStrictEqual(seen, ['top', 'focus']);

  // A playground address with a page id loads that entry, so it renders.
  seen.length = 0;
  ctx.location.hash = '#docs/playground/42';
  App.handleRoute();
  assert.deepStrictEqual(seen, ['docs', 'scroll:playground']);
});

test('the help hashes open the help dialog over the Documentation page', () => {
  const { App, ctx } = loadAppCtx();
  const seen = [];
  App.showView = (v) => { App.state.view = v; };
  App._scrollToSection = () => {};
  App.openHelp = () => seen.push('help');
  ctx.Pages = { render(slug) { seen.push(slug); }, isShown: () => false };

  for (const hash of ['#about/help', '#help']) {
    seen.length = 0;
    App._lastHash = null;
    ctx.location.hash = hash;
    App.handleRoute();
    // The old address gives way to the page, and the dialog opens once there.
    assert.strictEqual(ctx.location.hash, '#docs', hash);
    assert.deepStrictEqual(seen, [], hash);
    App.handleRoute();
    assert.deepStrictEqual(seen, ['docs', 'help'], hash);
    App._lastHash = null;
    App.handleRoute();
    assert.deepStrictEqual(seen, ['docs', 'help', 'docs'], `${hash}: opens once`);
  }
});

test('the help dialog fills on first open, and closing it returns focus to its button', () => {
  const { App, ctx } = loadAppCtx();
  const listeners = {};
  const btn = {
    focused: 0,
    addEventListener(type, fn) { listeners[`btn:${type}`] = fn; },
    focus() { this.focused += 1; },
  };
  const dialog = {
    open: false,
    addEventListener(type, fn) { listeners[`dialog:${type}`] = fn; },
    showModal() { this.open = true; },
    close() { this.open = false; listeners['dialog:close'](); },
    closest: () => null,
  };
  const body = { childElementCount: 0, innerHTML: '' };
  const elements = { 'help-btn': btn, 'help-dialog': dialog, 'help-dialog-body': body };
  ctx.document.getElementById = (id) => elements[id] || null;
  ctx.Pages = { help: () => '<h3>Search, browse, filter</h3>' };

  App._bindHelp();
  App._bindHelp();   // bound once, whatever calls it again
  listeners['btn:click']();
  assert.strictEqual(dialog.open, true);
  assert.match(body.innerHTML, /Search, browse, filter/);

  // Escape is the native cancel of a modal dialog and ends in its close event.
  dialog.close();
  assert.strictEqual(btn.focused, 1);

  // A click on the backdrop lands on the dialog element itself.
  App.openHelp();
  listeners['dialog:pointerdown']({ target: dialog });
  listeners['dialog:click']({ target: dialog });
  assert.strictEqual(dialog.open, false);
  assert.strictEqual(btn.focused, 2);

  // A text selection that starts in the box and ends over the backdrop clicks
  // the dialog element too, and must not close it.
  App.openHelp();
  const text = { closest: () => null };
  listeners['dialog:pointerdown']({ target: text });
  listeners['dialog:click']({ target: dialog });
  assert.strictEqual(dialog.open, true);
  dialog.close();
  assert.strictEqual(btn.focused, 3);

  // A link inside the help leads to a view that takes the focus itself.
  App.openHelp();
  const routed = [];
  App.handleRoute = () => routed.push(ctx.location.hash);
  const link = { hash: '#docs/method', closest: (sel) => (sel.startsWith('a[') ? link : null) };
  listeners['dialog:click']({ target: link });
  assert.strictEqual(dialog.open, false);
  assert.strictEqual(btn.focused, 3);
  assert.deepStrictEqual(routed, [], 'a new address routes through hashchange');

  // A link to the address already shown fires no hashchange, so it is routed.
  ctx.location.hash = '#docs/method';
  App._lastHash = 'docs/method';
  App.openHelp();
  listeners['dialog:click']({ target: link });
  assert.strictEqual(dialog.open, false);
  assert.strictEqual(btn.focused, 3);
  assert.deepStrictEqual(routed, ['#docs/method']);
  assert.strictEqual(App._lastHash, null);
});

test('the navigation names Records and Documentation as the tab title does', () => {
  const html = fs.readFileSync(path.join(__dirname, '..', 'docs', 'index.html'), 'utf8');
  const nav = html.match(/<nav class="site-nav"[^>]*>([\s\S]*?)<\/nav>/)[1];
  const labels = [...nav.matchAll(/<a [^>]*>([^<]*)<\/a>/g)].map(m => m[1]);
  // Explore stays until it becomes an arrangement of the records; Edit joins
  // on localhost from app.js.
  assert.deepStrictEqual(labels, ['Overview', 'Records', 'Explore', 'Documentation']);
  assert.match(nav, /href="#records" id="nav-records"/);
  assert.match(nav, /href="#docs" id="nav-docs"/);
  assert.doesNotMatch(html, /#browse|Wiki catalogue/);
  // The print workbench is no item of the reader's navigation any more.
  assert.doesNotMatch(fs.readFileSync(path.join(__dirname, '..', 'docs', 'js', 'app.js'), 'utf8'),
    /nav-print-cards|Print cards|cards\.html/);
  // The imprint and the citation stand in the footer, not in the navigation.
  const footer = html.match(/<footer[\s\S]*<\/footer>/)[0];
  assert.match(footer, /<a href="#docs\/imprint">Imprint<\/a>/);
  assert.match(footer, /<a href="#docs\/citation">How to cite<\/a>/);
  assert.doesNotMatch(html, /#about|href="#data"/);
  // Help is a native dialog opened from the header.
  assert.match(html, /<button type="button" id="help-btn"[^>]*aria-controls="help-dialog"/);
  assert.match(html, /<dialog id="help-dialog"[^>]*aria-labelledby="help-dialog-title"/);
});

test('the edit toggle shows only where entry cards can be edited', () => {
  const { App, ctx } = loadAppCtx();
  const btn = { style: {} };
  ctx.document.getElementById = () => btn;

  for (const [hash, view, visible] of [
    ['', 'home', true],
    ['#q=zweig', 'results', true],
    ['#records&q=zweig', 'results', true],
    ['#print=I%2FA%2F1%231', 'results', false],
    ['#data/quality', 'page', true],
    ['#docs', 'page', false],
    ['#docs/method', 'page', false],
    // The workbench keeps the former Data address; the playground section of
    // the Documentation page stays a plain text page for the toggle.
    ['#docs/playground', 'page', false],
    ['#stats', 'stats', false],
  ]) {
    ctx.location.hash = hash;
    App.state.view = view;
    App._updateEditToggleVisibility();
    assert.strictEqual(btn.style.display, visible ? '' : 'none', `${hash} / ${view}`);
  }
});

test('a user-triggered state change is a history entry, a normalization is not', () => {
  const { App, ctx } = loadAppCtx();
  App._lastHash = '';
  App.state.query = '';
  App.state.filters = {};

  // Choosing a facet, removing a chip, submitting a search: places Back has to
  // return to. Before, every one of them replaced the entry, so the first
  // interaction made Back leave the application.
  App.state.filters = { type: 'fiction' };
  App.updateURL(true);
  assert.deepStrictEqual(ctx.historyCalls.at(-1), ['push', '#records&type=fiction']);

  // Re-rendering a state that is already in the URL only normalizes it.
  App.updateURL(false);
  assert.deepStrictEqual(ctx.historyCalls.at(-1), ['replace', '#records&type=fiction']);

  // A push that would duplicate the current entry stays a replace.
  App.updateURL(true);
  assert.deepStrictEqual(ctx.historyCalls.at(-1), ['replace', '#records&type=fiction']);

  App.state.filters = { type: 'essay' };
  App.updateURL(true);
  assert.deepStrictEqual(ctx.historyCalls.at(-1), ['push', '#records&type=essay']);
  assert.strictEqual(App._lastHash, 'records&type=essay');
});

test('the skip-link fragment is not treated as a route', () => {
  const { App, ctx } = loadAppCtx();
  App._lastHash = 'q=zweig';
  ctx.location.hash = '#main-content';
  App.handleRoute();
  // The route state is untouched: skipping to the content must not throw the
  // reader back to the start view.
  assert.strictEqual(App._lastHash, 'q=zweig');
});

test('an unresolvable title reports the missing page instead of falling through', () => {
  const { App, ctx } = loadAppCtx();
  const seen = [];
  App.data = {};   // no redirect map at all: the access must be guarded
  App.titleMap = new Map();
  App.showView = (v) => { App.state.view = v; };
  App._resetSearchState = () => {};
  App._setResultsContext = () => {};
  App.renderChips = () => {};
  App._renderMissingPage = (msg) => seen.push(msg);
  ctx.Facets = { render() {} };

  App._lastHash = null;
  ctx.location.hash = '#title=Nonexistent%20Page';
  App.handleRoute();
  assert.strictEqual(App.state.view, 'results');
  assert.strictEqual(seen.length, 1);
  assert.match(seen[0], /does not exist/);
});

test('a known title resolves to its entry permalink', () => {
  const { App, ctx } = loadAppCtx();
  App.data = { redirects: { 'Old Name': 4711 } };
  App.titleMap = new Map([['Real Title', 42]]);
  App._resetSearchState = () => {};
  App._setResultsContext = () => {};

  App._lastHash = null;
  ctx.location.hash = '#title=Old%20Name';
  App.handleRoute();
  assert.strictEqual(ctx.location.hash, 'entry=4711');

  App._lastHash = null;
  ctx.location.hash = '#title=Real%20Title';
  App.handleRoute();
  assert.strictEqual(ctx.location.hash, 'entry=42');
});

test('edit mode cannot be entered on the published site', () => {
  const App = loadApp();
  App.state.isLocal = false;
  App.state.editMode = false;
  App.toggleEditMode();
  assert.strictEqual(App.state.editMode, false);
});

test('a permalink tab names its entry, and the base title matches index.html', () => {
  const { App, ctx } = loadAppCtx();
  const html = fs.readFileSync(path.join(__dirname, '..', 'docs', 'index.html'), 'utf8');
  assert.strictEqual(html.match(/<title>([^<]*)<\/title>/)[1], App.BASE_TITLE);

  App.state.singleEntry = true;
  App.filtered = [{ sourcePageId: 774, title: 'Amok' }];
  App._updateTitle('results');
  assert.strictEqual(ctx.document.title, `Amok — ${App.BASE_TITLE}`);

  App.state.singleEntry = false;
  App._updateTitle('results');
  assert.strictEqual(ctx.document.title, `Records — ${App.BASE_TITLE}`);

  ctx.location.hash = '#docs/method';
  App._updateTitle('page');
  assert.strictEqual(ctx.document.title, `Documentation — ${App.BASE_TITLE}`);
});

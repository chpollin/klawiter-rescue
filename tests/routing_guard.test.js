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
  assert.strictEqual(App._lastHash, 'q=zweig&type=fiction');

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
  assert.strictEqual(App._lastHash, 'q=zweig');

  App.state.sort = 'year-desc';
  App.updateURL();
  assert.strictEqual(App._lastHash, 'q=zweig&sort=year-desc');

  // Browse keeps its own marker so a sorted catalogue view survives a reload.
  App.state.query = '';
  App.state.browse = true;
  App.state.sort = 'title';
  App.updateURL();
  assert.strictEqual(App._lastHash, 'browse=&sort=title');
});

test('a hash sort value round-trips and unknown values fall back', () => {
  const App = loadApp();
  App.state.query = '';
  App.state.filters = { type: 'fiction' };
  App.state.browse = false;
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
  App.state.browse = false;
  // Workbench lists derive from artifacts and carry no hash of their own.
  assert.strictEqual(App.isAddressableResults(), false);
  App.state.browse = true;
  assert.strictEqual(App.isAddressableResults(), true);
  App.state.browse = false;
  App.state.query = 'zweig';
  assert.strictEqual(App.isAddressableResults(), true);
  App.state.view = 'stats';
  assert.strictEqual(App.isAddressableResults(), false);
});

test('the old deep links still resolve to their merged section', () => {
  const App = loadApp();
  // The four static pages were merged into #about and #data; the hashes that
  // were published before must keep working.
  assert.strictEqual(App.LEGACY_ROUTES.methodology, 'about/methodology');
  assert.strictEqual(App.LEGACY_ROUTES.help, 'about/help');
  assert.strictEqual(App.LEGACY_ROUTES.imprint, 'about/imprint');
  assert.strictEqual(App.LEGACY_ROUTES.jsonld, 'data/playground');
  // #data itself is a page of its own and must not redirect.
  assert.strictEqual(App.LEGACY_ROUTES.data, undefined);
  assert.strictEqual(App.LEGACY_ROUTES.quality, undefined);
});

test('a legacy hash is rewritten rather than rendered', () => {
  const { App, ctx } = loadAppCtx();
  App._lastHash = null;
  ctx.location.hash = '#methodology';
  App.handleRoute();
  assert.strictEqual(ctx.location.hash, 'about/methodology');
});

test('a page hash carries an optional section suffix', () => {
  const { App, ctx } = loadAppCtx();
  const seen = [];
  App.showView = (v) => { App.state.view = v; };
  App._scrollToSection = (s) => seen.push(`scroll:${s}`);
  ctx.Pages = { render(slug) { seen.push(slug); } };

  App._lastHash = null;
  ctx.location.hash = '#about/help';
  App.handleRoute();
  assert.deepStrictEqual(seen, ['about', 'scroll:help']);

  seen.length = 0;
  App._lastHash = null;
  ctx.location.hash = '#data';
  App.handleRoute();
  assert.deepStrictEqual(seen, ['data']);
});

test('the edit toggle shows only where entry cards can be edited', () => {
  const { App, ctx } = loadAppCtx();
  const btn = { style: {} };
  ctx.document.getElementById = () => btn;

  for (const [hash, view, visible] of [
    ['', 'home', true],
    ['#q=zweig', 'results', true],
    ['#quality', 'page', true],
    ['#about/help', 'page', false],
    ['#data', 'page', false],
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
  assert.deepStrictEqual(ctx.historyCalls.at(-1), ['push', '#type=fiction']);

  // Re-rendering a state that is already in the URL only normalizes it.
  App.updateURL(false);
  assert.deepStrictEqual(ctx.historyCalls.at(-1), ['replace', '#type=fiction']);

  // A push that would duplicate the current entry stays a replace.
  App.updateURL(true);
  assert.deepStrictEqual(ctx.historyCalls.at(-1), ['replace', '#type=fiction']);

  App.state.filters = { type: 'essay' };
  App.updateURL(true);
  assert.deepStrictEqual(ctx.historyCalls.at(-1), ['push', '#type=essay']);
  assert.strictEqual(App._lastHash, 'type=essay');
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

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

function loadApp() {
  const location = { hash: '', pathname: '/', hostname: 'localhost' };
  const ctx = {
    window: { location, addEventListener() {} },
    document: { addEventListener() {}, getElementById() { return null; } },
    location,
    history: { replaceState() {} },
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
  return vm.runInContext(source + '\nApp', ctx);
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

test('edit mode cannot be entered on the published site', () => {
  const App = loadApp();
  App.state.isLocal = false;
  App.state.editMode = false;
  App.toggleEditMode();
  assert.strictEqual(App.state.editMode, false);
});

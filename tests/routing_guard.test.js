/**
 * Pins the route-guard contract of docs/js/app.js: history.replaceState in
 * updateURL fires no hashchange, so updateURL must keep _lastHash in sync.
 * Without it, every return to the start view after filtering (logo click,
 * clearing the last filter chip, emptying the search) is swallowed by the
 * guard as "unchanged hash".
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
    document: { addEventListener() {} },
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

test('edit mode cannot be entered on the published site', () => {
  const App = loadApp();
  App.state.isLocal = false;
  App.state.editMode = false;
  App.toggleEditMode();
  assert.strictEqual(App.state.editMode, false);
});

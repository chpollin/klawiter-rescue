/**
 * Pins the pure logic the Explore views were given so their readings stay
 * honest: the translator field is split into the people it actually names,
 * recognizably cut-off values are excluded, numbers are formatted the same
 * way everywhere, and a year range handed over from Explore resolves to the
 * same bounds the results route filters on.
 */
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

// constants.js and utils.js are plain script files sharing one global scope.
function loadUtils(name) {
  const ctx = { console };
  vm.createContext(ctx);
  for (const file of ['constants.js', 'utils.js']) {
    vm.runInContext(
      fs.readFileSync(path.join(__dirname, '..', 'docs', 'js', file), 'utf8'),
      ctx
    );
  }
  return vm.runInContext(name, ctx);
}

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
  return vm.runInContext(source + '\nApp', ctx);
}

test('a joint translator credit is split into the people it names', () => {
  const splitTranslators = loadUtils('splitTranslators');
  // String comparison: the arrays come from a vm realm, whose prototypes fail
  // deepStrictEqual's cross-realm identity check.
  assert.strictEqual(
    JSON.stringify(splitTranslators('Eden and Cedar Paul')),
    JSON.stringify(['Eden', 'Cedar Paul'])
  );
  assert.strictEqual(
    JSON.stringify(splitTranslators('Anthea Bell & Nicholas Jacobs')),
    JSON.stringify(['Anthea Bell', 'Nicholas Jacobs'])
  );
  assert.strictEqual(
    JSON.stringify(splitTranslators('Hans Meyer und Erika Weber')),
    JSON.stringify(['Hans Meyer', 'Erika Weber'])
  );
});

test('a single translator survives splitting unchanged', () => {
  const splitTranslators = loadUtils('splitTranslators');
  assert.strictEqual(
    JSON.stringify(splitTranslators('Anthea Bell')),
    JSON.stringify(['Anthea Bell'])
  );
  // Names carrying a nobiliary particle are not joint credits
  assert.strictEqual(
    JSON.stringify(splitTranslators('Ludwig von Ficker')),
    JSON.stringify(['Ludwig von Ficker'])
  );
});

test('recognizably cut-off values are dropped rather than counted', () => {
  const splitTranslators = loadUtils('splitTranslators');
  const isTruncatedName = loadUtils('isTruncatedName');

  assert.strictEqual(isTruncatedName('Eden and'), true);
  assert.strictEqual(isTruncatedName('Translated by'), true);
  assert.strictEqual(isTruncatedName('Cedar Paul-'), true);
  assert.strictEqual(isTruncatedName('Cedar Paul…'), true);
  assert.strictEqual(isTruncatedName(''), true);
  assert.strictEqual(isTruncatedName('Cedar Paul'), false);
  assert.strictEqual(isTruncatedName('Cedar P.'), false);

  // A credit cut off after the conjunction yields no complete name, so it
  // contributes nothing rather than a guess at the first half.
  assert.strictEqual(JSON.stringify(splitTranslators('Eden and')), JSON.stringify([]));
  assert.strictEqual(JSON.stringify(splitTranslators('')), JSON.stringify([]));
});

test('translator keys read a record the same way the filter does', () => {
  const translatorKeys = loadUtils('translatorKeys');
  assert.strictEqual(
    JSON.stringify(translatorKeys({ translator: 'Eden and Cedar Paul' })),
    JSON.stringify(['Eden', 'Cedar Paul'])
  );
  assert.strictEqual(JSON.stringify(translatorKeys({})), JSON.stringify([]));
});

test('numbers are formatted once, in one place', () => {
  const fmt = loadUtils('fmt');
  assert.strictEqual(fmt(1234567), '1,234,567');
  assert.strictEqual(fmt(0), '0');
  assert.strictEqual(fmt(null), '0');
  assert.strictEqual(fmt('—'), '—');
});

test('a decade or year range from Explore resolves to inclusive bounds', () => {
  const App = loadApp();
  assert.strictEqual(JSON.stringify(App.yearBounds({ decade: '1930' })), '[1930,1939]');
  assert.strictEqual(JSON.stringify(App.yearBounds({ years: '1930-1940' })), '[1930,1940]');
  assert.strictEqual(App.yearBounds({ years: '1930-' })[1], Infinity);
  assert.strictEqual(App.yearBounds({ years: '-1940' })[0], -Infinity);
  assert.strictEqual(App.yearBounds({}), null);
  // The decade wins over a stale range, matching Explore's handover order
  assert.strictEqual(
    JSON.stringify(App.yearBounds({ decade: '1950', years: '1900-1910' })),
    '[1950,1959]'
  );
});

test('the results route accepts every filter key Explore hands over', () => {
  const App = loadApp();
  for (const key of ['publisher', 'translator', 'years', 'decade', 'location', 'language', 'type', 'period']) {
    assert.ok(App.FILTER_KEYS.includes(key), `${key} missing from FILTER_KEYS`);
    assert.ok(App.FILTER_LABELS[key], `${key} has no chip label`);
  }
});

/**
 * Pins the acceptance view (docs/acceptance/acceptance.js) against the
 * hand-made report in tests/fixtures/acceptance-report.json.
 *
 * The view draws one report of pipeline/acceptance.py: milestones with their
 * pass counts, checks whose failing examples open the record card, the
 * coverage ledger grouped by disposition, and samples whose values light up
 * their passage in the source entry. Every report string is escaped, and a
 * span counts code points as Python slices the entry.
 */
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const docs = file => fs.readFileSync(path.join(__dirname, '..', 'docs', file), 'utf8');
const report = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'acceptance-report.json'), 'utf8'));

function view() {
  const ctx = { console, URLSearchParams };
  vm.createContext(ctx);
  vm.runInContext(docs('js/record-card.js'), ctx);
  vm.runInContext(docs('acceptance/acceptance.js'), ctx);
  return vm.runInContext('AcceptanceView', ctx);
}

const V = view();
const clone = o => JSON.parse(JSON.stringify(o));
const text = html => html.replace(/<[^>]*>/g, '').replace(/&lt;/g, '<').replace(/&gt;/g, '>')
  .replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&amp;/g, '&');

/** Each mark of the entry as its text and the value indices it carries. */
const marks = html => [...html.matchAll(/<mark class="acc-mark" tabindex="0" data-values="([^"]*)">([^<]*)<\/mark>/g)]
  .map(m => ({ values: m[1], text: text(m[2]) }));

test('the fixture says it is a fixture, and the headline says so', () => {
  assert.strictEqual(report.generatedBy, 'fixture');
  const line = V.headline(report);
  assert.match(line, /Dataset 0\.9/);
  assert.match(line, /4,758 pages/);
  assert.match(line, /<code>23d8f11<\/code>/);
  assert.match(line, /acc-fixture-word">fixture</);
});

test('each milestone carries its state word and its pass count', () => {
  assert.strictEqual(V.passCount(report, 'D1'), '3 of 5 checks pass');
  assert.strictEqual(V.passCount(report, 'D2'), '0 of 2 checks pass');
  assert.strictEqual(V.passCount(report, 'P'), 'no checks yet');
  const html = V.program(report, { milestone: '', sample: '' });
  const items = [...html.matchAll(/<li class="acc-ms[^"]*" data-milestone="([^"]+)">([\s\S]*?)<\/li>/g)];
  assert.deepStrictEqual(items.map(m => m[1]), ['D1', 'D2', 'D3', 'D4', 'C1', 'P']);
  const d1 = text(items[0][2]);
  assert.match(d1, /in progress/);
  assert.match(d1, /3 of 5 checks pass/);
  assert.match(items[0][2], /acc-status-in-progress/);
  assert.match(text(items[3][2]), /blocked.*Blocked by: Needs the operator's VPN/s);
  // The status shape stands beside the word, so colour is never alone.
  assert.match(items[3][2], /<svg class="acc-status-icon"[^>]*>.*<\/svg>blocked/);
});

test('verified-by and accepted-by open on demand', () => {
  const html = V.program(report, { milestone: '', sample: '' });
  assert.match(html, /<details class="acc-ms-more"><summary>Verified and accepted by<\/summary><dl><dt>Verified by<\/dt>/);
});

test('selecting a milestone filters the checks and the link keeps the sample', () => {
  const state = { milestone: 'D2', sample: '9001' };
  const html = V.checks(report, state);
  const ids = [...html.matchAll(/data-check="([^"]+)"/g)].map(m => m[1]);
  assert.deepStrictEqual(ids, ['one-biblstruct-per-publication', 'fields-dispositioned']);
  assert.match(html, /Milestone D2, 0 of 2 checks pass/);
  assert.match(html, /href="\?sample=9001">Show all checks/);
  const all = V.checks(report, { milestone: '', sample: '' });
  assert.strictEqual([...all.matchAll(/data-check=/g)].length, report.checks.length);
  // The current milestone's link clears the filter; the others set theirs.
  const program = V.program(report, state);
  assert.match(program, /data-milestone="D2">[^]*?href="\?sample=9001" aria-current="true"/);
  assert.match(program, /data-milestone="D1">[^]*?href="\?m=D1&amp;sample=9001"/);
});

test('the query state round-trips', () => {
  assert.deepStrictEqual({ ...V.parseState('?m=D1&sample=212') }, { milestone: 'D1', sample: '212' });
  assert.deepStrictEqual({ ...V.parseState('') }, { milestone: '', sample: '' });
  assert.strictEqual(V.hrefFor({ milestone: 'C1', sample: '' }), '?m=C1');
  assert.strictEqual(V.hrefFor({ milestone: '', sample: '' }), './');
});

test('failing examples link to the record card; a page-less example stays text', () => {
  const html = V.check(report.checks.find(c => c.id === 'source-text-verbatim'));
  const links = [...html.matchAll(/<a href="([^"]+)">Page (\d+)<\/a>/g)].map(m => [m[1], m[2]]);
  assert.deepStrictEqual(links, [['../#entry=1187', '1187'], ['../#entry=2290', '2290']]);
  assert.match(html, /<li>One redirect page without a page id<\/li>/);
  assert.match(html, /3 failed of 4,758 checked/);
  assert.match(html, /acc-status-fail/);
  const open = V.check(report.checks.find(c => c.id === 'print-out-of-sourcedesc'));
  assert.doesNotMatch(open, /checked/);
});

test('every report string is escaped, including < in values and details', () => {
  const html = V.check(report.checks.find(c => c.id === 'source-text-verbatim'));
  assert.ok(html.includes('&#39;&amp;&#39; written as &#39;&amp;amp;amp;&#39; in &lt;quote&gt;'));
  assert.ok(!html.includes('<quote>'));
  const sample = V.sample(report, { milestone: '', sample: '9001' });
  assert.ok(sample.includes('Ungeduld des Herzens &lt;Auszug&gt;'));
  assert.ok(!/<Auszug>/.test(sample));
  const hostile = clone(report);
  hostile.program[0].title = '<img src=x onerror=alert(1)>';
  hostile.coverage[0].field = '"><script>';
  hostile.acceptance[0].question = '<b>bold</b>';
  const page = V.page(hostile, { milestone: '', sample: '' });
  assert.ok(!page.includes('<img src=x'));
  assert.ok(!page.includes('<script>'));
  assert.ok(!page.includes('<b>bold'));
});

test('highlight spans sit at their offsets in the entry', () => {
  const s = report.samples[0];
  const got = marks(V.entryHtml(s));
  const expected = [...V.flatValues(s)].filter(x => x.v.span).map(x => ({ values: String(x.index), text: x.v.value }));
  assert.deepStrictEqual(got, expected);
  // The unmarked text survives untouched, so the entry reads as the source.
  assert.strictEqual(text(V.entryHtml(s)), s.entry);
});

test('the TEI fragment is shown escaped and complete', () => {
  const s = report.samples[1];
  const html = V.teiHtml(s.tei);
  assert.strictEqual(text(html), s.tei);
  assert.ok(!html.includes('<biblStruct'));
  assert.match(html, /<span class="acc-tag">&lt;biblStruct<\/span>/);
});

test('spans count code points, and overlapping spans split into shared segments', () => {
  const sample = {
    entry: '𝔄 Wien, Leipzig: Insel',
    publications: [{ id: 'X.1', values: [
      { field: 'place', value: 'Wien, Leipzig', span: [2, 15], producer: 'regex', state: 'not-reviewed' },
      { field: 'place', value: 'Leipzig', span: [8, 15], producer: 'llm', state: 'proposed' },
      { field: 'publisher', value: 'Insel', span: [17, 22], producer: 'regex', state: 'not-reviewed' },
      { field: 'year', value: '1931', span: [20, 99], producer: 'regex', state: 'not-reviewed' },
    ] }],
  };
  assert.deepStrictEqual(marks(V.entryHtml(sample)), [
    { values: '0', text: 'Wien, ' },
    { values: '0 1', text: 'Leipzig' },
    { values: '2', text: 'Insel' },
  ]);
  const values = V.valuesList(sample);
  assert.match(values, /1931<\/span>[^]*span outside the entry/);
});

test('a value without a passage shows its gap word and takes no highlight', () => {
  const html = V.valuesList(report.samples[0]);
  const rows = [...html.matchAll(/<li class="acc-value([^"]*)"([^>]*)>([\s\S]*?)<\/li>/g)];
  const title = rows.find(r => /acc-value-field">title</.test(r[3]));
  assert.match(title[1], /has-gap/);
  assert.doesNotMatch(title[2], /data-values/);
  assert.match(title[3], /acc-gap">page title</);
  const language = rows.find(r => /acc-value-field">language</.test(r[3]));
  assert.match(language[3], /category link in the wiki markup/);
  const translator = rows.find(r => /acc-value-field">translator</.test(r[3]));
  assert.match(translator[2], /tabindex="0" data-values="1"/);
});

test('values carry the record-card producer signs and state words', () => {
  const html = V.valuesList(report.samples[1]);
  assert.match(html, /rc-family-rule[^]*?<span>rule<\/span>/);
  assert.match(html, /rc-family-llm[^]*?<span>LLM-enriched<\/span>/);
  assert.match(html, /rc-family-person[^]*?<span>expert-curated<\/span>/);
  assert.match(html, /acc-state-contested">contested</);
  assert.match(html, /text differs from passage/);
  assert.doesNotMatch(html, /regex/);
  const sample = V.sample(report, { milestone: '', sample: '9001' });
  assert.match(sample, /class="rc-legend"/);
  assert.match(sample, /<a href="\.\.\/#entry=9001">Page 9001<\/a>/);
});

test('an unknown sample falls back to the first, and the selector marks the current one', () => {
  const html = V.sample(report, { milestone: '', sample: '77' });
  assert.match(html, /<a data-state href="\?sample=212" aria-current="true">/);
  assert.doesNotMatch(html, /href="\?sample=9001" aria-current/);
});

test('coverage groups fields by disposition, pending ones with their milestone', () => {
  const html = V.coverage(report);
  const groups = [...html.matchAll(/data-disposition="([^"]+)"[\s\S]*?(?=<section|$)/g)]
    .map(m => [m[1], [...m[0].matchAll(/data-field="([^"]+)"/g)].map(f => f[1])]);
  assert.deepStrictEqual(groups, [
    ['exported', ['title', 'translator', 'editor', 'place', 'publisher', 'year', 'extent', 'language']],
    ['pending', ['series', 'edition', 'contents', 'work hub']],
    ['excluded', ['categories', 'lastEditor']],
  ]);
  assert.match(html, /data-field="translator">[^]*?1,412 records[^]*?<code>monogr\/respStmt<\/code>/);
  assert.match(html, /data-field="series">[^]*?due in D2; Series in a source entry/);
  assert.match(html, /data-field="lastEditor">[^]*?Wiki revision metadata/);
});

test('the operator decisions list open ones first, with milestone and state word', () => {
  const html = V.acceptance(report);
  assert.match(html, /3 open, 1 decided\./);
  const ids = [...html.matchAll(/data-decision="([^"]+)"/g)].map(m => m[1]);
  assert.deepStrictEqual(ids.at(-1), 'stylesheet-route');
  assert.match(html, /acc-status-accepted/);
});

test('a missing report shows one sentence with the generator command and nothing else', () => {
  const html = V.missing('');
  assert.strictEqual((html.match(/<[a-z]+[\s>]/g) || []).length, 2);
  assert.match(html, /python -m uv run python pipeline\/acceptance\.py/);
  assert.doesNotMatch(html, /<(a|button|input|select)\b/);
});

test('the page links its assets inside docs and loads record-card.js first', () => {
  const html = docs('acceptance/index.html');
  const scripts = [...html.matchAll(/<script src="([^"]+)"/g)].map(m => m[1]);
  assert.deepStrictEqual(scripts, ['../js/record-card.js', 'acceptance.js']);
  assert.doesNotMatch(html, /https?:\/\/(?!www\.w3)/);
  assert.match(docs('acceptance/acceptance.js'), /REPORT_URL: '\.\.\/local\/acceptance\.json'/);
});

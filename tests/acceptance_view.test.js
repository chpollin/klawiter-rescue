/**
 * Pins the acceptance view (docs/acceptance/acceptance.js) against the
 * hand-made report in tests/fixtures/acceptance-report.json.
 *
 * The view is a decision view: one plain line per milestone, failing checks
 * above the decisions, one card per decision in report order with the sample
 * pages it rests on, and the check report folded below. Values light up their
 * passage in the source entry, every report string is escaped, and a span
 * counts code points as Python slices the entry.
 */
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const docs = file => fs.readFileSync(path.join(__dirname, '..', 'docs', file), 'utf8');
const report = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'acceptance-report.json'), 'utf8'));

function view() {
  const ctx = { console };
  vm.createContext(ctx);
  vm.runInContext(docs('js/record-card.js'), ctx);
  vm.runInContext(docs('acceptance/acceptance.js'), ctx);
  return vm.runInContext('AcceptanceView', ctx);
}

const V = view();
const clone = o => JSON.parse(JSON.stringify(o));
const text = html => html.replace(/<[^>]*>/g, '').replace(/&lt;/g, '<').replace(/&gt;/g, '>')
  .replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&amp;/g, '&');
const decisionOf = id => V.decision(report, report.acceptance.find(a => a.id === id));

/** Each mark of the entry as its text and the value indices it carries. */
const marks = html => [...html.matchAll(/<mark class="acc-mark" tabindex="0" data-values="([^"]*)">([^<]*)<\/mark>/g)]
  .map(m => ({ values: m[1], text: text(m[2]) }));

test('the fixture says it is a fixture, and the headline says so', () => {
  assert.strictEqual(report.generatedBy, 'fixture');
  const line = V.headline(report);
  assert.match(line, /Dataset 0\.9/);
  assert.match(line, /<code>23d8f11<\/code>/);
  assert.match(line, /acc-fixture-word">fixture</);
});

test('each milestone is one plain line of checks and decisions', () => {
  const lines = Object.fromEntries([...V.program(report).matchAll(/data-milestone="([^"]+)">([\s\S]*?)<\/li>/g)]
    .map(m => [m[1], text(m[2])]));
  assert.deepStrictEqual(Object.keys(lines), ['D1', 'D2', 'D3', 'D4', 'C1', 'P']);
  assert.strictEqual(lines.D1, 'D1 Faithful export3 of 5 checks pass, 1 fail, 1 open, no decision open');
  assert.strictEqual(lines.D2, 'D2 Complete model0 of 2 checks pass, 2 fail, 3 decisions open');
  assert.strictEqual(lines.D3, 'D3 SZD page local0 of 1 check passes, 1 skipped, no decision open, 1 decided');
  assert.match(lines.D4, /^D4 Stagingno checks yet, no decision open, blocked: Needs the operator's VPN/);
  assert.match(V.program(report), /<a href="#E8">3 decisions open<\/a>/);
  // No goal paragraph and no empty disclosure in the program.
  assert.doesNotMatch(V.program(report), /<details|acc-ms-goal|Verified/);
});

test('failing checks stand expanded above the decisions; the check report is folded below', () => {
  const page = V.page(report, {});
  const failing = page.indexOf('id="acc-failing"');
  const decisions = page.indexOf('id="acc-decisions"');
  const checkReport = page.indexOf('<details class="acc-section acc-report"');
  assert.ok(failing > 0 && failing < decisions && decisions < checkReport);
  const fails = V.failing(report);
  assert.deepStrictEqual([...fails.matchAll(/data-check="([^"]+)"/g)].map(m => m[1]),
    ['source-text-verbatim', 'one-biblstruct-per-publication', 'fields-dispositioned']);
  assert.doesNotMatch(page, /<details[^>]*acc-report[^>]* open/);
  const passing = clone(report);
  passing.checks.forEach(c => { if (c.status === 'fail') c.status = 'pass'; });
  assert.strictEqual(V.failing(passing), '');
  assert.doesNotMatch(V.page(passing, {}), /acc-failing/);
});

test('decision cards follow the report order with question, why, recommendation and state', () => {
  const html = V.decisions(report);
  assert.deepStrictEqual([...html.matchAll(/<article class="acc-decision[^"]*" id="([^"]+)"/g)].map(m => m[1]),
    ['E8', 'E6', 'E3', 'E1']);
  const e8 = decisionOf('E8');
  assert.match(e8, /<h3 id="E8-h"><span class="acc-decision-id">E8<\/span> Should pages classified otherwise/);
  assert.match(text(e8), /Recommendation Yes: the publication layer reads the entry itself/);
  assert.match(e8, /acc-status-open/);
  assert.match(html, /3 open, 1 decided\. Answer in the chat with the id, such as "E8 yes"\./);
  // Answering happens in the chat: the page renders no control for it.
  assert.doesNotMatch(V.page(report, {}), /<(button|input|select|textarea|form)\b/);
});

test('a recorded answer shows with its date', () => {
  assert.match(text(decisionOf('E1')), /Answer: yes, 2026-10-30/);
  assert.match(decisionOf('E1'), /acc-status-accepted/);
  assert.doesNotMatch(decisionOf('E8'), /acc-answer/);
});

test('a card embeds its evidence pages with the look sentence above each', () => {
  const e6 = decisionOf('E6');
  const pages = [...e6.matchAll(/<div class="acc-sample" data-page="(\d+)"><p class="acc-look">([^<]*)<\/p>/g)]
    .map(m => [m[1], text(m[2])]);
  assert.deepStrictEqual(pages, [
    ['212', 'Each value and its marked passage, and the values the language model supplied.'],
    ['9001', 'Whether the page splits into the publications Klawiter lists.'],
  ]);
  assert.match(e6, /<a href="\.\.\/#entry=9001">Page 9001<\/a>/);
  // One legend per card, covering the signs of all its samples.
  assert.strictEqual((e6.match(/class="rc-legend"/g) || []).length, 1);
  assert.match(e6, /rc-legend-item rc-family-person/);
  assert.strictEqual((decisionOf('E1').match(/rc-legend/g) || []).length, 0);
});

test('publications left out of the export say so and carry no TEI', () => {
  const e8 = decisionOf('E8');
  assert.strictEqual((e8.match(/read from the entry, not in the export/g) || []).length, 5);
  assert.match(e8, /5 publications, none in the export/);
  assert.doesNotMatch(e8, /<summary>TEI<\/summary>/);
  assert.match(e8, /<summary>TEI of the source entry<\/summary>/);
});

test('long publication lists fold after the first three behind a native disclosure', () => {
  const html = V.publications(report.samples.find(s => s.page === 8800));
  const [shown, folded] = html.split('<details class="acc-pubs-more">');
  assert.strictEqual((shown.match(/data-publication=/g) || []).length, 3);
  assert.strictEqual((folded.match(/data-publication=/g) || []).length, 2);
  assert.match(folded, /^<summary>Show all 5 publications<\/summary><ol class="acc-pubs" start="4">/);
  // Two publications do not fold.
  assert.doesNotMatch(V.publications(report.samples.find(s => s.page === 9001)), /acc-pubs-more/);
});

test('each exported publication has its own TEI behind a disclosure, dedented', () => {
  const s = report.samples.find(x => x.page === 9001);
  const one = V.teiOfPublication(s.tei, 'SZDKLA.9001.1');
  assert.match(one, /^<biblStruct xml:id="SZDKLA\.9001\.1"/);
  assert.match(one, /\n<\/biblStruct>$/);
  assert.doesNotMatch(one, /SZDKLA\.9001\.2/);
  assert.match(one, /\n  <monogr>/);
  const html = V.publications(s);
  assert.strictEqual((html.match(/<details class="acc-tei-more"><summary>TEI<\/summary>/g) || []).length, 2);
  assert.strictEqual(text(V.teiHtml(one)), one);
  assert.match(V.teiOfSource(report.samples[0].tei), /^<bibl type="wikiPage"[\s\S]*<\/bibl>$/);
});

test('an entry without publications says so', () => {
  const e3 = decisionOf('E3');
  assert.match(e3, /No publication is read from this entry\./);
  assert.match(e3, /A foreword/);
});

test('failing examples link to the record card; a page-less example stays text', () => {
  const html = V.check(report.checks.find(c => c.id === 'source-text-verbatim'));
  const links = [...html.matchAll(/<a href="([^"]+)">Page (\d+)<\/a>/g)].map(m => [m[1], m[2]]);
  assert.deepStrictEqual(links, [['../#entry=1187', '1187'], ['../#entry=2290', '2290']]);
  assert.match(html, /<li>One redirect page without a page id<\/li>/);
  assert.match(html, /3 failed of 4,758 checked/);
  const open = V.check(report.checks.find(c => c.id === 'print-out-of-sourcedesc'));
  assert.doesNotMatch(open, /checked/);
});

test('every report string is escaped, including < in values and details', () => {
  const html = V.check(report.checks.find(c => c.id === 'source-text-verbatim'));
  assert.ok(html.includes('&#39;&amp;&#39; written as &#39;&amp;amp;amp;&#39; in &lt;quote&gt;'));
  const e6 = decisionOf('E6');
  assert.ok(e6.includes('Ungeduld des Herzens &lt;Auszug&gt;'));
  assert.ok(!/<Auszug>/.test(e6));
  const hostile = clone(report);
  hostile.program[0].title = '<img src=x onerror=alert(1)>';
  hostile.coverage[0].field = '"><script>';
  hostile.acceptance[0].question = '<b>bold</b>';
  hostile.acceptance[0].evidence[0].look = '<i>look</i>';
  hostile.acceptance[0].id = '"><svg onload=1>';
  const page = V.page(hostile, {});
  assert.ok(!page.includes('<img src=x'));
  assert.ok(!page.includes('<script>'));
  assert.ok(!page.includes('<b>bold'));
  assert.ok(!page.includes('<i>look'));
  assert.ok(!page.includes('<svg onload'));
});

test('highlight spans sit at their offsets in the entry', () => {
  const s = report.samples[0];
  const got = marks(V.entryHtml(s));
  const expected = [...V.flatValues(s)].filter(x => x.v.span).map(x => ({ values: String(x.index), text: x.v.value }));
  assert.deepStrictEqual(got, expected);
  assert.strictEqual(text(V.entryHtml(s)), s.entry);
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
  assert.match(V.publications(sample), /1931<\/span>[^]*span outside the entry/);
});

test('gap kinds read as words, and a value without a passage takes no highlight', () => {
  const html = V.publications(report.samples[0]);
  const rows = [...html.matchAll(/<li class="acc-value([^"]*)"([^>]*)>([\s\S]*?)<\/li>/g)];
  const row = field => rows.find(r => new RegExp(`acc-value-field">${field}<`).test(r[3]));
  assert.match(row('title')[1], /has-gap/);
  assert.doesNotMatch(row('title')[2], /data-values/);
  assert.match(row('title')[3], /acc-gap">from the page title</);
  assert.match(row('language')[3], /from a category link in the wiki markup/);
  assert.match(row('translator')[2], /tabindex="0" data-values="1"/);
  assert.strictEqual(V.gapWord('repeated'), 'passage occurs more than once');
  assert.strictEqual(V.gapWord('not-verbatim'), 'not verbatim in the entry');
  assert.strictEqual(V.gapWord('not-located'), 'passage not located');
});

test('values carry the record-card producer signs and state words', () => {
  const html = V.publications(report.samples.find(s => s.page === 9001));
  assert.match(html, /rc-family-rule[^]*?<span>rule<\/span>/);
  assert.match(html, /rc-family-llm[^]*?<span>LLM-enriched<\/span>/);
  assert.match(html, /rc-family-person[^]*?<span>expert-curated<\/span>/);
  assert.match(html, /acc-state-contested">contested</);
  assert.match(html, /text differs from passage/);
  assert.doesNotMatch(html, /regex/);
});

test('the check report holds checks, values, the field ledger and unreferenced samples', () => {
  const html = V.checkReport(report);
  assert.match(html, /^<details class="acc-section acc-report" id="acc-report"><summary><h2>Check report<\/h2>/);
  assert.strictEqual([...html.matchAll(/data-check=/g)].length, report.checks.length);
  assert.match(html, /<dt>with a passage<\/dt>/);
  assert.deepStrictEqual([...html.matchAll(/class="acc-sample" data-page="(\d+)"/g)].map(m => m[1]), ['213']);
  assert.doesNotMatch(V.decisions(report), /data-page="213"/);
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
  assert.match(html, /data-field="translator">[^]*?1,412<[^]*?<code>monogr\/respStmt<\/code>/);
  assert.match(html, /data-field="series">[^]*?due in D2; Series in a source entry/);
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
  assert.doesNotMatch(html, /https?:\/\//);
  assert.match(docs('acceptance/acceptance.js'), /REPORT_URL: '\.\.\/local\/acceptance\.json'/);
});

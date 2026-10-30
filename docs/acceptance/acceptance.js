/**
 * Acceptance view: the operator's open decisions over one report of
 * pipeline/acceptance.py, each with the sample pages it rests on.
 *
 * Pure functions take the report object and return HTML strings, so
 * tests/acceptance_view.test.js renders them against a fixture; boot() alone
 * fetches the report, mounts the page and wires the span highlighting. The
 * producer signs, the legend and the state words come from
 * docs/js/record-card.js, loaded before this file, so a sign means here what
 * it means on a record card. Answers are given in the chat and recorded by
 * the generator; the page shows them and offers no control to answer.
 *
 * Trust boundary: every string from the report is escaped here; the only
 * unescaped markup is what these functions build from escaped parts and the
 * icon paths of RecordCard.
 */
const AcceptanceView = {
  REPORT_URL: '../local/acceptance.json',
  GENERATE: 'python -m uv run python pipeline/acceptance.py',
  // Publications shown before the rest folds behind a disclosure.
  VISIBLE_PUBLICATIONS: 3,

  esc(s) {
    return RecordCard.escape(s);
  },

  num(n) {
    return typeof n === 'number' ? n.toLocaleString('en-US') : this.esc(n == null ? '?' : n);
  },

  plural(n, one, many) {
    return `${this.num(n)} ${n === 1 ? one : many}`;
  },

  // A status is a shape and a word; the hue only repeats them.
  STATUS_SHAPES: {
    pass: '<path d="M2.5 6.5l2.5 2.5 4.5-6"/>',
    fail: '<path d="M3 3l6 6M9 3l-6 6"/>',
    open: '<circle cx="6" cy="6" r="3.5"/>',
    skipped: '<path d="M2.5 6h7"/>',
    accepted: '<path d="M2.5 6.5l2.5 2.5 4.5-6"/>',
    rejected: '<path d="M3 3l6 6M9 3l-6 6"/>',
  },

  status(state) {
    const key = Object.prototype.hasOwnProperty.call(this.STATUS_SHAPES, state) ? state : 'open';
    return `<span class="acc-status acc-status-${key}"><svg class="acc-status-icon" viewBox="0 0 12 12"`
      + ` width="12" height="12" aria-hidden="true" focusable="false">${this.STATUS_SHAPES[key]}</svg>`
      + `${this.esc(state || key)}</span>`;
  },

  /** The one line above everything: dataset, time, commit, producer. */
  headline(report) {
    const d = report.dataset || {};
    const when = String(report.generatedAt || '').replace('T', ' ').replace(/(:\d\d)(\.\d+)?([+-]\d\d:\d\d|Z)?$/, '$1');
    const parts = [
      `Dataset ${this.esc(d.version || '?')}`,
      `${this.num(d.pages)} pages`,
      `${this.num(d.publications)} publications`,
      `report of ${this.esc(when || '?')}`,
      `commit <code>${this.esc(report.commit || '?')}</code>`,
    ];
    if (report.generatedBy && report.generatedBy !== 'pipeline/acceptance.py') {
      parts.push(`<strong class="acc-fixture-word">${this.esc(report.generatedBy)}</strong>`);
    }
    return `<p class="acc-headline">${parts.join('<span class="acc-sep" aria-hidden="true"> | </span>')}</p>`;
  },

  checksOf(report, id) {
    return (report.checks || []).filter(c => c.milestone === id);
  },

  decisionsOf(report, id) {
    return (report.acceptance || []).filter(a => a.milestone === id);
  },

  /**
   * One plain line per milestone: its checks, then its decisions; the
   * decision count links to the first open card of the milestone.
   */
  milestoneLine(report, m) {
    const checks = this.checksOf(report, m.id);
    const count = s => checks.filter(c => c.status === s).length;
    const parts = [];
    if (checks.length) {
      let p = `${count('pass')} of ${checks.length} ${checks.length === 1 ? 'check passes' : 'checks pass'}`;
      if (count('fail')) p += `, <strong class="acc-fail-word">${count('fail')} fail</strong>`;
      if (count('open')) p += `, ${count('open')} open`;
      if (count('skipped')) p += `, ${count('skipped')} skipped`;
      parts.push(p);
    } else parts.push('no checks yet');
    const open = this.decisionsOf(report, m.id).filter(a => a.state === 'open');
    const decided = this.decisionsOf(report, m.id).length - open.length;
    if (open.length) {
      parts.push(`<a href="#${this.esc(open[0].id)}">${this.plural(open.length, 'decision', 'decisions')} open</a>`);
    } else parts.push('no decision open');
    if (decided) parts.push(`${decided} decided`);
    if (m.blockedBy) parts.push(`blocked: ${this.esc(m.blockedBy)}`);
    return `<li class="acc-ms" data-milestone="${this.esc(m.id)}"><span class="acc-ms-name">`
      + `<span class="acc-ms-id">${this.esc(m.id)}</span> ${this.esc(m.title)}</span>`
      + `<span class="acc-ms-line">${parts.join(', ')}</span></li>`;
  },

  program(report) {
    return `<ol class="acc-program">${(report.program || []).map(m => this.milestoneLine(report, m)).join('')}</ol>`;
  },

  example(ex) {
    const detail = this.esc(ex.detail);
    if (ex.page === null || ex.page === undefined || ex.page === '') return `<li>${detail}</li>`;
    const page = this.esc(ex.page);
    return `<li><a href="../#entry=${page}">Page ${page}</a> ${detail}</li>`;
  },

  check(c) {
    const m = c.measured || {};
    // An open or skipped check has measured nothing; zero counts would read as a result.
    const measured = m.checked > 0 || c.status === 'pass' || c.status === 'fail'
      ? `<span class="acc-measured">${this.num(m.failed)} failed of ${this.num(m.checked)} checked</span>` : '';
    const examples = (c.examples || []).slice(0, 20);
    const list = examples.length
      ? `<ul class="acc-examples" aria-label="Examples, ${this.esc(c.title)}">${examples.map(ex => this.example(ex)).join('')}</ul>`
      : '';
    const note = c.note ? `<p class="acc-note">${this.esc(c.note)}</p>` : '';
    return `<li class="acc-check acc-check-${this.esc(c.status)}" data-check="${this.esc(c.id)}">`
      + `<div class="acc-check-head">${this.status(c.status)}<span class="acc-check-title">${this.esc(c.title)}</span>`
      + `<span class="acc-check-ms">${this.esc(c.milestone)}</span>${measured}</div>`
      + `<p class="acc-proves">${this.esc(c.proves)}</p>${note}${list}</li>`;
  },

  failing(report) {
    const fails = (report.checks || []).filter(c => c.status === 'fail');
    if (!fails.length) return '';
    return '<section class="acc-section acc-failing" id="acc-failing" aria-labelledby="acc-failing-h">'
      + `<h2 id="acc-failing-h">Failing checks</h2><ol class="acc-checks">${fails.map(c => this.check(c)).join('')}</ol></section>`;
  },

  // Gap kinds the generator emits, said in words.
  GAP_WORDS: {
    'page-title': 'from the page title',
    'category-markup': 'from a category link in the wiki markup',
    'not-located': 'passage not located',
    repeated: 'passage occurs more than once',
    'not-verbatim': 'not verbatim in the entry',
  },

  gapWord(gap) {
    return this.GAP_WORDS[gap] || RecordCard.GAP_WORDS[gap] || String(gap).replace(/-/g, ' ');
  },

  // The report names the parser family "regex"; on a record card it is "rule".
  producerKind(p) {
    return p === 'regex' ? 'rule' : (p || 'rule');
  },

  producerSign(p) {
    const kind = this.producerKind(p);
    const family = RecordCard.producerFamily(kind);
    return `<span class="acc-producer rc-family-${family}" title="${this.esc(RecordCard.FAMILY_MEANING[family])}">`
      + `${RecordCard.producerIcon(family)}<span>${this.esc(RecordCard.producerWord(kind))}</span></span>`;
  },

  /** All values of a sample in order, each with its index across publications. */
  flatValues(sample) {
    const out = [];
    (sample.publications || []).forEach(pub => (pub.values || []).forEach(v => out.push({ pub: pub.id, v })));
    return out.map((x, i) => Object.assign({ index: i }, x));
  },

  familiesOf(samples) {
    const set = new Set();
    samples.forEach(s => this.flatValues(s).forEach(x => set.add(RecordCard.producerFamily(this.producerKind(x.v.producer)))));
    return set;
  },

  /** A span is usable when it lies inside the entry, counted in code points. */
  validSpan(span, length) {
    return Array.isArray(span) && span.length === 2 && Number.isInteger(span[0]) && Number.isInteger(span[1])
      && span[0] >= 0 && span[0] < span[1] && span[1] <= length;
  },

  /**
   * The entry with each value's span as a mark. Offsets count Unicode code
   * points, as Python slices the entry; overlapping spans split into segments
   * that name every value covering them.
   */
  entryHtml(sample) {
    const chars = Array.from(String(sample.entry || ''));
    const spans = this.flatValues(sample)
      .filter(x => this.validSpan(x.v.span, chars.length))
      .map(x => ({ start: x.v.span[0], end: x.v.span[1], index: x.index }));
    const cuts = new Set([0, chars.length]);
    spans.forEach(s => { cuts.add(s.start); cuts.add(s.end); });
    const points = [...cuts].sort((a, b) => a - b);
    let html = '';
    for (let i = 0; i < points.length - 1; i++) {
      const a = points[i];
      const b = points[i + 1];
      const text = this.esc(chars.slice(a, b).join(''));
      const cover = spans.filter(s => s.start <= a && s.end >= b).map(s => s.index);
      html += cover.length
        ? `<mark class="acc-mark" tabindex="0" data-values="${cover.join(' ')}">${text}</mark>`
        : text;
    }
    return html;
  },

  valueRow(x, entryLength) {
    const v = x.v;
    let where;
    if (this.validSpan(v.span, entryLength)) where = '';
    else if (v.gap) where = `<span class="acc-gap">${this.esc(this.gapWord(v.gap))}</span>`;
    else if (v.span) where = '<span class="acc-gap acc-gap-bad">span outside the entry</span>';
    else where = '<span class="acc-gap">no passage</span>';
    const differs = v.textDiffers ? '<span class="acc-differs">text differs from passage</span>' : '';
    const state = `<span class="acc-state acc-state-${this.esc(v.state)}">${this.esc(RecordCard.stateWord(v.state))}</span>`;
    const attrs = where ? '' : ` tabindex="0" data-values="${x.index}"`;
    return `<li class="acc-value${where ? ' has-gap' : ''}"${attrs}>`
      + `<span class="acc-value-field">${this.esc(v.field)}</span>`
      + `<span class="acc-value-text">${this.esc(v.value)}</span>`
      + `<span class="acc-value-meta">${this.producerSign(v.producer)}${state}${where}${differs}</span></li>`;
  },

  /** A block of the TEI string: its first line's indent is removed from every line. */
  teiBlock(tei, re) {
    const m = String(tei || '').match(re);
    if (!m) return '';
    const indent = m[1];
    return m[2].split('\n').map(line => (line.startsWith(indent) ? line.slice(indent.length) : line)).join('\n');
  },

  teiOfPublication(tei, id) {
    const safe = String(id).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return this.teiBlock(tei, new RegExp(`(?:^|\\n)([ \\t]*)(<biblStruct\\b[^>]*xml:id="${safe}"[\\s\\S]*?</biblStruct>)`));
  },

  teiOfSource(tei) {
    return this.teiBlock(tei, /(?:^|\n)([ \t]*)(<bibl\b[^>]*type="wikiPage"[\s\S]*?<\/bibl>)/);
  },

  /** Escaped XML with the tags tinted; the text stays exactly as given. */
  teiHtml(tei) {
    return this.esc(tei).replace(/&lt;(\/?)([\w:.-]+)([\s\S]*?)(\/?)&gt;/g,
      (all, close, name, attrs, self) => `<span class="acc-tag">&lt;${close}${name}</span>`
        + attrs.replace(/([\w:.-]+)=(&quot;[\s\S]*?&quot;)/g,
          '<span class="acc-attr">$1</span>=<span class="acc-attr-value">$2</span>')
        + `<span class="acc-tag">${self}&gt;</span>`);
  },

  teiDisclosure(label, xml) {
    if (!xml) return '';
    return `<details class="acc-tei-more"><summary>${this.esc(label)}</summary>`
      + `<pre class="acc-tei"><code>${this.teiHtml(xml)}</code></pre></details>`;
  },

  publication(sample, pub, flat, length) {
    const rows = flat.filter(x => x.pub === pub.id).map(x => this.valueRow(x, length)).join('');
    const excluded = pub.exported === false;
    const mark = excluded ? '<span class="acc-not-exported">read from the entry, not in the export</span>' : '';
    const tei = excluded ? '' : this.teiDisclosure('TEI', this.teiOfPublication(sample.tei, pub.id));
    return `<li class="acc-pub${excluded ? ' is-not-exported' : ''}" data-publication="${this.esc(pub.id)}">`
      + `<p class="acc-pub-head"><span class="acc-pub-id">${this.esc(pub.id)}</span>${mark}</p>`
      + `<ul class="acc-value-list">${rows}</ul>${tei}</li>`;
  },

  /** The publications of a sample; beyond the first few they fold away. */
  publications(sample) {
    const pubs = sample.publications || [];
    const length = Array.from(String(sample.entry || '')).length;
    const flat = this.flatValues(sample);
    if (!pubs.length) return '<p class="acc-empty">No publication is read from this entry.</p>';
    const draw = list => list.map(p => this.publication(sample, p, flat, length)).join('');
    const n = this.VISIBLE_PUBLICATIONS;
    const excluded = pubs.filter(p => p.exported === false).length;
    const summary = `<p class="acc-pub-count">${this.plural(pubs.length, 'publication', 'publications')}`
      + `${excluded ? `, ${excluded === pubs.length ? 'none' : `${pubs.length - excluded}`} in the export` : ''}</p>`;
    if (pubs.length <= n + 1) return `${summary}<ol class="acc-pubs">${draw(pubs)}</ol>`;
    return `${summary}<ol class="acc-pubs">${draw(pubs.slice(0, n))}</ol>`
      + `<details class="acc-pubs-more"><summary>Show all ${pubs.length} publications</summary>`
      + `<ol class="acc-pubs" start="${n + 1}">${draw(pubs.slice(n))}</ol></details>`;
  },

  /** One sample page: entry with its marks beside the values it was read into. */
  sample(sample, look) {
    const long = Array.from(String(sample.entry || '')).length > 1200;
    const instruction = look ? `<p class="acc-look">${this.esc(look)}</p>` : '';
    return `<div class="acc-sample" data-page="${this.esc(sample.page)}">${instruction}`
      + `<p class="acc-sample-head"><a href="../#entry=${this.esc(sample.page)}">Page ${this.esc(sample.page)}</a> `
      + `<span class="acc-sample-title">${this.esc(sample.title)}</span>`
      + `<span class="acc-sample-kind">${this.esc(sample.kind)}</span></p>`
      + '<div class="acc-sample-grid">'
      + `<div class="acc-entry-wrap"><p class="acc-entry${long ? ' is-long' : ''}"`
      + `${long ? ` tabindex="0" aria-label="Source entry of page ${this.esc(sample.page)}"` : ''}>${this.entryHtml(sample)}</p>`
      + `${this.teiDisclosure('TEI of the source entry', this.teiOfSource(sample.tei))}</div>`
      + `<div class="acc-sample-values">${this.publications(sample)}</div>`
      + '</div></div>';
  },

  sampleByPage(report, page) {
    return (report.samples || []).find(s => String(s.page) === String(page)) || null;
  },

  answer(a) {
    if (!a.answer) return '';
    return `<p class="acc-answer">Answer: <strong>${this.esc(a.answer.answer)}</strong>`
      + `${a.answer.date ? `, ${this.esc(a.answer.date)}` : ''}</p>`;
  },

  /** One decision as a card: question, reason, recommendation, its evidence. */
  decision(report, a) {
    const evidence = (a.evidence || []).map(ev => ({ ev, s: this.sampleByPage(report, ev.page) }));
    const samples = evidence.filter(e => e.s).map(e => e.s);
    const legend = samples.length ? RecordCard.legend(this.familiesOf(samples)) : '';
    const body = evidence.map(({ ev, s }) => (s ? this.sample(s, ev.look)
      : `<p class="acc-look">${this.esc(ev.look)} <span class="acc-gap acc-gap-bad">Page ${this.esc(ev.page)} is not among the samples.</span></p>`)).join('');
    return `<article class="acc-decision acc-decision-${this.esc(a.state)}" id="${this.esc(a.id)}" aria-labelledby="${this.esc(a.id)}-h">`
      + `<header class="acc-decision-head"><h3 id="${this.esc(a.id)}-h"><span class="acc-decision-id">${this.esc(a.id)}</span> `
      + `${this.esc(a.question)}</h3><p class="acc-decision-meta">${this.status(a.state)}`
      + `<span class="acc-check-ms">${this.esc(a.milestone)}</span></p></header>`
      + `<p class="acc-why">${this.esc(a.why)}</p>`
      + `<p class="acc-recommendation"><span class="acc-label">Recommendation</span> ${this.esc(a.recommendation)}</p>`
      + `${this.answer(a)}${legend}${body}</article>`;
  },

  decisions(report) {
    const items = report.acceptance || [];
    if (!items.length) return '<p class="acc-empty">The report carries no decisions.</p>';
    const open = items.filter(a => a.state === 'open').length;
    return `<p class="acc-scope">${open} open, ${items.length - open} decided. Answer in the chat with the id, such as "${this.esc(items[0].id)} yes".</p>`
      + items.map(a => this.decision(report, a)).join('');
  },

  DISPOSITIONS: [['exported', 'Exported'], ['pending', 'Pending'], ['excluded', 'Excluded']],

  coverageRow(f) {
    let where = '';
    if (f.disposition === 'exported') where = f.target ? `<code>${this.esc(f.target)}</code>` : 'no target named';
    else if (f.disposition === 'pending') {
      where = (f.milestone ? `due in ${this.esc(f.milestone)}` : 'no milestone') + (f.reason ? `; ${this.esc(f.reason)}` : '');
    } else where = f.reason ? this.esc(f.reason) : 'no reason given';
    return `<li class="acc-field" data-field="${this.esc(f.field)}"><span class="acc-field-name">${this.esc(f.field)}</span>`
      + `<span class="acc-field-layer">${this.esc(f.layer)}</span>`
      + `<span class="acc-field-records">${this.num(f.records)}</span>`
      + `<span class="acc-field-where">${where}</span></li>`;
  },

  /** Fields grouped by disposition; pending fields ordered by milestone. */
  coverage(report) {
    const fields = report.coverage || [];
    const order = (report.program || []).map(m => m.id);
    const rank = id => { const i = order.indexOf(id); return i < 0 ? order.length : i; };
    const known = this.DISPOSITIONS.map(d => d[0]);
    const groups = this.DISPOSITIONS.slice();
    if (fields.some(f => !known.includes(f.disposition))) groups.push(['other', 'Other disposition']);
    return groups.map(([key, label]) => {
      let rows = fields.filter(f => (key === 'other' ? !known.includes(f.disposition) : f.disposition === key));
      if (!rows.length) return '';
      if (key === 'pending') rows = rows.slice().sort((a, b) => rank(a.milestone) - rank(b.milestone));
      return `<section class="acc-disposition" data-disposition="${key}"><h4>${label}`
        + ` <span class="acc-count">${this.plural(rows.length, 'field', 'fields')}</span></h4>`
        + `<ul class="acc-fields">${rows.map(f => this.coverageRow(f)).join('')}</ul></section>`;
    }).join('');
  },

  /** Where the values come from, as one short list of counts. */
  values(report) {
    const v = report.values;
    if (!v) return '';
    const without = Object.entries(v.withoutSource || {})
      .map(([k, n]) => `<li><span class="acc-n">${this.num(n)}</span> ${this.esc(this.gapWord(k))}</li>`).join('');
    return '<dl class="acc-values">'
      + `<div><dt>Values</dt><dd>${this.num(v.total)}</dd></div>`
      + `<div><dt>with a passage</dt><dd>${this.num(v.withPassage)}</dd></div>`
      + `<div><dt>with a metadata source</dt><dd>${this.num(v.withMetaSource)}</dd></div>`
      + `<div><dt>text differs from passage</dt><dd>${this.num(v.textDiffers)}</dd></div>`
      + (without ? `<div class="acc-values-without"><dt>without a source</dt><dd><ul>${without}</ul></dd></div>` : '')
      + '</dl>';
  },

  /** Samples no decision refers to; they stay reachable for reviewers. */
  unreferenced(report) {
    const used = new Set((report.acceptance || []).flatMap(a => (a.evidence || []).map(ev => String(ev.page))));
    const rest = (report.samples || []).filter(s => !used.has(String(s.page)));
    if (!rest.length) return '';
    const families = this.familiesOf(rest);
    return `<h3>Other samples</h3>${RecordCard.legend(families)}${rest.map(s => this.sample(s, s.why)).join('')}`;
  },

  /** Everything a reviewer reads behind the decisions, folded by default. */
  checkReport(report) {
    const checks = report.checks || [];
    const pass = checks.filter(c => c.status === 'pass').length;
    return '<details class="acc-section acc-report" id="acc-report">'
      + `<summary><h2>Check report</h2><span class="acc-count">${pass} of ${checks.length} checks pass</span></summary>`
      + `<h3>Checks</h3><ol class="acc-checks">${checks.map(c => this.check(c)).join('')}</ol>`
      + `<h3>Values</h3>${this.values(report)}`
      + `<h3>Fields in the TEI</h3><p class="acc-scope">Field, layer, records, and where it goes or why not.</p>${this.coverage(report)}`
      + `${this.unreferenced(report)}</details>`;
  },

  /** The whole page body for a report. */
  page(report) {
    return this.headline(report)
      + `<section class="acc-section" id="acc-program" aria-label="Milestones">${this.program(report)}</section>`
      + this.failing(report)
      + `<section class="acc-section" id="acc-decisions" aria-labelledby="acc-decisions-h"><h2 id="acc-decisions-h">Decisions</h2>`
      + `${this.decisions(report)}</section>`
      + this.checkReport(report);
  },

  missing(detail) {
    const why = detail ? ` (${this.esc(detail)})` : '';
    return `<p class="acc-missing">No acceptance report is available${why}; it is generated by `
      + `<code>${this.esc(this.GENERATE)}</code>.</p>`;
  },

  /**
   * Marks and value rows of one sample that share a value index light up
   * together; a mark in a scrolled entry is brought into its box.
   */
  highlight(root, target) {
    root.querySelectorAll('.is-active').forEach(el => el.classList.remove('is-active'));
    const host = target && target.closest && target.closest('[data-values]');
    const sample = host && host.closest('.acc-sample');
    if (!sample) return;
    const wanted = host.dataset.values.split(' ');
    let first = null;
    sample.querySelectorAll('[data-values]').forEach(el => {
      if (!el.dataset.values.split(' ').some(i => wanted.includes(i))) return;
      el.classList.add('is-active');
      if (!first && el.classList.contains('acc-mark')) first = el;
    });
    const box = first && first.closest('.acc-entry.is-long');
    if (box && host !== first) {
      const top = first.offsetTop - box.offsetTop;
      if (top < box.scrollTop || top > box.scrollTop + box.clientHeight - 24) box.scrollTop = Math.max(0, top - 48);
    }
  },

  async boot() {
    const root = document.getElementById('acc-root');
    let report;
    try {
      const res = await fetch(this.REPORT_URL, { cache: 'no-store' });
      if (!res.ok) throw new Error(res.status === 404 ? '' : `HTTP ${res.status}`);
      report = await res.json();
    } catch (err) {
      root.innerHTML = this.missing(err && err.message);
      return;
    }
    root.innerHTML = this.page(report);
    // A link to a decision opens the card even after the page was drawn.
    if (location.hash) {
      const target = document.getElementById(decodeURIComponent(location.hash.slice(1)));
      if (target) target.scrollIntoView();
    }
    const on = e => this.highlight(root, e.target);
    root.addEventListener('mouseover', on);
    root.addEventListener('focusin', on);
    root.addEventListener('mouseleave', () => this.highlight(root, null));
    root.addEventListener('focusout', e => { if (!root.contains(e.relatedTarget)) this.highlight(root, null); });
  },
};

if (typeof document !== 'undefined' && document.getElementById('acc-root')) AcceptanceView.boot();

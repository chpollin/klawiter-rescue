/**
 * Acceptance view: one report of pipeline/acceptance.py, read per milestone.
 *
 * Pure functions take the report object and return HTML strings, so
 * tests/acceptance_view.test.js renders them against a fixture; boot() alone
 * fetches the report, mounts the strings and wires the query state and the
 * span highlighting. The producer signs and the state and gap words come from
 * docs/js/record-card.js, loaded before this file, so a sign means here what
 * it means on a record card.
 *
 * Trust boundary: every string from the report is escaped here; the only
 * unescaped markup is what these functions build from escaped parts and the
 * icon paths of RecordCard.
 */
const AcceptanceView = {
  REPORT_URL: '../local/acceptance.json',
  GENERATE: 'python -m uv run python pipeline/acceptance.py',

  esc(s) {
    return RecordCard.escape(s);
  },

  /**
   * State lives in the query (`m` the milestone filter, `sample` the sample
   * page), so it survives a reload and leaves the hash to the section anchors.
   */
  parseState(search) {
    const p = new URLSearchParams(String(search || '').replace(/^\?/, ''));
    return { milestone: p.get('m') || '', sample: p.get('sample') || '' };
  },

  hrefFor(state) {
    const p = new URLSearchParams();
    if (state.milestone) p.set('m', state.milestone);
    if (state.sample) p.set('sample', state.sample);
    const s = p.toString();
    return s ? `?${s}` : './';
  },

  // A status is a shape and a word; the hue only repeats them.
  STATUS_SHAPES: {
    pass: '<path d="M2.5 6.5l2.5 2.5 4.5-6"/>',
    fail: '<path d="M3 3l6 6M9 3l-6 6"/>',
    open: '<circle cx="6" cy="6" r="3.5"/>',
    skipped: '<path d="M2.5 6h7"/>',
    done: '<path d="M2.5 6.5l2.5 2.5 4.5-6"/>',
    'in-progress': '<circle cx="6" cy="6" r="3.5"/><path d="M6 2.5v7"/>',
    blocked: '<rect x="2.5" y="2.5" width="7" height="7"/><path d="M2.5 9.5l7-7"/>',
    accepted: '<path d="M2.5 6.5l2.5 2.5 4.5-6"/>',
    rejected: '<path d="M3 3l6 6M9 3l-6 6"/>',
  },

  STATUS_WORDS: {
    pass: 'pass', fail: 'fail', open: 'open', skipped: 'skipped',
    done: 'done', 'in-progress': 'in progress', blocked: 'blocked',
    accepted: 'accepted', rejected: 'rejected',
  },

  status(state) {
    const key = Object.prototype.hasOwnProperty.call(this.STATUS_WORDS, state) ? state : 'open';
    const word = this.STATUS_WORDS[key];
    return `<span class="acc-status acc-status-${key}"><svg class="acc-status-icon" viewBox="0 0 12 12"`
      + ` width="12" height="12" aria-hidden="true" focusable="false">${this.STATUS_SHAPES[key]}</svg>`
      + `${this.esc(state && state !== key ? state : word)}</span>`;
  },

  num(n) {
    return typeof n === 'number' ? n.toLocaleString('en-US') : this.esc(n == null ? '?' : n);
  },

  checksOf(report, milestoneId) {
    return (report.checks || []).filter(c => c.milestone === milestoneId);
  },

  /** "n of m checks pass", or a plain word when the milestone has none. */
  passCount(report, milestoneId) {
    const checks = this.checksOf(report, milestoneId);
    if (!checks.length) return 'no checks yet';
    const pass = checks.filter(c => c.status === 'pass').length;
    return `${pass} of ${checks.length} checks pass`;
  },

  /** The one line above everything: dataset, time, commit, producer. */
  headline(report) {
    const d = report.dataset || {};
    const when = String(report.generatedAt || '').replace('T', ' ').replace(/(:\d\d)(\.\d+)?([+-]\d\d:\d\d|Z)?$/, '$1');
    const parts = [
      `Dataset ${this.esc(d.version || '?')}`,
      `${this.num(d.pages)} pages`,
      `${this.num(d.publications)} publications`,
      `generated ${this.esc(when || '?')}`,
      `commit <code>${this.esc(report.commit || '?')}</code>`,
    ];
    if (report.generatedBy && report.generatedBy !== 'pipeline/acceptance.py') {
      parts.push(`<strong class="acc-fixture-word">${this.esc(report.generatedBy)}</strong>`);
    }
    return `<p class="acc-headline">${parts.join('<span class="acc-sep" aria-hidden="true"> | </span>')}</p>`;
  },

  /** The milestones as a list of links that filter the checks. */
  program(report, state) {
    const items = (report.program || []).map(m => {
      const current = state.milestone === m.id;
      const href = this.hrefFor({ milestone: current ? '' : m.id, sample: state.sample });
      const blocked = m.blockedBy ? `<p class="acc-ms-blocked">Blocked by: ${this.esc(m.blockedBy)}</p>` : '';
      const repos = (m.repos || []).length
        ? `<dt>Repositories</dt><dd>${(m.repos || []).map(r => this.esc(r)).join(', ')}</dd>` : '';
      return `<li class="acc-ms${current ? ' is-current' : ''}" data-milestone="${this.esc(m.id)}">`
        + `<a class="acc-ms-link" data-state href="${this.esc(href)}"${current ? ' aria-current="true"' : ''}>`
        + `<span class="acc-ms-id">${this.esc(m.id)}</span> <span class="acc-ms-title">${this.esc(m.title)}</span></a>`
        + `${this.status(m.state)}<span class="acc-ms-count">${this.esc(this.passCount(report, m.id))}</span>`
        + `<p class="acc-ms-goal">${this.esc(m.goal)}</p>${blocked}`
        + '<details class="acc-ms-more"><summary>Verified and accepted by</summary><dl>'
        + `<dt>Verified by</dt><dd>${this.esc(m.verifiedBy)}</dd>`
        + `<dt>Accepted by</dt><dd>${this.esc(m.acceptedBy)}</dd>${repos}</dl></details></li>`;
    }).join('');
    return `<ol class="acc-program">${items}</ol>`;
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
    const measured = m.checked !== undefined && (m.checked > 0 || c.status === 'pass' || c.status === 'fail')
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

  /** The checks of the selected milestone, or all of them in program order. */
  checks(report, state) {
    const all = report.checks || [];
    const shown = state.milestone ? all.filter(c => c.milestone === state.milestone) : all;
    const scope = state.milestone
      ? `Milestone ${this.esc(state.milestone)}, ${this.esc(this.passCount(report, state.milestone))}.`
        + ` <a data-state href="${this.esc(this.hrefFor({ milestone: '', sample: state.sample }))}">Show all checks</a>`
      : `All milestones, ${all.filter(c => c.status === 'pass').length} of ${all.length} checks pass.`;
    const body = shown.length
      ? `<ol class="acc-checks">${shown.map(c => this.check(c)).join('')}</ol>`
      : '<p class="acc-empty">This milestone has no checks in the report.</p>';
    return `<p class="acc-scope">${scope}</p>${body}`;
  },

  DISPOSITIONS: [
    ['exported', 'Exported'],
    ['pending', 'Pending'],
    ['excluded', 'Excluded'],
  ],

  coverageRow(f) {
    let where = '';
    if (f.disposition === 'exported') where = f.target ? `<code>${this.esc(f.target)}</code>` : 'no target named';
    else if (f.disposition === 'pending') {
      where = (f.milestone ? `due in ${this.esc(f.milestone)}` : 'no milestone')
        + (f.reason ? `; ${this.esc(f.reason)}` : '');
    } else where = f.reason ? this.esc(f.reason) : 'no reason given';
    return `<li class="acc-field" data-field="${this.esc(f.field)}"><span class="acc-field-name">${this.esc(f.field)}</span>`
      + `<span class="acc-field-layer">${this.esc(f.layer)}</span>`
      + `<span class="acc-field-records">${this.num(f.records)} records</span>`
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
      return `<section class="acc-disposition" data-disposition="${key}"><h3>${label}`
        + ` <span class="acc-count">${rows.length} ${rows.length === 1 ? 'field' : 'fields'}</span></h3>`
        + `<ul class="acc-fields">${rows.map(f => this.coverageRow(f)).join('')}</ul></section>`;
    }).join('');
  },

  /** Where the values come from, as one short list of counts. */
  values(report) {
    const v = report.values;
    if (!v) return '';
    const without = Object.entries(v.withoutSource || {})
      .map(([k, n]) => `<li><span class="acc-n">${this.num(n)}</span> ${this.esc(k)}</li>`).join('');
    return '<dl class="acc-values">'
      + `<div><dt>Values</dt><dd>${this.num(v.total)}</dd></div>`
      + `<div><dt>with a passage</dt><dd>${this.num(v.withPassage)}</dd></div>`
      + `<div><dt>with a metadata source</dt><dd>${this.num(v.withMetaSource)}</dd></div>`
      + `<div><dt>text differs from passage</dt><dd>${this.num(v.textDiffers)}</dd></div>`
      + (without ? `<div class="acc-values-without"><dt>without a source</dt><dd><ul>${without}</ul></dd></div>` : '')
      + '</dl>';
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

  gapWord(gap) {
    return RecordCard.GAP_WORDS[gap] || String(gap).replace(/-/g, ' ');
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

  valuesList(sample) {
    const length = Array.from(String(sample.entry || '')).length;
    const flat = this.flatValues(sample);
    return (sample.publications || []).map(pub => {
      const rows = flat.filter(x => x.pub === pub.id).map(x => this.valueRow(x, length)).join('');
      return `<h4 class="acc-pub-id">${this.esc(pub.id)}</h4><ul class="acc-value-list">${rows}</ul>`;
    }).join('');
  },

  /** Escaped XML with the tags tinted; the text stays exactly as given. */
  teiHtml(tei) {
    return this.esc(tei).replace(/&lt;(\/?)([\w:.-]+)([\s\S]*?)(\/?)&gt;/g,
      (all, close, name, attrs, self) => `<span class="acc-tag">&lt;${close}${name}</span>`
        + attrs.replace(/([\w:.-]+)=(&quot;[\s\S]*?&quot;)/g,
          '<span class="acc-attr">$1</span>=<span class="acc-attr-value">$2</span>')
        + `<span class="acc-tag">${self}&gt;</span>`);
  },

  sampleNav(report, state) {
    const samples = report.samples || [];
    const current = this.currentSample(report, state);
    return `<ul class="acc-sample-nav">${samples.map(s => {
      const on = current && String(current.page) === String(s.page);
      return `<li><a data-state href="${this.esc(this.hrefFor({ milestone: state.milestone, sample: String(s.page) }))}"`
        + `${on ? ' aria-current="true"' : ''}><span class="acc-sample-page">${this.esc(s.page)}</span> `
        + `${this.esc(s.title)}</a></li>`;
    }).join('')}</ul>`;
  },

  currentSample(report, state) {
    const samples = report.samples || [];
    return samples.find(s => String(s.page) === String(state.sample)) || samples[0] || null;
  },

  sample(report, state) {
    const s = this.currentSample(report, state);
    if (!s) return '<p class="acc-empty">The report carries no samples.</p>';
    const families = new Set(this.flatValues(s).map(x => RecordCard.producerFamily(this.producerKind(x.v.producer))));
    return `${this.sampleNav(report, state)}`
      + `<div class="acc-sample-head"><h3><a href="../#entry=${this.esc(s.page)}">Page ${this.esc(s.page)}</a> `
      + `${this.esc(s.title)}</h3><span class="acc-sample-kind">${this.esc(s.kind)}</span>`
      + `<p class="acc-why">${this.esc(s.why)}</p></div>`
      + '<div class="acc-sample-grid">'
      + `<section class="acc-region acc-region-entry" aria-labelledby="acc-h-entry"><h4 id="acc-h-entry">Source entry</h4>`
      + `<p class="acc-entry">${this.entryHtml(s)}</p></section>`
      + `<section class="acc-region acc-region-values" aria-labelledby="acc-h-values"><h4 id="acc-h-values">Values</h4>`
      + `${RecordCard.legend(families)}${this.valuesList(s)}</section>`
      + `<section class="acc-region acc-region-tei" aria-labelledby="acc-h-tei"><h4 id="acc-h-tei">TEI</h4>`
      + `<pre class="acc-tei"><code>${this.teiHtml(s.tei || '')}</code></pre></section>`
      + '</div>';
  },

  acceptance(report) {
    const items = report.acceptance || [];
    if (!items.length) return '<p class="acc-empty">No operator decisions in the report.</p>';
    const open = items.filter(a => a.state === 'open');
    const decided = items.filter(a => a.state !== 'open');
    const row = a => `<li class="acc-decision" data-decision="${this.esc(a.id)}">${this.status(a.state)}`
      + `<span class="acc-check-ms">${this.esc(a.milestone)}</span><p>${this.esc(a.question)}</p></li>`;
    return `<p class="acc-scope">${open.length} open, ${decided.length} decided.</p>`
      + `<ol class="acc-decisions">${open.concat(decided).map(row).join('')}</ol>`;
  },

  /** The whole page body for a report and a hash state. */
  page(report, state) {
    const section = (id, title, body) => `<section class="acc-section" id="${id}" aria-labelledby="${id}-h">`
      + `<h2 id="${id}-h">${title}</h2>${body}</section>`;
    return this.headline(report)
      + section('acc-program', 'Program', this.program(report, state))
      + section('acc-checks', 'Checks', this.checks(report, state))
      + section('acc-coverage', 'Fields in the TEI', this.coverage(report) + this.values(report))
      + section('acc-samples', 'Samples', this.sample(report, state))
      + section('acc-acceptance', 'Operator decisions', this.acceptance(report));
  },

  missing(detail) {
    const why = detail ? ` (${this.esc(detail)})` : '';
    return `<p class="acc-missing">No acceptance report is available${why}; it is generated by `
      + `<code>${this.esc(this.GENERATE)}</code>.</p>`;
  },

  /** Marks and value rows that share a value index light up together. */
  highlight(root, target) {
    root.querySelectorAll('.is-active').forEach(el => el.classList.remove('is-active'));
    const host = target && target.closest && target.closest('[data-values]');
    if (!host || !root.contains(host)) return;
    const wanted = host.dataset.values.split(' ');
    root.querySelectorAll('[data-values]').forEach(el => {
      if (el.dataset.values.split(' ').some(i => wanted.includes(i))) el.classList.add('is-active');
    });
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
    const render = () => {
      const state = this.parseState(location.search);
      // Focus survives the redraw: a milestone link by its milestone, a
      // sample link by the current sample, any other link by its target.
      const active = document.activeElement;
      const inRoot = active && active !== root && root.contains(active);
      const ms = inRoot && active.closest('.acc-ms');
      const inNav = inRoot && active.closest('.acc-sample-nav');
      const href = inRoot ? active.getAttribute('href') : null;
      root.innerHTML = this.page(report, state);
      let again = null;
      if (ms) again = root.querySelector(`.acc-ms[data-milestone="${CSS.escape(ms.dataset.milestone)}"] .acc-ms-link`);
      else if (inNav) again = root.querySelector('.acc-sample-nav [aria-current]');
      else if (href) again = [...root.querySelectorAll('a[href]')].find(a => a.getAttribute('href') === href);
      if (again) again.focus({ preventScroll: true });
    };
    render();
    // State links change the query without a reload; Back and Forward redraw.
    root.addEventListener('click', e => {
      const a = e.target.closest('a[data-state]');
      if (!a || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      e.preventDefault();
      history.pushState(null, '', a.getAttribute('href'));
      render();
    });
    window.addEventListener('popstate', render);
    const on = e => this.highlight(root, e.target);
    root.addEventListener('mouseover', on);
    root.addEventListener('focusin', on);
    root.addEventListener('mouseleave', () => this.highlight(root, null));
    root.addEventListener('focusout', e => { if (!root.contains(e.relatedTarget)) this.highlight(root, null); });
  },
};

if (typeof document !== 'undefined' && document.getElementById('acc-root')) AcceptanceView.boot();

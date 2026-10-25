/**
 * RecordCard: one card anatomy for a wiki record and a print object.
 *
 * Pure functions from a card model to HTML strings. Nothing here fetches,
 * reads the DOM or keeps state, so the wiki adapter (detail.js) and the print
 * adapter build a model and the same functions draw both. The model:
 *
 *   {kind: 'wiki'|'print', id, permalink, sourceSign: {label, volume?, pdfPage?,
 *    pageId?}, title, type, relation: {state, route?, words}, review: {state,
 *    producer, contested}, snippet, groups: [{heading?, state?, producer?,
 *    rows: [{key, label, values: [{text, href?, producer, state, chainId,
 *    chain: {passage, record, sourceFile, producer}}]}]}],
 *    sourceText: {text, marks: [{start, end, key, valueIndex}]}}
 *
 * Trust boundary: every model string is escaped here, except `value.html`,
 * `row.labelExtra` and `row.note`, which an adapter builds from escaped parts
 * so a value keeps its authority link, contested mark or edit control.
 *
 * A value row discloses its chain through a visible button per value; the
 * panel the button controls is an empty slot until a handler fills it with
 * chainSteps(), so the card at rest repeats no value and hides no fact.
 */
const RecordCard = {
  escape(s) {
    if (s === null || s === undefined) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  },

  // The committed words of the reader; the operator decides the final ones
  // (knowledge/design.md, Open design decisions).
  PRODUCER_WORDS: {
    rule: 'rule', llm: 'LLM-enriched', person: 'expert-curated', compiler: 'compiler',
    inherited: 'inherited', derived: 'derived', fixture: 'test fixture',
  },

  STATE_WORDS: {
    'not-reviewed': 'not reviewed', proposed: 'proposed', contested: 'contested',
    confirmed: 'confirmed', edited: 'edited, unsaved', open: 'open', complete: 'complete',
    flagged: 'flagged',
  },

  // A gap is said in words, and a gap a rule made never reads like one in
  // the source. No kind stands in for a first match.
  GAP_WORDS: {
    'not-located': 'passage not located',
    rule: 'gap by rule',
    source: 'not given in the source',
    category: 'category link in the wiki markup',
    derived: 'derived from another value',
  },

  STEPS: ['Value', 'Passage', 'Record', 'Source file', 'Producer', 'State'],

  /** A checksum read by its ends; the whole value stays in the tooltip. */
  checksum(value) {
    const hex = String(value || '');
    if (!hex) return '';
    const short = hex.length > 12 ? `${hex.slice(0, 4)}…${hex.slice(-4)}` : hex;
    return `<span class="checksum" title="SHA-256 ${this.escape(hex)}">${this.escape(short)}</span>`;
  },

  producerWord(kind, override) {
    if (override) return String(override);
    return this.PRODUCER_WORDS[kind] || (kind ? String(kind) : 'rule');
  },

  stateWord(state) {
    if (!state) return this.STATE_WORDS['not-reviewed'];
    return this.STATE_WORDS[state] || String(state);
  },

  _id(s) {
    return String(s).replace(/[^A-Za-z0-9_-]+/g, '-');
  },

  chainId(r, value, index) {
    if (value && value.chainId) return this._id(value.chainId);
    return this._id(`chain-${r.idBase || r.key || 'value'}-${index}`);
  },

  // --- Slip ------------------------------------------------------------------

  ICONS: {
    print: '<svg class="rc-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M4 4.5A1.5 1.5 0 0 1 5.5 3H11v17H5.5A1.5 1.5 0 0 1 4 18.5z"/><path d="M20 4.5A1.5 1.5 0 0 0 18.5 3H13v17h5.5a1.5 1.5 0 0 0 1.5-1.5z"/></svg>',
    wiki: '<svg class="rc-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 3 2.5 15 0 18M12 3c-2.5 3-2.5 15 0 18"/></svg>',
  },

  /** The source sign: an icon with its name, the volume and PDF page or the wiki page. */
  sourceSign(m) {
    const sign = m.sourceSign || {};
    const parts = [sign.label || (m.kind === 'print' ? 'Print' : 'Wiki')];
    if (sign.volume) parts.push(`volume ${sign.volume}`);
    if (sign.pdfPage != null) parts.push(`PDF page ${sign.pdfPage}`);
    if (sign.pageId != null && !sign.label) parts.push(`page ${sign.pageId}`);
    return `<span class="rc-sign rc-sign-${this.escape(m.kind)}">${this.ICONS[m.kind] || ''}`
      + `<span class="rc-sign-text">${this.escape(parts.join(', '))}</span></span>`;
  },

  /** The relation to the other source, proposed until a person decides. */
  relationMark(m) {
    const rel = m.relation;
    if (!rel || !rel.words) return '';
    const route = rel.route ? `, ${this.escape(rel.route)}` : '';
    return `<span class="rc-relation">${this.escape(rel.words)}${route}`
      + `<span class="rc-state-word">, ${this.escape(this.stateWord(rel.state || 'proposed'))}</span></span>`;
  },

  /** The review state of the record and its producer, and "contested" where a claim is open. */
  reviewMark(m) {
    const review = m.review || {};
    const producer = review.producer ? `, ${this.escape(review.producer)}` : '';
    const contested = review.contested ? '<span class="rc-contested">, contested</span>' : '';
    return `<span class="rc-review">${this.escape(this.stateWord(review.state))}${producer}${contested}</span>`;
  },

  /** A slip at rest: two lines and three marks, nothing else. */
  slip(m) {
    const title = m.permalink
      ? `<a class="rc-slip-title" href="${this.escape(m.permalink)}">${this.escape(m.title || 'Untitled')}</a>`
      : `<span class="rc-slip-title">${this.escape(m.title || 'Untitled')}</span>`;
    const snippet = m.snippet ? `<p class="rc-slip-snippet">${this.escape(m.snippet)}</p>` : '';
    return `<div class="rc-slip" data-kind="${this.escape(m.kind)}" data-record="${this.escape(m.id)}">`
      + `<p class="rc-slip-line">${title} <span class="rc-slip-id">${this.escape(m.id)}</span></p>`
      + snippet
      + `<p class="rc-slip-marks">${this.sourceSign(m)}${this.relationMark(m)}${this.reviewMark(m)}</p>`
      + '</div>';
  },

  // --- Open card -------------------------------------------------------------

  /**
   * The head: identifier as the permalink, source location, title and type
   * with the record's decision. The type is the one type badge of the head.
   */
  head(m) {
    const id = m.permalink
      ? `<a class="rc-id" href="${this.escape(m.permalink)}">${this.escape(m.id)}</a>`
      : `<span class="rc-id">${this.escape(m.id)}</span>`;
    const position = m.position ? `<span class="rc-position">${this.escape(m.position)}</span>` : '';
    const type = m.type ? `<span class="badge rc-type">${this.escape(m.type)}</span>` : '';
    let title = this.escape(m.title || 'Untitled');
    let slot = '';
    if (m.titleValue && m.titleValue.chain) {
      const r = { key: 'title', label: 'Title', idBase: `${m.id}-title`, values: [m.titleValue] };
      title = `<span data-provenance-for="title">${title}${this._button(r, m.titleValue, 0)}</span>`;
      slot = this._slot(r, m.titleValue, 0);
    }
    return `<header class="rc-head" data-region="head">`
      + `<p class="rc-head-line">${id}${this.sourceSign(m)}${position}</p>`
      + `<h2 class="rc-title">${title}</h2>${slot}`
      + `<p class="rc-head-line">${type}${this.relationMark(m)}${this.reviewMark(m)}</p>`
      + '</header>';
  },

  /** The visible producer button of one value; its nearest row names the key. */
  _button(r, value, index) {
    const id = this.chainId(r, value, index);
    const word = this.producerWord(value.producer, value.producerWord);
    const kind = this._id(value.producer || 'rule');
    return `<button type="button" class="prov-badge rc-producer-btn rc-producer-${kind}"`
      + ` aria-expanded="false" aria-controls="${id}"><span class="rc-producer">${this.escape(word)}</span>`
      + '<span class="visually-hidden">, provenance chain</span></button>';
  },

  /** The empty panel a button controls, filled on demand by chainSteps(). */
  _slot(r, value, index) {
    const id = this.chainId(r, value, index);
    const name = `Provenance chain, ${r.label || r.key}`;
    return `<div class="rc-chain" id="${id}" role="group" aria-label="${this.escape(name)}" hidden></div>`;
  },

  /** One value with its state word where it deviates, and its producer button. */
  valueHtml(r, value, index) {
    const body = value.html != null ? value.html
      : value.href ? `<a href="${this.escape(value.href)}">${this.escape(value.text)}</a>`
        : this.escape(value.text);
    const state = value.showState && value.state
      ? `<span class="rc-state-word"> ${this.escape(this.stateWord(value.state))}</span>`
      : '';
    return value.chain ? `${body}${state}${this._button(r, value, index)}` : `${body}${state}`;
  },

  /**
   * One value row: a label and its values, each with its own chain button,
   * and one panel slot per value under the row.
   */
  row(r) {
    const values = (r.values || []).filter(Boolean);
    const chained = values.some(value => value.chain);
    const key = r.dataKey || r.key;
    const attrs = (key ? ` data-key="${this.escape(key)}"` : '')
      + (chained && r.key ? ` data-provenance-for="${this.escape(r.key)}"` : '');
    const title = r.help ? ` title="${this.escape(r.help)}"` : '';
    const items = values.map((value, i) => this.valueHtml(r, value, i));
    let body;
    if (r.layout === 'ol' || r.layout === 'ul') {
      const cls = r.listClass ? ` class="${this.escape(r.listClass)}"` : '';
      body = `<${r.layout}${cls}>${items.map(item => `<li class="rc-value">${item}</li>`).join('')}</${r.layout}>`;
    } else if (r.layout === 'lines') {
      body = items.map(item => `<span class="rc-value rc-line">${item}</span>`).join('');
    } else {
      const sep = r.separator == null ? ', ' : r.separator;
      body = items.map(item => `<span class="rc-value">${item}</span>`).join(this.escape(sep));
    }
    const note = r.note ? `<div class="rc-note">${r.note}</div>` : '';
    const slots = values.map((value, i) => (value.chain ? this._slot(r, value, i) : '')).join('');
    return `<div class="meta-row rc-row"${attrs}><div class="meta-label"${title}>${
      this.escape(r.label)}${r.labelExtra || ''}</div><div class="meta-value">${body}${note}</div>${slots}</div>`;
  },

  /** One group of rows, headed where the model names a heading. */
  group(g) {
    const state = g.state ? ` <span class="rc-state-word">${this.escape(this.stateWord(g.state))}${
      g.producer ? `, ${this.escape(g.producer)}` : ''}</span>` : '';
    const heading = g.heading ? `<h3 class="rc-group-heading">${this.escape(g.heading)}${state}</h3>` : '';
    return `<section class="rc-group">${heading}<div class="meta-table">${
      (g.rows || []).map(r => this.row(r)).join('')}</div></section>`;
  },

  /** The whole open card in its fixed region order: head, values, source. */
  card(m) {
    return `<article class="rc-card" data-kind="${this.escape(m.kind)}" data-record="${this.escape(m.id)}">`
      + this.head(m)
      + `<div class="rc-values" data-region="values">${(m.groups || []).map(g => this.group(g)).join('')}</div>`
      + this.source(m)
      + '</article>';
  },

  // --- Chain -----------------------------------------------------------------

  /** The passage of a value, located by its offsets or named as a gap. */
  passage(m, value) {
    const p = (value && value.chain && value.chain.passage) || {};
    const text = m && m.sourceText && typeof m.sourceText.text === 'string' ? m.sourceText.text : null;
    if (Number.isInteger(p.textStart) && Number.isInteger(p.textEnd) && p.textEnd > p.textStart) {
      let slice = typeof p.text === 'string' ? p.text : null;
      if (slice === null && text !== null && p.textStart >= 0 && p.textEnd <= text.length) {
        slice = text.slice(p.textStart, p.textEnd);
      }
      if (slice !== null) {
        return { located: true, text: slice, textStart: p.textStart, textEnd: p.textEnd,
          markId: p.markId || null, scope: p.scope || '' };
      }
      return { located: false, gap: 'not-located', reason: 'its offsets leave the displayed text',
        scope: p.scope || '' };
    }
    const gap = this.GAP_WORDS[p.gap] ? p.gap : 'not-located';
    return { located: false, gap, reason: p.reason || '', rule: p.rule || '', scope: p.scope || '' };
  },

  _passageHtml(m, value) {
    const p = this.passage(m, value);
    const scope = p.scope ? ` <span class="rc-sub">${this.escape(p.scope)}</span>` : '';
    if (p.located) {
      const show = p.markId ? ` <button type="button" class="rc-show" data-rc-show="${
        this.escape(this._id(p.markId))}">Show in source</button>` : '';
      return `<q class="rc-passage">${this.escape(p.text)}</q> <span class="rc-sub">characters ${
        p.textStart}–${p.textEnd} of the source text</span>${scope}${show}`;
    }
    const rule = p.gap === 'rule' && p.rule ? `: ${this.escape(p.rule)}` : '';
    const reason = p.reason ? ` <span class="rc-sub">(${this.escape(p.reason)})</span>` : '';
    return `<span class="rc-gap rc-gap-${this.escape(p.gap)}">${this.escape(this.GAP_WORDS[p.gap])}${
      rule}</span>${reason}${scope}`;
  },

  _recordHtml(m, value) {
    const rec = (value.chain && value.chain.record) || (m && m.record) || {};
    const lines = [];
    const plain = s => this.escape(s);
    if (rec.id) lines.push(`<code>${plain(rec.id)}</code>${rec.type ? `, ${plain(rec.type)}` : ''}`);
    if (rec.sign) lines.push(plain(rec.sign));
    const ids = [rec.textId != null ? `Text ID ${rec.textId}` : '', rec.blobId != null ? `Blob ID ${rec.blobId}` : '']
      .filter(Boolean).join(', ');
    if (ids) lines.push(plain(ids));
    const rev = rec.revision;
    if (rev && (rev.first || rev.last)) {
      const one = item => (item ? `${item.id}${item.date ? ` of ${item.date}` : ''}` : '');
      lines.push(plain(rev.first && rev.last
        ? `revisions ${one(rev.first)} to ${one(rev.last)}`
        : `revision ${one(rev.first || rev.last)}`));
    }
    if (rec.revisionNote) lines.push(plain(rec.revisionNote));
    const print = [rec.volume ? `volume ${rec.volume}` : '', rec.part ? `part ${rec.part}` : '',
      rec.address ? `address ${rec.address}` : '',
      rec.pdfPage != null ? `PDF page ${rec.pdfPage}${rec.pdfPageEnd != null && rec.pdfPageEnd !== rec.pdfPage
        ? `–${rec.pdfPageEnd}` : ''}` : '',
      rec.line != null ? `line ${rec.line}` : ''].filter(Boolean).join(', ');
    if (print) lines.push(plain(print));
    if (rec.publication) {
      lines.push(`publication ${plain(rec.publication.label || '')}${rec.publication.id
        ? ` <code>${plain(rec.publication.id)}</code>` : ''}`);
    }
    const block = rec.block;
    if (block) {
      const shown = Number.isInteger(block.textStart) && Number.isInteger(block.textEnd)
        ? `block characters ${block.textStart}–${block.textEnd} of the source text`
        : 'block not located in the displayed text';
      const raw = Number.isInteger(block.start) && Number.isInteger(block.end)
        ? `, raw characters ${block.start}–${block.end}` : '';
      lines.push(`${plain(shown + raw)}${block.sha256 ? `, ${this.checksum(block.sha256)}` : ''}`);
    } else if (rec.sha256) {
      lines.push(`text ${this.checksum(rec.sha256)}`);
    }
    for (const line of rec.extra || []) lines.push(plain(line));
    if (!lines.length) return '<span class="rc-gap">record not named</span>';
    return lines.map(line => `<span class="rc-line">${line}</span>`).join('');
  },

  _sourceFileHtml(m, value) {
    const file = (value.chain && value.chain.sourceFile) || (m && m.sourceFile) || {};
    if (file.file || file.fileName) {
      const sha = file.sha256 || file.sha256Prefix;
      return `<code>${this.escape(file.file || file.fileName)}</code>${sha ? `, ${this.checksum(sha)}` : ''}`;
    }
    return `<span class="rc-gap">${this.escape(file.words || 'file not named in the published data')}</span>`;
  },

  _producerHtml(value) {
    const p = (value.chain && value.chain.producer) || {};
    const word = this.producerWord(value.producer, value.producerWord);
    const parts = [p.words || ''];
    if (p.rule) parts.push(`rule ${p.rule}`);
    if (p.model) parts.push(`model ${p.model}`);
    if (p.frozenAt) parts.push(`frozen ${String(p.frozenAt).slice(0, 10)}`);
    if (p.by) parts.push(p.by);
    const detail = parts.filter(Boolean).map(s => this.escape(s)).join(', ');
    const prompt = p.promptSha256 ? `, prompt ${this.checksum(p.promptSha256)}` : '';
    return `<strong class="rc-producer-name">${this.escape(word)}</strong>${
      detail ? `: ${detail}` : ''}${prompt}`;
  },

  _stateHtml(value) {
    const words = value.stateText || this.stateWord(value.state);
    return this.escape(words);
  },

  /** The steps of one value's chain, as visible text. */
  chainSteps(m, r, valueIndex) {
    const value = (r.values || [])[valueIndex];
    if (!value || !value.chain) return '';
    const derived = value.derivedFrom ? ` <span class="rc-sub">derived from ${this.escape(value.derivedFrom)}</span>` : '';
    const steps = [
      ['Value', `${this.escape(value.text)}${derived}`],
      ['Passage', this._passageHtml(m, value)],
      ['Record', this._recordHtml(m, value)],
      ['Source file', this._sourceFileHtml(m, value)],
      ['Producer', this._producerHtml(value)],
      ['State', this._stateHtml(value)],
    ];
    return `<dl class="rc-chain-steps">${steps.map(([name, html]) =>
      `<div class="rc-step"><dt>${name}</dt><dd>${html}</dd></div>`).join('')}</dl>`;
  },

  /** The open panel of one value's chain, under the id its button controls. */
  chain(m, r, valueIndex) {
    const value = (r.values || [])[valueIndex];
    if (!value || !value.chain) return '';
    const id = this.chainId(r, value, valueIndex);
    const name = `Provenance chain, ${r.label || r.key}`;
    return `<div class="rc-chain" id="${id}" role="group" aria-label="${this.escape(name)}">${
      this.chainSteps(m, r, valueIndex)}</div>`;
  },

  // --- Source text -----------------------------------------------------------

  /**
   * The source text with the record's passages marked. A block mark (a
   * publication's passage) carries its label; a value mark sits inside it. A
   * mark that leaves the text or crosses another one is dropped rather than
   * drawn at a guessed place.
   */
  sourceBody(text, marks, textHtml) {
    const s = String(text == null ? '' : text);
    const render = typeof textHtml === 'function' ? textHtml : t => this.escape(t);
    const valid = (marks || []).filter(mk => mk && Number.isInteger(mk.start) && Number.isInteger(mk.end)
      && mk.start >= 0 && mk.end > mk.start && mk.end <= s.length)
      .sort((a, b) => a.start - b.start || b.end - a.end);
    const root = { start: 0, end: s.length, children: [], kind: 'root' };
    const stack = [root];
    for (const mk of valid) {
      while (stack.length > 1 && mk.start >= stack[stack.length - 1].end) stack.pop();
      const parent = stack[stack.length - 1];
      if (mk.end > parent.end) continue;
      // A block holds values, never another block.
      if (mk.kind === 'block' && stack.some(node => node.kind === 'block')) continue;
      const node = Object.assign({ children: [] }, mk);
      parent.children.push(node);
      stack.push(node);
    }
    const draw = node => {
      let out = '';
      let cursor = node.start;
      let afterBlock = false;
      for (const child of node.children) {
        let gap = s.slice(cursor, child.start);
        // A block is a box of its own, so the line break beside it would add
        // an empty line inside the flow.
        if (child.kind === 'block') {
          if (afterBlock) gap = gap.replace(/^\n/, '');
          gap = gap.replace(/\n$/, '');
        } else if (afterBlock) {
          gap = gap.replace(/^\n/, '');
        }
        out += render(gap);
        const inner = draw(child);
        if (child.kind === 'block') {
          const label = child.label ? `<span class="source-slice-label">${this.escape(child.label)}</span>` : '';
          out += `<span class="source-slice">${label}${inner}</span>`;
          afterBlock = true;
        } else {
          const id = child.id ? ` id="${this.escape(this._id(child.id))}" tabindex="-1"` : '';
          out += `<mark class="rc-mark"${id} data-mark-for="${this.escape(child.key || '')}">${inner}</mark>`;
          afterBlock = false;
        }
        cursor = child.end;
      }
      let rest = s.slice(cursor, node.end);
      if (afterBlock) rest = rest.replace(/^\n/, '');
      return out + render(rest);
    };
    return draw(root);
  },

  /** The source region of a card. */
  source(m, textHtml) {
    const st = m.sourceText || {};
    if (!st.text) return '';
    const label = st.label ? `<h3 class="rc-group-heading">${this.escape(st.label)}</h3>` : '';
    return `<section class="rc-source" data-region="source">${label}<div class="rc-source-text">${
      this.sourceBody(st.text, st.marks, textHtml)}</div></section>`;
  },
};

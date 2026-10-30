/**
 * Records: the record desk's controller (knowledge/design.md, Record desk).
 *
 * Records is the result view of the reader under its address `#records`. The
 * wiki records are App's result list and cards; this file adds what the desk
 * holds beyond them: the source a list draws from, the print records where
 * the local review server serves them, the print card under `#print=<id>`,
 * and the way back from a card to the place in the list it was opened from.
 *
 * Trust boundary: print records exist only on this computer, because the
 * rights to the print volumes are unresolved. They load only when
 * `local/print-structure.json` answers, then `/review/status` answers JSON,
 * then `/viewer/index.json` answers, and then the print adapter module
 * imports. Without all four the page requests no print data, renders no
 * source control and names no print record. The module is imported
 * dynamically inside try/catch and never statically, so the reader keeps
 * working on every host where it is absent (and in the vm tests, which have
 * no dynamic import).
 *
 * The adapter's contract (pipeline/print_volumes/viewer/records-print.js,
 * strand S3): `load()` reads the print index once; `list(filter)` returns the
 * slip models of the objects a filter `{q, volume, part, kind}` selects, each
 * `{kind: 'print', id, entry, title, sourceSign, relation, review, snippet}`;
 * `model(id)` returns the card model of one object (record-card.js). Any of
 * them may return a promise.
 */
const Records = {
  SOURCES: ['wiki', 'print', 'both'],
  UNITS: ['object', 'entry'],
  PRINT_MODULE: '/viewer/records-print.js',
  PAGE_SIZE: 50,

  /** The print filters of the address, beside the wiki filters App reads. */
  state: { source: 'wiki', unit: 'object', volume: '', part: '', kind: '', page: 0 },

  print: { status: 'unknown', module: null, structure: null },
  _probe: null,
  _load: null,
  _structure: null,
  _renderToken: 0,

  // --- Address ---------------------------------------------------------------

  /**
   * Read source, unit and print filters from the hash. A source that needs
   * print records reads as wiki where they are not available, so an address
   * shows the same records on every host that can show them, and the wiki
   * where it cannot.
   */
  fromParams(params) {
    const src = params.get('src');
    const unit = params.get('unit');
    this.state = {
      source: this.SOURCES.includes(src) ? src : 'wiki',
      unit: this.UNITS.includes(unit) ? unit : 'object',
      volume: params.get('vol') || '',
      part: params.get('part') || '',
      kind: params.get('kind') || '',
      page: 0,
    };
    this.requested = this.state.source;
    if (this.print.status !== 'available') this.state.source = 'wiki';
    return this.state;
  },

  /** True while this computer has not yet answered whether it shows print. */
  _pending() {
    return App.state.isLocal && this.print.status === 'unknown';
  },

  /**
   * Write the non-default source state into the parameters of a list hash.
   * While the answer is pending, an address that asked for print keeps
   * asking, so the answer can still route it; where print is unavailable the
   * address loses the request.
   */
  writeParams(params) {
    const s = this.state;
    const source = this._pending() && this.requested ? this.requested : s.source;
    if (source === 'wiki') return;
    params.set('src', source);
    if (s.volume) params.set('vol', s.volume);
    if (s.part) params.set('part', s.part);
    if (s.kind) params.set('kind', s.kind);
    if (s.unit !== 'object') params.set('unit', s.unit);
  },

  /** The address of one print record; its id carries `/` and `#`. */
  printHash(id) {
    return `#print=${encodeURIComponent(id)}`;
  },

  /**
   * The Records address of a print count, in the unit of that count. A count
   * of entries opens the entries, never the objects they hold.
   */
  printHref({ volume = '', part = '', kind = '', unit = 'object' } = {}) {
    const params = new URLSearchParams();
    params.set('src', 'print');
    if (volume) params.set('vol', volume);
    if (part) params.set('part', part);
    if (kind) params.set('kind', kind);
    if (unit !== 'object') params.set('unit', unit);
    return `#records&${params.toString()}`;
  },

  // The wiki data name the print volumes in words, the print structure by key.
  CITED_VOLUMES: { 'main-volume': 'I', 'addendum-1': 'A1', 'addendum-2': 'A2' },

  /**
   * The Records address of a print address a wiki page cites, or '' where
   * print records cannot be shown. A cited entry opens its section searched
   * for the address, a cited section the section.
   */
  printCitationHref(cite) {
    const volume = cite && this.CITED_VOLUMES[cite.printVolume];
    if (this.print.status !== 'available' || !volume) return '';
    const href = this.printHref({ volume, part: cite.printSection || '', unit: 'entry' });
    return cite.citationTarget === 'entry' && cite.printAddress
      ? `${href}&q=${encodeURIComponent(cite.printAddress)}` : href;
  },

  showsWiki() {
    return this.state.source !== 'print';
  },

  showsPrint() {
    return this.state.source !== 'wiki' && this.print.status === 'available';
  },

  // --- Print availability ------------------------------------------------------

  async _json(url) {
    try {
      const resp = await fetch(url);
      if (!resp.ok) return null;
      return await resp.json();
    } catch (err) {
      return null;
    }
  },

  /** The local print structure, asked for once; null on the published site. */
  printStructure() {
    if (!App.state.isLocal) return Promise.resolve(null);
    if (!this._structure) this._structure = this._json('local/print-structure.json');
    return this._structure;
  },

  // Kept apart so a test can stand in for the browser's dynamic import.
  _import(url) {
    return import(url);
  },

  /**
   * Whether print records can be shown here, asked once. Each step runs only
   * when the one before it answered, so a fresh clone on a plain static
   * server asks for the structure file alone and the published site asks
   * for nothing.
   */
  probePrint() {
    if (!App.state.isLocal) return Promise.resolve(false);
    if (!this._probe) {
      this._probe = (async () => {
        const structure = await this.printStructure();
        if (!structure) return false;
        // A static server can answer any path; only the review server
        // answers this one with its recording state.
        const status = await this._json('/review/status');
        if (!status || typeof status !== 'object' || !('recording' in status)) return false;
        try {
          const index = await fetch('/viewer/index.json', { method: 'HEAD' });
          if (!index.ok) return false;
        } catch (err) {
          return false;
        }
        let mod = null;
        try {
          mod = await this._import(this.PRINT_MODULE);
        } catch (err) {
          return false;
        }
        if (!mod || !['load', 'list', 'model'].every(name => typeof mod[name] === 'function')) return false;
        this.print = { status: 'available', module: mod, structure,
          recording: status.recording === true };
        return true;
      })().then((ok) => {
        if (!ok) this.print = { status: 'unavailable', module: null, structure: null };
        return ok;
      });
    }
    return this._probe;
  },

  /** The print index, loaded once and only for a list that shows print. */
  ensureLoaded() {
    if (!this._load) {
      this._load = Promise.resolve(this.print.module.load());
      this._load.catch(() => { this._load = null; });
    }
    return this._load;
  },

  // --- Print list --------------------------------------------------------------

  /** Slips of the current filter, one per entry where the unit is the entry. */
  async printItems(query) {
    await this.ensureLoaded();
    const s = this.state;
    const raw = await this.print.module.list({ q: query || '', volume: s.volume, part: s.part, kind: s.kind });
    const models = (Array.isArray(raw) ? raw : (raw && raw.items) || []).filter(m => m && m.id != null);
    return this.groupByUnit(models, s.unit);
  },

  /**
   * One item per object, or per entry with the objects it holds. The first
   * object of an entry in document order stands for it, so the slip opens
   * where the entry begins.
   */
  groupByUnit(models, unit) {
    if (unit !== 'entry') return models.map(model => ({ model, count: 1 }));
    const byEntry = new Map();
    for (const model of models) {
      // Counting an object as its own entry would print a count of objects
      // under the word "entries", so a slip without its entry stops the list.
      if (model.entry == null || model.entry === '') throw new Error(`print slip ${model.id} names no entry`);
      const key = String(model.entry);
      const item = byEntry.get(key);
      if (item) item.count += 1;
      else byEntry.set(key, { model, count: 1 });
    }
    return [...byEntry.values()];
  },

  unitWord(n) {
    if (this.state.unit === 'entry') return n === 1 ? 'print entry' : 'print entries';
    return n === 1 ? 'print object' : 'print objects';
  },

  /** Words for the print filters, in the order of the address. */
  printFilterWords() {
    const s = this.state;
    const words = [];
    if (s.volume) words.push(this.volumeName(s.volume));
    if (s.part) words.push(/^[A-R]$/.test(s.part) ? `section ${s.part}` : s.part);
    if (s.kind) words.push(s.kind === 'index' ? 'index entries' : s.kind.replace(/[_-]+/g, ' '));
    return words;
  },

  volumeName(key) {
    const volumes = typeof PRINT_VOLUMES !== 'undefined' ? PRINT_VOLUMES : [];
    const volume = volumes.find(v => v.key === key);
    return volume ? volume.name : `volume ${key}`;
  },

  /** Chips of the print filters; the source itself has its own control. */
  chips() {
    if (!this.showsPrint()) return [];
    const s = this.state;
    const chips = [];
    if (s.volume) chips.push({ key: 'vol', label: 'Volume', display: this.volumeName(s.volume) });
    if (s.part) chips.push({ key: 'part', label: 'Section', display: s.part });
    if (s.kind) chips.push({ key: 'kind', label: 'Kind', display: s.kind.replace(/[_-]+/g, ' ') });
    if (s.unit !== 'object') chips.push({ key: 'unit', label: 'Listed by', display: 'entry' });
    return chips;
  },

  CHIP_KEYS: { vol: 'volume', part: 'part', kind: 'kind', unit: 'unit' },

  /** Drop one print filter; true when the key is one. */
  clearKey(key) {
    const field = this.CHIP_KEYS[key];
    if (!field) return false;
    this.state[field] = field === 'unit' ? 'object' : '';
    return true;
  },

  setSource(source) {
    if (!this.SOURCES.includes(source) || (source !== 'wiki' && this.print.status !== 'available')) return;
    this.state.source = source;
    this.state.page = 0;
    App.state.records = true;
    App.applyFilters({ push: true });
    App.showView('results', { focus: false });
  },

  // --- Rendering ---------------------------------------------------------------

  _el(id) {
    return typeof document !== 'undefined' && document.getElementById ? document.getElementById(id) : null;
  },

  /**
   * The source control. It is drawn only where print records can be shown,
   * because a choice that can never take effect is no control.
   */
  renderSourceControl() {
    const host = this._el('records-source');
    if (!host) return;
    // Called while a list renders, which can be before the view switches to it.
    const listed = !App.state.singleEntry && !App.state.customLabel;
    if (this.print.status !== 'available' || !listed) {
      host.innerHTML = '';
      host.hidden = true;
      return;
    }
    const labels = { wiki: 'Wiki', print: 'Print', both: 'Both' };
    host.innerHTML = `<fieldset class="records-source-set"><legend class="records-source-legend">Source</legend>${
      this.SOURCES.map(src => `<label class="records-source-option"><input type="radio" name="records-src" value="${src}"${
        src === this.state.source ? ' checked' : ''}> ${labels[src]}</label>`).join('')}</fieldset>`;
    host.hidden = false;
  },

  /**
   * Bring the source chrome in line with the route App rendered: the control,
   * and for a list that shows print its print records. Called after every
   * list render; a print request starts only where print is available.
   */
  afterRender(snapshot) {
    this.renderSourceControl();
    const section = this._el('records-print');
    if (!this.showsPrint() || App.state.singleEntry || App.state.customLabel) {
      if (section) {
        section.innerHTML = '';
        section.hidden = true;
      }
      if (snapshot) this.restore(snapshot);
      return Promise.resolve();
    }
    if (this.state.source === 'print') this._hideWikiChrome();
    return this.renderPrint(snapshot);
  },

  /** A print-only list has no wiki facets, sort or wiki defaults note. */
  _hideWikiChrome() {
    for (const id of ['facets', 'mobile-filter-btn', 'sort-select', 'list-defaults', 'batch-export-btn']) {
      const el = this._el(id);
      if (el && el.classList) el.classList.add('hidden');
    }
    const label = typeof document !== 'undefined' && document.querySelector
      ? document.querySelector('.sort-label') : null;
    if (label) label.classList.add('hidden');
  },

  _slipHtml(item) {
    const model = Object.assign({}, item.model, { kind: 'print', permalink: this.printHash(item.model.id) });
    const note = item.count > 1
      ? `<p class="records-slip-note">${item.count} objects in this entry</p>` : '';
    return `<li class="records-slip" data-record="${RecordCard.escape(model.id)}">${RecordCard.slip(model)}${note}</li>`;
  },

  _countLabel(n) {
    const filters = this.printFilterWords();
    const q = App.state.query;
    let label = `${n.toLocaleString('en')} ${this.unitWord(n)}`;
    if (q) label += ` for \u201c${q}\u201d`;
    if (filters.length) label += `: ${filters.join(', ')}`;
    return label;
  },

  /** Print slips into their section, with their own count and paging. */
  async renderPrint(snapshot) {
    const section = this._el('records-print');
    if (!section) return;
    const token = ++this._renderToken;
    const both = this.state.source === 'both';
    const heading = both ? '<h2 class="records-print-heading" id="records-print-heading">Print</h2>' : '';
    section.hidden = false;
    section.setAttribute('aria-labelledby', both ? 'records-print-heading' : 'results-count');
    section.innerHTML = `${heading}<p class="records-status" role="status">Loading print records\u2026</p>`;
    // A print-only list has no wiki count to stand in its heading meanwhile.
    const count = this._el('results-count');
    if (!both && count) count.textContent = 'Print records';
    let items;
    try {
      items = await this.printItems(App.state.query);
    } catch (err) {
      if (token !== this._renderToken) return;
      section.innerHTML = `${heading}<p class="records-status" role="alert">The print records could not be loaded (${
        RecordCard.escape(err && err.message ? err.message : String(err))}).
        <button type="button" class="link-btn" data-act="records-retry">Retry</button></p>`;
      return;
    }
    if (token !== this._renderToken) return;
    this._items = items;
    const page = snapshot && Number.isInteger(snapshot.printPage) ? snapshot.printPage : this.state.page;
    this.state.page = page;
    const label = this._countLabel(items.length);
    if (count) count.textContent = both ? `${App._resultsLabel(App.filtered.length)}; ${label}` : label;
    this._drawPrintPage(section, heading, both ? label : '');
    if (snapshot) this.restore(snapshot);
  },

  _drawPrintPage(section, heading, sub) {
    const items = this._items || [];
    const end = Math.min((this.state.page + 1) * this.PAGE_SIZE, items.length);
    const more = end < items.length
      ? '<div class="load-more"><button type="button" data-act="records-more">Load more print records&hellip;</button></div>'
      : '';
    const empty = items.length ? '' : '<p class="records-status">No print records match.</p>';
    const count = sub ? `<p class="records-print-count">${RecordCard.escape(sub)}</p>` : '';
    section.innerHTML = `${heading}${count}${empty}<ol class="records-slips">${
      items.slice(0, end).map(item => this._slipHtml(item)).join('')}</ol>${more}`;
  },

  morePrint() {
    const section = this._el('records-print');
    if (!section || !this._items) return;
    this.state.page += 1;
    const first = this.state.page * this.PAGE_SIZE;
    const both = this.state.source === 'both';
    const heading = both ? '<h2 class="records-print-heading" id="records-print-heading">Print</h2>' : '';
    this._drawPrintPage(section, heading, both ? this._countLabel(this._items.length) : '');
    // The first new slip takes the focus, so the keyboard continues there.
    const link = section.querySelectorAll('.records-slip .rc-slip-title')[first];
    if (link && typeof link.focus === 'function') link.focus();
  },

  // --- Print card ----------------------------------------------------------------

  /**
   * The chains of a print card, registered where the shared chain handler of
   * detail.js finds them (Detail._chains, keyed apart from the wiki pages).
   */
  _registerChains(key, model) {
    if (typeof Detail === 'undefined' || !Detail._chains) return;
    const chains = new Map();
    // The title's chain button stands in the head, under the row RecordCard.head builds for it.
    if (model.titleValue && model.titleValue.chain) {
      const r = { key: 'title', label: 'Title', idBase: `${model.id}-title`, values: [model.titleValue] };
      chains.set(RecordCard.chainId(r, model.titleValue, 0), { r, i: 0 });
    }
    for (const group of model.groups || []) {
      for (const r of group.rows || []) {
        (r.values || []).forEach((value, i) => {
          if (value && value.chain) chains.set(RecordCard.chainId(r, value, i), { r, i });
        });
      }
    }
    Detail._chains.set(key, { model, chains });
  },

  /** The route `#print=<id>`: one print record, read as a record. */
  async openPrint(id) {
    const token = ++this._renderToken;
    const list = this._el('results-list');
    const count = this._el('results-count');
    const missing = () => App._renderMissingMessage('This record address does not resolve here.');
    if (!(await this.probePrint())) {
      if (token === this._renderToken) missing();
      return;
    }
    if (count) count.textContent = 'Loading the record\u2026';
    let model = null;
    try {
      await this.ensureLoaded();
      model = await this.print.module.model(id);
    } catch (err) {
      model = null;
    }
    if (token !== this._renderToken) return;
    if (!model) {
      missing();
      return;
    }
    const m = Object.assign({}, model, { kind: 'print', permalink: this.printHash(model.id != null ? model.id : id) });
    this._registerChains(`print:${m.id}`, m);
    if (count) count.textContent = 'Permalink \u2014 1 print record';
    if (list) list.innerHTML = `<div class="records-print-card">${RecordCard.card(m)}</div>`;
    if (typeof document !== 'undefined') document.title = `${m.title || 'Untitled'} \u2014 ${App.BASE_TITLE}`;
  },

  // --- The way back ----------------------------------------------------------------

  /**
   * What a reader leaves behind on a result route: the scroll position, the
   * open card or the selected result, how far the list was paged, and the
   * print record they followed. Stored on the current history entry, so Back
   * finds it and a fresh visit of the same address starts at the top.
   */
  snapshot(target) {
    const open = typeof document !== 'undefined' && document.querySelector
      ? document.querySelector('#results-list .entry-card.card-expanded') : null;
    const slip = target && target.closest ? target.closest('.records-slip') : null;
    return {
      scrollY: typeof window !== 'undefined' && Number.isFinite(window.scrollY) ? window.scrollY : 0,
      page: App.state.page,
      printPage: this.state.page,
      openPid: App._paneMode ? App.state.selectedId : (open ? parseInt(open.dataset.pid, 10) : null),
      printId: slip ? slip.dataset.record : null,
    };
  },

  saveSnapshot(target) {
    if (App.state.view !== 'results' || typeof history === 'undefined' || !history.replaceState) return;
    const state = Object.assign({}, history.state || {}, { records: this.snapshot(target) });
    history.replaceState(state, '', location.href);
  },

  /** The snapshot of the history entry being routed to, if any. */
  fromHistory() {
    const state = typeof history !== 'undefined' ? history.state : null;
    return state && state.records ? state.records : null;
  },

  /**
   * Return a re-rendered result route to the place its snapshot names: page
   * the list as far as it was, open the card that was open, and scroll back.
   */
  restore(snap) {
    if (!snap) return;
    const pid = Number.isInteger(snap.openPid) ? snap.openPid : null;
    if (!App.state.singleEntry && App.showsList()) {
      const wanted = Number.isInteger(snap.page) ? snap.page : 0;
      if (wanted > App.state.page || (pid != null && App._paneMode && App.state.selectedId !== pid)) {
        App.state.page = Math.max(App.state.page, wanted);
        if (pid != null) App.state.selectedId = pid;
        App.renderResults();
      }
      if (pid != null) {
        if (App._paneMode) App.selectEntry(pid);
        else App.openCard(pid);
      }
    }
    const y = Number.isFinite(snap.scrollY) ? snap.scrollY : 0;
    const back = () => {
      if (typeof window !== 'undefined' && window.scrollTo) window.scrollTo(0, y);
      const target = pid != null ? App._listHeader(pid)
        : (snap.printId && typeof document !== 'undefined' && document.querySelector
          ? document.querySelector(`#records-print .records-slip[data-record="${
            String(snap.printId).replace(/["\\]/g, '\\$&')}"] .rc-slip-title`) : null);
      if (target && typeof target.focus === 'function') target.focus({ preventScroll: true });
    };
    back();
    // The browser restores its own saved position after the route ran, and
    // the view switch moves the focus to its heading; the next frame comes
    // after both.
    if (typeof requestAnimationFrame === 'function') requestAnimationFrame(back);
  },
};

if (typeof document !== 'undefined' && document.addEventListener) {
  // A link followed from a result route leaves its place on the history
  // entry it leaves, before the hash changes.
  document.addEventListener('click', (ev) => {
    const link = ev.target && ev.target.closest ? ev.target.closest('a[href^="#"]') : null;
    if (link) Records.saveSnapshot(link);
  }, true);

  document.addEventListener('change', (ev) => {
    const input = ev.target;
    if (input && input.name === 'records-src') Records.setSource(input.value);
  });

  document.addEventListener('click', (ev) => {
    const btn = ev.target && ev.target.closest ? ev.target.closest('#records-print [data-act]') : null;
    if (!btn) return;
    if (btn.dataset.act === 'records-more') Records.morePrint();
    else if (btn.dataset.act === 'records-retry') Records.renderPrint();
  });
}

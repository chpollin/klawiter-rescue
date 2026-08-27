/**
 * Klawiter Bibliography — Main Application
 * 5-view routing: home, results, detail, stats, page (static content)
 */
const App = {
  data: null,
  entries: [],    // namespace 0 only
  entryMap: new Map(),  // sourcePageId → entry for O(1) lookup
  index: null,
  filtered: [],
  state: {
    query: '',
    filters: {},
    sort: 'relevance',
    browse: false,   // catalogue view without query or filters
    view: 'home',
    entryId: null,
    page: 0,
    pageSize: 50,
    editMode: false,
    isLocal: window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1',
    pendingEdits: {},  // pageId -> { field: { value, oldValue, provenance } }
  },

  async init() {
    try {
      const resp = await fetch('data/klawiter.json');
      if (!resp.ok) throw new Error(`data/klawiter.json: HTTP ${resp.status}`);
      this.data = await resp.json();
      // Filter to namespace 0 only
      this.entries = this.data.entries.filter(e => e.pageNamespace === 0);
      this.entryMap = new Map(this.entries.map(e => [e.sourcePageId, e]));
      this.titleMap = new Map(this.entries.filter(e => e.title).map(e => [e.title, e.sourcePageId]));
      this.verifyData();
      this.bindEvents();
      // Reconciliation data is additive (curation candidates, contested
      // claims) and must never block the first paint; redraw once it is in.
      Edit.loadReconciliation().then(() => {
        if (this.state.view === 'results') this.renderResults();
      });
      if (this.state.isLocal) Edit.restore();   // recover pending edits from a prior session
      this._lastHash = null;
      this.handleRoute();
      window.addEventListener('hashchange', () => this.handleRoute());
      window.addEventListener('popstate', () => this.handleRoute());
    } catch (err) {
      const home = document.getElementById('view-home');
      home.textContent = '';
      const message = document.createElement('p');
      message.style.color = 'var(--sz-burgundy)';
      message.textContent = `Error loading data: ${err.message}`;
      home.appendChild(message);
    }
  },

  verifyData() {
    const e = this.entries;
    const meta = this.data._meta;
    const warnings = [];

    // Compute actual counts
    const ns0 = e.length;
    const nonNs0 = this.data.entries.length - ns0;
    const redirects = Object.keys(this.data.redirects || {}).length;

    // Field coverage (actual)
    const fields = ['title', 'year', 'publisher', 'location', 'language', 'translator', 'pageCount'];
    const cov = {};
    fields.forEach(f => {
      const count = e.filter(x => x[f] != null && x[f] !== '').length;
      cov[f] = { count, pct: +(100 * count / ns0).toFixed(1) };
    });

    // Diversity
    const langs = new Set(e.map(x => x.language).filter(Boolean));
    const locs = new Set(e.map(x => x.location).filter(Boolean));
    const years = e.map(x => x.year).filter(Boolean);
    const minYear = years.length ? Math.min(...years) : '?';
    const maxYear = years.length ? Math.max(...years) : '?';

    // Types
    const types = {};
    e.forEach(x => { types[x.entryType] = (types[x.entryType] || 0) + 1; });
    const typeCount = Object.keys(types).length;

    // Provenance
    const provCount = e.filter(x => x._provenance).length;

    // Compare against pipeline _meta (if present)
    if (meta) {
      if (meta.ns0Count !== ns0) warnings.push(`ns0 count: expected ${meta.ns0Count}, got ${ns0}`);
      if (meta.redirectCount !== redirects) warnings.push(`redirects: expected ${meta.redirectCount}, got ${redirects}`);
      for (const f of fields) {
        if (meta.fieldCoverage && meta.fieldCoverage[f]) {
          const diff = Math.abs(cov[f].pct - meta.fieldCoverage[f].pct);
          if (diff > 0.1) warnings.push(`${f} coverage: expected ${meta.fieldCoverage[f].pct}%, got ${cov[f].pct}%`);
        }
      }
    }

    // Data quality checks
    const markupTitles = e.filter(x => x.title && (/'''/.test(x.title) || /\[\[|\]\]/.test(x.title)));
    if (markupTitles.length) warnings.push(`${markupTitles.length} titles with wiki markup residue`);
    const noTitle = e.filter(x => !x.title).length;
    if (noTitle) warnings.push(`${noTitle} entries without title`);

    // Compact output
    const covLine = fields.map(f => `${f} ${cov[f].pct}%`).join(' | ');

    console.groupCollapsed(`Klawiter Data Verification — ${ns0} entries (ns0)`);
    console.log(`${ns0} entries (ns0) | ${nonNs0} non-ns0 | ${redirects} redirects`);
    console.log(covLine);
    console.log(`${typeCount} types | ${langs.size} languages | ${locs.size} locations | ${minYear}–${maxYear}`);
    if (provCount) console.log(`Provenance: ${provCount} entries with _provenance data`);
    if (warnings.length === 0) {
      console.log(meta ? 'OK — all counts match pipeline baseline' : 'OK — no _meta baseline (pipeline <v14)');
    } else {
      warnings.forEach(w => console.warn(`WARN: ${w}`));
    }
    console.groupEnd();
  },

  // Built lazily on the first search: indexing 5,000+ full texts is the
  // most expensive startup step and the home view never needs it.
  ensureIndex() {
    if (!this.index) this.buildIndex();
  },

  buildIndex() {
    this.index = new FlexSearch.Index({
      tokenize: 'forward',
      resolution: 9,
    });
    this.entries.forEach((e, i) => {
      const text = [
        e.title, e.originalTitle, e.fullBibliographicEntry,
        e.publisher, e.location, e.language, e.translator,
        (e.categories || []).join(' '),
      ].filter(Boolean).join(' ');
      this.index.add(i, text);
    });
  },

  // --- Routing ---
  handleRoute() {
    const hash = location.hash.slice(1);
    // Guard: skip if hash unchanged (avoids double-processing from popstate + hashchange)
    if (hash === this._lastHash) return;
    this._lastHash = hash;
    const params = new URLSearchParams(hash);
    this.state.browse = false;

    // Data-quality workbench (curation view)
    if (hash === 'quality') {
      this.showView('page');
      Curate.render();
      return;
    }

    // Static content pages
    const staticPages = ['about', 'methodology', 'help', 'data', 'jsonld', 'imprint'];
    if (staticPages.includes(hash)) {
      this.showView('page');
      Pages.render(hash);
      return;
    }

    // Browse view — show all entries, no filters. Recognized by the parameter
    // so that the sort state can ride along (#browse&sort=title).
    if (params.has('browse')) {
      this.state.query = '';
      this.state.filters = {};
      this.state.browse = true;
      this.applySortFromParams(params);
      document.getElementById('search-input').value = '';
      this.filtered = [...this.entries];
      this.state.page = 0;
      this.sortEntries();
      this.showView('results');
      this.renderResults();
      Facets.render(this.filtered);
      this.renderChips();
      return;
    }

    // Stats view — explore interface with optional sub-state in hash
    if (hash === 'stats' || hash.startsWith('stats/')) {
      this.state.query = '';
      this.state.filters = {};
      document.getElementById('search-input').value = '';
      this.showView('stats');
      Explore.render(this.entries);
      // Restore explore sub-state from hash if present
      if (hash.startsWith('stats/')) {
        const rest = hash.slice(6);
        const qIdx = rest.indexOf('?');
        const mode = qIdx >= 0 ? rest.slice(0, qIdx) : rest;
        const paramStr = qIdx >= 0 ? rest.slice(qIdx + 1) : '';
        Explore.restoreFromHash(mode, new URLSearchParams(paramStr));
      }
      return;
    }

    // Entry view — show in results with card expanded
    if (params.has('entry')) {
      const pid = parseInt(params.get('entry'));
      const entry = this.entryMap.get(pid);
      if (entry) {
        // Show all entries of the same type as context, with this entry visible
        this.state.query = '';
        this.state.filters = {};
        this.filtered = [entry];
        this.state.page = 0;
        this.showView('results');
        document.getElementById('results-count').textContent = 'Permalink';
        this.renderResults();
        // Auto-expand after render
        setTimeout(() => this.toggleCard(pid), 50);
      } else {
        this.state.query = '';
        this.state.filters = {};
        this.filtered = [];
        this.state.page = 0;
        this.showView('results');
        this.renderResults();
        document.getElementById('results-count').textContent = 'Entry not found';
      }
      return;
    }

    // Redirect resolution
    if (params.has('title')) {
      const title = params.get('title');
      const targetPid = this.data.redirects[title];
      if (targetPid) {
        location.hash = `entry=${targetPid}`;
        return;
      }
    }

    // Parse filters
    this.state.query = params.get('q') || '';
    this.state.filters = {};
    for (const [key, val] of params) {
      if (['type', 'language', 'period', 'location', 'category'].includes(key)) {
        this.state.filters[key] = val;
      }
    }
    this.applySortFromParams(params);

    document.getElementById('search-input').value = this.state.query;

    if (this.state.query || Object.keys(this.state.filters).length > 0) {
      this.applyFilters();
      this.showView('results');
    } else {
      this.showView('home');
      Home.render(this.entries);
    }
  },

  // Sort values the hash may carry. 'triage' orders by data signal and needs
  // the triage artifact, which only the local edit mode loads.
  SORTS: ['relevance', 'year-asc', 'year-desc', 'title', 'triage'],

  /** Validated sort value for a hash parameter set; unknown values fall back. */
  sortFromParams(params) {
    const s = params.get('sort');
    if (!s || !this.SORTS.includes(s)) return 'relevance';
    if (s === 'triage' && !this.state.editMode) return 'relevance';
    return s;
  },

  /** True while the current result list is reproducible from the hash. */
  isAddressableResults() {
    return this.state.view === 'results'
      && (this.state.browse || !!this.state.query || Object.keys(this.state.filters).length > 0);
  },

  applySortFromParams(params) {
    this.state.sort = this.sortFromParams(params);
    const sel = document.getElementById('sort-select');
    if (sel) sel.value = this.state.sort;
  },

  updateURL() {
    const params = new URLSearchParams();
    if (this.state.browse) params.set('browse', '');
    if (this.state.query) params.set('q', this.state.query);
    for (const [k, v] of Object.entries(this.state.filters)) {
      params.set(k, v);
    }
    // Default sort stays out of the URL, so unsorted views keep clean hashes.
    if (this.state.sort && this.state.sort !== 'relevance') params.set('sort', this.state.sort);
    const hash = params.toString();
    history.replaceState(null, '', hash ? `#${hash}` : location.pathname);
    // Keep the route guard in sync: replaceState fires no hashchange, so
    // without this the next navigation back to the very hash we replaced
    // (for example '' for home) would be swallowed as "unchanged".
    this._lastHash = hash;
  },

  // --- Filtering ---
  applyFilters() {
    let indices;
    if (this.state.query) {
      this.ensureIndex();
      indices = this.index.search(this.state.query, { limit: 5000 });
    } else {
      indices = this.entries.map((_, i) => i);
    }

    this.filtered = indices
      .map(i => this.entries[i])
      .filter(e => {
        const f = this.state.filters;
        if (f.type && e.entryType !== f.type) return false;
        if (f.language && e.language !== f.language) return false;
        if (f.period && e.timePeriod !== f.period) return false;
        if (f.location && e.location !== f.location) return false;
        if (f.category && !(e.categories || []).includes(f.category)) return false;
        return true;
      });

    this.sortEntries();
    this.state.page = 0;
    this.renderResults();
    Facets.render(this.filtered);
    this.renderChips();
    this.updateURL();
  },

  sortEntries() {
    // Sort in place — filtered is always a fresh copy from applyFilters()
    const s = this.state.sort;
    if (s === 'year-asc') {
      this.filtered.sort((a, b) => (a.year ?? Infinity) - (b.year ?? Infinity));
    } else if (s === 'year-desc') {
      this.filtered.sort((a, b) => (b.year ?? -Infinity) - (a.year ?? -Infinity));
    } else if (s === 'title') {
      this.filtered.sort((a, b) => (a.title || '').localeCompare(b.title || ''));
    } else if (s === 'triage') {
      // Edit-mode only: most urgent data signal first (census, verify flags,
      // llm, missing). Attention ordering, not a quality ranking; ties keep
      // their previous order (Array.prototype.sort is stable).
      this.filtered.sort((a, b) => Edit.triageRank(a.sourcePageId) - Edit.triageRank(b.sourcePageId));
    }
  },

  // --- Views ---
  showView(view) {
    this.state.view = view;
    document.getElementById('view-home').classList.toggle('hidden', view !== 'home');
    document.getElementById('view-results').classList.toggle('hidden', view !== 'results');
    document.getElementById('view-stats').classList.toggle('hidden', view !== 'stats');
    document.getElementById('view-page').classList.toggle('hidden', view !== 'page');

    // Sidebar only on results view
    document.getElementById('facets').classList.toggle('hidden', view !== 'results');

    // Hide header search on home (home has its own prominent search)
    document.querySelector('.header-search').classList.toggle('hidden', view === 'home');

    // Filter chips only on results view
    const chips = document.getElementById('filter-chips');
    if (view !== 'results') chips.innerHTML = '';

    // Nav active state
    document.getElementById('nav-home').classList.toggle('active', view === 'home');
    document.getElementById('nav-stats').classList.toggle('active', view === 'stats');
    document.getElementById('nav-about').classList.toggle('active',
      view === 'page' && location.hash === '#about');

    // Close dropdown when navigating
    const dropdown = document.getElementById('nav-more');
    if (dropdown) dropdown.classList.remove('open');

    // Update search placeholder
    const input = document.getElementById('search-input');
    input.placeholder = `Search ${this.entries.length.toLocaleString('en')} entries…`;

    // Dynamic page title
    this._updateTitle(view);
  },

  _updateTitle(view) {
    const base = 'Klawiter Bibliography';
    const titles = {
      home: base,
      stats: `Explore \u2014 ${base}`,
    };
    if (titles[view]) { document.title = titles[view]; return; }
    if (view === 'page') {
      const page = location.hash.slice(1);
      const labels = { about: 'About', methodology: 'Methodology', help: 'Help', data: 'Data Access', imprint: 'Imprint', quality: 'Data Quality' };
      document.title = labels[page] ? `${labels[page]} \u2014 ${base}` : base;
      return;
    }
    if (view === 'results') {
      const f = this.state.filters;
      if (f.type) { document.title = `${ENTRY_TYPE_LABELS[f.type] || f.type} \u2014 ${base}`; return; }
      if (this.state.query) { document.title = `\u201c${this.state.query}\u201d \u2014 ${base}`; return; }
      document.title = `Browse \u2014 ${base}`;
      return;
    }
    document.title = base;
  },

  // --- Results ---
  renderResults() {
    const total = this.filtered.length;
    const end = Math.min((this.state.page + 1) * this.state.pageSize, total);
    const visible = this.filtered.slice(0, end);

    const countEl = document.getElementById('results-count');
    countEl.textContent = this._resultsLabel(total);

    // Show/hide batch export button
    const exportBtn = document.getElementById('batch-export-btn');
    if (exportBtn) exportBtn.classList.toggle('hidden', total === 0);

    const list = document.getElementById('results-list');
    if (total === 0) {
      const q = this.state.query ? `for "${esc(this.state.query)}"` : '';
      list.innerHTML = `<div class="empty-state">
        <p>No results ${q}.</p>
        <p>Try broadening your search or removing filters.</p>
      </div>`;
      document.getElementById('load-more').classList.add('hidden');
      return;
    }
    list.innerHTML = visible.map(e => this.renderCard(e)).join('');

    document.getElementById('load-more').classList.toggle('hidden', end >= total);
  },

  renderCard(e) {
    const badge = `<span class="badge badge-${e.entryType}">${ENTRY_TYPE_LABELS[e.entryType] || e.entryType}</span>`;
    const year = e.year ? `<span class="card-meta-text">${e.year}</span>` : '';
    const lang = e.language ? `<span class="card-meta-text">${e.language}</span>` : '';
    const loc = e.location ? `<span class="card-meta-text">${esc(e.location)}</span>` : '';

    const title = hl(esc(e.title || 'Untitled'), this.state.query);

    const parts = [];
    if (e.publisher) parts.push(esc(e.publisher));
    if (e.pageCount) parts.push(e.pageCount + ' pp.');
    const secondary = parts.length ? `<div class="card-secondary">${parts.join(' · ')}</div>` : '';

    const triage = this.state.editMode ? Edit.cardHint(e.sourcePageId) : '';

    // No source-text snippet here: it duplicated the start of the full
    // bibliographic entry shown on expansion. Title plus meta identify the card.
    return `<div class="entry-card" id="card-${e.sourcePageId}" data-pid="${e.sourcePageId}">
      <div class="card-header" tabindex="0" role="button">
        <div class="card-meta">${badge} ${year} ${lang} ${loc} ${triage}</div>
        <div class="card-title"${titleAttrs(e, e.title)}>${title}</div>
        ${secondary}
      </div>
      <div class="card-detail hidden" id="card-detail-${e.sourcePageId}"></div>
    </div>`;
  },

  toggleCard(pageId) {
    const detailEl = document.getElementById(`card-detail-${pageId}`);
    const cardEl = document.getElementById(`card-${pageId}`);
    if (!detailEl || !cardEl) return;

    // If already open, close it
    if (!detailEl.classList.contains('hidden')) {
      detailEl.classList.add('hidden');
      cardEl.classList.remove('card-expanded');
      return;
    }

    // Close any other open card
    document.querySelectorAll('.card-detail:not(.hidden)').forEach(el => {
      el.classList.add('hidden');
      el.closest('.entry-card').classList.remove('card-expanded');
    });

    // Render detail content and expand
    const entry = this.entryMap.get(pageId);
    if (entry) {
      detailEl.innerHTML = Detail.renderInline(entry);
      detailEl.classList.remove('hidden');
      cardEl.classList.add('card-expanded');
      // Scroll card into view if needed
      cardEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  },

  renderChips() {
    const container = document.getElementById('filter-chips');
    const chips = [];
    for (const [key, val] of Object.entries(this.state.filters)) {
      const label = key === 'type' ? 'Type' : key === 'language' ? 'Language' :
                    key === 'period' ? 'Period' : key === 'category' ? 'Category' : 'Location';
      const display = key === 'type' ? (ENTRY_TYPE_LABELS[val] || val) :
                      key === 'period' ? (PERIOD_LABELS[val] || val) : val;
      chips.push(`<span class="chip" data-filter-key="${key}">${esc(label)}: ${esc(display)}
        <button>&times;</button></span>`);
    }
    if (this.state.query) {
      chips.push(`<span class="chip" data-filter-key="search">Search: ${esc(this.state.query)}
        <button>&times;</button></span>`);
    }
    container.innerHTML = chips.join('');
  },

  _resultsLabel(total) {
    const f = this.state.filters;
    const parts = [];
    if (f.type) parts.push(ENTRY_TYPE_LABELS[f.type] || f.type);
    if (f.language) parts.push(f.language);
    if (f.period) parts.push(f.period);
    if (f.location) parts.push(f.location);
    if (this.state.query) parts.push(`\u201c${this.state.query}\u201d`);
    const count = `${total.toLocaleString('en')} result${total !== 1 ? 's' : ''}`;
    return parts.length ? `${parts.join(' \u00b7 ')} \u2014 ${count}` : count;
  },

  setFilter(key, value) {
    this.state.filters[key] = value;
    this.applyFilters();
    this.showView('results');
  },

  removeFilter(key) {
    delete this.state.filters[key];
    if (!this.state.query && Object.keys(this.state.filters).length === 0) {
      location.hash = '';
    } else {
      this.applyFilters();
    }
  },

  clearSearch() {
    this.state.query = '';
    document.getElementById('search-input').value = '';
    if (Object.keys(this.state.filters).length === 0) {
      location.hash = '';
    } else {
      this.applyFilters();
    }
  },

  // Session-scoped result list from the data-quality workbench: shows a
  // precomputed entry set under its own label. Not hash-addressable — the
  // lists derive from artifacts, not from filter state.
  showCustomResults(entries, label) {
    this.state.query = '';
    this.state.filters = {};
    this.state.browse = false;
    document.getElementById('search-input').value = '';
    this.filtered = [...entries];
    this.state.page = 0;
    this.sortEntries();
    this.showView('results');
    this.renderResults();
    Facets.render(this.filtered);
    this.renderChips();
    document.getElementById('results-count').textContent =
      `${label} — ${entries.length.toLocaleString('en')} entr${entries.length === 1 ? 'y' : 'ies'}`;
  },

  // Edit-mode keyboard: j/k walks the result cards (next/previous expanded).
  _stepCard(dir) {
    const cards = [...document.querySelectorAll('#results-list .entry-card')];
    if (!cards.length) return;
    const openIdx = cards.findIndex(c => c.classList.contains('card-expanded'));
    const next = openIdx === -1 ? (dir > 0 ? 0 : cards.length - 1) : openIdx + dir;
    if (next < 0 || next >= cards.length) return;
    this.toggleCard(parseInt(cards[next].dataset.pid));
  },

  // --- Events ---
  bindEvents() {
    let timer;
    document.getElementById('search-input').addEventListener('input', (ev) => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        this.state.query = ev.target.value.trim();
        if (this.state.query || Object.keys(this.state.filters).length > 0) {
          this.applyFilters();
          this.showView('results');
        } else {
          location.hash = '';
        }
      }, 200);
    });

    document.getElementById('sort-select').addEventListener('change', (ev) => {
      this.state.sort = ev.target.value;
      this.sortEntries();
      this.renderResults();
      // Only a hash-addressable result list may write itself back to the URL;
      // the workbench lists derive from artifacts and carry no hash.
      if (this.isAddressableResults()) this.updateURL();
    });

    // Delegated click/keydown on results list (replaces per-card inline handlers)
    const resultsList = document.getElementById('results-list');
    resultsList.addEventListener('click', (ev) => {
      const header = ev.target.closest('.card-header');
      if (header) {
        const card = header.closest('.entry-card');
        if (card) this.toggleCard(parseInt(card.dataset.pid));
      }
    });
    resultsList.addEventListener('keydown', (ev) => {
      if (ev.key === 'Enter' || ev.key === ' ') {
        const header = ev.target.closest('.card-header');
        if (header) {
          ev.preventDefault();
          const card = header.closest('.entry-card');
          if (card) this.toggleCard(parseInt(card.dataset.pid));
        }
      }
    });

    // Delegated click on filter chips
    document.getElementById('filter-chips').addEventListener('click', (ev) => {
      const btn = ev.target.closest('button');
      if (!btn) return;
      const chip = btn.closest('.chip');
      if (!chip) return;
      const key = chip.dataset.filterKey;
      if (key === 'search') this.clearSearch();
      else this.removeFilter(key);
    });

    // Batch export button
    document.getElementById('batch-export-btn').addEventListener('click', () => {
      Export.batchBibtex(this.filtered);
    });

    document.getElementById('load-more-btn').addEventListener('click', () => {
      this.state.page++;
      const start = this.state.page * this.state.pageSize;
      const end = Math.min(start + this.state.pageSize, this.filtered.length);
      const visible = this.filtered.slice(start, end);
      document.getElementById('results-list')
        .insertAdjacentHTML('beforeend', visible.map(e => this.renderCard(e)).join(''));
      document.getElementById('load-more').classList.toggle('hidden', end >= this.filtered.length);
    });

    document.getElementById('home-link').addEventListener('click', (ev) => {
      ev.preventDefault();
      location.hash = '';
    });

    // Nav "More" dropdown
    const dropdownToggle = document.querySelector('#nav-more .nav-dropdown-toggle');
    if (dropdownToggle) {
      dropdownToggle.addEventListener('click', (ev) => {
        ev.stopPropagation();
        const dropdown = document.getElementById('nav-more');
        const isOpen = dropdown.classList.toggle('open');
        dropdownToggle.setAttribute('aria-expanded', isOpen);
      });
      document.addEventListener('click', () => {
        const dropdown = document.getElementById('nav-more');
        dropdown.classList.remove('open');
        dropdownToggle.setAttribute('aria-expanded', 'false');
      });
    }

    // Mobile filter
    document.getElementById('mobile-filter-btn').addEventListener('click', () => {
      document.getElementById('mobile-facets').classList.remove('hidden');
      document.getElementById('mobile-facet-content').innerHTML =
        document.getElementById('facets').innerHTML;
    });
    document.getElementById('mobile-filter-close').addEventListener('click', () => {
      document.getElementById('mobile-facets').classList.add('hidden');
    });

    // Edit-mode keyboard navigation on the results list (j = next, k = previous).
    document.addEventListener('keydown', (ev) => {
      if (!this.state.editMode || this.state.view !== 'results') return;
      const t = ev.target;
      if (t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName))) return;
      if (ev.key === 'j' || ev.key === 'k') {
        ev.preventDefault();
        this._stepCard(ev.key === 'j' ? 1 : -1);
      }
    });

    // Edit mode toggle (localhost only)
    if (this.state.isLocal) {
      const header = document.querySelector('.header-inner');
      const toggle = document.createElement('button');
      toggle.id = 'edit-toggle';
      toggle.className = 'edit-toggle-btn';
      toggle.title = 'Curation mode (available on localhost only): review fields against the source, decide authority candidates, export decisions as a patch file';
      toggle.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 3a2.83 2.83 0 114 4L7.5 20.5 2 22l1.5-5.5L17 3z"/></svg> Edit';
      toggle.onclick = () => this.toggleEditMode();
      header.appendChild(toggle);
    }
  },

  toggleEditMode() {
    // The curation mode is a localhost tool; the published site must not
    // enter it even when the setter is called from the console.
    if (!this.state.isLocal) return;
    this.state.editMode = !this.state.editMode;
    document.body.classList.toggle('edit-mode', this.state.editMode);
    const btn = document.getElementById('edit-toggle');
    if (btn) {
      btn.classList.toggle('active', this.state.editMode);
      btn.innerHTML = this.state.editMode
        ? '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 3a2.83 2.83 0 114 4L7.5 20.5 2 22l1.5-5.5L17 3z"/></svg> Editing'
        : '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 3a2.83 2.83 0 114 4L7.5 20.5 2 22l1.5-5.5L17 3z"/></svg> Edit';
    }
    this._setTriageSortOption(this.state.editMode);
    if (this.state.editMode) {
      // Triage hints need the artifact; refresh once it is in (cards render
      // their hint chips only from a full pass, so redraw the results list).
      Promise.all([Edit.loadTriage(), Edit.loadReconciliation()])
        .then(() => this._refreshAfterEditToggle());
    } else {
      this._refreshAfterEditToggle();
    }
  },

  // The "Prüfbedarf" sort exists only while edit mode is on.
  _setTriageSortOption(on) {
    const sel = document.getElementById('sort-select');
    if (!sel) return;
    let opt = sel.querySelector('option[value="triage"]');
    if (on && !opt) {
      opt = document.createElement('option');
      opt.value = 'triage';
      opt.textContent = 'Needs review first';
      sel.appendChild(opt);
    } else if (!on && opt) {
      if (this.state.sort === 'triage') {
        this.state.sort = 'relevance';
        sel.value = 'relevance';
        this.sortEntries();
        if (this.isAddressableResults()) this.updateURL();
      }
      opt.remove();
    }
  },

  // Redraw the results list after an edit-mode change, keeping the
  // expanded card open.
  _refreshAfterEditToggle() {
    if (this.state.view !== 'results') return;
    const expanded = document.querySelector('.entry-card.card-expanded');
    const expandedPid = expanded ? parseInt(expanded.dataset.pid) : null;
    if (this.state.sort === 'triage') this.sortEntries();
    this.renderResults();
    if (expandedPid != null && this.entryMap.has(expandedPid)) this.toggleCard(expandedPid);
  },
};

// Boot (constants, utils, export loaded via separate script tags)
document.addEventListener('DOMContentLoaded', () => App.init());

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
    customLabel: null,  // session list opened from the workbench or Explore
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
      this._clearUnavailable();
      // The verification runs some fifteen full passes over the corpus and
      // writes to the console; that is a development instrument and has no
      // business in the critical path of the published site.
      if (this.state.isLocal) this.verifyData();
      if (!this._eventsBound) {
        this.bindEvents();
        window.addEventListener('hashchange', () => this.handleRoute());
        window.addEventListener('popstate', () => this.handleRoute());
        this._eventsBound = true;
      }
      if (this.state.isLocal) {
        Edit.restore();   // recover pending edits from a prior session
        this._notePendingFromPreviousSession();
      }
      this._lastHash = null;
      this.handleRoute();
      this._prewarmIndex();
    } catch (err) {
      this._renderUnavailable(err.message);
    }
  },

  /**
   * Full-page failure state. Without the dataset nothing in the header does
   * anything, so navigation and search are visibly disabled rather than left
   * inert, and the cause is named next to a retry.
   */
  _renderUnavailable(cause) {
    document.body.classList.add('app-unavailable');
    for (const id of ['view-results', 'view-stats', 'view-page']) {
      const el = document.getElementById(id);
      if (el) el.classList.add('hidden');
    }
    const input = document.getElementById('search-input');
    if (input) input.disabled = true;
    document.querySelectorAll('.site-nav a').forEach(a => a.setAttribute('aria-disabled', 'true'));
    const home = document.getElementById('view-home');
    if (!home) return;
    home.classList.remove('hidden');
    home.innerHTML = `<div class="fatal-error" role="alert">
      <h1>The bibliography could not be loaded</h1>
      <p class="fatal-cause"></p>
      <p>The dataset file is served from this site; a reload usually resolves a
         transient network error.</p>
      <p><button id="fatal-retry" class="browse-btn">Retry</button></p>
    </div>`;
    home.querySelector('.fatal-cause').textContent = cause;
    const retry = document.getElementById('fatal-retry');
    if (retry) retry.addEventListener('click', () => this.init());
  },

  _clearUnavailable() {
    document.body.classList.remove('app-unavailable');
    const input = document.getElementById('search-input');
    if (input) input.disabled = false;
    document.querySelectorAll('.site-nav a').forEach(a => a.removeAttribute('aria-disabled'));
  },

  /**
   * A restored session shows the save counter while every field stays
   * read-only until edit mode is on. Say so at the badge instead of leaving a
   * counter that answers to nothing.
   */
  _notePendingFromPreviousSession() {
    if (this.state.editMode || Edit.getPendingCount() === 0) return;
    const saveBtn = document.getElementById('edit-save-btn');
    if (!saveBtn || document.getElementById('edit-pending-note')) return;
    const note = document.createElement('span');
    note.id = 'edit-pending-note';
    note.className = 'edit-pending-note';
    note.textContent = 'pending decisions from a previous session — enable Edit to continue';
    saveBtn.insertAdjacentElement('afterend', note);
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

  /** Shorter inputs match almost everything and are not worth a full pass. */
  MIN_QUERY_LENGTH: 2,

  /** Cap on the hits a single query returns; a reached cap is disclosed. */
  SEARCH_LIMIT: 5000,

  /** Result count above which a batch export asks first. */
  BATCH_CONFIRM_ABOVE: 1000,

  // Built lazily: indexing the full texts is the most expensive startup step
  // and the home view never needs it.
  ensureIndex() {
    if (!this.index) this.buildIndex();
  },

  /**
   * Build the index once the first paint is done. Building it on the first
   * keystroke instead blocked the main thread exactly while the visitor was
   * typing; idle time before that is free.
   */
  _prewarmIndex() {
    const build = () => { try { this.ensureIndex(); } catch (e) { /* built on demand instead */ } };
    if (typeof requestIdleCallback === 'function') requestIdleCallback(build, { timeout: 3000 });
    else if (typeof setTimeout === 'function') setTimeout(build, 1200);
  },

  buildIndex() {
    this.index = new FlexSearch.Index({
      tokenize: 'forward',
      resolution: 9,
      // Diacritics folding: the corpus is full of transliterations, and
      // without it "Zoscenko" misses "Zoščenko".
      charset: 'latin:advanced',
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
  /** Hashes that render into #view-page through Pages.render. */
  STATIC_PAGES: ['about', 'data'],

  /** Old hashes of the pre-merge layout, mapped to their new section. */
  LEGACY_ROUTES: {
    methodology: 'about/methodology',
    help: 'about/help',
    imprint: 'about/imprint',
    jsonld: 'data/playground',
  },

  /** Scroll a rendered page section into view; the id is set by Pages. */
  _scrollToSection(section) {
    const el = document.getElementById(`sec-${section}`);
    if (el) el.scrollIntoView({ block: 'start' });
  },

  /** Fragments that address an element on the page rather than a route. */
  ELEMENT_FRAGMENTS: ['main-content'],

  /** Drop query, filters and the search field; every non-results route does. */
  _resetSearchState() {
    this.state.query = '';
    this.state.filters = {};
    const input = document.getElementById('search-input');
    if (input) input.value = '';
  },

  handleRoute() {
    const hash = location.hash.slice(1);
    // The skip link points at #main-content. Treating it as a route threw the
    // reader back to the start view, which is the opposite of skipping.
    if (this.ELEMENT_FRAGMENTS.includes(hash)) return;
    // Guard: skip if hash unchanged (avoids double-processing from popstate + hashchange)
    if (hash === this._lastHash) return;
    this._lastHash = hash;
    const params = new URLSearchParams(hash);
    this.state.browse = false;
    this.state.customLabel = null;
    this._setResultsContext('');

    // Legacy deep links from the four-page layout. The pages were merged into
    // #about and #data; the old hashes stay valid and land on their section.
    const legacy = this.LEGACY_ROUTES[hash];
    if (legacy) {
      location.hash = legacy;
      return;
    }

    // Data-quality workbench (curation view)
    if (hash === 'quality') {
      this._resetSearchState();
      this.showView('page');
      Curate.render();
      return;
    }

    // Static content pages, optionally with a section anchor: '#about/help'.
    const [slug, section] = hash.split('/');
    if (this.STATIC_PAGES.includes(slug)) {
      this._resetSearchState();
      this.showView('page');
      Pages.render(slug);
      if (section) this._scrollToSection(section);
      return;
    }

    // Browse view — show all entries, no filters. Recognized by the parameter
    // so that the sort state can ride along (#browse&sort=title).
    if (params.has('browse')) {
      this._resetSearchState();
      this.state.browse = true;
      this.applySortFromParams(params);
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
      this._resetSearchState();
      this.showView('stats');
      this._renderExploreLoading();
      this.ensureExploreLibs().then(() => {
        if (this.state.view !== 'stats') return;   // navigated away while loading
        Explore.render(this.entries);
        // Restore explore sub-state from hash if present
        if (hash.startsWith('stats/')) {
          const rest = hash.slice(6);
          const qIdx = rest.indexOf('?');
          const mode = qIdx >= 0 ? rest.slice(0, qIdx) : rest;
          const paramStr = qIdx >= 0 ? rest.slice(qIdx + 1) : '';
          Explore.restoreFromHash(mode, new URLSearchParams(paramStr));
        }
      }).catch(() => this._renderExploreError());
      return;
    }

    // Entry view — show in results with card expanded
    if (params.has('entry')) {
      const pid = parseInt(params.get('entry'), 10);
      const entry = this.entryMap.get(pid);
      this._resetSearchState();
      this.state.page = 0;
      this.filtered = entry ? [entry] : [];
      this.showView('results');
      // The sidebar and the chip bar would otherwise keep the state of the
      // result list this permalink was opened from.
      Facets.render(this.filtered);
      this.renderChips();
      if (entry) {
        this.renderResults();
        // renderResults writes the count label, so the permalink label has to
        // be set after it, not before.
        document.getElementById('results-count').textContent = 'Permalink — 1 entry';
        // Auto-expand after render
        setTimeout(() => this.toggleCard(pid), 50);
      } else {
        this._renderMissingPage('This page ID does not exist (it may have been a redirect).');
      }
      return;
    }

    // Redirect resolution
    if (params.has('title')) {
      const title = params.get('title');
      const redirects = (this.data && this.data.redirects) || {};
      const targetPid = redirects[title] || (this.titleMap && this.titleMap.get(title));
      if (targetPid) {
        location.hash = `entry=${targetPid}`;
        return;
      }
      // An unresolvable title used to fall through to the start view without a
      // word, which reads as a broken link rather than a missing page.
      this._resetSearchState();
      this.state.page = 0;
      this.filtered = [];
      this.showView('results');
      Facets.render(this.filtered);
      this.renderChips();
      this._renderMissingPage('This page title does not exist (it may have been a redirect).');
      return;
    }

    // Parse filters
    this.state.query = params.get('q') || '';
    this.state.filters = {};
    for (const [key, val] of params) {
      if (App.FILTER_KEYS.includes(key)) {
        this.state.filters[key] = val;
      }
    }
    this.applySortFromParams(params);

    const input = document.getElementById('search-input');
    if (input) input.value = this.state.query;

    if (this.state.query || Object.keys(this.state.filters).length > 0) {
      // A route render reproduces a state that is already in the URL, so it
      // normalizes the hash rather than adding a second entry for it.
      this.applyFilters({ push: false });
      this.showView('results');
    } else {
      this.showView('home');
      Home.render(this.entries);
    }
  },

  /** Message page for a permalink that resolves to nothing. */
  _renderMissingPage(message) {
    const countEl = document.getElementById('results-count');
    if (countEl) countEl.textContent = 'Not found';
    const exportBtn = document.getElementById('batch-export-btn');
    if (exportBtn) exportBtn.classList.add('hidden');
    const loadMore = document.getElementById('load-more');
    if (loadMore) loadMore.classList.add('hidden');
    const list = document.getElementById('results-list');
    if (!list) return;
    list.innerHTML = `<div class="empty-state">
      <p class="missing-page-message"></p>
      <p><a href="#">Back to the start page</a></p>
    </div>`;
    list.querySelector('.missing-page-message').textContent = message;
  },

  // --- Explore libraries ---
  /** d3 first: topojson-client and d3-sankey both read the d3 global. */
  EXPLORE_SCRIPTS: ['vendor/d3.v7.min.js', 'vendor/topojson-client.min.js',
    'vendor/d3-sankey.min.js'],

  _loadScript(src) {
    return new Promise((resolve, reject) => {
      const el = document.createElement('script');
      el.src = src;
      el.onload = () => resolve();
      el.onerror = () => reject(new Error(`could not load ${src}`));
      document.body.appendChild(el);
    });
  },

  /**
   * The visualization stack is the largest asset on the site and only Explore
   * uses it, so every other visitor paid for it. Loaded on the first visit to
   * the route, in order, once.
   */
  ensureExploreLibs() {
    if (!this._exploreLibs) {
      this._exploreLibs = this.EXPLORE_SCRIPTS.reduce(
        (chain, src) => chain.then(() => this._loadScript(src)),
        Promise.resolve()
      );
      // A failed load must not poison the route forever; retry rebuilds it.
      this._exploreLibs.catch(() => { this._exploreLibs = null; });
    }
    return this._exploreLibs;
  },

  _renderExploreLoading() {
    const el = document.getElementById('view-stats');
    if (el) {
      el.innerHTML = `<div class="loading-indicator"><div class="loading-spinner"></div>
        <p>Loading visualizations&hellip;</p></div>`;
    }
  },

  _renderExploreError() {
    const el = document.getElementById('view-stats');
    if (!el) return;
    el.innerHTML = `<div class="empty-state" role="alert">
      <p>The visualization libraries could not be loaded.</p>
      <p>Search, filters and the entry lists work without them.</p>
      <p><button class="link-btn" data-act="retry-explore">Retry</button></p>
    </div>`;
  },

  // Filter keys the results route reads from the hash. `publisher`,
  // `translator` and the two year forms exist so that a selection made in
  // Explore can be handed over as an addressable result list.
  FILTER_KEYS: ['type', 'language', 'period', 'location', 'category',
    'publisher', 'translator', 'years', 'decade'],

  FILTER_LABELS: {
    type: 'Type', language: 'Language', period: 'Period', location: 'Location',
    category: 'Category', publisher: 'Publisher', translator: 'Translator',
    years: 'Years', decade: 'Decade',
  },

  /** Inclusive [min, max] a `years` or `decade` filter value stands for. */
  yearBounds(filters) {
    if (filters.decade != null && filters.decade !== '') {
      const d = parseInt(filters.decade, 10);
      return Number.isFinite(d) ? [d, d + 9] : null;
    }
    if (!filters.years) return null;
    const [a, b] = String(filters.years).split('-');
    const lo = a ? parseInt(a, 10) : null;
    const hi = b ? parseInt(b, 10) : null;
    if (lo == null && hi == null) return null;
    return [Number.isFinite(lo) ? lo : -Infinity, Number.isFinite(hi) ? hi : Infinity];
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

  /**
   * Write the current state to the URL.
   *
   * A user-triggered state change is a place the Back button must return to,
   * so it pushes. Renders that only reproduce a state already in the URL
   * normalize it with replaceState; pushing there filled the history with
   * duplicates and made Back leave the application after one interaction.
   */
  updateURL(push) {
    const params = new URLSearchParams();
    if (this.state.browse) params.set('browse', '');
    if (this.state.query) params.set('q', this.state.query);
    for (const [k, v] of Object.entries(this.state.filters)) {
      params.set(k, v);
    }
    // Default sort stays out of the URL, so unsorted views keep clean hashes.
    if (this.state.sort && this.state.sort !== 'relevance') params.set('sort', this.state.sort);
    const hash = params.toString();
    const url = hash ? `#${hash}` : location.pathname;
    if (push && hash !== this._lastHash) history.pushState(null, '', url);
    else history.replaceState(null, '', url);
    // Keep the route guard in sync: neither call fires a hashchange, so
    // without this the next navigation back to the very hash we wrote
    // (for example '' for home) would be swallowed as "unchanged".
    this._lastHash = hash;
  },

  // --- Filtering ---
  /** True while the entry passes every filter in `f`. */
  _matchesFilters(e, f, bounds) {
    if (f.type && e.entryType !== f.type) return false;
    if (f.language && e.language !== f.language) return false;
    if (f.period && e.timePeriod !== f.period) return false;
    if (f.location && e.location !== f.location) return false;
    if (f.publisher && e.publisher !== f.publisher) return false;
    if (f.translator && !translatorKeys(e).includes(f.translator)) return false;
    if (bounds && !(e.year >= bounds[0] && e.year <= bounds[1])) return false;
    if (f.category && !(e.categories || []).includes(f.category)) return false;
    return true;
  },

  _applyFilterSet(entries, filters) {
    const bounds = this.yearBounds(filters);
    return entries.filter(e => this._matchesFilters(e, filters, bounds));
  },

  /** Entries the query alone selects; the whole corpus when there is none. */
  _queryBase() {
    const q = this.state.query;
    if (q && q.length >= this.MIN_QUERY_LENGTH) {
      this.ensureIndex();
      const indices = this.index.search(q, { limit: this.SEARCH_LIMIT });
      this._searchCapped = indices.length >= this.SEARCH_LIMIT;
      return indices.map(i => this.entries[i]);
    }
    this._searchCapped = false;
    return this.entries;
  },

  /**
   * Entry set a facet group counts against: every active filter except its
   * own. Counting against the fully filtered set instead made a facet collapse
   * to its own selection, so no second value of that facet was reachable.
   */
  facetCandidates(filterKey) {
    const others = {};
    for (const [k, v] of Object.entries(this.state.filters)) {
      if (k !== filterKey) others[k] = v;
    }
    return this._applyFilterSet(this._filterBase || this.entries, others);
  },

  applyFilters(opts) {
    this._filterBase = this._queryBase();
    this.filtered = this._applyFilterSet(this._filterBase, this.state.filters);

    this.sortEntries();
    this.state.page = 0;
    this.renderResults();
    Facets.render(this.filtered);
    this.renderChips();
    this.updateURL(opts ? opts.push : false);
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
  showView(view, opts) {
    const changed = this.state.view !== view;
    this.state.view = view;
    if (view !== 'results') this.closeMobileFacets();
    document.getElementById('view-home').classList.toggle('hidden', view !== 'home');
    document.getElementById('view-results').classList.toggle('hidden', view !== 'results');
    document.getElementById('view-stats').classList.toggle('hidden', view !== 'stats');
    document.getElementById('view-page').classList.toggle('hidden', view !== 'page');

    // Sidebar only on results view; the mobile opener follows it, because a
    // filter button on a page without a result list filters nothing.
    document.getElementById('facets').classList.toggle('hidden', view !== 'results');
    const mobileBtn = document.getElementById('mobile-filter-btn');
    if (mobileBtn) mobileBtn.classList.toggle('hidden', view !== 'results');

    // Hide header search on home (home has its own prominent search)
    document.querySelector('.header-search').classList.toggle('hidden', view === 'home');

    // Filter chips only on results view
    const chips = document.getElementById('filter-chips');
    if (view !== 'results') chips.innerHTML = '';

    // Nav active state
    const slug = location.hash.slice(1).split('/')[0];
    document.getElementById('nav-home').classList.toggle('active', view === 'home');
    document.getElementById('nav-stats').classList.toggle('active', view === 'stats');
    document.getElementById('nav-data').classList.toggle('active',
      view === 'page' && slug === 'data');
    document.getElementById('nav-about').classList.toggle('active',
      view === 'page' && slug === 'about');

    this._updateEditToggleVisibility();

    // Update search placeholder
    const input = document.getElementById('search-input');
    input.placeholder = `Search ${this.entries.length.toLocaleString('en')} entries…`;

    // Dynamic page title
    this._updateTitle(view);

    // Hash navigation replaces the page without a document load, so nothing
    // announces the new view. Only on a real view change, and never while the
    // caller is keeping the focus somewhere deliberate (typing in the search).
    if (changed && !(opts && opts.focus === false)) this._focusViewStart();
  },

  _focusViewStart() {
    const containers = { home: 'view-home', results: 'view-results',
      stats: 'view-stats', page: 'view-page' };
    const container = document.getElementById(containers[this.state.view]);
    const target = (container && container.querySelector('h1'))
      || document.getElementById('main-content');
    if (!target || typeof target.focus !== 'function') return;
    if (!target.hasAttribute('tabindex')) target.setAttribute('tabindex', '-1');
    target.focus({ preventScroll: true });
  },

  // Edit is a card-level action: only the views that actually show entry
  // cards (or lead straight to them) offer the toggle.
  EDIT_VIEWS: ['home', 'results'],

  _updateEditToggleVisibility() {
    const btn = document.getElementById('edit-toggle');
    if (!btn) return;
    const slug = location.hash.slice(1).split('/')[0];
    const usable = this.EDIT_VIEWS.includes(this.state.view)
      || (this.state.view === 'page' && slug === 'quality');
    btn.style.display = usable ? '' : 'none';
  },

  // The single place that sets document.title; Pages must not set it too,
  // or the two sources drift apart.
  _updateTitle(view) {
    const base = 'Klawiter \u2014 Stefan Zweig Bibliography';
    const titles = {
      home: base,
      stats: `Explore \u2014 ${base}`,
    };
    if (titles[view]) { document.title = titles[view]; return; }
    if (view === 'page') {
      const page = location.hash.slice(1).split('/')[0];
      const labels = { about: 'About', data: 'Data', quality: 'Data Quality' };
      document.title = labels[page] ? `${labels[page]} \u2014 ${base}` : base;
      return;
    }
    if (view === 'results') {
      const f = this.state.filters;
      // A workbench list names itself; it has no filter state to derive from.
      if (this.state.customLabel) {
        document.title = `${this.state.customLabel} — ${base}`;
        return;
      }
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

    // Show/hide batch export button, and say how much it would export
    const exportBtn = document.getElementById('batch-export-btn');
    if (exportBtn) {
      exportBtn.classList.toggle('hidden', total === 0);
      const label = document.getElementById('batch-export-label');
      if (label) label.textContent = `Export ${total.toLocaleString('en')} as BibTeX`;
    }

    const list = document.getElementById('results-list');
    if (total === 0) {
      const q = this.state.query ? ` for “${esc(this.state.query)}”` : '';
      const active = Object.keys(this.state.filters).length > 0 || !!this.state.query;
      const clear = active
        ? '<p><button class="link-btn" data-act="clear-all">Clear all filters</button></p>'
        : '';
      list.innerHTML = `<div class="empty-state">
        <p>No results${q}.</p>
        <p>Try broadening your search or removing filters.</p>
        ${clear}
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

    const title = hlEsc(e.title || 'Untitled', this.state.query);

    const parts = [];
    if (e.publisher) parts.push(esc(e.publisher));
    if (e.pageCount) parts.push(e.pageCount + ' pp.');
    const secondary = parts.length ? `<div class="card-secondary">${parts.join(' · ')}</div>` : '';

    const triage = this.state.editMode ? Edit.cardHint(e.sourcePageId) : '';

    // No source-text snippet here: it duplicated the start of the full
    // bibliographic entry shown on expansion. Title plus meta identify the card.
    return `<div class="entry-card" id="card-${e.sourcePageId}" data-pid="${e.sourcePageId}">
      <div class="card-header" tabindex="0" role="button" aria-expanded="false"
           aria-controls="card-detail-${e.sourcePageId}">
        <div class="card-meta">${badge} ${year} ${lang} ${loc} ${triage}</div>
        <div class="card-title"${titleAttrs(e, e.title)}>${title}</div>
        ${secondary}
      </div>
      <div class="card-detail hidden" id="card-detail-${e.sourcePageId}"></div>
    </div>`;
  },

  _setCardExpanded(cardEl, on) {
    cardEl.classList.toggle('card-expanded', on);
    const header = cardEl.querySelector('.card-header');
    if (header) header.setAttribute('aria-expanded', on ? 'true' : 'false');
  },

  toggleCard(pageId) {
    const detailEl = document.getElementById(`card-detail-${pageId}`);
    const cardEl = document.getElementById(`card-${pageId}`);
    if (!detailEl || !cardEl) return;

    // If already open, close it
    if (!detailEl.classList.contains('hidden')) {
      detailEl.classList.add('hidden');
      this._setCardExpanded(cardEl, false);
      return;
    }

    // Close any other open card
    document.querySelectorAll('.card-detail:not(.hidden)').forEach(el => {
      el.classList.add('hidden');
      this._setCardExpanded(el.closest('.entry-card'), false);
    });

    // Render detail content and expand
    const entry = this.entryMap.get(pageId);
    if (entry) {
      detailEl.innerHTML = Detail.renderInline(entry);
      detailEl.classList.remove('hidden');
      this._setCardExpanded(cardEl, true);
      // Scroll card into view if needed
      cardEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      // The expanded card is the first place reconciliation data shows up, so
      // this is where it is fetched rather than on every page load.
      if (Edit.reconciliation === null) {
        this._ensureReconciliation().then(() => Edit._rerender(pageId));
      }
    }
  },

  /**
   * Load the additive curation data once, sharing one promise across the
   * places that need it (an expanded card, the edit toggle). Curate.render
   * holds its own await on the same idempotent loader.
   */
  _ensureReconciliation() {
    if (!this._reconPromise) this._reconPromise = Edit.loadReconciliation();
    return this._reconPromise;
  },

  /**
   * Human-readable value of one filter. Chips and the result label resolve
   * their labels here, so a period reads as its own name in both instead of
   * as the raw key in one of them.
   */
  _filterDisplay(key, val) {
    if (key === 'type') return ENTRY_TYPE_LABELS[val] || val;
    if (key === 'period') return PERIOD_LABELS[val] || val;
    if (key === 'decade') return `${val}s`;
    if (key === 'years') return String(val).replace('-', '–');
    return String(val);
  },

  /** Active filters plus the query, in a stable order. */
  _activeFilters() {
    const active = [];
    for (const key of this.FILTER_KEYS) {
      const val = this.state.filters[key];
      if (val == null || val === '') continue;
      // A decade wins over a stale range, matching yearBounds.
      if (key === 'years' && this.state.filters.decade) continue;
      active.push({
        key,
        label: this.FILTER_LABELS[key] || key,
        display: this._filterDisplay(key, val),
      });
    }
    if (this.state.query) {
      active.push({ key: 'search', label: 'Search', display: this.state.query });
    }
    return active;
  },

  renderChips() {
    const container = document.getElementById('filter-chips');
    if (!container) return;
    const active = this._activeFilters();
    const chips = active.map(({ key, label, display }) =>
      `<span class="chip" data-filter-key="${esc(key)}">${esc(label)}: ${esc(display)}
        <button aria-label="Remove filter ${esc(label)}: ${esc(display)}">&times;</button></span>`);
    if (active.length > 1) {
      chips.push('<button class="chip-clear" data-filter-key="all">Clear all</button>');
    }
    container.innerHTML = chips.join('');
  },

  _resultsLabel(total) {
    const parts = this._activeFilters().map(({ key, display }) =>
      key === 'search' ? `\u201c${display}\u201d` : display);
    const count = `${total.toLocaleString('en')} result${total !== 1 ? 's' : ''}`;
    let label = parts.length ? `${parts.join(' \u00b7 ')} \u2014 ${count}` : count;
    // A capped search used to look like a complete count.
    if (this._searchCapped) {
      label += ` (first ${this.SEARCH_LIMIT.toLocaleString('en')} matches)`;
    }
    return label;
  },

  setFilter(key, value) {
    this.state.filters[key] = value;
    this.applyFilters({ push: true });
    this.showView('results');
  },

  removeFilter(key) {
    delete this.state.filters[key];
    if (!this.state.query && Object.keys(this.state.filters).length === 0) {
      location.hash = '';
    } else {
      this.applyFilters({ push: true });
    }
  },

  clearSearch() {
    this.state.query = '';
    const input = document.getElementById('search-input');
    if (input) input.value = '';
    if (Object.keys(this.state.filters).length === 0) {
      location.hash = '';
    } else {
      this.applyFilters({ push: true });
    }
  },

  /** Drop query and every filter at once, from the chip bar or the empty state. */
  clearAll() {
    this._resetSearchState();
    location.hash = '';
  },

  // Session-scoped result list from the data-quality workbench: shows a
  // precomputed entry set under its own label. Not hash-addressable — the
  // lists derive from artifacts, not from filter state.
  showCustomResults(entries, label) {
    this._resetSearchState();
    this.state.browse = false;
    this.state.customLabel = label;
    this.filtered = [...entries];
    this.state.page = 0;
    this.sortEntries();
    // The list carries no hash, so the way back has to be on the page.
    this._setResultsContext(this._backLinkHtml());
    this.showView('results');
    this.renderResults();
    Facets.render(this.filtered);
    this.renderChips();
    document.getElementById('results-count').textContent =
      `${label} — ${entries.length.toLocaleString('en')} entr${entries.length === 1 ? 'y' : 'ies'}`;
  },

  /** Routes a session list can be opened from, with the name of the way back. */
  RESULT_ORIGINS: { quality: 'Data Quality', stats: 'Explore' },

  _backLinkHtml() {
    const from = location.hash.slice(1);
    const name = this.RESULT_ORIGINS[from.split('/')[0]];
    if (!name) return '';
    return `<button class="link-btn results-back" data-act="back" data-hash="${esc(from)}">
      &larr; Back to ${esc(name)}</button>`;
  },

  _setResultsContext(html) {
    const el = document.getElementById('results-context');
    if (!el) return;
    el.innerHTML = html;
    el.classList.toggle('hidden', !html);
  },

  /**
   * Navigate to a hash that may already be the current one. A session list
   * leaves the hash of the view it was opened from untouched, so assigning it
   * again fires no hashchange and the guard would swallow the route.
   */
  goTo(hash) {
    if (location.hash.slice(1) === hash) {
      this._lastHash = null;
      this.handleRoute();
    } else {
      location.hash = hash;
    }
  },

  // --- Mobile filter drawer ---
  /**
   * Move the sidebar into the drawer instead of copying its markup. The copy
   * duplicated every element id, froze at the state of the moment it was
   * taken, and its facet clicks reached the original list, so the drawer never
   * reflected or closed on a selection.
   */
  openMobileFacets() {
    const overlay = document.getElementById('mobile-facets');
    const host = document.getElementById('mobile-facet-content');
    const sidebar = document.getElementById('facets');
    if (!overlay || !host || !sidebar || !overlay.classList.contains('hidden')) return;
    this._facetHome = sidebar.parentNode;
    this._facetAnchor = sidebar.nextSibling;
    host.appendChild(sidebar);
    overlay.classList.remove('hidden');
    this._mobileOpener = document.activeElement;
    const close = document.getElementById('mobile-filter-close');
    if (close) close.focus();
  },

  closeMobileFacets() {
    const overlay = document.getElementById('mobile-facets');
    if (!overlay || overlay.classList.contains('hidden')) return;
    overlay.classList.add('hidden');
    const sidebar = document.getElementById('facets');
    if (sidebar && this._facetHome) {
      this._facetHome.insertBefore(sidebar, this._facetAnchor);
    }
    this._facetHome = null;
    this._facetAnchor = null;
    if (this._mobileOpener && typeof this._mobileOpener.focus === 'function') {
      this._mobileOpener.focus();
    }
    this._mobileOpener = null;
  },

  /** Escape closes the drawer; Tab stays inside it while it is open. */
  _mobileFacetsKeydown(ev) {
    if (ev.key === 'Escape') {
      ev.preventDefault();
      this.closeMobileFacets();
      return;
    }
    if (ev.key !== 'Tab') return;
    const panel = document.querySelector('#mobile-facets .mobile-panel');
    if (!panel) return;
    const focusable = [...panel.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    )].filter(el => el.offsetParent !== null || el === document.activeElement);
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (ev.shiftKey && document.activeElement === first) {
      ev.preventDefault();
      last.focus();
    } else if (!ev.shiftKey && document.activeElement === last) {
      ev.preventDefault();
      first.focus();
    }
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

  // --- Search input ---
  /**
   * The one search behaviour. The header field and the start-page field feed
   * the same debounce, so the two places do not teach two different models of
   * when a search happens.
   */
  onSearchInput(value) {
    clearTimeout(this._searchTimer);
    this._searchTimer = setTimeout(() => this.commitSearch(value), 200);
  },

  commitSearch(value) {
    clearTimeout(this._searchTimer);
    const raw = String(value == null ? '' : value).trim();
    // A single character matches almost the whole corpus; it is not yet a query.
    this.state.query = raw.length >= this.MIN_QUERY_LENGTH ? raw : '';
    if (this.state.query || Object.keys(this.state.filters).length > 0) {
      const fromHome = this.state.view !== 'results';
      this.applyFilters({ push: true });
      // The search field keeps the focus; announcing the view would take it
      // away mid-word.
      this.showView('results', { focus: false });
      // The start-page field does not exist on the results view, so typing
      // continues in the header field, caret at the end.
      if (fromHome) this._focusHeaderSearch();
    } else {
      location.hash = '';
    }
  },

  _focusHeaderSearch() {
    const input = document.getElementById('search-input');
    if (!input) return;
    input.value = this.state.query;
    input.focus();
    try {
      input.setSelectionRange(input.value.length, input.value.length);
    } catch (e) { /* not a field that carries a selection */ }
  },

  // --- Events ---
  bindEvents() {
    document.getElementById('search-input').addEventListener('input', (ev) => {
      this.onSearchInput(ev.target.value);
    });

    document.getElementById('sort-select').addEventListener('change', (ev) => {
      this.state.sort = ev.target.value;
      this.sortEntries();
      this.renderResults();
      // Only a hash-addressable result list may write itself back to the URL;
      // the workbench lists derive from artifacts and carry no hash.
      if (this.isAddressableResults()) this.updateURL(true);
    });

    // Delegated click/keydown on results list (replaces per-card inline handlers)
    const resultsList = document.getElementById('results-list');
    resultsList.addEventListener('click', (ev) => {
      const action = ev.target.closest('[data-act]');
      if (action && action.dataset.act === 'clear-all') {
        this.clearAll();
        return;
      }
      const header = ev.target.closest('.card-header');
      if (header) {
        const card = header.closest('.entry-card');
        if (card) this.toggleCard(parseInt(card.dataset.pid));
      }
    });

    // Way back out of a session list, and the retry of the Explore libraries.
    document.addEventListener('click', (ev) => {
      const el = ev.target.closest('#results-context [data-act="back"], [data-act="retry-explore"]');
      if (!el) return;
      if (el.dataset.act === 'back') this.goTo(el.dataset.hash);
      else { this._lastHash = null; this.handleRoute(); }
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
      if (btn.dataset.filterKey === 'all') { this.clearAll(); return; }
      const chip = btn.closest('.chip');
      if (!chip) return;
      const key = chip.dataset.filterKey;
      if (key === 'search') this.clearSearch();
      else this.removeFilter(key);
    });

    // Batch export button
    document.getElementById('batch-export-btn').addEventListener('click', () => {
      const total = this.filtered.length;
      // A very large export takes a while and produces a file few people meant
      // to ask for, so it is confirmed rather than started silently.
      if (total > this.BATCH_CONFIRM_ABOVE && typeof confirm === 'function'
          && !confirm(`Export ${total.toLocaleString('en')} entries as BibTeX?`)) {
        return;
      }
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

    // Mobile filter
    document.getElementById('mobile-filter-btn')
      .addEventListener('click', () => this.openMobileFacets());
    document.getElementById('mobile-filter-close')
      .addEventListener('click', () => this.closeMobileFacets());
    const overlay = document.getElementById('mobile-facets');
    overlay.addEventListener('click', (ev) => {
      if (ev.target === overlay) this.closeMobileFacets();
    });
    overlay.addEventListener('keydown', (ev) => this._mobileFacetsKeydown(ev));

    // Edit-mode keyboard navigation on the results list (j = next, k = previous).
    document.addEventListener('keydown', (ev) => {
      // A browser or OS shortcut is not a card command.
      if (ev.ctrlKey || ev.metaKey || ev.altKey) return;
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
      toggle.addEventListener('click', () => this.toggleEditMode());
      header.appendChild(toggle);
      this._updateEditToggleVisibility();
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
      const note = document.getElementById('edit-pending-note');
      if (note) note.remove();   // the counter is actionable again
      // Triage hints need the artifact; refresh once it is in (cards render
      // their hint chips only from a full pass, so redraw the results list).
      Promise.all([Edit.loadTriage(), this._ensureReconciliation()])
        .then(() => this._refreshAfterEditToggle());
    } else {
      this._refreshAfterEditToggle();
    }
  },

  // The "needs review" sort exists only while edit mode is on.
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
        if (this.isAddressableResults()) this.updateURL(false);
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

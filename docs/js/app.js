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
      this.data = await resp.json();
      // Filter to namespace 0 only
      this.entries = this.data.entries.filter(e => e.pageNamespace === 0);
      this.entryMap = new Map(this.entries.map(e => [e.sourcePageId, e]));
      this.titleMap = new Map(this.entries.filter(e => e.title).map(e => [e.title, e.sourcePageId]));
      this.logDataSummary();
      this.buildIndex();
      this.bindEvents();
      this.handleRoute();
      window.addEventListener('hashchange', () => this.handleRoute());
    } catch (err) {
      document.getElementById('view-home').innerHTML =
        `<p style="color:#7A1B2D">Error loading data: ${err.message}</p>`;
    }
  },

  logDataSummary() {
    if (!this.state.isLocal) return;
    const e = this.entries;
    const all = this.data.entries;

    // Counts by type
    const types = {};
    e.forEach(x => { types[x.entryType] = (types[x.entryType] || 0) + 1; });

    // Field coverage
    const fields = ['title', 'year', 'publisher', 'location', 'language', 'translator', 'pageCount'];
    const coverage = {};
    fields.forEach(f => {
      const count = e.filter(x => x[f] != null && x[f] !== '').length;
      coverage[f] = `${count}/${e.length} (${(100 * count / e.length).toFixed(1)}%)`;
    });

    // Array fields
    const arrayFields = ['reprints', 'translations', 'contentItems', 'seeAlso', 'categories'];
    const arrayCoverage = {};
    arrayFields.forEach(f => {
      const count = e.filter(x => x[f] && x[f].length > 0).length;
      arrayCoverage[f] = `${count}/${e.length} (${(100 * count / e.length).toFixed(1)}%)`;
    });

    // Languages + locations
    const langs = new Set(e.map(x => x.language).filter(Boolean));
    const locs = new Set(e.map(x => x.location).filter(Boolean));
    const years = e.map(x => x.year).filter(Boolean);

    // Data quality
    const wikiMarkupTitles = e.filter(x => x.title && (/'''/.test(x.title) || /\[\[|\]\]/.test(x.title)));
    const noTitle = e.filter(x => !x.title);
    const noYear = e.filter(x => !x.year);

    console.group('%c📚 Klawiter Bibliography — Data Summary', 'font-weight:bold; font-size:14px');
    console.log(`Total entries in JSON: ${all.length}`);
    console.log(`Namespace 0 (displayed): ${e.length}`);
    console.log(`Excluded (ns≠0): ${all.length - e.length}`);
    console.log(`Redirects: ${Object.keys(this.data.redirects).length}`);
    console.log('');
    console.log('%cEntry Types:', 'font-weight:bold');
    console.table(types);
    console.log('%cField Coverage:', 'font-weight:bold');
    console.table(coverage);
    console.log('%cArray Field Coverage:', 'font-weight:bold');
    console.table(arrayCoverage);
    console.log('%cOverview:', 'font-weight:bold');
    console.log(`Languages: ${langs.size} | Locations: ${locs.size} | Year range: ${Math.min(...years)}–${Math.max(...years)}`);
    console.log('%cData Quality:', 'font-weight:bold');
    console.log(`Titles with wiki markup: ${wikiMarkupTitles.length}`);
    if (wikiMarkupTitles.length) console.log('  Examples:', wikiMarkupTitles.slice(0, 5).map(x => x.title));
    console.log(`Entries without title: ${noTitle.length}`);
    console.log(`Entries without year: ${noYear.length}`);
    console.groupEnd();
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
    const params = new URLSearchParams(hash);

    // Static content pages
    const staticPages = ['about', 'methodology', 'help', 'data', 'imprint'];
    if (staticPages.includes(hash)) {
      this.showView('page');
      Pages.render(hash);
      return;
    }

    // Browse view — show all entries, no filters
    if (hash === 'browse') {
      this.state.query = '';
      this.state.filters = {};
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

    // Stats view — always shows full dataset, clears filters
    if (hash === 'stats') {
      this.state.query = '';
      this.state.filters = {};
      document.getElementById('search-input').value = '';
      this.showView('stats');
      Explore.render(this.entries);
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
        this.showDetail(pid);
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

    document.getElementById('search-input').value = this.state.query;

    if (this.state.query || Object.keys(this.state.filters).length > 0) {
      this.applyFilters();
      this.showView('results');
    } else {
      this.showView('home');
      Home.render(this.entries);
    }
  },

  updateURL() {
    const params = new URLSearchParams();
    if (this.state.query) params.set('q', this.state.query);
    for (const [k, v] of Object.entries(this.state.filters)) {
      params.set(k, v);
    }
    const hash = params.toString();
    history.replaceState(null, '', hash ? `#${hash}` : location.pathname);
  },

  // --- Filtering ---
  applyFilters() {
    let indices;
    if (this.state.query) {
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
    const s = this.state.sort;
    if (s === 'year-asc') {
      this.filtered.sort((a, b) => (a.year || 9999) - (b.year || 9999));
    } else if (s === 'year-desc') {
      this.filtered.sort((a, b) => (b.year || -1) - (a.year || -1));
    } else if (s === 'title') {
      this.filtered.sort((a, b) => (a.title || '').localeCompare(b.title || ''));
    }
  },

  // --- Views ---
  showView(view) {
    this.state.view = view;
    document.getElementById('view-home').classList.toggle('hidden', view !== 'home');
    document.getElementById('view-results').classList.toggle('hidden', view !== 'results');
    document.getElementById('view-detail').classList.toggle('hidden', view !== 'detail');
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
      const labels = { about: 'About', methodology: 'Methodology', help: 'Help', data: 'Data Access', imprint: 'Imprint' };
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

  showDetail(pageId) {
    const entry = this.entryMap.get(pageId);
    this.state.view = 'detail';
    this.state.entryId = pageId;
    this.showView('detail');
    Detail.render(entry);
    window.scrollTo(0, 0);
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

    const snippet = esc((e.fullBibliographicEntry || '').slice(0, 180));

    return `<div class="entry-card" id="card-${e.sourcePageId}">
      <div class="card-header" tabindex="0" role="button"
           onclick="App.toggleCard(${e.sourcePageId})"
           onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();App.toggleCard(${e.sourcePageId})}">
        <div class="card-meta">${badge} ${year} ${lang} ${loc}</div>
        <div class="card-title">${title}</div>
        ${secondary}
        <div class="card-snippet">${snippet}</div>
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
      chips.push(`<span class="chip">${esc(label)}: ${esc(display)}
        <button onclick="App.removeFilter('${key}')">&times;</button></span>`);
    }
    if (this.state.query) {
      chips.push(`<span class="chip">Search: ${esc(this.state.query)}
        <button onclick="App.clearSearch()">&times;</button></span>`);
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

    document.getElementById('back-btn').addEventListener('click', () => {
      history.back();
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

    // Edit mode toggle (localhost only)
    if (this.state.isLocal) {
      const header = document.querySelector('.header-inner');
      const toggle = document.createElement('button');
      toggle.id = 'edit-toggle';
      toggle.className = 'edit-toggle-btn';
      toggle.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 3a2.83 2.83 0 114 4L7.5 20.5 2 22l1.5-5.5L17 3z"/></svg> Edit';
      toggle.onclick = () => this.toggleEditMode();
      header.appendChild(toggle);
    }
  },

  toggleEditMode() {
    this.state.editMode = !this.state.editMode;
    document.body.classList.toggle('edit-mode', this.state.editMode);
    const btn = document.getElementById('edit-toggle');
    if (btn) {
      btn.classList.toggle('active', this.state.editMode);
      btn.innerHTML = this.state.editMode
        ? '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 3a2.83 2.83 0 114 4L7.5 20.5 2 22l1.5-5.5L17 3z"/></svg> Editing'
        : '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 3a2.83 2.83 0 114 4L7.5 20.5 2 22l1.5-5.5L17 3z"/></svg> Edit';
    }
    // Re-render current detail if open
    const expandedCard = document.querySelector('.entry-card.card-expanded');
    if (expandedCard) {
      const pid = parseInt(expandedCard.id.replace('card-', ''));
      const detail = expandedCard.querySelector('.card-detail');
      const entry = this.entryMap.get(pid);
      if (detail && entry) {
        detail.innerHTML = Detail.renderInline(entry);
      }
    }
  },
};

// Boot (constants, utils, export loaded via separate script tags)
document.addEventListener('DOMContentLoaded', () => App.init());

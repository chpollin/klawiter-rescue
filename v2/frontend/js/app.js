/**
 * Klawiter Bibliography — Main Application
 * State management, data loading, routing.
 */
const App = {
  data: null,        // { entries: [], redirects: {} }
  index: null,       // FlexSearch index
  filtered: [],      // Current filtered entries
  state: {
    query: '',
    filters: {},     // { type: 'fiction', language: 'German', ... }
    sort: 'relevance',
    view: 'dashboard', // 'dashboard' | 'results' | 'detail'
    entryId: null,
    page: 0,
    pageSize: 50,
  },

  async init() {
    this.showLoading(true);
    try {
      const resp = await fetch('data/klawiter.json');
      this.data = await resp.json();
      this.buildIndex();
      this.bindEvents();
      this.handleRoute();
      window.addEventListener('hashchange', () => this.handleRoute());
    } catch (err) {
      document.getElementById('dashboard').innerHTML =
        `<p class="text-red-600">Fehler beim Laden: ${err.message}</p>`;
    }
    this.showLoading(false);
  },

  buildIndex() {
    this.index = new FlexSearch.Index({
      tokenize: 'forward',
      resolution: 9,
    });
    this.data.entries.forEach((e, i) => {
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

    if (params.has('entry')) {
      const pid = parseInt(params.get('entry'));
      this.showDetail(pid);
      return;
    }

    // Redirect resolution: #title=Some+Page+Title
    if (params.has('title')) {
      const title = params.get('title');
      const targetPid = this.data.redirects[title];
      if (targetPid) {
        location.hash = `entry=${targetPid}`;
        return;
      }
    }

    // Parse filters from URL
    this.state.query = params.get('q') || '';
    this.state.filters = {};
    for (const [key, val] of params) {
      if (['type', 'language', 'period', 'location'].includes(key)) {
        this.state.filters[key] = val;
      }
    }

    document.getElementById('search-input').value = this.state.query;

    if (this.state.query || Object.keys(this.state.filters).length > 0) {
      this.applyFilters();
      this.showView('results');
    } else {
      this.showView('dashboard');
      Charts.render(this.data.entries);
      Facets.render(this.data.entries);
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

    // Text search
    if (this.state.query) {
      indices = this.index.search(this.state.query, { limit: 5000 });
    } else {
      indices = this.data.entries.map((_, i) => i);
    }

    // Facet filters
    this.filtered = indices
      .map(i => this.data.entries[i])
      .filter(e => {
        const f = this.state.filters;
        if (f.type && e.entryType !== f.type) return false;
        if (f.language && e.language !== f.language) return false;
        if (f.period && e.timePeriod !== f.period) return false;
        if (f.location && e.location !== f.location) return false;
        return true;
      });

    // Sort
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
      this.filtered.sort((a, b) => (b.year || 0) - (a.year || 0));
    } else if (s === 'title') {
      this.filtered.sort((a, b) => (a.title || '').localeCompare(b.title || ''));
    }
    // 'relevance' = search order, no re-sort needed
  },

  // --- Views ---
  showView(view) {
    this.state.view = view;
    document.getElementById('dashboard').classList.toggle('hidden', view !== 'dashboard');
    document.getElementById('results').classList.toggle('hidden', view !== 'results');
    document.getElementById('detail').classList.toggle('hidden', view !== 'detail');
  },

  showDetail(pageId) {
    const entry = this.data.entries.find(e => e.sourcePageId === pageId);
    if (!entry) {
      // Try redirect
      const targetPid = Object.values(this.data.redirects).find(p => p === pageId);
      if (!targetPid) {
        document.getElementById('detail-content').innerHTML =
          '<p class="text-gray-500">Eintrag nicht gefunden.</p>';
      }
    }
    this.state.view = 'detail';
    this.state.entryId = pageId;
    this.showView('detail');
    Detail.render(entry);
  },

  // --- Results ---
  renderResults() {
    const total = this.filtered.length;
    const start = 0;
    const end = Math.min((this.state.page + 1) * this.state.pageSize, total);
    const visible = this.filtered.slice(start, end);

    document.getElementById('results-count').textContent =
      `${total.toLocaleString('de-DE')} Ergebnis${total !== 1 ? 'se' : ''}`;

    const list = document.getElementById('results-list');
    list.innerHTML = visible.map(e => this.renderCard(e)).join('');

    const loadMore = document.getElementById('load-more');
    loadMore.classList.toggle('hidden', end >= total);
  },

  renderCard(e) {
    const badge = `<span class="badge badge-${e.entryType}">${e.entryType}</span>`;
    const year = e.year ? `<span class="text-gray-500">${e.year}</span>` : '';
    const lang = e.language ? `<span class="text-gray-400 text-xs">${e.language}</span>` : '';
    const loc = e.location ? `<span class="text-gray-400 text-xs">${esc(e.location)}</span>` : '';
    const title = hl(esc(e.title || 'Ohne Titel'), this.state.query);
    const snippet = esc((e.fullBibliographicEntry || '').slice(0, 200));

    return `<div class="entry-card" onclick="location.hash='entry=${e.sourcePageId}'">
      <div class="flex items-start gap-3">
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2 flex-wrap">
            ${badge} ${year} ${lang} ${loc}
          </div>
          <h3 class="font-medium mt-1 leading-snug">${title}</h3>
          <p class="text-sm text-gray-500 mt-1 line-clamp-2">${snippet}</p>
        </div>
      </div>
    </div>`;
  },

  renderChips() {
    const container = document.getElementById('filter-chips');
    const chips = [];
    for (const [key, val] of Object.entries(this.state.filters)) {
      chips.push(`<span class="chip">${key}: ${esc(val)}
        <button onclick="App.removeFilter('${key}')">&times;</button></span>`);
    }
    if (this.state.query) {
      chips.push(`<span class="chip">Suche: ${esc(this.state.query)}
        <button onclick="App.clearSearch()">&times;</button></span>`);
    }
    container.innerHTML = chips.join('');
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

  showLoading(show) {
    const inp = document.getElementById('search-input');
    inp.placeholder = show ? 'Lade Bibliographie...' : `Suche in ${this.data?.totalEntries?.toLocaleString('de-DE') || ''} Einträgen...`;
  },

  bindEvents() {
    // Search
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

    // Sort
    document.getElementById('sort-select').addEventListener('change', (ev) => {
      this.state.sort = ev.target.value;
      this.sortEntries();
      this.renderResults();
    });

    // Load more
    document.getElementById('load-more-btn').addEventListener('click', () => {
      this.state.page++;
      // Append instead of replace
      const start = this.state.page * this.state.pageSize;
      const end = Math.min(start + this.state.pageSize, this.filtered.length);
      const visible = this.filtered.slice(start, end);
      const list = document.getElementById('results-list');
      list.insertAdjacentHTML('beforeend', visible.map(e => this.renderCard(e)).join(''));
      document.getElementById('load-more').classList.toggle('hidden', end >= this.filtered.length);
    });

    // Home link
    document.getElementById('home-link').addEventListener('click', (ev) => {
      ev.preventDefault();
      location.hash = '';
    });

    // Back button
    document.getElementById('back-btn').addEventListener('click', () => {
      history.back();
    });

    // Export
    document.getElementById('export-btn').addEventListener('click', () => {
      const blob = new Blob([JSON.stringify(this.data, null, 2)], { type: 'application/ld+json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'klawiter-bibliography.jsonld';
      a.click();
      URL.revokeObjectURL(url);
    });

    // Mobile filter toggle
    document.getElementById('mobile-filter-btn').addEventListener('click', () => {
      document.getElementById('mobile-facets').classList.remove('hidden');
      document.getElementById('mobile-facet-content').innerHTML =
        document.getElementById('facets').innerHTML;
    });
    document.getElementById('mobile-filter-close').addEventListener('click', () => {
      document.getElementById('mobile-facets').classList.add('hidden');
    });
  },
};

// --- Helpers ---
function esc(s) {
  if (!s) return '';
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function hl(text, query) {
  if (!query || !text) return text;
  const words = query.split(/\s+/).filter(w => w.length > 1);
  if (!words.length) return text;
  const re = new RegExp(`(${words.map(w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`, 'gi');
  return text.replace(re, '<mark>$1</mark>');
}

// Boot
document.addEventListener('DOMContentLoaded', () => App.init());

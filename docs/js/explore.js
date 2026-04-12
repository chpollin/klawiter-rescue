/**
 * Explore — Shared controller for the interactive exploration interface.
 * Manages mode switching, shared state, data preprocessing, and the detail panel.
 */
const Explore = {
  entries: [],
  mode: 'timeline',
  selection: [],        // array of sourcePageId currently selected
  filters: {
    languages: [],
    types: [],
    yearRange: [null, null],
    decade: null,
    location: null,
    publisher: null,
    period: null,
  },

  // Precomputed indices
  byYear: new Map(),
  byLanguage: new Map(),
  byType: new Map(),
  byPublisher: new Map(),
  topLanguages: [],
  yearExtent: [1815, 2020],

  // Color palette — base values from shared COLORS constant, language palette local
  colors: {
    languages: {
      'German': COLORS.burgundy, 'Chinese': COLORS.gold, 'French': '#6B7A3A',
      'English': '#5B5040', 'Spanish': '#8B5C3A', 'Arabic': '#5B3A7A',
      'Bulgarian': '#3A5B6B', 'Albanian': '#7A4A1B', 'Russian': '#3A3A5B',
      'Croatian': '#6B3A4A', 'Other': '#9E9585',
    },
    types: {
      'fiction': '#631a34', 'essay': '#8B5C3A', 'poetry': '#6B7A3A',
      'drama': '#7A4A1B', 'correspondence': '#3A3A5B', 'film': '#5B5040',
      'historical-study': '#5B3A7A', 'secondary-literature': '#3A5B6B',
      'collected-works': '#C2A360', 'foreword': '#7A2D45', 'translation': '#6B3A4A',
      'symposium': '#4A6B3A', 'dramatic-reading': '#5B6B3A',
      'newspaper': '#6B5B3A', 'other': '#9E9585',
    },
    provenance: { regex: '#6B7A3A', llm: '#C2A360', missing: '#7A2D45' },
    burgundy: COLORS.burgundy,
    gold: COLORS.gold,
    cream: COLORS.cream,
    gridLine: COLORS.gridLine,
    textLight: COLORS.textLight,
  },

  // -------------------------------------------------------------------------
  // Init & Preprocessing
  // -------------------------------------------------------------------------

  render(entries) {
    this.entries = entries;
    this._preprocess();
    this._renderScaffolding();
    this._bindModeTabs();
    this.setMode('timeline');
  },

  _preprocess() {
    const e = this.entries;

    // Year extent
    const years = e.map(x => x.year).filter(Boolean);
    this.yearExtent = [Math.min(...years), Math.max(...years)];

    // Index by year
    this.byYear = new Map();
    for (const entry of e) {
      if (!entry.year) continue;
      if (!this.byYear.has(entry.year)) this.byYear.set(entry.year, []);
      this.byYear.get(entry.year).push(entry);
    }

    // Index by language
    this.byLanguage = new Map();
    for (const entry of e) {
      const lang = entry.language || 'Unknown';
      if (!this.byLanguage.has(lang)) this.byLanguage.set(lang, []);
      this.byLanguage.get(lang).push(entry);
    }

    // Top 10 languages (exclude Unknown — those go into "Other")
    const langCounts = [...this.byLanguage.entries()]
      .filter(([lang]) => lang !== 'Unknown')
      .map(([lang, arr]) => ({ lang, count: arr.length }))
      .sort((a, b) => b.count - a.count);
    this.topLanguages = langCounts.slice(0, 10).map(x => x.lang);

    // Index by type
    this.byType = new Map();
    for (const entry of e) {
      const t = entry.entryType || 'other';
      if (!this.byType.has(t)) this.byType.set(t, []);
      this.byType.get(t).push(entry);
    }

    // Index by publisher
    this.byPublisher = new Map();
    for (const entry of e) {
      if (!entry.publisher) continue;
      if (!this.byPublisher.has(entry.publisher)) this.byPublisher.set(entry.publisher, []);
      this.byPublisher.get(entry.publisher).push(entry);
    }
  },

  // -------------------------------------------------------------------------
  // Scaffolding
  // -------------------------------------------------------------------------

  _renderScaffolding() {
    const container = document.getElementById('view-stats');
    const e = this.entries;
    const languages = new Set(e.map(x => x.language).filter(Boolean));

    container.innerHTML = `
      <div class="explore-header">
        <h2 class="section-heading">Explore the Bibliography</h2>
        <div class="explore-header-meta">
          ${e.length.toLocaleString('en')} entries &middot; ${languages.size} languages &middot;
          ${this.byType.size} types &middot; ${this.yearExtent[0]}&ndash;${this.yearExtent[1]}
        </div>
        <div class="explore-mode-tabs" role="tablist">
          <button role="tab" class="mode-tab active" data-mode="timeline">Timeline</button>
          <button role="tab" class="mode-tab" data-mode="geography">Geography</button>
          <button role="tab" class="mode-tab" data-mode="network">Connections</button>
        </div>
      </div>

      <div id="explore-filter-chips" class="explore-filter-chips"></div>

      <div class="explore-body explore-body-full">
        <div class="explore-viz explore-viz-full" id="explore-viz">
          <div id="viz-timeline" class="explore-panel"></div>
          <div id="viz-geography" class="explore-panel hidden"></div>
          <div id="viz-network" class="explore-panel hidden"></div>
        </div>
        <aside class="explore-detail hidden" id="explore-detail">
          <div class="explore-detail-summary" id="explore-detail-content"></div>
        </aside>
      </div>

      <div class="stats-export">
        <button class="action-btn" onclick="Export.fullDataset()">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          Download full dataset (JSON-LD)
        </button>
      </div>
    `;

    // Shared tooltip
    if (!document.getElementById('explore-tooltip')) {
      const tip = document.createElement('div');
      tip.id = 'explore-tooltip';
      tip.className = 'explore-tooltip';
      document.body.appendChild(tip);
    }
  },

  _bindModeTabs() {
    document.querySelectorAll('.mode-tab').forEach(tab => {
      tab.addEventListener('click', () => this.setMode(tab.dataset.mode));
    });
  },

  // -------------------------------------------------------------------------
  // Mode switching
  // -------------------------------------------------------------------------

  setMode(mode) {
    this.mode = mode;

    // Update tab active state
    document.querySelectorAll('.mode-tab').forEach(tab => {
      tab.classList.toggle('active', tab.dataset.mode === mode);
      tab.setAttribute('aria-selected', tab.dataset.mode === mode);
    });

    // Show/hide panels
    document.querySelectorAll('.explore-panel').forEach(p => p.classList.add('hidden'));
    const panel = document.getElementById(`viz-${mode}`);
    if (panel) panel.classList.remove('hidden');

    // Reset selection (visual highlight is mode-specific) but preserve filters
    this.selection = [];
    this._renderFilterChips();
    const data = this.hasActiveFilters() ? this.getFiltered() : this.entries;
    this.updateSelection([]);

    // Render the active mode with current filtered data
    if (mode === 'timeline' && typeof ExploreTimeline !== 'undefined') {
      ExploreTimeline.render(data);
    } else if (mode === 'geography' && typeof ExploreGeography !== 'undefined') {
      ExploreGeography.render(data);
    } else if (mode === 'network' && typeof ExploreNetwork !== 'undefined') {
      ExploreNetwork.render(data);
    }
  },

  // -------------------------------------------------------------------------
  // Shared filtering
  // -------------------------------------------------------------------------

  hasActiveFilters() {
    const f = this.filters;
    return f.languages.length > 0 || f.types.length > 0 ||
      f.yearRange[0] != null || f.yearRange[1] != null ||
      f.decade != null || f.location != null || f.publisher != null || f.period != null;
  },

  getFiltered() {
    let filtered = this.entries;
    const f = this.filters;
    if (f.languages.length) filtered = filtered.filter(e => f.languages.includes(e.language));
    if (f.types.length) filtered = filtered.filter(e => f.types.includes(e.entryType));
    if (f.yearRange[0] != null) filtered = filtered.filter(e => e.year >= f.yearRange[0]);
    if (f.yearRange[1] != null) filtered = filtered.filter(e => e.year <= f.yearRange[1]);
    if (f.decade != null) {
      const d0 = f.decade, d1 = d0 + 9;
      filtered = filtered.filter(e => e.year >= d0 && e.year <= d1);
    }
    if (f.location) filtered = filtered.filter(e => e.location === f.location);
    if (f.publisher) filtered = filtered.filter(e => e.publisher === f.publisher);
    if (f.period) filtered = filtered.filter(e => e.timePeriod === f.period);
    return filtered;
  },

  toggleFilter(key, value) {
    const f = this.filters;
    if (key === 'languages' || key === 'types') {
      const idx = f[key].indexOf(value);
      if (idx >= 0) f[key].splice(idx, 1);
      else f[key].push(value);
    } else {
      f[key] = f[key] === value ? null : value;
    }
    this._onFilterChange();
  },

  clearFilter(key) {
    const f = this.filters;
    if (key === 'languages' || key === 'types') f[key] = [];
    else if (key === 'yearRange') f[key] = [null, null];
    else f[key] = null;
    this._onFilterChange();
  },

  clearAllFilters() {
    this.filters = {
      languages: [], types: [], yearRange: [null, null],
      decade: null, location: null, publisher: null, period: null,
    };
    this._onFilterChange();
  },

  _onFilterChange() {
    this._renderFilterChips();
    const data = this.hasActiveFilters() ? this.getFiltered() : this.entries;
    if (this.mode === 'timeline' && typeof ExploreTimeline !== 'undefined') {
      ExploreTimeline.render(data);
    } else if (this.mode === 'geography' && typeof ExploreGeography !== 'undefined') {
      ExploreGeography.render(data);
    } else if (this.mode === 'network' && typeof ExploreNetwork !== 'undefined') {
      ExploreNetwork.render(data);
    }
    this.updateSelection(data.length < this.entries.length ? data : []);
    document.dispatchEvent(new CustomEvent('explore:filterChange', {
      detail: { filters: { ...this.filters }, filtered: data.length },
    }));
  },

  _renderFilterChips() {
    const el = document.getElementById('explore-filter-chips');
    if (!el) return;
    const f = this.filters;
    const chips = [];

    for (const lang of f.languages) {
      chips.push(`<span class="chip">Language: ${esc(lang)} <button onclick="Explore.toggleFilter('languages','${lang.replace(/'/g, "\\'")}')">&times;</button></span>`);
    }
    for (const type of f.types) {
      chips.push(`<span class="chip">Type: ${esc(ENTRY_TYPE_LABELS[type] || type)} <button onclick="Explore.toggleFilter('types','${type}')">&times;</button></span>`);
    }
    if (f.yearRange[0] != null || f.yearRange[1] != null) {
      const label = `${f.yearRange[0] || '?'}\u2013${f.yearRange[1] || '?'}`;
      chips.push(`<span class="chip">Years: ${label} <button onclick="Explore.clearFilter('yearRange')">&times;</button></span>`);
    }
    if (f.decade != null) {
      chips.push(`<span class="chip">Decade: ${f.decade}s <button onclick="Explore.clearFilter('decade')">&times;</button></span>`);
    }
    if (f.location) {
      chips.push(`<span class="chip">Location: ${esc(f.location)} <button onclick="Explore.clearFilter('location')">&times;</button></span>`);
    }
    if (f.publisher) {
      chips.push(`<span class="chip">Publisher: ${esc(f.publisher)} <button onclick="Explore.clearFilter('publisher')">&times;</button></span>`);
    }
    if (f.period) {
      chips.push(`<span class="chip">Period: ${esc(PERIOD_LABELS[f.period] || f.period)} <button onclick="Explore.clearFilter('period')">&times;</button></span>`);
    }

    if (chips.length) {
      chips.push(`<button class="chip-clear" onclick="Explore.clearAllFilters()">Clear all</button>`);
    }
    el.innerHTML = chips.join(' ');
  },

  updateSelection(entries) {
    this.selection = entries.map(e => e.sourcePageId);
    const panel = document.getElementById('explore-detail');
    const detail = document.getElementById('explore-detail-content');
    if (!panel || !detail) return;

    if (entries.length === 0) {
      // No selection — hide detail panel, chart goes full width
      panel.classList.add('hidden');
      detail.innerHTML = '';
    } else {
      // Show detail panel alongside chart
      panel.classList.remove('hidden');
      if (entries.length === 1) {
        detail.innerHTML = Detail.renderInline(entries[0]);
      } else {
        detail.innerHTML = this._renderDetailGroup(entries);
      }
    }
  },

  navigateToResults(filters) {
    const params = new URLSearchParams();
    for (const [k, v] of Object.entries(filters)) {
      if (v) params.set(k, v);
    }
    location.hash = params.toString();
  },

  // -------------------------------------------------------------------------
  // Tooltip
  // -------------------------------------------------------------------------

  showTooltip(html, event) {
    const tip = document.getElementById('explore-tooltip');
    if (!tip) return;
    tip.innerHTML = html;
    tip.style.display = 'block';

    const rect = tip.getBoundingClientRect();
    const x = Math.min(event.pageX + 12, window.innerWidth - rect.width - 20);
    const y = event.pageY - rect.height - 8;
    tip.style.left = x + 'px';
    tip.style.top = (y > 0 ? y : event.pageY + 12) + 'px';
  },

  hideTooltip() {
    const tip = document.getElementById('explore-tooltip');
    if (tip) tip.style.display = 'none';
  },

  // -------------------------------------------------------------------------
  // Detail panel renderers
  // -------------------------------------------------------------------------

  _renderDetailSummary(entries) {
    const langs = new Set(entries.map(e => e.language).filter(Boolean));
    const types = new Set(entries.map(e => e.entryType).filter(Boolean));
    const withSeeAlso = entries.filter(e => e.seeAlso && e.seeAlso.length).length;
    const withTranslations = entries.filter(e => e.translations && e.translations.length).length;

    return `
      <div class="detail-summary">
        <h3 class="detail-summary-title">Collection Overview</h3>
        <p class="detail-summary-text">
          ${entries.length.toLocaleString('en')} entries in ${langs.size} languages
          across ${types.size} types.
        </p>
        <p class="detail-summary-hint">
          Click or brush elements in the visualization to explore entries.
        </p>
        <div class="detail-summary-stats">
          <div><strong>${withSeeAlso}</strong> entries with cross-references</div>
          <div><strong>${withTranslations}</strong> entries with translations</div>
        </div>
      </div>
    `;
  },

  _renderDetailGroup(entries) {
    // Top languages in selection
    const langCounts = countByField(entries, 'language');
    const topLangs = Object.entries(langCounts).sort((a, b) => b[1] - a[1]).slice(0, 5);

    // Top types in selection
    const typeCounts = countByField(entries, 'entryType');
    const topTypes = Object.entries(typeCounts).sort((a, b) => b[1] - a[1]).slice(0, 5);

    // Year range
    const years = entries.map(e => e.year).filter(Boolean);
    const minY = years.length ? Math.min(...years) : '?';
    const maxY = years.length ? Math.max(...years) : '?';

    // Entry list (max 20)
    const shown = entries.slice(0, 20);
    const listHtml = shown.map(e =>
      `<li class="detail-entry-item">
        <a href="#entry=${e.sourcePageId}" class="detail-entry-link">
          <span class="badge badge-${e.entryType}">${ENTRY_TYPE_LABELS[e.entryType] || e.entryType}</span>
          ${esc(e.title || 'Untitled')}
          ${e.year ? `<span class="detail-entry-year">${e.year}</span>` : ''}
        </a>
      </li>`
    ).join('');

    const moreHtml = entries.length > 20
      ? `<p class="detail-more">and ${(entries.length - 20).toLocaleString('en')} more</p>`
      : '';

    return `
      <div class="detail-group">
        <h3 class="detail-group-title">${entries.length.toLocaleString('en')} entries selected</h3>
        <div class="detail-group-meta">
          <span>${minY}&ndash;${maxY}</span>
        </div>

        <div class="detail-group-section">
          <h4>Languages</h4>
          <div class="detail-mini-bars">
            ${topLangs.map(([lang, count]) =>
              `<div class="mini-bar-row">
                <span class="mini-bar-label">${esc(lang)}</span>
                <span class="mini-bar-count">${count}</span>
              </div>`
            ).join('')}
          </div>
        </div>

        <div class="detail-group-section">
          <h4>Types</h4>
          <div class="detail-mini-bars">
            ${topTypes.map(([type, count]) =>
              `<div class="mini-bar-row">
                <span class="mini-bar-label">${ENTRY_TYPE_LABELS[type] || type}</span>
                <span class="mini-bar-count">${count}</span>
              </div>`
            ).join('')}
          </div>
        </div>

        <div class="detail-group-section">
          <h4>Entries</h4>
          <ul class="detail-entry-list">${listHtml}</ul>
          ${moreHtml}
        </div>

        <button class="action-btn explore-view-btn" onclick="Explore._navigateFromFilters()">
          View all ${entries.length.toLocaleString('en')} entries
        </button>
      </div>
    `;
  },

  _navigateFromFilters() {
    const f = this.filters;
    const params = {};
    if (f.languages.length) params.language = f.languages[0];
    if (f.types.length) params.type = f.types[0];
    if (f.location) params.location = f.location;
    if (f.publisher) params.publisher = f.publisher;
    if (f.period) params.period = f.period;
    this.navigateToResults(params);
  },
};

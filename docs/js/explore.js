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
  },

  // Precomputed indices
  byYear: new Map(),
  byLanguage: new Map(),
  byType: new Map(),
  topLanguages: [],
  yearExtent: [1815, 2020],

  // Color palette (SZD design system extended)
  colors: {
    languages: {
      'German': '#7A1B2D', 'Chinese': '#B8963E', 'French': '#6B7A3A',
      'English': '#5B5040', 'Spanish': '#8B5C3A', 'Arabic': '#5B3A7A',
      'Bulgarian': '#3A5B6B', 'Albanian': '#7A4A1B', 'Russian': '#3A3A5B',
      'Croatian': '#6B3A4A', 'Other': '#9E9585',
    },
    burgundy: '#7A1B2D',
    gold: '#B8963E',
    cream: '#FAF8F3',
    gridLine: '#EDE8DF',
    textLight: '#8A7E6B',
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

    // Top 10 languages
    const langCounts = [...this.byLanguage.entries()]
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
        <div class="explore-mode-tabs" role="tablist">
          <button role="tab" class="mode-tab active" data-mode="timeline">Timeline</button>
          <button role="tab" class="mode-tab" data-mode="overview">Overview</button>
          <button role="tab" class="mode-tab" data-mode="network">Connections</button>
        </div>
      </div>

      <div class="stats-cards">
        <div class="stat-card">
          <div class="stat-value">${e.length.toLocaleString('en')}</div>
          <div class="stat-label">Entries</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${this.byType.size}</div>
          <div class="stat-label">Types</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${languages.size}</div>
          <div class="stat-label">Languages</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${this.yearExtent[0]}&ndash;${this.yearExtent[1]}</div>
          <div class="stat-label">Time Span</div>
        </div>
      </div>

      <div class="explore-body">
        <div class="explore-viz" id="explore-viz">
          <div id="viz-timeline" class="explore-panel"></div>
          <div id="viz-overview" class="explore-panel hidden"></div>
          <div id="viz-network" class="explore-panel hidden"></div>
        </div>
        <aside class="explore-detail" id="explore-detail">
          <div class="explore-detail-summary" id="explore-detail-content">
            ${this._renderDetailSummary(e)}
          </div>
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

    // Render the active mode
    if (mode === 'timeline' && typeof ExploreTimeline !== 'undefined') {
      ExploreTimeline.render(this.entries);
    } else if (mode === 'overview' && typeof ExploreOverview !== 'undefined') {
      ExploreOverview.render(this.entries);
    } else if (mode === 'network' && typeof ExploreNetwork !== 'undefined') {
      ExploreNetwork.render(this.entries);
    }
  },

  // -------------------------------------------------------------------------
  // Shared filtering
  // -------------------------------------------------------------------------

  getFiltered() {
    let filtered = this.entries;
    const f = this.filters;
    if (f.languages.length) filtered = filtered.filter(e => f.languages.includes(e.language));
    if (f.types.length) filtered = filtered.filter(e => f.types.includes(e.entryType));
    if (f.yearRange[0] != null) filtered = filtered.filter(e => e.year >= f.yearRange[0]);
    if (f.yearRange[1] != null) filtered = filtered.filter(e => e.year <= f.yearRange[1]);
    return filtered;
  },

  updateSelection(entries) {
    this.selection = entries.map(e => e.sourcePageId);
    const detail = document.getElementById('explore-detail-content');
    if (!detail) return;

    if (entries.length === 0) {
      detail.innerHTML = this._renderDetailSummary(this.entries);
    } else if (entries.length === 1) {
      detail.innerHTML = Detail.renderInline(entries[0]);
    } else {
      detail.innerHTML = this._renderDetailGroup(entries);
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
    const langCounts = {};
    entries.forEach(e => { if (e.language) langCounts[e.language] = (langCounts[e.language] || 0) + 1; });
    const topLangs = Object.entries(langCounts).sort((a, b) => b[1] - a[1]).slice(0, 5);

    // Top types in selection
    const typeCounts = {};
    entries.forEach(e => { if (e.entryType) typeCounts[e.entryType] = (typeCounts[e.entryType] || 0) + 1; });
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

        <button class="action-btn explore-view-btn" onclick="Explore.navigateToResults({${
          this.filters.types.length ? `type:'${this.filters.types[0]}'` : ''
        }${this.filters.languages.length ? `${this.filters.types.length ? ',' : ''}language:'${this.filters.languages[0]}'` : ''}})">
          View all ${entries.length.toLocaleString('en')} entries
        </button>
      </div>
    `;
  },
};

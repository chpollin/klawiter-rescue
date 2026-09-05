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
    country: null,
    publisher: null,
    translator: null,
    period: null,
    showProvenance: false,
  },

  /**
   * Label for a record whose language field is empty. Kept apart from
   * "Other languages", which means a recorded language outside the top ranks:
   * merging the two would read as evidence about translation history where it
   * is in fact a gap in the source.
   */
  NOT_RECORDED: 'Not recorded',

  // Precomputed indices
  byLanguage: new Map(),
  typeCount: 0,
  topLanguages: [],
  yearExtent: null,   // [min, max]; derived in _preprocess, never hardcoded
  yearlessCount: 0,   // entries carrying no year at all

  // Color palette — base values from shared COLORS constant, language palette local
  colors: {
    languages: {
      'German': COLORS.burgundy, 'Chinese': COLORS.gold, 'French': '#6B7A3A',
      'English': '#5B5040', 'Spanish': '#8B5C3A', 'Arabic': '#5B3A7A',
      'Bulgarian': '#3A5B6B', 'Albanian': '#7A4A1B', 'Russian': '#3A3A5B',
      'Croatian': '#6B3A4A', 'Other': '#9E9585',
      'Not recorded': '#CFC8BB',
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

  /** Modes the interface offers, in tab order. */
  MODES: ['timeline', 'geography', 'network'],

  render(entries) {
    this.entries = entries;
    this._initializing = true;
    this._preprocess();
    this._renderScaffolding();
    this._bindModeTabs();
    // #stats resumes the last view; a fresh session starts at the overview.
    this.setMode(this.MODES.includes(this.mode) ? this.mode : this.MODES[0]);
    this._initializing = false;
    this.updateExploreURL(false);
  },

  /** The dataset-wide year range published in the data baseline. */
  _metaYearRange() {
    return (App.data && App.data._meta && App.data._meta.yearRange) || null;
  },

  /**
   * Derive the static structure of the corpus. The result depends on the full
   * record set only, so it is computed once per dataset; filtering changes the
   * drawn subset, never the language ranking or the year extent that the
   * scales are built from.
   */
  _preprocess() {
    if (this._preprocessedFor === this.entries) return;
    const e = this.entries;

    // Year extent — from the entries in hand, falling back to the shipped
    // baseline when none of them carries a year.
    const years = e.map(x => x.year).filter(Boolean);
    const range = this._metaYearRange();
    this.yearExtent = years.length
      ? [Math.min(...years), Math.max(...years)]
      : (range ? [range.min, range.max] : [0, 0]);
    this.yearlessCount = e.length - years.length;

    // Index by language; a missing value is its own category
    this.byLanguage = new Map();
    for (const entry of e) {
      const lang = entry.language || this.NOT_RECORDED;
      if (!this.byLanguage.has(lang)) this.byLanguage.set(lang, []);
      this.byLanguage.get(lang).push(entry);
    }

    // Top 10 languages — the palette carries exactly ten named languages, so
    // every ranked language keeps a distinguishable color.
    this.topLanguages = [...this.byLanguage.entries()]
      .filter(([lang]) => lang !== this.NOT_RECORDED)
      .sort((a, b) => b[1].length - a[1].length)
      .slice(0, 10)
      .map(([lang]) => lang);

    this.typeCount = new Set(e.map(x => x.entryType || 'other')).size;

    this._preprocessedFor = e;
  },

  /** The visualization module backing a mode, or null when not yet loaded. */
  _module(mode) {
    if (mode === 'timeline') return typeof ExploreTimeline !== 'undefined' ? ExploreTimeline : null;
    if (mode === 'geography') return typeof ExploreGeography !== 'undefined' ? ExploreGeography : null;
    if (mode === 'network') return typeof ExploreNetwork !== 'undefined' ? ExploreNetwork : null;
    return null;
  },

  _renderActiveMode(data) {
    const mod = this._module(this.mode);
    if (mod) mod.render(data);
  },

  /** The record set the active view should draw. */
  visibleEntries() {
    return this.hasActiveFilters() ? this.getFiltered() : this.entries;
  },

  // -------------------------------------------------------------------------
  // Scaffolding
  // -------------------------------------------------------------------------

  /**
   * Shared modes and selection bar. The overview uses the full width; Map
   * and Connections keep their supporting facets and selection in a sidebar.
   */
  _renderScaffolding() {
    const container = document.getElementById('view-stats');

    container.innerHTML = `
      <div class="explore-head">
        <div><h1 class="page-title">Explore the bibliography</h1>
          <p class="explore-intro">Follow patterns in the catalogue, then read the entries behind them.</p></div>
        <div class="explore-mode-tabs" role="group" aria-label="Visualization">
          <button type="button" class="mode-tab" data-mode="timeline" aria-pressed="false">Overview</button>
          <button type="button" class="mode-tab" data-mode="geography" aria-pressed="false">Map</button>
          <button type="button" class="mode-tab" data-mode="network" aria-pressed="false">Connections</button>
        </div>
      </div>

      <div class="explore-selection-bar" aria-label="Current selection">
        <div id="explore-filter-chips" class="explore-filter-chips"></div>
      </div>
      <div class="explore-layout">
        <aside class="explore-sidebar" aria-label="Filters and selection">
          <div id="explore-facets"></div>
          <div id="explore-notes" class="explore-notes"></div>
          <div class="explore-detail hidden" id="explore-detail">
            <div class="explore-detail-summary" id="explore-detail-content"></div>
          </div>
        </aside>
        <div class="explore-viz" id="explore-viz">
          <div id="viz-timeline" class="explore-panel"></div>
          <div id="viz-geography" class="explore-panel hidden"></div>
          <div id="viz-network" class="explore-panel hidden"></div>
        </div>
      </div>

      <div class="stats-export">
        <button type="button" class="action-btn" data-act="export-dataset">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16" aria-hidden="true">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          Download dataset (JSON)
        </button>
      </div>
    `;

    const exportBtn = container.querySelector('[data-act="export-dataset"]');
    if (exportBtn) exportBtn.addEventListener('click', () => Export.fullDataset());

    // Shared tooltip — announced as a live region so the keyboard path
    // conveys the same reading the pointer path does.
    if (!document.getElementById('explore-tooltip')) {
      const tip = document.createElement('div');
      tip.id = 'explore-tooltip';
      tip.className = 'explore-tooltip';
      tip.setAttribute('role', 'status');
      tip.setAttribute('aria-live', 'polite');
      document.body.appendChild(tip);
    }
  },

  _bindModeTabs() {
    document.querySelectorAll('.mode-tab').forEach(tab => {
      tab.addEventListener('click', () => this.setMode(tab.dataset.mode));
    });
  },

  // ---------------------------------------------------------------------------
  // Sidebar filters — one filter bar for all three visualizations
  // ---------------------------------------------------------------------------

  /** Facet groups of the sidebar; every mode reads the same selection. */
  FACET_GROUPS: [
    { key: 'languages', label: 'Language', limit: 10 },
    { key: 'types', label: 'Type', limit: 12 },
    { key: 'decade', label: 'Decade', limit: 8 },
  ],

  _expandedFacets: {},

  /** The facet value a record falls into, or null when it has none. */
  _facetValue(key, entry) {
    if (key === 'languages') return entry.language || this.NOT_RECORDED;
    if (key === 'types') return entry.entryType || 'other';
    if (key === 'decade') return entry.year ? Math.floor(entry.year / 10) * 10 : null;
    return null;
  },

  _facetLabel(key, value) {
    if (key === 'types') return ENTRY_TYPE_LABELS[value] || value;
    if (key === 'decade') return `${value}s`;
    return String(value);
  },

  _isFacetActive(key, value) {
    if (key === 'decade') return this.filters.decade === value;
    return this.filters[key].includes(value);
  },

  /**
   * Counts of one facet group against every other active filter. Counting
   * against the fully filtered set would collapse a group to its own
   * selection, so no second value of it stays reachable.
   */
  facetCounts(key) {
    const others = { ...this.filters };
    if (key === 'decade') { others.decade = null; others.yearRange = [null, null]; }
    else others[key] = [];
    const counts = new Map();
    for (const entry of this._applyFilters(this.entries, others)) {
      const value = this._facetValue(key, entry);
      if (value == null) continue;
      counts.set(value, (counts.get(value) || 0) + 1);
    }
    return [...counts.entries()].sort((a, b) => key === 'decade'
      ? a[0] - b[0]
      : (b[1] - a[1] || String(a[0]).localeCompare(String(b[0]))));
  },

  _renderSidebar() {
    const host = document.getElementById('explore-facets');
    if (!host) return;
    host.innerHTML = this.FACET_GROUPS.map(g => this._facetGroupHtml(g)).join('');
  },

  _facetGroupHtml(group) {
    const rows = this.facetCounts(group.key);
    const expanded = !!this._expandedFacets[group.key];
    const shown = expanded ? rows : rows.slice(0, group.limit);
    const items = shown.map(([value, count]) => {
      const on = this._isFacetActive(group.key, value);
      return `<button type="button" class="facet-item${on ? ' active' : ''}"
        aria-pressed="${on}" data-facet="${group.key}" data-value="${esc(String(value))}">
        <span class="facet-label">${esc(this._facetLabel(group.key, value))}</span>
        <span class="facet-count">${fmt(count)}</span>
      </button>`;
    }).join('');
    const more = rows.length > group.limit
      ? `<button type="button" class="facet-more" data-facet-more="${group.key}">${
          expanded ? 'Show fewer' : `Show all ${rows.length}`}</button>`
      : '';
    return `<div class="facet-group">
      <div class="facet-heading">${group.label}</div>${items}${more}
    </div>`;
  },

  toggleFacetExpand(key) {
    this._expandedFacets[key] = !this._expandedFacets[key];
    this._renderSidebar();
  },

  /** A sidebar click; the value arrives as the string the attribute carried. */
  setFacet(key, raw) {
    if (key === 'decade') {
      // A decade and an entered year range address the same axis.
      this.filters.yearRange = [null, null];
      const timeline = this._module('timeline');
      if (timeline) timeline.zoomedDomain = null;
      this.toggleFilter('decade', parseInt(raw, 10));
      return;
    }
    this.toggleFilter(key, raw);
  },

  /**
   * What the active view cannot draw, stated once in the sidebar instead of
   * on the drawing surface. Returns the host so the caller can bind the
   * controls it wrote into it.
   */
  setViewNote(html) {
    const host = document.getElementById('explore-notes');
    if (host) host.innerHTML = html;
    return host;
  },

  // -------------------------------------------------------------------------
  // Mode switching
  // -------------------------------------------------------------------------

  setMode(mode) {
    this.mode = mode;
    const layout = document.querySelector('.explore-layout');
    if (layout) layout.classList.toggle('dashboard-layout', mode === 'timeline');

    document.querySelectorAll('.mode-tab').forEach(tab => {
      const active = tab.dataset.mode === mode;
      tab.classList.toggle('active', active);
      tab.setAttribute('aria-pressed', String(active));
    });

    // Show/hide panels
    document.querySelectorAll('.explore-panel').forEach(p => p.classList.add('hidden'));
    const panel = document.getElementById(`viz-${mode}`);
    if (panel) panel.classList.remove('hidden');

    // Reset selection (visual highlight is mode-specific) but preserve filters
    this.selection = [];
    this.setViewNote('');
    this._renderFilterChips();
    this.updateSelection([]);
    this._renderActiveMode(this.visibleEntries());
    this.updateExploreURL(true);
  },

  // -------------------------------------------------------------------------
  // Shared filtering
  // -------------------------------------------------------------------------

  hasActiveFilters() {
    const f = this.filters;
    return f.languages.length > 0 || f.types.length > 0 ||
      f.yearRange[0] != null || f.yearRange[1] != null ||
      f.decade != null || f.location != null || f.country != null ||
      f.publisher != null || f.translator != null || f.period != null;
  },

  getFiltered() {
    return this._applyFilters(this.entries, this.filters);
  },

  /** Apply one filter set to one record set; the facet counts reuse this. */
  _applyFilters(entries, f) {
    let filtered = entries;
    if (f.decade != null || f.yearRange.some(value => value != null)) {
      filtered = filtered.filter(e => Number.isFinite(e.year) && e.year > 0);
    }
    if (f.languages.length) {
      filtered = filtered.filter(e => f.languages.includes(e.language || this.NOT_RECORDED));
    }
    if (f.types.length) filtered = filtered.filter(e => f.types.includes(e.entryType));
    if (f.yearRange[0] != null) filtered = filtered.filter(e => e.year >= f.yearRange[0]);
    if (f.yearRange[1] != null) filtered = filtered.filter(e => e.year <= f.yearRange[1]);
    if (f.decade != null) {
      const d0 = f.decade, d1 = d0 + 9;
      filtered = filtered.filter(e => e.year >= d0 && e.year <= d1);
    }
    if (f.location) filtered = filtered.filter(e => e.location === f.location);
    if (f.country) {
      // The location → country mapping lives with the geodata, which only the
      // map view loads; without it the filter cannot be honoured and is a no-op.
      const geo = this._module('geography');
      if (geo && geo.countryOfEntry) filtered = filtered.filter(e => geo.countryOfEntry(e) === f.country);
    }
    if (f.publisher) filtered = filtered.filter(e => e.publisher === f.publisher);
    if (f.translator) filtered = filtered.filter(e => translatorKeys(e).includes(f.translator));
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
      decade: null, location: null, country: null,
      publisher: null, translator: null, period: null,
      showProvenance: false,
    };
    this._onFilterChange();
  },

  _onFilterChange() {
    const focused = document.activeElement && document.activeElement.dataset.dashboardFocus;
    this._renderFilterChips();
    const data = this.visibleEntries();
    this._renderActiveMode(data);
    this.updateSelection(data.length < this.entries.length ? data : []);
    // The active mode has just been redrawn; marking it as the source keeps
    // its own listener from redrawing it a second time.
    document.dispatchEvent(new CustomEvent('explore:filterChange', {
      detail: { filters: { ...this.filters }, filtered: data.length, mode: this.mode },
    }));
    this.updateExploreURL(false);
    if (focused) {
      let target = [...document.querySelectorAll('[data-dashboard-focus]')]
        .find(el => el.dataset.dashboardFocus === focused);
      if (!target || target.disabled) {
        target = this.mode === 'timeline'
          ? document.querySelector('#viz-timeline [name="from"]')
          : document.querySelector('.mode-tab.active');
      }
      if (target) target.focus({ preventScroll: true });
    }
  },

  /**
   * Register a mode's reconciliation handler for filter changes raised
   * elsewhere. Only one view is on screen at a time, so this is a state
   * reconciliation hook rather than live cross-view linking: it fires when a
   * filter changes without the active mode having drawn itself already.
   */
  bindModeFilterListener(mode, fn) {
    this._modeListeners = this._modeListeners || {};
    if (this._modeListeners[mode]) {
      document.removeEventListener('explore:filterChange', this._modeListeners[mode]);
    }
    const handler = (event) => {
      if (this.mode !== mode) return;
      if (event.detail && event.detail.mode === mode) return;
      fn(this.visibleEntries(), event);
    };
    this._modeListeners[mode] = handler;
    document.addEventListener('explore:filterChange', handler);
  },

  /**
   * The chip bar and the facet lists show one and the same selection, so the
   * single entry point redraws both; the views that set a filter directly
   * (year range, map playback) call this and stay in step.
   */
  _renderFilterChips() {
    this._renderSidebar();
    const el = document.getElementById('explore-filter-chips');
    if (!el) return;
    const f = this.filters;
    const chips = [];

    const chip = (label, value, key, raw) =>
      `<span class="chip">${label}: ${value} <button type="button" aria-label="Remove ${esc(label)}: ${esc(String(raw == null ? value : raw))}"
        data-explore-clear="${esc(key)}"${raw == null ? '' : ` data-value="${esc(String(raw))}"`}>&times;</button></span>`;

    for (const lang of f.languages) {
      chips.push(chip('Language', esc(lang),
        'languages', lang));
    }
    for (const type of f.types) {
      chips.push(chip('Type', esc(ENTRY_TYPE_LABELS[type] || type),
        'types', type));
    }
    if (f.yearRange[0] != null || f.yearRange[1] != null) {
      chips.push(chip('Years', `${f.yearRange[0] || '?'}–${f.yearRange[1] || '?'}`,
        'yearRange'));
    }
    if (f.decade != null) chips.push(chip('Decade', `${f.decade}s`, 'decade'));
    if (f.location) chips.push(chip('Location', esc(f.location), 'location'));
    if (f.country) {
      const geo = this._module('geography');
      const name = (geo && geo._countryNames[f.country]) || f.country;
      chips.push(chip('Country', esc(name), 'country'));
    }
    if (f.publisher) chips.push(chip('Publisher', esc(f.publisher), 'publisher'));
    if (f.translator) chips.push(chip('Translator', esc(f.translator), 'translator'));
    if (f.period) {
      chips.push(chip('Period', esc(PERIOD_LABELS[f.period] || f.period), 'period'));
    }

    el.innerHTML = `<span class="explore-selection-label">Selection</span>`
      + (chips.length ? chips.join(' ') : '<span class="explore-selection-empty">All entries · select a bar to explore</span>')
      + `<button type="button" class="chip-clear" data-explore-reset data-dashboard-focus="reset-filters" ${chips.length ? '' : 'disabled'}>Reset filters</button>`;
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
      this._selectedEntries = entries;
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
      for (const value of Array.isArray(v) ? v : [v]) {
        if (value) params.append(k, value);
      }
    }
    location.hash = params.toString();
  },

  // -------------------------------------------------------------------------
  // URL hash state persistence
  // -------------------------------------------------------------------------

  updateExploreURL(pushState) {
    if (this._initializing) return;
    const params = new URLSearchParams();
    const f = this.filters;
    if (f.languages.length) params.set('language', f.languages.join(','));
    if (f.types.length) params.set('type', f.types.join(','));
    if (f.yearRange[0] != null || f.yearRange[1] != null) {
      params.set('years', `${f.yearRange[0] || ''}-${f.yearRange[1] || ''}`);
    }
    if (f.decade != null) params.set('decade', f.decade);
    if (f.location) params.set('location', f.location);
    if (f.country) params.set('country', f.country);
    if (f.publisher) params.set('publisher', f.publisher);
    if (f.translator) params.set('translator', f.translator);
    if (f.period) params.set('period', f.period);
    if (f.showProvenance) params.set('provenance', 'true');
    // Timeline-specific state
    const timeline = this._module('timeline');
    if (this.mode === 'timeline' && timeline) {
      if (timeline.layerMode !== 'language') params.set('layers', timeline.layerMode);
      if (timeline.chartMode !== 'bars') params.set('chart', timeline.chartMode);
    }
    const paramStr = params.toString();
    const hash = `stats/${this.mode}${paramStr ? '?' + paramStr : ''}`;
    const method = pushState ? 'pushState' : 'replaceState';
    history[method](null, '', '#' + hash);
    // Keep App._lastHash in sync to prevent double-processing
    if (typeof App !== 'undefined') App._lastHash = hash;
  },

  restoreFromHash(mode, params) {
    // A bookmarked selection replaces session state, including absent filters.
    this.filters = {
      languages: [], types: [], yearRange: [null, null],
      decade: null, location: null, country: null,
      publisher: null, translator: null, period: null, showProvenance: false,
    };
    // Restore filter state from URL parameters
    const lang = params.get('language');
    if (lang) this.filters.languages = lang.split(',');
    const type = params.get('type');
    if (type) this.filters.types = type.split(',');
    const yearValue = value => /^\d{1,4}$/.test(value || '') && Number(value) > 0 ? Number(value) : null;
    const years = params.get('years');
    if (years) {
      const parts = years.split('-');
      if (parts.length === 2) {
        const [y0, y1] = parts.map(yearValue);
        if (y0 == null || y1 == null || y0 <= y1) this.filters.yearRange = [y0, y1];
      }
    }
    const decade = yearValue(params.get('decade'));
    if (decade != null && decade % 10 === 0) {
      this.filters.decade = decade;
      this.filters.yearRange = [null, null];
    }
    const loc = params.get('location');
    if (loc) this.filters.location = loc;
    const country = params.get('country');
    if (country) this.filters.country = country;
    const pub = params.get('publisher');
    if (pub) this.filters.publisher = pub;
    const trans = params.get('translator');
    if (trans) this.filters.translator = trans;
    const period = params.get('period');
    if (period) this.filters.period = period;
    if (params.get('provenance') === 'true') this.filters.showProvenance = true;
    // Timeline-specific state
    const timeline = this._module('timeline');
    if (timeline) {
      const layers = params.get('layers');
      if (layers) timeline.layerMode = layers;
      const chart = params.get('chart');
      if (chart) timeline.chartMode = chart;
    }
    // Apply: switch to the requested mode (re-renders with filters)
    // Suppress pushState during restore — use replaceState instead
    this._initializing = true;
    const validModes = ['timeline', 'geography', 'network'];
    this.setMode(validModes.includes(mode) ? mode : 'timeline');
    this._initializing = false;
    this.updateExploreURL(false);
  },

  // -------------------------------------------------------------------------
  // Tooltip
  // -------------------------------------------------------------------------

  /**
   * Anchor for the tooltip. A pointer event carries its own page position; a
   * focus event does not, so the focused element's box stands in for it.
   */
  _tooltipAnchor(event) {
    if (event && typeof event.pageX === 'number' && event.pageX !== 0) {
      return { x: event.pageX, y: event.pageY };
    }
    const el = event && (event.currentTarget || event.target);
    if (el && typeof el.getBoundingClientRect === 'function') {
      const r = el.getBoundingClientRect();
      return { x: r.left + window.scrollX, y: r.top + window.scrollY };
    }
    return { x: 0, y: 0 };
  },

  showTooltip(html, event) {
    const tip = document.getElementById('explore-tooltip');
    if (!tip) return;
    tip.innerHTML = html;
    tip.style.display = 'block';

    const rect = tip.getBoundingClientRect();
    const anchor = this._tooltipAnchor(event);
    const x = Math.min(anchor.x + 12, window.innerWidth - rect.width - 20);
    const y = anchor.y - rect.height - 8;
    tip.style.left = x + 'px';
    tip.style.top = (y > 0 ? y : anchor.y + 12) + 'px';
  },

  hideTooltip() {
    const tip = document.getElementById('explore-tooltip');
    if (tip) tip.style.display = 'none';
  },

  // -------------------------------------------------------------------------
  // Detail panel renderers
  // -------------------------------------------------------------------------

  _renderDetailGroup(entries) {
    // Top languages and types in selection
    const topLangs = topN(entries, 'language', 5);
    const topTypes = topN(entries, 'entryType', 5);

    // Year range
    const years = entries.map(e => e.year).filter(Boolean);
    const minY = years.length ? Math.min(...years) : '?';
    const maxY = years.length ? Math.max(...years) : '?';

    // Entry list (max 20)
    const shown = entries.slice(0, 20);
    const listHtml = shown.map(e =>
      `<li class="detail-entry-item">
        <a href="#entry=${e.sourcePageId}" class="detail-entry-link">
          <span class="badge">${ENTRY_TYPE_LABELS[e.entryType] || e.entryType}</span>
          ${esc(e.title || 'Untitled')}
          ${e.year ? `<span class="detail-entry-year">${e.year}</span>` : ''}
        </a>
      </li>`
    ).join('');

    const moreHtml = entries.length > 20
      ? `<p class="detail-more">and ${fmt(entries.length - 20)} more</p>`
      : '';

    return `
      <div class="detail-group">
        <h3 class="detail-group-title">${fmt(entries.length)} entries selected</h3>
        <div class="detail-group-meta">
          <span>${minY}&ndash;${maxY}</span>
        </div>

        <div class="detail-group-section">
          <h4>Languages</h4>
          <div class="detail-mini-bars">
            ${topLangs.map(([lang, count]) =>
              `<div class="mini-bar-row">
                <span class="mini-bar-label">${esc(lang)}</span>
                <span class="mini-bar-count">${fmt(count)}</span>
              </div>`
            ).join('')}
          </div>
        </div>

        <div class="detail-group-section">
          <h4>Types</h4>
          <div class="detail-mini-bars">
            ${topTypes.map(([type, count]) =>
              `<div class="mini-bar-row">
                <span class="mini-bar-label">${esc(ENTRY_TYPE_LABELS[type] || type)}</span>
                <span class="mini-bar-count">${fmt(count)}</span>
              </div>`
            ).join('')}
          </div>
        </div>

        <div class="detail-group-section">
          <h4>Entries</h4>
          <ul class="detail-entry-list">${listHtml}</ul>
          ${moreHtml}
        </div>

        <button type="button" class="action-btn explore-view-btn" onclick="Explore._navigateFromFilters()">
          View all ${fmt(entries.length)} entries
        </button>
      </div>
    `;
  },

  /**
   * Filter keys the results route can reproduce from the hash. `country` is
   * absent on purpose: it resolves through the geodata, which the results
   * route does not load, so a country selection is handed over as a
   * session-scoped list instead.
   */
  _resultParams() {
    const f = this.filters;
    const params = {};
    if (f.languages.length) params.language = [...f.languages];
    if (f.types.length) params.type = [...f.types];
    if (f.location) params.location = f.location;
    if (f.publisher) params.publisher = f.publisher;
    if (f.translator) params.translator = f.translator;
    if (f.period) params.period = f.period;
    if (f.decade != null) params.decade = String(f.decade);
    else if (f.yearRange[0] != null || f.yearRange[1] != null) {
      params.years = `${f.yearRange[0] || ''}-${f.yearRange[1] || ''}`;
    }
    return params;
  },

  _navigateFromFilters() {
    if (this.filters.country) {
      const geo = this._module('geography');
      const name = (geo && geo._countryNames[this.filters.country]) || this.filters.country;
      App.showCustomResults(this._selectedEntries || this.getFiltered(), name);
      return;
    }
    const params = this._resultParams();
    if (!Object.keys(params).length && this._selectedEntries) {
      App.showCustomResults(this._selectedEntries, 'Selection');
      return;
    }
    this.navigateToResults(params);
  },
};

// One delegated listener for the sidebar; the facet lists are rebuilt on every
// filter change, so per-element handlers would have to be rebound each time.
document.addEventListener('click', (ev) => {
  const reset = ev.target.closest('[data-explore-reset]');
  if (reset) { Explore.clearAllFilters(); return; }
  const clear = ev.target.closest('[data-explore-clear]');
  if (clear) {
    if (clear.dataset.value != null) Explore.toggleFilter(clear.dataset.exploreClear, clear.dataset.value);
    else Explore.clearFilter(clear.dataset.exploreClear);
    return;
  }
  const more = ev.target.closest('#explore-facets [data-facet-more]');
  if (more) { Explore.toggleFacetExpand(more.dataset.facetMore); return; }
  const item = ev.target.closest('#explore-facets [data-facet]');
  if (item) Explore.setFacet(item.dataset.facet, item.dataset.value);
});

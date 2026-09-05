/** Linked overview of the flat catalogue. Each counted item is a source-page entry. */
const ExploreTimeline = {
  entries: [],
  // Retained for existing timeline URLs; the overview uses one neutral series.
  layerMode: 'language',
  chartMode: 'bars',
  zoomedDomain: null,
  expanded: {},

  coverage(entries) {
    const dated = entries.filter(entry => Number.isFinite(entry.year) && entry.year > 0);
    return {
      total: entries.length,
      dated: dated.length,
      undated: entries.length - dated.length,
      languages: new Set(entries.map(entry => entry.language).filter(Boolean)).size,
      missingLanguage: entries.filter(entry => !entry.language).length,
    };
  },

  decadeCounts(entries) {
    const counts = new Map();
    for (const entry of entries) {
      if (!Number.isFinite(entry.year) || entry.year <= 0) continue;
      const decade = Math.floor(entry.year / 10) * 10;
      counts.set(decade, (counts.get(decade) || 0) + 1);
    }
    if (!counts.size) return [];
    const min = Math.min(...counts.keys()), max = Math.max(...counts.keys());
    const rows = [];
    for (let decade = min; decade <= max; decade += 10) rows.push([decade, counts.get(decade) || 0]);
    return rows;
  },

  /** Alternatives ignore their own axis so a selected bar never removes its neighbours. */
  contextForYears() {
    return Explore._applyFilters(Explore.entries, {
      ...Explore.filters, yearRange: [null, null], decade: null,
    });
  },

  render(entries) {
    const host = document.getElementById('viz-timeline');
    if (!host) return;
    this.entries = entries;
    const stats = this.coverage(entries);
    const percent = stats.total ? Math.round(100 * stats.dated / stats.total) : 0;
    const full = Explore.entries.length;
    const missing = stats.missingLanguage;
    host.innerHTML = `
      <div class="dashboard-summary" aria-label="Selection summary">
        <div class="dashboard-metric dashboard-metric-primary">
          <span class="dashboard-eyebrow">Selected entries</span>
          <strong>${fmt(stats.total)}</strong><span>of ${fmt(full)} catalogue entries</span>
        </div>
        <div class="dashboard-metric"><span class="dashboard-eyebrow">With a recorded year</span>
          <strong>${fmt(stats.dated)}</strong><span>${percent}% of this selection</span></div>
        <div class="dashboard-metric"><span class="dashboard-eyebrow">Year not recorded</span>
          <strong>${fmt(stats.undated)}</strong>
          <button type="button" class="link-btn" data-dashboard-undated ${stats.undated ? '' : 'disabled'}>Read these entries</button></div>
        <div class="dashboard-metric"><span class="dashboard-eyebrow">Recorded languages</span>
          <strong>${fmt(stats.languages)}</strong><span>${fmt(missing)} entries without a language</span></div>
      </div>
      <p id="dashboard-status" class="dashboard-scope" role="status" aria-live="polite">${fmt(stats.total)} entries selected. Counts describe source pages; one page may cite several editions.</p>
      <section class="dashboard-panel dashboard-time" aria-labelledby="dashboard-time-title">
        <div class="dashboard-panel-head"><div>
          <span class="dashboard-eyebrow">Through time</span><h2 id="dashboard-time-title">Entries by recorded year</h2>
          <p>Select a decade, or set a year range. Undated entries are counted above.</p>
        </div><span class="dashboard-chart-unit">Entries / decade</span></div>
        ${this.timelineHtml(entries)}
        ${this.rangeHtml()}
      </section>
      <div class="dashboard-rankings">
        ${this.rankingHtml('languages', 'Languages', 'Select one or more languages', 7)}
        ${this.rankingHtml('types', 'Entry types', 'Select one or more types', 7)}
      </div>
      ${this.previewHtml(entries)}
    `;
    host.addEventListener('click', this._clickHandler ||= event => this.onClick(event));
    const range = host.querySelector('.dashboard-range');
    range.addEventListener('submit', event => this.applyRange(event));
    range.addEventListener('input', () => range.elements.to.setCustomValidity(''));
    host.onfocusin = event => this.describeDecade(event);
    host.onpointerover = event => this.describeDecade(event);
  },

  timelineHtml(selected) {
    const rows = this.decadeCounts(this.contextForYears());
    if (!rows.length) return '<p class="dashboard-empty">No recorded years in this selection. Broaden the other filters to explore the timeline.</p>';
    const selectedCounts = new Map(this.decadeCounts(selected));
    const max = Math.max(...rows.map(([, count]) => count));
    const filtered = Explore.filters.decade != null || Explore.filters.yearRange.some(value => value != null);
    const bars = rows.map(([decade, count]) => {
      const chosen = selectedCounts.get(decade) || 0;
      const pressed = Explore.filters.decade === decade;
      const label = `${decade}–${decade + 9}: ${fmt(count)} entries${filtered ? `, ${fmt(chosen)} in the selected range` : ''}`;
      return `<button type="button" class="dashboard-decade${filtered && chosen ? ' is-selected' : ''}"
        data-dashboard-decade="${decade}" data-dashboard-focus="decade:${decade}"
        aria-label="${label}" aria-pressed="${pressed}" title="${label}" ${count ? '' : 'disabled'}>
        <span class="dashboard-decade-bar" style="height:${100 * count / max}%"></span>
        ${filtered ? `<span class="dashboard-decade-selected" style="height:${100 * chosen / max}%"></span>` : ''}
      </button>`;
    }).join('');
    return `<div class="dashboard-timeline">
      <div class="dashboard-y-axis" aria-hidden="true"><span>${fmt(max)}</span><span>${fmt(Math.round(max / 2))}</span><span>0</span></div>
      <div class="dashboard-histogram" role="group" aria-label="Filter by decade" style="--decades:${rows.length}">${bars}</div>
      <div class="dashboard-x-axis" aria-hidden="true"><span>${rows[0][0]}</span><span>${rows[Math.floor((rows.length - 1) / 2)][0]}</span><span>${rows.at(-1)[0] + 9}</span></div>
    </div><p class="dashboard-chart-reading" id="dashboard-chart-reading">${filtered ? 'Burgundy shows the selected years. ' : ''}Bars retain the other filters. Focus or hover for exact counts.</p>`;
  },

  rangeHtml() {
    const f = Explore.filters;
    const from = f.decade != null ? f.decade : f.yearRange[0];
    const to = f.decade != null ? f.decade + 9 : f.yearRange[1];
    const [min, max] = Explore.yearExtent || [0, 0];
    return `<form class="dashboard-range" aria-label="Filter by recorded year">
      <label>From year<input name="from" type="number" min="1" max="9999" step="1" inputmode="numeric" aria-label="From year" data-dashboard-focus="from-year" placeholder="${min || 'Any'}" value="${from == null ? '' : from}"></label>
      <span class="dashboard-range-separator" aria-hidden="true">—</span>
      <label>To year<input name="to" type="number" min="1" max="9999" step="1" inputmode="numeric" aria-label="To year" data-dashboard-focus="to-year" placeholder="${max || 'Any'}" value="${to == null ? '' : to}"></label>
      <button type="submit" class="action-btn" data-dashboard-focus="apply-range">Apply range</button>
      <button type="button" class="link-btn" data-dashboard-clear-years data-dashboard-focus="clear-years" ${from == null && to == null ? 'disabled' : ''}>All years</button>
    </form>`;
  },

  rankingHtml(key, title, hint, limit) {
    const rows = Explore.facetCounts(key);
    const selected = Explore.filters[key];
    const shown = this.expanded[key] ? rows : rows.filter(([value], index) =>
      index < limit || selected.includes(value) || (key === 'languages' && value === Explore.NOT_RECORDED));
    const max = Math.max(1, ...rows.map(([, count]) => count));
    const items = shown.map(([value, count]) => {
      const active = selected.includes(value);
      const label = Explore._facetLabel(key, value);
      return `<li><button type="button" class="dashboard-rank${active ? ' is-selected' : ''}"
        data-dashboard-facet="${key}" data-value="${esc(String(value))}" data-dashboard-focus="${key}:${esc(String(value))}"
        aria-pressed="${active}" aria-label="${esc(label)}: ${fmt(count)} entries">
        <span class="dashboard-rank-name">${esc(label)}</span><span class="dashboard-rank-count">${fmt(count)}</span>
        <span class="dashboard-rank-track" aria-hidden="true"><span style="width:${100 * count / max}%"></span></span>
      </button></li>`;
    }).join('');
    return `<section class="dashboard-panel" aria-labelledby="dashboard-${key}-title">
      <div class="dashboard-panel-head"><div><h2 id="dashboard-${key}-title">${title}</h2><p>${hint}. Other filters stay applied.</p></div></div>
      ${items ? `<ol class="dashboard-ranking">${items}</ol>` : '<p class="dashboard-empty">No matching entries. Try clearing a filter.</p>'}
      ${rows.length > limit ? `<button type="button" class="link-btn dashboard-more" data-dashboard-more="${key}" data-dashboard-focus="more:${key}" aria-expanded="${!!this.expanded[key]}">${this.expanded[key] ? 'Show fewer' : `Show all ${rows.length} ${key === 'types' ? 'types' : 'language groups'}`}</button>` : ''}
    </section>`;
  },

  previewHtml(entries) {
    const shown = entries.slice(0, 5);
    return `<section class="dashboard-panel dashboard-preview" aria-labelledby="dashboard-preview-title">
      <div class="dashboard-panel-head"><div><span class="dashboard-eyebrow">Behind the numbers</span>
        <h2 id="dashboard-preview-title">Read the selected entries</h2><p>${entries.length ? `Showing ${shown.length} of ${fmt(entries.length)} entries in source order.` : 'No entries match these filters.'}</p>
      </div><button type="button" class="action-btn" data-dashboard-results ${entries.length ? '' : 'disabled'}>View all ${fmt(entries.length)} entries <span aria-hidden="true">↗</span></button></div>
      <ol class="dashboard-entry-list">${shown.map(entry => `<li>
        <a href="#entry=${entry.sourcePageId}" class="dashboard-entry-link"><span class="dashboard-entry-title">${esc(entry.title || 'Untitled')}</span>
          <span class="dashboard-entry-meta">${entry.year || 'Year not recorded'} · ${esc(entry.language || Explore.NOT_RECORDED)} · ${esc(ENTRY_TYPE_LABELS[entry.entryType] || entry.entryType || 'Other')}</span>
        </a><span aria-hidden="true">→</span></li>`).join('')}</ol>
    </section>`;
  },

  applyRange(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const from = form.elements.from, to = form.elements.to;
    to.setCustomValidity('');
    const lo = from.value === '' ? null : Number(from.value);
    const hi = to.value === '' ? null : Number(to.value);
    if ((lo != null && !Number.isInteger(lo)) || (hi != null && !Number.isInteger(hi))) return;
    if (lo != null && hi != null && lo > hi) {
      to.setCustomValidity('The end year must be the same as or after the start year.');
      to.reportValidity();
      return;
    }
    Explore.filters.yearRange = [lo, hi];
    Explore.filters.decade = null;
    Explore._onFilterChange();
  },

  onClick(event) {
    const target = event.target.closest('button');
    if (!target || target.disabled) return;
    if (target.dataset.dashboardDecade != null) {
      Explore.setFacet('decade', target.dataset.dashboardDecade);
    } else if (target.dataset.dashboardFacet) {
      Explore.toggleFilter(target.dataset.dashboardFacet, target.dataset.value);
    } else if (target.dataset.dashboardMore) {
      const key = target.dataset.dashboardMore;
      this.expanded[key] = !this.expanded[key];
      this.render(this.entries);
      document.querySelector(`[data-dashboard-more="${key}"]`).focus({ preventScroll: true });
    } else if (target.hasAttribute('data-dashboard-results')) {
      this.openResults();
    } else if (target.hasAttribute('data-dashboard-undated')) {
      App.showCustomResults(this.entries.filter(entry => !Number.isFinite(entry.year) || entry.year <= 0), 'Entries without a recorded year');
    } else if (target.hasAttribute('data-dashboard-clear-years')) {
      Explore.filters.yearRange = [null, null];
      Explore.filters.decade = null;
      Explore._onFilterChange();
    }
  },

  openResults() {
    if (!Explore.hasActiveFilters()) Explore.navigateToResults({ browse: '1' });
    else {
      Explore._selectedEntries = this.entries;
      Explore._navigateFromFilters();
    }
  },

  describeDecade(event) {
    const bar = event.target.closest('[data-dashboard-decade]');
    const reading = document.getElementById('dashboard-chart-reading');
    if (bar && reading) reading.textContent = bar.getAttribute('aria-label');
  },
};

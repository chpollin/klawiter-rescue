/**
 * Faceted navigation — type, language, period, location.
 */
const Facets = {
  render(entries) {
    this.renderFacet('facet-type-list', entries, 'entryType', 'type', ENTRY_TYPE_LABELS);
    this.renderFacet('facet-language-list', entries, 'language', 'language', null, 15);
    this.renderFacet('facet-period-list', entries, 'timePeriod', 'period', PERIOD_LABELS);
    this.renderFacet('facet-location-list', entries, 'location', 'location', null, 15);
  },

  renderFacet(containerId, entries, field, filterKey, labels, limit) {
    const counts = {};
    for (const e of entries) {
      const val = e[field];
      if (val) counts[val] = (counts[val] || 0) + 1;
    }

    const sorted = Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, limit || 50);

    const active = App.state.filters[filterKey];
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = sorted.map(([val, count]) => {
      const label = labels ? (labels[val] || val) : val;
      const isActive = active === val;
      const escaped = val.replace(/'/g, "\\'");
      return `<div class="facet-item ${isActive ? 'active' : ''}" tabindex="0" role="button"
                   onclick="Facets.toggle('${filterKey}', '${escaped}')"
                   onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();Facets.toggle('${filterKey}','${escaped}')}">
        <span>${esc(label)}</span>
        <span class="facet-count">${count}</span>
      </div>`;
    }).join('');
  },

  toggle(filterKey, value) {
    if (App.state.filters[filterKey] === value) {
      App.removeFilter(filterKey);
    } else {
      App.setFilter(filterKey, value);
    }
  },
};

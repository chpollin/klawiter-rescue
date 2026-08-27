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
    const counts = countByField(entries, field);

    const sorted = Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, limit || 50);

    const active = App.state.filters[filterKey];
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = sorted.map(([val, count]) => {
      const label = labels ? (labels[val] || val) : val;
      const isActive = active === val;
      return `<div class="facet-item ${isActive ? 'active' : ''}" tabindex="0" role="button"
                   data-facet-key="${esc(filterKey)}" data-facet-value="${esc(val)}">
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

  _target(ev) {
    return ev.target.closest('.facet-item[data-facet-key]');
  },
};

// Delegated on the document so the mobile drawer, which clones the facet
// markup, is served by the same handler. The value travels as a data
// attribute; inside an inline handler it was a JS string literal that a
// quote in the value could end early.
document.addEventListener('click', (ev) => {
  const item = Facets._target(ev);
  if (item) Facets.toggle(item.dataset.facetKey, item.dataset.facetValue);
});

document.addEventListener('keydown', (ev) => {
  if (ev.key !== 'Enter' && ev.key !== ' ') return;
  const item = Facets._target(ev);
  if (!item) return;
  ev.preventDefault();
  Facets.toggle(item.dataset.facetKey, item.dataset.facetValue);
});

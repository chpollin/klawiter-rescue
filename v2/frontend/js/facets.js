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
      return `<div class="facet-item ${isActive ? 'active' : ''}"
                   onclick="Facets.toggle('${filterKey}', '${val.replace(/'/g, "\\'")}')">
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

const ENTRY_TYPE_LABELS = {
  'fiction': 'Belletristik',
  'essay': 'Essays',
  'poetry': 'Lyrik',
  'drama': 'Dramatik',
  'correspondence': 'Korrespondenz',
  'film': 'Film / Oper',
  'historical-study': 'Historische Studien',
  'secondary-literature': 'Sekundärliteratur',
  'collected-works': 'Gesammelte Werke',
  'foreword': 'Vor-/Nachworte',
  'translation': 'Übersetzungen (von Zweig)',
  'symposium': 'Symposien / Ausstellungen',
  'dramatic-reading': 'Dramatische Lesungen',
  'newspaper': 'Zeitungsartikel',
  'other': 'Sonstige',
};

const PERIOD_LABELS = {
  'pre-zweig': 'Vor Zweig (–1880)',
  'lifetime': 'Lebenszeit (1881–1942)',
  'post-wwii': 'Nachkriegszeit (1943–1980)',
  'late-20c': 'Spätes 20. Jh. (1981–2000)',
  'contemporary': 'Gegenwart (2001–)',
};

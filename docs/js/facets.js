/**
 * Faceted navigation — type, language, period, location, review.
 */
const Facets = {
  /** Facet groups whose long tail is collapsed until asked for. */
  DEFAULT_LIMIT: 15,

  /** Groups whose values stay folded away until the reader asks for them. */
  CLOSED_BY_DEFAULT: ['period', 'location'],

  expanded: {},     // filterKey -> true while its full list is shown
  open: {},         // filterKey -> true/false once the group was toggled
  _entries: null,   // the set the current rendering was built from

  render(entries) {
    this._entries = entries;
    this.renderFacet('facet-type-list', this._candidates('type', entries),
      'entryType', 'type', ENTRY_TYPE_LABELS);
    this.renderFacet('facet-language-list', this._candidates('language', entries),
      'language', 'language', null, this.DEFAULT_LIMIT);
    this.renderFacet('facet-period-list', this._candidates('period', entries),
      'timePeriod', 'period', PERIOD_LABELS);
    this.renderFacet('facet-location-list', this._candidates('location', entries),
      'location', 'location', null, this.DEFAULT_LIMIT);
    this.renderFacet('facet-review-list', this._candidates('review', entries),
      'review', 'review');
    for (const key of ['type', 'language', 'period', 'location', 'review']) {
      this._applyGroupState(key);
    }
  },

  isOpen(filterKey) {
    return this.open[filterKey] === undefined
      ? !this.CLOSED_BY_DEFAULT.includes(filterKey)
      : this.open[filterKey];
  },

  /**
   * A closed group still has to say that it is filtering, so its heading
   * carries the number of values selected inside it.
   */
  _applyGroupState(filterKey) {
    const btn = document.querySelector(`[data-facet-toggle="${filterKey}"]`);
    const list = document.getElementById(`facet-${filterKey}-list`);
    if (!btn || !list) return;
    const open = this.isOpen(filterKey);
    btn.setAttribute('aria-expanded', String(open));
    list.hidden = !open;
    const active = App.state.filters[filterKey];
    const count = Array.isArray(active) ? active.length : (active ? 1 : 0);
    const badge = btn.querySelector('.facet-group-count');
    if (badge) badge.textContent = !open && count ? String(count) : '';
  },

  toggleOpen(filterKey) {
    this.open[filterKey] = !this.isOpen(filterKey);
    this._applyGroupState(filterKey);
  },

  /**
   * Standard drilldown: a facet counts against the set that all other filters
   * select, not against the fully filtered result. Counting against the result
   * made every alternative value of the chosen facet disappear the moment it
   * was chosen, so the choice could not be changed, only cleared.
   */
  _candidates(filterKey, entries) {
    const active = App.state && App.state.filters ? Object.keys(App.state.filters).length : 0;
    return active && typeof App.facetCandidates === 'function'
      ? App.facetCandidates(filterKey)
      : entries;
  },

  /**
   * The values one entry falls under in a facet. Language, place and period
   * are read from the publication layer, so a page with a German and an Arabic
   * publication is counted under both and its count agrees with the list the
   * facet opens. A missing language is a value of its own, and the review
   * facet reads a derived state rather than a field.
   */
  _values(entry, field, filterKey) {
    if (filterKey === 'review') return App.reviewValues(entry);
    if (filterKey === 'language') return App.languageValues(entry);
    if (filterKey === 'location') return App.placeValues(entry);
    if (filterKey === 'period') return App.periodValues(entry);
    const value = entry[field];
    return value == null || value === '' ? [] : [value];
  },

  _counts(entries, field, filterKey) {
    const counts = {};
    for (const entry of entries) {
      for (const value of this._values(entry, field, filterKey)) {
        counts[value] = (counts[value] || 0) + 1;
      }
    }
    return counts;
  },

  renderFacet(containerId, entries, field, filterKey, labels, limit) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const counts = this._counts(entries, field, filterKey);
    const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);
    const total = sorted.length;
    const active = App.state.filters[filterKey];
    const selected = Array.isArray(active) ? active : (active ? [active] : []);
    const cap = limit || 50;
    const collapsed = total > cap && !this.expanded[filterKey];
    const shown = collapsed ? sorted.slice(0, cap) : sorted;
    // The selected value stays visible even when it sits outside the top of
    // the ranking, or the sidebar would show no trace of the active filter.
    for (const value of selected) {
      if (shown.some(([val]) => val === value)) continue;
      const hit = sorted.find(([val]) => val === value);
      shown.push(hit || [value, 0]);
    }

    let html = shown.map(([val, count]) => {
      const label = filterKey === 'review'
        ? App.reviewLabel(val) : (labels ? (labels[val] || val) : val);
      const isActive = selected.includes(val);
      return `<div class="facet-item ${isActive ? 'active' : ''}" tabindex="0" role="button"
                   aria-pressed="${isActive}"
                   data-facet-key="${esc(filterKey)}" data-facet-value="${esc(val)}">
        <span>${esc(label)}</span>
        <span class="facet-count">${count}</span>
      </div>`;
    }).join('');

    if (total > cap) {
      html += `<button class="facet-more" data-facet-more="${esc(filterKey)}"
                       aria-expanded="${!collapsed}">${collapsed
        ? `Show all ${total}` : 'Show fewer'}</button>`;
    }
    container.innerHTML = html;
  },

  toggle(filterKey, value) {
    const active = App.state.filters[filterKey];
    if (Array.isArray(active)) {
      const next = active.includes(value) ? active.filter(v => v !== value) : [...active, value];
      if (next.length) App.setFilter(filterKey, next);
      else App.removeFilter(filterKey);
    } else if (active === value) {
      App.removeFilter(filterKey);
    } else {
      App.setFilter(filterKey, value);
    }
    // On a phone the drawer covers the result it just changed.
    App.closeMobileFacets();
  },

  toggleGroup(filterKey) {
    this.expanded[filterKey] = !this.expanded[filterKey];
    if (this._entries) this.render(this._entries);
  },

  _target(ev) {
    return ev.target.closest('.facet-item[data-facet-key]');
  },
};

// Delegated on the document so the sidebar is served by the same handler
// wherever it currently sits, in the page or moved into the mobile drawer.
// The value travels as a data attribute; inside an inline handler it was a JS
// string literal that a quote in the value could end early.
document.addEventListener('click', (ev) => {
  const group = ev.target.closest('[data-facet-toggle]');
  if (group) {
    Facets.toggleOpen(group.dataset.facetToggle);
    return;
  }
  const more = ev.target.closest('[data-facet-more]');
  if (more) {
    Facets.toggleGroup(more.dataset.facetMore);
    return;
  }
  const item = Facets._target(ev);
  if (item) Facets.toggle(item.dataset.facetKey, item.dataset.facetValue);
});

document.addEventListener('keydown', (ev) => {
  if (ev.ctrlKey || ev.metaKey || ev.altKey) return;
  if (ev.key !== 'Enter' && ev.key !== ' ') return;
  const item = Facets._target(ev);
  if (!item) return;
  ev.preventDefault();
  Facets.toggle(item.dataset.facetKey, item.dataset.facetValue);
});

/**
 * Home — Category list, browse CTA, explore link.
 */
const Home = {

  render(entries) {
    const container = document.getElementById('view-home');

    // Count entries per type
    const counts = countByField(entries, 'entryType');

    // Stats
    const languages = new Set(entries.map(e => e.language).filter(Boolean));
    const locations = new Set(entries.map(e => e.location).filter(Boolean));
    const years = entries.map(e => e.year).filter(Boolean);
    const minYear = years.length ? Math.min(...years) : '?';
    const maxYear = years.length ? Math.max(...years) : '?';

    // Build groups HTML
    const groupsHtml = CATEGORY_GROUPS.map(group => {
      const rows = group.types
        .filter(t => counts[t])
        .map(t => this._renderCategoryRow(t, counts[t]))
        .join('');

      if (!rows) return '';
      return `
        <div class="category-section">
          <h2 class="section-heading">${esc(group.heading)}</h2>
          <div class="category-list">${rows}</div>
        </div>
      `;
    }).join('');

    // "Other" types not in any group
    const groupedTypes = new Set(CATEGORY_GROUPS.flatMap(g => g.types));
    const otherTypes = Object.keys(counts).filter(t => !groupedTypes.has(t) && counts[t] > 0);
    let otherHtml = '';
    if (otherTypes.length) {
      const otherRows = otherTypes.map(t =>
        this._renderCategoryRow(t, counts[t])
      ).join('');
      otherHtml = `
        <div class="category-section">
          <h2 class="section-heading">Other</h2>
          <div class="category-list">${otherRows}</div>
        </div>
      `;
    }

    // One-screen layout: intro, search and entry points in the top block,
    // the category groups side by side below. The former stats footer is
    // folded into the intro sentence.
    container.innerHTML = `
      <div class="home-intro home-compact">
        <h1 class="home-title">Stefan Zweig Bibliography</h1>
        <p class="home-subtitle">The Klawiter Bibliography as Open Data</p>
        <p class="home-text">
          ${entries.length.toLocaleString('en')} publications by and about Stefan Zweig,
          from first editions and translations to secondary literature, films and
          correspondence, in ${languages.size} languages and ${locations.size.toLocaleString('en')}
          publication places (${minYear}&ndash;${maxYear}), searchable and
          downloadable as a structured dataset.
        </p>
        <div class="home-search-row">
          <div class="home-search">
            <input type="search" id="home-search-input"
                   aria-label="Search bibliography"
                   value="${esc(App.state.query || '')}"
                   placeholder="Search ${entries.length.toLocaleString('en')} entries\u2026">
            <svg class="home-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
            </svg>
          </div>
          <button class="browse-btn" data-act="browse">Browse Catalogue</button>
        </div>
      </div>

      <div class="home-groups">
        ${groupsHtml}
        ${otherHtml}
      </div>
    `;

    // The start-page field runs the same search as the header field. Two
    // fields with two models (Enter here, live there) taught the visitor that
    // search works differently depending on where they clicked.
    const homeSearch = document.getElementById('home-search-input');
    if (homeSearch) {
      homeSearch.addEventListener('input', (ev) => App.onSearchInput(ev.target.value));
      homeSearch.addEventListener('keydown', (ev) => {
        if (ev.key === 'Enter') {
          ev.preventDefault();
          App.commitSearch(ev.target.value);
        }
      });
    }
  },

  // A category is one plain row: name, count, and a click that opens the
  // filtered list. The former expandable subcategories guessed a
  // "Format (Language)" structure most categories do not have.
  _renderCategoryRow(type, count) {
    const label = ENTRY_TYPE_LABELS[type] || type;
    return `<button type="button" class="category-row"
        data-act="filter-type" data-type="${esc(type)}">
        <span class="category-row-name">${esc(label)}</span>
        <span class="category-row-count">${count.toLocaleString('en')}</span>
      </button>`;
  },

  // One delegated dispatcher for the whole home view. Inline handlers carried
  // the value inside a JS string literal, which broke on category names with
  // an apostrophe: esc() writes &#39; into the attribute, the parser hands the
  // decoded ' back to the handler, and the literal ends early.
  _dispatch(el) {
    const act = el.dataset.act;
    if (act === 'browse') location.hash = 'browse';
    else if (act === 'filter-type') App.setFilter('type', el.dataset.type);
  },
};

// Every control in the home view is a real button, so one click listener is
// the whole keyboard path as well.
document.addEventListener('click', (ev) => {
  const el = ev.target.closest('#view-home [data-act]');
  if (!el) return;
  Home._dispatch(el);
});

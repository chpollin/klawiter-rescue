/**
 * Home — Expandable category list with subcategories, browse CTA, explore link.
 */
const Home = {
  expandedType: null,

  render(entries) {
    const container = document.getElementById('view-home');

    // Count entries per type
    const counts = countByField(entries, 'entryType');

    // Build subcategory tree from categories arrays
    const subcats = this._buildSubcategories(entries);

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
        .map(t => this._renderCategoryRow(t, counts[t], subcats[t]))
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
        this._renderCategoryRow(t, counts[t], subcats[t])
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
        <h1 class="home-title">Stefan Zweig Bibliography
          <span class="home-subtitle-inline">Digital Edition</span></h1>
        <p class="home-text">
          ${entries.length.toLocaleString('en')} publications by and about Stefan Zweig,
          from first editions and translations to secondary literature, films and
          correspondence, in ${languages.size} languages and ${locations.size.toLocaleString('en')}
          publication places (${minYear}&ndash;${maxYear}). Compiled by
          Dr.&nbsp;Randolph&nbsp;J.&nbsp;Klawiter (University of Notre Dame) and published
          here as a searchable, structured open dataset.
        </p>
        <div class="home-search-row">
          <div class="home-search">
            <input type="search" id="home-search-input"
                   placeholder="Search ${entries.length.toLocaleString('en')} entries\u2026 (press Enter)">
            <svg class="home-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
            </svg>
          </div>
          <button class="browse-btn" data-act="browse">Browse Catalogue</button>
          <a href="#stats" class="explore-link">Explore &rarr;</a>
        </div>
      </div>

      <div class="home-groups">
        ${groupsHtml}
        ${otherHtml}
      </div>
    `;

    // Bind home search
    const homeSearch = document.getElementById('home-search-input');
    if (homeSearch) {
      homeSearch.addEventListener('keydown', (ev) => {
        if (ev.key === 'Enter') {
          const q = ev.target.value.trim();
          if (q) location.hash = `q=${encodeURIComponent(q)}`;
        }
      });
    }
  },

  _renderCategoryRow(type, count, subcatData) {
    const label = ENTRY_TYPE_LABELS[type] || type;
    const hasSubcats = subcatData && subcatData.length > 0;
    const chevron = hasSubcats
      ? `<button class="category-expand-btn" data-act="expand" data-type="${esc(type)}" aria-label="Expand ${esc(label)}">
           <svg class="expand-chevron" viewBox="0 0 12 8" fill="none" stroke="currentColor" stroke-width="1.5" width="12" height="8">
             <path d="M1 1.5L6 6.5L11 1.5"/>
           </svg>
         </button>`
      : '';

    const subcatHtml = hasSubcats
      ? `<div class="category-expand" id="subcats-${type}">${this._renderSubcategories(subcatData)}</div>`
      : '';

    return `
      <div class="category-row" id="catrow-${type}">
        <div class="category-row-header">
          <span class="category-row-name" role="button" tabindex="0"
                data-act="filter-type" data-type="${esc(type)}">${esc(label)}</span>
          <span class="category-row-count">${count.toLocaleString('en')}</span>
          ${chevron}
        </div>
        ${subcatHtml}
      </div>
    `;
  },

  _renderSubcategories(subcatData) {
    // Group by format (e.g., "Individual Stories", "Volumes")
    const byFormat = {};
    for (const { format, language, count, fullCategory } of subcatData) {
      if (!byFormat[format]) byFormat[format] = [];
      byFormat[format].push({ language, count, fullCategory });
    }

    return Object.entries(byFormat).map(([format, items]) => {
      // Sort by count descending
      items.sort((a, b) => b.count - a.count);
      const itemsHtml = items.slice(0, 10).map(it =>
        `<span class="subcategory-item" role="button" tabindex="0"
              data-act="filter-category" data-category="${esc(it.fullCategory)}">${esc(it.language)} <span class="subcategory-count">${it.count}</span></span>`
      ).join('');
      const moreCount = items.length - 10;
      const more = moreCount > 0 ? `<span class="subcategory-more">+${moreCount} more</span>` : '';
      return `
        <div class="subcategory-group">
          <span class="subcategory-format">${esc(format)}</span>
          <div class="subcategory-items">${itemsHtml}${more}</div>
        </div>
      `;
    }).join('');
  },

  _buildSubcategories(entries) {
    // Parse "MainCategory / Format (Language)" patterns from categories arrays
    const tree = {}; // entryType -> [{ format, language, count, fullCategory }]

    const catCounts = {};
    for (const e of entries) {
      if (!e.categories) continue;
      for (const cat of e.categories) {
        catCounts[cat] = (catCounts[cat] || 0) + 1;
      }
    }

    // Map entryType labels to match category prefixes
    const typeToPrefix = {};
    for (const [type, label] of Object.entries(ENTRY_TYPE_LABELS)) {
      // "fiction" -> "Fiction", "secondary-literature" -> "Secondary Literature"
      typeToPrefix[type] = label;
    }

    for (const [cat, count] of Object.entries(catCounts)) {
      if (!cat.includes(' / ')) continue;

      const slashPos = cat.indexOf(' / ');
      const prefix = cat.substring(0, slashPos);
      const rest = cat.substring(slashPos + 3);

      // Find which entryType this prefix belongs to
      let matchedType = null;
      for (const [type, label] of Object.entries(ENTRY_TYPE_LABELS)) {
        if (prefix === label || prefix.startsWith(label)) {
          matchedType = type;
          break;
        }
      }
      if (!matchedType) continue;

      // Parse "Format (Language)" from rest
      const parenMatch = rest.match(/^(.+?)\s*\(([^)]+)\)$/);
      let format, language;
      if (parenMatch) {
        format = parenMatch[1].trim();
        language = parenMatch[2].trim();
      } else {
        format = rest.trim();
        language = '';
      }

      if (!tree[matchedType]) tree[matchedType] = [];
      tree[matchedType].push({ format, language: language || format, count, fullCategory: cat });
    }

    return tree;
  },

  toggleExpand(type) {
    const row = document.getElementById(`catrow-${type}`);
    const subcats = document.getElementById(`subcats-${type}`);
    if (!row || !subcats) return;

    if (row.classList.contains('expanded')) {
      row.classList.remove('expanded');
      this.expandedType = null;
    } else {
      // Close any other expanded row
      if (this.expandedType && this.expandedType !== type) {
        const prev = document.getElementById(`catrow-${this.expandedType}`);
        if (prev) prev.classList.remove('expanded');
      }
      row.classList.add('expanded');
      this.expandedType = type;
    }
  },

  // One delegated dispatcher for the whole home view. Inline handlers carried
  // the value inside a JS string literal, which broke on category names with
  // an apostrophe: esc() writes &#39; into the attribute, the parser hands the
  // decoded ' back to the handler, and the literal ends early.
  _dispatch(el) {
    const act = el.dataset.act;
    if (act === 'browse') location.hash = 'browse';
    else if (act === 'expand') this.toggleExpand(el.dataset.type);
    else if (act === 'filter-type') App.setFilter('type', el.dataset.type);
    else if (act === 'filter-category') App.setFilter('category', el.dataset.category);
  },
};

document.addEventListener('click', (ev) => {
  const el = ev.target.closest('#view-home [data-act]');
  // closest() resolves to the innermost target, so the expand button inside a
  // category row no longer needs to stop propagation to its row.
  if (!el) return;
  Home._dispatch(el);
});

document.addEventListener('keydown', (ev) => {
  if (ev.key !== 'Enter' && ev.key !== ' ') return;
  const el = ev.target.closest('#view-home [role="button"][data-act]');
  if (!el) return;
  ev.preventDefault();
  Home._dispatch(el);
});

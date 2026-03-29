/**
 * Startseite — Category portal with tiles grouped by Werke / Rezeption / Editionen.
 */
const Home = {
  // Uses CATEGORY_GROUPS from constants.js

  render(entries) {
    const container = document.getElementById('view-home');

    // Count entries per type
    const counts = {};
    for (const e of entries) {
      if (e.entryType) counts[e.entryType] = (counts[e.entryType] || 0) + 1;
    }

    // Stats
    const languages = new Set(entries.map(e => e.language).filter(Boolean));
    const locations = new Set(entries.map(e => e.location).filter(Boolean));
    const years = entries.map(e => e.year).filter(Boolean);
    const minYear = years.length ? Math.min(...years) : '?';
    const maxYear = years.length ? Math.max(...years) : '?';

    // Build groups HTML
    const groupsHtml = CATEGORY_GROUPS.map(group => {
      const tiles = group.types
        .filter(t => counts[t])
        .map(t => `
          <div class="category-tile" tabindex="0" role="button"
               onclick="App.setFilter('type', '${t}')"
               onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();App.setFilter('type','${t}')}">
            <div class="tile-name">${esc(ENTRY_TYPE_LABELS[t] || t)}</div>
            <div class="tile-count">${(counts[t] || 0).toLocaleString('de-DE')}</div>
          </div>
        `).join('');

      if (!tiles) return '';
      return `
        <div class="category-section">
          <h2 class="section-heading">${esc(group.heading)}</h2>
          <div class="tile-grid">${tiles}</div>
        </div>
      `;
    }).join('');

    // "Other" types not in any group
    const groupedTypes = new Set(CATEGORY_GROUPS.flatMap(g => g.types));
    const otherTypes = Object.keys(counts).filter(t => !groupedTypes.has(t) && counts[t] > 0);
    let otherHtml = '';
    if (otherTypes.length) {
      const otherTiles = otherTypes.map(t => `
        <div class="category-tile" tabindex="0" role="button"
             onclick="App.setFilter('type', '${t}')"
             onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();App.setFilter('type','${t}')}">
          <div class="tile-name">${esc(ENTRY_TYPE_LABELS[t] || t)}</div>
          <div class="tile-count">${counts[t]}</div>
        </div>
      `).join('');
      otherHtml = `
        <div class="category-section">
          <h2 class="section-heading">Other</h2>
          <div class="tile-grid">${otherTiles}</div>
        </div>
      `;
    }

    container.innerHTML = `
      <div class="home-intro">
        <h1 class="home-title">Stefan Zweig Bibliography</h1>
        <h2 class="home-subtitle">(Klawiter)</h2>
        <p class="home-text">
          The Klawiter Bibliography catalogues over ${entries.length.toLocaleString('en')}
          publications by and about Stefan Zweig in ${languages.size} languages.
          Compiled by Dr.&nbsp;Randolph&nbsp;J.&nbsp;Klawiter (University of Notre Dame),
          this digital edition makes the data available as a searchable, structured collection.
        </p>
        <div class="home-search">
          <input type="search" id="home-search-input"
                 placeholder="Search ${entries.length.toLocaleString('en')} entries… (press Enter)">
          <svg class="home-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
          </svg>
        </div>
      </div>

      ${groupsHtml}
      ${otherHtml}

      <div class="home-stats-line">
        ${entries.length.toLocaleString('en')} entries · ${languages.size} languages ·
        ${locations.size} locations · ${minYear}–${maxYear}
        &nbsp;&middot;&nbsp; <a href="#stats">Detailed statistics →</a>
      </div>
    `;

    // Bind home search — navigate only on Enter, not on every keystroke
    const homeSearch = document.getElementById('home-search-input');
    if (homeSearch) {
      homeSearch.addEventListener('keydown', (ev) => {
        if (ev.key === 'Enter') {
          const q = ev.target.value.trim();
          if (q) {
            location.hash = `q=${encodeURIComponent(q)}`;
          }
        }
      });
    }
  },
};

/**
 * Detail view — SZD-style two-column metadata table with conditional sections.
 * Used both for standalone #entry= view and inline expandable cards.
 * Supports provenance badges and edit mode (localhost only).
 */
const Detail = {
  // Standalone detail view (for direct #entry= links)
  render(entry) {
    const container = document.getElementById('detail-content');
    if (!entry) {
      container.innerHTML = '<p style="color:var(--sz-text-light)">Entry not found.</p>';
      return;
    }

    const typeLabel = ENTRY_TYPE_LABELS[entry.entryType] || entry.entryType;
    container.innerHTML = `
      <div class="detail-type">${esc(typeLabel)}</div>
      <h2 class="detail-title">${esc(entry.title || 'Untitled')}</h2>
      ${this._buildContent(entry)}
    `;
  },

  // Inline detail for expandable cards (no type/title header, already shown in card)
  renderInline(entry) {
    return this._buildContent(entry);
  },

  // Provenance badge HTML
  _provBadge(fieldName, entry) {
    const prov = entry._provenance;
    if (!prov || !prov[fieldName]) return '';
    const source = prov[fieldName];
    const labels = { regex: 'R', llm: 'L', missing: '\u2014', expert: 'E' };
    const titles = { regex: 'Regex extracted', llm: 'LLM enriched', missing: 'Missing', expert: 'Expert curated' };
    return `<span class="prov-badge prov-${source}" title="${titles[source] || source}">${labels[source] || source[0].toUpperCase()}</span>`;
  },

  // Editable field wrapper
  _editableValue(fieldName, value, entry) {
    if (!App.state.editMode) return value;
    const pid = entry.sourcePageId;
    const currentVal = value.replace(/<[^>]*>/g, ''); // strip HTML tags for raw text
    return `<span class="editable-field" contenteditable="true"
      data-field="${fieldName}" data-pid="${pid}"
      data-original="${esc(currentVal)}"
      onblur="Edit.trackChange(this)">${value}</span>`;
  },

  // Shared content builder
  _buildContent(entry) {
    let html = '';
    const rows = [];
    const prov = entry._provenance || {};

    // Title (always present, not provenance-tracked)
    rows.push(this.row('Title', esc(entry.title)));

    if (entry.originalTitle && entry.originalTitle !== entry.title) {
      rows.push(this.row('Original Title', esc(entry.originalTitle)));
    }

    if (entry.year) {
      const period = entry.timePeriod ? ` \u2014 ${PERIOD_LABELS[entry.timePeriod] || entry.timePeriod}` : '';
      rows.push(this.row('Year', `${entry.year}${period}`));
    }

    // Provenance-tracked fields
    if (entry.publisher || App.state.editMode) {
      const val = entry.publisher ? esc(entry.publisher) : '<span class="missing-value">not extracted</span>';
      rows.push(this.row('Publisher', this._editableValue('publisher', val, entry), 'publisher', entry));
    }

    if (entry.location || App.state.editMode) {
      let locText = '';
      if (entry.location) {
        locText = esc(entry.location);
        if (entry.allLocations && entry.allLocations.length > 1) {
          locText = entry.allLocations.map(l => esc(l)).join(', ');
        }
      } else {
        locText = '<span class="missing-value">not extracted</span>';
      }
      rows.push(this.row('Location', this._editableValue('location', locText, entry), 'location', entry));
    }

    if (entry.language) {
      const code = entry.languageCode ? ` (${entry.languageCode})` : '';
      rows.push(this.row('Language', esc(entry.language) + code));
    }

    if (entry.pageCount || App.state.editMode) {
      const val = entry.pageCount ? String(entry.pageCount) : '<span class="missing-value">not extracted</span>';
      rows.push(this.row('Pages', this._editableValue('pageCount', val, entry), 'pageCount', entry));
    }

    if (entry.translator || App.state.editMode) {
      const val = entry.translator ? esc(entry.translator) : '<span class="missing-value">not extracted</span>';
      rows.push(this.row('Translator', this._editableValue('translator', val, entry), 'translator', entry));
    }

    if (entry.categories && entry.categories.length) {
      const catLinks = entry.categories.map(c => {
        return `<a href="#type=${encodeURIComponent(entry.entryType)}">${esc(c)}</a>`;
      });
      rows.push(this.row('Categories', catLinks.join(', ')));
    }

    html += `<div class="meta-table">${rows.join('')}</div>`;

    // --- Full bibliographic entry (always visible as verification source) ---
    if (entry.fullBibliographicEntry) {
      html += `
        <div class="detail-section">
          <h3 class="detail-section-heading">Full Bibliographic Entry</h3>
          <div class="detail-bibentry">${esc(entry.fullBibliographicEntry)}</div>
        </div>
      `;
    }

    // --- Reprints ---
    if (entry.reprints && entry.reprints.length) {
      html += `
        <div class="detail-section">
          <h3 class="detail-section-heading">Reprints</h3>
          <ul class="detail-list">
            ${entry.reprints.map(r => `<li>${esc(r)}</li>`).join('')}
          </ul>
        </div>
      `;
    }

    // --- Translations ---
    if (entry.translations && entry.translations.length) {
      html += `
        <div class="detail-section">
          <h3 class="detail-section-heading">Translations</h3>
          <ul class="detail-list">
            ${entry.translations.map(t => `<li>${esc(t)}</li>`).join('')}
          </ul>
        </div>
      `;
    }

    // --- Content items ---
    if (entry.contentItems && entry.contentItems.length) {
      html += `
        <div class="detail-section">
          <h3 class="detail-section-heading">Contents</h3>
          <ol class="detail-list-numbered">
            ${entry.contentItems.map(c => `<li>${esc(c)}</li>`).join('')}
          </ol>
        </div>
      `;
    }

    // --- See also ---
    if (entry.seeAlso && entry.seeAlso.length) {
      const refs = entry.seeAlso.map(ref => this.makeLink(ref));
      html += `
        <div class="detail-section">
          <h3 class="detail-section-heading">See Also</h3>
          <div>${refs.join(', ')}</div>
        </div>
      `;
    }

    // --- Action bar ---
    const pid = entry.sourcePageId;
    html += `
      <div class="action-bar">
        <button class="action-btn" onclick="Export.bibtex(${pid})" title="Export BibTeX">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
          Cite (BibTeX)
        </button>
        <button class="action-btn" onclick="Export.ris(${pid})" title="Export RIS">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          Cite (RIS)
        </button>
        <button class="action-btn" onclick="Export.jsonld(${pid})" title="Download JSON-LD">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          JSON-LD
        </button>
        <button class="action-btn" onclick="Export.permalink(${pid})" data-permalink="${pid}" title="Copy permalink">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
          Permalink
        </button>
      </div>
    `;

    // --- Provenance ---
    html += `<div class="detail-provenance">
      Page ID: ${entry.sourcePageId}
      ${entry.sourceTextId ? ' \u00b7 Text ID: ' + entry.sourceTextId : ''}
      ${entry.sourceBlobId ? ' \u00b7 Blob: ' + entry.sourceBlobId : ''}
    </div>`;

    return html;
  },

  row(label, value, fieldName, entry) {
    const badge = fieldName && entry ? this._provBadge(fieldName, entry) : '';
    return `<div class="meta-row">
      <div class="meta-label">${label}${badge}</div>
      <div class="meta-value">${value}</div>
    </div>`;
  },

  makeLink(title) {
    const entry = App.entries.find(e => e.title === title);
    if (entry) {
      return `<a href="#entry=${entry.sourcePageId}">${esc(title)}</a>`;
    }
    const pid = App.data.redirects[title];
    if (pid) {
      return `<a href="#entry=${pid}">${esc(title)}</a>`;
    }
    return esc(title);
  },
};

/**
 * Detail view — SZD-style two-column metadata table with conditional sections.
 * Used both for standalone #entry= view and inline expandable cards.
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

  // Shared content builder
  _buildContent(entry) {
    let html = '';
    const rows = [];

    rows.push(this.row('Title', esc(entry.title)));

    if (entry.originalTitle && entry.originalTitle !== entry.title) {
      rows.push(this.row('Original Title', esc(entry.originalTitle)));
    }

    if (entry.year) {
      const period = entry.timePeriod ? ` — ${PERIOD_LABELS[entry.timePeriod] || entry.timePeriod}` : '';
      rows.push(this.row('Year', `${entry.year}${period}`));
    }

    if (entry.publisher) {
      rows.push(this.row('Publisher', esc(entry.publisher)));
    }

    if (entry.location) {
      let locText = esc(entry.location);
      if (entry.allLocations && entry.allLocations.length > 1) {
        locText = entry.allLocations.map(l => esc(l)).join(', ');
      }
      rows.push(this.row('Location', locText));
    }

    if (entry.language) {
      const code = entry.languageCode ? ` (${entry.languageCode})` : '';
      rows.push(this.row('Language', esc(entry.language) + code));
    }

    if (entry.pageCount) {
      rows.push(this.row('Pages', entry.pageCount));
    }

    if (entry.translator) {
      rows.push(this.row('Translator', esc(entry.translator)));
    }

    if (entry.categories && entry.categories.length) {
      const catLinks = entry.categories.map(c => {
        return `<a href="#type=${encodeURIComponent(entry.entryType)}">${esc(c)}</a>`;
      });
      rows.push(this.row('Categories', catLinks.join(', ')));
    }

    html += `<div class="meta-table">${rows.join('')}</div>`;

    // --- Full bibliographic entry ---
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
    html += `
      <div class="action-bar">
        <button class="action-btn" onclick="Detail.exportBibtex(${entry.sourcePageId})" title="Export BibTeX">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
          </svg>
          Cite (BibTeX)
        </button>
        <button class="action-btn" onclick="Detail.exportRis(${entry.sourcePageId})" title="Export RIS">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
          Cite (RIS)
        </button>
        <button class="action-btn" onclick="Detail.exportJsonLd(${entry.sourcePageId})" title="Download JSON-LD">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          JSON-LD
        </button>
        <button class="action-btn" onclick="Detail.copyPermalink(${entry.sourcePageId})" title="Copy permalink">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
            <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
          </svg>
          Permalink
        </button>
      </div>
    `;

    // --- Provenance ---
    html += `<div class="detail-provenance">
      Page ID: ${entry.sourcePageId}
      ${entry.sourceTextId ? ' · Text ID: ' + entry.sourceTextId : ''}
      ${entry.sourceBlobId ? ' · Blob: ' + entry.sourceBlobId : ''}
    </div>`;

    return html;
  },

  row(label, value) {
    return `<div class="meta-row">
      <div class="meta-label">${label}</div>
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

  // --- Exports ---
  _getEntry(pageId) {
    return App.entries.find(e => e.sourcePageId === pageId);
  },

  exportBibtex(pageId) {
    const e = this._getEntry(pageId);
    if (!e) return;

    const key = `klawiter${pageId}`;
    const fields = [];
    fields.push(`  author = {Zweig, Stefan}`);
    if (e.title) fields.push(`  title = {${e.title}}`);
    if (e.year) fields.push(`  year = {${e.year}}`);
    if (e.publisher) fields.push(`  publisher = {${e.publisher}}`);
    if (e.location) fields.push(`  address = {${e.location}}`);
    if (e.pageCount) fields.push(`  pages = {${e.pageCount}}`);
    if (e.language) fields.push(`  language = {${e.language}}`);
    if (e.translator) fields.push(`  note = {Translated by ${e.translator}}`);

    const type = (e.entryType === 'essay' || e.entryType === 'newspaper') ? 'article' : 'book';
    const bib = `@${type}{${key},\n${fields.join(',\n')}\n}`;

    this._download(bib, `klawiter-${pageId}.bib`, 'application/x-bibtex');
  },

  exportRis(pageId) {
    const e = this._getEntry(pageId);
    if (!e) return;

    const lines = [];
    const type = (e.entryType === 'essay' || e.entryType === 'newspaper') ? 'JOUR' : 'BOOK';
    lines.push(`TY  - ${type}`);
    if (e.title) lines.push(`TI  - ${e.title}`);
    lines.push(`AU  - Zweig, Stefan`);
    if (e.year) lines.push(`PY  - ${e.year}`);
    if (e.publisher) lines.push(`PB  - ${e.publisher}`);
    if (e.location) lines.push(`CY  - ${e.location}`);
    if (e.language) lines.push(`LA  - ${e.language}`);
    if (e.translator) lines.push(`A2  - ${e.translator}`);
    if (e.pageCount) lines.push(`SP  - ${e.pageCount}`);
    lines.push(`ER  -`);

    this._download(lines.join('\n'), `klawiter-${pageId}.ris`, 'application/x-research-info-systems');
  },

  exportJsonLd(pageId) {
    const e = this._getEntry(pageId);
    if (!e) return;
    const jsonld = {
      '@context': { 'klawiter': 'https://klawiter-rescue.github.io/vocab/' },
      '@type': e['@type'] || `klawiter:${e.entryType}Entry`,
      '@id': e['@id'] || `klawiter:entry/${pageId}`,
    };
    for (const [k, v] of Object.entries(e)) {
      if (!k.startsWith('@') && v != null) {
        jsonld[`klawiter:${k}`] = v;
      }
    }
    this._download(
      JSON.stringify(jsonld, null, 2),
      `klawiter-${pageId}.jsonld`,
      'application/ld+json'
    );
  },

  copyPermalink(pageId) {
    const url = `${location.origin}${location.pathname}#entry=${pageId}`;
    navigator.clipboard.writeText(url).then(() => {
      const btn = document.querySelector('.action-btn[title="Permalink kopieren"]');
      if (btn) {
        const orig = btn.innerHTML;
        btn.innerHTML = '✓ Copied';
        setTimeout(() => { btn.innerHTML = orig; }, 2000);
      }
    });
  },

  _download(content, filename, type) {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  },
};

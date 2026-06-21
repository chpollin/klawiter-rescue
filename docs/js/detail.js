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

  // Provenance badge HTML. A pending editor action overrides the machine
  // provenance so the badge reflects the human verdict before it is saved.
  _provBadge(fieldName, entry) {
    const pid = entry.sourcePageId;
    const pend = App.state.editMode ? Edit.pending(pid, fieldName) : undefined;
    let source;
    if (pend) {
      source = 'editor';
    } else {
      const prov = entry._provenance;
      if (!prov || !prov[fieldName]) return '';
      source = prov[fieldName];
    }
    const labels = { regex: 'R', llm: 'L', missing: '\u2014', editor: 'E', expert: 'E' };
    const titles = { regex: 'Regex extracted', llm: 'LLM enriched', missing: 'Missing',
                     editor: 'Expert curated', expert: 'Expert curated' };
    const cls = source === 'expert' ? 'editor' : source;   // unify legacy "expert" onto "editor"
    return `<span class="prov-badge prov-${cls}" title="${titles[source] || source}">${labels[source] || source[0].toUpperCase()}</span>`;
  },

  // Three-status review chip (Ungepr\u00fcft / Agent-gepr\u00fcft / Mensch-gepr\u00fcft).
  _reviewChip(entry) {
    const st = Edit.entryStatus(entry.sourcePageId);
    const map = {
      unreviewed: { label: 'Ungepr\u00fcft', cls: 'review-unreviewed' },
      agent_verified: { label: 'Agent-gepr\u00fcft', cls: 'review-agent' },
      approved: { label: 'Mensch-gepr\u00fcft', cls: 'review-approved' },
    };
    const m = map[st.status] || map.unreviewed;
    const note = st.pending ? ' <span class="review-pending">ungespeichert</span>' : '';
    return `<div class="review-chip ${m.cls}">${m.label}${note}</div>`;
  },

  // Editable cell for a provenance-tracked field (edit mode only). An empty
  // field shows a placeholder so typing into it is recorded as Add, not Correct.
  _editableValue(fieldName, entry) {
    const pid = entry.sourcePageId;
    const raw = entry[fieldName];
    const has = raw != null && raw !== '';
    const original = has ? String(raw) : '';
    const ph = has ? '' : ' data-placeholder="add value\u2026"';
    return `<span class="editable-field${has ? '' : ' editable-empty'}" contenteditable="true"
      data-field="${fieldName}" data-pid="${pid}"
      data-original="${esc(original)}"${ph}
      onblur="Edit.trackChange(this)">${has ? esc(original) : ''}</span>`;
  },

  // Per-field action controls: Accept on a present value, Undo on a pending one.
  _fieldControls(fieldName, entry) {
    const pid = entry.sourcePageId;
    const pend = Edit.pending(pid, fieldName);
    const has = entry[fieldName] != null && entry[fieldName] !== '';
    let inner = '';
    if (pend) {
      inner += `<span class="field-action field-action-${pend.action}">${pend.action}</span>`;
      inner += `<button class="field-btn field-revert" title="Undo" onclick="Edit.revert(${pid}, '${fieldName}')">\u21ba</button>`;
    } else if (has) {
      inner += `<button class="field-btn field-accept" title="Accept this value" onclick="Edit.accept(${pid}, '${fieldName}')">\u2713</button>`;
    }
    return inner ? ` <span class="field-controls">${inner}</span>` : '';
  },

  // Build the edit-mode cell (editable value + action controls) for a tracked field.
  _editCell(fieldName, entry) {
    return this._editableValue(fieldName, entry) + this._fieldControls(fieldName, entry);
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
      let cell;
      if (App.state.editMode) {
        cell = this._editCell('publisher', entry);
      } else {
        cell = entry.publisher ? esc(entry.publisher) : '<span class="missing-value">not extracted</span>';
      }
      rows.push(this.row('Publisher', cell, 'publisher', entry));
    }

    if (entry.location || App.state.editMode) {
      let cell;
      if (App.state.editMode) {
        // Only the primary location is editable; allLocations is a separate map facet.
        cell = this._editCell('location', entry);
      } else {
        let locText = esc(entry.location);
        if (entry.allLocations && entry.allLocations.length > 1) {
          locText = entry.allLocations.map(l => esc(l)).join(', ');
        }
        // Wikidata link for the primary location (klawiter:locationSameAs).
        if (entry.location && entry.locationSameAs) {
          locText += ` <a class="wikidata-link" href="${esc(entry.locationSameAs)}" target="_blank" rel="noopener" title="View ${esc(entry.location)} on Wikidata">Wikidata</a>`;
        }
        cell = locText;
      }
      rows.push(this.row('Location', cell, 'location', entry));
    }

    if (entry.language) {
      const code = entry.languageCode ? ` (${entry.languageCode})` : '';
      rows.push(this.row('Language', esc(entry.language) + code));
    }

    if (entry.pageCount || App.state.editMode) {
      const cell = App.state.editMode
        ? this._editCell('pageCount', entry)
        : (entry.pageCount ? String(entry.pageCount) : '<span class="missing-value">not extracted</span>');
      rows.push(this.row('Pages', cell, 'pageCount', entry));
    }

    if (entry.translator || App.state.editMode) {
      const cell = App.state.editMode
        ? this._editCell('translator', entry)
        : (entry.translator ? esc(entry.translator) : '<span class="missing-value">not extracted</span>');
      rows.push(this.row('Translator', cell, 'translator', entry));
    }

    if (entry.categories && entry.categories.length) {
      const catLinks = entry.categories.map(c => {
        return `<a href="#type=${encodeURIComponent(entry.entryType)}">${esc(c)}</a>`;
      });
      rows.push(this.row('Categories', catLinks.join(', ')));
    }

    if (App.state.editMode) html = this._reviewChip(entry) + html;
    html += `<div class="meta-table">${rows.join('')}</div>`;

    // --- Full bibliographic entry (always visible as verification source) ---
    // In edit mode this is the adjudication source: the editor checks each field
    // against it. Per-field raw-wiki segmentation is a later increment.
    if (entry.fullBibliographicEntry) {
      const evidence = App.state.editMode;
      html += `
        <div class="detail-section${evidence ? ' detail-evidence' : ''}">
          <h3 class="detail-section-heading">${evidence ? 'Source — verify each field against this' : 'Full Bibliographic Entry'}</h3>
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
    const pid = App.titleMap.get(title) || (App.data.redirects && App.data.redirects[title]);
    if (pid) return `<a href="#entry=${pid}">${esc(title)}</a>`;
    return esc(title);
  },
};

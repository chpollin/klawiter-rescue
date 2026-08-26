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

  // Marker on a field a verify.py flag points at (rank 0-2 triage hint).
  // Provenance-class hints carry no extra marker: the provenance badge
  // already says llm / missing on the same row.
  _triageFlag(fieldName, entry) {
    const hint = Edit.triageHints(entry).find(h => h.field === fieldName && h.rank <= 2);
    if (!hint) return '';
    const detail = hint.detail ? `: ${String(hint.detail).replace(/\s+/g, ' ')}` : '';
    return ` <span class="triage-flag" title="${esc(hint.label + detail)}">!</span>`;
  },

  // Source evidence beside a tracked field (increment 3): the passage of the
  // entry source holding the value, or \u2014 when no field-precise span is
  // derivable \u2014 the whole source text, collapsible. The fallback is the
  // honest variant: it does not pretend to a segmentation it cannot derive.
  _fieldEvidence(fieldName, entry) {
    const ev = Edit.evidence(entry, fieldName);
    if (ev) {
      const multi = ev.count > 1
        ? ` <span class="evidence-count" title="Der Wert kommt mehrfach im Quelltext vor; bei Multi-Edition-Seiten kann der Ausschnitt aus einem anderen Editionsblock stammen.">${ev.count} Fundstellen</span>`
        : '';
      return `<div class="field-evidence">${esc(ev.before)}<mark>${esc(ev.match)}</mark>${esc(ev.after)}${multi}</div>`;
    }
    if (!entry.fullBibliographicEntry) return '';
    return `<details class="field-evidence-fallback">
      <summary>Kein feldgenauer Ausschnitt ableitbar \u2014 ganzer Quelltext</summary>
      <div class="field-evidence-full">${esc(entry.fullBibliographicEntry)}</div>
    </details>`;
  },

  // Build the edit-mode cell (editable value + controls + source evidence).
  _editCell(fieldName, entry) {
    return this._editableValue(fieldName, entry)
      + this._triageFlag(fieldName, entry)
      + this._fieldControls(fieldName, entry)
      + this._fieldEvidence(fieldName, entry);
  },

  _reconciliationCell(entry) {
    const review = Edit.locationReconciliation(entry);
    if (!review) return '<span class="missing-value">No reconciliation record</span>';
    const pending = Edit.pendingLocationDecision(entry.sourcePageId);
    const decision = pending || review.decision;
    const status = pending
      ? 'pending editor decision'
      : (decision ? decision.action : 'proposal only');
    const published = review.publishable
      ? ` <a class="wikidata-link" href="${esc(review.publishable.uri)}" target="_blank" rel="noopener">published link</a>`
      : '';
    const candidates = (review.candidates || []).map(candidate => {
      const score = candidate.score == null ? '' : `, score ${candidate.score}`;
      return `<li><a href="${esc(candidate.uri)}" target="_blank" rel="noopener">${esc(candidate.label)} (${esc(candidate.qid)})</a>${score}
        <button class="reconciliation-btn" onclick="Edit.decideLocation(${entry.sourcePageId}, 'confirm', '${candidate.qid}')">Confirm</button></li>`;
    }).join('');
    const revert = pending
      ? `<button class="reconciliation-btn" onclick="Edit.revertLocationDecision(${entry.sourcePageId})">Undo pending</button>`
      : '';
    return `<div class="reconciliation-block">
      <div><strong>${esc(status)}</strong>${published}</div>
      ${candidates ? `<ul>${candidates}</ul>` : '<div>No candidate available.</div>'}
      <div class="reconciliation-actions">
        <button class="reconciliation-btn" onclick="Edit.decideLocation(${entry.sourcePageId}, 'reject')">Reject candidates</button>
        <button class="reconciliation-btn" onclick="Edit.decideLocation(${entry.sourcePageId}, 'unresolved')">Keep unresolved</button>
        ${revert}
      </div>
    </div>`;
  },

  _contestedAuthorityCell(entry) {
    const claims = Edit.authorityClaimsFor(entry);
    if (!claims.length) return '';
    const rendered = claims.map(claim => {
      const interpretations = (claim.interpretations || []).map(item => {
        const proposedObject = item.proposedObject && item.proposedObject['@id'];
        const object = proposedObject
          ? `<br><code>${esc(proposedObject)}</code>`
          : '<br><span>Keine Normdatenzuordnung</span>';
        return `<li><strong>${esc(item.label)}</strong>${object}</li>`;
      }).join('');
      const evidence = (claim.sourceEvidence || []).map(item =>
        `<li>Seite ${esc(item.sourcePageId)}, Zeile ${esc(item.sourceLine)}: ${esc(item.sourceValue)}<br>SHA-256 <code>${esc(item.sourceTextSha256)}</code></li>`
      ).join('');
      const history = (claim.reviewHistory || []).map(item =>
        `<li><code>${esc(item.decidedBy)}</code>: ${esc(item.action)} — <code>${esc(item.decisionId)}</code></li>`
      ).join('');
      return `<article class="contested-claim">
        <div class="contested-claim-heading">Strittige Normdatenzuordnung — Entscheidung offen</div>
        <div class="contested-claim-id"><code>${esc(claim['@id'])}</code></div>
        <p>Die Aussage bleibt Bestandteil der Daten. Keine Deutung wird als bestätigte <code>schema:sameAs</code>-Beziehung ausgegeben.</p>
        <h4>Konkurrierende Deutungen</h4>
        <ul>${interpretations}</ul>
        <h4>Quellenbelege</h4>
        <ul>${evidence}</ul>
        <h4>Prüfverlauf</h4>
        <ul>${history}</ul>
      </article>`;
    }).join('');
    return `<div class="contested-status" role="status">${rendered}</div>`;
  },

  _contestedClaimsBlock(entry) {
    const claims = Edit.editionClaimsFor(entry);
    if (!claims.length) return '';
    const rendered = claims.map(claim => {
      const interpretations = claim.interpretations.map(item =>
        `<li><strong>${esc(item.label)}</strong><br><span>${esc(item.basis)}</span><br><code>${esc(item.proposedObject)}</code></li>`
      ).join('');
      const history = claim.reviewHistory.map(item =>
        `<li><code>${esc(item.reviewer)}</code>: ${esc(item.outcome)}${item.basis ? ` — ${esc(item.basis)}` : ''}</li>`
      ).join('');
      return `<article class="contested-claim">
        <div class="contested-claim-heading">Strittige Werksbindung — Entscheidung offen</div>
        <div class="contested-claim-id"><code>${esc(claim.claimId)}</code></div>
        <p>Die Edition bleibt Bestandteil der Daten. Keine der folgenden Deutungen wird als bestätigte <code>schema:exampleOfWork</code>-Beziehung ausgegeben.</p>
        <h4>Konkurrierende Deutungen</h4>
        <ul>${interpretations}</ul>
        <h4>Prüfverlauf</h4>
        <ul>${history}</ul>
        <div class="contested-source">Quelle: Seite ${claim.source.sourcePageId}, Zeichen ${claim.source.selector[0]}–${claim.source.selector[1]}; SHA-256 <code>${esc(claim.source.sliceSha256)}</code></div>
      </article>`;
    }).join('');
    return `<section class="detail-section contested-claims" aria-label="Strittige Aussagen">${rendered}</section>`;
  },

  // Ordered attention hints for the entry (edit mode): where checking is most
  // urgent, by data signal. A priority aid, not a quality or workflow score.
  _triageBlock(entry) {
    const hints = Edit.triageHints(entry);
    if (!hints.length) return '';
    const items = hints.map(h => {
      const field = h.field ? `<strong>${esc(Edit.FIELD_LABELS[h.field] || h.field)}</strong> \u2014 ` : '';
      const detail = h.detail
        ? `: <span class="triage-detail">${esc(String(h.detail).replace(/\s+/g, ' ').slice(0, 80))}</span>`
        : '';
      return `<li class="triage-rank-${h.rank}">${field}${esc(h.label)}${detail}</li>`;
    });
    return `<div class="triage-hints">
      <div class="triage-hints-head" title="Priorit\u00e4tshilfe aus vorhandenen Datensignalen (Provenienz-Schicht, Verifikations-Flags, Census). Kein Qualit\u00e4ts- oder Wirksamkeitsma\u00df.">Pr\u00fcfhinweise</div>
      <ul>${items.join('')}</ul>
    </div>`;
  },

  // Shared content builder
  _buildContent(entry) {
    let html = '';
    const rows = [];
    const prov = entry._provenance || {};
    const contestedAuthority = this._contestedAuthorityCell(entry);

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
      if (App.state.editMode && entry.location) {
        rows.push(this.row('Authority reconciliation', this._reconciliationCell(entry)));
      }
    }

    if (contestedAuthority) {
      rows.push(this.row('Normdatenstatus', contestedAuthority));
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

    if (App.state.editMode) html = this._reviewChip(entry) + this._triageBlock(entry) + html;
    html += `<div class="meta-table">${rows.join('')}</div>`;
    html += this._contestedClaimsBlock(entry);

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

/**
 * Detail view — expanded entry content for the result cards and #entry= links.
 *
 * Two layouts, one per audience: the read layout is compact (the collapsed
 * card header already shows type, title, year, publisher, location, language
 * and page count, so the expansion adds only what the header does not carry
 * and the structured content sections); the edit layout (localhost EIL mode)
 * keeps the full field table with provenance badges, evidence snippets and
 * authority candidate blocks, because there every field is an adjudication
 * surface.
 */
const Detail = {
  renderInline(entry) {
    return App.state.editMode
      ? this._buildEditContent(entry)
      : this._buildReadContent(entry);
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
    const labels = { regex: 'R', llm: 'L', missing: '—', editor: 'E', expert: 'E' };
    const titles = { regex: 'Regex extracted', llm: 'LLM enriched', missing: 'Missing',
                     editor: 'Expert curated', expert: 'Expert curated' };
    const cls = source === 'expert' ? 'editor' : source;   // unify legacy "expert" onto "editor"
    return `<span class="prov-badge prov-${cls}" title="${titles[source] || source}">${labels[source] || source[0].toUpperCase()}</span>`;
  },

  // Review chip: the dataset projection (entry.review, built by the pipeline
  // from decided reconciliation subjects and applied patches) layered under
  // the live session state, which wins because it is newer.
  _reviewChip(entry) {
    const map = {
      unreviewed: { label: 'Unreviewed', cls: 'review-unreviewed' },
      agent_verified: { label: 'Agent-verified', cls: 'review-agent' },
      contested: { label: 'Contested', cls: 'review-contested' },
      approved: { label: 'Expert-reviewed', cls: 'review-approved' },
    };
    const st = Edit.entryStatus(entry.sourcePageId);
    const dataset = entry.review && entry.review.status;
    const status = st.pending ? st.status : (dataset || 'unreviewed');
    const m = map[status] || map.unreviewed;
    const by = !st.pending && dataset && entry.review.reviewed_by
      ? ` title="Decided by ${esc(entry.review.reviewed_by)}"`
      : '';
    const note = st.pending ? ' <span class="review-pending">unsaved</span>' : '';
    return `<div class="review-chip ${m.cls}"${by}>${m.label}${note}</div>`;
  },

  // Editable cell for a provenance-tracked field (edit mode only). An empty
  // field shows a placeholder so typing into it is recorded as Add, not Correct.
  _editableValue(fieldName, entry) {
    const pid = entry.sourcePageId;
    const raw = entry[fieldName];
    const has = raw != null && raw !== '';
    const original = has ? String(raw) : '';
    const ph = has ? '' : ' data-placeholder="add value…"';
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
      inner += `<button class="field-btn field-revert" title="Undo" onclick="Edit.revert(${pid}, '${fieldName}')">↺</button>`;
    } else if (has) {
      inner += `<button class="field-btn field-accept" title="Accept this value" onclick="Edit.accept(${pid}, '${fieldName}')">✓</button>`;
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
  // entry source holding the value, or — when no field-precise span is
  // derivable — the whole source text, collapsible. The fallback is the
  // honest variant: it does not pretend to a segmentation it cannot derive.
  _fieldEvidence(fieldName, entry) {
    const ev = Edit.evidence(entry, fieldName);
    if (ev) {
      const multi = ev.count > 1
        ? ` <span class="evidence-count" title="The value occurs more than once in the source; on multi-edition pages the excerpt can come from a different edition block.">${ev.count} occurrences</span>`
        : '';
      return `<div class="field-evidence">${esc(ev.before)}<mark>${esc(ev.match)}</mark>${esc(ev.after)}${multi}</div>`;
    }
    if (!entry.fullBibliographicEntry) return '';
    return `<details class="field-evidence-fallback">
      <summary>No field-precise excerpt derivable — full source text</summary>
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

  // How many displayed entries a subject-level authority decision covers.
  _subjectReach(count) {
    if (!count || count < 2) return '';
    return ` <span class="subject-reach" title="A decision on this name applies to every entry carrying it.">applies to ${count} entries</span>`;
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
    const reach = this._subjectReach(
      App.entries.filter(e => e.location === entry.location).length
    );
    const candidates = (review.candidates || []).map(candidate => {
      const score = candidate.score == null ? '' : `, score ${candidate.score}`;
      return `<li><a href="${esc(candidate.uri)}" target="_blank" rel="noopener">${esc(candidate.label)} (${esc(candidate.qid)})</a>${score}
        <button class="reconciliation-btn" onclick="Edit.decideLocation(${entry.sourcePageId}, 'confirm', '${candidate.qid}')">Confirm</button></li>`;
    }).join('');
    const revert = pending
      ? `<button class="reconciliation-btn" onclick="Edit.revertLocationDecision(${entry.sourcePageId})">Undo pending</button>`
      : '';
    return `<div class="reconciliation-block">
      <div><strong>${esc(status)}</strong>${published}${reach}</div>
      ${candidates ? `<ul>${candidates}</ul>` : '<div>No candidate available.</div>'}
      <div class="reconciliation-actions">
        <button class="reconciliation-btn" onclick="Edit.decideLocation(${entry.sourcePageId}, 'reject')">Reject candidates</button>
        <button class="reconciliation-btn" onclick="Edit.decideLocation(${entry.sourcePageId}, 'unresolved')">Keep unresolved</button>
        ${revert}
      </div>
    </div>`;
  },

  // Candidate block for translator (kind 'person') and publisher names,
  // reusing the location pattern. "Keep unresolved" is available because
  // every agent subject now carries source occurrences, which the pipeline
  // requires as the evidence behind an unresolved decision.
  _agentReconciliationCell(entry, kind) {
    const review = Edit.agentReconciliation(entry, kind);
    if (!review) return '<span class="missing-value">No candidate record (below occurrence threshold)</span>';
    const name = review.name;
    const pending = Edit.pendingAgentDecision(kind, name);
    const decision = pending || review.decision;
    const status = pending
      ? 'pending editor decision'
      : (decision ? decision.action : 'proposal only');
    const published = review.publishable
      ? ` <a class="wikidata-link" href="${esc(review.publishable.uri)}" target="_blank" rel="noopener">published link</a>`
      : '';
    const reach = this._subjectReach(review.occurrences);
    const candidates = (review.candidates || []).map(candidate => {
      const score = candidate.score == null ? '' : `, score ${candidate.score}`;
      return `<li><a href="${esc(candidate.uri)}" target="_blank" rel="noopener">${esc(candidate.label)} (${esc(candidate.qid)})</a>${score}
        <button class="reconciliation-btn" onclick="Edit.decideAgent(${entry.sourcePageId}, '${kind}', 'confirm', '${candidate.qid}')">Confirm</button></li>`;
    }).join('');
    const revert = pending
      ? `<button class="reconciliation-btn" onclick="Edit.revertAgentDecision(${entry.sourcePageId}, '${kind}')">Undo pending</button>`
      : '';
    return `<div class="reconciliation-block">
      <div><strong>${esc(status)}</strong>${published}${reach}</div>
      ${candidates ? `<ul>${candidates}</ul>` : '<div>No candidate available.</div>'}
      <div class="reconciliation-actions">
        <button class="reconciliation-btn" onclick="Edit.decideAgent(${entry.sourcePageId}, '${kind}', 'reject')">Reject candidates</button>
        <button class="reconciliation-btn" onclick="Edit.decideAgent(${entry.sourcePageId}, '${kind}', 'unresolved')">Keep unresolved</button>
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
          : '<br><span>No authority assignment</span>';
        return `<li><strong>${esc(item.label)}</strong>${object}</li>`;
      }).join('');
      const evidence = (claim.sourceEvidence || []).map(item =>
        `<li>Page ${esc(item.sourcePageId)}, line ${esc(item.sourceLine)}: ${esc(item.sourceValue)}<br>SHA-256 <code>${esc(item.sourceTextSha256)}</code></li>`
      ).join('');
      const history = (claim.reviewHistory || []).map(item =>
        `<li><code>${esc(item.decidedBy)}</code>: ${esc(item.action)} — <code>${esc(item.decisionId)}</code></li>`
      ).join('');
      return `<article class="contested-claim">
        <div class="contested-claim-heading">Contested authority assignment — decision open</div>
        <div class="contested-claim-id"><code>${esc(claim.claimId)}</code></div>
        <p>The claim stays part of the data. No interpretation is emitted as a confirmed <code>schema:sameAs</code> relation.</p>
        <h4>Competing interpretations</h4>
        <ul>${interpretations}</ul>
        <h4>Source evidence</h4>
        <ul>${evidence}</ul>
        <h4>Review history</h4>
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
        <div class="contested-claim-heading">Contested work identity — decision open</div>
        <div class="contested-claim-id"><code>${esc(claim.claimId)}</code></div>
        <p>The edition stays part of the data. None of the following interpretations is emitted as a confirmed <code>schema:exampleOfWork</code> relation.</p>
        <h4>Competing interpretations</h4>
        <ul>${interpretations}</ul>
        <h4>Review history</h4>
        <ul>${history}</ul>
        <div class="contested-source">Source: page ${claim.source.sourcePageId}, characters ${claim.source.selector[0]}–${claim.source.selector[1]}; SHA-256 <code>${esc(claim.source.sliceSha256)}</code></div>
      </article>`;
    }).join('');
    return `<section class="detail-section contested-claims" aria-label="Contested claims">${rendered}</section>`;
  },

  // Ordered attention hints for the entry (edit mode): where checking is most
  // urgent, by data signal. A priority aid, not a quality or workflow score.
  _triageBlock(entry) {
    const hints = Edit.triageHints(entry);
    if (!hints.length) return '';
    const items = hints.map(h => {
      const field = h.field ? `<strong>${esc(Edit.FIELD_LABELS[h.field] || h.field)}</strong> — ` : '';
      const detail = h.detail
        ? `: <span class="triage-detail">${esc(String(h.detail).replace(/\s+/g, ' ').slice(0, 80))}</span>`
        : '';
      return `<li class="triage-rank-${h.rank}">${field}${esc(h.label)}${detail}</li>`;
    });
    return `<div class="triage-hints">
      <div class="triage-hints-head" title="Priority aid from existing data signals (provenance layer, verification flags, census). Not a quality measure.">Review hints</div>
      <ul>${items.join('')}</ul>
    </div>`;
  },

  // ---------------------------------------------------------------------------
  // Read layout — one information level per block, nothing the card header
  // already shows is repeated.
  // ---------------------------------------------------------------------------

  _buildReadContent(entry) {
    let html = '';

    // Inline meta: only what the collapsed header does not carry.
    const meta = [];
    if (entry.originalTitle && entry.originalTitle !== entry.title) {
      meta.push(`<span class="inline-meta-item"><span class="inline-meta-label">Original title</span> <span${titleAttrs(entry, entry.originalTitle)}>${esc(entry.originalTitle)}</span></span>`);
    }
    if (entry.translator) {
      meta.push(`<span class="inline-meta-item"><span class="inline-meta-label">Translator</span> ${esc(entry.translator)}</span>`);
    }
    if (entry.allLocations && entry.allLocations.length > 1) {
      meta.push(`<span class="inline-meta-item"><span class="inline-meta-label">Locations</span> ${entry.allLocations.map(l => esc(l)).join(', ')}</span>`);
    }
    if (entry.location && entry.locationSameAs) {
      meta.push(`<span class="inline-meta-item"><a class="wikidata-link" href="${esc(entry.locationSameAs)}" target="_blank" rel="noopener" title="View ${esc(entry.location)} on Wikidata">${esc(entry.location)} on Wikidata</a></span>`);
    }
    if (entry.categories && entry.categories.length) {
      const catLinks = entry.categories.map(c =>
        `<a href="#type=${encodeURIComponent(entry.entryType)}">${esc(c)}</a>`);
      meta.push(`<span class="inline-meta-item"><span class="inline-meta-label">Categories</span> ${catLinks.join(', ')}</span>`);
    }
    if (meta.length) html += `<div class="detail-inline-meta">${meta.join('')}</div>`;

    // Contested claims stay visible to every reader: openness is part of the
    // published data, not an edit-mode extra.
    const contestedAuthority = this._contestedAuthorityCell(entry);
    if (contestedAuthority) html += contestedAuthority;
    html += this._contestedClaimsBlock(entry);

    // Structured contents before the raw source: the parsed view is the
    // reading format, the Klawiter original below is the provenance record.
    if (entry.contentItems && entry.contentItems.length) {
      html += `
        <div class="detail-section">
          <h3 class="detail-section-heading">Contents (${entry.contentItems.length})</h3>
          <ol class="detail-list-numbered detail-contents">
            ${entry.contentItems.map(c => this._contentItem(c)).join('')}
          </ol>
        </div>
      `;
    }

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

    if (entry.seeAlso && entry.seeAlso.length) {
      const refs = entry.seeAlso.map(ref => this.makeLink(ref));
      html += `
        <div class="detail-section">
          <h3 class="detail-section-heading">See Also</h3>
          <div>${refs.join(', ')}</div>
        </div>
      `;
    }

    // The full Klawiter entry is the source record: kept complete, collapsed.
    if (entry.fullBibliographicEntry) {
      html += `
        <details class="detail-source-details">
          <summary>Full bibliographic entry (Klawiter source)</summary>
          <div class="detail-bibentry">${esc(entry.fullBibliographicEntry)}</div>
        </details>
      `;
    }

    html += this._actionBar(entry);
    html += this._provenanceLine(entry);
    return html;
  },

  // Split a trailing page reference off a contents item for aligned display.
  _contentItem(text) {
    const m = /^(.*?)[,.]?\s*(pp?\.\s*[\d\s()\/\-–.]+[a-z]?)\s*$/i.exec(text);
    if (m && m[1]) {
      return `<li><span class="content-item-title">${esc(m[1])}</span><span class="content-item-pages">${esc(m[2])}</span></li>`;
    }
    return `<li>${esc(text)}</li>`;
  },

  // ---------------------------------------------------------------------------
  // Edit layout — the full adjudication table (localhost EIL mode).
  // ---------------------------------------------------------------------------

  _buildEditContent(entry) {
    let html = '';
    const rows = [];
    const contestedAuthority = this._contestedAuthorityCell(entry);

    rows.push(this.row('Title', `<span${titleAttrs(entry, entry.title)}>${esc(entry.title)}</span>`));

    if (entry.originalTitle && entry.originalTitle !== entry.title) {
      rows.push(this.row('Original title',
        `<span${titleAttrs(entry, entry.originalTitle)}>${esc(entry.originalTitle)}</span>`));
    }

    if (entry.year) {
      const period = entry.timePeriod ? ` — ${PERIOD_LABELS[entry.timePeriod] || entry.timePeriod}` : '';
      rows.push(this.row('Year', `${entry.year}${period}`));
    }

    rows.push(this.row('Publisher', this._editCell('publisher', entry), 'publisher', entry));
    if (entry.publisher) {
      rows.push(this.row('Authority candidates', this._agentReconciliationCell(entry, 'publisher')));
    }

    rows.push(this.row('Location', this._editCell('location', entry), 'location', entry));
    if (entry.location) {
      rows.push(this.row('Authority candidates', this._reconciliationCell(entry)));
    }

    if (contestedAuthority) {
      rows.push(this.row('Authority status', contestedAuthority));
    }

    if (entry.language) {
      const code = entry.languageCode ? ` (${entry.languageCode})` : '';
      rows.push(this.row('Language', esc(entry.language) + code));
    }

    rows.push(this.row('Pages', this._editCell('pageCount', entry), 'pageCount', entry));

    rows.push(this.row('Translator', this._editCell('translator', entry), 'translator', entry));
    if (entry.translator) {
      rows.push(this.row('Authority candidates', this._agentReconciliationCell(entry, 'person')));
    }

    if (entry.categories && entry.categories.length) {
      const catLinks = entry.categories.map(c =>
        `<a href="#type=${encodeURIComponent(entry.entryType)}">${esc(c)}</a>`);
      rows.push(this.row('Categories', catLinks.join(', ')));
    }

    html += this._reviewChip(entry) + this._triageBlock(entry);
    html += `<div class="prov-legend" title="Field provenance">
      <span class="prov-badge prov-regex">R</span> regex-extracted
      <span class="prov-badge prov-llm">L</span> LLM-enriched
      <span class="prov-badge prov-editor">E</span> expert-curated
      <span class="prov-badge prov-missing">—</span> missing
    </div>`;
    html += `<div class="meta-table">${rows.join('')}</div>`;
    html += this._contestedClaimsBlock(entry);

    // In edit mode the source is the adjudication reference: kept open.
    if (entry.fullBibliographicEntry) {
      html += `
        <div class="detail-section detail-evidence">
          <h3 class="detail-section-heading">Source — verify each field against this</h3>
          <div class="detail-bibentry">${esc(entry.fullBibliographicEntry)}</div>
        </div>
      `;
    }

    if (entry.seeAlso && entry.seeAlso.length) {
      const refs = entry.seeAlso.map(ref => this.makeLink(ref));
      html += `
        <div class="detail-section">
          <h3 class="detail-section-heading">See Also</h3>
          <div>${refs.join(', ')}</div>
        </div>
      `;
    }

    html += this._actionBar(entry);
    html += this._provenanceLine(entry);
    return html;
  },

  // ---------------------------------------------------------------------------
  // Shared building blocks
  // ---------------------------------------------------------------------------

  _actionBar(entry) {
    const pid = entry.sourcePageId;
    return `
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
  },

  _provenanceLine(entry) {
    return `<div class="detail-provenance">
      Page ID: ${entry.sourcePageId}
      ${entry.sourceTextId ? ' · Text ID: ' + entry.sourceTextId : ''}
      ${entry.sourceBlobId ? ' · Blob: ' + entry.sourceBlobId : ''}
    </div>`;
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

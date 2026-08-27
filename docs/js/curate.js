/**
 * Data-quality workbench (#quality) — the curation-facing exploration view.
 *
 * Turns the evidence the pipeline already publishes (triage.json,
 * reconciliation.json, the provenance layer inside klawiter.json) into
 * actionable lists: a field-completeness matrix, the open work queues, and
 * the authority-candidate queue. Every list opens as a result list; in edit
 * mode (localhost) the candidate queue decides subjects directly, with
 * keyboard support (arrows/j/k move, y confirm, n reject).
 *
 * Read-only on the published site: the numbers are computed live from the
 * published artifacts, decisions require the local edit mode.
 */
const Curate = {
  FIELDS: [
    ['year', 'Year'],
    ['publisher', 'Publisher'],
    ['location', 'Location'],
    ['language', 'Language'],
    ['translator', 'Translator'],
    ['pageCount', 'Pages'],
    ['fullBibliographicEntry', 'Citation'],
  ],

  _brokenRefs: null,   // cached: [{name, pids}] unresolvable seeAlso targets

  render() {
    const container = document.getElementById('view-page');
    container.innerHTML = '<div class="loading-indicator"><div class="loading-spinner"></div><p>Loading quality data…</p></div>';
    Promise.all([Edit.loadTriage(), Edit.loadReconciliation()]).then(() => {
      this._build(container);
    });
  },

  _build(container) {
    container.innerHTML = `
      <div class="page-content curate-page">
        <h2 class="section-heading">Data Quality</h2>
        <p class="curate-intro">
          The processing state of the dataset, computed live from the published
          artifacts. Every list opens the affected entries.
          ${App.state.isLocal ? 'In edit mode, authority candidates can be decided directly from the queue below.' : 'Deciding open cases requires the local curation mode.'}
        </p>
        ${this._statusPanel()}
        <h3 class="curate-section-heading">Field completeness by entry type</h3>
        <p class="curate-hint">Share of entries with a value. Click a cell to open the entries missing that field.</p>
        ${this._matrix()}
        <h3 class="curate-section-heading">Open work queues</h3>
        ${this._queues()}
        <h3 class="curate-section-heading">Authority candidates (translators and publishers)</h3>
        <p class="curate-hint" id="agent-queue-hint"></p>
        <div id="agent-queue"></div>
      </div>
    `;
    this._renderAgentQueue();
    this._bindMatrix(container);
    this._bindQueues(container);
  },

  // -------------------------------------------------------------------------
  // Status panel
  // -------------------------------------------------------------------------

  _statusPanel() {
    const meta = App.data._meta || {};
    const summary = Edit.summary || {};
    const triageCount = Edit.triage ? Object.keys(Edit.triage).length : 0;
    const llmEntries = App.entries.filter(e =>
      e._provenance && Object.values(e._provenance).includes('llm')).length;
    const broken = this._brokenReferences();
    const brokenEntryCount = new Set(broken.flatMap(b => b.pids)).size;
    const pending = Edit.getPendingCount();

    const stat = (value, label) =>
      `<div class="network-stat"><strong>${value}</strong><span>${label}</span></div>`;
    return `<div class="network-stats-grid curate-stats">
      ${stat((meta.ns0Count || App.entries.length).toLocaleString('en'), 'Bibliography entries')}
      ${stat(triageCount.toLocaleString('en'), 'Entries with review hints')}
      ${stat(llmEntries.toLocaleString('en'), 'Entries with LLM-derived fields')}
      ${stat(brokenEntryCount.toLocaleString('en'), 'Entries with unresolved references')}
      ${stat(((summary.locationSubjects || 0) - (summary.publishedLocationLinks || 0)).toLocaleString('en'), 'Location names without link')}
      ${stat((summary.contestedAuthorityClaims || 0) + (summary.contestedEditionClaims || 0), 'Contested claims')}
      ${stat(pending.toLocaleString('en'), 'Pending decisions this session')}
    </div>`;
  },

  // -------------------------------------------------------------------------
  // Completeness matrix
  // -------------------------------------------------------------------------

  _matrix() {
    const types = [...new Set(App.entries.map(e => e.entryType || 'other'))]
      .map(t => ({ key: t, entries: App.entries.filter(e => (e.entryType || 'other') === t) }))
      .sort((a, b) => b.entries.length - a.entries.length);

    const cell = (field, typeKey, entries) => {
      const missing = entries.filter(e => e[field] == null || e[field] === '');
      const pct = entries.length ? Math.round(100 * (entries.length - missing.length) / entries.length) : 0;
      const cls = pct >= 90 ? 'matrix-high' : pct >= 60 ? 'matrix-mid' : 'matrix-low';
      if (!missing.length) return `<td class="${cls}">${pct}%</td>`;
      return `<td class="${cls}"><button class="matrix-cell" data-field="${field}" data-type="${typeKey}"
        title="${missing.length} entries without ${field}">${pct}%</button></td>`;
    };

    const header = ['<th scope="col">Field</th>', `<th scope="col">All (${App.entries.length.toLocaleString('en')})</th>`]
      .concat(types.map(t =>
        `<th scope="col">${ENTRY_TYPE_LABELS[t.key] || t.key} (${t.entries.length.toLocaleString('en')})</th>`))
      .join('');
    const rows = this.FIELDS.map(([field, label]) => {
      const cells = [cell(field, '*', App.entries)]
        .concat(types.map(t => cell(field, t.key, t.entries)))
        .join('');
      return `<tr><th scope="row">${label}</th>${cells}</tr>`;
    }).join('');
    return `<div class="matrix-scroll"><table class="curate-matrix">
      <thead><tr>${header}</tr></thead><tbody>${rows}</tbody>
    </table></div>`;
  },

  _bindMatrix(container) {
    container.querySelectorAll('.matrix-cell').forEach(btn => {
      btn.addEventListener('click', () => {
        const field = btn.dataset.field;
        const type = btn.dataset.type;
        const label = this.FIELDS.find(([f]) => f === field)[1];
        const pool = type === '*' ? App.entries
          : App.entries.filter(e => (e.entryType || 'other') === type);
        const missing = pool.filter(e => e[field] == null || e[field] === '');
        const typeLabel = type === '*' ? 'all types' : (ENTRY_TYPE_LABELS[type] || type);
        App.showCustomResults(missing, `Missing ${label} (${typeLabel})`);
      });
    });
  },

  // -------------------------------------------------------------------------
  // Work queues
  // -------------------------------------------------------------------------

  _brokenReferences() {
    if (this._brokenRefs) return this._brokenRefs;
    const broken = new Map();   // unresolvable target name → [sourcePageId]
    for (const entry of App.entries) {
      for (const ref of (entry.seeAlso || [])) {
        const pid = App.titleMap.get(ref) || (App.data.redirects && App.data.redirects[ref]);
        if (pid && App.entryMap.has(pid)) continue;
        if (!broken.has(ref)) broken.set(ref, []);
        broken.get(ref).push(entry.sourcePageId);
      }
    }
    this._brokenRefs = [...broken.entries()]
      .map(([name, pids]) => ({ name, pids }))
      .sort((a, b) => b.pids.length - a.pids.length || a.name.localeCompare(b.name));
    return this._brokenRefs;
  },

  _queues() {
    const t = Edit.triage || {};
    const byClass = { census: [], notInSource: [], detectable: [] };
    for (const [pid, flags] of Object.entries(t)) {
      if (!App.entryMap.has(parseInt(pid))) continue;
      if (flags.census) byClass.census.push(parseInt(pid));
      if (flags.notInSource && flags.notInSource.length) byClass.notInSource.push(parseInt(pid));
      if (flags.detectable && Object.keys(flags.detectable).length) byClass.detectable.push(parseInt(pid));
    }
    const llm = App.entries.filter(e =>
      e._provenance && Object.values(e._provenance).includes('llm'));
    const broken = this._brokenReferences();
    const brokenPids = [...new Set(broken.flatMap(b => b.pids))];
    const claims = Edit.contestedAuthorityClaims || [];
    const claimPids = [...new Set(claims.flatMap(c =>
      (c.sourceEvidence || []).map(ev => Number(ev.sourcePageId))))]
      .filter(pid => App.entryMap.has(pid));

    const queueRow = (key, label, note, count) => count
      ? `<li><button class="queue-btn" data-queue="${key}">${label} <strong>${count.toLocaleString('en')}</strong></button> <span class="curate-note">${note}</span></li>`
      : `<li><span class="queue-empty">${label} — none</span></li>`;

    const brokenTop = broken.slice(0, 12).map(b =>
      `<li>${esc(b.name)} <span class="detail-entry-year">${b.pids.length}×</span></li>`).join('');

    this._queueSets = {
      census: byClass.census,
      notInSource: byClass.notInSource,
      detectable: byClass.detectable,
      llm: llm.map(e => e.sourcePageId),
      broken: brokenPids,
      claims: claimPids,
    };

    return `<ul class="curate-queues">
      ${queueRow('census', 'Census anomalies', 'record-level findings from the census check', byClass.census.length)}
      ${queueRow('notInSource', 'Value not found in source', 'extracted value has no match in the raw text', byClass.notInSource.length)}
      ${queueRow('detectable', 'Detectable but not extracted', 'the raw text holds a value the extraction missed', byClass.detectable.length)}
      ${queueRow('llm', 'LLM-derived fields to validate', 'first-priority provenance class', llm.length)}
      ${queueRow('broken', 'Unresolved cross-references', 'See-Also targets without a page (red links)', brokenPids.length)}
      ${queueRow('claims', 'Contested authority claims', 'competing interpretations, decision open', claimPids.length)}
    </ul>
    ${broken.length ? `<details class="curate-broken-list">
      <summary>Most frequent unresolved reference targets (${broken.length.toLocaleString('en')} distinct)</summary>
      <ul>${brokenTop}</ul>
    </details>` : ''}`;
  },

  _bindQueues(container) {
    const labels = {
      census: 'Census anomalies',
      notInSource: 'Value not found in source',
      detectable: 'Detectable but not extracted',
      llm: 'LLM-derived fields',
      broken: 'Unresolved cross-references',
      claims: 'Contested authority claims',
    };
    container.querySelectorAll('.queue-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const key = btn.dataset.queue;
        const entries = (this._queueSets[key] || [])
          .map(pid => App.entryMap.get(pid))
          .filter(Boolean);
        App.showCustomResults(entries, labels[key]);
      });
    });
  },

  // -------------------------------------------------------------------------
  // Authority-candidate queue (subject-level decisions)
  // -------------------------------------------------------------------------

  // Pure derivation, pinned by tests/curation_queue.test.js: open subjects
  // first (by reach, descending), then pending, then decided/published.
  agentQueue(agents, pending) {
    const statusRank = { open: 0, pending: 1, decided: 2, published: 3 };
    return Object.values(agents || {}).map(subject => {
      const pend = pending[`agent:${subject.kind}/${subject.name}`];
      let status = 'open';
      if (subject.publishable) status = 'published';
      else if (subject.decision) status = 'decided';
      else if (pend) status = 'pending';
      return { ...subject, pending: pend || null, status };
    }).sort((a, b) =>
      statusRank[a.status] - statusRank[b.status]
      || (b.occurrences || 0) - (a.occurrences || 0)
      || a.name.localeCompare(b.name));
  },

  refreshQueue() {
    if (document.getElementById('agent-queue')) this._renderAgentQueue();
  },

  _renderAgentQueue() {
    const host = document.getElementById('agent-queue');
    const hint = document.getElementById('agent-queue-hint');
    if (!host) return;
    const rows = this.agentQueue(Edit.agents, Edit.pendingReconciliation);
    if (!rows.length) {
      host.innerHTML = '<p class="queue-empty">No candidate subjects published.</p>';
      return;
    }
    const open = rows.filter(r => r.status === 'open').length;
    const editable = App.state.isLocal && App.state.editMode;
    hint.textContent = editable
      ? `${open} open of ${rows.length} subjects. Keys: ↓/↑ or j/k move, y confirm top candidate, n reject, u keep unresolved, Enter show entries. A decision covers every entry with the name.`
      : `${open} open of ${rows.length} subjects. One decision covers every entry with the name; deciding requires the local edit mode.`;

    host.innerHTML = `<div class="agent-queue" role="list">${rows.map(r => this._agentRow(r, editable)).join('')}</div>`;

    host.querySelectorAll('.agent-queue-row').forEach(row => {
      row.addEventListener('keydown', ev => this._queueKey(ev, row));
    });
  },

  _agentRow(r, editable) {
    const top = (r.candidates || [])[0];
    const candidate = top
      ? `<a href="${esc(top.uri)}" target="_blank" rel="noopener">${esc(top.label)} (${esc(top.qid)})</a>${top.score != null ? `, score ${top.score}` : ''}`
      : '<span class="missing-value">no candidate</span>';
    const statusLabels = {
      open: 'proposal only', pending: 'pending (unsaved)',
      decided: r.decision ? r.decision.action : 'decided', published: 'published',
    };
    const k = esc(r.kind);
    const n = esc(r.name);
    let actions = '';
    if (editable) {
      if (r.pending) {
        actions = `<button class="reconciliation-btn" data-act="undo">Undo</button>`;
      } else if (r.status === 'open') {
        actions = (top ? `<button class="reconciliation-btn" data-act="confirm">Confirm</button>` : '')
          + `<button class="reconciliation-btn" data-act="reject">Reject</button>`
          + `<button class="reconciliation-btn" data-act="unresolved" title="Keep the case open as a contested claim with its source occurrences">Unresolved</button>`;
      }
    }
    return `<div class="agent-queue-row status-${r.status}" role="listitem" tabindex="0"
      data-kind="${k}" data-name="${n}" ${top ? `data-qid="${esc(top.qid)}"` : ''}>
      <span class="agent-queue-kind">${r.kind === 'person' ? 'Translator' : 'Publisher'}</span>
      <span class="agent-queue-name">${esc(r.name)}</span>
      <span class="agent-queue-reach" title="Occurrences in the source data">${r.occurrences || 0}×</span>
      <span class="agent-queue-candidate">${candidate}</span>
      <span class="agent-queue-status">${statusLabels[r.status]}${r.pending ? ` → ${esc(r.pending.action)}` : ''}</span>
      <span class="agent-queue-actions">${actions}</span>
    </div>`;
  },

  _queueKey(ev, row) {
    const kind = row.dataset.kind;
    const name = row.dataset.name;
    if (ev.key === 'ArrowDown' || ev.key === 'j') {
      ev.preventDefault();
      const next = row.nextElementSibling;
      if (next) next.focus();
    } else if (ev.key === 'ArrowUp' || ev.key === 'k') {
      ev.preventDefault();
      const prev = row.previousElementSibling;
      if (prev) prev.focus();
    } else if (ev.key === 'Enter') {
      ev.preventDefault();
      this._showSubjectEntries(kind, name);
    } else if (App.state.editMode && (ev.key === 'y' || ev.key === 'n' || ev.key === 'u')) {
      ev.preventDefault();
      const action = ev.key === 'y' ? 'confirm' : (ev.key === 'n' ? 'reject' : 'unresolved');
      const qid = ev.key === 'y' ? row.dataset.qid : null;
      if (ev.key === 'y' && !qid) return;
      const next = row.nextElementSibling;
      Edit.decideAgentSubject(kind, name, action, qid);
      // refreshQueue re-renders and re-sorts; put focus on the row that
      // followed, found again by identity, so the walk continues.
      if (next) {
        const sel = `.agent-queue-row[data-kind="${next.dataset.kind}"][data-name="${CSS.escape(next.dataset.name)}"]`;
        const again = document.querySelector(sel);
        if (again) again.focus();
      }
    }
  },

  _showSubjectEntries(kind, name) {
    const field = kind === 'person' ? 'translator' : 'publisher';
    const entries = App.entries.filter(e => e[field] === name);
    App.showCustomResults(entries, `${kind === 'person' ? 'Translator' : 'Publisher'}: ${name}`);
  },
};

// Click delegation for queue action buttons (avoids quoting names in inline handlers).
document.addEventListener('click', (ev) => {
  const btn = ev.target.closest('.agent-queue-row .reconciliation-btn[data-act]');
  if (!btn) return;
  const row = btn.closest('.agent-queue-row');
  if (btn.dataset.act === 'undo') {
    Edit.revertAgentDecisionSubject(row.dataset.kind, row.dataset.name);
  } else {
    Edit.decideAgentSubject(
      row.dataset.kind, row.dataset.name, btn.dataset.act,
      btn.dataset.act === 'confirm' ? row.dataset.qid : null
    );
  }
});

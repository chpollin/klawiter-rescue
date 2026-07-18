/**
 * Edit module — Expert-in-the-Loop curation for Klawiter Bibliography.
 *
 * Increments 1-3 of the EIL editing interface (design: knowledge/eil-editing.md):
 * the three typed actions (Accept / Correct / Add), edit-history records, the
 * three-status review surfaced per entry, session durability via localStorage,
 * a version-2 patch export that pipeline/apply_patches.py consumes directly,
 * per-entry triage hints bundled from existing data signals (increment 2), and
 * per-field source evidence snippets (increment 3).
 *
 * Only active when App.state.isLocal && App.state.editMode. The exported patch
 * is the only outward artifact; nothing is written to the dataset from here.
 */
const Edit = {
  EDITOR_ROLE: 'Editor (SZD)',          // role, not a personal name (privacy convention)
  STORAGE_KEY: 'klawiter.pendingEdits.v2',
  TRIAGE_URL: 'data/triage.json',       // built by pipeline/build_triage.py (local file, no external request)

  FIELD_LABELS: { publisher: 'Publisher', location: 'Location', translator: 'Translator',
                  pageCount: 'Pages', title: 'Title' },
  TRACKED_FIELDS: ['publisher', 'location', 'translator', 'pageCount'],

  triage: null,            // pageId(str) -> flags from triage.json; null until loaded
  _triageFetched: false,

  // Load the triage artifact once, on entering edit mode. On failure the
  // hints honestly degrade to what the entry itself carries (provenance).
  loadTriage() {
    if (this._triageFetched) return Promise.resolve();
    this._triageFetched = true;
    return fetch(this.TRIAGE_URL)
      .then(r => (r.ok ? r.json() : null))
      .then(doc => { this.triage = doc && doc.entries ? doc.entries : {}; })
      .catch(() => { this.triage = {}; });
  },

  // Restore pending edits from a previous session so in-progress work survives a reload.
  restore() {
    try {
      const raw = localStorage.getItem(this.STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed && typeof parsed === 'object') App.state.pendingEdits = parsed;
      }
    } catch (e) { /* corrupt or unavailable store: start clean */ }
    this.updateBadge();
  },

  persist() {
    try {
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(App.state.pendingEdits));
    } catch (e) { /* quota exceeded or disabled: stay in-memory for this session */ }
  },

  _prov(pid, field) {
    const entry = App.entryMap.get(pid);
    return entry && entry._provenance ? (entry._provenance[field] || 'missing') : 'missing';
  },

  _now() {
    return new Date().toISOString();
  },

  // Inline value change: classify as Add (field was empty/missing) or Correct (was present).
  trackChange(el) {
    if (!App.state.editMode) return;
    const field = el.dataset.field;
    const pid = parseInt(el.dataset.pid);
    const original = el.dataset.original || '';
    const newValue = el.textContent.trim();

    if (newValue === original || (!newValue && !original)) {
      this._clear(pid, field);
      this._afterChange(pid);
      return;
    }

    const prov = this._prov(pid, field);
    const action = (!original || prov === 'missing') ? 'add' : 'correct';
    this._set(pid, field, {
      action,
      oldValue: original || null,
      newValue: newValue || null,
      previousProvenance: prov,
      edited_at: this._now(),
    });
    this._afterChange(pid);
  },

  // Accept confirms a present value as correct without changing it.
  accept(pid, field) {
    if (!App.state.editMode) return;
    const entry = App.entryMap.get(pid);
    const value = entry ? entry[field] : null;
    if (value == null || value === '') return;   // nothing to accept on a missing field
    this._set(pid, field, {
      action: 'accept',
      oldValue: String(value),
      newValue: String(value),
      previousProvenance: this._prov(pid, field),
      edited_at: this._now(),
    });
    this._afterChange(pid);
  },

  // Undo a pending action on a field.
  revert(pid, field) {
    this._clear(pid, field);
    this._afterChange(pid);
  },

  _set(pid, field, record) {
    if (!App.state.pendingEdits[pid]) App.state.pendingEdits[pid] = {};
    App.state.pendingEdits[pid][field] = record;
  },

  _clear(pid, field) {
    if (!App.state.pendingEdits[pid]) return;
    delete App.state.pendingEdits[pid][field];
    if (Object.keys(App.state.pendingEdits[pid]).length === 0) delete App.state.pendingEdits[pid];
  },

  pending(pid, field) {
    return App.state.pendingEdits[pid] ? App.state.pendingEdits[pid][field] : undefined;
  },

  // Live review status: persisted from the dataset, raised to approved by pending human edits.
  entryStatus(pid) {
    if (App.state.pendingEdits[pid] && Object.keys(App.state.pendingEdits[pid]).length) {
      return { status: 'approved', pending: true };
    }
    const entry = App.entryMap.get(pid);
    const r = entry && entry.review;
    if (r && r.status) return { status: r.status, pending: false };
    return { status: 'unreviewed', pending: false };
  },

  _afterChange(pid) {
    this.persist();
    this.updateBadge();
    // Defer so a click that caused a contenteditable blur finishes on the old DOM
    // (the action is already recorded in state) before the entry re-renders.
    setTimeout(() => this._rerender(pid), 0);
  },

  // Re-render the open detail/card for one entry so badges and status refresh.
  _rerender(pid) {
    const inline = document.getElementById(`card-detail-${pid}`);
    if (inline && !inline.classList.contains('hidden')) {
      inline.innerHTML = Detail.renderInline(App.entryMap.get(pid));
      return;
    }
    if (App.state.view === 'detail' && App.state.entryId === pid) {
      Detail.render(App.entryMap.get(pid));
    }
  },

  getPendingCount() {
    let count = 0;
    for (const pid in App.state.pendingEdits) count += Object.keys(App.state.pendingEdits[pid]).length;
    return count;
  },

  updateBadge() {
    const count = this.getPendingCount();
    let badge = document.getElementById('edit-badge');

    if (count > 0 && !badge) {
      const header = document.querySelector('.header-inner');
      const saveBtn = document.createElement('button');
      saveBtn.id = 'edit-save-btn';
      saveBtn.className = 'edit-save-btn';
      saveBtn.onclick = () => this.exportPatch();
      saveBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg> Save <span id="edit-badge" class="edit-badge">${count}</span>`;
      header.appendChild(saveBtn);
    } else if (badge) {
      badge.textContent = count;
      if (count === 0) {
        const saveBtn = document.getElementById('edit-save-btn');
        if (saveBtn) saveBtn.remove();
      }
    }
  },

  // --- Triage hints (increment 2) ---
  // Bundle the signals that already exist into one ordered per-entry hint
  // list: census anomaly, verify.py flags (value not found in the raw text /
  // value detectable in the raw text but absent from output), then the
  // provenance layers (llm = first check priority, missing = check the source
  // for a value; see knowledge/production-readiness.md). This is an attention
  // aid over the data situation, not a quality or workflow score: the rank
  // orders signal classes for the editor's time, nothing numeric is shown or
  // derived from it (protocol, not instrumentation).
  triageHints(entry) {
    if (!entry) return [];
    if (entry.review && entry.review.status === 'approved') return [];  // already human-verified
    const pid = entry.sourcePageId;
    const t = (this.triage && this.triage[String(pid)]) || {};
    const prov = entry._provenance || {};
    // A field the editor has already adjudicated (pending action or persisted
    // editor provenance) needs no further attention hint.
    const adjudicated = f => !!this.pending(pid, f) || prov[f] === 'editor' || prov[f] === 'expert';
    const hints = [];
    if (t.census) hints.push({ rank: 0, field: null, label: t.census });
    for (const f of (t.notInSource || [])) {
      if (adjudicated(f)) continue;
      hints.push({ rank: 1, field: f, label: 'Wert nicht im Rohtext gefunden' });
    }
    for (const [f, raw] of Object.entries(t.detectable || {})) {
      if (adjudicated(f)) continue;
      hints.push({ rank: 2, field: f, label: 'Im Rohtext erkennbar, nicht extrahiert', detail: raw });
    }
    for (const f of this.TRACKED_FIELDS) {
      if (adjudicated(f)) continue;
      if (prov[f] === 'llm') {
        hints.push({ rank: 3, field: f, label: 'LLM-abgeleitet, nicht validiert' });
      } else if (prov[f] === 'missing' && !(t.detectable && t.detectable[f])) {
        hints.push({ rank: 4, field: f, label: 'Nicht extrahiert, Rohtext auf Wert prüfen' });
      }
    }
    hints.sort((a, b) => a.rank - b.rank);
    return hints;
  },

  // Ordering key for the edit-mode "Prüfbedarf" sort: the most urgent signal
  // class present on the entry (lower = check sooner), 9 when nothing points here.
  triageRank(pid) {
    const hints = this.triageHints(App.entryMap.get(pid));
    return hints.length ? hints[0].rank : 9;
  },

  // Compact per-card hint for the results list in edit mode.
  cardHint(pid) {
    const hints = this.triageHints(App.entryMap.get(pid));
    if (!hints.length) return '';
    const top = hints[0];
    const field = top.field ? `${this.FIELD_LABELS[top.field] || top.field}: ` : '';
    const more = hints.length > 1 ? ` <span class="triage-more">+${hints.length - 1}</span>` : '';
    return `<span class="triage-chip triage-rank-${top.rank}" title="Prüfhinweis aus Datensignalen">${esc(field)}${esc(top.label)}${more}</span>`;
  },

  // --- Source evidence per field (increment 3) ---
  // Locate a field value inside the entry's source text so the editor checks
  // against the evidence without leaving the row. Whitespace-tolerant and
  // case-insensitive; returns { index, length, count } of the first occurrence
  // in the original text, or null. Multi-edition pages can hold several
  // occurrences; count surfaces that ambiguity instead of hiding it.
  _findValueSpan(text, value) {
    if (!text || value == null || String(value).trim() === '') return null;
    const pattern = String(value).trim()
      .replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
      .replace(/\s+/g, '\\s+');
    let re;
    try { re = new RegExp(pattern, 'gi'); } catch (e) { return null; }
    const matches = [...text.matchAll(re)];
    if (!matches.length) return null;
    return { index: matches[0].index, length: matches[0][0].length, count: matches.length };
  },

  // Page counts rarely appear as the bare number: accept a digit-bounded
  // literal, the N/(M)p. summation, and pp. X-Y ranges — the same semantics
  // verify.py uses to confirm a page count against the raw text.
  _findPageCountSpan(text, count) {
    const n = parseInt(count, 10);
    if (!text || !Number.isFinite(n)) return null;
    const literal = new RegExp(`(?<!\\d)${n}(?!\\d)`).exec(text);
    if (literal) return { index: literal.index, length: literal[0].length, count: 1 };
    for (const m of text.matchAll(/(\d+)\/\((\d+)\)p/g)) {
      if (parseInt(m[1], 10) + parseInt(m[2], 10) === n) {
        return { index: m.index, length: m[0].length, count: 1 };
      }
    }
    for (const m of text.matchAll(/pp\.?\s*\(?(\d+)\)?\s*[-–]\s*\(?(\d+)\)?/g)) {
      if (parseInt(m[2], 10) - parseInt(m[1], 10) + 1 === n) {
        return { index: m.index, length: m[0].length, count: 1 };
      }
    }
    return null;
  },

  // Cut a readable window around a span, extended to whitespace boundaries.
  _snippetAround(text, span, radius = 70) {
    let start = Math.max(0, span.index - radius);
    let end = Math.min(text.length, span.index + span.length + radius);
    while (start > 0 && !/\s/.test(text[start])) start--;
    while (end < text.length && !/\s/.test(text[end])) end++;
    return {
      before: (start > 0 ? '…' : '') + text.slice(start, span.index),
      match: text.slice(span.index, span.index + span.length),
      after: text.slice(span.index + span.length, end) + (end < text.length ? '…' : ''),
      count: span.count || 1,
    };
  },

  // Evidence snippet for one tracked field: the source passage holding the
  // machine value, or — for a missing field — the verify.py-detected raw
  // value. Returns null when no field-precise span is derivable; the caller
  // then falls back to the collapsible full source (the honest variant).
  evidence(entry, field) {
    const text = entry && entry.fullBibliographicEntry;
    if (!text) return null;
    let span = null;
    if (field === 'pageCount') {
      span = this._findPageCountSpan(text, entry.pageCount);
    } else if (entry[field]) {
      span = this._findValueSpan(text, entry[field]);
    }
    if (!span) {
      const t = (this.triage && this.triage[String(entry.sourcePageId)]) || {};
      const detected = t.detectable && t.detectable[field];
      if (detected) span = this._findValueSpan(text, detected);
    }
    return span ? this._snippetAround(text, span) : null;
  },

  // Export pending edits as a version-2 patch document. The patch shape is the
  // contract pipeline/apply_patches.py reads (see tests/test_patch_contract.py).
  exportPatch() {
    const patches = [];
    for (const [pid, fields] of Object.entries(App.state.pendingEdits)) {
      for (const [field, change] of Object.entries(fields)) {
        patches.push({
          pageId: parseInt(pid),
          field: field,
          action: change.action,
          oldValue: change.oldValue ?? null,
          newValue: change.newValue ?? null,
          previousProvenance: change.previousProvenance,
          edited_by: this.EDITOR_ROLE,
          edited_at: change.edited_at,
          source: 'human',
        });
      }
    }

    if (patches.length === 0) return;

    const patchDoc = {
      patchVersion: 2,
      created: this._now(),
      source: 'klawiter-eil-interface',
      totalChanges: patches.length,
      patches: patches,
    };

    downloadBlob(
      JSON.stringify(patchDoc, null, 2),
      `klawiter-patch-${this._now().slice(0, 10)}.json`,
      'application/json'
    );
  },
};

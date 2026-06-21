/**
 * Edit module — Expert-in-the-Loop curation for Klawiter Bibliography.
 *
 * Increment 1 of the EIL editing interface (design: knowledge/eil-editing.md):
 * the three typed actions (Accept / Correct / Add), edit-history records, the
 * three-status review surfaced per entry, session durability via localStorage,
 * and a version-2 patch export that pipeline/apply_patches.py consumes directly.
 *
 * Only active when App.state.isLocal && App.state.editMode. The exported patch
 * is the only outward artifact; nothing is written to the dataset from here.
 */
const Edit = {
  EDITOR_ROLE: 'Editor (SZD)',          // role, not a personal name (privacy convention)
  STORAGE_KEY: 'klawiter.pendingEdits.v2',

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

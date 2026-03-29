/**
 * Edit module — Expert-in-the-Loop curation for Klawiter Bibliography.
 * Tracks field changes, exports JSON patches, shows pending edit counts.
 * Only active when App.state.isLocal && App.state.editMode.
 */
const Edit = {
  trackChange(el) {
    if (!App.state.editMode) return;

    const field = el.dataset.field;
    const pid = parseInt(el.dataset.pid);
    const original = el.dataset.original;
    const newValue = el.textContent.trim();

    if (newValue === original || (!newValue && !original)) return;

    if (!App.state.pendingEdits[pid]) {
      App.state.pendingEdits[pid] = {};
    }

    const entry = App.entryMap.get(pid);
    const prov = entry && entry._provenance ? entry._provenance[field] : 'unknown';

    if (newValue === original) {
      delete App.state.pendingEdits[pid][field];
      if (Object.keys(App.state.pendingEdits[pid]).length === 0) {
        delete App.state.pendingEdits[pid];
      }
    } else {
      App.state.pendingEdits[pid][field] = {
        oldValue: original,
        newValue: newValue,
        provenance: prov,
      };
    }

    this.updateBadge();
  },

  getPendingCount() {
    let count = 0;
    for (const pid in App.state.pendingEdits) {
      count += Object.keys(App.state.pendingEdits[pid]).length;
    }
    return count;
  },

  updateBadge() {
    const count = this.getPendingCount();
    let badge = document.getElementById('edit-badge');

    if (count > 0 && !badge) {
      // Create save button if it doesn't exist
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

  exportPatch() {
    const patches = [];
    for (const [pid, fields] of Object.entries(App.state.pendingEdits)) {
      for (const [field, change] of Object.entries(fields)) {
        patches.push({
          pageId: parseInt(pid),
          field: field,
          oldValue: change.oldValue,
          newValue: change.newValue,
          previousProvenance: change.provenance,
        });
      }
    }

    if (patches.length === 0) return;

    const patchDoc = {
      patchVersion: 1,
      created: new Date().toISOString(),
      source: 'klawiter-eil-interface',
      totalChanges: patches.length,
      patches: patches,
    };

    const blob = new Blob([JSON.stringify(patchDoc, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `klawiter-patch-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  },
};

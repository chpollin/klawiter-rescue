/**
 * main.js – application bootstrap (rev 2)
 * --------------------------------------
 *  ▸ waits for DOM
 *  ▸ initialises UI ▸ router ▸ charts
 *  ▸ loads CSV (via ZweigBibliography)
 *  ▸ subscribes to ZweigStore → single render pipeline
 */

(function () {
    // ---------- helpers ---------- //
    /**
     * Check whether a bibliography entry matches current store filters & query.
     * @param {Object} e    – entry
     * @param {Object} st   – state snapshot from ZweigStore
     * @returns {Boolean}
     */
    const entryMatchesState = (e, st) => {
      // text query (title, orig_title, etc.) – case‑insensitive
      if (st.query) {
        const q = st.query.toLowerCase();
        if (
          ![
            e.title,
            e.original_title,
            e.full_bibliographic_entry,
            e.publisher,
            e.location,
            e.clean_content,
          ].some((f) => f && f.toLowerCase().includes(q))
        )
          return false;
      }
  
      // category / language / timePeriod – multi‑select (Set) → match ANY selected
      for (const facet of ['category', 'language', 'timePeriod']) {
        const selected = st.filters[facet];
        if (selected && selected.size) {
          const key =
            facet === 'category'
              ? 'main_category'
              : facet === 'timePeriod'
              ? 'time_period'
              : facet; // language field is same name
          if (!selected.has(e[key])) return false;
        }
      }
  
      // year range inclusive
      const [minY, maxY] = st.filters.yearRange;
      if (minY !== null && e.year && e.year < minY) return false;
      if (maxY !== null && e.year && e.year > maxY) return false;
  
      return true;
    };
  
    /**
     * Recompute filtered list & render appropriate view.
     * Runs on every state change *and* after data load.
     */
    const renderFromState = (st) => {
      if (!ZweigBibliography.isLoaded()) return;
  
      // ---------------- get filtered dataset ----------------
      const all = ZweigBibliography.getAllEntries();
      const results = all.filter((e) => entryMatchesState(e, st));
  
      // ---------------- update charts ----------------
      ZweigCharts.update(results);
  
      // ---------------- switch view ----------------
      switch (st.view) {
        case 'dashboard':
          ZweigUI.displayDashboard();
          break;
  
        case 'list':
          ZweigUI.displayEntries(results);
          break;
  
        case 'detail': {
          if (st.selectedEntry) {
            const entry = ZweigBibliography.getEntryById(st.selectedEntry);
            if (entry) {
              ZweigUI.displayEntryDetail(entry);
            } else {
              ZweigUI.showError(`Entry ${st.selectedEntry} not found.`);
              ZweigStore.setState({ view: 'dashboard', selectedEntry: null });
            }
          }
          break;
        }
      }
    };
  
    // ---------- bootstrap ---------- //
    document.addEventListener('DOMContentLoaded', () => {
      console.log('[bootstrap] DOM ready');
  
      // 1. initialise UI, router, charts
      ZweigUI.initialize();
      ZweigRouter.initialize();
      ZweigCharts.initialize();
  
      // 2. load CSV (only once)
      if (!ZweigBibliography.isLoading() && !ZweigBibliography.isLoaded()) {
        ZweigUI.showLoading(true);
        ZweigBibliography.loadData().catch((err) => {
          ZweigUI.showLoading(false);
          ZweigUI.showError(`Failed to load data: ${err.message}`);
        });
      }
  
      // 3. react to data load
      ZweigBibliography.addEventListener('loaded', () => {
        ZweigUI.showLoading(false);
        renderFromState(ZweigStore.getState());
      });
  
      // 4. subscribe to store updates → single render pipeline
      ZweigStore.subscribe(renderFromState);
    });
  })();
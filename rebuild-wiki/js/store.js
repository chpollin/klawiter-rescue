/**
 * store.js – minimalist global state container for the Zweig Bibliography SPA
 * ---------------------------------------------------------------
 * All application views (dashboard / list / detail), filters, search query
 * and selection live here. Components subscribe to state changes instead of
 * talking to one another directly → predictable flow & easy URL sync.
 */

const ZweigStore = (function () {
    /* ---------- initial state shape ---------- */
    const _state = {
      view: 'dashboard',            // 'dashboard' | 'list' | 'detail'
      query: '',                    // text search
      filters: {
        category: new Set(),        // multi‑select
        language: new Set(),
        timePeriod: new Set(),
        yearRange: [null, null]     // [min,max] – null = no bound
      },
      selectedEntry: null           // page_id when in detail view
    };
  
    const _listeners = new Set();
  
    /* ---------- helpers ---------- */
    const _cloneDeep = (obj) => JSON.parse(JSON.stringify(obj));
  
    const _emit = () => {
      const snapshot = _cloneDeep(_state);
      _listeners.forEach((cb) => cb(snapshot));
    };
  
    /* ---------- public API ---------- */
    return {
      /**
       * Subscribe to state updates.
       * @param {Function} cb – callback receiving the latest state
       * @returns {Function} unsubscribe
       */
      subscribe(cb) {
        if (typeof cb !== 'function') return () => {};
        _listeners.add(cb);
        // immediate first call with current state
        cb(_cloneDeep(_state));
        return () => _listeners.delete(cb);
      },
  
      /**
       * Read‑only snapshot of current state.
       */
      getState() {
        return _cloneDeep(_state);
      },
  
      /**
       * Merge a partial update and notify subscribers.
       * Keys not present remain untouched.
       */
      setState(partial) {
        Object.keys(partial).forEach((k) => {
          if (k === 'filters' && typeof partial[k] === 'object') {
            Object.keys(partial.filters).forEach((f) => {
              const val = partial.filters[f];
              if (f === 'yearRange') {
                _state.filters.yearRange = Array.isArray(val) ? val.slice(0, 2) : [null, null];
              } else if (Array.isArray(val)) {
                _state.filters[f] = new Set(val);
              } else if (val instanceof Set) {
                _state.filters[f] = new Set([...val]);
              }
            });
          } else {
            _state[k] = partial[k];
          }
        });
        _emit();
      },
  
      /**
       * Clear all filters and optionally the search query.
       */
      clearFilters(resetQuery = false) {
        _state.filters.category.clear();
        _state.filters.language.clear();
        _state.filters.timePeriod.clear();
        _state.filters.yearRange = [null, null];
        if (resetQuery) _state.query = '';
        _emit();
      },
  
      /**
       * Convenience: toggle a value inside a Set‑based filter
       */
      toggleFilter(facet, value) {
        if (!_state.filters[facet]) return;
        if (_state.filters[facet].has(value)) {
          _state.filters[facet].delete(value);
        } else {
          _state.filters[facet].add(value);
        }
        _emit();
      }
    };
  })();
  
  // Make globally available for now (can be ESM‑imported under bundler)
  window.ZweigStore = ZweigStore;
  
/**
 * store.js – minimal global reactive state container (rev 2.1)
 * ------------------------------------------------------------
 * Provides:
 *   • getState()          – shallow clone of current state
 *   • commit(patch)       – merge‑patch + notify subscribers
 *   • replaceState(obj)   – hard replace (used by router)
 *   • subscribe(cb)       – listen to any change
 *   • unsubscribe(cb)
 *   • getFilteredEntries() – helper to reuse last computed list (for export)
 */

const ZweigStore = (function () {
    /* ------------- private ------------- */
    let _state = {
      view: 'dashboard',   // 'dashboard' | 'list' | 'detail'
      query: '',           // search string
      filters: {           // multi‑select facets
        category: [],
        language: [],
        timePeriod: [],
      },
      yearRange: null,     // { min, max } or null
      selectedId: null,    // page_id string for detail
      entries: [],         // filtered result cache (list & dash)
      selectedEntry: null, // detail cache
      loading: true,
      error: null,
    }
  
    const _subs = new Set()
  
    const _notify = (prev) => _subs.forEach((cb) => cb({ ..._state }, prev))
  
    const _shallowEqual = (a, b) =>
      a === b || (typeof a === 'object' && typeof b === 'object' && a && b && Object.keys(a).every((k) => a[k] === b[k]))
  
    /* ------------- public ------------- */
    return {
      /**
       * Get a shallow clone of the state (read‑only)
       */
      getState() {
        return { ..._state }
      },
  
      /**
       * Merge patch → triggers notify if changed
       * @param {Object} patch
       */
      commit(patch = {}) {
        const prev = { ..._state }
        let changed = false
        Object.keys(patch).forEach((k) => {
          if (!_shallowEqual(_state[k], patch[k])) {
            _state[k] = patch[k]
            changed = true
          }
        })
        if (changed) _notify(prev)
      },
  
      /**
       * Hard replace entire state, optionally suppressing notification
       * Used by Router when parsing URL → state on initial load/hashchange.
       */
      replaceState(newState = {}, silent = false) {
        const prev = { ..._state }
        _state = { ..._state, ...newState }
        if (!silent) _notify(prev)
      },
  
      /**
       * Subscribe to every state change
       * @param {Function} cb (state, prevState)
       */
      subscribe(cb) {
        _subs.add(cb)
      },
      unsubscribe(cb) {
        _subs.delete(cb)
      },
  
      /* ------- derived helpers (not reactive) ------- */
      /** Return last cached filtered entries (fast) */
      getFilteredEntries() {
        return _state.entries || []
      },
    }
  })()
  
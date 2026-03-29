/**
 * router.js  – hash‑based deep‑linking & history handler (rev 2)
 * -------------------------------------------------------------------
 * Responsibilities
 *   • Parse URL → hydrate ZweigStore (on first load & hashchange)
 *   • Listen to ZweigStore → push compact URI reflecting current state
 *   • Debounce pushes & avoid feedback loops with a guard flag
 */

const ZweigRouter = (function () {
    let _suppress = false; // prevents store‑>router push triggering router‑>store loop
  
    /* util -------------------------------------------------------------- */
    const _encode = encodeURIComponent;
  
    const _arrayToParam = (arr) => (arr && arr.length ? arr.map(_encode).join(',') : undefined);
  
    // Build a URI fragment from state
    const _stateToHash = (state) => {
      const parts = [];
  
      // view & id (for detail)
      if (state.view === 'detail' && state.selectedId) {
        parts.push(`view=detail&id=${_encode(state.selectedId)}`);
      } else if (state.view === 'list') {
        parts.push('view=list');
        if (state.query) parts.push(`query=${_encode(state.query)}`);
        if (state.yearRange) parts.push(`year=${state.yearRange.min}-${state.yearRange.max}`);
        // multi‑facets
        const { category, language, timePeriod } = state.filters;
        if (category?.length) parts.push(`category=${_arrayToParam(category)}`);
        if (language?.length) parts.push(`language=${_arrayToParam(language)}`);
        if (timePeriod?.length) parts.push(`timePeriod=${_arrayToParam(timePeriod)}`);
      } else {
        parts.push('dashboard');
      }
  
      return '#' + parts.join('&');
    };
  
    // Parse current hash → state diff
    const _hashToPartialState = () => {
      const raw = window.location.hash.slice(1);
      if (!raw) return { view: 'dashboard' };
  
      if (raw === 'dashboard') return { view: 'dashboard' };
  
      const params = Object.fromEntries(
        raw.split('&').map((kv) => {
          const [k, v] = kv.split('=');
          return [k, v ? decodeURIComponent(v) : true];
        })
      );
  
      if (params.view === 'detail') {
        return { view: 'detail', selectedId: params.id };
      }
  
      if (params.view === 'list') {
        const range = params.year?.split('-').map(Number);
        return {
          view: 'list',
          query: params.query || '',
          yearRange: range?.length === 2 ? { min: range[0], max: range[1] } : undefined,
          filters: {
            category: params.category ? params.category.split(',').map(decodeURIComponent) : undefined,
            language: params.language ? params.language.split(',').map(decodeURIComponent) : undefined,
            timePeriod: params.timePeriod ? params.timePeriod.split(',').map(decodeURIComponent) : undefined,
          },
        };
      }
  
      return { view: 'dashboard' }; // fallback
    };
  
    /* handlers ----------------------------------------------------------- */
    const _onHashChange = () => {
      if (_suppress) return; // we triggered it ourselves → ignore
      const partial = _hashToPartialState();
      ZweigStore.replaceState(partial, /*pushHistory=*/false); // hydrate store without another URL push
    };
  
    const _onStoreChange = (state) => {
      _suppress = true;
      window.location.hash = _stateToHash(state);
      // allow another cycle on next tick
      setTimeout(() => (_suppress = false), 0);
    };
  
    /* public ------------------------------------------------------------- */
    return {
      initialize() {
        window.addEventListener('hashchange', _onHashChange);
  
        // Apply initial hash → store before anyone renders
        const initialPartial = _hashToPartialState();
        ZweigStore.replaceState(initialPartial, /*pushHistory=*/false);
  
        // Listen for store updates to keep URL in sync
        ZweigStore.subscribe(_onStoreChange);
  
        console.info('[Router] Initialized.');
      },
    };
  })();
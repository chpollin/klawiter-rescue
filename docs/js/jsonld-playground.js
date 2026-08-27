/**
 * JSON-LD Playground — interactive exploration of the dataset's Linked Data structure.
 * Lets users pick an entry and view it in compact, expanded, and triple form.
 */
const JsonldPlayground = {

  /** The @context from vocabulary.py, mirrored for client-side expansion. */
  CONTEXT: {
    '@version': 1.1,
    'schema': 'https://schema.org/',
    'dcterms': 'http://purl.org/dc/terms/',
    'klawiter': 'https://chpollin.github.io/klawiter-rescue/vocab/',
    'xsd': 'http://www.w3.org/2001/XMLSchema#',
    'name': 'schema:name',
    'description': 'schema:description',
    'creator': 'schema:creator',
    'sourceOrganization': 'schema:sourceOrganization',
    'datePublished': { '@id': 'schema:datePublished', '@type': 'xsd:gYear' },
    'publisher': 'schema:publisher',
    'inLanguage': 'schema:inLanguage',
    'numberOfPages': { '@id': 'schema:numberOfPages', '@type': 'xsd:integer' },
    'translator': 'schema:translator',
    'locationCreated': 'schema:locationCreated',
    'sameAs': { '@id': 'schema:sameAs', '@type': '@id' },
    'isRelatedTo': { '@id': 'schema:isRelatedTo', '@container': '@set' },
    'workTranslation': { '@id': 'schema:workTranslation', '@container': '@set' },
    'hasPart': { '@id': 'schema:hasPart', '@container': '@list' },
    'author': 'schema:author',
    'bibliographicCitation': 'dcterms:bibliographicCitation',
    'entryType': 'klawiter:entryType',
    'timePeriod': 'klawiter:timePeriod',
    'totalEntries': { '@id': 'klawiter:totalEntries', '@type': 'xsd:integer' },
    'entries': { '@id': 'klawiter:entries', '@container': '@list' },
    'categories': { '@id': 'klawiter:categories', '@container': '@set' },
    'contentItems': { '@id': 'klawiter:contentItems', '@container': '@list' },
    'mainCategory': 'klawiter:mainCategory',
    'originalTitle': 'klawiter:originalTitle',
    'languageCode': 'klawiter:languageCode',
    'allYears': { '@id': 'klawiter:allYears', '@container': '@set' },
    'allLocations': { '@id': 'klawiter:allLocations', '@container': '@set' },
    'reprints': { '@id': 'klawiter:reprints', '@container': '@set' },
    'sourcePageId': { '@id': 'klawiter:sourcePageId', '@type': 'xsd:integer' },
    'sourceTextId': { '@id': 'klawiter:sourceTextId', '@type': 'xsd:integer' },
    'sourceBlobId': { '@id': 'klawiter:sourceBlobId', '@type': 'xsd:integer' },
    'pageNamespace': 'klawiter:pageNamespace',
    'isRedirect': 'klawiter:isRedirect',
    'redirectTarget': 'klawiter:redirectTarget',
  },

  /** Frontend key → JSON-LD key mapping (inverse of _FRONTEND_KEY_MAP in 05_to_jsonld.py) */
  FRONTEND_TO_JSONLD: {
    'title': 'name',
    'year': 'datePublished',
    'location': 'locationCreated',
    'language': 'inLanguage',
    'pageCount': 'numberOfPages',
    'fullBibliographicEntry': 'bibliographicCitation',
    'seeAlso': 'isRelatedTo',
    'translations': 'workTranslation',
    'contentItems': 'hasPart',
  },

  /** Stefan Zweig author object for primary works */
  STEFAN_ZWEIG: {
    '@type': 'schema:Person',
    'name': 'Stefan Zweig',
    'sameAs': 'https://www.wikidata.org/entity/Q78491',
  },

  currentEntry: null,
  _bound: false,          // the document-level listener is registered once
  _activeSuggestion: -1,  // keyboard cursor into the suggestion list

  /**
   * The Data page renders the playground on every visit, so init() runs
   * repeatedly. Element-bound listeners go on the freshly rendered nodes;
   * the document-level dismissal listener is registered once and resolves
   * its element at event time.
   */
  init() {
    const searchInput = document.getElementById('jsonld-search');
    const randomBtn = document.getElementById('jsonld-random');
    const suggestions = document.getElementById('jsonld-suggestions');

    if (!searchInput) return;

    searchInput.addEventListener('input', () => this._onSearch(searchInput, suggestions));
    searchInput.addEventListener('keydown', (e) => this._onSearchKey(e, searchInput, suggestions));
    searchInput.addEventListener('focus', () => {
      if (suggestions.children.length > 0) this._setListOpen(suggestions, true);
    });
    randomBtn.addEventListener('click', () => this._loadRandom());

    if (!this._bound) {
      this._bound = true;
      document.addEventListener('click', (e) => {
        const list = document.getElementById('jsonld-suggestions');
        if (list && !e.target.closest('.jsonld-search-wrap')) this._setListOpen(list, false);
      });
    }

    // Tab switching
    document.querySelectorAll('.jsonld-tab').forEach(tab => {
      tab.addEventListener('click', () => this._switchTab(tab.dataset.tab));
    });

    // '#data/playground/<pageId>' addresses one entry; without it, a random one.
    const entry = this._entryFromHash();
    if (entry) {
      searchInput.value = entry.title || '';
      this._loadEntry(entry);
    } else {
      this._loadRandom();
    }
  },

  /** The page id of a '#data/playground/<pageId>' route, resolved to an entry. */
  _entryFromHash() {
    const parts = (location.hash || '').replace(/^#/, '').split('/');
    if (parts[0] !== 'data' || parts[1] !== 'playground' || !parts[2]) return null;
    const pid = parseInt(parts[2], 10);
    return Number.isFinite(pid) && App.entryMap ? (App.entryMap.get(pid) || null) : null;
  },

  /** Search entries by title */
  _onSearch(input, suggestions) {
    const q = input.value.trim().toLowerCase();
    suggestions.innerHTML = '';
    this._activeSuggestion = -1;
    if (q.length < 2) { this._setListOpen(suggestions, false); return; }

    const matches = App.entries
      .filter(e => e.title && e.title.toLowerCase().includes(q))
      .slice(0, 8);

    if (matches.length === 0) {
      // An empty list that simply stays hidden reads as a broken field.
      suggestions.innerHTML = '<div class="jsonld-suggestion jsonld-suggestion-empty" role="status">No matches</div>';
      this._setListOpen(suggestions, true);
      return;
    }

    matches.forEach((e, i) => {
      const option = document.createElement('button');
      option.type = 'button';
      option.className = 'jsonld-suggestion';
      option.setAttribute('role', 'option');
      option.setAttribute('aria-selected', 'false');
      option.id = `jsonld-suggestion-${i}`;
      option.textContent = `${e.title} (${e.year || '?'})`;
      option.addEventListener('click', () => this._pick(e, input, suggestions));
      suggestions.appendChild(option);
    });
    this._setListOpen(suggestions, true);
  },

  /** Open state of the suggestion list, mirrored onto the combobox. */
  _setListOpen(suggestions, open) {
    suggestions.classList.toggle('hidden', !open);
    const input = document.getElementById('jsonld-search');
    if (input) input.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (!open && input) input.removeAttribute('aria-activedescendant');
  },

  _pick(entry, input, suggestions) {
    input.value = entry.title;
    this._setListOpen(suggestions, false);
    this._activeSuggestion = -1;
    this._loadEntry(entry);
  },

  /** Arrow keys walk the suggestions, Enter takes the marked one, Escape closes. */
  _onSearchKey(ev, input, suggestions) {
    if (ev.ctrlKey || ev.metaKey || ev.altKey) return;
    const options = [...suggestions.querySelectorAll('.jsonld-suggestion[role="option"]')];
    if (ev.key === 'Escape') {
      this._setListOpen(suggestions, false);
      this._activeSuggestion = -1;
      return;
    }
    if (!options.length || suggestions.classList.contains('hidden')) return;
    if (ev.key === 'ArrowDown' || ev.key === 'ArrowUp') {
      ev.preventDefault();
      const step = ev.key === 'ArrowDown' ? 1 : -1;
      // From "nothing marked", Down opens at the first and Up at the last.
      const from = this._activeSuggestion < 0 ? (step === 1 ? -1 : 0) : this._activeSuggestion;
      this._activeSuggestion = (from + step + options.length) % options.length;
      options.forEach((el, i) => {
        const on = i === this._activeSuggestion;
        el.setAttribute('aria-selected', on ? 'true' : 'false');
        el.classList.toggle('is-active', on);
        if (on) {
          el.scrollIntoView({ block: 'nearest' });
          input.setAttribute('aria-activedescendant', el.id);
        }
      });
    } else if (ev.key === 'Enter' && this._activeSuggestion >= 0) {
      ev.preventDefault();
      options[this._activeSuggestion].click();
    }
  },

  /** Load a random ns-0 entry */
  _loadRandom() {
    const ns0 = App.entries.filter(e => e.title && e.pageNamespace === 0);
    const entry = ns0[Math.floor(Math.random() * ns0.length)];
    const input = document.getElementById('jsonld-search');
    if (input) input.value = entry.title || '';
    this._loadEntry(entry);
  },

  /** Load and render an entry in all tabs */
  _loadEntry(entry) {
    this.currentEntry = entry;
    const compact = this._toCompactJsonld(entry);
    const expanded = this._toExpandedJsonld(compact);
    const triples = this._toTriples(expanded);

    // Compact view
    const compactEl = document.getElementById('jsonld-compact');
    if (compactEl) compactEl.innerHTML = this._syntaxHighlight(compact);

    // Expanded view
    const expandedEl = document.getElementById('jsonld-expanded');
    if (expandedEl) expandedEl.innerHTML = this._syntaxHighlight(expanded);

    // Triples view
    const triplesEl = document.getElementById('jsonld-triples');
    if (triplesEl) triplesEl.innerHTML = this._renderTriples(triples);

    // Stats
    const statsEl = document.getElementById('jsonld-stats');
    if (statsEl) {
      statsEl.textContent = `${Object.keys(compact).length - 1} properties | ${triples.length} triples | @id: ${compact['@id']}`;
    }
  },

  /** Convert frontend entry back to compact JSON-LD with @context */
  _toCompactJsonld(entry) {
    const jsonld = {
      '@context': this.CONTEXT,
    };

    // Copy fields, mapping frontend keys back to JSON-LD keys
    for (const [key, val] of Object.entries(entry)) {
      if (val == null || val === '') continue;
      if (key.startsWith('@')) {
        jsonld[key] = val;
        continue;
      }
      const jsonldKey = this.FRONTEND_TO_JSONLD[key] || key;
      // Convert year int back to string for datePublished
      if (jsonldKey === 'datePublished') {
        jsonld[jsonldKey] = String(val);
      } else {
        jsonld[jsonldKey] = val;
      }
    }

    // Add author for primary works
    if (!ABOUT_ZWEIG_TYPES.includes(entry.entryType) && entry.entryType !== 'redirect') {
      jsonld['author'] = this.STEFAN_ZWEIG;
    }

    return jsonld;
  },

  /** Expand compact JSON-LD — resolve all prefixes to full URIs */
  _toExpandedJsonld(compact) {
    const ctx = compact['@context'] || this.CONTEXT;
    const prefixes = {};
    const termDefs = {};

    // Separate prefix declarations from term definitions
    for (const [key, val] of Object.entries(ctx)) {
      if (key.startsWith('@')) continue;
      if (typeof val === 'string' && val.endsWith('/')) {
        prefixes[key] = val;
      } else if (typeof val === 'string') {
        termDefs[key] = { '@id': val };
      } else if (typeof val === 'object' && val['@id']) {
        termDefs[key] = val;
      }
    }

    const expandPrefix = (v) => {
      if (typeof v !== 'string') return v;
      const colon = v.indexOf(':');
      if (colon > 0) {
        const prefix = v.substring(0, colon);
        if (prefixes[prefix]) return prefixes[prefix] + v.substring(colon + 1);
      }
      return v;
    };

    const expanded = {};
    for (const [key, val] of Object.entries(compact)) {
      if (key === '@context') continue;
      if (key === '@type') {
        expanded['@type'] = Array.isArray(val) ? val.map(expandPrefix) : expandPrefix(val);
        continue;
      }
      if (key === '@id') {
        expanded['@id'] = expandPrefix(val);
        continue;
      }

      // Resolve term to full IRI
      const def = termDefs[key];
      const fullKey = def ? expandPrefix(def['@id']) : expandPrefix(key);

      // Expand value
      if (typeof val === 'object' && val !== null && !Array.isArray(val)) {
        // Nested object (like author)
        const nested = {};
        for (const [nk, nv] of Object.entries(val)) {
          if (nk === '@type') { nested['@type'] = expandPrefix(nv); continue; }
          if (nk === '@id') { nested['@id'] = expandPrefix(nv); continue; }
          const nDef = termDefs[nk];
          const nFullKey = nDef ? expandPrefix(nDef['@id']) : expandPrefix(nk);
          nested[nFullKey] = nv;
        }
        expanded[fullKey] = nested;
      } else if (def && def['@type'] === 'xsd:integer') {
        expanded[fullKey] = { '@value': val, '@type': expandPrefix('xsd:integer') };
      } else if (def && def['@type'] === 'xsd:gYear') {
        expanded[fullKey] = { '@value': val, '@type': expandPrefix('xsd:gYear') };
      } else if (def && def['@type'] === '@id') {
        expanded[fullKey] = { '@id': expandPrefix(val) };
      } else {
        expanded[fullKey] = val;
      }
    }
    return expanded;
  },

  /** Extract subject-predicate-object triples from expanded JSON-LD */
  _toTriples(expanded) {
    const triples = [];
    const subject = expanded['@id'] || '(blank)';

    for (const [pred, obj] of Object.entries(expanded)) {
      if (pred === '@id') continue;
      if (pred === '@type') {
        const types = Array.isArray(obj) ? obj : [obj];
        types.forEach(t => triples.push([subject, 'rdf:type', t]));
        continue;
      }

      if (Array.isArray(obj)) {
        obj.forEach(item => triples.push([subject, pred, this._formatObject(item)]));
      } else if (typeof obj === 'object' && obj !== null) {
        if ('@value' in obj) {
          triples.push([subject, pred, `"${obj['@value']}"^^${obj['@type'] || 'xsd:string'}`]);
        } else if ('@id' in obj && Object.keys(obj).length === 1) {
          triples.push([subject, pred, obj['@id']]);
        } else {
          // Nested object — add as blank node
          const bnode = obj['@id'] || '_:author';
          triples.push([subject, pred, bnode]);
          for (const [nk, nv] of Object.entries(obj)) {
            if (nk === '@id') continue;
            if (nk === '@type') { triples.push([bnode, 'rdf:type', nv]); continue; }
            triples.push([bnode, nk, this._formatObject(nv)]);
          }
        }
      } else {
        triples.push([subject, pred, `"${obj}"`]);
      }
    }
    return triples;
  },

  _formatObject(val) {
    if (typeof val === 'object' && val !== null) {
      if ('@value' in val) return `"${val['@value']}"^^${val['@type'] || 'xsd:string'}`;
      if ('@id' in val) return val['@id'];
      return JSON.stringify(val);
    }
    if (typeof val === 'number') return `"${val}"^^http://www.w3.org/2001/XMLSchema#integer`;
    return `"${val}"`;
  },

  /** Syntax-highlight a JSON object */
  _syntaxHighlight(obj) {
    // Escape before highlighting: JSON.stringify keeps < > & literally,
    // and titles in the data do contain angle brackets.
    const json = JSON.stringify(obj, null, 2)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
    return json.replace(
      /("(?:\\u[\da-fA-F]{4}|\\[^u]|[^\\"])*")\s*:?|(\btrue\b|\bfalse\b|\bnull\b)|(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)/g,
      (match, str, bool, num) => {
        if (str) {
          if (/:$/.test(match)) {
            // Key
            const clean = str.replace(/"/g, '');
            if (clean.startsWith('@')) return `<span class="jh-ctx">${str}</span>:`;
            if (clean.startsWith('http')) return `<span class="jh-uri">${str}</span>:`;
            return `<span class="jh-key">${str}</span>:`;
          }
          // String value
          const clean = str.replace(/"/g, '');
          if (clean.startsWith('http')) return `<span class="jh-uri">${str}</span>`;
          if (clean.startsWith('schema:') || clean.startsWith('klawiter:') || clean.startsWith('dcterms:') || clean.startsWith('xsd:'))
            return `<span class="jh-prefix">${str}</span>`;
          return `<span class="jh-str">${str}</span>`;
        }
        if (bool) return `<span class="jh-bool">${match}</span>`;
        if (num) return `<span class="jh-num">${match}</span>`;
        return match;
      }
    );
  },

  /** Render triples as an HTML table */
  _renderTriples(triples) {
    if (triples.length === 0) return '<p>No triples.</p>';
    const rows = triples.map(([s, p, o]) => {
      const fmtUri = (v) => {
        if (typeof v === 'string' && v.startsWith('http')) {
          // Shorten known prefixes for readability
          const short = v
            .replace('https://schema.org/', 'schema:')
            .replace('http://purl.org/dc/terms/', 'dcterms:')
            .replace('https://chpollin.github.io/klawiter-rescue/vocab/', 'klawiter:')
            .replace('http://www.w3.org/2001/XMLSchema#', 'xsd:')
            .replace('http://www.w3.org/1999/02/22-rdf-syntax-ns#', 'rdf:');
          return `<span class="jh-prefix" title="${esc(v)}">${esc(short)}</span>`;
        }
        if (typeof v === 'string' && v.startsWith('"')) {
          return `<span class="jh-str">${esc(v)}</span>`;
        }
        return `<span class="jh-uri">${esc(v)}</span>`;
      };
      return `<tr><td>${fmtUri(s)}</td><td>${fmtUri(p)}</td><td>${fmtUri(o)}</td></tr>`;
    }).join('');
    return `<table class="page-table triples-table">
      <thead><tr><th>Subject</th><th>Predicate</th><th>Object</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
  },

  /** Switch the active view. Three toggle buttons, not a tab widget. */
  _switchTab(tabId) {
    document.querySelectorAll('.jsonld-tab').forEach(t => {
      const on = t.dataset.tab === tabId;
      t.classList.toggle('active', on);
      t.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
    document.querySelectorAll('.jsonld-panel').forEach(p =>
      p.classList.toggle('hidden', p.id !== `jsonld-${tabId}`)
    );
  },
};

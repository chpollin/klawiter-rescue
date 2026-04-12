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

  /** Entry types that are ABOUT Zweig (no author field) */
  ABOUT_ZWEIG_TYPES: new Set([
    'secondary-literature', 'historical-study', 'symposium', 'other',
  ]),

  currentEntry: null,

  /** Initialize after page render */
  init() {
    const searchInput = document.getElementById('jsonld-search');
    const randomBtn = document.getElementById('jsonld-random');
    const suggestions = document.getElementById('jsonld-suggestions');

    if (!searchInput) return;

    searchInput.addEventListener('input', () => this._onSearch(searchInput, suggestions));
    searchInput.addEventListener('focus', () => {
      if (suggestions.children.length > 0) suggestions.classList.remove('hidden');
    });
    randomBtn.addEventListener('click', () => this._loadRandom());
    document.addEventListener('click', (e) => {
      if (!e.target.closest('.jsonld-search-wrap')) suggestions.classList.add('hidden');
    });

    // Tab switching
    document.querySelectorAll('.jsonld-tab').forEach(tab => {
      tab.addEventListener('click', () => this._switchTab(tab.dataset.tab));
    });

    // Load a random entry on init
    this._loadRandom();
  },

  /** Search entries by title */
  _onSearch(input, suggestions) {
    const q = input.value.trim().toLowerCase();
    suggestions.innerHTML = '';
    if (q.length < 2) { suggestions.classList.add('hidden'); return; }

    const matches = App.entries
      .filter(e => e.title && e.title.toLowerCase().includes(q))
      .slice(0, 8);

    if (matches.length === 0) { suggestions.classList.add('hidden'); return; }

    matches.forEach(e => {
      const li = document.createElement('div');
      li.className = 'jsonld-suggestion';
      li.textContent = `${e.title} (${e.year || '?'})`;
      li.addEventListener('click', () => {
        input.value = e.title;
        suggestions.classList.add('hidden');
        this._loadEntry(e);
      });
      suggestions.appendChild(li);
    });
    suggestions.classList.remove('hidden');
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
    if (!this.ABOUT_ZWEIG_TYPES.has(entry.entryType) && entry.entryType !== 'redirect') {
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
    const json = JSON.stringify(obj, null, 2);
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

  /** Switch active tab */
  _switchTab(tabId) {
    document.querySelectorAll('.jsonld-tab').forEach(t =>
      t.classList.toggle('active', t.dataset.tab === tabId)
    );
    document.querySelectorAll('.jsonld-panel').forEach(p =>
      p.classList.toggle('hidden', p.id !== `jsonld-${tabId}`)
    );
  },
};

/**
 * Explore Network — Connections between entries.
 *
 * Sub-mode 1 (Cross-References): ranked list of the most-referenced entries.
 * A bibliography answers "which works are referenced most, and from where";
 * the earlier global bubble graph answered neither (its largest node was the
 * small-cluster aggregate), so it was replaced by this ranking. Each row
 * expands to the referencing entries; entry-level neighborhood stays on the
 * entry card (See Also).
 *
 * Sub-mode 2 (Translators): Sankey flow diagram, type → language → translator.
 */
const ExploreNetwork = {
  svg: null,

  // Raw reference graph: links are directed source → target (source's
  // seeAlso resolves to target).
  nodes: [],
  links: [],

  subMode: 'references',     // 'references' | 'translators'

  // Translator Sankey state
  _activePeriod: 'all',

  _lastEntries: null,

  // =========================================================================
  // Entry point
  // =========================================================================

  render(entries) {
    this._lastEntries = entries;
    const container = document.getElementById('viz-network');
    if (!container) return;
    container.innerHTML = '';

    // Cross-view filter listener
    this._bindFilterListener();

    // Sub-mode toggle
    const toggle = document.createElement('div');
    toggle.className = 'network-submode-tabs';
    toggle.innerHTML = `
      <button class="geo-toggle ${this.subMode === 'references' ? 'active' : ''}" data-sub="references">Cross-References</button>
      <button class="geo-toggle ${this.subMode === 'translators' ? 'active' : ''}" data-sub="translators">Translators</button>
    `;
    container.appendChild(toggle);
    toggle.querySelectorAll('.geo-toggle').forEach(btn => {
      btn.addEventListener('click', () => {
        this.subMode = btn.dataset.sub;
        this.render(entries);
      });
    });

    if (this.subMode === 'references') {
      this._renderReferences(container, entries);
    } else {
      this._renderTranslators(container, entries);
    }
  },

  // =========================================================================
  // Cross-Reference ranking
  // =========================================================================

  _renderReferences(container, entries) {
    this._buildGraph(entries);

    if (this.nodes.length === 0) {
      container.innerHTML += `
        <div class="ov-empty" style="text-align:center;padding:3rem">
          <p>No cross-references found in the current dataset.</p>
          <p style="font-size:0.8rem;color:var(--sz-text-light)">
            ${entries.filter(e => e.seeAlso && e.seeAlso.length).length} entries have cross-references,
            but not enough could be resolved to build a ranking.
          </p>
        </div>
      `;
      return;
    }

    const ranked = this._rankTargets();
    const referencing = new Set(this.links.map(l => l.source));

    // Info bar
    const totalEntries = this._lastEntries ? this._lastEntries.length : this.nodes.length;
    const coveragePct = totalEntries > 0
      ? (this.nodes.length / totalEntries * 100).toFixed(1) : '0.0';
    const info = document.createElement('div');
    info.className = 'network-info';
    info.innerHTML = `
      <span class="ov-title" style="margin-bottom:0">Most Referenced Entries</span>
      <span style="font-size:0.75rem;color:var(--sz-text-light)">
        ${this.nodes.length.toLocaleString('en')} of ${totalEntries.toLocaleString('en')} entries connected (${coveragePct}%) ·
        ${this.links.length.toLocaleString('en')} resolved reference links
      </span>
    `;
    container.appendChild(info);

    // Ranked list: each row expands to the entries referencing this target.
    const maxCount = ranked.length ? ranked[0].sources.length : 1;
    const list = document.createElement('div');
    list.className = 'reference-ranking';
    list.innerHTML = ranked.slice(0, 50).map((row, i) => {
      const entry = App.entryMap.get(row.id);
      if (!entry) return '';
      const barWidth = Math.max(2, Math.round(100 * row.sources.length / maxCount));
      const sources = row.sources
        .map(pid => App.entryMap.get(pid))
        .filter(Boolean)
        .sort((a, b) => (a.year ?? 9999) - (b.year ?? 9999));
      const sourceList = sources.map(s =>
        `<li><a href="#entry=${s.sourcePageId}">${esc(s.title || 'Untitled')}</a>${s.year ? ` <span class="detail-entry-year">${s.year}</span>` : ''}</li>`
      ).join('');
      return `<details class="reference-rank-row">
        <summary>
          <span class="reference-rank-pos">${i + 1}</span>
          <span class="reference-rank-main">
            <span class="badge badge-${entry.entryType}">${ENTRY_TYPE_LABELS[entry.entryType] || entry.entryType}</span>
            <a href="#entry=${row.id}">${esc(entry.title || 'Untitled')}</a>
            ${entry.year ? `<span class="detail-entry-year">${entry.year}</span>` : ''}
          </span>
          <span class="reference-rank-count" title="Referenced by ${row.sources.length} entries">
            <span class="reference-rank-bar" style="width:${barWidth}%"></span>
            ${row.sources.length}
          </span>
        </summary>
        <ul class="reference-rank-sources">${sourceList}</ul>
      </details>`;
    }).join('');
    container.appendChild(list);

    if (ranked.length > 50) {
      const more = document.createElement('p');
      more.className = 'detail-more';
      more.textContent = `and ${(ranked.length - 50).toLocaleString('en')} more referenced entries with fewer links`;
      container.appendChild(more);
    }

    this._renderReferenceStats(ranked, referencing);
  },

  // Rank reference targets by how many distinct entries point at them.
  _rankTargets() {
    const inbound = new Map();   // targetId → Set of referencing sourcePageIds
    for (const l of this.links) {
      if (!inbound.has(l.target)) inbound.set(l.target, new Set());
      inbound.get(l.target).add(l.source);
    }
    return [...inbound.entries()]
      .map(([id, set]) => ({ id, sources: [...set] }))
      .sort((a, b) => b.sources.length - a.sources.length
        || (App.entryMap.get(a.id)?.title || '').localeCompare(App.entryMap.get(b.id)?.title || ''));
  },

  _renderReferenceStats(ranked, referencing) {
    const panel = document.getElementById('explore-detail');
    const detail = document.getElementById('explore-detail-content');
    if (!panel || !detail) return;
    if (Explore.selection.length > 0) return;

    panel.classList.remove('hidden');
    detail.innerHTML = `
      <div class="detail-summary">
        <h3 class="detail-summary-title">Reference Network</h3>
        <div class="network-stats-grid">
          <div class="network-stat"><strong>${this.links.length.toLocaleString('en')}</strong><span>Resolved links</span></div>
          <div class="network-stat"><strong>${ranked.length.toLocaleString('en')}</strong><span>Referenced entries</span></div>
          <div class="network-stat"><strong>${referencing.size.toLocaleString('en')}</strong><span>Referencing entries</span></div>
          <div class="network-stat"><strong>${ranked.length ? ranked[0].sources.length : 0}</strong><span>Top in-degree</span></div>
        </div>
        <p class="detail-summary-hint">Expand a row for the entries citing it; open any entry for its own See-Also neighborhood. Unresolvable references are listed under Data Quality.</p>
      </div>
    `;
  },

  // =========================================================================
  // Data building
  // =========================================================================

  _buildGraph(entries) {
    const nodeMap = new Map();
    const links = [];

    for (const entry of entries) {
      if (!entry.seeAlso || !entry.seeAlso.length) continue;
      for (const ref of entry.seeAlso) {
        let targetId = App.titleMap.get(ref);
        if (!targetId && App.data && App.data.redirects) {
          targetId = App.data.redirects[ref];
        }
        if (!targetId || !App.entryMap.has(targetId)) continue;

        const sourceId = entry.sourcePageId;
        if (sourceId === targetId) continue;

        if (!nodeMap.has(sourceId)) {
          nodeMap.set(sourceId, {
            id: sourceId, title: entry.title, entryType: entry.entryType,
            year: entry.year, language: entry.language, degree: 0,
          });
        }
        const target = App.entryMap.get(targetId);
        if (!nodeMap.has(targetId)) {
          nodeMap.set(targetId, {
            id: targetId, title: target.title, entryType: target.entryType,
            year: target.year, language: target.language, degree: 0,
          });
        }
        links.push({ source: sourceId, target: targetId });
        nodeMap.get(sourceId).degree++;
        nodeMap.get(targetId).degree++;
      }
    }

    this.nodes = [...nodeMap.values()];
    this.links = links;
  },

  // =========================================================================
  // Translator Sankey Flow Diagram
  // Ref: SankeyNetwork (2025, doi:10.1016/j.mex.2025.103230) —
  //      Sankey diagrams for bibliometric flow visualization.
  // Three columns: Entry Type → Language → Top Translator
  // =========================================================================

  _renderTranslators(container, entries) {
    const withTranslator = entries.filter(e => e.translator);
    if (withTranslator.length === 0) {
      container.innerHTML += `
        <div class="ov-empty" style="text-align:center;padding:3rem">
          <p>No translators found in the current dataset.</p>
        </div>
      `;
      return;
    }

    // Period filter
    this._activePeriod = this._activePeriod || 'all';
    const periods = [
      { key: 'all', label: 'All periods' },
      { key: 'lifetime', label: '1881–1942', min: 1881, max: 1942 },
      { key: 'post-wwii', label: '1943–1980', min: 1943, max: 1980 },
      { key: 'late-20c', label: '1981–2000', min: 1981, max: 2000 },
      { key: 'contemporary', label: '2001–', min: 2001, max: 2030 },
    ];

    const filterBar = document.createElement('div');
    filterBar.className = 'network-toolbar';
    filterBar.innerHTML = periods.map(p =>
      `<button class="geo-toggle ${this._activePeriod === p.key ? 'active' : ''}" data-period="${p.key}">${p.label}</button>`
    ).join('');
    container.appendChild(filterBar);

    filterBar.querySelectorAll('.geo-toggle').forEach(btn => {
      btn.addEventListener('click', () => {
        this._activePeriod = btn.dataset.period;
        this.render(this._lastEntries);
      });
    });

    // Filter entries by period
    const period = periods.find(p => p.key === this._activePeriod);
    const filtered = period && period.min
      ? withTranslator.filter(e => e.year >= period.min && e.year <= period.max)
      : withTranslator;

    if (filtered.length === 0) {
      container.innerHTML += `<div style="text-align:center;padding:2rem;color:var(--sz-text-light)">No translator entries in this period.</div>`;
      return;
    }

    // Build Sankey data
    const sankeyData = this._buildTranslatorSankey(filtered);

    // Info bar
    const totalEntries = this._lastEntries ? this._lastEntries.length : 0;
    const coveragePct = totalEntries > 0
      ? (withTranslator.length / totalEntries * 100).toFixed(1) : '0.0';

    const info = document.createElement('div');
    info.className = 'network-info';
    info.innerHTML = `
      <span class="ov-title" style="margin-bottom:0">Translation Flows</span>
      <span style="font-size:0.75rem;color:var(--sz-text-light)">
        ${filtered.length.toLocaleString('en')} translations by ${sankeyData.translatorCount} translators into ${sankeyData.langCount} languages (${coveragePct}% coverage)
      </span>
    `;
    container.appendChild(info);

    // Render Sankey
    this._renderSankey(container, sankeyData, filtered);

    // Stats panel
    this._renderTranslatorStats(filtered, sankeyData);
  },

  _buildTranslatorSankey(entries) {
    // Count: type → language, language → translator
    const typeLangCounts = new Map();  // "type|lang" → count
    const langTransCounts = new Map(); // "lang|translator" → count
    const translatorNames = new Map(); // normalized → display name
    const translatorTotals = new Map();

    for (const e of entries) {
      const type = e.entryType || 'other';
      const lang = e.language || 'Unknown';
      const normName = normalizeTranslator(e.translator);
      if (!normName || normName.length < 2) continue;

      const tlKey = `${type}|${lang}`;
      typeLangCounts.set(tlKey, (typeLangCounts.get(tlKey) || 0) + 1);

      const ltKey = `${lang}|${normName}`;
      langTransCounts.set(ltKey, (langTransCounts.get(ltKey) || 0) + 1);

      if (!translatorNames.has(normName)) translatorNames.set(normName, e.translator.trim());
      translatorTotals.set(normName, (translatorTotals.get(normName) || 0) + 1);
    }

    // Top languages (by entry count)
    const langTotals = new Map();
    for (const [key, count] of typeLangCounts) {
      const lang = key.split('|')[1];
      langTotals.set(lang, (langTotals.get(lang) || 0) + count);
    }
    const topLangs = [...langTotals.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 12)
      .map(([l]) => l);
    const topLangSet = new Set(topLangs);

    // Top translators (by entry count)
    const topTranslators = [...translatorTotals.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 20)
      .map(([t]) => t);
    const topTransSet = new Set(topTranslators);

    // Top entry types
    const typeTotals = new Map();
    for (const [key, count] of typeLangCounts) {
      const type = key.split('|')[0];
      typeTotals.set(type, (typeTotals.get(type) || 0) + count);
    }
    const topTypes = [...typeTotals.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 8)
      .map(([t]) => t);
    const topTypeSet = new Set(topTypes);

    // Build node list: types (col 0), languages (col 1), translators (col 2)
    const nodes = [];
    const nodeIndex = new Map();

    const addNode = (name, col, category) => {
      if (nodeIndex.has(name + '|' + col)) return nodeIndex.get(name + '|' + col);
      const idx = nodes.length;
      nodes.push({ name, col, category });
      nodeIndex.set(name + '|' + col, idx);
      return idx;
    };

    for (const t of topTypes) addNode(ENTRY_TYPE_LABELS[t] || t, 0, t);
    addNode('Other types', 0, '_other_type');
    for (const l of topLangs) addNode(l, 1, l);
    addNode('Other languages', 1, '_other_lang');
    for (const t of topTranslators) {
      addNode(translatorNames.get(t) || t, 2, t);
    }
    addNode('Other translators', 2, '_other_trans');

    // Build links
    const links = [];
    const linkMap = new Map();

    const addLink = (s, t, v) => {
      const key = `${s}->${t}`;
      if (linkMap.has(key)) {
        linkMap.get(key).value += v;
      } else {
        const link = { source: s, target: t, value: v };
        linkMap.set(key, link);
        links.push(link);
      }
    };

    // Type → Language links
    for (const [key, count] of typeLangCounts) {
      const [type, lang] = key.split('|');
      const typeNode = topTypeSet.has(type)
        ? nodeIndex.get((ENTRY_TYPE_LABELS[type] || type) + '|0')
        : nodeIndex.get('Other types|0');
      const langNode = topLangSet.has(lang)
        ? nodeIndex.get(lang + '|1')
        : nodeIndex.get('Other languages|1');
      addLink(typeNode, langNode, count);
    }

    // Language → Translator links
    for (const [key, count] of langTransCounts) {
      const [lang, trans] = key.split('|');
      const langNode = topLangSet.has(lang)
        ? nodeIndex.get(lang + '|1')
        : nodeIndex.get('Other languages|1');
      const transNode = topTransSet.has(trans)
        ? nodeIndex.get((translatorNames.get(trans) || trans) + '|2')
        : nodeIndex.get('Other translators|2');
      addLink(langNode, transNode, count);
    }

    // Filter out zero-value links and orphan nodes
    const validLinks = links.filter(l => l.value > 0);

    return {
      nodes, links: validLinks,
      translatorCount: translatorTotals.size,
      langCount: langTotals.size,
      topTranslators: topTranslators.map(t => ({
        id: t, name: translatorNames.get(t) || t, count: translatorTotals.get(t),
      })),
    };
  },

  _renderSankey(container, sankeyData, entries) {
    const rect = container.getBoundingClientRect();
    const width = rect.width || 700;
    const height = CHART_DIMS.network.height;
    const margin = { top: 10, right: 10, bottom: 10, left: 10 };

    const innerW = width - margin.left - margin.right;
    const innerH = height - margin.top - margin.bottom;

    // d3-sankey layout
    const sankey = d3.sankey()
      .nodeId(d => d.index)
      .nodeAlign(d3.sankeyLeft)
      .nodeWidth(18)
      .nodePadding(6)
      .extent([[0, 0], [innerW, innerH]]);

    const graph = sankey({
      nodes: sankeyData.nodes.map(d => ({ ...d })),
      links: sankeyData.links.map(d => ({ ...d })),
    });

    // Language color for links
    const langColor = (name) => {
      return Explore.colors.languages[name] || Explore.colors.languages['Other'] || '#9E9585';
    };

    // Node color by column
    const nodeColor = (d) => {
      if (d.col === 0) {
        // Entry type column
        return Explore.colors.types[d.category] || COLORS.burgundy;
      }
      if (d.col === 1) {
        // Language column
        return langColor(d.category === '_other_lang' ? 'Other' : d.name);
      }
      // Translator column — color by their dominant source language
      const inLinks = graph.links.filter(l => l.target === d);
      if (inLinks.length > 0) {
        const biggest = inLinks.reduce((a, b) => a.value > b.value ? a : b);
        const langNode = graph.nodes[biggest.source.index || biggest.source];
        return langColor(langNode ? langNode.name : 'Other');
      }
      return '#9E9585';
    };

    // SVG
    this.svg = d3.select(container).append('svg')
      .attr('class', 'explore-svg')
      .attr('viewBox', `0 0 ${width} ${height}`)
      .attr('preserveAspectRatio', 'xMidYMid meet')
      .attr('role', 'img')
      .attr('aria-label', 'Translator flow diagram');

    const g = this.svg.append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Links (flows)
    const link = g.append('g')
      .attr('fill', 'none')
      .selectAll('path')
      .data(graph.links)
      .join('path')
      .attr('d', d3.sankeyLinkHorizontal())
      .attr('stroke', d => {
        // Color by the language node (col 1) in the flow
        const langNode = d.source.col === 1 ? d.source : d.target.col === 1 ? d.target : d.source;
        return langColor(langNode.name);
      })
      .attr('stroke-opacity', 0.35)
      .attr('stroke-width', d => Math.max(1, d.width))
      .style('mix-blend-mode', 'multiply');

    // Nodes
    const node = g.append('g')
      .selectAll('rect')
      .data(graph.nodes)
      .join('rect')
      .attr('x', d => d.x0)
      .attr('y', d => d.y0)
      .attr('height', d => Math.max(1, d.y1 - d.y0))
      .attr('width', d => d.x1 - d.x0)
      .attr('fill', nodeColor)
      .attr('stroke', Explore.colors.cream)
      .attr('stroke-width', 0.5)
      .style('cursor', 'pointer');

    // Node labels
    g.append('g')
      .selectAll('text')
      .data(graph.nodes)
      .join('text')
      .attr('x', d => d.col === 2 ? d.x0 - 6 : d.x1 + 6)
      .attr('y', d => (d.y0 + d.y1) / 2)
      .attr('dy', '0.35em')
      .attr('text-anchor', d => d.col === 2 ? 'end' : 'start')
      .attr('font-size', d => {
        const h = d.y1 - d.y0;
        return h > 14 ? '10px' : h > 8 ? '8px' : '0px'; // hide tiny labels
      })
      .attr('font-family', 'system-ui, sans-serif')
      .attr('fill', '#333')
      .attr('paint-order', 'stroke')
      .attr('stroke', 'white')
      .attr('stroke-width', 2)
      .text(d => {
        const v = d.value || 0;
        const maxChars = d.col === 1 ? 15 : 25;
        const name = d.name.length > maxChars ? d.name.slice(0, maxChars - 1) + '…' : d.name;
        return d.y1 - d.y0 > 8 ? `${name} (${v})` : '';
      });

    // Column headers
    const colLabels = ['Work Type', 'Language', 'Translator'];
    g.append('g').selectAll('text')
      .data([0, 1, 2])
      .join('text')
      .attr('x', col => {
        const colNodes = graph.nodes.filter(n => n.col === col);
        if (colNodes.length === 0) return 0;
        return col === 2
          ? colNodes[0].x0 - 6
          : colNodes[0].x1 + 6;
      })
      .attr('y', -2)
      .attr('text-anchor', col => col === 2 ? 'end' : 'start')
      .attr('font-size', '10px')
      .attr('font-family', 'system-ui, sans-serif')
      .attr('font-weight', '600')
      .attr('fill', COLORS.burgundy)
      .text(col => colLabels[col]);

    // Hover interactions
    node.on('mouseenter', (event, d) => {
      // Highlight connected links
      link.attr('stroke-opacity', l =>
        (l.source === d || l.target === d) ? 0.7 : 0.08
      );
      node.attr('opacity', n => {
        if (n === d) return 1;
        const connected = graph.links.some(l =>
          (l.source === d && l.target === n) || (l.target === d && l.source === n)
        );
        return connected ? 1 : 0.3;
      });

      const inflow = (d.targetLinks || []).reduce((s, l) => s + l.value, 0);
      const outflow = (d.sourceLinks || []).reduce((s, l) => s + l.value, 0);

      Explore.showTooltip(
        `<strong>${esc(d.name)}</strong><br>` +
        `${d.value || 0} entries<br>` +
        (inflow ? `<small>← ${inflow} inflow</small><br>` : '') +
        (outflow ? `<small>→ ${outflow} outflow</small>` : ''),
        event
      );
    })
    .on('mouseleave', () => {
      link.attr('stroke-opacity', 0.35);
      node.attr('opacity', 1);
      Explore.hideTooltip();
    })
    .on('click', (event, d) => {
      // Show entries for this node
      let filtered;
      if (d.col === 0) {
        filtered = entries.filter(e => (ENTRY_TYPE_LABELS[e.entryType] || e.entryType) === d.name || e.entryType === d.category);
      } else if (d.col === 1) {
        filtered = entries.filter(e => e.language === d.name || (d.category === '_other_lang' && !d.name.includes(e.language)));
      } else {
        filtered = entries.filter(e => e.translator && normalizeTranslator(e.translator) === d.category);
      }
      if (filtered.length) Explore.updateSelection(filtered.slice(0, 50));
    });

    // Link hover
    link.on('mouseenter', (event, d) => {
      link.attr('stroke-opacity', l => l === d ? 0.7 : 0.08);
      Explore.showTooltip(
        `<strong>${esc(d.source.name)} → ${esc(d.target.name)}</strong><br>` +
        `${d.value} entries`,
        event
      );
    })
    .on('mouseleave', () => {
      link.attr('stroke-opacity', 0.35);
      Explore.hideTooltip();
    });
  },

  _renderTranslatorStats(entries, sankeyData) {
    const panel = document.getElementById('explore-detail');
    const detail = document.getElementById('explore-detail-content');
    if (!panel || !detail) return;
    if (Explore.selection.length > 0) return;

    panel.classList.remove('hidden');

    const totalEntries = this._lastEntries ? this._lastEntries.length : 0;
    const coveragePct = totalEntries > 0
      ? (entries.length / totalEntries * 100).toFixed(1) : '0.0';

    // Language ranking
    const langCounts = new Map();
    for (const e of entries) {
      const lang = e.language || 'Unknown';
      langCounts.set(lang, (langCounts.get(lang) || 0) + 1);
    }
    const topLangs = [...langCounts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8);

    detail.innerHTML = `
      <div class="detail-summary">
        <h3 class="detail-summary-title">Translation Flows</h3>
        <div class="network-stats-grid">
          <div class="network-stat"><strong>${entries.length.toLocaleString('en')}</strong><span>Translations</span></div>
          <div class="network-stat"><strong>${sankeyData.translatorCount}</strong><span>Translators</span></div>
          <div class="network-stat"><strong>${sankeyData.langCount}</strong><span>Languages</span></div>
          <div class="network-stat"><strong>${coveragePct}%</strong><span>Coverage</span></div>
        </div>
        <div class="detail-group-section" style="margin-top:0.75rem">
          <h4>Top languages</h4>
          <ul class="detail-entry-list">
            ${topLangs.map(([lang, count]) => `
              <li class="detail-entry-item">
                <span class="detail-entry-link">
                  <span class="badge" style="background:${Explore.colors.languages[lang] || '#9E9585'};color:white">${count}</span>
                  ${esc(lang)}
                </span>
              </li>
            `).join('')}
          </ul>
        </div>
        <div class="detail-group-section" style="margin-top:0.75rem">
          <h4>Top translators</h4>
          <ul class="detail-entry-list">
            ${sankeyData.topTranslators.slice(0, 8).map(t => `
              <li class="detail-entry-item">
                <span class="detail-entry-link">
                  <span class="badge badge-fiction">${t.count}</span>
                  ${esc(t.name)}
                </span>
              </li>
            `).join('')}
          </ul>
        </div>
        <p class="detail-summary-hint">Hover flows for details. Click nodes for entries.</p>
      </div>
    `;
  },

  // =========================================================================
  // Brushed Linking
  // =========================================================================

  _bindFilterListener() {
    if (this._filterHandler) {
      document.removeEventListener('explore:filterChange', this._filterHandler);
    }
    this._filterHandler = (event) => {
      if (Explore.mode !== 'network') return;
      if (event.detail && event.detail.mode === 'network') return;
      const data = Explore.hasActiveFilters() ? Explore.getFiltered() : Explore.entries;
      this.render(data);
    };
    document.addEventListener('explore:filterChange', this._filterHandler);
  },

};

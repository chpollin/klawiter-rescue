/**
 * Explore Network — Connections between entries.
 *
 * Sub-mode 1 (Cross-References): ranked list of the most-referenced pages.
 * A bibliography answers "which pages are referenced most, and from where";
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

    // Reconcile this view when a filter changes elsewhere
    Explore.bindModeFilterListener('network', (filtered) => this.render(filtered));

    // Sub-mode toggle
    const toggle = document.createElement('div');
    toggle.className = 'network-submode-tabs';
    toggle.innerHTML = `
      <button type="button" class="geo-toggle ${this.subMode === 'references' ? 'active' : ''}"
        aria-pressed="${this.subMode === 'references'}" data-sub="references">Cross-References</button>
      <button type="button" class="geo-toggle ${this.subMode === 'translators' ? 'active' : ''}"
        aria-pressed="${this.subMode === 'translators'}" data-sub="translators">Translators</button>
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
            ${fmt(entries.filter(e => e.seeAlso && e.seeAlso.length).length)} entries have cross-references,
            but not enough could be resolved to build a ranking.
          </p>
        </div>
      `;
      return;
    }

    const ranked = this._rankTargets();
    const referencing = new Set(this.links.map(l => l.source));

    // Coverage over one and the same set: how many of the entries in view take
    // part in the reference graph. Targets resolved outside the current view
    // are counted separately, because they are not in the denominator.
    const inView = new Set(entries.map(e => e.sourcePageId));
    const connectedInView = this.nodes.filter(n => inView.has(n.id)).length;
    const external = this.nodes.length - connectedInView;
    const coveragePct = entries.length > 0
      ? (connectedInView / entries.length * 100).toFixed(1) : '0.0';

    const info = document.createElement('div');
    info.className = 'network-info';
    info.innerHTML = `
      <span class="ov-title" style="margin-bottom:0">Most referenced pages</span>
      <span style="font-size:0.75rem;color:var(--sz-text-light)">
        ${fmt(connectedInView)} of ${fmt(entries.length)} entries in view are connected (${coveragePct}%) ·
        ${fmt(this.links.length)} resolved reference links${external ? ` · ${fmt(external)} targets outside the current filter` : ''}
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
            <span class="badge">${ENTRY_TYPE_LABELS[entry.entryType] || entry.entryType}</span>
            <a href="#entry=${row.id}">${esc(entry.title || 'Untitled')}</a>
            ${entry.year ? `<span class="detail-entry-year">${entry.year}</span>` : ''}
          </span>
          <span class="reference-rank-count" title="Referenced by ${row.sources.length} entries">
            <span class="reference-rank-bar" style="width:${barWidth}%"></span>
            ${fmt(row.sources.length)}
          </span>
        </summary>
        <ul class="reference-rank-sources">${sourceList}</ul>
      </details>`;
    }).join('');
    container.appendChild(list);

    if (ranked.length > 50) {
      const more = document.createElement('p');
      more.className = 'detail-more';
      more.textContent = `and ${fmt(ranked.length - 50)} more referenced pages with fewer links`;
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
          <div class="network-stat"><strong>${fmt(this.links.length)}</strong><span>Resolved links</span></div>
          <div class="network-stat"><strong>${fmt(ranked.length)}</strong><span>Referenced pages</span></div>
          <div class="network-stat"><strong>${fmt(referencing.size)}</strong><span>Referencing entries</span></div>
          <div class="network-stat"><strong>${fmt(ranked.length ? ranked[0].sources.length : 0)}</strong><span>Top in-degree</span></div>
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
            year: entry.year, language: entry.language,
          });
        }
        const target = App.entryMap.get(targetId);
        if (!nodeMap.has(targetId)) {
          nodeMap.set(targetId, {
            id: targetId, title: target.title, entryType: target.entryType,
            year: target.year, language: target.language,
          });
        }
        links.push({ source: sourceId, target: targetId });
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
      `<button type="button" class="geo-toggle ${this._activePeriod === p.key ? 'active' : ''}"
        aria-pressed="${this._activePeriod === p.key}" data-period="${p.key}">${p.label}</button>`
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
        ${fmt(filtered.length)} translations by ${fmt(sankeyData.translatorCount)} translators into ${fmt(sankeyData.langCount)} languages (${coveragePct}% coverage)
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
    const translatorTotals = new Map();

    for (const e of entries) {
      const type = e.entryType || 'other';
      const lang = e.language || Explore.NOT_RECORDED;
      // A joint credit names two people; counting the whole string invents a
      // translator, and a value cut off mid-name is no evidence at all.
      const names = translatorKeys(e);
      if (!names.length) continue;

      const tlKey = `${type}|${lang}`;
      typeLangCounts.set(tlKey, (typeLangCounts.get(tlKey) || 0) + 1);

      for (const name of names) {
        const ltKey = `${lang}|${name}`;
        langTransCounts.set(ltKey, (langTransCounts.get(ltKey) || 0) + 1);
        translatorTotals.set(name, (translatorTotals.get(name) || 0) + 1);
      }
    }

    // Top languages — capped at the ten the palette can tell apart, so no two
    // language bands share a color.
    const langTotals = new Map();
    for (const [key, count] of typeLangCounts) {
      const lang = key.split('|')[1];
      langTotals.set(lang, (langTotals.get(lang) || 0) + count);
    }
    const topLangs = [...langTotals.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
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
    for (const t of topTranslators) addNode(t, 2, t);
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
      const sep = key.indexOf('|');
      const lang = key.slice(0, sep);
      const trans = key.slice(sep + 1);
      const langNode = topLangSet.has(lang)
        ? nodeIndex.get(lang + '|1')
        : nodeIndex.get('Other languages|1');
      const transNode = topTransSet.has(trans)
        ? nodeIndex.get(trans + '|2')
        : nodeIndex.get('Other translators|2');
      addLink(langNode, transNode, count);
    }

    return {
      nodes, links: links.filter(l => l.value > 0),
      translatorCount: translatorTotals.size,
      langCount: langTotals.size,
      topLangs,
      topTranslators: topTranslators.map(t => ({ id: t, name: t, count: translatorTotals.get(t) })),
    };
  },

  /**
   * Fold a set of node indices into a catch-all node and reindex.
   * Used after the first layout pass to collect translator bands too thin to
   * carry a label; an unlabelled sliver states nothing the reader can use.
   */
  _foldNodes(data, foldIdx, targetIdx) {
    const keep = data.nodes.map((_, i) => i).filter(i => !foldIdx.has(i));
    const remap = new Map();
    keep.forEach((oldIdx, newIdx) => remap.set(oldIdx, newIdx));
    for (const i of foldIdx) remap.set(i, remap.get(targetIdx));

    const nodes = keep.map(i => ({ ...data.nodes[i] }));
    const merged = new Map();
    for (const l of data.links) {
      const s = remap.get(l.source), t = remap.get(l.target);
      if (s == null || t == null || s === t) continue;
      const key = `${s}->${t}`;
      if (merged.has(key)) merged.get(key).value += l.value;
      else merged.set(key, { source: s, target: t, value: l.value });
    }
    return { ...data, nodes, links: [...merged.values()] };
  },

  _renderSankey(container, sankeyData, entries) {
    const rect = container.getBoundingClientRect();
    const width = rect.width || 700;
    const height = CHART_DIMS.network.height;
    const margin = { top: 16, right: 10, bottom: 10, left: 10 };

    const innerW = width - margin.left - margin.right;
    const innerH = height - margin.top - margin.bottom;

    const layout = (data) => d3.sankey()
      .nodeId(d => d.index)
      .nodeAlign(d3.sankeyLeft)
      .nodeWidth(18)
      .nodePadding(6)
      .extent([[0, 0], [innerW, innerH]])({
        nodes: data.nodes.map(d => ({ ...d })),
        links: data.links.map(d => ({ ...d })),
      });

    let data = sankeyData;
    let graph = layout(data);

    // Second pass: anything under 8px in the translator column cannot show a
    // name, so it joins "Other translators".
    const otherIdx = data.nodes.findIndex(n => n.category === '_other_trans');
    if (otherIdx >= 0) {
      const tiny = new Set(graph.nodes
        .filter(n => n.col === 2 && n.category !== '_other_trans' && (n.y1 - n.y0) < 8)
        .map(n => n.index));
      if (tiny.size) {
        data = this._foldNodes(data, tiny, otherIdx);
        graph = layout(data);
      }
    }

    // Language color for links
    const langColor = (name) =>
      Explore.colors.languages[name] || Explore.colors.languages['Other'] || '#9E9585';

    // Node color by column
    const nodeColor = (d) => {
      if (d.col === 0) return Explore.colors.types[d.category] || COLORS.burgundy;
      if (d.col === 1) return langColor(d.category === '_other_lang' ? 'Other' : d.name);
      // Translator column — color by their dominant source language
      const inLinks = graph.links.filter(l => l.target === d);
      if (inLinks.length > 0) {
        const biggest = inLinks.reduce((a, b) => a.value > b.value ? a : b);
        const langNode = biggest.source;
        return langColor(langNode ? langNode.name : 'Other');
      }
      return '#9E9585';
    };

    this.svg = d3.select(container).append('svg')
      .attr('class', 'explore-svg')
      .attr('viewBox', `0 0 ${width} ${height}`)
      .attr('preserveAspectRatio', 'xMidYMid meet')
      .attr('role', 'group')
      .attr('aria-labelledby', 'sankey-title sankey-desc');
    this.svg.append('title').attr('id', 'sankey-title').text('Translation flows');
    this.svg.append('desc').attr('id', 'sankey-desc').text(
      'Flow from work type through language to translator. The same figures are ' +
      'listed as keyboard-reachable rankings in the panel beside the diagram.'
    );

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
      .attr('font-size', d => (d.y1 - d.y0) > 14 ? '10px' : '8px')
      .attr('font-family', 'var(--font-sans)')
      .attr('fill', '#333')
      .attr('paint-order', 'stroke')
      .attr('stroke', 'white')
      .attr('stroke-width', 2)
      .text(d => {
        if ((d.y1 - d.y0) <= 8) return '';
        const maxChars = d.col === 1 ? 15 : 25;
        const name = d.name.length > maxChars ? d.name.slice(0, maxChars - 1) + '…' : d.name;
        return `${name} (${fmt(d.value || 0)})`;
      });

    // Column headers
    const colLabels = ['Work Type', 'Language', 'Translator'];
    g.append('g').selectAll('text')
      .data([0, 1, 2])
      .join('text')
      .attr('x', col => {
        const colNodes = graph.nodes.filter(n => n.col === col);
        if (colNodes.length === 0) return 0;
        return col === 2 ? colNodes[0].x0 - 6 : colNodes[0].x1 + 6;
      })
      .attr('y', -4)
      .attr('text-anchor', col => col === 2 ? 'end' : 'start')
      .attr('font-size', '10px')
      .attr('font-family', 'var(--font-sans)')
      .attr('font-weight', '600')
      .attr('fill', COLORS.burgundy)
      .text(col => colLabels[col]);

    // Hover interactions
    node.on('mouseenter', (event, d) => {
      link.attr('stroke-opacity', l => (l.source === d || l.target === d) ? 0.7 : 0.08);
      node.attr('opacity', n => {
        if (n === d) return 1;
        const connected = graph.links.some(l =>
          (l.source === d && l.target === n) || (l.target === d && l.source === n));
        return connected ? 1 : 0.3;
      });

      const inflow = (d.targetLinks || []).reduce((s, l) => s + l.value, 0);
      const outflow = (d.sourceLinks || []).reduce((s, l) => s + l.value, 0);

      Explore.showTooltip(
        `<strong>${esc(d.name)}</strong><br>` +
        `${fmt(d.value || 0)} entries<br>` +
        (inflow ? `<small>← ${fmt(inflow)} inflow</small><br>` : '') +
        (outflow ? `<small>→ ${fmt(outflow)} outflow</small>` : ''),
        event
      );
    })
    .on('mouseleave', () => {
      link.attr('stroke-opacity', 0.35);
      node.attr('opacity', 1);
      Explore.hideTooltip();
    })
    .on('click', (event, d) => this._selectSankeyNode(d, entries, sankeyData));

    // Link hover
    link.on('mouseenter', (event, d) => {
      link.attr('stroke-opacity', l => l === d ? 0.7 : 0.08);
      Explore.showTooltip(
        `<strong>${esc(d.source.name)} → ${esc(d.target.name)}</strong><br>${fmt(d.value)} entries`,
        event
      );
    })
    .on('mouseleave', () => {
      link.attr('stroke-opacity', 0.35);
      Explore.hideTooltip();
    });
  },

  /**
   * A node click sets the matching Explore filter where one exists. The three
   * catch-all nodes stand for a complement rather than a value, so they select
   * their records instead. The selection carries the whole match set; only the
   * rendering of it is capped, so the count on screen is the real count.
   */
  _selectSankeyNode(d, entries, sankeyData) {
    if (d.col === 0) {
      if (d.category !== '_other_type') { Explore.toggleFilter('types', d.category); return; }
      const top = new Set(sankeyData.nodes.filter(n => n.col === 0 && n.category !== '_other_type')
        .map(n => n.category));
      Explore.updateSelection(entries.filter(e => !top.has(e.entryType || 'other')));
      return;
    }
    if (d.col === 1) {
      if (d.category !== '_other_lang') { Explore.toggleFilter('languages', d.name); return; }
      // "Other languages" is the complement of the drawn top languages;
      // testing the label text matched almost every record.
      const top = new Set(sankeyData.topLangs);
      Explore.updateSelection(entries.filter(e => !top.has(e.language || Explore.NOT_RECORDED)));
      return;
    }
    if (d.category !== '_other_trans') { Explore.toggleFilter('translator', d.category); return; }
    const top = new Set(sankeyData.topTranslators.map(t => t.id));
    Explore.updateSelection(entries.filter(e => {
      const names = translatorKeys(e);
      return names.length && names.every(n => !top.has(n));
    }));
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
      const lang = e.language || Explore.NOT_RECORDED;
      langCounts.set(lang, (langCounts.get(lang) || 0) + 1);
    }
    const topLangs = [...langCounts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8);

    detail.innerHTML = `
      <div class="detail-summary">
        <h3 class="detail-summary-title">Translation Flows</h3>
        <div class="network-stats-grid">
          <div class="network-stat"><strong>${fmt(entries.length)}</strong><span>Translations</span></div>
          <div class="network-stat"><strong>${fmt(sankeyData.translatorCount)}</strong><span>Translators</span></div>
          <div class="network-stat"><strong>${fmt(sankeyData.langCount)}</strong><span>Languages</span></div>
          <div class="network-stat"><strong>${coveragePct}%</strong><span>Coverage</span></div>
        </div>
        <div class="detail-group-section" style="margin-top:0.75rem">
          <h4>Top languages</h4>
          <ul class="detail-entry-list">
            ${topLangs.map(([lang, count]) => `
              <li class="detail-entry-item">
                <button type="button" class="rank-filter-btn" data-kind="language" data-value="${esc(lang)}">
                  <span class="count-badge" style="background:${Explore.colors.languages[lang] || '#9E9585'}">${fmt(count)}</span>
                  ${esc(lang)}
                </button>
              </li>
            `).join('')}
          </ul>
        </div>
        <div class="detail-group-section" style="margin-top:0.75rem">
          <h4>Top translators</h4>
          <ul class="detail-entry-list">
            ${sankeyData.topTranslators.slice(0, 8).map(t => `
              <li class="detail-entry-item">
                <button type="button" class="rank-filter-btn" data-kind="translator" data-value="${esc(t.id)}">
                  <span class="count-badge">${fmt(t.count)}</span>
                  ${esc(t.name)}
                </button>
              </li>
            `).join('')}
          </ul>
        </div>
        <p class="detail-summary-hint">Hover a flow for its figures; the two rankings above filter from the keyboard.</p>
      </div>
    `;

    // The rankings are the keyboard path into the Sankey.
    detail.querySelectorAll('.rank-filter-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        if (btn.dataset.kind === 'language') Explore.toggleFilter('languages', btn.dataset.value);
        else Explore.toggleFilter('translator', btn.dataset.value);
      });
    });
  },
};

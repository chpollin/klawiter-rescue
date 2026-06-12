/**
 * Explore Network — Two-level network visualization of cross-references.
 *
 * Level 1 (Overview): Communities as meta-nodes. Each circle = one connected
 * component, sized by member count, labeled with the hub title. ~10-20 nodes.
 *
 * Level 2 (Detail): Drill-down into a single community. Shows all member nodes
 * with force layout, hub highlighting, degree filter.
 *
 * Sub-mode 2: Translators network (unchanged, flat force layout).
 */
const ExploreNetwork = {
  simulation: null,
  svg: null,

  // Raw graph
  nodes: [],
  links: [],
  communities: new Map(),    // nodeId → communityId

  // Aggregated for overview
  communityData: [],         // meta-node objects
  communityLinks: [],        // meta-link objects

  // View state
  viewLevel: 'overview',     // 'overview' | 'detail'
  activeCommunity: null,     // communityId for detail view (or language string for translators)
  minDegree: 1,              // degree filter (detail only)
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
        this.viewLevel = 'overview';
        this.activeCommunity = null;
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
  // Cross-Reference Network (two-level)
  // =========================================================================

  _renderReferences(container, entries) {
    this._buildGraph(entries);

    if (this.nodes.length === 0) {
      container.innerHTML += `
        <div class="ov-empty" style="text-align:center;padding:3rem">
          <p>No cross-references found in the current dataset.</p>
          <p style="font-size:0.8rem;color:var(--sz-text-light)">
            ${entries.filter(e => e.seeAlso && e.seeAlso.length).length} entries have cross-references,
            but not enough could be resolved to build a graph.
          </p>
        </div>
      `;
      return;
    }

    this._detectCommunities();
    this._buildCommunityData();

    if (this.viewLevel === 'detail' && this.activeCommunity !== null) {
      this._renderDetail(container);
    } else {
      this._renderOverview(container);
    }
  },

  // =========================================================================
  // Level 1: Community Overview
  // =========================================================================

  _renderOverview(container) {
    const data = this.communityData;
    const links = this.communityLinks.map(l => ({ ...l })); // copy for simulation

    // Info bar
    const info = document.createElement('div');
    info.className = 'network-info';
    const realComm = data.filter(d => !d.isAggregate).length;
    const totalEntries = this._lastEntries ? this._lastEntries.length : this.nodes.length;
    const coveragePct = totalEntries > 0
      ? (this.nodes.length / totalEntries * 100).toFixed(1) : '0.0';
    info.innerHTML = `
      <span class="ov-title" style="margin-bottom:0">Cross-Reference Network</span>
      <span style="font-size:0.75rem;color:var(--sz-text-light)">
        ${this.nodes.length.toLocaleString('en')} of ${totalEntries.toLocaleString('en')} entries connected (${coveragePct}%) in ${realComm} communities \u2014 click to explore
      </span>
    `;
    container.appendChild(info);

    const rect = container.getBoundingClientRect();
    const width = rect.width || 700;
    const height = CHART_DIMS.network.height;

    // Scales
    const maxSize = d3.max(data, d => d.size) || 1;
    const rScale = d3.scaleSqrt().domain([1, maxSize]).range([14, 65]);

    const communityColor = d3.scaleOrdinal(d3.schemeTableau10)
      .domain(data.map(d => d.id));

    // SVG
    this.svg = d3.select(container).append('svg')
      .attr('class', 'explore-svg')
      .attr('viewBox', `0 0 ${width} ${height}`)
      .attr('preserveAspectRatio', 'xMidYMid meet')
      .attr('role', 'img')
      .attr('aria-label', 'Cross-reference community overview');

    const zoomG = this.svg.append('g');
    this.svg.call(d3.zoom()
      .scaleExtent([0.5, 3])
      .on('zoom', (event) => zoomG.attr('transform', event.transform))
    );

    // Meta-links
    const maxWeight = d3.max(links, d => d.weight) || 1;
    const linkWidth = d3.scaleLinear().domain([1, maxWeight]).range([1.5, 7]);

    const link = zoomG.append('g').selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke', Explore.colors.textLight)
      .attr('stroke-width', d => linkWidth(d.weight))
      .attr('stroke-opacity', 0.35);

    // Meta-nodes
    const node = zoomG.append('g').selectAll('circle')
      .data(data)
      .join('circle')
      .attr('r', d => rScale(d.size))
      .attr('fill', d => d.isAggregate ? '#9E9585' : communityColor(d.id))
      .attr('stroke', Explore.colors.cream)
      .attr('stroke-width', 2)
      .attr('opacity', d => d.isAggregate ? 0.5 : 0.85)
      .style('cursor', d => d.isAggregate ? 'default' : 'pointer');

    // Labels on all meta-nodes
    const label = zoomG.append('g').selectAll('text')
      .data(data)
      .join('text')
      .text(d => {
        const t = d.hub.title || 'Small clusters';
        const short = t.length > 25 ? t.slice(0, 23) + '\u2026' : t;
        return `${short} (${d.size})`;
      })
      .attr('font-size', d => d.size > 20 ? '11px' : '9px')
      .attr('font-family', 'system-ui, sans-serif')
      .attr('text-anchor', 'middle')
      .attr('fill', '#333')
      .attr('paint-order', 'stroke')
      .attr('stroke', 'white')
      .attr('stroke-width', 3)
      .attr('pointer-events', 'none');

    // Member count inside large circles
    const countLabel = zoomG.append('g').selectAll('text')
      .data(data.filter(d => d.size >= 10))
      .join('text')
      .text(d => d.size)
      .attr('font-size', d => Math.min(rScale(d.size) * 0.6, 24) + 'px')
      .attr('font-family', 'system-ui, sans-serif')
      .attr('font-weight', '700')
      .attr('text-anchor', 'middle')
      .attr('dominant-baseline', 'central')
      .attr('fill', 'white')
      .attr('opacity', 0.8)
      .attr('pointer-events', 'none');

    // Hover
    node.on('mouseenter', (event, d) => {
      node.attr('opacity', n => n.id === d.id ? 1 : 0.3);
      link.attr('stroke-opacity', l => {
        const s = typeof l.source === 'object' ? l.source.id : l.source;
        const t = typeof l.target === 'object' ? l.target.id : l.target;
        return (s === d.id || t === d.id) ? 0.8 : 0.08;
      }).attr('stroke', l => {
        const s = typeof l.source === 'object' ? l.source.id : l.source;
        const t = typeof l.target === 'object' ? l.target.id : l.target;
        return (s === d.id || t === d.id) ? Explore.colors.gold : Explore.colors.textLight;
      });

      const types = d.topTypes ? d.topTypes.slice(0, 3)
        .map(([t, c]) => `${ENTRY_TYPE_LABELS[t] || t}: ${c}`).join('<br>') : '';

      Explore.showTooltip(
        `<strong>${esc(d.hub.title || 'Small clusters')}</strong><br>` +
        `${d.size} entries, ${d.internalEdges} internal links<br>` +
        (d.externalEdges ? `${d.externalEdges} links to other communities<br>` : '') +
        (types ? `<small>${types}</small>` : '') +
        (!d.isAggregate ? '<br><small>Click to explore</small>' : ''),
        event
      );
    })
    .on('mouseleave', () => {
      node.attr('opacity', d => d.isAggregate ? 0.5 : 0.85);
      link.attr('stroke-opacity', 0.35).attr('stroke', Explore.colors.textLight);
      Explore.hideTooltip();
    })
    .on('click', (event, d) => {
      if (d.isAggregate) return;
      this.activeCommunity = d.id;
      this.viewLevel = 'detail';
      this.minDegree = d.size > 100 ? 2 : 1;
      this.render(this._lastEntries);
    });

    // Simulation
    const pad = 30;
    this.simulation = d3.forceSimulation(data)
      .force('link', d3.forceLink(links).id(d => d.id).distance(d =>
        rScale(d.source.size || 1) + rScale(d.target.size || 1) + 40
      ))
      .force('charge', d3.forceManyBody().strength(d => -rScale(d.size) * 8))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collide', d3.forceCollide().radius(d => rScale(d.size) + 8).strength(0.8))
      .force('x', d3.forceX(width / 2).strength(0.04))
      .force('y', d3.forceY(height / 2).strength(0.04));

    this.simulation.tick(300);
    this.simulation.stop();

    data.forEach(d => {
      d.x = Math.max(pad + rScale(d.size), Math.min(width - pad - rScale(d.size), d.x));
      d.y = Math.max(pad + rScale(d.size), Math.min(height - pad - rScale(d.size), d.y));
    });

    link
      .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
    node
      .attr('cx', d => d.x).attr('cy', d => d.y);
    label
      .attr('x', d => d.x)
      .attr('y', d => d.y + rScale(d.size) + 14);
    countLabel
      .attr('x', d => d.x)
      .attr('y', d => d.y);

    // Legend
    this._drawOverviewLegend(container, communityColor, data);

    // Stats panel
    this._renderOverviewStats();
  },

  // =========================================================================
  // Level 2: Community Detail (drill-down)
  // =========================================================================

  _renderDetail(container) {
    const cid = this.activeCommunity;
    const meta = this.communityData.find(c => c.id === cid);
    if (!meta) { this.viewLevel = 'overview'; this._renderOverview(container); return; }

    const memberIds = new Set(meta.memberIds);

    // Extract community sub-graph
    const detailNodes = this.nodes
      .filter(n => memberIds.has(n.id))
      .map(n => ({ ...n })); // copy for simulation

    const detailLinks = this.links
      .filter(l => memberIds.has(l.source) && memberIds.has(l.target))
      .map(l => ({ source: l.source, target: l.target })); // copy

    // Recompute degree within community
    const degMap = new Map();
    for (const n of detailNodes) degMap.set(n.id, 0);
    for (const l of detailLinks) {
      degMap.set(l.source, (degMap.get(l.source) || 0) + 1);
      degMap.set(l.target, (degMap.get(l.target) || 0) + 1);
    }
    for (const n of detailNodes) n.degree = degMap.get(n.id) || 0;

    // Controls: back button + degree filter
    const maxDeg = d3.max(detailNodes, d => d.degree) || 1;
    const sliderMax = Math.min(maxDeg, 10);

    const controls = document.createElement('div');
    controls.className = 'network-controls';
    controls.innerHTML = `
      <div class="network-info">
        <button class="geo-toggle active" id="network-back">\u2190 All communities</button>
        <span class="ov-title" style="margin-bottom:0">${esc(meta.hub.title)}</span>
        <span id="network-count" style="font-size:0.75rem;color:var(--sz-text-light)">
          ${detailNodes.length} entries, ${detailLinks.length} connections
        </span>
      </div>
      <div class="network-toolbar">
        <label class="network-slider-label">
          Min. connections: <strong id="degree-val">${this.minDegree}</strong>
          <input type="range" id="degree-slider" min="1" max="${sliderMax}" value="${this.minDegree}" class="network-slider">
        </label>
      </div>
    `;
    container.appendChild(controls);

    // Back button
    controls.querySelector('#network-back').addEventListener('click', () => {
      this.viewLevel = 'overview';
      this.activeCommunity = null;
      this.minDegree = 1;
      this.render(this._lastEntries);
    });

    const rect = container.getBoundingClientRect();
    const width = rect.width || 700;
    const height = CHART_DIMS.network.height;

    // Color by entry type
    const typeColor = d3.scaleOrdinal()
      .domain(Object.keys(ENTRY_TYPE_LABELS))
      .range([
        COLORS.burgundy, COLORS.gold, '#6B7A3A', '#5B5040', '#8B5C3A',
        '#5B3A7A', '#3A5B6B', '#7A4A1B', '#3A3A5B', '#6B3A4A',
        '#9E9585', '#4A6B3A', '#6B5B3A', '#3A4A6B', '#5B3A3A', '#7A6B3A',
      ]);

    // Size scale
    const rScale = d3.scaleSqrt().domain([1, maxDeg]).range([5, 18]);
    for (const n of detailNodes) n._r = rScale(n.degree);

    // SVG
    this.svg = d3.select(container).append('svg')
      .attr('class', 'explore-svg')
      .attr('viewBox', `0 0 ${width} ${height}`)
      .attr('preserveAspectRatio', 'xMidYMid meet')
      .attr('role', 'img')
      .attr('aria-label', `Community detail: ${meta.hub.title}`);

    const zoomG = this.svg.append('g');
    this.svg.call(d3.zoom()
      .scaleExtent([0.3, 5])
      .on('zoom', (event) => zoomG.attr('transform', event.transform))
    );

    // Links
    const link = zoomG.append('g').selectAll('line')
      .data(detailLinks)
      .join('line')
      .attr('stroke', Explore.colors.gridLine)
      .attr('stroke-width', 1)
      .attr('stroke-opacity', 0.4);

    // Hub identification (top 10)
    const hubs = [...detailNodes].sort((a, b) => b.degree - a.degree).slice(0, 10);
    const hubIds = new Set(hubs.map(h => h.id));

    // Halo
    const halo = zoomG.append('g').selectAll('circle')
      .data(hubs)
      .join('circle')
      .attr('r', d => rScale(d.degree) * 2.5)
      .attr('fill', d => typeColor(d.entryType))
      .attr('opacity', 0.15)
      .attr('pointer-events', 'none');

    // Nodes
    const node = zoomG.append('g').selectAll('circle')
      .data(detailNodes)
      .join('circle')
      .attr('r', d => rScale(d.degree))
      .attr('fill', d => typeColor(d.entryType))
      .attr('stroke', d => hubIds.has(d.id) ? Explore.colors.gold : Explore.colors.cream)
      .attr('stroke-width', d => hubIds.has(d.id) ? 2 : 1)
      .style('cursor', 'pointer')
      .call(this._drag());

    // Hub labels
    const hubLabel = zoomG.append('g').selectAll('text')
      .data(hubs.filter(h => h.degree >= this.minDegree))
      .join('text')
      .text(d => {
        const t = d.title || 'Untitled';
        return t.length > 35 ? t.slice(0, 33) + '\u2026' : t;
      })
      .attr('font-size', '9px')
      .attr('font-family', 'system-ui, sans-serif')
      .attr('fill', '#333')
      .attr('paint-order', 'stroke')
      .attr('stroke', 'white')
      .attr('stroke-width', 3)
      .attr('pointer-events', 'none');

    // Hover
    node.on('mouseenter', (event, d) => {
      const neighborIds = new Set([d.id]);
      detailLinks.forEach(l => {
        const s = typeof l.source === 'object' ? l.source.id : l.source;
        const t = typeof l.target === 'object' ? l.target.id : l.target;
        if (s === d.id) neighborIds.add(t);
        if (t === d.id) neighborIds.add(s);
      });

      node.attr('opacity', n => neighborIds.has(n.id) ? 1 : 0.15);
      link.attr('stroke-opacity', l =>
        (l.source.id === d.id || l.target.id === d.id) ? 0.8 : 0.05
      ).attr('stroke', l =>
        (l.source.id === d.id || l.target.id === d.id) ? Explore.colors.gold : Explore.colors.gridLine
      );
      halo.attr('opacity', h => neighborIds.has(h.id) ? 0.2 : 0.05);
      hubLabel.attr('opacity', h => neighborIds.has(h.id) ? 1 : 0.15);

      Explore.showTooltip(
        `<strong>${esc(d.title || 'Untitled')}</strong><br>` +
        `${ENTRY_TYPE_LABELS[d.entryType] || d.entryType}${d.year ? ` (${d.year})` : ''}<br>` +
        `${d.degree} connection${d.degree !== 1 ? 's' : ''}`,
        event
      );
    })
    .on('mouseleave', () => {
      const min = this.minDegree;
      node.attr('opacity', d => d.degree >= min ? 1 : 0);
      link.attr('stroke-opacity', l => {
        const sd = typeof l.source === 'object' ? l.source.degree : 0;
        const td = typeof l.target === 'object' ? l.target.degree : 0;
        return (sd >= min && td >= min) ? 0.4 : 0;
      }).attr('stroke', Explore.colors.gridLine);
      halo.attr('opacity', d => d.degree >= min ? 0.15 : 0);
      hubLabel.attr('opacity', d => d.degree >= min ? 1 : 0);
      Explore.hideTooltip();
    })
    .on('click', (event, d) => {
      const entry = App.entryMap.get(d.id);
      if (entry) Explore.updateSelection([entry]);
    })
    .on('dblclick', (event, d) => {
      location.hash = `entry=${d.id}`;
    });

    // Simulation — tuned for community size
    const pad = 20;
    const charge = detailNodes.length > 100 ? -40 : -80;
    const dist = detailNodes.length > 100 ? 60 : 100;

    this.simulation = d3.forceSimulation(detailNodes)
      .force('link', d3.forceLink(detailLinks).id(d => d.id).distance(dist))
      .force('charge', d3.forceManyBody().strength(charge))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collide', d3.forceCollide().radius(d => rScale(d.degree) + 3))
      .force('x', d3.forceX(width / 2).strength(0.03))
      .force('y', d3.forceY(height / 2).strength(0.03));

    this.simulation.tick(250);
    this.simulation.stop();

    detailNodes.forEach(d => {
      d.x = Math.max(pad, Math.min(width - pad, d.x));
      d.y = Math.max(pad, Math.min(height - pad, d.y));
    });

    link
      .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
    node
      .attr('cx', d => d.x).attr('cy', d => d.y);
    halo
      .attr('cx', d => d.x).attr('cy', d => d.y);
    hubLabel
      .attr('x', d => d.x + rScale(d.degree) + 4)
      .attr('y', d => d.y + 3);

    // Degree filter
    const slider = container.querySelector('#degree-slider');
    const degreeVal = container.querySelector('#degree-val');
    const countEl = container.querySelector('#network-count');

    const applyFilter = () => {
      const min = this.minDegree;
      const t = d3.transition().duration(300);

      node.transition(t)
        .attr('opacity', d => d.degree >= min ? 1 : 0)
        .attr('pointer-events', d => d.degree >= min ? 'auto' : 'none');
      link.transition(t)
        .attr('stroke-opacity', l =>
          (l.source.degree >= min && l.target.degree >= min) ? 0.4 : 0
        );
      halo.transition(t)
        .attr('opacity', d => d.degree >= min ? 0.15 : 0);
      hubLabel.transition(t)
        .attr('opacity', d => d.degree >= min ? 1 : 0);

      const vis = detailNodes.filter(d => d.degree >= min).length;
      const visL = detailLinks.filter(l => l.source.degree >= min && l.target.degree >= min).length;
      countEl.textContent = `${vis} entries, ${visL} connections`;

      this._renderDetailStats(meta, detailNodes, detailLinks);
    };

    slider.addEventListener('input', () => {
      this.minDegree = +slider.value;
      degreeVal.textContent = this.minDegree;
      applyFilter();
    });

    // Apply initial filter (important for large communities starting at minDegree > 1)
    applyFilter();

    // Legend
    this._drawDetailLegend(container, typeColor, detailNodes);

    // Stats
    this._renderDetailStats(meta, detailNodes, detailLinks);
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

  _detectCommunities() {
    const adj = new Map();
    for (const node of this.nodes) adj.set(node.id, []);
    for (const link of this.links) {
      const s = link.source, t = link.target;
      if (adj.has(s)) adj.get(s).push(t);
      if (adj.has(t)) adj.get(t).push(s);
    }

    this.communities = new Map();
    let communityId = 0;
    const visited = new Set();
    const sorted = [...this.nodes].sort((a, b) => b.degree - a.degree);

    for (const node of sorted) {
      if (visited.has(node.id)) continue;
      const queue = [node.id];
      visited.add(node.id);
      while (queue.length > 0) {
        const current = queue.shift();
        this.communities.set(current, communityId);
        for (const neighbor of (adj.get(current) || [])) {
          if (!visited.has(neighbor)) {
            visited.add(neighbor);
            queue.push(neighbor);
          }
        }
      }
      communityId++;
    }
  },

  _buildCommunityData() {
    // Group nodes by community
    const groups = new Map();
    for (const node of this.nodes) {
      const cid = this.communities.get(node.id);
      if (!groups.has(cid)) groups.set(cid, []);
      groups.get(cid).push(node);
    }

    const MIN_SIZE = 3;
    const metaNodes = [];
    const smallMembers = [];

    for (const [cid, members] of groups) {
      if (members.length < MIN_SIZE) {
        smallMembers.push(...members);
        continue;
      }

      const hub = members.reduce((a, b) => a.degree > b.degree ? a : b);
      const memberIdSet = new Set(members.map(m => m.id));

      // Type distribution
      const typeCounts = {};
      for (const m of members) {
        typeCounts[m.entryType] = (typeCounts[m.entryType] || 0) + 1;
      }
      const topTypes = Object.entries(typeCounts).sort((a, b) => b[1] - a[1]);

      // Edge counts
      let internal = 0, external = 0;
      for (const l of this.links) {
        const sIn = memberIdSet.has(l.source);
        const tIn = memberIdSet.has(l.target);
        if (sIn && tIn) internal++;
        else if (sIn || tIn) external++;
      }

      metaNodes.push({
        id: cid,
        size: members.length,
        hub: { id: hub.id, title: hub.title, degree: hub.degree },
        dominantType: topTypes[0] ? topTypes[0][0] : 'other',
        topTypes,
        memberIds: [...memberIdSet],
        internalEdges: internal,
        externalEdges: external,
      });
    }

    // Aggregate small communities
    if (smallMembers.length > 0) {
      metaNodes.push({
        id: -1,
        size: smallMembers.length,
        hub: { id: null, title: 'Small clusters', degree: 0 },
        dominantType: 'other',
        topTypes: [],
        memberIds: smallMembers.map(n => n.id),
        internalEdges: 0,
        externalEdges: 0,
        isAggregate: true,
      });
    }

    // Sort: largest first
    metaNodes.sort((a, b) => {
      if (a.isAggregate) return 1;
      if (b.isAggregate) return -1;
      return b.size - a.size;
    });

    // Build meta-links
    const metaIdSet = new Set(metaNodes.filter(m => !m.isAggregate).map(m => m.id));
    const metaLinkMap = new Map();

    for (const l of this.links) {
      const cs = this.communities.get(l.source);
      const ct = this.communities.get(l.target);
      if (cs === ct) continue;

      const cs2 = metaIdSet.has(cs) ? cs : -1;
      const ct2 = metaIdSet.has(ct) ? ct : -1;
      if (cs2 === ct2) continue;

      const key = Math.min(cs2, ct2) + '|' + Math.max(cs2, ct2);
      metaLinkMap.set(key, (metaLinkMap.get(key) || 0) + 1);
    }

    this.communityLinks = [];
    for (const [key, weight] of metaLinkMap) {
      const [s, t] = key.split('|').map(Number);
      this.communityLinks.push({ source: s, target: t, weight });
    }

    this.communityData = metaNodes;
  },

  // =========================================================================
  // Stats panels
  // =========================================================================

  _renderOverviewStats() {
    const panel = document.getElementById('explore-detail');
    const detail = document.getElementById('explore-detail-content');
    if (!panel || !detail) return;
    if (Explore.selection.length > 0) return;

    panel.classList.remove('hidden');

    const data = this.communityData.filter(d => !d.isAggregate);
    const smallCluster = this.communityData.find(d => d.isAggregate);

    const totalEntries = this._lastEntries ? this._lastEntries.length : this.nodes.length;
    const coveragePct = totalEntries > 0
      ? (this.nodes.length / totalEntries * 100).toFixed(1) : '0.0';
    detail.innerHTML = `
      <div class="detail-summary">
        <h3 class="detail-summary-title">Network Overview</h3>
        <div class="network-stats-grid">
          <div class="network-stat"><strong>${this.nodes.length} / ${totalEntries}</strong><span>Connected (${coveragePct}%)</span></div>
          <div class="network-stat"><strong>${this.links.length}</strong><span>Edges</span></div>
          <div class="network-stat"><strong>${data.length}</strong><span>Communities</span></div>
          <div class="network-stat"><strong>${smallCluster ? smallCluster.size : 0}</strong><span>Small clusters</span></div>
        </div>
        <div class="detail-group-section" style="margin-top:0.75rem">
          <h4>Communities</h4>
          <ul class="detail-entry-list">
            ${data.slice(0, 8).map(c => `
              <li class="detail-entry-item" style="cursor:pointer" onclick="ExploreNetwork.activeCommunity=${c.id};ExploreNetwork.viewLevel='detail';ExploreNetwork.minDegree=${c.size > 100 ? 2 : 1};ExploreNetwork.render(ExploreNetwork._lastEntries)">
                <span class="detail-entry-link">
                  <span class="badge badge-${c.dominantType}">${c.size}</span>
                  ${esc(c.hub.title)}
                  <span class="detail-entry-year">${c.hub.degree} links</span>
                </span>
              </li>
            `).join('')}
          </ul>
        </div>
        <p class="detail-summary-hint">Click a community to explore its members.</p>
      </div>
    `;
  },

  _renderDetailStats(meta, detailNodes, detailLinks) {
    const panel = document.getElementById('explore-detail');
    const detail = document.getElementById('explore-detail-content');
    if (!panel || !detail) return;
    if (Explore.selection.length > 0) return;

    panel.classList.remove('hidden');

    const min = this.minDegree;
    const vis = detailNodes.filter(d => d.degree >= min);
    const visL = detailLinks.filter(l => {
      const sd = typeof l.source === 'object' ? l.source.degree : 0;
      const td = typeof l.target === 'object' ? l.target.degree : 0;
      return sd >= min && td >= min;
    });

    const totalDeg = vis.reduce((s, n) => s + n.degree, 0);
    const avgDeg = vis.length ? (totalDeg / vis.length).toFixed(1) : '0';
    const topHubs = [...vis].sort((a, b) => b.degree - a.degree).slice(0, 5);

    detail.innerHTML = `
      <div class="detail-summary">
        <h3 class="detail-summary-title">${esc(meta.hub.title)}</h3>
        <div class="network-stats-grid">
          <div class="network-stat"><strong>${vis.length}</strong><span>Visible</span></div>
          <div class="network-stat"><strong>${visL.length}</strong><span>Edges</span></div>
          <div class="network-stat"><strong>${avgDeg}</strong><span>Avg. degree</span></div>
          <div class="network-stat"><strong>${meta.externalEdges}</strong><span>External</span></div>
        </div>
        <div class="detail-group-section" style="margin-top:0.75rem">
          <h4>Top Hubs</h4>
          <ul class="detail-entry-list">
            ${topHubs.map(h => `
              <li class="detail-entry-item">
                <a href="#entry=${h.id}" class="detail-entry-link">
                  <span class="badge badge-${h.entryType}">${ENTRY_TYPE_LABELS[h.entryType] || h.entryType}</span>
                  ${esc(h.title || 'Untitled')}
                  <span class="detail-entry-year">${h.degree} links</span>
                </a>
              </li>
            `).join('')}
          </ul>
        </div>
        <p class="detail-summary-hint">Click a node for entry details.</p>
      </div>
    `;
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
      { key: 'lifetime', label: '1881\u20131942', min: 1881, max: 1942 },
      { key: 'post-wwii', label: '1943\u20131980', min: 1943, max: 1980 },
      { key: 'late-20c', label: '1981\u20132000', min: 1981, max: 2000 },
      { key: 'contemporary', label: '2001\u2013', min: 2001, max: 2030 },
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
        const name = d.name.length > maxChars ? d.name.slice(0, maxChars - 1) + '\u2026' : d.name;
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
        (inflow ? `<small>\u2190 ${inflow} inflow</small><br>` : '') +
        (outflow ? `<small>\u2192 ${outflow} outflow</small>` : ''),
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
        `<strong>${esc(d.source.name)} \u2192 ${esc(d.target.name)}</strong><br>` +
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
      this.viewLevel = 'overview';
      this.activeCommunity = null;
      this.render(data);
    };
    document.addEventListener('explore:filterChange', this._filterHandler);
  },

  // =========================================================================
  // Helpers
  // =========================================================================

  _drag() {
    return d3.drag()
      .on('start', (event, d) => {
        if (!event.active && this.simulation) this.simulation.alphaTarget(0.3).restart();
        d.fx = d.x; d.fy = d.y;
      })
      .on('drag', (event, d) => {
        d.fx = event.x; d.fy = event.y;
        this.svg.selectAll('line')
          .attr('x1', l => l.source.x).attr('y1', l => l.source.y)
          .attr('x2', l => l.target.x).attr('y2', l => l.target.y);
        this.svg.selectAll('circle')
          .attr('cx', n => n.x).attr('cy', n => n.y);
        this.svg.selectAll('text')
          .filter((n) => n && n.id === d.id)
          .attr('x', d.x + (d._r || 8) + 4)
          .attr('y', d.y + 3);
      })
      .on('end', (event, d) => {
        if (!event.active && this.simulation) this.simulation.alphaTarget(0);
        d.fx = null; d.fy = null;
      });
  },

  _drawOverviewLegend(container, communityColor, data) {
    const shown = data.filter(d => !d.isAggregate).slice(0, 8);
    if (shown.length < 2) return;
    const legend = document.createElement('div');
    legend.className = 'network-legend';
    legend.innerHTML = shown.map(d => {
      const t = d.hub.title || '?';
      const short = t.length > 20 ? t.slice(0, 18) + '\u2026' : t;
      return `<span class="network-legend-item">
        <span class="network-legend-dot" style="background:${communityColor(d.id)}"></span>
        ${esc(short)} (${d.size})
      </span>`;
    }).join('');
    container.appendChild(legend);
  },

  _drawDetailLegend(container, typeColor, nodes) {
    const types = [...new Set(nodes.map(n => n.entryType))];
    if (types.length < 2) return;
    const legend = document.createElement('div');
    legend.className = 'network-legend';
    legend.innerHTML = types.slice(0, 8).map(t =>
      `<span class="network-legend-item">
        <span class="network-legend-dot" style="background:${typeColor(t)}"></span>
        ${ENTRY_TYPE_LABELS[t] || t}
      </span>`
    ).join('');
    container.appendChild(legend);
  },

};

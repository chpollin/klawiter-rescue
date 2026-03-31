/**
 * Explore Network — Force-directed graph of seeAlso relationships.
 * Nodes = entries, links = cross-references. Supports drag, zoom, hover, click.
 */
const ExploreNetwork = {
  simulation: null,
  svg: null,
  nodes: [],
  links: [],

  render(entries) {
    const container = document.getElementById('viz-network');
    if (!container) return;
    container.innerHTML = '';

    this._buildGraph(entries);

    if (this.nodes.length === 0) {
      container.innerHTML = `
        <div class="ov-empty" style="text-align:center;padding:3rem">
          <p>No cross-references found in the current dataset.</p>
          <p style="font-size:0.8rem;color:var(--sz-text-light)">
            The network graph requires entries with "See also" links.
            ${entries.filter(e => e.seeAlso && e.seeAlso.length).length} entries have cross-references,
            but not enough could be resolved to build a graph.
          </p>
        </div>
      `;
      return;
    }

    const rect = container.getBoundingClientRect();
    const width = rect.width || 700;
    const height = CHART_DIMS.network.height;

    // Info bar
    const info = document.createElement('div');
    info.className = 'network-info';
    info.innerHTML = `<span class="ov-title">Cross-Reference Network</span> <span style="font-size:0.75rem;color:var(--sz-text-light)">${this.nodes.length} entries, ${this.links.length} connections</span>`;
    container.appendChild(info);

    // Color scale by entry type
    const typeColor = d3.scaleOrdinal()
      .domain(Object.keys(ENTRY_TYPE_LABELS))
      .range([
        COLORS.burgundy, COLORS.gold, '#6B7A3A', '#5B5040', '#8B5C3A',
        '#5B3A7A', '#3A5B6B', '#7A4A1B', '#3A3A5B', '#6B3A4A',
        '#9E9585', '#4A6B3A', '#6B5B3A', '#3A4A6B', '#5B3A3A', '#7A6B3A',
      ]);

    // Size scale by degree
    const maxDeg = d3.max(this.nodes, d => d.degree) || 1;
    const rScale = d3.scaleSqrt().domain([1, maxDeg]).range([4, 16]);

    // SVG
    this.svg = d3.select(container).append('svg')
      .attr('class', 'explore-svg')
      .attr('viewBox', `0 0 ${width} ${height}`)
      .attr('preserveAspectRatio', 'xMidYMid meet')
      .attr('role', 'img')
      .attr('aria-labelledby', 'network-title network-desc');

    this.svg.append('title').attr('id', 'network-title')
      .text('Cross-reference network');
    this.svg.append('desc').attr('id', 'network-desc')
      .text(`Force-directed graph of ${this.nodes.length} entries connected by ${this.links.length} cross-references`);

    // Zoom
    const zoomG = this.svg.append('g');
    this.svg.call(d3.zoom()
      .scaleExtent([0.3, 4])
      .on('zoom', (event) => zoomG.attr('transform', event.transform))
    );

    // Links
    const link = zoomG.append('g').selectAll('line')
      .data(this.links)
      .join('line')
      .attr('stroke', Explore.colors.gridLine)
      .attr('stroke-width', 1)
      .attr('stroke-opacity', 0.4);

    // Nodes
    const node = zoomG.append('g').selectAll('circle')
      .data(this.nodes)
      .join('circle')
      .attr('r', d => rScale(d.degree))
      .attr('fill', d => typeColor(d.entryType))
      .attr('stroke', Explore.colors.cream)
      .attr('stroke-width', 1)
      .style('cursor', 'pointer')
      .call(this._drag());

    // Hover
    node.on('mouseenter', (event, d) => {
      // Highlight this node and neighbors
      const neighborIds = new Set();
      this.links.forEach(l => {
        if (l.source.id === d.id) neighborIds.add(l.target.id);
        if (l.target.id === d.id) neighborIds.add(l.source.id);
      });
      neighborIds.add(d.id);

      node.attr('opacity', n => neighborIds.has(n.id) ? 1 : 0.15);
      link.attr('stroke-opacity', l =>
        (l.source.id === d.id || l.target.id === d.id) ? 0.8 : 0.05
      ).attr('stroke', l =>
        (l.source.id === d.id || l.target.id === d.id) ? Explore.colors.gold : Explore.colors.gridLine
      );

      Explore.showTooltip(
        `<strong>${esc(d.title || 'Untitled')}</strong><br>` +
        `${ENTRY_TYPE_LABELS[d.entryType] || d.entryType}${d.year ? ` (${d.year})` : ''}<br>` +
        `${d.degree} connection${d.degree !== 1 ? 's' : ''}`,
        event
      );
    })
    .on('mouseleave', () => {
      node.attr('opacity', 1);
      link.attr('stroke-opacity', 0.4).attr('stroke', Explore.colors.gridLine);
      Explore.hideTooltip();
    })
    .on('click', (event, d) => {
      const entry = App.entryMap.get(d.id);
      if (entry) Explore.updateSelection([entry]);
    })
    .on('dblclick', (event, d) => {
      location.hash = `entry=${d.id}`;
    });

    // Simulation with boundary forces
    const pad = 20;
    this.simulation = d3.forceSimulation(this.nodes)
      .force('link', d3.forceLink(this.links).id(d => d.id).distance(50))
      .force('charge', d3.forceManyBody().strength(-30))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collide', d3.forceCollide().radius(d => rScale(d.degree) + 2))
      .force('x', d3.forceX(width / 2).strength(0.05))
      .force('y', d3.forceY(height / 2).strength(0.05));

    // Run simulation synchronously for instant layout
    this.simulation.tick(200);
    this.simulation.stop();

    // Clamp positions within bounds
    this.nodes.forEach(d => {
      d.x = Math.max(pad, Math.min(width - pad, d.x));
      d.y = Math.max(pad, Math.min(height - pad, d.y));
    });

    // Position elements
    link
      .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
    node
      .attr('cx', d => d.x).attr('cy', d => d.y);

    // Legend
    this._drawLegend(container, typeColor);
  },

  _buildGraph(entries) {
    const nodeMap = new Map();
    const links = [];

    // Build graph from seeAlso (reuse App.titleMap built at init)
    for (const entry of entries) {
      if (!entry.seeAlso || !entry.seeAlso.length) continue;

      for (const ref of entry.seeAlso) {
        // Try to resolve the reference
        let targetId = App.titleMap.get(ref);
        if (!targetId && App.data && App.data.redirects) {
          targetId = App.data.redirects[ref];
        }
        if (!targetId) continue;

        // Both source and target must be in entries
        if (!App.entryMap.has(targetId)) continue;

        const sourceId = entry.sourcePageId;
        if (sourceId === targetId) continue;

        // Add nodes
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

  _drag() {
    return d3.drag()
      .on('start', (event, d) => {
        if (!event.active && this.simulation) this.simulation.alphaTarget(0.3).restart();
        d.fx = d.x; d.fy = d.y;
      })
      .on('drag', (event, d) => {
        d.fx = event.x; d.fy = event.y;
        // Update positions during drag
        this.svg.selectAll('line')
          .attr('x1', l => l.source.x).attr('y1', l => l.source.y)
          .attr('x2', l => l.target.x).attr('y2', l => l.target.y);
        this.svg.selectAll('circle')
          .attr('cx', n => n.x).attr('cy', n => n.y);
      })
      .on('end', (event, d) => {
        if (!event.active && this.simulation) this.simulation.alphaTarget(0);
        d.fx = null; d.fy = null;
      });
  },

  _drawLegend(container, typeColor) {
    // Compact legend showing entry types present in the graph
    const typesPresent = [...new Set(this.nodes.map(n => n.entryType))];
    if (typesPresent.length < 2) return;

    const legend = document.createElement('div');
    legend.className = 'network-legend';
    legend.innerHTML = typesPresent.slice(0, 8).map(t =>
      `<span class="network-legend-item">
        <span class="network-legend-dot" style="background:${typeColor(t)}"></span>
        ${ENTRY_TYPE_LABELS[t] || t}
      </span>`
    ).join('');
    container.appendChild(legend);
  },
};

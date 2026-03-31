/**
 * Explore Overview — Four linked small multiples with cross-filtering.
 * Decade histogram, type treemap, language bars, location lollipop.
 */
const ExploreOverview = {
  entries: [],
  filtered: [],
  activeFilters: { type: null, language: null, decade: null },

  render(entries) {
    this.entries = entries;
    this.filtered = entries;
    this.activeFilters = { type: null, language: null, decade: null };

    const container = document.getElementById('viz-overview');
    if (!container) return;
    container.innerHTML = `
      <div class="overview-chips" id="overview-chips"></div>
      <div class="overview-grid">
        <div class="overview-cell" id="ov-decades"></div>
        <div class="overview-cell" id="ov-types"></div>
        <div class="overview-cell" id="ov-languages"></div>
        <div class="overview-cell" id="ov-locations"></div>
      </div>
    `;

    this._renderAll();
  },

  _applyFilters() {
    let f = this.entries;
    const af = this.activeFilters;
    if (af.type) f = f.filter(e => e.entryType === af.type);
    if (af.language) f = f.filter(e => e.language === af.language);
    if (af.decade) {
      const d0 = af.decade, d1 = d0 + 9;
      f = f.filter(e => e.year >= d0 && e.year <= d1);
    }
    this.filtered = f;
    Explore.updateSelection(f);
    this._renderChips();
    this._renderAll();
  },

  _toggleFilter(key, value) {
    this.activeFilters[key] = this.activeFilters[key] === value ? null : value;
    this._applyFilters();
  },

  _clearFilters() {
    this.activeFilters = { type: null, language: null, decade: null };
    this.filtered = this.entries;
    Explore.updateSelection([]);
    this._renderChips();
    this._renderAll();
  },

  _renderChips() {
    const el = document.getElementById('overview-chips');
    if (!el) return;
    const af = this.activeFilters;
    const chips = [];
    if (af.type) chips.push(`<span class="chip">Type: ${ENTRY_TYPE_LABELS[af.type] || af.type} <button onclick="ExploreOverview._toggleFilter('type',null);ExploreOverview._applyFilters()">&times;</button></span>`);
    if (af.language) chips.push(`<span class="chip">Language: ${af.language} <button onclick="ExploreOverview._toggleFilter('language',null);ExploreOverview._applyFilters()">&times;</button></span>`);
    if (af.decade) chips.push(`<span class="chip">Decade: ${af.decade}s <button onclick="ExploreOverview._toggleFilter('decade',null);ExploreOverview._applyFilters()">&times;</button></span>`);
    if (chips.length) chips.push(`<button class="chip-clear" onclick="ExploreOverview._clearFilters()">Clear all</button>`);
    el.innerHTML = chips.join(' ');
  },

  _renderAll() {
    this._renderDecades();
    this._renderTypes();
    this._renderLanguages();
    this._renderLocations();
  },

  // -------------------------------------------------------------------------
  // Decade Histogram
  // -------------------------------------------------------------------------
  _renderDecades() {
    const el = document.getElementById('ov-decades');
    if (!el) return;
    el.innerHTML = '<div class="ov-title">Publications by Decade</div>';

    const data = this.filtered;
    const decades = {};
    for (const e of data) {
      if (!e.year) continue;
      const d = Math.floor(e.year / 10) * 10;
      decades[d] = (decades[d] || 0) + 1;
    }

    const sorted = Object.entries(decades)
      .map(([d, c]) => ({ decade: +d, count: c }))
      .sort((a, b) => a.decade - b.decade);

    if (!sorted.length) { el.innerHTML += '<div class="ov-empty">No data</div>'; return; }

    const { width, height } = CHART_DIMS.overview;
    const m = { top: 5, right: 10, bottom: 25, left: 35 };
    const w = width - m.left - m.right, h = height - m.top - m.bottom;

    const x = d3.scaleBand().domain(sorted.map(d => d.decade)).range([0, w]).padding(0.15);
    const y = d3.scaleLinear().domain([0, d3.max(sorted, d => d.count)]).nice().range([h, 0]);

    const svg = d3.select(el).append('svg')
      .attr('viewBox', `0 0 ${width} ${height}`).attr('class', 'explore-svg')
      .attr('role', 'img').attr('aria-label', `Publications by decade: ${sorted.length} decades shown`);
    const g = svg.append('g').attr('transform', `translate(${m.left},${m.top})`);

    g.selectAll('rect').data(sorted).join('rect')
      .attr('x', d => x(d.decade))
      .attr('y', d => y(d.count))
      .attr('width', x.bandwidth())
      .attr('height', d => h - y(d.count))
      .attr('fill', d => d.decade === this.activeFilters.decade ? Explore.colors.gold : Explore.colors.burgundy)
      .attr('rx', 2)
      .attr('opacity', 0.85)
      .style('cursor', 'pointer')
      .on('click', (event, d) => this._toggleFilter('decade', d.decade))
      .on('mouseenter', (event, d) => {
        Explore.showTooltip(`<strong>${d.decade}s</strong><br>${d.count} entries`, event);
      })
      .on('mouseleave', () => Explore.hideTooltip());

    g.append('g').attr('transform', `translate(0,${h})`)
      .call(d3.axisBottom(x).tickFormat(d => `${d}s`).tickValues(sorted.filter((_, i) => i % 3 === 0).map(d => d.decade)))
      .selectAll('text').style('font-size', '0.6rem').attr('fill', Explore.colors.textLight);
    g.append('g').call(d3.axisLeft(y).ticks(3))
      .selectAll('text').style('font-size', '0.6rem').attr('fill', Explore.colors.textLight);
    g.selectAll('.domain').attr('stroke', Explore.colors.gridLine);
    g.selectAll('line').attr('stroke', Explore.colors.gridLine);
  },

  // -------------------------------------------------------------------------
  // Type Treemap
  // -------------------------------------------------------------------------
  _renderTypes() {
    const el = document.getElementById('ov-types');
    if (!el) return;
    el.innerHTML = '<div class="ov-title">Entry Types</div>';

    const data = this.filtered;
    const counts = countByField(data, 'entryType');

    const children = Object.entries(counts)
      .map(([type, count]) => ({ type, count, label: ENTRY_TYPE_LABELS[type] || type }))
      .sort((a, b) => b.count - a.count);

    if (!children.length) { el.innerHTML += '<div class="ov-empty">No data</div>'; return; }

    const { width, height } = CHART_DIMS.overview;
    const root = d3.hierarchy({ children }).sum(d => d.count);
    d3.treemap().size([width, height]).padding(2).round(true)(root);

    const colorScale = d3.scaleSequential()
      .domain([0, d3.max(children, d => d.count)])
      .interpolator(d3.interpolate('#E8DFD4', COLORS.burgundy));

    const svg = d3.select(el).append('svg')
      .attr('viewBox', `0 0 ${width} ${height}`).attr('class', 'explore-svg')
      .attr('role', 'img').attr('aria-label', `Entry types: ${children.length} types shown`);

    const cells = svg.selectAll('g').data(root.leaves()).join('g')
      .attr('transform', d => `translate(${d.x0},${d.y0})`)
      .style('cursor', 'pointer')
      .on('click', (event, d) => this._toggleFilter('type', d.data.type))
      .on('mouseenter', (event, d) => {
        Explore.showTooltip(`<strong>${d.data.label}</strong><br>${d.data.count} entries`, event);
      })
      .on('mouseleave', () => Explore.hideTooltip());

    cells.append('rect')
      .attr('width', d => d.x1 - d.x0)
      .attr('height', d => d.y1 - d.y0)
      .attr('fill', d => d.data.type === this.activeFilters.type ? Explore.colors.gold : colorScale(d.data.count))
      .attr('rx', 2)
      .attr('stroke', Explore.colors.cream)
      .attr('stroke-width', 1);

    cells.filter(d => (d.x1 - d.x0) > 50 && (d.y1 - d.y0) > 20)
      .append('text')
      .attr('x', 4).attr('y', 14)
      .attr('fill', d => d.data.count > d3.max(children, c => c.count) * 0.4 ? '#fff' : Explore.colors.textLight)
      .style('font-size', '0.6rem')
      .style('font-family', 'var(--font-sans)')
      .text(d => d.data.label.length > 15 ? d.data.label.slice(0, 13) + '..' : d.data.label);
  },

  // -------------------------------------------------------------------------
  // Language Bars
  // -------------------------------------------------------------------------
  _renderLanguages() {
    const el = document.getElementById('ov-languages');
    if (!el) return;
    el.innerHTML = '<div class="ov-title">Languages (Top 15)</div>';

    const data = this.filtered;
    const counts = countByField(data, 'language');

    const sorted = Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 15)
      .map(([lang, count]) => ({ lang, count }));

    if (!sorted.length) { el.innerHTML += '<div class="ov-empty">No data</div>'; return; }

    const { width, height } = CHART_DIMS.overview;
    const m = { top: 5, right: 10, bottom: 5, left: 80 };
    const w = width - m.left - m.right, h = height - m.top - m.bottom;

    const y = d3.scaleBand().domain(sorted.map(d => d.lang)).range([0, h]).padding(0.12);
    const x = d3.scaleLinear().domain([0, d3.max(sorted, d => d.count)]).range([0, w]);

    const svg = d3.select(el).append('svg')
      .attr('viewBox', `0 0 ${width} ${height}`).attr('class', 'explore-svg')
      .attr('role', 'img').attr('aria-label', `Top ${sorted.length} languages`);
    const g = svg.append('g').attr('transform', `translate(${m.left},${m.top})`);

    g.selectAll('rect').data(sorted).join('rect')
      .attr('x', 0)
      .attr('y', d => y(d.lang))
      .attr('width', d => x(d.count))
      .attr('height', y.bandwidth())
      .attr('fill', d => d.lang === this.activeFilters.language ? Explore.colors.gold : Explore.colors.burgundy)
      .attr('rx', 2)
      .attr('opacity', 0.85)
      .style('cursor', 'pointer')
      .on('click', (event, d) => this._toggleFilter('language', d.lang))
      .on('mouseenter', (event, d) => {
        Explore.showTooltip(`<strong>${d.lang}</strong><br>${d.count} entries`, event);
      })
      .on('mouseleave', () => Explore.hideTooltip());

    g.append('g').call(d3.axisLeft(y).tickSize(0))
      .selectAll('text').style('font-size', '0.6rem').attr('fill', Explore.colors.textLight);
    g.select('.domain').remove();
  },

  // -------------------------------------------------------------------------
  // Location Lollipop
  // -------------------------------------------------------------------------
  _renderLocations() {
    const el = document.getElementById('ov-locations');
    if (!el) return;
    el.innerHTML = '<div class="ov-title">Locations (Top 10)</div>';

    const data = this.filtered;
    const counts = countByField(data, 'location');

    const sorted = Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(([loc, count]) => ({ loc, count }));

    if (!sorted.length) { el.innerHTML += '<div class="ov-empty">No data</div>'; return; }

    const { width, height } = CHART_DIMS.overview;
    const m = { top: 5, right: 10, bottom: 5, left: 95 };
    const w = width - m.left - m.right, h = height - m.top - m.bottom;

    const y = d3.scaleBand().domain(sorted.map(d => d.loc)).range([0, h]).padding(0.2);
    const x = d3.scaleLinear().domain([0, d3.max(sorted, d => d.count)]).range([0, w]);

    const svg = d3.select(el).append('svg')
      .attr('viewBox', `0 0 ${width} ${height}`).attr('class', 'explore-svg')
      .attr('role', 'img').attr('aria-label', `Top ${sorted.length} publication locations`);
    const g = svg.append('g').attr('transform', `translate(${m.left},${m.top})`);

    // Lollipop lines
    g.selectAll('.lollipop-line').data(sorted).join('line')
      .attr('x1', 0)
      .attr('x2', d => x(d.count))
      .attr('y1', d => y(d.loc) + y.bandwidth() / 2)
      .attr('y2', d => y(d.loc) + y.bandwidth() / 2)
      .attr('stroke', Explore.colors.gridLine)
      .attr('stroke-width', 1);

    // Lollipop circles
    g.selectAll('circle').data(sorted).join('circle')
      .attr('cx', d => x(d.count))
      .attr('cy', d => y(d.loc) + y.bandwidth() / 2)
      .attr('r', 4)
      .attr('fill', Explore.colors.burgundy)
      .style('cursor', 'pointer')
      .on('click', (event, d) => {
        Explore.navigateToResults({ location: d.loc });
      })
      .on('mouseenter', (event, d) => {
        Explore.showTooltip(`<strong>${d.loc}</strong><br>${d.count} entries`, event);
      })
      .on('mouseleave', () => Explore.hideTooltip());

    g.append('g').call(d3.axisLeft(y).tickSize(0))
      .selectAll('text').style('font-size', '0.55rem').attr('fill', Explore.colors.textLight);
    g.select('.domain').remove();
  },
};

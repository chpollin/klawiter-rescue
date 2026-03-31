/**
 * Explore Timeline — Stacked area chart showing publication volume over time,
 * with layers colored by language. Supports brushing and hover interaction.
 */
const ExploreTimeline = {
  svg: null,
  brush: null,
  data: null,
  keys: [],
  x: null,
  y: null,
  color: null,
  margin: { top: 20, right: 20, bottom: 80, left: 45 },
  annotations: [
    { year: 1881, label: 'Born', align: 'left' },
    { year: 1933, label: 'Exile', align: 'left' },
    { year: 1942, label: 'Death', align: 'right' },
  ],

  render(entries) {
    const container = document.getElementById('viz-timeline');
    if (!container) return;
    container.innerHTML = '';

    const rect = container.getBoundingClientRect();
    const width = rect.width || 700;
    const height = CHART_DIMS.timeline.height;
    const m = this.margin;
    const w = width - m.left - m.right;
    const h = height - m.top - m.bottom;

    // Build stacked data
    this._buildData(entries);

    // Scales
    this.x = d3.scaleLinear()
      .domain(d3.extent(this.data, d => d.year))
      .range([0, w]);

    const stack = d3.stack()
      .keys(this.keys)
      .order(d3.stackOrderInsideOut)
      .offset(d3.stackOffsetNone);

    const series = stack(this.data);

    this.y = d3.scaleLinear()
      .domain([0, d3.max(series, s => d3.max(s, d => d[1]))])
      .nice()
      .range([h, 0]);

    this.color = d3.scaleOrdinal()
      .domain(this.keys)
      .range(this.keys.map(k => Explore.colors.languages[k] || Explore.colors.languages['Other']));

    // SVG
    this.svg = d3.select(container)
      .append('svg')
      .attr('class', 'explore-svg')
      .attr('viewBox', `0 0 ${width} ${height}`)
      .attr('preserveAspectRatio', 'xMidYMid meet')
      .attr('role', 'img')
      .attr('aria-labelledby', 'timeline-title timeline-desc');

    this.svg.append('title').attr('id', 'timeline-title')
      .text('Publication timeline');
    this.svg.append('desc').attr('id', 'timeline-desc')
      .text(`Stacked area chart showing ${entries.length} publications from ${Explore.yearExtent[0]} to ${Explore.yearExtent[1]}, colored by language`);

    const g = this.svg.append('g')
      .attr('transform', `translate(${m.left},${m.top})`);

    // Zweig lifetime band
    g.append('rect')
      .attr('class', 'lifetime-band')
      .attr('x', this.x(1881))
      .attr('y', 0)
      .attr('width', this.x(1942) - this.x(1881))
      .attr('height', h)
      .attr('fill', Explore.colors.gold)
      .attr('opacity', 0.08);

    // Grid lines
    g.append('g')
      .attr('class', 'grid')
      .call(d3.axisLeft(this.y)
        .ticks(5)
        .tickSize(-w)
        .tickFormat('')
      )
      .selectAll('line')
      .attr('stroke', Explore.colors.gridLine)
      .attr('stroke-dasharray', '2,2');
    g.select('.grid .domain').remove();

    // Area generator
    const area = d3.area()
      .x(d => this.x(d.data.year))
      .y0(d => this.y(d[0]))
      .y1(d => this.y(d[1]))
      .curve(d3.curveMonotoneX);

    // Draw stacked areas
    const layers = g.selectAll('.stream-layer')
      .data(series)
      .join('path')
      .attr('class', 'stream-layer')
      .attr('d', area)
      .attr('fill', d => this.color(d.key))
      .attr('opacity', 0.85)
      .attr('stroke', 'none')
      .style('cursor', 'pointer');

    // Hover interaction
    layers
      .on('mouseenter', (event, d) => {
        layers.attr('opacity', s => s.key === d.key ? 1 : 0.2);
      })
      .on('mousemove', (event, d) => {
        const [mx] = d3.pointer(event, g.node());
        const yearVal = Math.round(this.x.invert(mx));
        const dataPoint = this.data.find(p => p.year === yearVal);
        const count = dataPoint ? (dataPoint[d.key] || 0) : 0;
        Explore.showTooltip(
          `<strong>${d.key}</strong><br>${yearVal}: ${count} publication${count !== 1 ? 's' : ''}`,
          event
        );
      })
      .on('mouseleave', () => {
        layers.attr('opacity', 0.85);
        Explore.hideTooltip();
      })
      .on('click', (event, d) => {
        const filtered = Explore.entries.filter(e => e.language === d.key);
        Explore.filters.languages = [d.key];
        Explore.updateSelection(filtered);
      })
      .on('dblclick', (event, d) => {
        Explore.navigateToResults({ language: d.key });
      });

    // Axes
    g.append('g')
      .attr('class', 'x-axis')
      .attr('transform', `translate(0,${h})`)
      .call(d3.axisBottom(this.x)
        .ticks(12)
        .tickFormat(d3.format('d'))
      )
      .selectAll('text')
      .attr('fill', Explore.colors.textLight)
      .style('font-size', '0.7rem');

    g.append('g')
      .attr('class', 'y-axis')
      .call(d3.axisLeft(this.y).ticks(5))
      .selectAll('text')
      .attr('fill', Explore.colors.textLight)
      .style('font-size', '0.7rem');

    g.selectAll('.x-axis .domain, .y-axis .domain').attr('stroke', Explore.colors.gridLine);
    g.selectAll('.x-axis line, .y-axis line').attr('stroke', Explore.colors.gridLine);

    // Annotations
    this._drawAnnotations(g, h);

    // Brush
    this.brush = d3.brushX()
      .extent([[0, 0], [w, h]])
      .on('end', (event) => this._onBrush(event, entries));

    g.append('g')
      .attr('class', 'brush')
      .call(this.brush);

    // Legend (below x-axis)
    this._drawLegend(g, w, h);

    // Brush hint
    g.append('text')
      .attr('class', 'brush-hint')
      .attr('x', w / 2)
      .attr('y', h + 25)
      .attr('text-anchor', 'middle')
      .attr('fill', Explore.colors.textLight)
      .style('font-size', '0.65rem')
      .style('font-style', 'italic')
      .style('font-family', 'var(--font-sans)')
      .text('Drag to select a time range');
  },

  _buildData(entries) {
    this.keys = [...Explore.topLanguages, 'Other'];

    // Group by year
    const yearMap = new Map();
    for (const e of entries) {
      if (!e.year) continue;
      if (!yearMap.has(e.year)) yearMap.set(e.year, {});
      const lang = Explore.topLanguages.includes(e.language) ? e.language : 'Other';
      const bucket = yearMap.get(e.year);
      bucket[lang] = (bucket[lang] || 0) + 1;
    }

    // Fill all years in range
    const [minY, maxY] = Explore.yearExtent;
    this.data = [];
    for (let y = minY; y <= maxY; y++) {
      const row = { year: y };
      const bucket = yearMap.get(y) || {};
      for (const key of this.keys) {
        row[key] = bucket[key] || 0;
      }
      this.data.push(row);
    }
  },

  _drawAnnotations(g, h) {
    for (const ann of this.annotations) {
      const x = this.x(ann.year);
      g.append('line')
        .attr('x1', x).attr('x2', x)
        .attr('y1', 0).attr('y2', h)
        .attr('stroke', Explore.colors.textLight)
        .attr('stroke-width', 1)
        .attr('stroke-dasharray', '4,3')
        .attr('opacity', 0.5);

      g.append('text')
        .attr('x', x + (ann.align === 'right' ? -4 : 4))
        .attr('y', -6)
        .attr('text-anchor', ann.align === 'right' ? 'end' : 'start')
        .attr('fill', Explore.colors.textLight)
        .style('font-size', '0.65rem')
        .style('font-family', 'var(--font-sans)')
        .text(`${ann.label} ${ann.year}`);
    }
  },

  _drawLegend(g, w, h) {
    // Place legend below x-axis, wrapping into rows
    const itemW = 80;
    const cols = Math.floor(w / itemW);
    const legend = g.append('g')
      .attr('class', 'legend')
      .attr('transform', `translate(0, ${h + 35})`);

    const items = legend.selectAll('.legend-item')
      .data(this.keys)
      .join('g')
      .attr('class', 'legend-item')
      .attr('transform', (d, i) => {
        const col = i % cols;
        const row = Math.floor(i / cols);
        return `translate(${col * itemW}, ${row * 16})`;
      });

    items.append('rect')
      .attr('width', 10)
      .attr('height', 10)
      .attr('rx', 2)
      .attr('fill', d => this.color(d));

    items.append('text')
      .attr('x', 14)
      .attr('y', 9)
      .attr('fill', Explore.colors.textLight)
      .style('font-size', '0.65rem')
      .style('font-family', 'var(--font-sans)')
      .text(d => d);
  },

  _onBrush(event, entries) {
    if (!event.selection) {
      Explore.filters.yearRange = [null, null];
      Explore.updateSelection([]);
      return;
    }

    const [x0, x1] = event.selection.map(this.x.invert);
    const y0 = Math.round(x0);
    const y1 = Math.round(x1);
    Explore.filters.yearRange = [y0, y1];

    const selected = entries.filter(e => e.year >= y0 && e.year <= y1);
    Explore.updateSelection(selected);
  },
};

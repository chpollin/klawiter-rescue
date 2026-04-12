/**
 * Explore Timeline — Stacked area chart showing publication volume over time.
 * Layers colored by language (default) or entry type (toggle).
 * Supports brushing with semantic zoom, provenance overlay, and cross-view events.
 */
const ExploreTimeline = {
  svg: null,
  g: null,
  brush: null,
  data: null,
  entries: null,
  keys: [],
  x: null,
  y: null,
  color: null,
  layerMode: 'language',   // 'language' or 'type'
  chartMode: 'bars',        // 'bars' or 'stream'
  showProvenance: false,
  fullExtent: null,         // [minYear, maxYear] — always the full range
  zoomedDomain: null,       // [y0, y1] when brushed, null for full extent
  margin: { top: 20, right: 20, bottom: 35, left: 45 },
  annotations: [
    { year: 1881, label: 'Born', detail: 'Stefan Zweig born in Vienna' },
    { year: 1914, label: 'WWI', detail: 'World War I begins; Zweig becomes pacifist' },
    { year: 1933, label: 'Exile', detail: 'Zweig leaves Austria after Nazi rise to power' },
    { year: 1939, label: 'WWII', detail: 'World War II begins' },
    { year: 1942, label: 'Death', detail: 'Zweig dies in Petropolis, Brazil; Schachnovelle published posthumously' },
  ],

  render(entries) {
    const container = document.getElementById('viz-timeline');
    if (!container) return;
    container.innerHTML = '';
    this.entries = entries;
    this.showProvenance = Explore.filters.showProvenance;

    const rect = container.getBoundingClientRect();
    const width = rect.width || 700;
    const height = CHART_DIMS.timeline.height;
    const m = this.margin;
    const w = width - m.left - m.right;
    const h = height - m.top - m.bottom;

    // Build data (sets this.data, this.keys for all modes)
    this._buildData(entries);
    this.fullExtent = d3.extent(this.data, d => d.year);

    const xDomain = this.zoomedDomain || this.fullExtent;
    this.x = d3.scaleLinear().domain(xDomain).range([0, w]);

    this.color = d3.scaleOrdinal()
      .domain(this.keys)
      .range(this.keys.map(k => {
        const palette = this.layerMode === 'type' ? Explore.colors.types : Explore.colors.languages;
        return palette[k] || Explore.colors.languages['Other'];
      }));

    // SVG
    this.svg = d3.select(container)
      .append('svg')
      .attr('class', 'explore-svg')
      .attr('viewBox', `0 0 ${width} ${height}`)
      .attr('preserveAspectRatio', 'xMidYMid meet')
      .attr('role', 'img')
      .attr('aria-labelledby', 'timeline-title timeline-desc');

    const modeLabel = this.chartMode === 'sparklines' ? 'Small multiples'
      : this.chartMode === 'ranks' ? 'Language rank chart' : 'Stacked bar chart';
    this.svg.append('title').attr('id', 'timeline-title').text('Publication timeline');
    this.svg.append('desc').attr('id', 'timeline-desc')
      .text(`${modeLabel} showing ${entries.length} publications from ${this.fullExtent[0]} to ${this.fullExtent[1]}, colored by ${this.layerMode}`);

    this.g = this.svg.append('g')
      .attr('transform', `translate(${m.left},${m.top})`);

    // Zweig lifetime band
    this.g.append('rect')
      .attr('class', 'lifetime-band')
      .attr('x', this.x(1881)).attr('y', 0)
      .attr('width', this.x(1942) - this.x(1881)).attr('height', h)
      .attr('fill', Explore.colors.gold).attr('opacity', 0.08);

    // Mode-specific rendering
    if (this.chartMode === 'sparklines') {
      this._renderSparklines(w, h);
    } else if (this.chartMode === 'ranks') {
      this._renderRanks(w, h);
    } else {
      this._renderBars(w, h);
    }

    // Common: x-axis, annotations, brush, controls
    this._drawXAxis(this.g, w, h);
    this._drawAnnotations(this.g, h);

    this.brush = d3.brushX()
      .extent([[0, 0], [w, h]])
      .on('brush', (event) => this._onBrushMove(event))
      .on('end', (event) => this._onBrushEnd(event, entries, w, h));
    this.g.append('g').attr('class', 'brush').call(this.brush);

    this._drawControls(container);

    this.g.append('text')
      .attr('class', 'brush-hint')
      .attr('x', w / 2).attr('y', h + 28)
      .attr('text-anchor', 'middle')
      .attr('fill', Explore.colors.textLight)
      .style('font-size', '0.6rem').style('font-style', 'italic')
      .style('font-family', 'var(--font-sans)')
      .text('Drag to select \u00b7 double-click to reset');
  },

  // ---------------------------------------------------------------------------
  // Data builders
  // ---------------------------------------------------------------------------

  _buildData(entries) {
    if (this.layerMode === 'type') {
      this._buildTypeData(entries);
    } else {
      this._buildLanguageData(entries);
    }
  },

  _buildLanguageData(entries) {
    this.keys = [...Explore.topLanguages, 'Other'];
    const yearMap = new Map();
    for (const e of entries) {
      if (!e.year) continue;
      if (!yearMap.has(e.year)) yearMap.set(e.year, {});
      const lang = Explore.topLanguages.includes(e.language) ? e.language : 'Other';
      const bucket = yearMap.get(e.year);
      bucket[lang] = (bucket[lang] || 0) + 1;
    }
    this._fillYears(yearMap);
  },

  _buildTypeData(entries) {
    // Top types by count, rest as 'other'
    const typeCounts = {};
    for (const e of entries) {
      const t = e.entryType || 'other';
      typeCounts[t] = (typeCounts[t] || 0) + 1;
    }
    const sorted = Object.entries(typeCounts).sort((a, b) => b[1] - a[1]);
    const topTypes = sorted.slice(0, 10).map(([t]) => t);
    this.keys = [...topTypes, 'other'];
    // Deduplicate: if 'other' is already in topTypes, don't add it again
    this.keys = [...new Set(this.keys)];

    const yearMap = new Map();
    for (const e of entries) {
      if (!e.year) continue;
      if (!yearMap.has(e.year)) yearMap.set(e.year, {});
      const t = topTypes.includes(e.entryType) ? e.entryType : 'other';
      const bucket = yearMap.get(e.year);
      bucket[t] = (bucket[t] || 0) + 1;
    }
    this._fillYears(yearMap);
  },

  _fillYears(yearMap) {
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

  // ---------------------------------------------------------------------------
  // Bars mode — stacked bars with decade aggregation at full extent
  // ---------------------------------------------------------------------------

  _renderBars(w, h) {
    const domainSpan = this.x.domain()[1] - this.x.domain()[0];
    const plotData = domainSpan > 50
      ? this._aggregateToDecades(this.data) : this.data;

    const stack = d3.stack()
      .keys(this.keys)
      .order(d3.stackOrderInsideOut)
      .offset(d3.stackOffsetNone);
    const series = stack(plotData);

    this.y = d3.scaleLinear()
      .domain([0, d3.max(series, s => d3.max(s, d => d[1]))])
      .nice().range([h, 0]);

    // Grid
    this.g.append('g').attr('class', 'grid')
      .call(d3.axisLeft(this.y).ticks(5).tickSize(-w).tickFormat(''))
      .selectAll('line')
      .attr('stroke', Explore.colors.gridLine).attr('stroke-dasharray', '2,2');
    this.g.select('.grid .domain').remove();

    this._drawBarRects(series, w, h, plotData.length);

    if (this.showProvenance) {
      this._drawProvenance(this.g, this.entries, w, h);
    }

    // Y-axis
    this.g.append('g').attr('class', 'y-axis')
      .call(d3.axisLeft(this.y).ticks(5))
      .selectAll('text')
      .attr('fill', Explore.colors.textLight).style('font-size', '0.7rem');
    this.g.selectAll('.y-axis .domain').attr('stroke', Explore.colors.gridLine);
    this.g.selectAll('.y-axis line').attr('stroke', Explore.colors.gridLine);
  },

  _aggregateToDecades(data) {
    const decadeMap = new Map();
    for (const row of data) {
      const decade = Math.floor(row.year / 10) * 10;
      if (!decadeMap.has(decade)) {
        const d = { year: decade };
        this.keys.forEach(k => d[k] = 0);
        decadeMap.set(decade, d);
      }
      const d = decadeMap.get(decade);
      this.keys.forEach(k => d[k] += (row[k] || 0));
    }
    return [...decadeMap.values()].sort((a, b) => a.year - b.year);
  },

  // ---------------------------------------------------------------------------
  // Semantic Zoom — X-Axis tick formatting based on domain width
  // ---------------------------------------------------------------------------

  _drawXAxis(g, w, h) {
    const domain = this.x.domain();
    const span = domain[1] - domain[0];

    let tickCount, tickFormat;
    if (span <= 30) {
      // Narrow range: every year
      tickCount = Math.min(span, 20);
      tickFormat = d3.format('d');
    } else if (span <= 80) {
      // Medium range: every 5 years
      tickCount = Math.floor(span / 5);
      tickFormat = d3.format('d');
    } else {
      // Wide range: decades
      tickCount = Math.floor(span / 10);
      tickFormat = d => `${Math.floor(d / 10) * 10}s`;
    }

    g.append('g')
      .attr('class', 'x-axis')
      .attr('transform', `translate(0,${h})`)
      .call(d3.axisBottom(this.x)
        .ticks(tickCount)
        .tickFormat(tickFormat)
      )
      .selectAll('text')
      .attr('fill', Explore.colors.textLight)
      .style('font-size', '0.7rem');

    g.selectAll('.x-axis .domain').attr('stroke', Explore.colors.gridLine);
    g.selectAll('.x-axis line').attr('stroke', Explore.colors.gridLine);
  },

  // ---------------------------------------------------------------------------
  // Annotations — extended with WWI, WWII
  // ---------------------------------------------------------------------------

  _drawAnnotations(g, h) {
    const domain = this.x.domain();
    const span = domain[1] - domain[0];
    const visible = this.annotations.filter(a => a.year >= domain[0] && a.year <= domain[1]);

    // Stagger y-positions to avoid label collision
    const labelYPositions = [];
    for (let i = 0; i < visible.length; i++) {
      const xPos = this.x(visible[i].year);
      // Check if previous label would overlap (within 40px)
      let yOffset = -6;
      for (let j = 0; j < i; j++) {
        const prevX = this.x(visible[j].year);
        if (Math.abs(xPos - prevX) < 45) {
          yOffset = labelYPositions[j] - 12; // stack upward
        }
      }
      labelYPositions.push(yOffset);
    }

    visible.forEach((ann, i) => {
      const x = this.x(ann.year);

      g.append('line')
        .attr('x1', x).attr('x2', x)
        .attr('y1', 0).attr('y2', h)
        .attr('stroke', Explore.colors.textLight)
        .attr('stroke-width', 1)
        .attr('stroke-dasharray', '4,3')
        .attr('opacity', 0.5);

      const labelText = span <= 60 ? `${ann.label} ${ann.year}` : ann.label;
      const align = ann.year > (domain[0] + domain[1]) / 2 ? 'end' : 'start';
      const dx = align === 'end' ? -4 : 4;

      const label = g.append('text')
        .attr('class', 'annotation-label')
        .attr('x', x + dx)
        .attr('y', labelYPositions[i])
        .attr('text-anchor', align)
        .attr('fill', Explore.colors.textLight)
        .style('font-size', '0.65rem')
        .style('font-family', 'var(--font-sans)')
        .text(labelText);

      // Hover detail on all zoom levels
      label
        .style('cursor', 'help')
        .on('mouseenter', (event) => {
          Explore.showTooltip(`<strong>${ann.label} ${ann.year}</strong><br>${ann.detail}`, event);
        })
        .on('mouseleave', () => Explore.hideTooltip());
    });
  },

  // ---------------------------------------------------------------------------
  // Provenance overlay — data quality heatmap
  // ---------------------------------------------------------------------------

  _drawProvenance(g, entries, w, h) {
    // Aggregate provenance by year: per year, count regex/llm/missing fields
    const provByYear = new Map();
    const provFields = ['publisher', 'location', 'translator', 'pageCount'];
    for (const e of entries) {
      if (!e.year || !e._provenance) continue;
      if (!provByYear.has(e.year)) provByYear.set(e.year, { regex: 0, llm: 0, missing: 0, total: 0 });
      const bucket = provByYear.get(e.year);
      for (const f of provFields) {
        const src = e._provenance[f];
        if (src === 'regex') bucket.regex++;
        else if (src === 'llm') bucket.llm++;
        else bucket.missing++;
        bucket.total++;
      }
    }

    const barWidth = Math.max(1, w / (this.fullExtent[1] - this.fullExtent[0] + 1));

    // Draw stacked bars: green (regex), gold (llm), burgundy (missing)
    const provGroup = g.append('g').attr('class', 'provenance-overlay');

    for (const [year, counts] of provByYear) {
      if (year < this.x.domain()[0] || year > this.x.domain()[1]) continue;
      const x = this.x(year) - barWidth / 2;
      const total = counts.total || 1;
      const regexH = (counts.regex / total) * h;
      const llmH = (counts.llm / total) * h;
      const missingH = (counts.missing / total) * h;

      // Stack from bottom: regex (green), llm (gold), missing (red)
      provGroup.append('rect')
        .attr('x', x).attr('width', barWidth)
        .attr('y', h - regexH).attr('height', regexH)
        .attr('fill', Explore.colors.provenance.regex)
        .attr('opacity', 0.15);

      provGroup.append('rect')
        .attr('x', x).attr('width', barWidth)
        .attr('y', h - regexH - llmH).attr('height', llmH)
        .attr('fill', Explore.colors.provenance.llm)
        .attr('opacity', 0.15);

      provGroup.append('rect')
        .attr('x', x).attr('width', barWidth)
        .attr('y', h - regexH - llmH - missingH).attr('height', missingH)
        .attr('fill', Explore.colors.provenance.missing)
        .attr('opacity', 0.15);
    }
  },

  // ---------------------------------------------------------------------------
  // Drawing modes — bars (discrete) vs. stream (continuous)
  // ---------------------------------------------------------------------------

  _drawBarRects(series, w, h, dataLength) {
    const domain = this.x.domain();
    const barWidth = Math.max(2, (w / (dataLength || 140)) * 0.85);
    const self = this;

    for (const s of series) {
      this.g.selectAll(`.bar-${s.key.replace(/[^a-zA-Z0-9]/g, '_')}`)
        .data(s.filter(d => d.data.year >= domain[0] && d.data.year <= domain[1]))
        .join('rect')
        .attr('class', `stream-bar stream-bar-${s.key.replace(/[^a-zA-Z0-9]/g, '_')}`)
        .attr('x', d => this.x(d.data.year) - barWidth / 2)
        .attr('y', d => this.y(d[1]))
        .attr('width', barWidth)
        .attr('height', d => this.y(d[0]) - this.y(d[1]))
        .attr('fill', this.color(s.key))
        .attr('opacity', 0.85)
        .style('cursor', 'pointer')
        .on('mouseenter', function () {
          self.g.selectAll('.stream-bar').attr('opacity', function () {
            return this.classList.contains(`stream-bar-${s.key.replace(/[^a-zA-Z0-9]/g, '_')}`) ? 1 : 0.2;
          });
        })
        .on('mousemove', function (event) {
          const d = d3.select(this).datum();
          const yearVal = d.data.year;
          const count = d[1] - d[0];
          const label = self.layerMode === 'type' ? (ENTRY_TYPE_LABELS[s.key] || s.key) : s.key;
          Explore.showTooltip(
            `<strong>${label}</strong><br>${yearVal}: ${count} publication${count !== 1 ? 's' : ''}`,
            event
          );
        })
        .on('mouseleave', () => {
          self.g.selectAll('.stream-bar').attr('opacity', 0.85);
          Explore.hideTooltip();
        })
        .on('click', () => {
          if (self.layerMode === 'type') Explore.toggleFilter('types', s.key);
          else Explore.toggleFilter('languages', s.key);
        });
    }
  },

  // ---------------------------------------------------------------------------
  // Sparklines mode — small multiples: one line per language/type
  // ---------------------------------------------------------------------------

  _renderSparklines(w, h) {
    const domain = this.x.domain();
    const visibleData = this.data.filter(d => d.year >= domain[0] && d.year <= domain[1]);
    const rowH = h / this.keys.length;
    const self = this;

    for (let i = 0; i < this.keys.length; i++) {
      const key = this.keys[i];
      const rowY = i * rowH;
      const sparkH = rowH - 4;

      // Per-key timeseries
      const ts = visibleData.map(d => ({ year: d.year, value: d[key] || 0 }));
      const total = d3.sum(ts, d => d.value);
      const maxVal = d3.max(ts, d => d.value) || 1;

      const yScale = d3.scaleLinear()
        .domain([0, maxVal]).range([rowY + rowH - 2, rowY + 2]);

      // Filled area
      const area = d3.area()
        .x(d => this.x(d.year)).y0(rowY + rowH - 2).y1(d => yScale(d.value))
        .curve(d3.curveMonotoneX);
      this.g.append('path').datum(ts)
        .attr('d', area).attr('fill', this.color(key)).attr('opacity', 0.2);

      // Line
      const line = d3.line()
        .x(d => this.x(d.year)).y(d => yScale(d.value))
        .curve(d3.curveMonotoneX);
      this.g.append('path').datum(ts)
        .attr('d', line).attr('fill', 'none')
        .attr('stroke', this.color(key)).attr('stroke-width', 1.5);

      // Label (left, inside chart)
      const label = this.layerMode === 'type' ? (ENTRY_TYPE_LABELS[key] || key) : key;
      this.g.append('text')
        .attr('x', 4).attr('y', rowY + 11)
        .attr('fill', this.color(key))
        .style('font-size', '0.6rem').style('font-family', 'var(--font-sans)')
        .style('font-weight', 'bold')
        .text(`${label} (${total})`);

      // Hover: show value at cursor year
      this.g.append('rect')
        .attr('x', 0).attr('y', rowY).attr('width', w).attr('height', rowH)
        .attr('fill', 'transparent').style('cursor', 'crosshair')
        .on('mousemove', function (event) {
          const [mx] = d3.pointer(event, self.g.node());
          const yearVal = Math.round(self.x.invert(mx));
          const d = ts.find(dd => dd.year === yearVal);
          if (d) {
            Explore.showTooltip(
              `<strong>${label}</strong><br>${yearVal}: ${d.value} publication${d.value !== 1 ? 's' : ''}`,
              event
            );
          }
        })
        .on('mouseleave', () => Explore.hideTooltip())
        .on('click', () => {
          if (self.layerMode === 'type') Explore.toggleFilter('types', key);
          else Explore.toggleFilter('languages', key);
        });

      // Separator
      if (i < this.keys.length - 1) {
        this.g.append('line')
          .attr('x1', 0).attr('x2', w)
          .attr('y1', rowY + rowH).attr('y2', rowY + rowH)
          .attr('stroke', Explore.colors.gridLine).attr('stroke-dasharray', '1,2');
      }
    }
    // Set y for annotation compatibility (full height)
    this.y = d3.scaleLinear().domain([0, 1]).range([h, 0]);
  },

  // ---------------------------------------------------------------------------
  // Ranks mode — bump chart showing language rank over decades
  // ---------------------------------------------------------------------------

  _renderRanks(w, h) {
    const domain = this.x.domain();
    const self = this;

    // Compute decade bins within visible domain
    const minDec = Math.floor(domain[0] / 10) * 10;
    const maxDec = Math.floor(domain[1] / 10) * 10;
    const decades = [];
    for (let d = minDec; d <= maxDec; d += 10) decades.push(d);

    const maxRank = Math.min(this.keys.length, 8);

    // Per decade: rank keys by sum
    const rankData = new Map();
    this.keys.forEach(k => rankData.set(k, []));

    for (const dec of decades) {
      const sums = {};
      this.keys.forEach(k => sums[k] = 0);
      for (const d of this.data) {
        if (d.year >= dec && d.year < dec + 10) {
          this.keys.forEach(k => sums[k] += (d[k] || 0));
        }
      }
      const ranked = Object.entries(sums)
        .filter(([, v]) => v > 0)
        .sort((a, b) => b[1] - a[1]);
      ranked.forEach(([k, v], i) => {
        rankData.get(k).push({ decade: dec, rank: i + 1, count: v });
      });
    }

    // Y scale: rank 1 (top) to maxRank (bottom)
    const yScale = d3.scaleLinear()
      .domain([0.5, maxRank + 0.5]).range([0, h]);

    // Grid: horizontal rank lines
    for (let r = 1; r <= maxRank; r++) {
      this.g.append('line')
        .attr('x1', 0).attr('x2', w)
        .attr('y1', yScale(r)).attr('y2', yScale(r))
        .attr('stroke', Explore.colors.gridLine).attr('stroke-dasharray', '2,2');
      this.g.append('text')
        .attr('x', -8).attr('y', yScale(r))
        .attr('text-anchor', 'end').attr('dominant-baseline', 'middle')
        .attr('fill', Explore.colors.textLight)
        .style('font-size', '0.6rem').style('font-family', 'var(--font-sans)')
        .text(`#${r}`);
    }

    // Draw line + dots for each key that appears in top maxRank
    const line = d3.line()
      .x(d => this.x(d.decade + 5))
      .y(d => yScale(d.rank))
      .curve(d3.curveMonotoneX);

    for (const key of this.keys) {
      const rd = rankData.get(key).filter(d => d.rank <= maxRank);
      if (rd.length === 0) continue;

      // Line
      this.g.append('path').datum(rd)
        .attr('d', line).attr('fill', 'none')
        .attr('stroke', this.color(key)).attr('stroke-width', 2.5)
        .attr('opacity', 0.8);

      // Dots with tooltips
      const safeKey = key.replace(/[^a-zA-Z0-9]/g, '_');
      this.g.selectAll(`.rank-dot-${safeKey}`)
        .data(rd).join('circle')
        .attr('class', `rank-dot rank-dot-${safeKey}`)
        .attr('cx', d => this.x(d.decade + 5))
        .attr('cy', d => yScale(d.rank))
        .attr('r', 4)
        .attr('fill', this.color(key))
        .attr('stroke', '#fff').attr('stroke-width', 1)
        .style('cursor', 'pointer')
        .on('mouseenter', function (event) {
          const d = d3.select(this).datum();
          const label = self.layerMode === 'type' ? (ENTRY_TYPE_LABELS[key] || key) : key;
          Explore.showTooltip(
            `<strong>${label}</strong><br>${d.decade}s: #${d.rank} (${d.count} publications)`,
            event
          );
        })
        .on('mouseleave', () => Explore.hideTooltip())
        .on('click', () => {
          if (self.layerMode === 'type') Explore.toggleFilter('types', key);
          else Explore.toggleFilter('languages', key);
        });

      // Label at last visible position
      const last = rd[rd.length - 1];
      if (last) {
        const label = this.layerMode === 'type' ? (ENTRY_TYPE_LABELS[key] || key) : key;
        this.g.append('text')
          .attr('x', this.x(last.decade + 5) + 8)
          .attr('y', yScale(last.rank))
          .attr('dominant-baseline', 'middle')
          .attr('fill', this.color(key))
          .style('font-size', '0.58rem').style('font-family', 'var(--font-sans)')
          .style('font-weight', 'bold')
          .text(label);
      }
    }

    this.y = yScale;
  },

  // ---------------------------------------------------------------------------
  // Controls — layer mode toggle
  // ---------------------------------------------------------------------------

  _drawControls(container) {
    const bar = document.createElement('div');
    bar.className = 'timeline-controls';
    bar.style.cssText = 'display:flex; flex-wrap:wrap; gap:8px 16px; padding:6px 0; font-size:0.72rem; font-family:var(--font-sans); color:var(--sz-text-light,#6B6B6B); align-items:center;';

    const langActive = this.layerMode === 'language';
    const btnStyle = (active) => `padding:2px 8px;border:1px solid #ccc;border-radius:3px;background:${active ? '#631a34' : '#fff'};color:${active ? '#fff' : '#333'};cursor:pointer;font-size:0.68rem;`;

    // Active filters are shown in Explore filter chips (no duplication here)

    // Provenance legend
    const provLegend = this.showProvenance
      ? `<span style="font-size:0.62rem;color:#888;">
          <span style="color:${Explore.colors.provenance.regex};">&#9632;</span> regex
          <span style="color:${Explore.colors.provenance.llm};">&#9632;</span> LLM
          <span style="color:${Explore.colors.provenance.missing};">&#9632;</span> missing
         </span>`
      : '';

    // Compact legend — color squares inline
    const legendItems = this.keys.map(k => {
      const label = this.layerMode === 'type' ? (ENTRY_TYPE_LABELS[k] || k) : k;
      const c = this.color ? this.color(k) : '#999';
      return `<span style="white-space:nowrap;"><span style="display:inline-block;width:8px;height:8px;background:${c};border-radius:1px;vertical-align:middle;margin-right:2px;"></span>${label}</span>`;
    }).join(' ');

    const cm = this.chartMode;

    bar.innerHTML = `
      <span style="display:flex;align-items:center;gap:4px;">
        <button onclick="ExploreTimeline.setLayerMode('language')" style="${btnStyle(langActive)}">by Language</button>
        <button onclick="ExploreTimeline.setLayerMode('type')" style="${btnStyle(!langActive)}">by Type</button>
      </span>
      <span style="display:flex;align-items:center;gap:4px;">
        <button onclick="ExploreTimeline.setChartMode('bars')" style="${btnStyle(cm === 'bars')}" title="Stacked bars — volume per year/decade">Bars</button>
        <button onclick="ExploreTimeline.setChartMode('sparklines')" style="${btnStyle(cm === 'sparklines')}" title="Small multiples — one chart per language">Sparklines</button>
        <button onclick="ExploreTimeline.setChartMode('ranks')" style="${btnStyle(cm === 'ranks')}" title="Bump chart — language ranking over decades">Ranks</button>
      </span>
      ${provLegend}
      <div style="width:100%;display:flex;flex-wrap:wrap;gap:4px 10px;font-size:0.62rem;line-height:1.4;color:#888;">
        ${legendItems}
      </div>
    `;
    container.prepend(bar);
  },

  // ---------------------------------------------------------------------------
  // Brush handlers — publish events for L2/L3
  // ---------------------------------------------------------------------------

  _onBrushMove(event) {
    // Live updates during brush drag — fire event for visible cross-views
    if (!event.selection) return;
    const [x0, x1] = event.selection.map(this.x.invert);
    const y0 = Math.round(x0);
    const y1 = Math.round(x1);
    Explore.filters.yearRange = [y0, y1];
    // Fire event so Geography/Connections can update live if visible
    document.dispatchEvent(new CustomEvent('explore:filterChange', {
      detail: { filters: { ...Explore.filters }, source: 'timeline-brush' },
    }));
  },

  _onBrushEnd(event, entries, w, h) {
    if (!event.selection) {
      // Brush cleared (or double-click) — reset to full extent
      this.zoomedDomain = null;
      Explore.filters.yearRange = [null, null];
      Explore._renderFilterChips();
      Explore.updateSelection([]);
      this.render(entries);
      document.dispatchEvent(new CustomEvent('explore:filterChange', {
        detail: { filters: { ...Explore.filters }, source: 'timeline-brush' },
      }));
      return;
    }

    const [x0, x1] = event.selection.map(this.x.invert);
    const y0 = Math.round(x0);
    const y1 = Math.round(x1);

    // Ignore tiny brushes (accidental clicks)
    if (y1 - y0 < 3) return;

    // Semantic zoom: set zoomed domain and re-render
    this.zoomedDomain = [y0, y1];
    Explore.filters.yearRange = [y0, y1];
    Explore._renderFilterChips();

    const selected = entries.filter(e => e.year >= y0 && e.year <= y1);
    Explore.updateSelection(selected);
    this.render(entries);

    // Fire event for cross-view updates
    document.dispatchEvent(new CustomEvent('explore:filterChange', {
      detail: { filters: { ...Explore.filters }, source: 'timeline-brush' },
    }));
  },

  // ---------------------------------------------------------------------------
  // Public API for controls
  // ---------------------------------------------------------------------------

  setLayerMode(mode) {
    this.layerMode = mode;
    if (this.entries) this.render(this.entries);
    Explore.updateExploreURL(false);
  },

  toggleProvenance(enabled) {
    Explore.setProvenance(enabled);
  },

  setChartMode(mode) {
    this.chartMode = mode;
    if (this.entries) this.render(this.entries);
    Explore.updateExploreURL(false);
  },
};

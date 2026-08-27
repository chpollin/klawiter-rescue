/**
 * Explore Timeline — Stacked bars, small multiples and a rank chart over time.
 * Layers colored by language (default) or entry type (toggle).
 * Supports brushing with semantic zoom and a data-provenance strip.
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
  chartMode: 'bars',        // 'bars', 'sparklines', or 'ranks'
  showProvenance: false,
  fullExtent: null,         // [minYear, maxYear] — always the full range
  zoomedDomain: null,       // [y0, y1] when brushed, null for full extent
  margin: { top: 20, right: 20, bottom: 35, left: 56 },

  /** A decade below this many records ranks noise, not reception history. */
  MIN_DECADE_ENTRIES: 10,

  annotations: [
    { year: 1881, label: 'Born', detail: 'Stefan Zweig born in Vienna' },
    { year: 1914, label: 'WWI', detail: 'World War I begins; Zweig becomes pacifist' },
    { year: 1933, label: 'Exile', detail: 'Zweig leaves Austria after Nazi rise to power' },
    { year: 1939, label: 'WWII', detail: 'World War II begins' },
    { year: 1942, label: 'Death', detail: 'Zweig dies in Petropolis, Brazil; Schachnovelle published posthumously' },
  ],

  /** CSS-safe suffix for a class name derived from a data key. */
  _safeKey(key) {
    return String(key).replace(/[^a-zA-Z0-9]/g, '_');
  },

  /** Human label for a stack key in the current layer mode. */
  _keyLabel(key) {
    return this.layerMode === 'type' ? (ENTRY_TYPE_LABELS[key] || key) : key;
  },

  /**
   * Margins depend on the chart mode: the rank chart writes series labels to
   * the right of the last decade, and the provenance strip needs its own band
   * below the time axis rather than being folded into the plot.
   */
  _margins() {
    const strip = this.showProvenance && this.chartMode === 'bars';
    return {
      top: 20,
      right: this.chartMode === 'ranks' ? 78 : 20,
      bottom: 35 + (strip ? 54 : 0),
      left: 56,
    };
  },

  render(entries) {
    const container = document.getElementById('viz-timeline');
    if (!container) return;
    container.innerHTML = '';
    this.entries = entries;
    this.showProvenance = Explore.filters.showProvenance;

    const rect = container.getBoundingClientRect();
    const width = rect.width || 700;
    const height = CHART_DIMS.timeline.height;
    const m = this.margin = this._margins();
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

    // SVG — role="group" keeps the interactive children in the accessibility
    // tree; role="img" would collapse the whole chart into a single label.
    this.svg = d3.select(container)
      .append('svg')
      .attr('class', 'explore-svg')
      .attr('viewBox', `0 0 ${width} ${height}`)
      .attr('preserveAspectRatio', 'xMidYMid meet')
      .attr('role', 'group')
      .attr('aria-labelledby', 'timeline-title timeline-desc');

    const modeLabel = this.chartMode === 'sparklines' ? 'Small multiples'
      : this.chartMode === 'ranks' ? 'Language rank chart' : 'Stacked bar chart';
    const drawn = entries.filter(e => e.year >= xDomain[0] && e.year <= xDomain[1]).length;
    const yearless = entries.filter(e => !e.year).length;
    this.svg.append('title').attr('id', 'timeline-title').text('Publication timeline');
    this.svg.append('desc').attr('id', 'timeline-desc').text(
      `${modeLabel} of ${fmt(drawn)} dated entries from ${xDomain[0]} to ${xDomain[1]}, ` +
      `colored by ${this.layerMode}. ${fmt(yearless)} further entries carry no year and are not drawn.`
    );

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

    if (this.showProvenance && this.chartMode === 'bars') {
      this._drawProvenanceStrip(this.g, entries, w, h);
    }

    this.brush = d3.brushX()
      .extent([[0, 0], [w, h]])
      .on('brush', (event) => this._onBrushMove(event))
      .on('end', (event) => this._onBrushEnd(event, entries, w, h));
    this.g.append('g').attr('class', 'brush').call(this.brush);

    this._drawControls(container);
    this._renderCoverageNote(yearless);

    this.g.append('text')
      .attr('class', 'brush-hint')
      .attr('x', w / 2).attr('y', h + 28)
      .attr('text-anchor', 'middle')
      .attr('fill', Explore.colors.textLight)
      .style('font-size', '0.6rem').style('font-style', 'italic')
      .style('font-family', 'var(--font-sans)')
      .text('Drag to select · double-click to reset');
  },

  /**
   * Names what the chart leaves out, in the sidebar rather than on the
   * drawing surface. The drawn count is in the chart's own description; the
   * undated remainder is a fact about the source and gets its own way into
   * the results list.
   */
  _renderCoverageNote(yearless) {
    if (!yearless) { Explore.setViewNote(''); return; }
    const host = Explore.setViewNote(
      `<button type="button" class="link-btn" id="timeline-yearless">`
      + `${fmt(yearless)} undated entries not drawn</button>`
    );
    const btn = host && host.querySelector('#timeline-yearless');
    if (btn) {
      btn.addEventListener('click', () => {
        App.showCustomResults(this.entries.filter(e => !e.year), 'Entries without a year');
      });
    }
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
    // "Other" holds recorded languages outside the ranked ten; a record whose
    // language field is empty is a separate category, so a gap in the source
    // never reads as a rare language.
    this.keys = [...Explore.topLanguages, 'Other', Explore.NOT_RECORDED];
    const top = new Set(Explore.topLanguages);
    const yearMap = new Map();
    for (const e of entries) {
      if (!e.year) continue;
      if (!yearMap.has(e.year)) yearMap.set(e.year, {});
      const lang = !e.language ? Explore.NOT_RECORDED : (top.has(e.language) ? e.language : 'Other');
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
    this.keys = [...new Set([...topTypes, 'other'])];

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
    const domain = this.x.domain();
    const domainSpan = domain[1] - domain[0];
    const binSpan = domainSpan > 50 ? 10 : 1;
    const aggregated = binSpan === 10 ? this._aggregateToDecades(this.data) : this.data;

    // Clip to the visible domain before stacking: both the value scale and the
    // bar width have to describe what is on screen, otherwise a zoom leaves
    // hairline bars under an axis scaled to the whole century.
    const plotData = aggregated.filter(d =>
      d.year + (binSpan - 1) >= domain[0] && d.year <= domain[1]);
    this._plotRows = plotData;
    this._binSpan = binSpan;

    const stack = d3.stack()
      .keys(this.keys)
      .order(d3.stackOrderInsideOut)
      .offset(d3.stackOffsetNone);
    const series = stack(plotData);

    // d3 leaves the series in key order and records the stacking position on
    // `.index`; the legend has to follow that order to be readable.
    this._stackOrder = series.slice().sort((a, b) => a.index - b.index).map(s => s.key);

    this.y = d3.scaleLinear()
      .domain([0, d3.max(series, s => d3.max(s, d => d[1])) || 1])
      .nice().range([h, 0]);

    // Grid
    this.g.append('g').attr('class', 'grid')
      .call(d3.axisLeft(this.y).ticks(5).tickSize(-w).tickFormat(''))
      .selectAll('line')
      .attr('stroke', Explore.colors.gridLine).attr('stroke-dasharray', '2,2');
    this.g.select('.grid .domain').remove();

    this._drawBarRects(series, w, h, plotData.length);

    // Y-axis
    this.g.append('g').attr('class', 'y-axis')
      .call(d3.axisLeft(this.y).ticks(5))
      .selectAll('text')
      .attr('fill', Explore.colors.textLight).style('font-size', '0.7rem');
    this.g.selectAll('.y-axis .domain').attr('stroke', Explore.colors.gridLine);
    this.g.selectAll('.y-axis line').attr('stroke', Explore.colors.gridLine);

    this.g.append('text')
      .attr('class', 'axis-title')
      .attr('transform', `rotate(-90)`)
      .attr('x', -h / 2).attr('y', -42)
      .attr('text-anchor', 'middle')
      .attr('fill', Explore.colors.textLight)
      .style('font-size', '0.65rem').style('font-family', 'var(--font-sans)')
      .text(binSpan === 10 ? 'Publications per decade' : 'Publications per year');
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
  // Annotations
  // ---------------------------------------------------------------------------

  _drawAnnotations(g, h) {
    const domain = this.x.domain();
    const span = domain[1] - domain[0];
    const visible = this.annotations.filter(a => a.year >= domain[0] && a.year <= domain[1]);

    // Stagger downward, into the plot: stacking upward pushed the 1933/1939/
    // 1942 cluster past the top edge, where the panel's overflow clipped it.
    const labelYPositions = [];
    for (let i = 0; i < visible.length; i++) {
      const xPos = this.x(visible[i].year);
      let yOffset = 11;
      for (let j = 0; j < i; j++) {
        if (Math.abs(xPos - this.x(visible[j].year)) < 45) {
          yOffset = Math.max(yOffset, labelYPositions[j] + 13);
        }
      }
      labelYPositions.push(Math.min(yOffset, h - 4));
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

      g.append('text')
        .attr('class', 'annotation-label')
        .attr('x', x + dx)
        .attr('y', labelYPositions[i])
        .attr('text-anchor', align)
        .attr('fill', Explore.colors.textLight)
        .style('font-size', '0.65rem')
        .style('font-family', 'var(--font-sans)')
        .style('cursor', 'help')
        .text(labelText)
        .on('mouseenter', (event) => {
          Explore.showTooltip(`<strong>${esc(ann.label)} ${ann.year}</strong><br>${esc(ann.detail)}`, event);
        })
        .on('mouseleave', () => Explore.hideTooltip());
    });
  },

  // ---------------------------------------------------------------------------
  // Provenance strip — data quality band below the time axis
  // ---------------------------------------------------------------------------

  /**
   * Field provenance as its own band. Drawn over the plot it read as
   * publication counts on the publication axis and put year bars on top of
   * decade bars; below the axis, in the same bins as the chart, it reads as
   * what it is, the share of the four curated fields per bin by their source.
   */
  _drawProvenanceStrip(g, entries, w, h) {
    const rows = this._plotRows || [];
    if (!rows.length) return;
    const binSpan = this._binSpan || 1;
    const provFields = ['publisher', 'location', 'translator', 'pageCount'];

    const bins = new Map();
    for (const row of rows) bins.set(row.year, { regex: 0, llm: 0, missing: 0, total: 0 });
    for (const e of entries) {
      if (!e.year || !e._provenance) continue;
      const binStart = binSpan === 10 ? Math.floor(e.year / 10) * 10 : e.year;
      const bucket = bins.get(binStart);
      if (!bucket) continue;
      for (const f of provFields) {
        const src = e._provenance[f];
        if (src === 'regex') bucket.regex++;
        else if (src === 'llm') bucket.llm++;
        else bucket.missing++;
        bucket.total++;
      }
    }

    const stripTop = h + 38;
    const stripH = 20;
    const barWidth = Math.max(1, (w / rows.length) * 0.9);
    const strip = g.append('g').attr('class', 'provenance-strip');

    for (const row of rows) {
      const counts = bins.get(row.year);
      if (!counts || !counts.total) continue;
      const x = this.x(row.year + (binSpan - 1) / 2) - barWidth / 2;
      let y = stripTop;
      for (const part of ['regex', 'llm', 'missing']) {
        const seg = (counts[part] / counts.total) * stripH;
        strip.append('rect')
          .attr('x', x).attr('width', barWidth)
          .attr('y', y).attr('height', seg)
          .attr('fill', Explore.colors.provenance[part])
          .attr('opacity', 0.75);
        y += seg;
      }
    }

    g.append('text')
      .attr('class', 'axis-title')
      .attr('x', 0).attr('y', stripTop + stripH + 13)
      .attr('fill', Explore.colors.textLight)
      .style('font-size', '0.6rem').style('font-family', 'var(--font-sans)')
      .text('Source of publisher, place, translator and page count per bin');
  },

  // ---------------------------------------------------------------------------
  // Bar drawing
  // ---------------------------------------------------------------------------

  _drawBarRects(series, w, h, dataLength) {
    const barWidth = Math.max(2, (w / Math.max(1, dataLength)) * 0.85);
    const binSpan = this._binSpan || 1;
    const self = this;

    for (const s of series) {
      const safe = this._safeKey(s.key);
      this.g.selectAll(`.bar-${safe}`)
        .data(s)
        .join('rect')
        .attr('class', `stream-bar stream-bar-${safe}`)
        .attr('x', d => this.x(d.data.year + (binSpan - 1) / 2) - barWidth / 2)
        .attr('y', d => this.y(d[1]))
        .attr('width', barWidth)
        .attr('height', d => Math.max(0, this.y(d[0]) - this.y(d[1])))
        .attr('fill', this.color(s.key))
        .attr('opacity', 0.85)
        .style('cursor', 'pointer')
        .on('mouseenter', function () {
          self.g.selectAll('.stream-bar').attr('opacity', function () {
            return this.classList.contains(`stream-bar-${safe}`) ? 1 : 0.2;
          });
        })
        .on('mousemove', function (event) {
          const d = d3.select(this).datum();
          const count = d[1] - d[0];
          const binLabel = binSpan === 10 ? `${d.data.year}s` : String(d.data.year);
          Explore.showTooltip(
            `<strong>${esc(self._keyLabel(s.key))}</strong><br>${binLabel}: ${fmt(count)} publication${count !== 1 ? 's' : ''}`,
            event
          );
        })
        .on('mouseleave', () => {
          self.g.selectAll('.stream-bar').attr('opacity', 0.85);
          Explore.hideTooltip();
        })
        .on('click', () => self._applyKeyFilter(s.key));
    }
  },

  /**
   * Filter (or select) by a stack key. "Other" is not a language but the
   * complement of the ranked ten, so it selects its records instead of
   * setting a filter that would match nothing.
   */
  _applyKeyFilter(key) {
    if (this.layerMode === 'type') {
      Explore.toggleFilter('types', key);
      return;
    }
    if (key === 'Other') {
      const top = new Set(Explore.topLanguages);
      Explore.updateSelection(this.entries.filter(e => e.language && !top.has(e.language)));
      return;
    }
    Explore.toggleFilter('languages', key);
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
      const label = this._keyLabel(key);
      this.g.append('text')
        .attr('x', 4).attr('y', rowY + 11)
        .attr('fill', this.color(key))
        .style('font-size', '0.6rem').style('font-family', 'var(--font-sans)')
        .style('font-weight', 'bold')
        .text(`${label} (${fmt(total)})`);

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
              `<strong>${esc(label)}</strong><br>${yearVal}: ${fmt(d.value)} publication${d.value !== 1 ? 's' : ''}`,
              event
            );
          }
        })
        .on('mouseleave', () => Explore.hideTooltip())
        .on('click', () => self._applyKeyFilter(key));

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

    // Decade bins within the visible domain, split into those carrying enough
    // records to rank and those that do not.
    const minDec = Math.floor(domain[0] / 10) * 10;
    const maxDec = Math.floor(domain[1] / 10) * 10;
    const decades = [];
    const sparse = [];
    for (let dec = minDec; dec <= maxDec; dec += 10) {
      let total = 0;
      for (const d of this.data) {
        if (d.year >= dec && d.year < dec + 10) {
          this.keys.forEach(k => total += (d[k] || 0));
        }
      }
      if (total >= this.MIN_DECADE_ENTRIES) decades.push(dec);
      else sparse.push(dec);
    }

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

    // Grey out the decades whose record count cannot carry a ranking
    for (const dec of sparse) {
      const x0 = this.x(dec), x1 = this.x(dec + 10);
      this.g.append('rect')
        .attr('class', 'rank-sparse-band')
        .attr('x', x0).attr('y', 0)
        .attr('width', Math.max(0, x1 - x0)).attr('height', h);
    }
    if (sparse.length) {
      this.g.append('text')
        .attr('class', 'axis-title')
        .attr('x', this.x(sparse[0]) + 4).attr('y', h - 6)
        .attr('fill', Explore.colors.textLight)
        .style('font-size', '0.58rem').style('font-family', 'var(--font-sans)')
        .text(`under ${this.MIN_DECADE_ENTRIES} entries per decade — not ranked`);
    }

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

      this.g.append('path').datum(rd)
        .attr('d', line).attr('fill', 'none')
        .attr('stroke', this.color(key)).attr('stroke-width', 2.5)
        .attr('opacity', 0.8);

      const safeKey = this._safeKey(key);
      const label = this._keyLabel(key);
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
          Explore.showTooltip(
            `<strong>${esc(label)}</strong><br>${d.decade}s: #${d.rank} (${fmt(d.count)} entries)`,
            event
          );
        })
        .on('mouseleave', () => Explore.hideTooltip())
        .on('click', () => self._applyKeyFilter(key));

      // Label at last visible position
      const last = rd[rd.length - 1];
      if (last) {
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
  // Controls — layer mode, chart mode, zoom reset, legend
  // ---------------------------------------------------------------------------

  _drawControls(container) {
    const bar = document.createElement('div');
    bar.className = 'timeline-controls';

    const langActive = this.layerMode === 'language';
    const cm = this.chartMode;
    const btn = (label, active, onclick, title) =>
      `<button type="button" class="geo-toggle${active ? ' active' : ''}" aria-pressed="${active}"` +
      `${title ? ` title="${esc(title)}"` : ''} onclick="${onclick}">${esc(label)}</button>`;

    const provLegend = this.showProvenance
      ? `<span class="timeline-prov-legend">
          <span class="timeline-swatch" style="background:${Explore.colors.provenance.regex}"></span> regex
          <span class="timeline-swatch" style="background:${Explore.colors.provenance.llm}"></span> LLM
          <span class="timeline-swatch" style="background:${Explore.colors.provenance.missing}"></span> not recorded
         </span>`
      : '';

    const resetZoom = this.zoomedDomain
      ? btn('Reset zoom', false, 'ExploreTimeline.resetZoom()', 'Return to the full time range')
      : '';

    // Legend in the actual stacking order, bottom of the stack first.
    const order = (cm === 'bars' && this._stackOrder) ? this._stackOrder : this.keys;
    const legendItems = order.map(k => {
      const c = this.color ? this.color(k) : '#999';
      const active = this.layerMode === 'type'
        ? Explore.filters.types.includes(k)
        : Explore.filters.languages.includes(k);
      return `<button type="button" class="timeline-legend-item${active ? ' active' : ''}" ` +
        `aria-pressed="${active}" data-key="${esc(k)}">` +
        `<span class="timeline-swatch" style="background:${c}"></span>${esc(this._keyLabel(k))}</button>`;
    }).join('');

    bar.innerHTML = `
      <span class="timeline-control-group">
        ${btn('by Language', langActive, "ExploreTimeline.setLayerMode('language')")}
        ${btn('by Type', !langActive, "ExploreTimeline.setLayerMode('type')")}
      </span>
      <span class="timeline-control-group">
        ${btn('Bars', cm === 'bars', "ExploreTimeline.setChartMode('bars')", 'Stacked bars — volume per year or decade')}
        ${btn('Sparklines', cm === 'sparklines', "ExploreTimeline.setChartMode('sparklines')", 'Small multiples — one chart per series')}
        ${btn('Ranks', cm === 'ranks', "ExploreTimeline.setChartMode('ranks')", 'Bump chart — series ranking over decades')}
      </span>
      ${resetZoom}
      ${provLegend}
      <div class="timeline-legend" role="group" aria-label="Series legend, filters the chart">
        ${legendItems}
      </div>
    `;
    container.prepend(bar);

    // The legend is the keyboard path into the chart: every series is a real
    // button that filters, focuses and announces its own reading.
    bar.querySelectorAll('.timeline-legend-item').forEach(item => {
      const key = item.dataset.key;
      const total = d3.sum(this.data, d => d[key] || 0);
      const describe = (event) => Explore.showTooltip(
        `<strong>${esc(this._keyLabel(key))}</strong><br>${fmt(total)} dated entries`, event);
      item.addEventListener('click', () => this._applyKeyFilter(key));
      item.addEventListener('mouseenter', describe);
      item.addEventListener('focusin', describe);
      item.addEventListener('mouseleave', () => Explore.hideTooltip());
      item.addEventListener('focusout', () => Explore.hideTooltip());
    });
  },

  // ---------------------------------------------------------------------------
  // Brush handlers
  // ---------------------------------------------------------------------------

  _onBrushMove(event) {
    if (!event.selection) return;
    const [x0, x1] = event.selection.map(this.x.invert);
    Explore.filters.yearRange = [Math.round(x0), Math.round(x1)];
    document.dispatchEvent(new CustomEvent('explore:filterChange', {
      detail: { filters: { ...Explore.filters }, mode: 'timeline', source: 'timeline-brush' },
    }));
  },

  _onBrushEnd(event, entries, w, h) {
    if (!event.selection) {
      // Brush cleared (or double-click) — reset to full extent
      this.resetZoom();
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

    Explore.updateSelection(entries.filter(e => e.year >= y0 && e.year <= y1));
    this.render(entries);

    document.dispatchEvent(new CustomEvent('explore:filterChange', {
      detail: { filters: { ...Explore.filters }, mode: 'timeline', source: 'timeline-brush' },
    }));
  },

  /** Return to the full time range and drop the year filter. */
  resetZoom() {
    this.zoomedDomain = null;
    Explore.filters.yearRange = [null, null];
    Explore._renderFilterChips();
    Explore.updateSelection([]);
    if (this.entries) this.render(this.entries);
    document.dispatchEvent(new CustomEvent('explore:filterChange', {
      detail: { filters: { ...Explore.filters }, mode: 'timeline', source: 'timeline-brush' },
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

  setChartMode(mode) {
    this.chartMode = mode;
    if (this.entries) this.render(this.entries);
    Explore.updateExploreURL(false);
  },
};

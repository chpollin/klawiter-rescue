/**
 * Explore Geography — Interactive map with bubble overlay.
 *
 * Two projection modes:
 * - Flat (default): d3.geoNaturalEarth1() — all data visible, pan/zoom via d3.zoom
 * - Globe: d3.geoOrthographic() — one hemisphere, drag-to-rotate, scroll-to-zoom
 *
 * Features:
 * 1. Projection toggle (flat ↔ globe)
 * 2. Brushed Linking: reacts to explore:filterChange from Timeline
 * 3. Animated Playback: iterates through decades with transitions
 * 4. Semantic Zoom: country-level → city-level as you zoom in
 * 5. Selection Feedback: gold highlight + dimming, filter chip integration
 * 6. Interactive legend: click language/period to filter
 */
const ExploreGeography = {
  svg: null,
  globeG: null,
  bubblesG: null,
  locationData: null,
  worldData: null,
  projection: null,
  path: null,
  colorMode: 'language',
  zoomLevel: 'country',
  currentEntries: [],
  allBubbles: [],
  countryBubbles: [],
  selectedLocation: null,
  animationTimer: null,
  animationDecade: null,
  isPlaying: false,
  width: 700,
  height: 560,
  radius: null,
  projectionMode: 'globe',     // 'globe' (default) | 'flat' (all data visible)
  _zoomBehavior: null,         // d3.zoom instance for flat mode
  _rotation: [-10, -45, 0],   // initial rotation: centered on Europe [λ, φ, γ]
  _scale: null,                // current projection scale
  _baseScale: null,            // default scale (fit to container)

  // =========================================================================
  // Render
  // =========================================================================

  async render(entries) {
    const container = document.getElementById('viz-geography');
    if (!container) return;
    container.innerHTML = '';
    this.currentEntries = entries;
    this.selectedLocation = Explore.filters.location || null;

    // Load geodata (cached)
    if (!this.locationData) {
      try {
        const resp = await fetch('data/locations.json');
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        this.locationData = await resp.json();
      } catch (e) {
        console.error('Failed to load locations:', e);
        container.innerHTML = '<div class="ov-empty">Could not load location data.</div>';
        return;
      }
    }
    if (!this.worldData) {
      try {
        const resp = await fetch('https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json');
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        this.worldData = await resp.json();
      } catch (e) {
        console.error('Failed to load world map:', e);
        container.innerHTML = '<div class="ov-empty">Could not load world map data.</div>';
        return;
      }
    }

    // Controls
    this._drawControls(container, entries);

    // Set up projection (globe or flat depending on projectionMode)
    const rect = container.getBoundingClientRect();
    this.width = rect.width || 700;
    this.height = CHART_DIMS.geography?.height || 560;
    this._initProjection();

    // Build bubble data
    this.allBubbles = this._buildCityBubbles(entries);
    this.countryBubbles = this._buildCountryBubbles(this.allBubbles);

    // Draw globe
    this._drawGlobe(container, entries.length);

    // Filter listener
    this._bindFilterListener();
  },

  // =========================================================================
  // Controls
  // =========================================================================

  _drawControls(container, entries) {
    const controls = document.createElement('div');
    controls.className = 'geo-controls';
    controls.id = 'geo-controls';
    controls.innerHTML = `
      <span class="ov-title" style="margin-bottom:0">Color:</span>
      <button class="geo-toggle ${this.colorMode === 'language' ? 'active' : ''}" data-cmode="language">Language</button>
      <button class="geo-toggle ${this.colorMode === 'period' ? 'active' : ''}" data-cmode="period">Period</button>
      <span style="flex:1"></span>
      <button class="geo-toggle" id="geo-reset-btn" title="Reset globe rotation and zoom">&#8634;</button>
      <button class="geo-toggle${this.projectionMode === 'flat' ? ' active' : ''}" id="geo-projection-btn" title="Toggle globe / flat map">&#127760;</button>
      <button class="geo-toggle geo-play-btn" id="geo-play-btn" title="Animate through decades">
        <span id="geo-play-icon">&#9654;</span>
      </button>
      <input type="range" id="geo-decade-slider" class="geo-slider"
        min="${Math.floor(Explore.yearExtent[0] / 10) * 10}"
        max="${Math.floor(Explore.yearExtent[1] / 10) * 10}"
        step="10"
        value="${this.animationDecade || Math.floor(Explore.yearExtent[0] / 10) * 10}">
      <span id="geo-decade-label" class="geo-decade-label">${this.animationDecade ? this.animationDecade + 's' : 'All'}</span>
    `;
    container.appendChild(controls);

    controls.querySelectorAll('[data-cmode]').forEach(btn => {
      btn.addEventListener('click', () => {
        this.colorMode = btn.dataset.cmode;
        this._updateBubbles();
        controls.querySelectorAll('[data-cmode]').forEach(b =>
          b.classList.toggle('active', b.dataset.cmode === this.colorMode));
      });
    });

    document.getElementById('geo-reset-btn').addEventListener('click', () => {
      this._rotation = [-10, -45, 0];
      this._scale = this._baseScale;
      this.zoomLevel = 'country';
      this.selectedLocation = null;
      if (this.projectionMode === 'flat' && this._zoomBehavior) {
        this.svg.call(this._zoomBehavior.transform, d3.zoomIdentity);
        this.globeG.attr('transform', null);
      }
      this.projection.scale(this._scale);
      if (this.projectionMode === 'globe') this.projection.rotate(this._rotation);
      this._redrawGlobe();
      this._resetToAll();
    });

    document.getElementById('geo-projection-btn').addEventListener('click', () => {
      this.projectionMode = this.projectionMode === 'globe' ? 'flat' : 'globe';
      document.getElementById('geo-projection-btn').classList.toggle('active', this.projectionMode === 'flat');
      this._rebuildProjection();
    });

    document.getElementById('geo-play-btn').addEventListener('click', () => {
      if (this.isPlaying) this._stopAnimation();
      else this._startAnimation();
    });

    document.getElementById('geo-decade-slider').addEventListener('input', (e) => {
      if (this.isPlaying) this._stopAnimation();
      const val = parseInt(e.target.value);
      this._setDecade(val);
    });

    // Double-click slider to reset to "All"
    document.getElementById('geo-decade-slider').addEventListener('dblclick', () => {
      if (this.isPlaying) this._stopAnimation();
      this._resetToAll();
    });
  },

  // =========================================================================
  // Animation
  // =========================================================================

  _startAnimation() {
    this.isPlaying = true;
    const icon = document.getElementById('geo-play-icon');
    if (icon) icon.innerHTML = '&#9646;&#9646;';
    const slider = document.getElementById('geo-decade-slider');
    const minD = parseInt(slider.min), maxD = parseInt(slider.max);
    let decade = this.animationDecade || minD;
    if (decade >= maxD) decade = minD;

    const step = () => {
      if (!this.isPlaying || decade > maxD) { this._stopAnimation(); return; }
      this._setDecade(decade);
      slider.value = decade;
      decade += 10;
      this.animationTimer = setTimeout(step, 1200);
    };
    step();
  },

  _stopAnimation() {
    this.isPlaying = false;
    if (this.animationTimer) clearTimeout(this.animationTimer);
    this.animationTimer = null;
    const icon = document.getElementById('geo-play-icon');
    if (icon) icon.innerHTML = '&#9654;';
  },

  /** Set globe to show a single decade. Always filters from the FULL dataset. */
  _setDecade(decade) {
    this.animationDecade = decade;
    const label = document.getElementById('geo-decade-label');
    if (label) label.textContent = decade + 's';

    // Always filter from full dataset (not the current filtered view)
    const allEntries = Explore.entries;
    Explore.filters.yearRange = [decade, decade + 9];
    Explore._renderFilterChips();
    const filtered = allEntries.filter(e => e.year >= decade && e.year <= decade + 9);

    this.allBubbles = this._buildCityBubbles(filtered);
    this.countryBubbles = this._buildCountryBubbles(this.allBubbles);
    this._updateBubbles(800);
    Explore.updateSelection(filtered.length < allEntries.length ? filtered : []);

    document.dispatchEvent(new CustomEvent('explore:filterChange', {
      detail: { filters: { ...Explore.filters }, mode: 'geography' },
    }));
  },

  /** Reset to show all decades (remove yearRange filter). */
  _resetToAll() {
    this.animationDecade = null;
    const label = document.getElementById('geo-decade-label');
    if (label) label.textContent = 'All';
    const slider = document.getElementById('geo-decade-slider');
    if (slider) slider.value = slider.min;

    Explore.filters.yearRange = [null, null];
    Explore._renderFilterChips();
    const allEntries = Explore.entries;

    this.allBubbles = this._buildCityBubbles(allEntries);
    this.countryBubbles = this._buildCountryBubbles(this.allBubbles);
    this._updateBubbles(500);
    Explore.updateSelection([]);

    document.dispatchEvent(new CustomEvent('explore:filterChange', {
      detail: { filters: { ...Explore.filters }, mode: 'geography' },
    }));
  },

  // =========================================================================
  // Bubble builders
  // =========================================================================

  _buildCityBubbles(entries) {
    const locationCounts = new Map();
    for (const e of entries) {
      if (!e.location) continue;
      if (!locationCounts.has(e.location)) locationCounts.set(e.location, { count: 0, entries: [] });
      const c = locationCounts.get(e.location);
      c.count++;
      c.entries.push(e);
    }

    const bubbles = [];
    let geocoded = 0;
    for (const [loc, data] of locationCounts) {
      const geo = this.locationData[loc];
      if (!geo) continue;
      geocoded += data.count;

      // Merge variant spellings at nearby coordinates
      const existing = bubbles.find(b =>
        Math.abs(b.lat - geo.lat) < 0.15 && Math.abs(b.lng - geo.lng) < 0.15
      );
      if (existing) {
        existing.count += data.count;
        existing.entries.push(...data.entries);
        if (!existing.locations.includes(loc)) existing.locations.push(loc);
      } else {
        bubbles.push({
          count: data.count, entries: [...data.entries],
          locations: [loc],
          lat: geo.lat, lng: geo.lng,
          country: geo.country || null,
          type: 'city',
        });
      }
    }
    this._geocodedEntries = geocoded;
    return bubbles;
  },

  _buildCountryBubbles(cityBubbles) {
    const countryMap = new Map();
    for (const b of cityBubbles) {
      const cc = b.country || 'XX';
      if (!countryMap.has(cc)) {
        countryMap.set(cc, {
          count: 0, entries: [], locations: [],
          latSum: 0, lngSum: 0, cityCount: 0,
          country: cc, type: 'country',
        });
      }
      const cb = countryMap.get(cc);
      cb.count += b.count;
      cb.entries.push(...b.entries);
      cb.locations.push(...b.locations);
      cb.latSum += b.lat * b.count;
      cb.lngSum += b.lng * b.count;
      cb.cityCount += b.count;
    }

    const result = [];
    for (const [cc, cb] of countryMap) {
      if (cc === 'XX') continue;
      result.push({
        ...cb,
        lat: cb.latSum / cb.cityCount,
        lng: cb.lngSum / cb.cityCount,
      });
    }
    for (const b of cityBubbles) {
      if (!b.country) result.push({ ...b, type: 'city-orphan' });
    }
    return result;
  },

  // =========================================================================
  // Projection & Interaction setup
  // =========================================================================

  /** Initialize projection based on projectionMode (globe or flat). */
  _initProjection() {
    const size = Math.min(this.width, this.height);
    this._baseScale = size / 2.2;
    if (!this._scale) this._scale = this._baseScale;

    if (this.projectionMode === 'globe') {
      this.projection = d3.geoOrthographic()
        .scale(this._scale)
        .translate([this.width / 2, this.height / 2])
        .rotate(this._rotation)
        .clipAngle(90);
    } else {
      this.projection = d3.geoNaturalEarth1()
        .scale(this._scale * 0.65)
        .translate([this.width / 2, this.height / 2]);
    }
    this.path = d3.geoPath(this.projection);
  },

  /** Bind interaction handlers (drag/wheel for globe, d3.zoom for flat). */
  _initInteractions() {
    const self = this;
    // Remove prior handlers
    this.svg.on('.drag', null).on('wheel', null);
    if (this._zoomBehavior) {
      this.svg.call(this._zoomBehavior.on('zoom', null));
      this._zoomBehavior = null;
    }

    if (this.projectionMode === 'globe') {
      // Drag-to-rotate
      let dragStart = null;
      this.svg.call(d3.drag()
        .on('start', (event) => {
          dragStart = { x: event.x, y: event.y, r: [...self._rotation] };
        })
        .on('drag', (event) => {
          if (!dragStart) return;
          const dx = event.x - dragStart.x;
          const dy = event.y - dragStart.y;
          const sensitivity = 0.4;
          self._rotation = [
            dragStart.r[0] + dx * sensitivity,
            Math.max(-80, Math.min(80, dragStart.r[1] - dy * sensitivity)),
            0,
          ];
          self.projection.rotate(self._rotation);
          self._redrawGlobe();
        })
      );
      // Scroll-to-zoom (projection scale)
      this.svg.on('wheel', (event) => {
        event.preventDefault();
        const factor = event.deltaY > 0 ? 0.9 : 1.12;
        self._scale = Math.max(self._baseScale * 0.8, Math.min(self._baseScale * 6, self._scale * factor));
        self.projection.scale(self._scale);
        const zoomRatio = self._scale / self._baseScale;
        const newLevel = zoomRatio >= 2.0 ? 'city' : 'country';
        if (newLevel !== self.zoomLevel) self.zoomLevel = newLevel;
        self._redrawGlobe();
      }, { passive: false });
    } else {
      // Flat map: d3.zoom for pan + zoom via SVG transform
      this._zoomBehavior = d3.zoom()
        .scaleExtent([0.8, 6])
        .on('zoom', (event) => {
          self.globeG.attr('transform', event.transform);
          const newLevel = event.transform.k >= 2.0 ? 'city' : 'country';
          if (newLevel !== self.zoomLevel) {
            self.zoomLevel = newLevel;
            self._updateBubbles(200);
          }
        });
      this.svg.call(this._zoomBehavior);
    }
  },

  /** Switch projection without full SVG teardown. */
  _rebuildProjection() {
    // Reset SVG-level transform from flat zoom
    this.globeG.attr('transform', null);
    if (this._zoomBehavior) {
      this.svg.call(this._zoomBehavior.transform, d3.zoomIdentity);
    }
    // Reset scale for new projection
    this._scale = null;
    this._initProjection();
    this._redrawGlobe();
    this._initInteractions();
    this._updateBubbles(300);
  },

  // =========================================================================
  // Globe drawing
  // =========================================================================

  _drawGlobe(container, totalEntries) {
    this.svg = d3.select(container).append('svg')
      .attr('class', 'explore-svg')
      .attr('viewBox', `0 0 ${this.width} ${this.height}`)
      .attr('preserveAspectRatio', 'xMidYMid meet')
      .attr('role', 'img')
      .attr('aria-label', 'Interactive globe showing publication locations');

    this.globeG = this.svg.append('g');

    // Ocean (sphere background)
    this.globeG.append('path')
      .datum({ type: 'Sphere' })
      .attr('class', 'geo-ocean')
      .attr('d', this.path);

    // Graticule (lat/lng grid)
    this.globeG.append('path')
      .datum(d3.geoGraticule10())
      .attr('class', 'geo-graticule')
      .attr('d', this.path);

    // Country boundaries
    const countries = topojson.feature(this.worldData, this.worldData.objects.countries);
    this.globeG.selectAll('.geo-land')
      .data(countries.features)
      .join('path')
      .attr('class', 'geo-land')
      .attr('d', this.path);

    // Country borders
    this.globeG.append('path')
      .datum(topojson.mesh(this.worldData, this.worldData.objects.countries, (a, b) => a !== b))
      .attr('class', 'geo-borders')
      .attr('d', this.path);

    // Bubble layer
    this.bubblesG = this.globeG.append('g').attr('class', 'geo-bubbles-layer');

    // Labels layer (on top of bubbles)
    this.labelsG = this.globeG.append('g').attr('class', 'geo-labels-layer');

    // Click on ocean/land to deselect
    const self = this;
    this.globeG.selectAll('.geo-ocean, .geo-land').on('click', function() {
      if (self.selectedLocation) self._deselectLocation();
    });

    // Bind interaction handlers (drag/wheel for globe, d3.zoom for flat)
    this._initInteractions();

    // Initial bubble render
    this._updateBubbles(0);

    // Coverage note
    const note = document.createElement('div');
    note.className = 'geo-note';
    const geocoded = this._geocodedEntries || 0;
    const pct = totalEntries > 0 ? Math.round(geocoded / totalEntries * 100) : 0;
    note.textContent = `${geocoded.toLocaleString('en')} of ${totalEntries.toLocaleString('en')} entries (${pct}%). Drag to rotate, scroll to zoom (countries \u2192 cities).`;
    container.appendChild(note);

    // Legend
    this._drawLegend(container);
  },

  /** Re-render all globe paths and bubbles after rotation or zoom. */
  _redrawGlobe() {
    this.path = d3.geoPath(this.projection);

    // Update all geo paths
    this.globeG.selectAll('.geo-ocean').attr('d', this.path);
    this.globeG.selectAll('.geo-graticule').attr('d', this.path);
    this.globeG.selectAll('.geo-land').attr('d', this.path);
    this.globeG.selectAll('.geo-borders').attr('d', this.path);

    // Update bubble positions + visibility (hide back-side bubbles)
    this._updateBubblePositions();
  },

  // =========================================================================
  // Bubble rendering
  // =========================================================================

  _updateBubbles(transitionMs) {
    if (!this.bubblesG) return;
    const duration = transitionMs || 0;
    const data = this.zoomLevel === 'city' ? this.allBubbles : this.countryBubbles;

    const maxCount = d3.max(data, d => d.count) || 1;
    const rRange = this.zoomLevel === 'city' ? [3, 24] : [4, 16];
    this.radius = d3.scaleSqrt().domain([1, maxCount]).range(rRange);

    data.sort((a, b) => b.count - a.count);

    const key = d => `${Math.round(d.lat * 100)}_${Math.round(d.lng * 100)}_${d.type}`;
    const self = this;

    const circles = this.bubblesG.selectAll('.geo-bubble').data(data, key);

    circles.exit()
      .transition().duration(duration)
      .attr('r', 0).attr('fill-opacity', 0)
      .remove();

    const enter = circles.enter()
      .append('circle')
      .attr('class', 'geo-bubble')
      .attr('r', 0)
      .attr('fill-opacity', 0)
      .style('cursor', 'pointer');

    // Position + style all bubbles
    const all = enter.merge(circles);

    all.each(function(d) {
      const projected = self.projection([d.lng, d.lat]);
      const visible = self._isVisible(d);
      const el = d3.select(this);

      if (duration > 0) {
        el.transition().duration(duration)
          .attr('cx', projected ? projected[0] : 0)
          .attr('cy', projected ? projected[1] : 0)
          .attr('r', visible ? self.radius(d.count) : 0)
          .attr('fill', self._getBubbleColor(d))
          .attr('fill-opacity', self._bubbleOpacity(d))
          .attr('stroke', self._isSelected(d) ? Explore.colors.gold : 'rgba(255,255,255,0.7)')
          .attr('stroke-width', self._isSelected(d) ? 2.5 : 1);
      } else {
        el.attr('cx', projected ? projected[0] : 0)
          .attr('cy', projected ? projected[1] : 0)
          .attr('r', visible ? self.radius(d.count) : 0)
          .attr('fill', self._getBubbleColor(d))
          .attr('fill-opacity', self._bubbleOpacity(d))
          .attr('stroke', self._isSelected(d) ? Explore.colors.gold : 'rgba(255,255,255,0.7)')
          .attr('stroke-width', self._isSelected(d) ? 2.5 : 1);
      }
    });

    // Event handlers
    all
      .on('mouseenter', function(event, d) {
        if (!self._isVisible(d)) return;
        d3.select(this).attr('stroke', Explore.colors.gold).attr('stroke-width', 2.5);
        const topLangs = self._topN(d.entries, 'language', 3);
        const langList = topLangs.map(([l, c]) => `${l}: ${c}`).join(', ');
        const countryName = d.type === 'country' && d.country
          ? (ExploreGeography._countryNames[d.country] || d.country) : '';
        const name = d.type === 'country'
          ? `${countryName}: ${d.locations.length} cities`
          : d.locations[0] + (d.locations.length > 1 ? ` (+${d.locations.length - 1})` : '');
        Explore.showTooltip(
          `<strong>${esc(name)}</strong><br>${d.count} entries<br><small>${langList}</small>`,
          event
        );
      })
      .on('mouseleave', function(event, d) {
        const sel = self._isSelected(d);
        d3.select(this)
          .attr('stroke', sel ? Explore.colors.gold : 'rgba(255,255,255,0.7)')
          .attr('stroke-width', sel ? 2.5 : 1);
        Explore.hideTooltip();
      })
      .on('click', function(event, d) {
        if (!self._isVisible(d)) return;
        const loc = d.locations[0];

        if (self.selectedLocation === loc) {
          self._deselectLocation();
        } else {
          self.selectedLocation = loc;
          Explore.filters.location = loc;
          Explore._renderFilterChips();
          self._updateBubbles(200);
          Explore.updateSelection(d.entries);
          self._fireFilterEvent();
        }
      });

    // Update city labels
    this._updateLabels();
  },

  /** Fast position + visibility update after rotate/zoom (no data-join). */
  _updateBubblePositions() {
    const self = this;
    this.bubblesG.selectAll('.geo-bubble').each(function(d) {
      const projected = self.projection([d.lng, d.lat]);
      const visible = self._isVisible(d);
      d3.select(this)
        .attr('cx', projected ? projected[0] : 0)
        .attr('cy', projected ? projected[1] : 0)
        .attr('r', visible && self.radius ? self.radius(d.count) : 0)
        .attr('fill-opacity', self._bubbleOpacity(d));
    });
    this._updateLabels();
  },

  /** Show city name labels for top bubbles when zoomed in. */
  _updateLabels() {
    if (!this.labelsG) return;
    const showLabels = this.zoomLevel === 'city';
    const data = this.zoomLevel === 'city' ? this.allBubbles : this.countryBubbles;

    // Top 8 by count, only visible ones
    const topBubbles = showLabels
      ? [...data].filter(d => this._isVisible(d)).sort((a, b) => b.count - a.count).slice(0, 8)
      : [];

    const self = this;
    const labels = this.labelsG.selectAll('.geo-city-label')
      .data(topBubbles, d => d.locations[0]);

    labels.exit().remove();

    labels.enter()
      .append('text')
      .attr('class', 'geo-city-label')
      .merge(labels)
      .each(function(d) {
        const projected = self.projection([d.lng, d.lat]);
        if (!projected) return;
        const r = self.radius ? self.radius(d.count) : 5;
        d3.select(this)
          .attr('x', projected[0] + r + 3)
          .attr('y', projected[1] + 3)
          .text(d.locations[0])
          .attr('font-size', '9px')
          .attr('font-family', 'var(--font-sans)')
          .attr('fill', '#444')
          .attr('paint-order', 'stroke')
          .attr('stroke', 'white')
          .attr('stroke-width', 3)
          .attr('pointer-events', 'none');
      });
  },

  /** Clear location selection, filter chip, and notify other views. */
  _deselectLocation() {
    this.selectedLocation = null;
    Explore.filters.location = null;
    Explore._renderFilterChips();
    this._updateBubbles(200);
    Explore.updateSelection([]);
    this._fireFilterEvent();
  },

  /** Dispatch explore:filterChange with mode='geography' to skip own listener. */
  _fireFilterEvent() {
    document.dispatchEvent(new CustomEvent('explore:filterChange', {
      detail: { filters: { ...Explore.filters }, mode: 'geography' },
    }));
  },

  /** Compute bubble opacity based on visibility and selection state. */
  _bubbleOpacity(d) {
    if (!this._isVisible(d)) return 0;
    if (!this.selectedLocation) return 0.78;
    return d.locations.includes(this.selectedLocation) ? 0.95 : 0.35;
  },

  /** Check if a point is on the visible side (globe: hemisphere check, flat: always visible). */
  _isVisible(bubble) {
    if (this.projectionMode === 'flat') return true;
    const rot = this.projection.rotate();
    const dist = d3.geoDistance([bubble.lng, bubble.lat], [-rot[0], -rot[1]]);
    return dist < Math.PI / 2;
  },

  _isSelected(bubble) {
    if (!this.selectedLocation) return false;
    return bubble.locations.includes(this.selectedLocation);
  },

  // =========================================================================
  // Color
  // =========================================================================

  _getBubbleColor(bubble) {
    if (this.colorMode === 'language') {
      const langCounts = {};
      for (const e of bubble.entries) {
        const lang = e.language || 'Unknown';
        langCounts[lang] = (langCounts[lang] || 0) + 1;
      }
      const dominant = Object.entries(langCounts).sort((a, b) => b[1] - a[1])[0];
      return dominant
        ? (Explore.colors.languages[dominant[0]] || Explore.colors.languages['Other'])
        : Explore.colors.languages['Other'];
    }
    const periodCounts = {};
    for (const e of bubble.entries) {
      periodCounts[e.timePeriod || 'unknown'] = (periodCounts[e.timePeriod || 'unknown'] || 0) + 1;
    }
    const dominant = Object.entries(periodCounts).sort((a, b) => b[1] - a[1])[0];
    return dominant ? this._getPeriodColor(dominant[0]) : '#9E9585';
  },

  // =========================================================================
  // Brushed Linking
  // =========================================================================

  _bindFilterListener() {
    if (this._filterHandler) {
      document.removeEventListener('explore:filterChange', this._filterHandler);
    }
    this._filterHandler = (event) => {
      if (Explore.mode !== 'geography') return;
      if (event.detail && event.detail.mode === 'geography') return;
      const filtered = Explore.hasActiveFilters() ? Explore.getFiltered() : Explore.entries;
      this.currentEntries = filtered;
      this.allBubbles = this._buildCityBubbles(filtered);
      this.countryBubbles = this._buildCountryBubbles(this.allBubbles);
      this._updateBubbles(300);
    };
    document.addEventListener('explore:filterChange', this._filterHandler);
  },

  // =========================================================================
  // Helpers
  // =========================================================================

  _topN(entries, field, n) {
    const counts = {};
    for (const e of entries) {
      const v = e[field];
      if (v) counts[v] = (counts[v] || 0) + 1;
    }
    return Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, n);
  },

  _drawLegend(container) {
    const old = container.querySelector('.geo-legend');
    if (old) old.remove();
    const legendDiv = document.createElement('div');
    legendDiv.className = 'geo-legend';

    if (this.colorMode === 'language') {
      const allLangs = {};
      for (const b of this.allBubbles) {
        for (const e of b.entries) allLangs[e.language || 'Unknown'] = (allLangs[e.language || 'Unknown'] || 0) + 1;
      }
      const topLangs = Object.entries(allLangs).sort((a, b) => b[1] - a[1]).slice(0, 8);
      legendDiv.innerHTML = topLangs.map(([lang]) => {
        const color = Explore.colors.languages[lang] || Explore.colors.languages['Other'];
        const active = Explore.filters.languages.includes(lang);
        return `<span class="geo-legend-item${active ? ' active' : ''}" data-key="languages" data-value="${esc(lang)}">` +
          `<span class="geo-legend-dot" style="background:${color}"></span>${esc(lang)}</span>`;
      }).join('');
    } else {
      const self = this;
      legendDiv.innerHTML = Object.entries(PERIOD_LABELS).map(([key, label]) => {
        const color = self._getPeriodColor(key);
        const active = Explore.filters.period === key;
        return `<span class="geo-legend-item${active ? ' active' : ''}" data-key="period" data-value="${key}">` +
          `<span class="geo-legend-dot" style="background:${color}"></span>${label}</span>`;
      }).join('');
    }
    // Interactive legend: click to filter
    legendDiv.querySelectorAll('.geo-legend-item').forEach(item => {
      item.addEventListener('click', () => {
        Explore.toggleFilter(item.dataset.key, item.dataset.value);
      });
    });
    container.appendChild(legendDiv);
  },

  /** Period → color mapping (shared between _getBubbleColor and _drawLegend). */
  _periodColors: {
    'pre-zweig': '#9E9585', 'lifetime': null, // set at runtime from Explore.colors.burgundy
    'post-wwii': '#6B7A3A', 'late-20c': '#5B3A7A', 'contemporary': null,
  },

  /** Get period color, resolving runtime references. */
  _getPeriodColor(key) {
    if (key === 'lifetime') return Explore.colors.burgundy;
    if (key === 'contemporary') return Explore.colors.gold;
    return this._periodColors[key] || '#9E9585';
  },

  /** ISO 3166-1 alpha-2 → readable country names (only countries in the dataset). */
  _countryNames: {
    AE:'UAE',AL:'Albania',AM:'Armenia',AR:'Argentina',AT:'Austria',AU:'Australia',
    AZ:'Azerbaijan',BA:'Bosnia',BD:'Bangladesh',BE:'Belgium',BG:'Bulgaria',BR:'Brazil',
    BY:'Belarus',CA:'Canada',CH:'Switzerland',CL:'Chile',CN:'China',CO:'Colombia',
    CY:'Cyprus',CZ:'Czechia',DE:'Germany',DK:'Denmark',DZ:'Algeria',EE:'Estonia',
    EG:'Egypt',ES:'Spain',FI:'Finland',FR:'France',GB:'United Kingdom',GE:'Georgia',
    GR:'Greece',HR:'Croatia',HU:'Hungary',ID:'Indonesia',IL:'Israel',IN:'India',
    IQ:'Iraq',IR:'Iran',IS:'Iceland',IT:'Italy',JO:'Jordan',JP:'Japan',KG:'Kyrgyzstan',
    KR:'South Korea',KW:'Kuwait',KZ:'Kazakhstan',LB:'Lebanon',LT:'Lithuania',
    LU:'Luxembourg',LV:'Latvia',MK:'North Macedonia',MN:'Mongolia',MX:'Mexico',
    MY:'Malaysia',NL:'Netherlands',NO:'Norway',OM:'Oman',PL:'Poland',PS:'Palestine',
    PT:'Portugal',QA:'Qatar',RO:'Romania',RS:'Serbia',RU:'Russia',SA:'Saudi Arabia',
    SE:'Sweden',SI:'Slovenia',SK:'Slovakia',SY:'Syria',TH:'Thailand',TJ:'Tajikistan',
    TN:'Tunisia',TR:'Turkey',TW:'Taiwan',UA:'Ukraine',US:'United States',UY:'Uruguay',
    UZ:'Uzbekistan',VN:'Vietnam',XK:'Kosovo',ZA:'South Africa',
  },
};

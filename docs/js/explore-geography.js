/**
 * Explore Geography — Interactive map with bubble overlay.
 *
 * Two projection modes:
 * - Globe (default): d3.geoOrthographic() — one hemisphere, drag-to-rotate, scroll-to-zoom
 * - Flat: d3.geoNaturalEarth1() — all data visible, pan/zoom via d3.zoom
 *
 * Semantic zoom moves between a country view and a city view. A click filters
 * at the level it is made on: a country bubble sets the country filter, a city
 * bubble sets the place filter, so the chip, the selection and the drawn
 * bubbles always describe the same set of records.
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
  selectedCountry: null,
  animationTimer: null,
  animationDecade: null,
  isPlaying: false,
  width: 700,
  height: 560,
  radius: null,
  projectionMode: 'globe',     // 'globe' (default) | 'flat' (all data visible)
  _container: null,
  _zoomBehavior: null,         // d3.zoom instance for flat mode
  _rotation: [-10, -45, 0],   // initial rotation: centered on Europe [λ, φ, γ]
  _scale: null,                // current projection scale
  _baseScale: null,            // default scale (fit to container)
  _mergeKeys: null,            // location name → canonical merge key
  _mergeCanon: null,           // merge key → representative geo record

  // =========================================================================
  // Render
  // =========================================================================

  async render(entries) {
    const container = document.getElementById('viz-geography');
    if (!container) return;
    this._container = container;
    container.innerHTML = '';
    this.currentEntries = entries;
    this.selectedLocation = Explore.filters.location || null;
    this.selectedCountry = Explore.filters.country || null;

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
      this._buildMergeIndex();
    }
    if (!this.worldData) {
      try {
        // Vendored world-atlas@2 geometry (Natural Earth data, public
        // domain): the site contacts no external host at runtime.
        const resp = await fetch('vendor/countries-110m.json');
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        this.worldData = await resp.json();
      } catch (e) {
        console.error('Failed to load world map:', e);
        container.innerHTML = '<div class="ov-empty">Could not load world map data.</div>';
        return;
      }
    }

    // Controls
    this._drawControls(container);

    // Set up projection (globe or flat depending on projectionMode)
    const rect = container.getBoundingClientRect();
    this.width = rect.width || 700;
    this.height = CHART_DIMS.geography?.height || 560;
    this._initProjection();

    // Build bubble data
    this.allBubbles = this._buildCityBubbles(entries);
    this.countryBubbles = this._buildCountryBubbles(this.allBubbles);

    // Draw globe
    this._drawGlobe(container, entries);

    // Reconcile this view when a filter changes elsewhere
    Explore.bindModeFilterListener('geography', (filtered) => {
      this.currentEntries = filtered;
      this.allBubbles = this._buildCityBubbles(filtered);
      this.countryBubbles = this._buildCountryBubbles(this.allBubbles);
      this._updateBubbles(motionMs(300));
      this._renderCoverageNote(this._container, filtered.length);
      this._drawLegend(this._container);
    });
  },

  /** ISO country code a record's place resolves to, or null. */
  countryOfEntry(entry) {
    if (!entry || !entry.location || !this.locationData) return null;
    const geo = this.locationData[entry.location];
    return (geo && geo.country) || null;
  },

  // =========================================================================
  // Controls
  // =========================================================================

  /** The earliest decade carrying enough records for the slider to start on. */
  _sliderBounds() {
    const counts = new Map();
    for (const e of Explore.entries) {
      if (!e.year) continue;
      const d = Math.floor(e.year / 10) * 10;
      counts.set(d, (counts.get(d) || 0) + 1);
    }
    const occupied = [...counts.entries()]
      .filter(([, n]) => n >= 10)
      .map(([d]) => d)
      .sort((a, b) => a - b);
    const fallbackMin = Math.floor(Explore.yearExtent[0] / 10) * 10;
    const fallbackMax = Math.floor(Explore.yearExtent[1] / 10) * 10;
    return occupied.length
      ? [occupied[0], occupied[occupied.length - 1]]
      : [fallbackMin, fallbackMax];
  },

  _drawControls(container) {
    const controls = document.createElement('div');
    controls.className = 'geo-controls';
    controls.id = 'geo-controls';
    const [minD, maxD] = this._sliderBounds();
    const playing = this.isPlaying;
    controls.innerHTML = `
      <span class="ov-title" style="margin-bottom:0" id="geo-color-label">Color:</span>
      <button type="button" class="geo-toggle ${this.colorMode === 'language' ? 'active' : ''}"
        aria-pressed="${this.colorMode === 'language'}" data-cmode="language">Language</button>
      <button type="button" class="geo-toggle ${this.colorMode === 'period' ? 'active' : ''}"
        aria-pressed="${this.colorMode === 'period'}" data-cmode="period">Period</button>
      <span style="flex:1"></span>
      <button type="button" class="geo-toggle" id="geo-reset-btn"
        aria-label="Reset map view and clear place filters"
        title="Reset map view and clear place filters">&#8634;</button>
      <button type="button" class="geo-toggle${this.projectionMode === 'flat' ? ' active' : ''}"
        id="geo-projection-btn" aria-pressed="${this.projectionMode === 'flat'}"
        aria-label="Flat map projection" title="Toggle globe / flat map">&#127760;</button>
      <button type="button" class="geo-toggle geo-play-btn" id="geo-play-btn"
        aria-pressed="${playing}" aria-label="${playing ? 'Pause decade playback' : 'Start decade playback'}"
        title="Animate through decades">
        <span id="geo-play-icon" aria-hidden="true">${playing ? '&#9646;&#9646;' : '&#9654;'}</span>
      </button>
      <label class="geo-slider-label" for="geo-decade-slider">Decade</label>
      <input type="range" id="geo-decade-slider" class="geo-slider"
        aria-label="Show a single decade"
        min="${minD}" max="${maxD}" step="10"
        value="${this.animationDecade || minD}">
      <span id="geo-decade-label" class="geo-decade-label" aria-live="polite">${this.animationDecade ? this.animationDecade + 's' : 'All'}</span>
    `;
    container.appendChild(controls);

    controls.querySelectorAll('[data-cmode]').forEach(btn => {
      btn.addEventListener('click', () => {
        this.colorMode = btn.dataset.cmode;
        this._updateBubbles();
        this._drawLegend(this._container);
        controls.querySelectorAll('[data-cmode]').forEach(b => {
          const active = b.dataset.cmode === this.colorMode;
          b.classList.toggle('active', active);
          b.setAttribute('aria-pressed', String(active));
        });
      });
    });

    document.getElementById('geo-reset-btn').addEventListener('click', () => {
      this._rotation = [-10, -45, 0];
      this._scale = this._baseScale;
      this.zoomLevel = 'country';
      this.selectedLocation = null;
      this.selectedCountry = null;
      Explore.filters.location = null;
      Explore.filters.country = null;
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
      const btn = document.getElementById('geo-projection-btn');
      btn.classList.toggle('active', this.projectionMode === 'flat');
      btn.setAttribute('aria-pressed', String(this.projectionMode === 'flat'));
      this._rebuildProjection();
    });

    document.getElementById('geo-play-btn').addEventListener('click', () => {
      if (this.isPlaying) this._stopAnimation();
      else this._startAnimation();
    });

    document.getElementById('geo-decade-slider').addEventListener('input', (e) => {
      if (this.isPlaying) this._stopAnimation();
      this._setDecade(parseInt(e.target.value, 10));
    });

    // Double-click slider to reset to "All"
    document.getElementById('geo-decade-slider').addEventListener('dblclick', () => {
      if (this.isPlaying) this._stopAnimation();
      this._resetToAll();
    });
  },

  /** Keep the playback button's name and state in step with what it does. */
  _syncPlayButton() {
    const btn = document.getElementById('geo-play-btn');
    const icon = document.getElementById('geo-play-icon');
    if (icon) icon.innerHTML = this.isPlaying ? '&#9646;&#9646;' : '&#9654;';
    if (btn) {
      btn.setAttribute('aria-pressed', String(this.isPlaying));
      btn.setAttribute('aria-label', this.isPlaying ? 'Pause decade playback' : 'Start decade playback');
    }
  },

  // =========================================================================
  // Animation
  // =========================================================================

  _startAnimation() {
    this.isPlaying = true;
    this._syncPlayButton();
    const slider = document.getElementById('geo-decade-slider');
    const minD = parseInt(slider.min, 10), maxD = parseInt(slider.max, 10);
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
    this._syncPlayButton();
  },

  /**
   * Show a single decade. The decade narrows whatever the other chips already
   * select, so it filters the current set rather than the whole corpus.
   */
  _setDecade(decade) {
    this.animationDecade = decade;
    const label = document.getElementById('geo-decade-label');
    if (label) label.textContent = decade + 's';

    Explore.filters.yearRange = [decade, decade + 9];
    Explore._renderFilterChips();
    const filtered = Explore.getFiltered();

    this.allBubbles = this._buildCityBubbles(filtered);
    this.countryBubbles = this._buildCountryBubbles(this.allBubbles);
    this._updateBubbles(motionMs(800));
    Explore.updateSelection(filtered.length < Explore.entries.length ? filtered : []);
    this._fireFilterEvent();
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
    const filtered = Explore.visibleEntries();

    this.allBubbles = this._buildCityBubbles(filtered);
    this.countryBubbles = this._buildCountryBubbles(this.allBubbles);
    this._updateBubbles(motionMs(500));
    Explore.updateSelection(filtered.length < Explore.entries.length ? filtered : []);
    this._fireFilterEvent();
  },

  // =========================================================================
  // Bubble builders
  // =========================================================================

  /**
   * Variant spellings that sit within 0.15° of each other are one place. The
   * pairing depends only on the geodata, so it is resolved once instead of
   * re-scanning the growing bubble list on every filter change.
   */
  _buildMergeIndex() {
    this._mergeKeys = new Map();
    this._mergeCanon = new Map();
    const anchors = [];
    for (const [name, geo] of Object.entries(this.locationData)) {
      if (!geo || typeof geo.lat !== 'number' || typeof geo.lng !== 'number') continue;
      const hit = anchors.find(a =>
        Math.abs(a.lat - geo.lat) < 0.15 && Math.abs(a.lng - geo.lng) < 0.15);
      if (hit) {
        this._mergeKeys.set(name, hit.key);
      } else {
        anchors.push({ key: name, lat: geo.lat, lng: geo.lng });
        this._mergeKeys.set(name, name);
        this._mergeCanon.set(name, { lat: geo.lat, lng: geo.lng, country: geo.country || null });
      }
    }
  },

  _buildCityBubbles(entries) {
    if (!this._mergeKeys) this._buildMergeIndex();
    const byKey = new Map();
    let geocoded = 0;
    const ungeocoded = new Map();

    for (const e of entries) {
      if (!e.location) continue;
      const key = this._mergeKeys.get(e.location);
      if (!key) {
        ungeocoded.set(e.location, (ungeocoded.get(e.location) || 0) + 1);
        continue;
      }
      geocoded++;
      let b = byKey.get(key);
      if (!b) {
        const canon = this._mergeCanon.get(key);
        b = {
          key, count: 0, entries: [], locations: [],
          lat: canon.lat, lng: canon.lng, country: canon.country, type: 'city',
        };
        byKey.set(key, b);
      }
      b.count++;
      b.entries.push(e);
      if (!b.locations.includes(e.location)) b.locations.push(e.location);
    }

    this._geocodedEntries = geocoded;
    this._ungeocoded = [...ungeocoded.entries()].sort((a, b) => b[1] - a[1]);
    return [...byKey.values()];
  },

  _buildCountryBubbles(cityBubbles) {
    const countryMap = new Map();
    for (const b of cityBubbles) {
      const cc = b.country || 'XX';
      if (!countryMap.has(cc)) {
        countryMap.set(cc, {
          key: cc, count: 0, entries: [], locations: [],
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
      result.push({ ...cb, lat: cb.latSum / cb.cityCount, lng: cb.lngSum / cb.cityCount });
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
            self._updateBubbles(motionMs(200));
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
    this._updateBubbles(motionMs(300));
  },

  // =========================================================================
  // Globe drawing
  // =========================================================================

  _drawGlobe(container, entries) {
    const totalEntries = entries.length;
    this.svg = d3.select(container).append('svg')
      .attr('class', 'explore-svg')
      .attr('viewBox', `0 0 ${this.width} ${this.height}`)
      .attr('preserveAspectRatio', 'xMidYMid meet')
      .attr('role', 'group')
      .attr('aria-labelledby', 'geo-title geo-desc');
    this.svg.append('title').attr('id', 'geo-title').text('Publication places');
    this.svg.append('desc').attr('id', 'geo-desc').text(
      'Map of publication places; bubble area is the number of entries. ' +
      'Drag to rotate, scroll to zoom from countries to cities. ' +
      'The legend below filters by language or period from the keyboard.'
    );
    // The pointer instruction is a hint, not a caption; it stays off the map.
    container.title = 'Drag to rotate, scroll to zoom (countries to cities)';

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
    this.globeG.selectAll('.geo-ocean, .geo-land').on('click', function () {
      if (self.selectedLocation || self.selectedCountry) self._deselectPlace();
    });

    // Bind interaction handlers (drag/wheel for globe, d3.zoom for flat)
    this._initInteractions();

    // Initial bubble render
    this._updateBubbles(0);

    // Coverage note plus the places the geocoding could not resolve
    this._renderCoverageNote(container, totalEntries);

    // Legend
    this._drawLegend(container);
  },

  /**
   * States what the map cannot show, in the sidebar rather than on the map,
   * and makes the remainder reachable: an unresolved place name is a curation
   * task, not a rounding error, so each one opens its own records.
   */
  _renderCoverageNote(container, totalEntries) {
    const geocoded = this._geocodedEntries || 0;
    const unplaced = Math.max(0, totalEntries - geocoded);
    const missing = this._ungeocoded || [];

    let html = unplaced
      ? `<button type="button" class="link-btn" id="geo-unplaced">${fmt(unplaced)} entries not placed</button>`
      : '';
    if (missing.length) {
      html += `<details class="geo-missing"><summary>${fmt(missing.length)} unresolved place names</summary> `
        + missing.slice(0, 25).map(([name, n]) =>
          `<button type="button" class="link-btn geo-missing-item" data-loc="${esc(name)}">${esc(name)} (${fmt(n)})</button>`
        ).join(' ')
        + (missing.length > 25 ? ` <span>and ${fmt(missing.length - 25)} more names</span>` : '')
        + `</details>`;
    }
    const note = Explore.setViewNote(html);
    if (!note) return;

    const unplacedBtn = note.querySelector('#geo-unplaced');
    if (unplacedBtn) {
      unplacedBtn.addEventListener('click', () => {
        // Placed means the record names a location the geodata resolves.
        App.showCustomResults(
          this.currentEntries.filter(e => !e.location || !this._mergeKeys.get(e.location)),
          'Entries without a mapped place'
        );
      });
    }
    note.querySelectorAll('.geo-missing-item').forEach(btn => {
      btn.addEventListener('click', () => {
        const loc = btn.dataset.loc;
        App.showCustomResults(
          this.currentEntries.filter(e => e.location === loc),
          `Unresolved place: ${loc}`
        );
      });
    });
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
    const duration = motionMs(transitionMs || 0);
    const data = this.zoomLevel === 'city' ? this.allBubbles : this.countryBubbles;

    const maxCount = d3.max(data, d => d.count) || 1;
    const rRange = this.zoomLevel === 'city' ? [3, 24] : [4, 16];
    this.radius = d3.scaleSqrt().domain([1, maxCount]).range(rRange);

    data.sort((a, b) => b.count - a.count);

    // Identity is the place, not its current weighted position: keying on the
    // coordinate made every filter change tear down and rebuild every bubble.
    const key = d => `${d.type}:${d.key}`;
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

    all.each(function (d) {
      const projected = self.projection([d.lng, d.lat]);
      const visible = self._isVisible(d);
      const base = d3.select(this);
      const el = duration > 0 ? base.transition().duration(duration) : base;
      el.attr('cx', projected ? projected[0] : 0)
        .attr('cy', projected ? projected[1] : 0)
        .attr('r', visible ? self.radius(d.count) : 0)
        .attr('fill', self._getBubbleColor(d))
        .attr('fill-opacity', self._bubbleOpacity(d))
        .attr('stroke', self._isSelected(d) ? Explore.colors.gold : 'rgba(255,255,255,0.7)')
        .attr('stroke-width', self._isSelected(d) ? 2.5 : 1);
    });

    // Event handlers
    all
      .on('mouseenter', function (event, d) {
        if (!self._isVisible(d)) return;
        d3.select(this).attr('stroke', Explore.colors.gold).attr('stroke-width', 2.5);
        Explore.showTooltip(self._bubbleTooltip(d), event);
      })
      .on('mouseleave', function (event, d) {
        const sel = self._isSelected(d);
        d3.select(this)
          .attr('stroke', sel ? Explore.colors.gold : 'rgba(255,255,255,0.7)')
          .attr('stroke-width', sel ? 2.5 : 1);
        Explore.hideTooltip();
      })
      .on('click', function (event, d) {
        if (!self._isVisible(d)) return;
        self._selectBubble(d);
      });

    // Update city labels
    this._updateLabels();
  },

  _bubbleTooltip(d) {
    const topLangs = topN(d.entries, 'language', 3);
    const langList = topLangs.map(([l, c]) => `${esc(l)}: ${fmt(c)}`).join(', ');
    const name = d.type === 'country'
      ? `${this._countryNames[d.country] || d.country} · ${d.locations.length} places`
      : d.locations[0] + (d.locations.length > 1 ? ` (+${d.locations.length - 1})` : '');
    return `<strong>${esc(name)}</strong><br>${fmt(d.count)} entries<br><small>${langList}</small>`;
  },

  /**
   * Filter at the level the click was made on. A country bubble stands for
   * every place in that country, so it sets the country filter; a city bubble
   * sets the place filter for the spelling it is drawn under.
   */
  _selectBubble(d) {
    if (d.type === 'country') {
      if (this.selectedCountry === d.country) { this._deselectPlace(); return; }
      this.selectedCountry = d.country;
      this.selectedLocation = null;
      Explore.filters.country = d.country;
      Explore.filters.location = null;
    } else {
      const loc = d.locations[0];
      if (this.selectedLocation === loc) { this._deselectPlace(); return; }
      this.selectedLocation = loc;
      this.selectedCountry = null;
      Explore.filters.location = loc;
      Explore.filters.country = null;
    }
    Explore._renderFilterChips();
    this._updateBubbles(motionMs(200));
    Explore.updateSelection(Explore.getFiltered());
    this._fireFilterEvent();
  },

  /** Fast position + visibility update after rotate/zoom (no data-join). */
  _updateBubblePositions() {
    const self = this;
    this.bubblesG.selectAll('.geo-bubble').each(function (d) {
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
      .data(topBubbles, d => d.key);

    labels.exit().remove();

    labels.enter()
      .append('text')
      .attr('class', 'geo-city-label')
      .merge(labels)
      .each(function (d) {
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

  /** Clear the place selection, its chip, and notify other views. */
  _deselectPlace() {
    this.selectedLocation = null;
    this.selectedCountry = null;
    Explore.filters.location = null;
    Explore.filters.country = null;
    Explore._renderFilterChips();
    this._updateBubbles(motionMs(200));
    Explore.updateSelection([]);
    this._fireFilterEvent();
  },

  /** Dispatch explore:filterChange with mode='geography' to skip own listener. */
  _fireFilterEvent() {
    document.dispatchEvent(new CustomEvent('explore:filterChange', {
      detail: { filters: { ...Explore.filters }, mode: 'geography' },
    }));
    Explore.updateExploreURL(false);
  },

  /** Compute bubble opacity based on visibility and selection state. */
  _bubbleOpacity(d) {
    if (!this._isVisible(d)) return 0;
    if (!this.selectedLocation && !this.selectedCountry) return 0.78;
    return this._isSelected(d) ? 0.95 : 0.35;
  },

  /** Check if a point is on the visible side (globe: hemisphere check, flat: always visible). */
  _isVisible(bubble) {
    if (this.projectionMode === 'flat') return true;
    const rot = this.projection.rotate();
    const dist = d3.geoDistance([bubble.lng, bubble.lat], [-rot[0], -rot[1]]);
    return dist < Math.PI / 2;
  },

  _isSelected(bubble) {
    if (this.selectedCountry) return bubble.country === this.selectedCountry;
    if (this.selectedLocation) return bubble.locations.includes(this.selectedLocation);
    return false;
  },

  // =========================================================================
  // Color
  // =========================================================================

  _getBubbleColor(bubble) {
    if (this.colorMode === 'language') {
      const langCounts = {};
      for (const e of bubble.entries) {
        const lang = e.language || Explore.NOT_RECORDED;
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
  // Legend — the keyboard path into the map
  // =========================================================================

  _drawLegend(container) {
    if (!container) return;
    const old = container.querySelector('.geo-legend');
    if (old) old.remove();
    const legendDiv = document.createElement('div');
    legendDiv.className = 'geo-legend';
    legendDiv.setAttribute('role', 'group');
    legendDiv.setAttribute('aria-label', 'Map legend, filters the entries');

    if (this.colorMode === 'language') {
      const allLangs = {};
      for (const b of this.allBubbles) {
        for (const e of b.entries) {
          const lang = e.language || Explore.NOT_RECORDED;
          allLangs[lang] = (allLangs[lang] || 0) + 1;
        }
      }
      const topLangs = Object.entries(allLangs).sort((a, b) => b[1] - a[1]).slice(0, 8);
      legendDiv.innerHTML = topLangs.map(([lang, count]) => {
        const color = Explore.colors.languages[lang] || Explore.colors.languages['Other'];
        const active = Explore.filters.languages.includes(lang);
        return `<button type="button" class="geo-legend-item${active ? ' active' : ''}" ` +
          `aria-pressed="${active}" data-key="languages" data-value="${esc(lang)}">` +
          `<span class="geo-legend-dot" style="background:${color}"></span>${esc(lang)} (${fmt(count)})</button>`;
      }).join('');
    } else {
      legendDiv.innerHTML = Object.entries(PERIOD_LABELS).map(([key, label]) => {
        const color = this._getPeriodColor(key);
        const active = Explore.filters.period === key;
        return `<button type="button" class="geo-legend-item${active ? ' active' : ''}" ` +
          `aria-pressed="${active}" data-key="period" data-value="${key}">` +
          `<span class="geo-legend-dot" style="background:${color}"></span>${esc(label)}</button>`;
      }).join('');
    }
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

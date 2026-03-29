/**
 * Statistics page — timeline, languages, locations, types.
 * All chart elements are clickable → navigate to filtered results.
 */
const Charts = {
  instances: {},

  render(entries) {
    const container = document.getElementById('view-stats');

    // Stats
    const types = new Set(entries.map(e => e.entryType).filter(Boolean));
    const languages = new Set(entries.map(e => e.language).filter(Boolean));
    const locations = new Set(entries.map(e => e.location).filter(Boolean));
    const years = entries.map(e => e.year).filter(Boolean);
    const minYear = years.length ? Math.min(...years) : '—';
    const maxYear = years.length ? Math.max(...years) : '—';

    container.innerHTML = `
      <h2 class="section-heading">Statistics</h2>

      <div class="stats-cards">
        <div class="stat-card">
          <div class="stat-value">${entries.length.toLocaleString('en')}</div>
          <div class="stat-label">Entries</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${types.size}</div>
          <div class="stat-label">Types</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${languages.size}</div>
          <div class="stat-label">Languages</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${minYear}–${maxYear}</div>
          <div class="stat-label">Time Span</div>
        </div>
      </div>

      <div class="chart-card chart-card-full">
        <div class="chart-title">Publications by Decade</div>
        <canvas id="chart-timeline" height="180"></canvas>
      </div>

      <div class="charts-grid" style="margin-top:1.5rem">
        <div class="chart-card">
          <div class="chart-title">Languages (Top 10)</div>
          <canvas id="chart-languages" height="220"></canvas>
        </div>
        <div class="chart-card">
          <div class="chart-title">Locations (Top 15)</div>
          <canvas id="chart-locations" height="220"></canvas>
        </div>
      </div>

      <div class="chart-card chart-card-full" style="margin-top:1.5rem">
        <div class="chart-title">Entry Types</div>
        <canvas id="chart-types" height="140"></canvas>
      </div>

      <div class="stats-export">
        <button class="action-btn" onclick="Export.fullDataset()">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          Download full dataset (JSON-LD)
        </button>
      </div>
    `;

    this.renderTimeline(entries);
    this.renderLanguages(entries);
    this.renderLocations(entries);
    this.renderTypes(entries);
  },

  renderTimeline(entries) {
    const decades = {};
    for (const e of entries) {
      if (e.year && e.year >= 1800 && e.year <= 2025) {
        const decade = Math.floor(e.year / 10) * 10;
        decades[decade] = (decades[decade] || 0) + 1;
      }
    }

    const labels = Object.keys(decades).sort();
    const data = labels.map(y => decades[y]);

    this.destroy('timeline');
    this.instances.timeline = new Chart(
      document.getElementById('chart-timeline'),
      {
        type: 'bar',
        data: {
          labels: labels.map(y => `${y}s`),
          datasets: [{
            data,
            backgroundColor: labels.map(y =>
              y >= 1880 && y <= 1940 ? '#B8963E' : '#7A1B2D'
            ),  // Gold = Zweig's lifetime decades, Burgundy = all others
            borderRadius: 3,
          }],
        },
        options: {
          plugins: { legend: { display: false } },
          scales: {
            y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: '#EDE8DF' } },
            x: { grid: { display: false } },
          },
          onClick: (_, elements) => {
            if (elements.length) {
              const decade = parseInt(labels[elements[0].index]);
              let period;
              if (decade < 1880) period = 'pre-zweig';
              else if (decade <= 1940) period = 'lifetime';
              else if (decade <= 1980) period = 'post-wwii';
              else if (decade <= 2000) period = 'late-20c';
              else period = 'contemporary';
              location.hash = `period=${period}`;
            }
          },
        },
      }
    );
  },

  renderLanguages(entries) {
    const langs = {};
    for (const e of entries) {
      if (e.language) langs[e.language] = (langs[e.language] || 0) + 1;
    }

    const sorted = Object.entries(langs).sort((a, b) => b[1] - a[1]).slice(0, 10);
    const labels = sorted.map(([l]) => l);
    const data = sorted.map(([, c]) => c);
    const colors = [
      '#7A1B2D', '#B8963E', '#6B7A3A', '#5B5040', '#8B5C3A',
      '#5B3A7A', '#3A5B6B', '#7A4A1B', '#3A3A5B', '#6B3A4A',
    ];

    this.destroy('languages');
    this.instances.languages = new Chart(
      document.getElementById('chart-languages'),
      {
        type: 'doughnut',
        data: {
          labels,
          datasets: [{ data, backgroundColor: colors }],
        },
        options: {
          plugins: {
            legend: { position: 'right', labels: { boxWidth: 12, font: { size: 11 } } },
          },
          onClick: (_, elements) => {
            if (elements.length) {
              location.hash = `language=${encodeURIComponent(labels[elements[0].index])}`;
            }
          },
        },
      }
    );
  },

  renderLocations(entries) {
    const locs = {};
    for (const e of entries) {
      if (e.location) locs[e.location] = (locs[e.location] || 0) + 1;
    }

    const sorted = Object.entries(locs).sort((a, b) => b[1] - a[1]).slice(0, 15);
    const labels = sorted.map(([l]) => l);
    const data = sorted.map(([, c]) => c);

    this.destroy('locations');
    this.instances.locations = new Chart(
      document.getElementById('chart-locations'),
      {
        type: 'bar',
        data: {
          labels,
          datasets: [{
            data,
            backgroundColor: '#7A1B2D',
            borderRadius: 3,
          }],
        },
        options: {
          indexAxis: 'y',
          plugins: { legend: { display: false } },
          scales: {
            x: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: '#EDE8DF' } },
            y: { grid: { display: false } },
          },
          onClick: (_, elements) => {
            if (elements.length) {
              location.hash = `location=${encodeURIComponent(labels[elements[0].index])}`;
            }
          },
        },
      }
    );
  },

  renderTypes(entries) {
    const types = {};
    for (const e of entries) {
      if (e.entryType) {
        const label = ENTRY_TYPE_LABELS[e.entryType] || e.entryType;
        types[e.entryType] = types[e.entryType] || { label, count: 0 };
        types[e.entryType].count++;
      }
    }

    const sorted = Object.entries(types).sort((a, b) => b[1].count - a[1].count);
    const typeKeys = sorted.map(([k]) => k);
    const labels = sorted.map(([, v]) => v.label);
    const data = sorted.map(([, v]) => v.count);

    this.destroy('types');
    this.instances.types = new Chart(
      document.getElementById('chart-types'),
      {
        type: 'bar',
        data: {
          labels,
          datasets: [{
            data,
            backgroundColor: '#B8963E',
            borderRadius: 3,
          }],
        },
        options: {
          indexAxis: 'y',
          plugins: { legend: { display: false } },
          scales: {
            x: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: '#EDE8DF' } },
            y: { grid: { display: false } },
          },
          onClick: (_, elements) => {
            if (elements.length) {
              location.hash = `type=${typeKeys[elements[0].index]}`;
            }
          },
        },
      }
    );
  },

  destroy(key) {
    if (this.instances[key]) {
      this.instances[key].destroy();
      delete this.instances[key];
    }
  },

};

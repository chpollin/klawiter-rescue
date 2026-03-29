/**
 * Dashboard charts — timeline, language distribution, type distribution.
 */
const Charts = {
  instances: {},

  render(entries) {
    this.renderStats(entries);
    this.renderTimeline(entries);
    this.renderLanguages(entries);
    this.renderTypes(entries);
  },

  renderStats(entries) {
    const types = new Set(entries.map(e => e.entryType).filter(Boolean));
    const languages = new Set(entries.map(e => e.language).filter(Boolean));
    const years = entries.map(e => e.year).filter(Boolean);
    const minYear = years.length ? Math.min(...years) : '—';
    const maxYear = years.length ? Math.max(...years) : '—';

    document.getElementById('stats-cards').innerHTML = `
      <div class="stat-card">
        <div class="stat-value">${entries.length.toLocaleString('de-DE')}</div>
        <div class="stat-label">Einträge</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${types.size}</div>
        <div class="stat-label">Entitätstypen</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${languages.size}</div>
        <div class="stat-label">Sprachen</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${minYear}–${maxYear}</div>
        <div class="stat-label">Zeitraum</div>
      </div>
    `;
  },

  renderTimeline(entries) {
    const years = {};
    for (const e of entries) {
      if (e.year && e.year >= 1880 && e.year <= 2025) {
        // Group by decade
        const decade = Math.floor(e.year / 10) * 10;
        years[decade] = (years[decade] || 0) + 1;
      }
    }

    const labels = Object.keys(years).sort();
    const data = labels.map(y => years[y]);

    this.destroy('timeline');
    this.instances.timeline = new Chart(
      document.getElementById('chart-timeline'),
      {
        type: 'bar',
        data: {
          labels: labels.map(y => `${y}er`),
          datasets: [{
            data,
            backgroundColor: labels.map(y =>
              y >= 1881 && y <= 1942 ? '#93c5fd' : '#dbeafe'
            ),
            borderRadius: 3,
          }],
        },
        options: {
          plugins: { legend: { display: false } },
          scales: {
            y: { beginAtZero: true, ticks: { precision: 0 } },
            x: { grid: { display: false } },
          },
          onClick: (_, elements) => {
            if (elements.length) {
              const decade = labels[elements[0].index];
              // Could filter by decade range
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
      '#3b82f6', '#ef4444', '#f59e0b', '#10b981', '#8b5cf6',
      '#ec4899', '#06b6d4', '#f97316', '#84cc16', '#6366f1',
    ];

    this.destroy('languages');
    this.instances.languages = new Chart(
      document.getElementById('chart-languages'),
      {
        type: 'doughnut',
        data: {
          labels,
          datasets: [{
            data,
            backgroundColor: colors,
          }],
        },
        options: {
          plugins: {
            legend: { position: 'right', labels: { boxWidth: 12, font: { size: 11 } } },
          },
          onClick: (_, elements) => {
            if (elements.length) {
              App.setFilter('language', labels[elements[0].index]);
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
        types[label] = (types[label] || 0) + 1;
      }
    }

    const sorted = Object.entries(types).sort((a, b) => b[1] - a[1]);
    const labels = sorted.map(([t]) => t);
    const data = sorted.map(([, c]) => c);

    this.destroy('types');
    this.instances.types = new Chart(
      document.getElementById('chart-types'),
      {
        type: 'bar',
        data: {
          labels,
          datasets: [{
            data,
            backgroundColor: '#dbeafe',
            borderRadius: 3,
          }],
        },
        options: {
          indexAxis: 'y',
          plugins: { legend: { display: false } },
          scales: {
            x: { beginAtZero: true, ticks: { precision: 0 } },
            y: { grid: { display: false } },
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

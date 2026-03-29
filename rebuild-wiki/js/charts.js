/**
 * charts.js
 * Builds and updates interactive visualisations (timeline & language distribution)
 * Requires Chart.js (v4+) loaded globally as window.Chart.
 */

const ZweigCharts = (function () {
    let _yearChart = null;
    let _languageChart = null;
  
    /* --------- helpers --------- */
    const _aggregateByYear = (entries) => {
      const map = new Map();
      entries.forEach((e) => {
        if (!e.year) return;
        const y = parseInt(e.year, 10);
        if (Number.isNaN(y)) return;
        map.set(y, (map.get(y) || 0) + 1);
      });
      // sort ascending by year
      return Array.from(map.entries()).sort((a, b) => a[0] - b[0]);
    };
  
    const _aggregateByLanguage = (entries) => {
      const map = new Map();
      entries.forEach((e) => {
        if (!e.language) return;
        map.set(e.language, (map.get(e.language) || 0) + 1);
      });
      // sort desc by count
      return Array.from(map.entries()).sort((a, b) => b[1] - a[1]);
    };
  
    /* --------- chart builders --------- */
    const _buildYearChart = (ctx, dataPairs) => {
      const labels = dataPairs.map((d) => d[0]);
      const data = dataPairs.map((d) => d[1]);
  
      return new Chart(ctx, {
        type: "bar",
        data: {
          labels,
          datasets: [
            {
              label: "Works per year",
              data,
            },
          ],
        },
        options: {
          maintainAspectRatio: false,
          onClick: (_evt, elems) => {
            if (!elems.length) return;
            const idx = elems[0].index;
            const year = labels[idx];
            ZweigRouter.navigateToYear(year);
          },
          plugins: {
            legend: { display: false },
            tooltip: { callbacks: { title: (ctx) => `Year ${ctx[0].label}` } },
          },
          scales: {
            x: { title: { display: true, text: "Year" }, ticks: { autoSkip: true } },
            y: { title: { display: true, text: "Count" }, beginAtZero: true },
          },
        },
      });
    };
  
    const _buildLanguageChart = (ctx, dataPairs) => {
      const labels = dataPairs.map((d) => d[0]);
      const data = dataPairs.map((d) => d[1]);
  
      return new Chart(ctx, {
        type: "pie",
        data: {
          labels,
          datasets: [
            {
              label: "Language distribution",
              data,
            },
          ],
        },
        options: {
          maintainAspectRatio: false,
          onClick: (_evt, elems) => {
            if (!elems.length) return;
            const idx = elems[0].index;
            const language = labels[idx];
            ZweigRouter.navigateToLanguage(language);
          },
          plugins: {
            tooltip: {
              callbacks: {
                label: (ctx) => `${ctx.label}: ${ctx.formattedValue} entries`,
              },
            },
          },
        },
      });
    };
  
    /* --------- public API --------- */
    const initialize = () => {
      const yearCanvas = document.getElementById("yearChart");
      const langCanvas = document.getElementById("languageChart");
      if (!yearCanvas || !langCanvas || !window.Chart) {
        console.warn("Charts: canvas or Chart.js missing");
        return;
      }
  
      const entries = ZweigBibliography.isLoaded()
        ? ZweigBibliography.getAllEntries()
        : [];
  
      _yearChart = _buildYearChart(yearCanvas.getContext("2d"), _aggregateByYear(entries));
      _languageChart = _buildLanguageChart(
        langCanvas.getContext("2d"),
        _aggregateByLanguage(entries)
      );
  
      // Update charts after data load & filter changes
      ZweigBibliography.addEventListener("loaded", () => updateAll());
      document.addEventListener("filter-changed", () => updateAll());
    };
  
    const updateAll = () => {
      if (!_yearChart || !_languageChart) return;
      const route = ZweigRouter.getCurrentRoute();
  
      // Build filters object similar to ZweigUI
      const filters = {};
      if (route.filter && route.id) {
        filters[route.filter] = route.filter === "year" ? parseInt(route.id, 10) : route.id;
      }
      if (route.query) {
        // not used here; charts regenerate from filtered entries
      }
  
      const filtered = ZweigBibliography.searchEntries(route.query || "", filters);
  
      // Year chart
      const yearPairs = _aggregateByYear(filtered);
      _yearChart.data.labels = yearPairs.map((d) => d[0]);
      _yearChart.data.datasets[0].data = yearPairs.map((d) => d[1]);
      _yearChart.update();
  
      // Language chart
      const langPairs = _aggregateByLanguage(filtered);
      _languageChart.data.labels = langPairs.map((d) => d[0]);
      _languageChart.data.datasets[0].data = langPairs.map((d) => d[1]);
      _languageChart.update();
    };
  
    return {
      initialize,
      updateAll,
    };
  })();
  
  // Auto‑init when DOM ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => ZweigCharts.initialize());
  } else {
    ZweigCharts.initialize();
  }
  
/* ===========================================================
   Zweig Dashboard – quick smoke‑test
   Put this in the DevTools console or bundle as test.js
   =========================================================== */
(function () {
  const MAX_WAIT = 10_000;                // 10 s bootstrap timeout
  const POLL_MS  =   200;

  // utility
  const ok = (cond, title) =>
    console.log(`${cond ? '✅ PASS' : '❌ FAIL'} – ${title}`);

  const waitForReady = () =>
    new Promise((resolve, reject) => {
      const t0 = Date.now();
      const tick = () => {
        // simple readiness heuristic: data + index + first results rendered
        if (window.S?.rows?.length &&
            window.S?.index &&
            document.querySelector('#results-list li')) {
          return resolve();
        }
        if (Date.now() - t0 > MAX_WAIT) return reject(new Error('timeout'));
        setTimeout(tick, POLL_MS);
      };
      tick();
    });

  waitForReady()
    .then(() => {
      /* ---------- individual assertions ---------- */
      ok(S.rows.length > 0,                'CSV rows loaded');
      ok(typeof S.index.search === 'function', 'FlexSearch index available');

      const catEls = document.querySelectorAll('#category-tree summary, #category-tree button');
      ok(catEls.length > 0,                'Category tree rendered');

      const facetBoxes = FACET_FIELDS.every(f =>
        document.querySelector(`[data-facet="${f}"]`));
      ok(facetBoxes,                        'Facet check‑box lists rendered');

      ok(document.querySelector('#timeline-chart').tagName === 'CANVAS',
         'Timeline <canvas> present');
      ok(document.querySelector('#distribution-chart').tagName === 'CANVAS',
         'Distribution <canvas> present');
      ok(document.querySelector('#network-graph').tagName === 'svg',
         'Network <svg> present');

      // sample search test
      const sampleWord = 'the';
      const hits = S.index.search(sampleWord);
      ok(hits.length > 0,                   `Search returns results for “${sampleWord}”`);

      // click simulation: first result → modal
      const first = document.querySelector('#results-list [data-open]');
      if (first) {
        first.click();
        ok(!document.getElementById('entry-modal').classList.contains('hidden'),
           'Modal opens on result click');
        document.getElementById('close-modal').click();
      } else {
        ok(false, 'No results to test modal');
      }

      console.log('%cSmoke‑tests finished', 'color:green;font-weight:bold;');
    })
    .catch(err => {
      console.error('Test harness failed:', err);
    });
})();

/* csv-worker.js – runs in a Web Worker context to parse large CSV files
 * Messages in:
 *   { id: <string>, csvText: <string>  }
 * Messages out:
 *   { id: <string>, type: 'progress', progress: 0‑100 }
 *   { id: <string>, type: 'done', data: <Array<Object>> }
 *   { id: <string>, type: 'error', message: <string> }
 *
 * Papa Parse is imported via `importScripts`, see index.html bundler config.
 */

importScripts('https://unpkg.com/papaparse@5.4.3/papaparse.min.js');

self.addEventListener('message', (e) => {
  const { id, csvText } = e.data || {};
  if (!csvText) {
    postMessage({ id, type: 'error', message: 'No CSV text provided' });
    return;
  }

  // --- Parse with Papa ---
  Papa.parse(csvText, {
    header: true,
    dynamicTyping: true,
    skipEmptyLines: true,
    worker: false, // already in worker
    step: (row, parser) => {
      const { data } = row;
      // Send occasional progress (every 500 rows)
      if (row && row.meta && row.meta.cursor % 500 === 0) {
        const progress = Math.round((row.meta.cursor / row.meta.fields.length) * 100);
        postMessage({ id, type: 'progress', progress });
      }
    },
    complete: (results) => {
      postMessage({ id, type: 'done', data: results.data });
    },
    error: (err) => {
      postMessage({ id, type: 'error', message: err.message });
    },
  });
});
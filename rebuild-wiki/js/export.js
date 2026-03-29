/**
 * export.js – utilities to export current result set (CSV or BibTeX)
 * ------------------------------------------------------------------
 * Public API:
 *   Exporter.download(entries, 'csv'|'bibtex')
 */

const Exporter = (function () {
    /* ---------------- private helpers ---------------- */
    const _fields = [
      'page_id',
      'title',
      'original_title',
      'year',
      'publisher',
      'location',
      'language',
      'main_category',
      'time_period',
    ];
  
    const _toCsv = (entries) => {
      const header = _fields.join(',');
      const rows = entries.map((e) =>
        _fields
          .map((f) => {
            const val = e[f] !== undefined ? String(e[f]) : '';
            return /[",\n]/.test(val) ? '"' + val.replace(/"/g, '""') + '"' : val;
          })
          .join(',')
      );
      return [header, ...rows].join('\n');
    };
  
    const _toBibTeX = (entries) => {
      return entries
        .map((e) => {
          const id = `zweig${e.page_id}`;
          return `@misc{${id},\n  author    = {Zweig, Stefan},\n  title     = {${e.title}},\n  year      = {${e.year || ''}},\n  language  = {${e.language || ''}},\n  note      = {${e.full_bibliographic_entry || ''}},\n}`;
        })
        .join('\n\n');
    };
  
    const _blobDownload = (content, mime, filename) => {
      const url = URL.createObjectURL(new Blob([content], { type: mime }));
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      requestAnimationFrame(() => {
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      });
    };
  
    /* ---------------- public API ---------------- */
    return {
      download(entries, type = 'csv') {
        if (!Array.isArray(entries) || entries.length === 0) return;
        const ts = new Date().toISOString().replace(/[:.]/g, '-');
        if (type === 'bibtex') {
          const bib = _toBibTeX(entries);
          _blobDownload(bib, 'application/x-bibtex', `zweig-export-${ts}.bib`);
        } else {
          const csv = _toCsv(entries);
          _blobDownload(csv, 'text/csv', `zweig-export-${ts}.csv`);
        }
      },
    };
  })();
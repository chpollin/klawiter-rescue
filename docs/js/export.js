/**
 * Citation export — BibTeX, RIS, JSON-LD, permalink.
 */
const Export = {
  _getEntry(pageId) {
    return App.entryMap.get(pageId);
  },

  bibtex(pageId) {
    const e = this._getEntry(pageId);
    if (!e) return;

    const key = `klawiter${pageId}`;
    const fields = [];
    const isAboutZweig = ABOUT_ZWEIG_TYPES.includes(e.entryType);
    if (!isAboutZweig) {
      fields.push(`  author = {Zweig, Stefan}`);
    }
    if (e.title) fields.push(`  title = {${escapeBibtex(e.title)}}`);
    if (e.year) fields.push(`  year = {${e.year}}`);
    if (e.publisher) fields.push(`  publisher = {${escapeBibtex(e.publisher)}}`);
    if (e.location) fields.push(`  address = {${escapeBibtex(e.location)}}`);
    if (e.pageCount) fields.push(`  pages = {${e.pageCount}}`);
    if (e.language) fields.push(`  language = {${escapeBibtex(e.language)}}`);
    if (e.translator) fields.push(`  note = {Translated by ${escapeBibtex(e.translator)}}`);
    if (isAboutZweig) fields.push(`  keywords = {Stefan Zweig}`);

    const type = (e.entryType === 'essay' || e.entryType === 'newspaper') ? 'article' : 'book';
    const bib = `@${type}{${key},\n${fields.join(',\n')}\n}`;
    downloadBlob(bib, `klawiter-${pageId}.bib`, 'application/x-bibtex');
  },

  ris(pageId) {
    const e = this._getEntry(pageId);
    if (!e) return;

    const isAboutZweig = ABOUT_ZWEIG_TYPES.includes(e.entryType);
    const lines = [];
    const type = (e.entryType === 'essay' || e.entryType === 'newspaper') ? 'JOUR' : 'BOOK';
    lines.push(`TY  - ${type}`);
    if (e.title) lines.push(`TI  - ${e.title}`);
    if (!isAboutZweig) lines.push(`AU  - Zweig, Stefan`);
    if (isAboutZweig) lines.push(`KW  - Stefan Zweig`);
    if (e.year) lines.push(`PY  - ${e.year}`);
    if (e.publisher) lines.push(`PB  - ${e.publisher}`);
    if (e.location) lines.push(`CY  - ${e.location}`);
    if (e.language) lines.push(`LA  - ${e.language}`);
    if (e.translator) lines.push(`A2  - ${e.translator}`);
    if (e.pageCount) lines.push(`N1  - ${e.pageCount} pages`);
    lines.push(`ER  -`);
    downloadBlob(lines.join('\n'), `klawiter-${pageId}.ris`, 'application/x-research-info-systems');
  },

  jsonld(pageId) {
    const e = this._getEntry(pageId);
    if (!e) return;
    const jsonld = {
      '@context': { 'klawiter': 'https://klawiter-rescue.github.io/vocab/' },
      '@type': e['@type'] || `klawiter:${e.entryType}Entry`,
      '@id': e['@id'] || `klawiter:entry/${pageId}`,
    };
    for (const [k, v] of Object.entries(e)) {
      if (!k.startsWith('@') && v != null) {
        jsonld[`klawiter:${k}`] = v;
      }
    }
    downloadBlob(JSON.stringify(jsonld, null, 2), `klawiter-${pageId}.jsonld`, 'application/ld+json');
  },

  permalink(pageId) {
    const url = `${location.origin}${location.pathname}#entry=${pageId}`;
    navigator.clipboard.writeText(url).then(() => {
      const btn = document.querySelector(`[data-permalink="${pageId}"]`);
      if (btn) {
        const orig = btn.innerHTML;
        btn.textContent = '✓ Copied';
        setTimeout(() => { btn.innerHTML = orig; }, 2000);
      }
    });
  },

  batchBibtex(entries) {
    const bibs = entries.map(e => {
      const key = `klawiter${e.sourcePageId}`;
      const fields = [];
      const isAboutZweig = ABOUT_ZWEIG_TYPES.includes(e.entryType);
      if (!isAboutZweig) fields.push(`  author = {Zweig, Stefan}`);
      if (e.title) fields.push(`  title = {${escapeBibtex(e.title)}}`);
      if (e.year) fields.push(`  year = {${e.year}}`);
      if (e.publisher) fields.push(`  publisher = {${escapeBibtex(e.publisher)}}`);
      if (e.location) fields.push(`  address = {${escapeBibtex(e.location)}}`);
      if (e.pageCount) fields.push(`  pages = {${e.pageCount}}`);
      if (e.language) fields.push(`  language = {${escapeBibtex(e.language)}}`);
      if (e.translator) fields.push(`  note = {Translated by ${escapeBibtex(e.translator)}}`);
      if (isAboutZweig) fields.push(`  keywords = {Stefan Zweig}`);
      const type = (e.entryType === 'essay' || e.entryType === 'newspaper') ? 'article' : 'book';
      return `@${type}{${key},\n${fields.join(',\n')}\n}`;
    });
    downloadBlob(bibs.join('\n\n'), 'klawiter-results.bib', 'application/x-bibtex');
  },

  fullDataset() {
    downloadBlob(JSON.stringify(App.data, null, 2), 'klawiter-bibliography.jsonld', 'application/ld+json');
  },
};

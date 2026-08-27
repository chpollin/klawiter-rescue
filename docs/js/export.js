/**
 * Citation export — BibTeX, RIS, JSON-LD, permalink.
 */
const Export = {
  _getEntry(pageId) {
    return App.entryMap.get(pageId);
  },

  _bibtexType(entryType) {
    return (entryType === 'essay' || entryType === 'newspaper') ? 'article' : 'book';
  },

  _bibtexFields(e) {
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
    return fields;
  },

  _toBibtex(e) {
    const key = `klawiter${e.sourcePageId}`;
    const type = this._bibtexType(e.entryType);
    const fields = this._bibtexFields(e);
    return `@${type}{${key},\n${fields.join(',\n')}\n}`;
  },

  bibtex(pageId) {
    const e = this._getEntry(pageId);
    if (!e) return;
    downloadBlob(this._toBibtex(e), `klawiter-${pageId}.bib`, 'application/x-bibtex');
  },

  ris(pageId) {
    const e = this._getEntry(pageId);
    if (!e) return;

    const isAboutZweig = ABOUT_ZWEIG_TYPES.includes(e.entryType);
    const type = (e.entryType === 'essay' || e.entryType === 'newspaper') ? 'JOUR' : 'BOOK';
    const lines = [`TY  - ${type}`];
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
    const jsonld = this._jsonldPayload(e);
    downloadBlob(JSON.stringify(jsonld, null, 2), `klawiter-${pageId}.jsonld`, 'application/ld+json');
  },

  _jsonldPayload(entry) {
    const compact = JsonldPlayground._toCompactJsonld(entry);
    const claims = Edit.editionClaimsFor(entry);
    if (!claims.length) return compact;
    const context = { ...compact['@context'], oa: 'http://www.w3.org/ns/oa#', prov: 'http://www.w3.org/ns/prov#' };
    const entryNode = { ...compact };
    delete entryNode['@context'];
    const claimNodes = claims.map(claim => ({
      '@id': claim.claimId,
      '@type': 'klawiter:ContestedClaim',
      'klawiter:claimStatus': claim.claimStatus,
      'klawiter:decisionStatus': claim.decisionStatus,
      'klawiter:claimSubject': { '@id': claim.subject },
      'klawiter:claimPredicate': { '@id': claim.predicate },
      'oa:hasTarget': {
        '@type': 'oa:SpecificResource',
        'oa:hasSource': { '@id': `klawiter:sourceText/${claim.source.sourcePageId}` },
        'oa:hasSelector': {
          '@type': 'oa:TextPositionSelector',
          'oa:start': claim.source.selector[0],
          'oa:end': claim.source.selector[1],
        },
      },
      'klawiter:sourceSliceSha256': claim.source.sliceSha256,
      'klawiter:interpretation': claim.interpretations.map(item => ({
        '@id': item.interpretationId,
        '@type': 'klawiter:ClaimInterpretation',
        'schema:name': item.label,
        'schema:description': item.basis,
        'klawiter:proposedObject': { '@id': item.proposedObject },
        'klawiter:interpretationStatus': item.status,
      })),
      'klawiter:reviewAction': claim.reviewHistory.map(item => ({
        '@id': item.reviewId,
        '@type': 'klawiter:ReviewAction',
        'prov:wasAssociatedWith': { '@id': item.reviewer },
        'klawiter:reviewOutcome': item.outcome,
        ...(item.basis ? { 'klawiter:reviewBasis': item.basis } : {}),
      })),
    }));
    return { '@context': context, '@graph': [entryNode, ...claimNodes] };
  },

  permalink(pageId) {
    const url = `${location.origin}${location.pathname}#entry=${pageId}`;
    navigator.clipboard.writeText(url).then(() => {
      const btn = document.querySelector(`[data-permalink="${pageId}"]`);
      if (btn) {
        const orig = btn.innerHTML;
        btn.textContent = '\u2713 Copied';
        setTimeout(() => { btn.innerHTML = orig; }, 2000);
      }
    });
  },

  batchBibtex(entries) {
    const bibs = entries.map(e => this._toBibtex(e));
    downloadBlob(bibs.join('\n\n'), 'klawiter-results.bib', 'application/x-bibtex');
  },

  // The flat frontend projection, not the JSON-LD serialization: its keys are
  // the frontend names and it carries no @context. Attaching one would claim a
  // mapping that does not hold, so the export is named for what it is; the
  // canonical JSON-LD lives in the repository under data/output/.
  fullDataset() {
    const payload = {
      ...App.data,
      contestedEditionClaims: Object.values(Edit.editionClaims).flat(),
      contestedAuthorityClaims: Edit.contestedAuthorityClaims,
    };
    downloadBlob(JSON.stringify(payload, null, 2), 'klawiter-bibliography.json', 'application/json');
  },
};

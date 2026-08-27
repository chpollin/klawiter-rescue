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

  /**
   * Base URL a citation should point at. A localhost or file:// run must not
   * hand out a link that resolves nowhere for the reader of the citation.
   */
  _siteBase() {
    const l = typeof location !== 'undefined' ? location : null;
    if (l && /^https?:$/.test(l.protocol)
        && !/^(localhost|127\.0\.0\.1)$/.test(l.hostname)) {
      return `${l.origin}${l.pathname}`;
    }
    return SITE_URL;
  },

  permalinkUrl(pageId) {
    return `${this._siteBase()}#entry=${pageId}`;
  },

  _bibtexFields(e) {
    const fields = [];
    const isAboutZweig = ABOUT_ZWEIG_TYPES.includes(e.entryType);
    if (!isAboutZweig) fields.push(`  author = {Zweig, Stefan}`);
    if (e.title) fields.push(`  title = {${escapeBibtex(e.title)}}`);
    if (e.year) fields.push(`  year = {${e.year}}`);
    if (e.publisher) fields.push(`  publisher = {${escapeBibtex(e.publisher)}}`);
    if (e.location) fields.push(`  address = {${escapeBibtex(e.location)}}`);
    // pagetotal, not pages: the recorded value is the extent of the volume,
    // while `pages` is the page range an item occupies inside a container.
    if (e.pageCount) fields.push(`  pagetotal = {${e.pageCount}}`);
    if (e.language) fields.push(`  language = {${escapeBibtex(e.language)}}`);
    if (e.translator) fields.push(`  note = {Translated by ${escapeBibtex(e.translator)}}`);
    if (isAboutZweig) fields.push(`  keywords = {Stefan Zweig}`);
    fields.push(`  url = {${this.permalinkUrl(e.sourcePageId)}}`);
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
    // One rule for what counts as an article, read by both formats.
    const type = this._bibtexType(e.entryType) === 'article' ? 'JOUR' : 'BOOK';
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
    lines.push(`UR  - ${this.permalinkUrl(pageId)}`);
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
    const url = this.permalinkUrl(pageId);
    const btn = document.querySelector(`[data-permalink="${pageId}"]`);
    const clipboard = typeof navigator !== 'undefined' ? navigator.clipboard : null;
    // Clipboard access is denied in an insecure context and by permission
    // policy; without the rejection path the button simply did nothing.
    if (clipboard && clipboard.writeText) {
      clipboard.writeText(url).then(
        () => this._copyFeedback(btn),
        () => this._copyFallback(btn, url)
      );
    } else {
      this._copyFallback(btn, url);
    }
  },

  /**
   * Confirm the copy for two seconds. The original label is remembered once,
   * so a second click inside the window resets the timer instead of freezing
   * the button on "Copied" by remembering that as its original.
   */
  _copyFeedback(btn) {
    if (!btn) return;
    if (btn._copyTimer) clearTimeout(btn._copyTimer);
    else btn._copyOriginal = btn.innerHTML;
    btn.textContent = '\u2713 Copied';
    btn._copyTimer = setTimeout(() => {
      btn.innerHTML = btn._copyOriginal;
      btn._copyTimer = null;
    }, 2000);
  },

  /** No clipboard: offer the URL in a selectable field next to the button. */
  _copyFallback(btn, url) {
    if (!btn || !btn.parentNode) return;
    let field = btn.parentNode.querySelector('.permalink-fallback');
    if (!field) {
      field = document.createElement('input');
      field.type = 'text';
      field.readOnly = true;
      field.className = 'permalink-fallback';
      field.setAttribute('aria-label', 'Permalink, select and copy');
      btn.parentNode.insertBefore(field, btn.nextSibling);
    }
    field.value = url;
    field.focus();
    field.select();
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

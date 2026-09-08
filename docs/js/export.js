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

  /**
   * The author a citation names.
   *
   * An author page carries the name of an author as its title, and every
   * publication listed on it is that author's, so the title is the author in
   * the form the page gives it. Otherwise the entry type decides: the Overview
   * groups the types into Works, Editions, Reception & Impact and Other, and
   * the first two are what Zweig wrote (translations by him included, where
   * the translator credit stays a translator credit). What is about him
   * carries no author and names him as a keyword instead. ABOUT_ZWEIG_TYPES is
   * derived from that grouping rather than kept as a second list.
   */
  _author(entry) {
    if (entry.pageKind === 'author-page') return entry.title || '';
    return ABOUT_ZWEIG_TYPES.includes(entry.entryType) ? '' : 'Zweig, Stefan';
  },

  /**
   * The place assignment of this entry is an open authority claim, so a
   * citation printing the place says so instead of passing it off as settled.
   * Read from the same reconciliation claims the card shows.
   */
  _contestedPlaceNote(entry) {
    const claims = (Edit.authorityClaimsFor(entry) || [])
      .filter(claim => claim.entityType === 'location');
    return claims.length ? 'Place authority assignment contested' : '';
  },

  _bibtexFields(e) {
    const fields = [];
    const isAboutZweig = ABOUT_ZWEIG_TYPES.includes(e.entryType);
    const author = this._author(e);
    if (author) fields.push(`  author = {${escapeBibtex(author)}}`);
    if (e.title) fields.push(`  title = {${escapeBibtex(e.title)}}`);
    if (e.year) fields.push(`  year = {${e.year}}`);
    if (e.publisher) fields.push(`  publisher = {${escapeBibtex(e.publisher)}}`);
    if (e.location) fields.push(`  address = {${escapeBibtex(e.location)}}`);
    // pagetotal, not pages: the recorded value is the extent of the volume,
    // while `pages` is the page range an item occupies inside a container.
    if (e.pageCount) fields.push(`  pagetotal = {${e.pageCount}}`);
    if (e.language) fields.push(`  language = {${escapeBibtex(e.language)}}`);
    const note = [];
    if (e.translator) note.push(`Translated by ${e.translator}`);
    const contested = this._contestedPlaceNote(e);
    if (contested) note.push(contested);
    if (note.length) fields.push(`  note = {${escapeBibtex(note.join('; '))}}`);
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

  // --- Publication-scoped citations ------------------------------------------
  // A source page can document several publications, and the flat fields
  // answer with one value per field across all of them. Where the publication
  // layer is loaded it is what a citation describes; the flat fields answer
  // only while it is not.

  /** The publications of a page, or null while the layer is not loaded. */
  _publications(entry) {
    const state = Detail._publicationState(entry);
    return state.status === 'ready' && state.publications.length ? state.publications : null;
  },

  /** Stable name of one publication, from its identifier. */
  _publicationSlug(entry, pub, index) {
    const id = pub && pub.id ? String(pub.id) : '';
    const tail = id.slice(id.lastIndexOf('/') + 1);
    return tail || `${entry.sourcePageId}-${index + 1}`;
  },

  _creditNames(pub, role) {
    return (pub.credits || [])
      .filter(credit => credit.role === role && credit.name)
      .map(credit => credit.name)
      .join(' and ');
  },

  /**
   * The credit statements in the wording of the source, and an online address
   * with the qualification the source gives it. The role fields generalize
   * that wording away, so it stays where a reader can read it.
   */
  _citationNote(pub) {
    const parts = (pub.credits || [])
      .filter(credit => credit.name)
      .map(credit => `${credit.creditLabel || credit.role} ${credit.name}`);
    if (pub.online && pub.online.url) {
      parts.push(`Online: ${pub.online.url}${pub.online.note ? ` (${pub.online.note})` : ''}`);
    }
    return parts.join('; ');
  },

  _publicationExtent(pub) {
    if (!pub.extent) return '';
    return String(pub.extent.raw || pub.extent.numbered || '');
  },

  /** `pagetotal` is a number of pages, so the notation of the source is not it. */
  _publicationPages(pub) {
    const numbered = pub.extent && pub.extent.numbered;
    return Number.isFinite(numbered) ? String(numbered) : '';
  },

  _toBibtexPublication(entry, pub, index) {
    const isAboutZweig = ABOUT_ZWEIG_TYPES.includes(entry.entryType);
    const type = pub.container ? 'article' : this._bibtexType(entry.entryType);
    const fields = [];
    const author = this._author(entry);
    if (author) fields.push(`  author = {${escapeBibtex(author)}}`);
    const title = pub.title || entry.title;
    if (title) fields.push(`  title = {${escapeBibtex(title)}}`);
    if (pub.year) fields.push(`  year = {${pub.year}}`);
    if (pub.editionStatement) fields.push(`  edition = {${escapeBibtex(pub.editionStatement)}}`);
    if (pub.publisher) fields.push(`  publisher = {${escapeBibtex(pub.publisher)}}`);
    // Every place of the publication in the wording of the source, joined the
    // way the imprint has them; naming one of them alone would settle a place
    // assignment the source leaves open.
    const address = pub.places && pub.places.length
      ? pub.places.join(', ')
      : (pub.container && pub.container.place) || '';
    if (address) fields.push(`  address = {${escapeBibtex(address)}}`);
    if (pub.container) {
      if (pub.container.title) {
        fields.push(`  journaltitle = {${escapeBibtex(pub.container.title)}}`);
      }
      if (pub.container.issue) fields.push(`  number = {${escapeBibtex(pub.container.issue)}}`);
      if (pub.container.pages) fields.push(`  pages = {${escapeBibtex(pub.container.pages)}}`);
    }
    // pagetotal, not pages: the numbered extent of the volume, while `pages`
    // is the range an item occupies inside a container.
    const pages = this._publicationPages(pub);
    if (pages) fields.push(`  pagetotal = {${pages}}`);
    if (pub.language) fields.push(`  language = {${escapeBibtex(pub.language)}}`);
    if (pub.series) fields.push(`  series = {${escapeBibtex(pub.series)}}`);
    if (pub.seriesVolume && !pub.container) {
      fields.push(`  volume = {${escapeBibtex(pub.seriesVolume)}}`);
    }
    const translators = this._creditNames(pub, 'translator');
    if (translators) fields.push(`  translator = {${escapeBibtex(translators)}}`);
    const editors = this._creditNames(pub, 'editor');
    if (editors) fields.push(`  editor = {${escapeBibtex(editors)}}`);
    const note = [this._citationNote(pub), this._contestedPlaceNote(entry)].filter(Boolean);
    // The notation of the source is prose beside a page count, so it belongs
    // in the note; a citation that carries no note is not given one for it.
    const extent = this._publicationExtent(pub);
    if (note.length && extent && extent !== pages) note.push(`Extent: ${extent}`);
    if (note.length) fields.push(`  note = {${escapeBibtex(note.join('; '))}}`);
    if (isAboutZweig) fields.push(`  keywords = {Stefan Zweig}`);
    fields.push(`  url = {${this.permalinkUrl(entry.sourcePageId)}}`);
    const key = `klawiter${this._publicationSlug(entry, pub, index)}`;
    return `@${type}{${key},\n${fields.join(',\n')}\n}`;
  },

  _toRis(e) {
    const isAboutZweig = ABOUT_ZWEIG_TYPES.includes(e.entryType);
    // One rule for what counts as an article, read by both formats.
    const type = this._bibtexType(e.entryType) === 'article' ? 'JOUR' : 'BOOK';
    const lines = [`TY  - ${type}`];
    if (e.title) lines.push(`TI  - ${e.title}`);
    const author = this._author(e);
    if (author) lines.push(`AU  - ${author}`);
    if (isAboutZweig) lines.push(`KW  - Stefan Zweig`);
    if (e.year) lines.push(`PY  - ${e.year}`);
    if (e.publisher) lines.push(`PB  - ${e.publisher}`);
    if (e.location) lines.push(`CY  - ${e.location}`);
    if (e.language) lines.push(`LA  - ${e.language}`);
    if (e.translator) lines.push(`A2  - ${e.translator}`);
    if (e.pageCount) lines.push(`N1  - ${e.pageCount} pages`);
    const contested = this._contestedPlaceNote(e);
    if (contested) lines.push(`N1  - ${contested}`);
    lines.push(`UR  - ${this.permalinkUrl(e.sourcePageId)}`);
    lines.push(`ER  -`);
    return lines.join('\n');
  },

  // A2 carries the translators and A3 the editors, keeping the reading the
  // flat export already used for the scalar translator field.
  _toRisPublication(entry, pub) {
    const isAboutZweig = ABOUT_ZWEIG_TYPES.includes(entry.entryType);
    const type = pub.container || this._bibtexType(entry.entryType) === 'article'
      ? 'JOUR'
      : 'BOOK';
    const lines = [`TY  - ${type}`];
    const title = pub.title || entry.title;
    if (title) lines.push(`TI  - ${title}`);
    const author = this._author(entry);
    if (author) lines.push(`AU  - ${author}`);
    if (isAboutZweig) lines.push(`KW  - Stefan Zweig`);
    if (pub.year) lines.push(`PY  - ${pub.year}`);
    if (pub.editionStatement) lines.push(`ET  - ${pub.editionStatement}`);
    if (pub.publisher) lines.push(`PB  - ${pub.publisher}`);
    for (const place of pub.places || []) lines.push(`CY  - ${place}`);
    if (pub.container) {
      if (pub.container.title) lines.push(`T2  - ${pub.container.title}`);
      if (pub.container.place && !(pub.places || []).length) {
        lines.push(`CY  - ${pub.container.place}`);
      }
      if (pub.container.issue) lines.push(`IS  - ${pub.container.issue}`);
      const pages = pub.container.pages || '';
      const range = /^\s*\(?(\d+)\)?\s*[-\u2013]\s*\(?(\d+)\)?\s*$/.exec(pages);
      if (range) {
        lines.push(`SP  - ${range[1]}`);
        lines.push(`EP  - ${range[2]}`);
      } else if (pages) {
        lines.push(`SP  - ${pages}`);
      }
    }
    if (pub.language) lines.push(`LA  - ${pub.language}`);
    for (const credit of pub.credits || []) {
      if (credit.role === 'translator') lines.push(`A2  - ${credit.name}`);
      else if (credit.role === 'editor') lines.push(`A3  - ${credit.name}`);
    }
    const extent = this._publicationExtent(pub);
    if (extent) lines.push(`N1  - Extent: ${extent}`);
    if (pub.series) {
      lines.push(`N1  - Series: ${pub.series}${pub.seriesVolume ? `, ${pub.seriesVolume}` : ''}`);
    }
    const note = this._citationNote(pub);
    if (note) lines.push(`N1  - ${note}`);
    const contested = this._contestedPlaceNote(entry);
    if (contested) lines.push(`N1  - ${contested}`);
    lines.push(`UR  - ${this.permalinkUrl(entry.sourcePageId)}`);
    lines.push(`ER  -`);
    return lines.join('\n');
  },

  /**
   * Cite one publication, every publication of the page, or the flat record.
   *
   * An index names the publication the reader chose. Without one the export
   * collects every publication of the page, and it falls back to the flat
   * fields while the publication layer is not loaded.
   */
  _citation(pageId, index, format) {
    const entry = this._getEntry(pageId);
    if (!entry) return null;
    const one = format === 'bib'
      ? (pub, i) => this._toBibtexPublication(entry, pub, i)
      : (pub) => this._toRisPublication(entry, pub);
    const pubs = this._publications(entry);
    if (pubs && index != null && pubs[index]) {
      return {
        content: one(pubs[index], index),
        name: `klawiter-${this._publicationSlug(entry, pubs[index], index)}`,
      };
    }
    if (pubs) {
      return { content: pubs.map(one).join('\n\n'), name: `klawiter-${pageId}` };
    }
    return {
      content: format === 'bib' ? this._toBibtex(entry) : this._toRis(entry),
      name: `klawiter-${pageId}`,
    };
  },

  bibtex(pageId, index) {
    const cite = this._citation(pageId, index, 'bib');
    if (cite) downloadBlob(cite.content, `${cite.name}.bib`, 'application/x-bibtex');
  },

  ris(pageId, index) {
    const cite = this._citation(pageId, index, 'ris');
    if (cite) {
      downloadBlob(cite.content, `${cite.name}.ris`, 'application/x-research-info-systems');
    }
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
      'klawiter:hasReviewAction': claim.reviewHistory.map(item => ({
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

  /** Pages loaded at once; a page file is small, the exported set is not. */
  BATCH_CONCURRENCY: 8,

  /**
   * Load the publication layer of every exported page that has one. Without it
   * the batch cited the flat record, which on a multi-publication page emits
   * one citation for the first edition and drops the rest.
   */
  _loadBatch(entries, onProgress) {
    const load = (entry) => {
      const state = Detail._publicationState(entry);
      // A load already in flight is awaited rather than started a second time.
      return state.status === 'loading' && state.promise
        ? state.promise
        : Detail.loadPublications(entry);
    };
    const pending = entries.filter(entry =>
      ['idle', 'loading'].includes(Detail._publicationState(entry).status));
    let done = entries.length - pending.length;
    const report = () => onProgress && onProgress({ loaded: done, total: entries.length });
    report();
    let next = 0;
    const lane = () => {
      if (next >= pending.length) return Promise.resolve();
      const entry = pending[next++];
      return Promise.resolve(load(entry)).then(() => {
        done++;
        report();
        return lane();
      });
    };
    return Promise.all(
      Array.from({ length: Math.min(this.BATCH_CONCURRENCY, pending.length) }, lane));
  },

  /**
   * One citation per publication, and the flat citation for a page whose
   * publication file does not exist or did not load. `onState` reports the
   * loading and then the number of citations, which differs from the number of
   * exported pages.
   */
  batchBibtex(entries, onState) {
    return this._loadBatch(entries, state => onState && onState(state)).then(() => {
      const cites = [];
      for (const entry of entries) {
        const pubs = this._publications(entry);
        if (pubs) pubs.forEach((pub, i) => cites.push(this._toBibtexPublication(entry, pub, i)));
        else cites.push(this._toBibtex(entry));
      }
      downloadBlob(cites.join('\n\n'), 'klawiter-results.bib', 'application/x-bibtex');
      if (onState) onState({ done: true, citations: cites.length });
      return cites.length;
    });
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

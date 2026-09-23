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

  /**
   * The address of an entry, or of one publication on it. Two editions on one
   * page are two citable things, so each carries the page and its own name
   * (#entry=1800&pub=1800-1960-a), which the route opens at that block.
   */
  permalinkUrl(pageId, publication) {
    const pub = publication ? `&pub=${encodeURIComponent(publication)}` : '';
    return `${this._siteBase()}#entry=${pageId}${pub}`;
  },

  /**
   * The author a citation names follows the role the source gives each party.
   *
   * Zweig is the author only of pages holding his own texts (ZWEIG_AUTHOR_TYPES).
   * An author page, a translation page and a foreword page are indexed under
   * the author of what they list, so the page title names the author there and
   * Zweig keeps his translator or contributor credit. Pages about Zweig carry
   * no author and name him as a keyword. Revisable setting, decided by the
   * main instance after delegation by the operator on 2026-09-22.
   */
  _author(entry) {
    if (entry.pageKind === 'author-page' || TITLE_AUTHOR_TYPES.includes(entry.entryType)) {
      return this._titleAuthor(entry.title);
    }
    return ZWEIG_AUTHOR_TYPES.includes(entry.entryType) ? 'Zweig, Stefan' : '';
  },

  /**
   * An inverted personal name, "Surname, Forename", is the only form in which
   * the page titles name a person. A title of any other shape in that position
   * (a list marker such as "[1]", a heading such as "Essays:", a book or an
   * article title) names nobody, and a citation without an author misleads
   * less than one with a title in the author field. Titles naming several
   * people ("Mann, Erika and Klaus", semicolon lists) are refused as well,
   * because their shorthand does not split into separate names reliably. What
   * follows " / " qualifies the page (a language, "Forewords", a second
   * spelling) and is not part of the name.
   */
  _NAME_FORM_RE: /^[\p{L}'’][\p{L}\p{M}'’.\-() ]*,\s[\p{L}'’][\p{L}\p{M}'’.\-() ]*$/u,

  _titleAuthor(title) {
    const head = String(title || '').split(' / ')[0].trim();
    if (!this._NAME_FORM_RE.test(head) || /\sand\s/.test(head)) return '';
    const [surname, forenames] = head.split(', ');
    const words = part => part.trim().split(/\s+/).length;
    return words(surname) <= 4 && words(forenames) <= 4 ? head : '';
  },

  /**
   * A publication whose source names its own author ("A graphic novel by") is
   * cited under that author, whatever the page it is listed on. This is the
   * per-publication exception to the page rule; the graphic-novel adaptation
   * on page 4916 is the case it was made for.
   */
  _publicationAuthor(entry, pub) {
    return this._creditNames(pub, 'author') || this._author(entry);
  },

  /**
   * Where a translation or foreword page is cited and no credit names Zweig,
   * his part would vanish from the citation now that he is not its author.
   * The compiler's classification of the page is the evidence for it, so the
   * note states what the page's section says, not a role in a particular
   * volume.
   */
  _zweigContributionNote(entry, names) {
    if (!TITLE_AUTHOR_TYPES.includes(entry.entryType)) return '';
    if (names.some(name => /\bZweig\b/.test(name || ''))) return '';
    return entry.entryType === 'translation'
      ? 'Contains a translation by Stefan Zweig'
      : 'Contains a foreword or afterword by Stefan Zweig';
  },

  /**
   * A place the citation prints is under an open authority claim, so the
   * citation says so instead of passing the place off as settled. Read from
   * the same claims the card shows, and only for a place of the cited
   * publication itself: a claim on another edition of the page is not a
   * statement about this one.
   */
  _contestedPlaceNote(entry, places) {
    const claims = (Edit.authorityClaimsFor(entry) || []).filter(claim =>
      claim.entityType === 'location' && claim.decisionStatus !== 'decided'
      && claim.subject && places.includes(claim.subject.name));
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
    const zweig = this._zweigContributionNote(e, [e.translator]);
    if (zweig) note.push(zweig);
    const contested = this._contestedPlaceNote(e, e.location ? [e.location] : []);
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
    return Detail.publicationSlug(entry, pub, index);
  },

  /** Every credit of a publication, its own and those of its contributions. */
  _allCredits(pub) {
    return (pub.credits || []).concat(
      ...(pub.contributions || []).map(item => item.credits || []));
  },

  /**
   * The names credited in one role, each once. A source can credit one person
   * twice in a role ("Translated with an afterword by" and "Translated with a
   * foreword by" on page 792); the wording of both stays in the note. With
   * `withContributions` the credits of the contained texts count as well:
   * page 1891 credits its three translators under its two contributions and
   * none under the volume.
   */
  _creditList(pub, role, withContributions) {
    const credits = withContributions ? this._allCredits(pub) : (pub.credits || []);
    return [...new Set(credits
      .filter(credit => credit.role === role && credit.name)
      .map(credit => credit.name))];
  },

  _creditNames(pub, role, withContributions) {
    return this._creditList(pub, role, withContributions).join(' and ');
  },

  /**
   * The credit statements in the wording of the source, those of each
   * contribution under its title, an online address with the qualification
   * the source gives it, and the note of the publication. The role fields
   * generalize that wording away, so it stays where a reader can read it.
   */
  _citationNote(pub) {
    const wording = credits => credits
      .filter(credit => credit.name)
      .map(credit => `${credit.creditLabel || credit.role} ${credit.name}`);
    const parts = [];
    // The publisher and place fields cannot say which publisher of a joint
    // imprint worked where, so the pairs of the source stand in the note.
    const imprints = this._imprints(pub);
    if (imprints) parts.push(`Imprint: ${this._imprintWording(imprints)}`);
    // The gloss is the compiler's rendering of the series title, which the
    // series field carries in the original wording alone.
    if (pub.series && pub.seriesGloss) parts.push(`Series: ${pub.series} (${pub.seriesGloss})`);
    parts.push(...wording(pub.credits || []));
    for (const item of pub.contributions || []) {
      const credits = wording(item.credits || []);
      if (credits.length) parts.push(`${item.title ? `${item.title}: ` : ''}${credits.join(', ')}`);
    }
    if (pub.online && pub.online.url) {
      parts.push(`Online: ${pub.online.url}${pub.online.note ? ` (${pub.online.note})` : ''}`);
    }
    if (pub.note) parts.push(pub.note);
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

  /** The publisher-place pairs of a joint imprint, or null for a single one. */
  _imprints(pub) {
    return Array.isArray(pub.imprints) && pub.imprints.length > 1 ? pub.imprints : null;
  },

  _imprintWording(imprints) {
    return imprints.map(pair => [pair.publisher, pair.place].filter(Boolean).join(', ')).join(' / ');
  },

  /** The places a citation prints: the imprint's, else the container's. */
  _publicationPlaces(pub) {
    if (pub.places && pub.places.length) return pub.places;
    return pub.container && pub.container.place ? [pub.container.place] : [];
  },

  /**
   * The number within the series, where the series wording does not already
   * end with it ("Hochschulsammlung Philosophie. Literaturwissenschaft, 16"
   * carries its 16); the card holds the same guard.
   */
  _seriesNumber(pub) {
    if (!pub.series || !pub.seriesVolume) return '';
    const volume = String(pub.seriesVolume).trim();
    return String(pub.series).trim().endsWith(volume) ? '' : volume;
  },

  _toBibtexPublication(entry, pub, index) {
    const isAboutZweig = ABOUT_ZWEIG_TYPES.includes(entry.entryType);
    const type = pub.container ? 'article' : this._bibtexType(entry.entryType);
    const fields = [];
    const author = this._publicationAuthor(entry, pub);
    if (author) fields.push(`  author = {${escapeBibtex(author)}}`);
    const title = pub.title || entry.title;
    if (title) fields.push(`  title = {${escapeBibtex(title)}}`);
    if (pub.year) fields.push(`  year = {${pub.year}}`);
    if (pub.editionStatement) fields.push(`  edition = {${escapeBibtex(pub.editionStatement)}}`);
    const places = this._publicationPlaces(pub);
    const imprints = this._imprints(pub);
    if (imprints) {
      // A joint imprint: biblatex name lists in the order of the source, so
      // the n-th publisher and the n-th place belong together; each item is
      // braced so a comma or "and" inside a name stays part of it.
      const list = values => values.filter(Boolean).map(value => `{${escapeBibtex(value)}}`).join(' and ');
      fields.push(`  publisher = {${list(imprints.map(pair => pair.publisher))}}`);
      fields.push(`  address = {${list(imprints.map(pair => pair.place))}}`);
    } else {
      if (pub.publisher) fields.push(`  publisher = {${escapeBibtex(pub.publisher)}}`);
      // Every place of the publication in the wording of the source, joined
      // the way the imprint has them; naming one of them alone would settle a
      // place assignment the source leaves open.
      if (places.length) fields.push(`  address = {${escapeBibtex(places.join(', '))}}`);
    }
    if (pub.container) {
      // biblatex reads journaltitle, classic BibTeX styles read journal.
      if (pub.container.title) {
        fields.push(`  journaltitle = {${escapeBibtex(pub.container.title)}}`);
        fields.push(`  journal = {${escapeBibtex(pub.container.title)}}`);
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
    // The number within a series is `number`; `volume` is a volume of a
    // multi-volume work. An article's `number` is its issue already.
    const seriesNumber = this._seriesNumber(pub);
    if (seriesNumber && !pub.container) {
      fields.push(`  number = {${escapeBibtex(seriesNumber)}}`);
    }
    const translators = this._creditNames(pub, 'translator', true);
    if (translators) fields.push(`  translator = {${escapeBibtex(translators)}}`);
    const editors = this._creditNames(pub, 'editor');
    if (editors) fields.push(`  editor = {${escapeBibtex(editors)}}`);
    const illustrators = this._creditNames(pub, 'illustrator');
    if (illustrators) fields.push(`  illustrator = {${escapeBibtex(illustrators)}}`);
    const note = [
      this._citationNote(pub),
      this._zweigContributionNote(entry, this._allCredits(pub).map(credit => credit.name)),
      this._contestedPlaceNote(entry, places),
    ].filter(Boolean);
    // The notation of the source is prose beside a page count, so it belongs
    // in the note; a citation that carries no note is not given one for it.
    const extent = this._publicationExtent(pub);
    if (note.length && extent && extent !== pages) note.push(`Extent: ${extent}`);
    if (note.length) fields.push(`  note = {${escapeBibtex(note.join('; '))}}`);
    if (isAboutZweig) fields.push(`  keywords = {Stefan Zweig}`);
    const slug = this._publicationSlug(entry, pub, index);
    fields.push(`  url = {${this.permalinkUrl(entry.sourcePageId, slug)}}`);
    return `@${type}{klawiter${slug},\n${fields.join(',\n')}\n}`;
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
    if (e.translator) lines.push(`${this.RIS_ROLES.translator}  - ${e.translator}`);
    if (e.pageCount) lines.push(`N1  - ${e.pageCount} pages`);
    const zweig = this._zweigContributionNote(e, [e.translator]);
    if (zweig) lines.push(`N1  - ${zweig}`);
    const contested = this._contestedPlaceNote(e, e.location ? [e.location] : []);
    if (contested) lines.push(`N1  - ${contested}`);
    lines.push(`UR  - ${this.permalinkUrl(e.sourcePageId)}`);
    lines.push(`ER  -`);
    return lines.join('\n');
  },

  /**
   * RIS creator tags by role and reference type. A4 is the subsidiary author,
   * which the RIS specification and Zotero's RIS translator
   * (zotero/translators, RIS.js) both read as the translator. The editor
   * depends on the type there: A2 on a journal article, A3 on a book, whose
   * A2 Zotero reads as the series editor. The role vocabulary of the records
   * holds no series editor, so nothing is written to that tag.
   */
  RIS_ROLES: { translator: 'A4' },
  RIS_EDITOR: { BOOK: 'A3', JOUR: 'A2' },

  _toRisPublication(entry, pub, index) {
    const isAboutZweig = ABOUT_ZWEIG_TYPES.includes(entry.entryType);
    const type = pub.container || this._bibtexType(entry.entryType) === 'article'
      ? 'JOUR'
      : 'BOOK';
    const lines = [`TY  - ${type}`];
    const title = pub.title || entry.title;
    if (title) lines.push(`TI  - ${title}`);
    for (const author of this._publicationAuthor(entry, pub).split(' and ').filter(Boolean)) {
      lines.push(`AU  - ${author}`);
    }
    if (isAboutZweig) lines.push(`KW  - Stefan Zweig`);
    if (pub.year) lines.push(`PY  - ${pub.year}`);
    if (pub.editionStatement) lines.push(`ET  - ${pub.editionStatement}`);
    const imprints = this._imprints(pub);
    if (imprints) {
      lines.push(`PB  - ${imprints.map(pair => pair.publisher).filter(Boolean).join(' / ')}`);
    } else if (pub.publisher) {
      lines.push(`PB  - ${pub.publisher}`);
    }
    const places = this._publicationPlaces(pub);
    for (const place of imprints ? imprints.map(pair => pair.place).filter(Boolean) : places) {
      lines.push(`CY  - ${place}`);
    }
    if (pub.container) {
      if (pub.container.title) lines.push(`T2  - ${pub.container.title}`);
      if (pub.container.issue) lines.push(`IS  - ${pub.container.issue}`);
      const pages = pub.container.pages || '';
      const range = /^\s*\(?(\d+)\)?\s*[-–]\s*\(?(\d+)\)?\s*$/.exec(pages);
      if (range) {
        lines.push(`SP  - ${range[1]}`);
        lines.push(`EP  - ${range[2]}`);
      } else if (pages) {
        lines.push(`SP  - ${pages}`);
      }
    } else {
      // On a book SP is the number of pages (Zotero: numPages).
      const pages = this._publicationPages(pub);
      if (pages) lines.push(`SP  - ${pages}`);
    }
    if (pub.language) lines.push(`LA  - ${pub.language}`);
    for (const name of this._creditList(pub, 'translator', true)) {
      lines.push(`${this.RIS_ROLES.translator}  - ${name}`);
    }
    for (const name of this._creditList(pub, 'editor')) {
      lines.push(`${this.RIS_EDITOR[type]}  - ${name}`);
    }
    // The series of a book is T2 with its number in M1; T2 of an article is
    // its journal, so there the series is T3 and its number stays in the note.
    const seriesNumber = this._seriesNumber(pub);
    if (pub.series) lines.push(`${type === 'BOOK' ? 'T2' : 'T3'}  - ${pub.series}`);
    if (seriesNumber && type === 'BOOK') lines.push(`M1  - ${seriesNumber}`);
    else if (seriesNumber) lines.push(`N1  - Series number: ${seriesNumber}`);
    const extent = this._publicationExtent(pub);
    if (extent) lines.push(`N1  - Extent: ${extent}`);
    const note = this._citationNote(pub);
    if (note) lines.push(`N1  - ${note}`);
    const zweig = this._zweigContributionNote(entry, this._allCredits(pub).map(credit => credit.name));
    if (zweig) lines.push(`N1  - ${zweig}`);
    const contested = this._contestedPlaceNote(entry, places);
    if (contested) lines.push(`N1  - ${contested}`);
    lines.push(`UR  - ${this.permalinkUrl(entry.sourcePageId,
      this._publicationSlug(entry, pub, index))}`);
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
      : (pub, i) => this._toRisPublication(entry, pub, i);
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

  /**
   * The contested note reads the reconciliation claims, which a card loads
   * when it opens; a download started before they arrived waits for them
   * rather than citing a contested place as settled.
   */
  _whenClaimsLoaded(run) {
    if (Edit.reconciliation === null && typeof App._ensureReconciliation === 'function') {
      return App._ensureReconciliation().then(run);
    }
    run();
    return Promise.resolve();
  },

  bibtex(pageId, index) {
    return this._whenClaimsLoaded(() => {
      const cite = this._citation(pageId, index, 'bib');
      if (cite) downloadBlob(cite.content, `${cite.name}.bib`, 'application/x-bibtex');
    });
  },

  ris(pageId, index) {
    return this._whenClaimsLoaded(() => {
      const cite = this._citation(pageId, index, 'ris');
      if (cite) {
        downloadBlob(cite.content, `${cite.name}.ris`, 'application/x-research-info-systems');
      }
    });
  },

  jsonld(pageId) {
    const e = this._getEntry(pageId);
    if (!e) return;
    return this._whenClaimsLoaded(() => {
      const jsonld = this._jsonldPayload(e);
      downloadBlob(JSON.stringify(jsonld, null, 2), `klawiter-${pageId}.jsonld`, 'application/ld+json');
    });
  },

  /**
   * The property a field decision of the review object is about. A place
   * decision settles the authority record of the place, which the record
   * carries as klawiter:locationSameAs.
   */
  _reviewedProperty(field) {
    if (field === 'location') return 'klawiter:locationSameAs';
    const term = JsonldPlayground.FRONTEND_TO_JSONLD[field] || field;
    const def = JsonldPlayground.CONTEXT[term];
    if (typeof def === 'string') return def;
    return def && def['@id'] ? def['@id'] : `klawiter:${field}`;
  },

  /**
   * The review state of the record and the decisions it rests on. The
   * playground shows only the terms of the @context, so these travel with the
   * download under their full vocabulary names.
   */
  _reviewProperties(entry) {
    const review = entry.review;
    if (!review || !review.status) return {};
    const place = Edit.locationReconciliation ? Edit.locationReconciliation(entry) : null;
    const actions = Object.entries(review.fields || {}).map(([field, action]) => {
      const node = {
        '@type': 'klawiter:ReviewAction',
        'klawiter:reviewOutcome': action,
        'schema:about': { '@id': this._reviewedProperty(field) },
        'prov:wasAssociatedWith': { 'schema:name': review.reviewed_by },
      };
      if (review.reviewed_at) node['klawiter:decidedAt'] = review.reviewed_at;
      if (field === 'location' && place && place.decision && place.decision.decisionId) {
        node['klawiter:decisionId'] = place.decision.decisionId;
      }
      return node;
    });
    return {
      'klawiter:reviewStatus': review.status,
      ...(actions.length ? { 'klawiter:hasReviewAction': actions } : {}),
    };
  },

  /** An authority claim as a graph node, with its readings and decisions. */
  _authorityClaimNode(claim) {
    const subject = claim.subject || {};
    const predicate = claim.predicate && claim.predicate['@id'] ? claim.predicate['@id'] : claim.predicate;
    return {
      '@id': claim.claimId,
      '@type': 'klawiter:ContestedClaim',
      'klawiter:claimStatus': claim.claimStatus,
      'klawiter:decisionStatus': claim.decisionStatus,
      'klawiter:claimSubject': {
        ...(subject['@id'] ? { '@id': subject['@id'] } : {}),
        ...(subject.name ? { 'schema:name': subject.name } : {}),
      },
      ...(predicate ? { 'klawiter:claimPredicate': { '@id': predicate } } : {}),
      'klawiter:interpretation': (claim.interpretations || []).map(item => ({
        '@id': item.interpretationId,
        '@type': 'klawiter:ClaimInterpretation',
        'schema:name': item.label,
        ...(item.proposedObject && item.proposedObject['@id']
          ? { 'klawiter:proposedObject': { '@id': item.proposedObject['@id'] } } : {}),
        'klawiter:interpretationStatus': item.status,
      })),
      'klawiter:evidence': (claim.sourceEvidence || []).map(item => item['@id']).filter(Boolean),
      'klawiter:hasReviewAction': (claim.reviewHistory || []).map(item => ({
        '@id': item.reviewId,
        '@type': 'klawiter:ReviewAction',
        'klawiter:decisionId': item.decisionId,
        'klawiter:reviewOutcome': item.action,
        'prov:wasAssociatedWith': { 'schema:name': item.decidedBy },
      })),
    };
  },

  _editionClaimNode(claim) {
    return {
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
    };
  },

  /**
   * The record as the playground compacts it, plus what that view leaves
   * out because the @context defines no term for it: the published place
   * authority link, the review state with its field decisions, and the
   * claims the entry carries, referenced from the record and included as
   * nodes of the graph.
   */
  _jsonldPayload(entry) {
    const compact = JsonldPlayground._toCompactJsonld(entry);
    const context = { ...compact['@context'], oa: 'http://www.w3.org/ns/oa#', prov: 'http://www.w3.org/ns/prov#' };
    const entryNode = { ...compact };
    delete entryNode['@context'];
    if (entry.locationSameAs) entryNode['klawiter:locationSameAs'] = { '@id': entry.locationSameAs };
    Object.assign(entryNode, this._reviewProperties(entry));
    const claimNodes = [
      ...(Edit.editionClaimsFor(entry) || []).map(claim => this._editionClaimNode(claim)),
      ...(typeof Edit.authorityClaimsFor === 'function' ? Edit.authorityClaimsFor(entry) || [] : [])
        .map(claim => this._authorityClaimNode(claim)),
    ];
    if (!claimNodes.length) return { '@context': context, ...entryNode };
    entryNode['klawiter:hasContestedClaim'] = claimNodes.map(node => ({ '@id': node['@id'] }));
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
    // The contested notes read the reconciliation claims, which a result list
    // need not have loaded; without them the notes depended on whether a card
    // had been opened in this session.
    const claims = typeof App._ensureReconciliation === 'function'
      ? App._ensureReconciliation()
      : Promise.resolve();
    const pages = this._loadBatch(entries, state => onState && onState(state));
    return Promise.all([claims, pages]).then(() => {
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
      decidedAuthorityClaims: Edit.decidedAuthorityClaims || [],
    };
    downloadBlob(JSON.stringify(payload, null, 2), 'klawiter-bibliography.json', 'application/json');
  },
};

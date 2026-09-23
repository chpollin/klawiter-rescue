/**
 * Detail view — expanded entry content for the result cards and #entry= links.
 *
 * Two layouts, one per audience: the read layout carries one field block in
 * which every value stands once under its own name, with the provenance class
 * and the review decision the record holds for that field, and the Klawiter
 * source underneath as the authority the fields were structured from; the
 * edit layout (localhost EIL mode) keeps the publications of that view
 * read-only and puts the editable cells, evidence snippets and authority
 * candidate blocks into the page record below them, because a patch addresses
 * the source page and not one of its publications.
 */
const Detail = {
  renderInline(entry) {
    const body = App.state.editMode
      ? this._buildEditContent(entry)
      : this._buildReadContent(entry);
    // The wrapper carries the entry id, so data arriving after the first paint
    // finds every place this entry is currently rendered.
    return `<div class="entry-detail" data-entry-detail="${entry.sourcePageId}">${body}</div>`;
  },

  /** Re-render every open detail of one entry after late data arrived. */
  _refresh(pid) {
    if (typeof document === 'undefined' || !document.querySelectorAll) return;
    const entry = App.entryMap && App.entryMap.get(pid);
    if (!entry) return;
    for (const el of document.querySelectorAll(`[data-entry-detail="${pid}"]`)) {
      el.outerHTML = this.renderInline(entry);
    }
    if (typeof App.revealPublication === 'function') App.revealPublication();
    if (typeof App.refreshCardMeta === 'function') App.refreshCardMeta(pid);
  },

  // --- Publication layer -----------------------------------------------------
  // A source page can document several publications. The layer ships inline in
  // the record or as a per-page file, so the card reads whichever the dataset
  // provides and fetches the file at most once per page and session.

  _pubCache: new Map(),

  _publicationState(entry) {
    if (Array.isArray(entry.publications) && entry.publications.length) {
      return { status: 'ready', publications: entry.publications,
               nameVariants: entry.nameVariants || [] };
    }
    if (!(Number(entry.publicationCount) > 0)) return { status: 'absent' };
    return this._pubCache.get(entry.sourcePageId) || { status: 'idle' };
  },

  loadPublications(entry) {
    const pid = entry.sourcePageId;
    if (typeof fetch !== 'function') {
      const state = { status: 'failed', error: 'no fetch in this context',
                      promise: Promise.resolve() };
      this._pubCache.set(pid, state);
      return state.promise;
    }
    const state = { status: 'loading' };
    state.promise = fetch(`data/publications/${pid}.json`)
      .then(resp => {
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        return resp.json();
      })
      .then(doc => {
        this._pubCache.set(pid, {
          status: 'ready',
          publications: doc.publications || [],
          nameVariants: doc.nameVariants || [],
          promise: state.promise,
        });
      })
      .catch(err => {
        this._pubCache.set(pid, { status: 'failed', error: err.message, promise: state.promise });
      });
    this._pubCache.set(pid, state);
    return state.promise;
  },

  // Provenance badge HTML. A pending editor action overrides the machine
  // provenance so the badge reflects the human verdict before it is saved.
  // The provenance map is a parameter, because a publication reports the
  // classes of its own fields.
  _provBadge(fieldName, entry, provenance) {
    const pid = entry.sourcePageId;
    // A pending action is page-scoped, so it answers for the page record
    // alone; a row that brings its own provenance map is a publication row
    // and keeps the class its own record holds.
    const pend = App.state.editMode && !provenance ? Edit.pending(pid, fieldName) : undefined;
    let source;
    if (pend) {
      source = 'editor';
    } else {
      const prov = provenance || entry._provenance;
      if (!prov || !prov[fieldName]) return '';
      source = prov[fieldName];
    }
    const labels = { regex: 'R', llm: 'L', missing: '—', editor: 'E', expert: 'E' };
    const titles = { regex: 'Regex extracted', llm: 'LLM enriched', missing: 'Missing',
                     editor: 'Expert curated', expert: 'Expert curated' };
    const cls = source === 'expert' ? 'editor' : source;   // unify legacy "expert" onto "editor"
    return `<span class="prov-badge prov-${cls}" title="${titles[source] || source}">${labels[source] || source[0].toUpperCase()}</span>`;
  },

  // One place for the help text of a named thing, so a label, a flag line and
  // a head text carry the same sentence wherever they are rendered. A phone
  // shows no tooltip, so nothing but an identifier, a code or a source phrase
  // lives here alone; every sentence explains what the visible line already
  // names.
  HELP: {
    'Title': 'The title of this publication as the source records it.',
    'Original title': 'The title of the work in its original language, where the source names it.',
    'Year': 'The year of publication the record holds for this page.',
    'Year of publication': 'The year of publication the record holds for this page.',
    'Language': 'The language of the publication; the tooltip of this label names the registered subtag.',
    'Place of publication': 'The place or places of the imprint, in the wording of the source.',
    'Location': 'The place of the imprint, in the wording of the source.',
    'Publisher': 'The publisher of the imprint, in the wording of the source.',
    'Extent': 'The extent of the publication.',
    'Extent (as in source)': 'The extent in the notation of the source, with the number the record holds beside it.',
    'Extent (numbered)': 'The numbered extent the record holds; the source carries no notation this can quote.',
    'Pages': 'The numbered extent the record holds for this page.',
    'Credits': 'The people the source credits for this publication, each under the role the record assigns.',
    'Contents': 'The parts this publication contains, with their pages and their own credits.',
    'Published in': 'The journal or volume this contribution appeared in.',
    'Online': 'An address printed in the source for this publication.',
    'Series': 'The series this publication belongs to, with its volume number.',
    'Note': 'What the source states about this publication beyond the named fields.',
    'Translator': 'The translator the flat projection holds for this page.',
    'Reprints': 'Reprints the source page lists.',
    'Translations': 'Translations the source page lists.',
    'See also': 'Cross-references the source page makes to other entries.',
    'Categories': 'The categories the source page is filed under; each opens the entries of that category.',
    'Name variant': 'A spelling in the source close to a credited name; both stand, and no identity is asserted.',
    'Open for review': 'What the extraction or repair rules leave open on this value; the tooltip names the flag code.',
    'Page kind': 'What this source page documents, and how many publications stand on it.',
    'Review status': 'The review decision the dataset holds for this entry, under the session state where one is open. It names the fields the decision covers; every other field is unreviewed.',
    'Authority candidates': 'Authority records proposed for this value; a decision applies to every entry carrying it.',
    'Authority status': 'Open authority claims on this entry.',
    'Edition confirmed': 'The edition graph holds this publication as an edition reviewed against its exact source slice.',
    'Edition proposed': 'The edition graph holds this publication as a deterministic proposal that no review has confirmed yet.',
  },

  /** Title attribute for a named thing, empty where the dictionary is silent. */
  help(label, extra) {
    const text = this.HELP[label];
    if (!text && !extra) return '';
    return ` title="${esc([text, extra].filter(Boolean).join(' ').replace(/\s+/g, ' ').trim())}"`;
  },

  REVIEW_ACTION_LABELS: { confirm: 'confirmed', correct: 'corrected', unresolved: 'unresolved',
                          reject: 'rejected' },

  // Review decision on one field, from the dataset review object. Its scope
  // is that field alone: a decided place says nothing about year or translator.
  // A place decision is about the authority record of one place value, so it
  // stands at that value (_placeList) rather than at a label over a list.
  _fieldReview(fieldName, entry) {
    if (fieldName === 'location' || fieldName === 'places') return '';
    const fields = entry && entry.review && entry.review.fields;
    const action = fields && fields[fieldName];
    if (!action) return '';
    return `<span class="field-review field-review-${esc(action)}"
      title="Reviewed decision on this field alone">${esc(this.REVIEW_ACTION_LABELS[action] || action)}</span>`;
  },

  /** The place decision of the review object, at the value it was made on. */
  _placeReview(entry) {
    const fields = entry && entry.review && entry.review.fields;
    const action = fields && fields.location;
    if (!action) return '';
    return ` <span class="field-review field-review-${esc(action)}"
      title="Reviewed decision on the authority record of this place alone">${
      esc(this.REVIEW_ACTION_LABELS[action] || action)}</span>`;
  },

  /** What a field decision of the review object is about, in a reader's words. */
  REVIEW_SCOPES: { location: 'place authority', publisher: 'publisher', translator: 'translator',
                   pageCount: 'extent', title: 'title' },

  /** "Place authority" for a review object deciding the place authority alone. */
  reviewScope(review) {
    const fields = Object.keys((review && review.fields) || {});
    if (!fields.length) return '';
    const words = fields.map(field => this.REVIEW_SCOPES[field] || field).join(' and ');
    return words.charAt(0).toUpperCase() + words.slice(1);
  },

  REVIEW_WORDS: { agent_verified: 'agent-verified', contested: 'contested',
                  approved: 'expert-reviewed' },

  /** Open authority claims the entry carries; a decided claim no longer contests. */
  _openAuthorityClaims(entry) {
    if (typeof Edit.authorityClaimsFor !== 'function') return [];
    return (Edit.authorityClaimsFor(entry) || []).filter(claim => claim.decisionStatus !== 'decided');
  },

  // Review chip: the dataset projection (entry.review, built by the pipeline
  // from decided reconciliation subjects and applied patches) layered under
  // the live session state, which wins because it is newer. "edited" is the
  // session state alone; "approved" stays reserved for the dataset. A
  // decision covers the fields its review object names, so the chip names
  // them, and an open authority claim the page carries is said beside it.
  _reviewChip(entry) {
    const classes = { unreviewed: 'review-unreviewed', agent_verified: 'review-agent',
      contested: 'review-contested', approved: 'review-approved', edited: 'review-edited' };
    const st = Edit.entryStatus(entry.sourcePageId);
    const dataset = entry.review && entry.review.status;
    const status = st.pending ? st.status : (dataset || 'unreviewed');
    let label;
    if (st.pending) label = 'Edited';
    else if (!dataset) label = 'Unreviewed';
    else {
      const word = this.REVIEW_WORDS[dataset] || String(dataset).replace(/[_-]+/g, ' ');
      const scope = this.reviewScope(entry.review);
      label = scope ? `${scope} ${word}` : word.charAt(0).toUpperCase() + word.slice(1);
    }
    const by = !st.pending && dataset && entry.review.reviewed_by
      ? `Decided by ${entry.review.reviewed_by}.`
      : '';
    const note = st.pending ? ' <span class="review-pending">unsaved</span>' : '';
    const open = status === 'contested' ? [] : this._openAuthorityClaims(entry);
    const nouns = [...new Set(open.map(claim => this.CLAIM_NOUNS[claim.entityType] || 'authority'))];
    const claims = nouns.length
      ? `, <span class="review-claim-note">open ${esc(nouns.join(' and '))} claim</span>`
      : '';
    return `<span class="review-chip ${classes[status] || 'review-other'}"${
      this.help('Review status', by)}>${esc(label)}${note}${claims}</span>`;
  },

  // Editable cell for a provenance-tracked field (edit mode only). A pending
  // correction is the newer state and is what the field shows; the superseded
  // dataset value stays visible beside it. An empty field shows a placeholder
  // and an explicit Add control, so typing into it is recorded as Add.
  _editableValue(fieldName, entry) {
    const pid = entry.sourcePageId;
    const pend = Edit.pending(pid, fieldName);
    const raw = entry[fieldName];
    const original = raw != null && raw !== '' ? String(raw) : '';
    const shown = pend && pend.action !== 'accept'
      ? (pend.newValue == null ? '' : String(pend.newValue))
      : original;
    const has = shown !== '';
    const ph = has ? '' : ' data-placeholder="add value…"';
    const label = Edit.FIELD_LABELS[fieldName] || fieldName;
    const field = `<span class="editable-field${has ? '' : ' editable-empty'}" contenteditable="true"
      role="textbox" aria-label="${esc(label)}"
      data-field="${fieldName}" data-pid="${pid}"
      data-original="${esc(original)}" data-rendered="${esc(shown)}"${ph}>${has ? esc(shown) : ''}</span>`;
    const superseded = pend && pend.action === 'correct' && pend.oldValue
      ? ` <span class="field-superseded" title="Value before this correction">${esc(String(pend.oldValue))}</span>`
      : '';
    const add = has ? '' : ` <button class="field-btn field-add" data-act="add-focus"
      data-field="${fieldName}" data-pid="${pid}">+ Add ${esc(label)}</button>`;
    return field + superseded + add;
  },

  // Per-field action controls: Accept on a present value, Undo on a pending one.
  _fieldControls(fieldName, entry) {
    const pid = entry.sourcePageId;
    const pend = Edit.pending(pid, fieldName);
    const has = entry[fieldName] != null && entry[fieldName] !== '';
    let inner = '';
    if (pend) {
      inner += `<span class="field-action field-action-${pend.action}">${pend.action}</span>`;
      inner += `<button class="field-btn field-revert" title="Undo" data-act="revert"
        data-field="${fieldName}" data-pid="${pid}">↺</button>`;
    } else if (has) {
      inner += `<button class="field-btn field-accept" title="Accept this value" data-act="accept"
        data-field="${fieldName}" data-pid="${pid}">✓</button>`;
    }
    return inner ? ` <span class="field-controls">${inner}</span>` : '';
  },

  // Marker on a field a verify.py flag points at (rank 0-2 triage hint).
  // Provenance-class hints carry no extra marker: the provenance badge
  // already says llm / missing on the same row.
  _triageFlag(fieldName, entry) {
    const hint = Edit.triageHints(entry).find(h => h.field === fieldName && h.rank <= 2);
    if (!hint) return '';
    const detail = hint.detail ? `: ${String(hint.detail).replace(/\s+/g, ' ')}` : '';
    return ` <span class="triage-flag" title="${esc(hint.label + detail)}">!</span>`;
  },

  // Source evidence beside a tracked field (increment 3): the passage of the
  // entry source holding the value, or — when no field-precise span is
  // derivable — the whole source text, collapsible. The fallback is the
  // honest variant: it does not pretend to a segmentation it cannot derive.
  _fieldEvidence(fieldName, entry) {
    const ev = Edit.evidence(entry, fieldName);
    if (ev) {
      const multi = ev.count > 1
        ? ` <span class="evidence-count" title="The value occurs more than once in the source; on multi-edition pages the excerpt can come from a different edition block.">${ev.count} occurrences</span>`
        : '';
      return `<div class="field-evidence">${esc(ev.before)}<mark>${esc(ev.match)}</mark>${esc(ev.after)}${multi}</div>`;
    }
    if (!entry.fullBibliographicEntry) return '';
    return `<details class="field-evidence-fallback">
      <summary>No field-precise excerpt derivable — full source text</summary>
      <div class="field-evidence-full">${esc(entry.fullBibliographicEntry)}</div>
    </details>`;
  },

  // Build the edit-mode cell (editable value + controls + source evidence).
  // The evidence is a block of its own, so the contested mark stands before it.
  _editCell(fieldName, entry) {
    return this._editableValue(fieldName, entry)
      + this._triageFlag(fieldName, entry)
      + this._fieldControls(fieldName, entry)
      + (fieldName === 'location' ? this._contestedMark(entry, entry.location) : '')
      + this._fieldEvidence(fieldName, entry);
  },

  // How many displayed entries a subject-level authority decision covers.
  _subjectReach(count) {
    if (!count || count < 2) return '';
    return ` <span class="subject-reach" title="A decision on this name applies to every entry carrying it.">applies to ${count} entries</span>`;
  },

  // Authority candidate block for the three reconciled subject kinds:
  // 'location', 'person' (translator) and 'publisher'. Location and agent
  // subjects differ only in the lookup and in how the reach is counted, so
  // they share one renderer. "Keep unresolved" is available for every kind
  // because each subject carries the source occurrences the pipeline requires
  // as the evidence behind an unresolved decision.
  _authorityCell(entry, kind) {
    const pid = entry.sourcePageId;
    const isLocation = kind === 'location';
    const review = isLocation
      ? Edit.locationReconciliation(entry)
      : Edit.agentReconciliation(entry, kind);
    if (!review) {
      return isLocation
        ? '<span class="missing-value">No reconciliation record</span>'
        : '<span class="missing-value">No candidate record (below occurrence threshold)</span>';
    }
    const pending = isLocation
      ? Edit.pendingLocationDecision(pid)
      : Edit.pendingAgentDecision(kind, review.name);
    const decision = pending || review.decision;
    const status = pending
      ? 'pending editor decision'
      : (decision ? decision.action : 'proposal only');
    const published = review.publishable
      ? ` <a class="wikidata-link" href="${esc(review.publishable.uri)}" target="_blank" rel="noopener">published link</a>`
      : '';
    const reach = this._subjectReach(isLocation
      ? App.entries.filter(e => e.location === entry.location).length
      : review.occurrences);
    const attrs = `data-pid="${pid}" data-kind="${esc(kind)}"`;
    const candidates = (review.candidates || []).map(candidate => {
      const score = candidate.score == null ? '' : `, score ${candidate.score}`;
      const verdict = this._candidateVerdict(decision, candidate);
      const mark = verdict
        ? ` <span class="candidate-verdict candidate-${verdict}">${verdict}</span>`
        : '';
      return `<li><a href="${esc(candidate.uri)}" target="_blank" rel="noopener">${esc(candidate.label)} (${esc(candidate.qid)})</a>${score}${mark}
        <button class="reconciliation-btn" ${attrs} data-act="confirm" data-qid="${esc(candidate.qid)}">${
          verdict === 'rejected' ? 'Confirm instead' : 'Confirm'}</button></li>`;
    }).join('');
    const revert = pending
      ? `<button class="reconciliation-btn" ${attrs} data-act="undo">Undo pending</button>`
      : '';
    return `<div class="reconciliation-block">
      <div><strong>${esc(status)}</strong>${published}${reach}</div>
      ${candidates ? `<ul>${candidates}</ul>` : '<div>No candidate available.</div>'}
      <div class="reconciliation-actions">
        <button class="reconciliation-btn" ${attrs} data-act="reject">Reject candidates</button>
        <button class="reconciliation-btn" ${attrs} data-act="unresolved">Keep unresolved</button>
        ${revert}
      </div>
    </div>`;
  },

  /**
   * What the recorded decision says about one candidate. A correction names
   * the matcher QID it replaced as `rejectedQid`; a rejection without one
   * refuses every candidate of the subject.
   */
  _candidateVerdict(decision, candidate) {
    if (!decision || !candidate) return '';
    if (decision.rejectedQid && decision.rejectedQid === candidate.qid) return 'rejected';
    if (decision.action === 'reject' && !decision.rejectedQid) return 'rejected';
    if ((decision.action === 'confirm' || decision.action === 'correct')
        && decision.qid === candidate.qid) return 'accepted';
    return '';
  },

  // A claim names what it contests, so the heading takes the noun of its
  // subject; the identifier and the standing rule behind it are what only an
  // occasional desktop check needs, so they are the tooltip of that heading.
  CLAIM_NOUNS: { location: 'place', person: 'person', publisher: 'publisher' },

  // The claim block is addressed per card, because a claim reached from its
  // source pages stands in several cards of one list.
  _claimAnchor(entry, claimId) {
    return `claim-${entry.sourcePageId}-${String(claimId).replace(/[^A-Za-z0-9]+/g, '-')}`;
  },

  /**
   * The word "contested" at the one value an open claim is about.
   *
   * The claim block carries the competing interpretations and the evidence,
   * but it stands below every field of the card, so the value it contests has
   * to say so where it is read. A claim applies only where its subject is
   * that value word for word; a compound imprint is not split at its commas.
   */
  _contestedMark(entry, value) {
    const claim = typeof Edit.openClaimOnValue === 'function'
      ? Edit.openClaimOnValue(entry, value)
      : null;
    if (!claim) return '';
    const tip = this.help(null,
      'An open claim contests this value. It stands with its evidence in this card.');
    return ` <a class="contested-mark"
      href="#${this._claimAnchor(entry, claim.claimId)}"${tip}>contested</a>`;
  },

  /**
   * The places of an imprint, each with what was decided about it.
   *
   * The authority record and the review decision of the record belong to the
   * one value they were made on (entry.location), and an open claim to the
   * value it names, so each mark follows its own value rather than the list.
   */
  _placeList(entry, places) {
    return places.map(place => {
      let out = esc(place);
      if (place === entry.location && entry.locationSameAs) {
        out += ` <a class="wikidata-link" href="${esc(entry.locationSameAs)}" target="_blank"
          rel="noopener" title="Place authority record for ${esc(place)}">Wikidata</a>`;
      }
      if (place === entry.location) out += this._placeReview(entry);
      return out + this._contestedMark(entry, place);
    }).join(', ');
  },

  _claimHeading(noun, claim, rule) {
    const tip = this.help(null, `${claim.claimId} ${rule}`);
    const text = claim.decisionStatus === 'decided'
      ? `${noun.charAt(0).toUpperCase()}${noun.slice(1)} assignment decided`
      : `Contested ${noun} assignment, decision open`;
    return `<h3 class="contested-claim-heading"${tip}>${esc(text)}</h3>`;
  },

  // A checksum is read by its ends; the full value stays one tooltip away.
  _checksum(value) {
    const hex = String(value || '');
    const short = hex.length > 12 ? `${hex.slice(0, 4)}…${hex.slice(-4)}` : hex;
    return `<span class="checksum" title="SHA-256 ${esc(hex)}">${esc(short)}</span>`;
  },

  // The tail of an authority IRI is the identifier a reader recognises; the
  // address itself is what the link resolves to.
  _authorityLink(uri) {
    const id = String(uri).split('/').filter(Boolean).pop();
    return `<a href="${esc(uri)}" target="_blank" rel="noopener"
      title="${esc(uri)}">${esc(id)}</a>`;
  },

  _contestedAuthorityCell(entry) {
    const claims = Edit.authorityClaimsFor(entry);
    if (!claims.length) return '';
    const rendered = claims.map(claim => {
      const noun = this.CLAIM_NOUNS[claim.entityType] || 'authority';
      const interpretations = (claim.interpretations || []).map(item => {
        const proposedObject = item.proposedObject && item.proposedObject['@id'];
        const object = proposedObject
          ? ` · ${this._authorityLink(proposedObject)}`
          : '';
        const status = claim.decisionStatus === 'decided' && item.status
          ? ` (${esc(item.status)})` : '';
        return `<li>${esc(item.label)}${object}${status}</li>`;
      }).join('');
      const evidence = (claim.sourceEvidence || []).map(item =>
        `<li>Page ${esc(item.sourcePageId)}, line ${esc(item.sourceLine)}: ${esc(item.sourceValue)}
          ${this._checksum(item.sourceTextSha256)}</li>`
      ).join('');
      const history = (claim.reviewHistory || []).map(item =>
        `<li title="${esc(item.decisionId)}">${esc(item.decidedBy)}: ${esc(item.action)}</li>`
      ).join('');
      return `<article class="contested-claim" id="${this._claimAnchor(entry, claim.claimId)}"
        tabindex="-1">
        ${this._claimHeading(noun, claim,
          '— the claim stays part of the data, no interpretation is emitted as a confirmed schema:sameAs relation.')}
        <h4>${claim.decisionStatus === 'decided' ? 'Interpretations' : 'Competing interpretations'}</h4>
        <ul>${interpretations}</ul>
        <h4>Source evidence</h4>
        <ul>${evidence}</ul>
        <h4>Review history</h4>
        <ul>${history}</ul>
      </article>`;
    }).join('');
    return `<div class="contested-status" role="status">${rendered}</div>`;
  },

  /**
   * The publication an edition claim is about: the edition identifier the
   * publication carries, or the shared tail of the two identifiers
   * (klawiter:edition/4916-2016-b and klawiter:publication/4916-2016-b).
   */
  _claimPublicationIndex(claim, publications) {
    const subject = String(claim.subject || '');
    const tail = subject.slice(subject.lastIndexOf('/') + 1);
    return (publications || []).findIndex(pub => (pub.editionId && pub.editionId === subject)
      || (tail && String(pub.id || '').endsWith(`/${tail}`)));
  },

  // A decided claim keeps its block: the accepted and the rejected reading,
  // the review history with the decision and what the decision left open stay
  // readable, because the decision is revisable and this is its record.
  _editionClaimArticle(claim) {
    const decided = claim.decisionStatus === 'decided';
    const interpretations = claim.interpretations.map(item =>
      `<li title="${esc(item.proposedObject)}">${esc(item.label)}${
        decided ? ` (${esc(item.status)})` : ''}
        <span class="field-sub">${esc(item.basis)}</span></li>`
    ).join('');
    const history = claim.reviewHistory.map(item =>
      `<li title="${esc(item.reviewId)}">${esc(item.reviewer)}: ${esc(item.outcome)}${
        item.date ? `, ${esc(item.date)}` : ''}${
        item.basis ? ` (${esc(item.basis)})` : ''}</li>`
    ).join('');
    const notes = (claim.reviewNotes || []).map(note => `<li>${esc(note)}</li>`).join('');
    const heading = decided
      ? `<h3 class="contested-claim-heading"${this.help(null, `${claim.claimId} — decided and
        revisable; the accepted reading is the edition's schema:exampleOfWork relation, the
        rejected one stays part of the data without it.`)}>Work identity decided</h3>`
      : `<h3 class="contested-claim-heading"${this.help(null, `${claim.claimId} — the edition stays part
        of the data, none of the interpretations is emitted as a confirmed schema:exampleOfWork
        relation.`)}>Contested work identity, decision open</h3>`;
    return `<article class="contested-claim">
      ${heading}
      <h4>${decided ? 'Interpretations' : 'Competing interpretations'}</h4>
      <ul>${interpretations}</ul>
      <h4>Review history</h4>
      <ul>${history}</ul>
      ${notes ? `<h4>Open for review</h4><ul>${notes}</ul>` : ''}
      <p class="contested-source">Page ${claim.source.sourcePageId}, characters
        ${claim.source.selector[0]}–${claim.source.selector[1]}
        ${this._checksum(claim.source.sliceSha256)}</p>
    </article>`;
  },

  /**
   * Edition claims that no rendered publication takes, as one section after
   * the publications. A claim whose publication is on the card stands in
   * that publication's block instead (_publicationSection).
   */
  _contestedClaimsBlock(entry, claims) {
    const list = claims || Edit.editionClaimsFor(entry);
    if (!list.length) return '';
    const rendered = list.map(claim => this._editionClaimArticle(claim)).join('');
    const open = list.some(claim => claim.decisionStatus !== 'decided');
    return `<section class="detail-section contested-claims" aria-label="${
      open ? 'Contested claims' : 'Decided claims'}">${rendered}</section>`;
  },

  // Ordered attention hints for the entry (edit mode): where checking is most
  // urgent, by data signal. A priority aid, not a quality or workflow score.
  _triageBlock(entry) {
    const hints = Edit.triageHints(entry);
    if (!hints.length) return '';
    const items = hints.map(h => {
      const field = h.field ? `<strong>${esc(Edit.FIELD_LABELS[h.field] || h.field)}</strong> — ` : '';
      const detail = h.detail
        ? `: <span class="triage-detail">${esc(String(h.detail).replace(/\s+/g, ' ').slice(0, 80))}</span>`
        : '';
      return `<li class="triage-rank-${h.rank}">${field}${esc(h.label)}${detail}</li>`;
    });
    return `<div class="triage-hints">
      <div class="triage-hints-head" title="Priority aid from existing data signals (provenance layer, verification flags, census). Not a quality measure.">Review hints</div>
      <ul>${items.join('')}</ul>
    </div>`;
  },

  // ---------------------------------------------------------------------------
  // Read layout — one field block in which every value stands once under its
  // own name, then the claims, then the source it was structured from.
  // ---------------------------------------------------------------------------

  _buildReadContent(entry) {
    const state = this._publicationState(entry);
    if (state.status === 'idle') {
      this.loadPublications(entry).then(() => this._refresh(entry.sourcePageId));
    }
    let html = this._publicationView(entry, state);

    // Contested claims stay visible to every reader: openness is part of the
    // published data, not an edit-mode extra. A missing claim file is said
    // here, where the claims would stand, so it does not read as a clean page.
    html += this._claimsLoadNote();
    const contestedAuthority = this._contestedAuthorityCell(entry);
    if (contestedAuthority) html += contestedAuthority;
    html += this._contestedClaimsBlock(entry, this._unplacedEditionClaims(entry, state));

    // On the permalink route the source is what the reader checks the fields
    // against, so it stands open. In a result list it stays collapsed, unless
    // it is all the expansion has, where one collapsed line reads as empty.
    html += this._sourceBlock(entry, App.state.singleEntry || html === '', state);
    html += this._actionBar(entry);
    return html;
  },

  _claimsLoadNote() {
    if (!Edit.reconciliationFailed) return '';
    const cause = Edit.reconciliationError ? ` (${esc(Edit.reconciliationError)})` : '';
    return `<p class="field-error" role="status">The authority decisions and contested claims
      could not be loaded${cause}. Open claims on this entry are not shown.</p>`;
  },

  /** Edition claims whose publication is not among the rendered blocks. */
  _unplacedEditionClaims(entry, state) {
    const claims = Edit.editionClaimsFor(entry) || [];
    if (state.status !== 'ready') return claims;
    return claims.filter(claim => this._claimPublicationIndex(claim, state.publications) === -1);
  },

  /**
   * The fields of the card, by the state of the publication layer.
   *
   * With the layer every fact belongs to the publication it was written
   * under. Without it the flat projection answers with one value per field,
   * which the note beside it says. A failed load keeps the card on the flat
   * fields rather than leaving it empty.
   */
  _publicationView(entry, state) {
    if (state.status === 'ready') {
      // The rows of the page precede the publications, because they hold for
      // every one of them.
      const placed = this._pageFlagPlacement(entry, state.publications);
      return this._pageFieldsBlock(entry, placed.page)
        + this._publicationBlocks(entry, state, placed.byPublication);
    }
    if (state.status === 'failed') {
      return this._publicationLoadNote(state) + this._fieldBlock(entry);
    }
    if (state.status === 'loading' || state.status === 'idle') {
      return this._publicationLoadNote(state);
    }
    return this._fieldBlock(entry);
  },

  /** The publications alone, as the edit layout shows them beside its table. */
  _publicationBlocks(entry, state, pageFlags) {
    const pubs = state.publications;
    const several = pubs.length > 1;
    // Under a filter that selects some publications of the page and not
    // others, the selected ones say so; a filter all of them answer marks
    // nothing.
    const matches = pubs.map(pub =>
      typeof App.publicationMatches === 'function' ? App.publicationMatches(pub) : null);
    const subset = matches.includes(true) && matches.includes(false);
    const claims = Edit.editionClaimsFor(entry) || [];
    return pubs.map((pub, i) => this._publicationSection(pub, entry, i, several, {
      match: subset && matches[i] === true,
      flags: (pageFlags && pageFlags.get(i)) || {},
      claims: claims.filter(claim => this._claimPublicationIndex(claim, pubs) === i),
    })).join('') + this._nameVariantsBlock(entry, state);
  },

  /** What the card says while the page file is on its way, and if it fails. */
  _publicationLoadNote(state) {
    if (state.status === 'loading' || state.status === 'idle') {
      return '<p class="field-loading" role="status">Loading the publications of this page…</p>';
    }
    if (state.status === 'failed') {
      return `<p class="field-error" role="status">The publications of this page could not be
        loaded (${esc(state.error)}). The fields below are the flat projection of the source
        page.</p>`;
    }
    return '';
  },

  /**
   * The name of one publication inside its page: the tail of its identifier,
   * or its position where the record carries none. The route, the citation
   * key and the section anchor all read it.
   */
  publicationSlug(entry, pub, index) {
    const id = pub && pub.id ? String(pub.id) : '';
    const tail = id.slice(id.lastIndexOf('/') + 1);
    return tail || `${entry.sourcePageId}-${index + 1}`;
  },

  publicationAnchor(entry, slug) {
    return `publication-${entry.sourcePageId}-${String(slug).replace(/[^A-Za-z0-9-]+/g, '-')}`;
  },

  /** One publication, headed by the year and what distinguishes it. */
  _publicationSection(pub, entry, index, several, extra = {}) {
    const rows = this._publicationRows(pub, entry, extra.flags || {});
    const slug = this.publicationSlug(entry, pub, index);
    const classes = ['detail-section', 'publication'];
    if (extra.match) classes.push('publication-match');
    if (App.state.publicationId === slug) classes.push('publication-target');
    const match = extra.match
      ? ' <span class="publication-match-label">matches the filter</span>'
      : '';
    const claims = (extra.claims || []).map(claim => this._editionClaimArticle(claim)).join('');
    return `<section class="${classes.join(' ')}" id="${this.publicationAnchor(entry, slug)}"
      tabindex="-1" aria-label="Publication ${index + 1}">
      <h3 class="publication-heading"><span>${this._publicationHeading(pub, entry)}${
        this._editionStatus(pub)}${match}</span>${
        several ? this._publicationActions(entry, index) : ''}</h3>
      <div class="meta-table">${rows.join('')}</div>
      ${this._reviewFlags(pub)}
      ${claims}
    </section>`;
  },

  /**
   * Whether the edition graph holds this publication as a reviewed edition
   * or as a proposal. Records built before the graph carried it say nothing.
   */
  _editionStatus(pub) {
    const labels = { confirmed: 'Edition confirmed', proposed: 'Edition proposed' };
    const label = labels[pub.reviewStatus];
    if (!label) return '';
    return ` <span class="publication-status publication-status-${esc(pub.reviewStatus)}"${
      this.help(label, pub.editionId ? `Edition ${pub.editionId}.` : '')}>${
      esc(label.replace('Edition ', 'edition '))}</span>`;
  },

  // A citation of a page with several publications has to say which one it
  // describes, so each block carries its own two exports, in its heading row
  // where they read as an addition to that publication rather than as a bar.
  _publicationActions(entry, index) {
    const pid = entry.sourcePageId;
    const attrs = `data-pid="${pid}" data-index="${index}"`;
    return `<span class="publication-actions">
      <button class="cite-link" data-export="bibtex" ${attrs}
        title="Export this publication as BibTeX">BibTeX</button> ·
      <button class="cite-link" data-export="ris" ${attrs}
        title="Export this publication as RIS">RIS</button>
    </span>`;
  },

  _publicationHeading(pub, entry) {
    return esc(this.publicationLabel(pub, entry));
  },

  /** Year and what distinguishes the publication, as plain text. */
  publicationLabel(pub, entry) {
    const year = pub.yearRaw || pub.year;
    const label = year == null ? 'Undated' : String(year);
    if (pub.editionStatement) return `${label} · ${pub.editionStatement}`;
    if (pub.title && pub.title !== entry.title) return `${label} · ${pub.title}`;
    return label;
  },

  ROLE_LABELS: { author: 'Author', translator: 'Translator', editor: 'Editor',
                 illustrator: 'Illustrator', contributor: 'Contributor' },

  // A page-level flag names a field of the flat record; a publication shows
  // that value under a row of its own name.
  FLAG_ROWS: { translator: 'credits', publisher: 'publisher', location: 'places' },

  /**
   * Where each page-level review flag stands on a card with publications: at
   * the row of the first publication carrying the flagged value, or in the
   * page fields where none does.
   */
  _pageFlagPlacement(entry, publications) {
    const byPublication = new Map();
    const page = [];
    for (const flag of Array.isArray(entry.reviewFlags) ? entry.reviewFlags : []) {
      const value = flag.field ? entry[flag.field] : null;
      const at = value == null ? -1 : publications.findIndex(pub => {
        if (flag.field === 'publisher') return pub.publisher === value;
        if (flag.field === 'location') return (pub.places || []).includes(value);
        if (flag.field === 'translator') {
          const credits = (pub.credits || []).concat(
            ...(pub.contributions || []).map(item => item.credits || []));
          return credits.some(credit => credit.name === value);
        }
        return false;
      });
      const row = this.FLAG_ROWS[flag.field];
      if (at === -1 || !row) { page.push(flag); continue; }
      const rows = byPublication.get(at) || {};
      (rows[row] = rows[row] || []).push(flag);
      byPublication.set(at, rows);
    }
    return { byPublication, page };
  },

  _publicationRows(pub, entry, flags = {}) {
    const rows = [];
    const prov = pub.provenance || {};
    const shown = new Set();
    const put = (label, value, fieldName) => {
      if (!value) return;
      rows.push(this.row(label, value, fieldName, entry, prov));
      if (flags[fieldName]) rows.push(this._reviewFlags({ reviewFlags: flags[fieldName] }));
      shown.add(fieldName);
    };

    // The title stands as a row wherever the heading did not already take it.
    if (pub.title && pub.title !== entry.title && pub.editionStatement) {
      put('Title', `<span${titleAttrs(pub, pub.title)}>${esc(pub.title)}</span>`, 'title');
    }
    put('Language', this._languageValue(pub), 'language');

    const places = Array.isArray(pub.places) ? pub.places : [];
    put('Place of publication', places.length ? this._placeList(entry, places) : '', 'places');

    put('Publisher', pub.publisher ? esc(pub.publisher) : '', 'publisher');
    put('Extent (as in source)', this._publicationExtent(pub), 'extent');
    put('Credits', this._creditsList(pub.credits), 'credits');
    put('Contents', this._contributionsList(pub.contributions), 'contributions');
    put('Published in', this._containerValue(pub.container), 'container');
    put('Online', this._onlineValue(pub.online), 'online');
    put('Series', this._seriesValue(pub), 'series');
    put('Note', pub.note ? esc(pub.note) : '', 'note');
    // A translator credited under a contribution has no Credits row of its own.
    for (const [fieldName, list] of Object.entries(flags)) {
      if (!shown.has(fieldName)) rows.push(this._reviewFlags({ reviewFlags: list }));
    }
    return rows;
  },

  // The language name is the value; the registered subtag is a code and stays
  // in the tooltip rather than taking room beside every language.
  _languageValue(fields) {
    if (!fields.language) return '';
    const code = fields.languageCode
      ? ` title="Registered language subtag ${esc(fields.languageCode)}"`
      : '';
    return `<span${code}>${esc(fields.language)}</span>`;
  },

  _publicationExtent(pub) {
    const extent = pub.extent;
    if (!extent) return '';
    if (!extent.raw) return extent.numbered == null ? '' : `<span>${extent.numbered} pp.</span>`;
    const parts = [];
    const plain = extent.raw.replace(/\s+/g, '') === `${extent.numbered}p.`;
    if (!plain && extent.numbered != null) parts.push(`${extent.numbered} numbered`);
    if (extent.unnumbered != null) parts.push(`${extent.unnumbered} unnumbered`);
    const detail = parts.length
      ? ` <span class="field-sub" title="Components of the source notation">${parts.join(', ')}</span>`
      : '';
    return esc(extent.raw) + detail;
  },

  // Roles come from the closed vocabulary of the record. What the source
  // phrase says beyond the role stands visibly beside the name, because a
  // phone shows no tooltip and "Verses translated by" is not "Translated by".
  _creditsList(credits) {
    if (!credits || !credits.length) return '';
    return credits.map(credit => {
      const role = credit.role
        ? `<span class="credit-role">${esc(this.ROLE_LABELS[credit.role] || credit.role)}</span> `
        : '';
      const label = credit.creditLabel ? ` title="${esc(credit.creditLabel)}"` : '';
      return `${role}<span class="credit-name"${label}>${esc(credit.name)}</span>`
        + this._creditQualifier(credit);
    }).join(' · ');
  },

  // The verb the role name generalizes away, per role of the vocabulary. A
  // contributor has no such verb, so its phrase stands whole.
  ROLE_VERBS: { translator: 'translated', editor: 'edited', illustrator: 'illustrated' },

  /**
   * What the credit phrase of the source says beyond the plain role.
   *
   * The phrase reads "<Role> by" wherever it adds nothing, and that case
   * yields an empty qualifier. Otherwise the role verb and the closing "by"
   * are dropped and the remainder stands after the name; the full phrase
   * stays in the tooltip of the name. A capital further along marks a name
   * the source spells that way, so the opening word keeps its case there.
   */
  _creditQualifier(credit) {
    if (!credit.creditLabel) return '';
    const verb = this.ROLE_VERBS[credit.role];
    let rest = String(credit.creditLabel).replace(/\s*\bby\s*$/i, '');
    if (verb) rest = rest.replace(new RegExp(`(^|\\s)${verb}(?=\\s|$)`, 'i'), '$1');
    rest = rest.replace(/\s+/g, ' ').replace(/^and\s+/i, '').replace(/\s+and$/i, '').trim();
    if (!rest) return '';
    const shown = /\s[A-Z]/.test(rest) ? rest : rest[0].toLowerCase() + rest.slice(1);
    return ` <span class="field-sub">(${esc(shown)})</span>`;
  },

  _contributionsList(contributions) {
    if (!contributions || !contributions.length) return '';
    const items = contributions.map(item => {
      const title = item.title ? `<span class="content-item-title">${esc(item.title)}</span>` : '';
      const pages = item.pages ? ` <span class="content-item-pages">${esc(item.pages)}</span>` : '';
      const credits = this._creditsList(item.credits);
      // The note repeats the credits wherever both are read from the same
      // bracket, so it stands in only where it carries the roles alone.
      const note = (!item.credits || !item.credits.length) && item.note
        ? ` <span class="field-sub">${esc(item.note)}</span>`
        : '';
      return `<li>${title}${pages}${credits ? ` ${credits}` : ''}${note}</li>`;
    });
    return `<ol class="detail-list-numbered contribution-list">${items.join('')}</ol>`;
  },

  _containerValue(container) {
    if (!container) return '';
    const parts = [];
    if (container.title) parts.push(esc(container.title));
    if (container.place) parts.push(esc(container.place));
    if (container.issue) parts.push(`issue ${esc(container.issue)}`);
    if (container.pages) parts.push(`pp. ${esc(container.pages)}`);
    return parts.join(', ');
  },

  _onlineValue(online) {
    if (!online || !online.url) return '';
    const note = online.note ? ` <span class="field-sub">${esc(online.note)}</span>` : '';
    return `<a href="${esc(online.url)}" target="_blank" rel="noopener">${esc(online.url)}</a>${note}`;
  },

  _seriesValue(pub) {
    if (!pub.series) return '';
    const volume = pub.seriesVolume
      && !String(pub.series).trim().endsWith(String(pub.seriesVolume))
      ? ` <span class="field-sub">volume ${esc(pub.seriesVolume)}</span>`
      : '';
    return esc(pub.series) + volume;
  },

  // What the extraction rules leave open on this publication, in the words of
  // the record. A hint for review, never a claim that the value is wrong.
  _reviewFlags(pub) {
    const flags = pub.reviewFlags || [];
    if (!flags.length) return '';
    return flags.map(flag =>
      `<p class="review-flag" role="note"${this.help('Open for review', `Flag ${flag.code}.`)}><span
        class="review-flag-label">Open for review</span> ${esc(flag.detail || flag.code)}</p>`
    ).join('');
  },

  // A spelling in the source that stands close to a credited name. Both stay,
  // and no identity between them is asserted.
  _nameVariantsBlock(entry, state) {
    const variants = (entry.nameVariants && entry.nameVariants.length
      ? entry.nameVariants
      : state.nameVariants) || [];
    if (!variants.length) return '';
    const rows = variants.map(variant => this.row('Name variant',
      `<span class="variant-name">${esc(variant.name)}</span>
       <span class="field-sub">beside ${esc(variant.variantOf)}, ${esc(variant.status)}</span>
       <span class="variant-context">${esc(variant.sourceContext)}</span>`));
    return `<section class="detail-section name-variants" aria-label="Name variants in source">
      <h3 class="detail-section-heading">Name variants in source</h3>
      <div class="meta-table">${rows.join('')}</div>
    </section>`;
  },

  /** The fields that belong to the source page rather than to a publication. */
  _pageFieldsBlock(entry, flags) {
    const rows = this._pageRows(entry, entry);
    if (flags && flags.length) rows.push(this._reviewFlags({ reviewFlags: flags }));
    if (!rows.length) return '';
    return `<div class="meta-table detail-fields" role="group"
      aria-label="Source page fields">${rows.join('')}</div>`;
  },

  /**
   * The bibliographic fields of the flat record, each named, each value once.
   *
   * This is the projection a page without a publication layer answers with.
   */
  _fieldBlock(entry) {
    const rows = this._fieldRows(entry, entry);
    if (!rows.length) return '';
    return `<section class="detail-section detail-fields" aria-label="Bibliographic fields">
      ${this._multiPublicationNote(entry)}
      <div class="meta-table">${rows.join('')}</div>
    </section>`;
  },

  _fieldRows(fields, entry) {
    const rows = [];
    const put = (label, value, fieldName) => {
      if (value) rows.push(this.row(label, value, fieldName, entry));
    };
    // A field the provenance layer tracks is shown even when it holds nothing,
    // because "missing" is a recorded state of the record and part of what a
    // reader checks. No placeholder stands in for the absent value.
    // A page-level review flag stands under the row of the field it names.
    const pageFlags = Array.isArray(entry.reviewFlags) ? entry.reviewFlags : [];
    const tracked = (label, fieldName, value) => {
      const prov = entry._provenance && entry._provenance[fieldName];
      if (value) rows.push(this.row(label, value, fieldName, entry));
      else if (prov === 'missing') {
        rows.push(this.row(label, '<span class="missing-value">Not recorded</span>',
          fieldName, entry));
      }
      const flags = pageFlags.filter(flag => flag.field === fieldName);
      if (flags.length) rows.push(this._reviewFlags({ reviewFlags: flags }));
    };

    if (fields.originalTitle && fields.originalTitle !== fields.title) {
      put('Original title',
        `<span${titleAttrs(entry, fields.originalTitle)}>${esc(fields.originalTitle)}</span>`);
    }
    put('Year of publication', fields.year ? String(fields.year) : '');
    put('Language', this._languageValue(fields));

    const places = Array.isArray(fields.allLocations) && fields.allLocations.length > 1
      ? fields.allLocations
      : (fields.location ? [fields.location] : []);
    tracked('Place of publication', 'location', places.length ? this._placeList(entry, places) : '');

    tracked('Publisher', 'publisher', fields.publisher ? esc(fields.publisher) : '');

    const extent = this._extentValue(fields, entry);
    tracked(extent.label, 'pageCount', extent.html);

    tracked('Translator', 'translator', fields.translator ? esc(fields.translator) : '');

    if (fields.contentItems && fields.contentItems.length) {
      put('Contents', `<ol class="detail-list-numbered detail-contents">${
        fields.contentItems.map(c => this._contentItem(c)).join('')}</ol>`);
    }
    return rows.concat(this._pageRows(fields, entry));
  },

  /** Rows the source page carries whether or not it documents publications. */
  _pageRows(fields, entry) {
    const rows = [];
    const put = (label, value) => {
      if (value) rows.push(this.row(label, value));
    };
    if (fields.reprints && fields.reprints.length) {
      put('Reprints', `<ul class="detail-list">${
        fields.reprints.map(r => `<li>${esc(r)}</li>`).join('')}</ul>`);
    }
    if (fields.translations && fields.translations.length) {
      put('Translations', `<ul class="detail-list">${
        fields.translations.map(t => `<li>${esc(t)}</li>`).join('')}</ul>`);
    }
    if (fields.seeAlso && fields.seeAlso.length) {
      put('See also', fields.seeAlso.map(ref => this.makeLink(ref)).join(', '));
    }
    if (fields.categories && fields.categories.length) {
      put('Categories', fields.categories.map(c =>
        `<a href="#category=${encodeURIComponent(c)}">${esc(c)}</a>`).join(', '));
    }
    return rows;
  },

  /**
   * Extent as the source spells it, with the record's number beside it.
   *
   * The token is anchored on the numbered extent the record holds, so this
   * quotes the source instead of parsing a second value out of it. Without a
   * match the number stands alone and the label says it is the numbered one.
   */
  _extentValue(fields, entry) {
    const n = parseInt(fields.pageCount, 10);
    if (!Number.isFinite(n)) return { label: 'Extent', html: '' };
    const text = entry.fullBibliographicEntry;
    const match = text
      ? new RegExp(`(?<!\\d)${n}(?:\\s*/\\s*\\(\\d+\\))?\\s*pp?\\.`).exec(text)
      : null;
    if (!match) return { label: 'Extent (numbered)', html: `<span>${n} pp.</span>` };
    const numbered = match[0].replace(/\s+/g, '') === `${n}p.`
      ? ''
      : ` <span class="field-sub" title="Numbered extent held by the record">${n} pp.</span>`;
    return { label: 'Extent (as in source)', html: esc(match[0]) + numbered };
  },

  /**
   * Marker for a source page holding more than one publication.
   *
   * Read from what the record carries, several dated blocks or categories in
   * several languages. The flat projection takes the first match per field,
   * so a single unnamed triade there would describe no real publication.
   */
  _multiPublicationNote(entry) {
    const years = Array.isArray(entry.allYears) ? entry.allYears.length : 0;
    const languages = new Set((entry.categories || [])
      .map(c => /\(([^)]+)\)\s*$/.exec(c))
      .filter(Boolean)
      .map(m => m[1]));
    if (years < 2 && languages.size < 2) return '';
    return `<p class="field-note">This source page carries more than one publication, and every
      field below is the first match in the source text.</p>`;
  },

  /**
   * The Klawiter entry, with the identifiers of that source text at it.
   *
   * Page, text and blob identify this source record rather than the card, so
   * they stand with it instead of in a card foot. Addresses printed in the
   * source stay reachable.
   */
  _sourceBlock(entry, open, state) {
    if (!entry.fullBibliographicEntry) return '';
    const publications = state && state.status === 'ready' ? state.publications : null;
    return `<details class="detail-source-details"${open ? ' open' : ''}>
      <summary>Full bibliographic entry (Klawiter source)</summary>
      <div class="detail-bibentry">${this._sourceBody(entry.fullBibliographicEntry, publications, entry)}</div>
      ${this._provenanceLine(entry)}
    </details>`;
  },

  /**
   * The source text, with the block each publication was read from marked.
   *
   * Only `textStart` and `textEnd` are used, the offsets into the text the
   * card shows; the segmentation offsets beside them address the raw source
   * and would mark the wrong passage. A slice without them, or one that
   * leaves the order or the bounds of the text, marks nothing.
   */
  _sourceBody(text, publications, entry) {
    const slices = (publications || [])
      .map(pub => ({ pub, slice: pub.sourceSlice }))
      .filter(({ slice }) => slice
        && Number.isFinite(slice.textStart) && Number.isFinite(slice.textEnd))
      .sort((a, b) => a.slice.textStart - b.slice.textStart);
    // A marked block is a box of its own, so the line break that separated
    // it from the text around it would add an empty line inside the flow.
    let out = '';
    let cursor = 0;
    let afterBlock = false;
    for (const { pub, slice } of slices) {
      if (slice.textStart < cursor || slice.textEnd <= slice.textStart
          || slice.textEnd > text.length) continue;
      let gap = text.slice(cursor, slice.textStart);
      if (afterBlock) gap = gap.replace(/^\n/, '');
      gap = gap.replace(/\n$/, '');
      const label = entry
        ? `<span class="source-slice-label">${esc(this.publicationLabel(pub, entry))}</span>`
        : '';
      out += linkifyEsc(gap)
        + `<span class="source-slice">${label}${
          linkifyEsc(text.slice(slice.textStart, slice.textEnd))}</span>`;
      cursor = slice.textEnd;
      afterBlock = true;
    }
    const rest = text.slice(cursor);
    return out + linkifyEsc(afterBlock ? rest.replace(/^\n/, '') : rest);
  },

  // Split a trailing page reference off a contents item for aligned display.
  // A title that is itself an entry becomes a link to that entry.
  _contentItem(text) {
    const m = /^(.*?)[,.]?\s*(pp?\.\s*[\d\s()\/\-–.]+[a-z]?)\s*$/i.exec(text);
    if (m && m[1]) {
      return `<li><span class="content-item-title">${this._contentTitle(m[1])}</span><span class="content-item-pages">${esc(m[2])}</span></li>`;
    }
    return `<li>${this._contentTitle(text)}</li>`;
  },

  _contentTitle(title) {
    const pid = App.titleMap && App.titleMap.get(title.trim());
    return pid ? `<a href="#entry=${pid}">${esc(title)}</a>` : esc(title);
  },

  // ---------------------------------------------------------------------------
  // Edit layout — the full adjudication table (localhost EIL mode).
  // ---------------------------------------------------------------------------

  // The patch contract addresses the source page, so an editable row carries
  // the page value even where the publications above hold one of their own.
  PAGE_SCOPE: 'This value belongs to the source page as a whole. An edit here applies to the '
    + 'page record, not to one of its publications.',

  /**
   * The scope line of the page record.
   *
   * A page with several publications shows their blocks above the table, and
   * the table holds one value per field for all of them, so the difference is
   * said where the editing happens rather than left to be inferred.
   */
  _pageRecordNote(entry, state) {
    const count = state.status === 'ready'
      ? state.publications.length
      : Number(entry.publicationCount);
    if (!(count > 1)) return '';
    return `<p class="review-flag" role="note"><span class="review-flag-label">Scope</span>
      The page record holds one value per field for a page with ${count} publications. An edit
      here applies to the page record, not to one publication.</p>`;
  },

  _buildEditContent(entry) {
    const state = this._publicationState(entry);
    if (state.status === 'idle') {
      this.loadPublications(entry).then(() => this._refresh(entry.sourcePageId));
    }
    let html = '';
    const rows = [];
    const contestedAuthority = this._contestedAuthorityCell(entry);
    const editRow = (label, fieldName) =>
      this.row(label, this._editCell(fieldName, entry), fieldName, entry, null, this.PAGE_SCOPE);

    rows.push(this.row('Title', `<span${titleAttrs(entry, entry.title)}>${esc(entry.title)}</span>`));

    if (entry.originalTitle && entry.originalTitle !== entry.title) {
      rows.push(this.row('Original title',
        `<span${titleAttrs(entry, entry.originalTitle)}>${esc(entry.originalTitle)}</span>`));
    }

    if (entry.year) {
      const period = entry.timePeriod ? ` — ${PERIOD_LABELS[entry.timePeriod] || entry.timePeriod}` : '';
      rows.push(this.row('Year', `${entry.year}${period}`));
    }

    rows.push(editRow('Publisher', 'publisher'));
    if (entry.publisher) {
      rows.push(this.row('Authority candidates', this._authorityCell(entry, 'publisher')));
    }

    rows.push(editRow('Location', 'location'));
    if (entry.location) {
      rows.push(this.row('Authority candidates', this._authorityCell(entry, 'location')));
    }

    if (contestedAuthority) {
      rows.push(this.row('Authority status', contestedAuthority));
    }

    if (entry.language) rows.push(this.row('Language', this._languageValue(entry)));

    rows.push(editRow('Pages', 'pageCount'));

    rows.push(editRow('Translator', 'translator'));
    if (entry.translator) {
      rows.push(this.row('Authority candidates', this._authorityCell(entry, 'person')));
    }

    if (entry.categories && entry.categories.length) {
      const catLinks = entry.categories.map(c =>
        `<a href="#category=${encodeURIComponent(c)}">${esc(c)}</a>`);
      rows.push(this.row('Categories', catLinks.join(', ')));
    }

    html += this._triageBlock(entry);
    // The publications stay as the reading view shows them and stay read-only,
    // because the patch contract carries no target for a single one of them.
    html += state.status === 'ready'
      ? this._publicationBlocks(entry, state,
        this._pageFlagPlacement(entry, state.publications).byPublication)
      : this._publicationLoadNote(state);
    html += `<section class="detail-section page-record">
      <h3 class="detail-section-heading">Page record</h3>
      ${this._pageRecordNote(entry, state)}
      <div class="meta-table">${rows.join('')}</div>
    </section>`;
    html += this._claimsLoadNote();
    html += this._contestedClaimsBlock(entry, this._unplacedEditionClaims(entry, state));

    // In edit mode the source is the adjudication reference: kept open.
    if (entry.fullBibliographicEntry) {
      html += `
        <div class="detail-section detail-evidence">
          <h3 class="detail-section-heading">Source — verify each field against this</h3>
          <div class="detail-bibentry">${linkifyEsc(entry.fullBibliographicEntry)}</div>
          ${this._provenanceLine(entry)}
        </div>
      `;
    }

    if (entry.seeAlso && entry.seeAlso.length) {
      const refs = entry.seeAlso.map(ref => this.makeLink(ref));
      html += `
        <div class="detail-section">
          <h3 class="detail-section-heading">See Also</h3>
          <div>${refs.join(', ')}</div>
        </div>
      `;
    }

    html += this._actionBar(entry);
    return html;
  },

  // ---------------------------------------------------------------------------
  // Shared building blocks
  // ---------------------------------------------------------------------------

  _actionBar(entry) {
    const pid = entry.sourcePageId;
    const state = this._publicationState(entry);
    const all = state.status === 'ready' && state.publications.length > 1 ? ' all' : '';
    return `
      <div class="action-bar">
        <button class="action-btn" data-export="bibtex" data-pid="${pid}" title="Export BibTeX">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
          Cite${all} (BibTeX)
        </button>
        <button class="action-btn" data-export="ris" data-pid="${pid}" title="Export RIS">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          Cite${all} (RIS)
        </button>
        <button class="action-btn" data-export="jsonld" data-pid="${pid}" title="Download JSON-LD">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          JSON-LD
        </button>
        <a class="action-btn" href="#data/playground/${pid}" title="Open this entry in the JSON-LD playground">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
          Playground
        </a>
        <button class="action-btn" data-export="permalink" data-pid="${pid}" data-permalink="${pid}" title="Copy permalink">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
          Permalink
        </button>
      </div>
    `;
  },

  _provenanceLine(entry) {
    return `<div class="detail-provenance" title="Identifiers of this source record">
      Page ID: ${entry.sourcePageId}
      ${entry.sourceTextId ? ' · Text ID: ' + entry.sourceTextId : ''}
      ${entry.sourceBlobId ? ' · Blob: ' + entry.sourceBlobId : ''}
    </div>`;
  },

  row(label, value, fieldName, entry, provenance, helpExtra) {
    const badge = fieldName && entry ? this._provBadge(fieldName, entry, provenance) : '';
    const review = fieldName && entry ? this._fieldReview(fieldName, entry) : '';
    // Label and value are flex items, so a short value stays on the label's
    // line and a long one wraps under it without a second element type.
    return `<div class="meta-row"><div class="meta-label"${this.help(label, helpExtra)}>${label}${badge}${review}</div><div class="meta-value">${value}</div></div>`;
  },

  makeLink(title) {
    const pid = App.titleMap.get(title) || (App.data.redirects && App.data.redirects[title]);
    if (pid) return `<a href="#entry=${pid}">${esc(title)}</a>`;
    return esc(title);
  },
};

// Event delegation for everything the detail card renders. The card HTML is
// rebuilt on every change, so handlers live on the document and read their
// arguments from data attributes instead of being interpolated into markup.
if (typeof document !== 'undefined' && document.addEventListener) {
  document.addEventListener('click', (ev) => {
    const target = ev.target.closest ? ev.target : null;
    if (!target) return;

    // The mark at a contested value points into its own card. The jump is made
    // here rather than by the browser, because the router reads a fragment as
    // a route and would leave the entry.
    const claimLink = target.closest('.contested-mark');
    if (claimLink) {
      ev.preventDefault();
      const block = document.getElementById(claimLink.getAttribute('href').slice(1));
      if (block) {
        block.scrollIntoView({ block: 'nearest' });
        block.focus();
      }
      return;
    }

    // Every export control of a card carries data-export, in the bar at its
    // foot as well as in a publication heading, and nothing else does.
    const exportBtn = target.closest('[data-export]');
    if (exportBtn) {
      const pid = Number(exportBtn.dataset.pid);
      const index = exportBtn.dataset.index;
      const fn = Export[exportBtn.dataset.export];
      if (typeof fn === 'function') {
        fn.call(Export, pid, index === undefined ? undefined : Number(index));
      }
      return;
    }

    const fieldBtn = target.closest('.meta-value .field-btn[data-act]');
    if (fieldBtn) {
      const pid = Number(fieldBtn.dataset.pid);
      const field = fieldBtn.dataset.field;
      if (fieldBtn.dataset.act === 'accept') Edit.accept(pid, field);
      else if (fieldBtn.dataset.act === 'revert') Edit.revert(pid, field);
      else if (fieldBtn.dataset.act === 'add-focus') {
        const cell = fieldBtn.parentElement.querySelector(
          `.editable-field[data-field="${field}"]`
        );
        if (cell) cell.focus();
      }
      return;
    }

    const authBtn = target.closest('.reconciliation-block .reconciliation-btn[data-act]');
    if (authBtn) {
      const pid = Number(authBtn.dataset.pid);
      const kind = authBtn.dataset.kind;
      const act = authBtn.dataset.act;
      if (kind === 'location') {
        if (act === 'undo') Edit.revertLocationDecision(pid);
        else Edit.decideLocation(pid, act, authBtn.dataset.qid || null);
      } else if (act === 'undo') {
        Edit.revertAgentDecision(pid, kind);
      } else {
        Edit.decideAgent(pid, kind, act, authBtn.dataset.qid || null);
      }
    }
  });

  // contenteditable keys: Enter commits (a line break in a single-value field
  // is never wanted), Escape restores the rendered value and leaves the field.
  document.addEventListener('keydown', (ev) => {
    const cell = ev.target.closest ? ev.target.closest('.editable-field') : null;
    if (!cell) return;
    if (ev.key === 'Enter') {
      ev.preventDefault();
      cell.blur();
    } else if (ev.key === 'Escape') {
      ev.preventDefault();
      cell.textContent = cell.dataset.rendered || '';
      cell.blur();
    }
  });

  // blur does not bubble; focusout is the delegated equivalent.
  document.addEventListener('focusout', (ev) => {
    const cell = ev.target.closest ? ev.target.closest('.editable-field') : null;
    if (cell) Edit.trackChange(cell);
  });
}

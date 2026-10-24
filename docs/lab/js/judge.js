/**
 * Prototype 1, Judge a value (knowledge/lab-frontend.md, E2 and S3.2).
 *
 * Route: judge.html#page=<id>[&sel=<value key>]. A value key names one value
 * button, "p<i>-<field>-<j>" for publication <i> or "r-<field>" for the
 * page-level record, so a selected value is addressable.
 */

import {
  loadJSON, h, fill, add, readHash, writeHash, typeLabel, dataStateBlock, citation, citeUrl,
  download, copyText, initHeader, errorBlock, yearsSpan, plural, accessDate,
} from './lab.js';
import {
  FIELD_LABELS as RECORD_LABELS, ORIGIN, editionStateText, placeStateParts, printPaneState,
  provenanceSteps,
} from './labels.js';
import { bibtex, jsonExport, ris } from './record-export.js';

const main = document.getElementById('main');
const NO_VALUE = 'no value recorded';
const NO_EXACT = 'no exact occurrence, the value may be normalised';
const sentence = text => `${text[0].toUpperCase()}${text.slice(1)}.`;
const BOUNDARY_REASONS = {
  'record-has-no-year': 'The record has no year, so the boundary check does not run.',
  'year-publication-passage-not-located':
    'The passage of the publication that has the record\'s year is not located in the text, so the boundary check does not run.',
};

let page = null;
let meta = null;
let valueIndex = new Map();
let shownClaims = new Map();
// Resolves to the local print files of the page ({ index, data, agreement }), all null in a published run.
let printFiles = null;

initHeader();
window.addEventListener('hashchange', route);
document.addEventListener('keydown', event => {
  if (event.key !== 'Escape' || event.ctrlKey || event.metaKey || event.altKey) return;
  if (document.querySelector('.value-btn[aria-pressed="true"]')) {
    event.preventDefault();
    select(null);
  }
});
route();

async function route() {
  const params = readHash();
  const id = Number(params.get('page'));
  if (!id) return renderStart();
  if (!page || page.pageId !== id) {
    fill(main, h('p', { class: 'status', role: 'status' }, `Loading page ${id}.`));
    try {
      [page, meta] = await Promise.all([loadJSON(`pages/${id}.json`), loadJSON('meta.json')]);
    } catch (error) {
      page = null;
      fill(main, 
        h('h1', {}, `Page ${id}`),
        errorBlock(new Error(`no prepared record for page ${id} (${error.message})`), route));
      return;
    }
    render();
    document.title = `${page.title}, Judge a value, Klawiter Bibliography Lab`;
    main.focus({ preventScroll: true });
  }
  select(params.get('sel'), { fromHash: true });
  const pubId = params.get('pub');
  const target = pubId && document.querySelector(`.publication[data-pub="${CSS.escape(pubId)}"]`);
  if (target) {
    target.classList.add('is-current');
    target.scrollIntoView({ block: 'start' });
  }
}

async function renderStart() {
  page = null;
  document.title = 'Judge a value, Klawiter Bibliography Lab';
  const form = h('form', { class: 'filters', onsubmit: event => {
    event.preventDefault();
    const id = form.elements.pid.value.trim();
    if (id) location.hash = `page=${encodeURIComponent(id)}`;
  } },
  h('div', { class: 'field' },
    h('label', { for: 'pid' }, 'Page id'),
    h('input', { id: 'pid', name: 'pid', type: 'number', min: '1', inputmode: 'numeric' })),
  h('button', { class: 'btn', type: 'submit' }, 'Open record'));
  const list = h('ul', { class: 'hit-list' });
  fill(main, 
    h('h1', {}, 'Judge a value'),
    h('p', { class: 'prose' }, 'Open the record of one wiki page. Selecting a value marks where it stands in the source text. Pages are found through the search in the header or by their id.'),
    form,
    h('h2', {}, 'Reference records'),
    list);
  try {
    const refs = await loadJSON('reference-records.json');
    for (const ref of Object.values(refs.classes)) {
      if (!ref.pageId) continue;
      list.append(h('li', {},
        h('a', { href: `#page=${ref.pageId}` }, `Page ${ref.pageId}`),
        h('div', { class: 'why' }, `Selected as ${ref.selectionRule}; ${plural(ref.candidates.count, 'candidate', 'candidates')}.`)));
    }
    list.append(h('li', {},
      h('a', { href: '#page=448' }, 'Page 448'),
      h('div', { class: 'why' }, refs.page448.reason)));
  } catch (error) {
    list.replaceWith(errorBlock(error, renderStart));
  }
}

function render() {
  valueIndex = new Map();
  shownClaims = new Map();
  const pubs = page.publications;
  const breakdown = pubs.length > 0;
  const grid = h('div', { class: `judge-grid ${breakdown ? 'has-breakdown' : 'no-breakdown'}` });
  const left = h('div', { class: 'judge-left' });
  if (breakdown) {
    left.append(h('section', { 'aria-labelledby': 'pubs-h' },
      h('h2', { class: 'section-label', id: 'pubs-h' }, 'Publications'),
      defaultsNote(pubs),
      pubs.map((pub, i) => publicationBlock(pub, i))));
  }
  left.append(recordBlock());
  grid.append(left, sourcePane());
  fill(main, headerBlock(), grid, toolsRow());
  loadPrint();
}

function headerBlock() {
  const pubs = page.publications;
  const years = pubs.length ? pubs.map(p => p.year) : page.allYears;
  const facts = [
    page.language || 'language not recorded',
    typeLabel(page.entryType),
    pubs.length ? plural(pubs.length, 'publication', 'publications') : 'no publication breakdown',
    yearsSpan(years),
    `page ${page.pageId}`,
  ];
  return h('header', { class: 'record-head' },
    h('h1', { lang: page.languageCode || null }, page.title),
    h('p', { class: 'subline' }, facts.join(', ')),
    page.works.length
      ? h('ul', { class: 'subline', 'aria-label': 'Work groups' }, page.works.map(w => h('li', {},
        'Work: ', h('a', { href: `find.html#work=${encodeURIComponent(w.workId)}` }, w.title),
        ` (${w.part === 'anchor' ? 'anchor page of the work' : w.part})`)))
      : h('p', { class: 'subline' }, 'No lab work group reaches this page.'));
}

// Publications

function publicationBlock(pub, i) {
  const f = pub.fields;
  const dl = h('dl', { class: 'fields' });
  const ctx = (label, agree, pd = null) => ({ kind: 'publication', label, pub, agree, pd });
  row(dl, 'Publisher', valueCell(f.publisher, `p${i}-publisher-0`, pub.id, ctx('Publisher', ['publisher', 0])));
  row(dl, f.places.length > 1 ? 'Places' : 'Place', f.places.length
    ? f.places.map((place, j) => h('div', {},
      valueCell(place, `p${i}-place-${j}`, pub.id, ctx('Place', ['place', j], pub.placeDecisions[j])),
      placeState(pub.placeDecisions[j], `p${i}-pd-${j}`)))
    : gapCell());
  row(dl, f.translators.length > 1 ? 'Translators' : 'Translator', f.translators.length
    ? f.translators.map((t, j) => valueCell(t, `p${i}-translator-${j}`, pub.id, ctx('Translator', ['translator', j])))
    : gapCell());
  row(dl, 'Extent', valueCell(f.extent, `p${i}-extent-0`, pub.id, ctx('Extent', ['extent', 0])));
  row(dl, 'Language', plainCell(f.language, `p${i}-language-0`, ctx('Language', null)));
  if (f.series.value) row(dl, 'Series', plainCell(f.series, `p${i}-series-0`, ctx('Series', null)));
  return h('article', { class: 'publication', id: `pub-${i}`, dataset: { pub: pub.id } },
    h('div', { class: 'publication-head' },
      h('h3', {}, `${pub.year ?? 'no year recorded'}${pub.imprint ? `, ${pub.imprint}` : ''}`),
      f.editionStatement.value ? h('span', { class: 'muted sans' }, f.editionStatement.value) : null),
    sharedEdition(page.publications) ? null : h('p', { class: 'state' }, editionState(pub.editionAssignment)),
    h('div', { class: 'pub-print', dataset: { pub: pub.id }, hidden: true }),
    pub.passageLocated ? null : h('p', { class: 'note' }, 'The passage of this publication is not located in the source text.'),
    dl,
    pub.reviewFlags.length ? h('ul', { class: 'note' }, pub.reviewFlags.map(flag => h('li', {}, FLAG_TEXT[flag.code] || flag.code))) : null);
}

const FLAG_TEXT = {
  'missing-location': 'The publication header names no place.',
  'imprint-segments-unresolved': 'Publisher and place cannot be separated with certainty in the source wording of the header.',
  'contents-pagination-exceeds-extent': 'Page numbers in the contents exceed the extent.',
};

/** Edition assignment: the state word at the heading, the short producer beside it. */
function editionState(ea) {
  const word = ea.state === 'contested' ? h('b', { class: 'contested-word' }, 'contested') : h('b', {}, ea.state);
  const rest = editionStateText(ea).slice(ea.state.length);
  return ['Edition assignment: ', word, rest];
}

/**
 * Defaults of the page stated once (exceptions before defaults): the origin
 * "rule", places without a Wikidata decision, the meaning of a gap.
 */
function defaultsNote(pubs) {
  const undecided = pubs.flatMap(p => p.placeDecisions).filter(d => d && !d.decision).length;
  const lines = [
    'Every value comes from the wiki text through an extraction rule unless it is marked otherwise.',
    undecided ? `${plural(undecided, 'place has', 'places have')} no Wikidata decision and no link; only decided places show a state.` : null,
    `"${NO_VALUE}" means a gap in the source and a value not extracted are not yet distinguished.`,
  ];
  const shared = sharedEdition(pubs);
  return [
    h('p', { class: 'note' }, lines.filter(Boolean).join(' ')),
    shared ? h('p', { class: 'state' }, 'Every publication on this page: ', editionState(shared)) : null,
  ];
}

/** The edition assignment all publications of a page share, stated once; null where they differ. */
function sharedEdition(pubs) {
  if (pubs.length < 2) return null;
  const first = editionStateText(pubs[0].editionAssignment);
  return pubs.every(p => editionStateText(p.editionAssignment) === first) ? pubs[0].editionAssignment : null;
}

function row(dl, label, cell) {
  dl.append(h('dt', {}, label), h('dd', {}, cell));
}

function gapCell() {
  return h('span', { class: 'gap' }, NO_VALUE);
}

function plainCell(field, key, ctx) {
  if (field.value === null || field.value === '') return gapCell();
  const line = h('span', { class: 'value-line' },
    h('span', { class: 'value-plain' }, String(field.value)),
    originWord(field.origin));
  if (!ctx) return line;
  const panel = provenancePanel(field, key, ctx);
  line.append(panel.button);
  return h('div', { class: 'value-cell' }, line, panel.body);
}

/** Only an origin other than the page default "rule" is shown beside a value. */
function originWord(origin) {
  return origin && origin !== 'regex' && ORIGIN[origin] ? h('span', { class: 'origin' }, ORIGIN[origin]) : null;
}

/** A value as a button that marks its occurrences, with origin, occurrence notes and its provenance chain. */
function valueCell(field, key, ownPubId, ctx) {
  if (field.value === null || field.value === '') {
    return ctx?.kind === 'record' && field.verificationCandidate ? candidateCell(field, key, ctx) : gapCell();
  }
  const occ = field.occurrences;
  const btn = h('button', {
    type: 'button', class: 'value-btn', 'aria-pressed': 'false', dataset: { key },
    onclick: () => select(btn.getAttribute('aria-pressed') === 'true' ? null : key),
  }, String(field.value));
  valueIndex.set(key, { field, ownPubId, button: btn });
  const panel = ctx ? provenancePanel(field, key, ctx) : null;
  const wrap = h('div', { class: 'value-cell' },
    h('span', { class: 'value-line' }, occ ? btn : h('span', { class: 'value-plain' }, String(field.value)), originWord(field.origin), panel?.button));
  if (occ) {
    const multi = occ.parts.length > 1;
    if (occ.noExactOccurrence) wrap.append(h('p', { class: 'part-results' }, NO_EXACT));
    else if (multi) {
      wrap.append(h('ul', { class: 'part-results' }, occ.parts.map(p => h('li', {},
        `"${p.part}": `, p.noExactOccurrence ? NO_EXACT : plural(p.occurrences.length, 'occurrence', 'occurrences')))));
    }
  }
  wrap.append(h('div', { class: 'inline-passage', 'data-for': key, hidden: true }), panel?.body);
  return wrap;
}

/**
 * A page-level gap for which the verification stage reported a string in the
 * raw text (S5.1): the gap stays the value, the candidate is shown with where
 * it stands and can be marked in the source.
 */
function candidateCell(field, key, ctx) {
  const cand = field.verificationCandidate;
  const candKey = `${key}-cand`;
  const occ = cand.occurrences.parts.flatMap(p => p.occurrences);
  const where = [...new Set(occ.map(o => (o.publicationId
    ? `in the passage of the ${page.publications.find(p => p.id === o.publicationId)?.year ?? 'undated'} publication`
    : o.section ? `in the section "${o.section}"${o.lineLabel ? `, line "${o.lineLabel}"` : ''}` : 'outside the publication passages')))];
  const btn = h('button', {
    type: 'button', class: 'value-btn', 'aria-pressed': 'false', dataset: { key: candKey },
    onclick: () => select(btn.getAttribute('aria-pressed') === 'true' ? null : candKey),
  }, cand.value);
  valueIndex.set(candKey, { field: { value: cand.value, occurrences: cand.occurrences }, ownPubId: null, button: btn });
  const panel = provenancePanel(field, key, ctx);
  const quoted = occ.length ? btn : `"${cand.value}"`;
  const place = where.length ? `, ${where.join('; ')}` : ', with no exact occurrence in the plain text';
  return h('div', { class: 'value-cell' },
    h('span', { class: 'value-line' }, gapCell(), panel.button),
    h('p', { class: 'note' }, 'The automatic check reported ', quoted,
      ` in the raw text${place}. No rule and no person adopted it, so it is no value of this record. Whether the source documents a ${ctx.label.toLowerCase()} for the record's publication is for the reader to judge from the marked passage.`),
    h('div', { class: 'inline-passage', 'data-for': candKey, hidden: true }),
    panel.body);
}

/** The "Provenance" control of one value and its panel, filled on first opening (S2.6). */
function provenancePanel(field, key, ctx) {
  const id = `prov-${key}`;
  const body = h('div', { class: 'provenance', id, hidden: true });
  const button = h('button', {
    type: 'button', class: 'linklike prov-btn', 'aria-expanded': 'false', 'aria-controls': id,
    'aria-label': `Provenance of the ${ctx.label.toLowerCase()} ${field.value ?? '(no value recorded)'}`,
    onclick: async () => {
      const open = button.getAttribute('aria-expanded') === 'true';
      button.setAttribute('aria-expanded', String(!open));
      body.hidden = open;
      if (open || body.childElementCount) return;
      body.append(h('p', { class: 'status' }, 'Collecting the steps.'));
      const steps = provenanceSteps({ ...ctx, field, page, meta, print: printFor(ctx, await printFiles) });
      fill(body, h('ol', { class: 'prov-steps' }, steps.map(s => h('li', {}, h('b', {}, `${s.step}: `), s.text))));
    },
  }, 'Provenance');
  return { button, body };
}

const PUB_FIELD_KEYS = { publisher: 'publisher', location: 'places', translator: 'translators' };

/** The print state of one value from the local files; a record value only learns whether they exist. */
function printFor(ctx, files) {
  if (!files || !files.index) return { kind: 'not-compared' };
  if (ctx.kind === 'record' || !ctx.agree) return { kind: 'compared', value: null, entries: [] };
  const pubAgreement = files.agreement?.publications?.[ctx.pub.id];
  if (!pubAgreement) return { kind: 'no-candidate' };
  const [name, index] = ctx.agree;
  const value = pubAgreement.values.find(v => v.field === name && v.index === index) || null;
  const byId = new Map((files.data?.print || []).map(m => [m.printId, m]));
  return { kind: 'compared', value, entries: value ? value.foundIn.map(pid => agreementHit(pid, pubAgreement, byId)) : [] };
}

// Place states

function placeState(pd, key, scope = 'this publication') {
  if (!pd) return null;
  const p = placeStateParts(pd, scope);
  const parts = [];
  if (!p) {
    if (scope !== 'this publication') parts.push(h('p', { class: 'state' }, 'Wikidata link: no decision recorded, no link'));
  } else {
    const qid = pd.qid ? h('a', { href: `https://www.wikidata.org/wiki/${pd.qid}` }, pd.qid) : null;
    const word = p.state === 'contested' ? h('b', { class: 'contested-word' }, 'contested') : h('b', {}, p.state);
    parts.push(h('p', { class: 'state' },
      qid ? ['Wikidata link ', qid] : 'Wikidata link', ': ', word,
      p.warning ? [', ', h('span', { class: 'warn-inline' }, `warning: ${p.warning}`)] : null,
      `, ${p.producer}, ${p.scope}`));
  }
  if (pd.decision) {
    const id = `dr-${key}`;
    const record = decisionRecord(pd, id);
    parts.push(h('button', {
      type: 'button', class: 'linklike', 'aria-expanded': 'false', 'aria-controls': id,
      onclick: event => {
        const open = event.currentTarget.getAttribute('aria-expanded') === 'true';
        event.currentTarget.setAttribute('aria-expanded', String(!open));
        record.hidden = open;
      },
    }, 'Decision record'), record);
  }
  for (const claim of pd.claims || []) {
    if (claim.status !== 'contested') continue;
    const where = shownClaims.get(claim.claimId);
    if (where) {
      parts.push(h('p', { class: 'state' }, 'Wikidata link: ', h('b', { class: 'contested-word' }, 'contested'), `, the readings are shown under ${where} above.`));
    } else {
      shownClaims.set(claim.claimId, scope === 'this publication' ? 'the publication' : 'the page-level record');
      parts.push(contestedClaim(claim));
    }
  }
  return parts.length ? h('div', { class: 'place-state' }, parts) : null;
}

function decisionRecord(pd, id) {
  const d = pd.decision;
  const date = d.date ? `${d.date}${d.dateSource === 'basis text' ? ', taken from the basis sentence' : ''}` : 'no date recorded';
  return h('div', { class: 'decision-record', id, hidden: true },
    h('dl', {},
      h('dt', {}, 'Stored decision'), h('dd', {}, d.storedAction),
      h('dt', {}, 'Producer'), h('dd', {}, pd.producer),
      h('dt', {}, 'Basis'), h('dd', {}, d.basis || 'no basis recorded'),
      h('dt', {}, 'Date'), h('dd', {}, date),
      d.supersedes ? [h('dt', {}, 'Supersedes'), h('dd', {}, d.supersedes)] : null,
      pd.snapshotPublishesLink ? [h('dt', {}, 'Published record links'), h('dd', {}, pd.snapshotPublishesLink)] : null,
      h('dt', {}, 'Evidence'), h('dd', {}, d.evidence.length ? h('ul', {}, d.evidence.map(e => h('li', {}, evidenceRef(e)))) : 'no evidence recorded')),
    h('p', {}, sentence(meta.texts.placeScope)),
    h('p', { class: 'muted' }, 'State and producer follow the provisional mapping from decider strings to producer labels.'));
}

/** Evidence in reader terms; a source occurrence links its page. */
function evidenceRef(e) {
  if (e.kind !== 'source-occurrence') return e.label;
  return ['source occurrence ', String(e.n), ' on ', h('a', { href: `#page=${e.pageId}` }, `page ${e.pageId}`), ` (text ${e.textId})`];
}

function contestedClaim(claim) {
  return h('section', { class: 'contested-block', 'aria-label': 'Contested place link' },
    h('p', {}, 'Wikidata link: ', h('b', { class: 'contested-word' }, 'contested'),
      `. ${plural(claim.readings.length, 'reading is', 'readings are')} recorded; none is shown as the value.`),
    h('div', { class: 'readings' }, claim.readings.map(r => h('div', { class: 'reading' },
      h('h4', {}, r.label),
      h('p', {}, r.object ? h('a', { href: r.object }, r.object.split('/').pop()) : 'no assignment'),
      h('p', { class: 'muted' }, `reading ${r.status}`)))),
    h('h4', {}, 'Evidence'),
    h('ul', { class: 'evidence-list' }, claim.evidence.map(e => h('li', {},
      h('a', { href: `#page=${e.pageId}` }, `page ${e.pageId}`), `, line ${e.line}: `, h('q', {}, e.text)))),
    h('h4', {}, 'Review history'),
    h('ul', { class: 'evidence-list' }, claim.reviewHistory.length
      ? claim.reviewHistory.map(r => h('li', {},
        `${r.action} by ${r.decider}, ${r.date || 'no date recorded'}`,
        r.basis ? `; basis: ${r.basis}` : '',
        r.evidence.length ? ['; evidence: ', r.evidence.map((e, n) => [n ? ', ' : '', evidenceRef(e)])] : ''))
      : h('li', {}, 'no review recorded')),
    h('p', { class: 'muted' }, `Claim ${claim.claimId}`));
}

// Page-level record

function recordBlock() {
  const rec = page.record;
  const pubs = page.publications;
  const dl = h('dl', { class: 'fields' });
  for (const [name, label] of Object.entries(RECORD_LABELS)) {
    const field = rec.fields[name];
    const ctx = { kind: 'record', label, pd: name === 'location' ? page.placeDecision : null, pubFieldKey: PUB_FIELD_KEYS[name] };
    const cell = field.occurrences || field.verificationCandidate
      ? valueCell(field, `r-${name}`, null, ctx)
      : plainCell(field, `r-${name}`, ctx);
    const extra = [];
    if (field.boundary) {
      for (const part of field.boundary.parts) {
        const who = field.boundary.parts.length > 1 ? `"${part.part}" ` : '';
        if (part.result === 'fires') {
          const years = part.heldBy.map(p => p.year ?? 'undated').join(' and ');
          extra.push(h('p', { class: 'warn' }, `${who ? who : 'The value '}occurs only in the passage of the ${years} ${part.heldBy.length > 1 ? 'publications' : 'publication'}.`));
        } else if (part.result === 'outside-publication-passages') {
          extra.push(h('p', { class: 'warn' }, `${who || 'The value '}occurs only outside the publication passages${outsideWhere(field, part.part)}, so it may not describe any publication of this page.`));
        }
      }
    }
    if (field.verification === 'not-found') {
      extra.push(h('p', { class: 'warn' }, sentence(meta.texts.verificationNotFound)));
      const parts = field.occurrences?.parts || [];
      if (parts.length > 1 && parts.every(p => !p.noExactOccurrence)) {
        extra.push(h('p', { class: 'note' }, sentence(meta.texts.verificationWholeValue)));
      }
    }
    if (name === 'location' && page.placeDecision) extra.push(placeState(page.placeDecision, 'r-pd', 'this record'));
    row(dl, label, [cell, extra]);
  }
  return h('section', { class: 'record-block', 'aria-labelledby': 'rec-h' },
    h('h2', { class: 'section-label', id: 'rec-h' }, 'Page-level record'),
    h('p', { class: 'note' }, sentence(meta.texts.record)),
    pubs.length ? null : h('p', { class: 'note' }, 'Every value comes from the wiki text through an extraction rule unless it is marked otherwise.'),
    h('p', { class: 'note' }, boundarySentence(pubs)),
    dl);
}

/** Where an occurrence outside every passage stands: the compiler's section and line label. */
function outsideWhere(field, part) {
  const occ = (field.occurrences?.parts || []).find(p => p.part === part)?.occurrences.find(o => !o.publicationId);
  if (!occ || !occ.section) return '';
  return `, in the section "${occ.section}"${occ.lineLabel ? `, line "${occ.lineLabel}"` : ''}`;
}

function boundarySentence(pubs) {
  const check = page.boundaryCheck;
  const year = page.record.fields.year.value;
  if (!pubs.length) {
    return page.severalYearsWithoutBreakdown
      ? sentence(meta.texts.severalYears)
      : 'The page has no publication breakdown, so the boundary check does not apply.';
  }
  if (!check.run) {
    if (check.reason === 'record-year-matches-no-publication') {
      return `The record's year ${year} matches no publication, so the boundary check does not run.`;
    }
    return BOUNDARY_REASONS[check.reason] || `The boundary check does not run (${check.reason}).`;
  }
  if (check.sharedYear) {
    return `Boundary check: ${check.yearPublications.length} publications share the record's year ${year}; a value found in the passage of any of them passes.`;
  }
  return `Boundary check: values are compared with the passage of the ${year} publication, which supplies the record's year.`;
}

// Source text and marks

function sourcePane() {
  const src = page.source;
  const restored = src.restoredRevision;
  const head = h('p', { class: 'source-head' },
    `${sentence(meta.texts.source).slice(0, -1)} ${page.pageId}, text ${src.textId}. The revision id of the text is not in the lab data.`);
  return h('section', { class: 'source-pane', 'aria-labelledby': 'src-h' },
    h('h2', { class: 'section-label', id: 'src-h' }, 'Source text'),
    head,
    restored ? h('p', { class: 'source-head' },
      `Restored: ${meta.texts.restored}, revision ${restored.humanRevision?.revisionId} of ${restored.humanRevision?.timestamp?.slice(0, 10)} by ${restored.humanRevision?.actor}. Later fixer revisions: ${restored.fixerRevisions?.length ?? 0}.`) : null,
    h('p', { class: 'status', id: 'mark-status', role: 'status' }),
    h('div', { class: 'source-text', id: 'source-text', lang: page.languageCode || null }, renderText(src.text, [])),
    printPane());
}

/** Text split at passage and mark boundaries; marks carry a visible label. */
function renderText(text, marks, { from = 0, to = text.length } = {}) {
  const passages = page.publications
    .filter(p => p.textStart !== null && p.textEnd !== null)
    .map(p => ({ start: p.textStart, end: p.textEnd, id: p.id }));
  const cuts = new Set([from, to]);
  for (const p of passages) { cuts.add(p.start); cuts.add(p.end); }
  for (const m of marks) { cuts.add(m.start); cuts.add(m.end); }
  const points = [...cuts].filter(n => n >= from && n <= to).sort((a, b) => a - b);
  const out = [];
  let current = null;
  for (let k = 0; k < points.length - 1; k++) {
    const [a, b] = [points[k], points[k + 1]];
    if (a === b) continue;
    const passage = passages.find(p => p.start <= a && b <= p.end);
    if (!current || current.passage !== passage) {
      current = { passage, node: passage ? h('span', { class: 'passage', dataset: { pub: passage.id } }) : document.createDocumentFragment() };
      out.push(current.node);
    }
    const mark = marks.find(m => m.start <= a && b <= m.end);
    const chunk = text.slice(a, b);
    if (mark) {
      const label = mark.start === a ? h('span', { class: 'sel-label' }, mark.label) : null;
      current.node.append(label || '', h('mark', { class: 'sel', id: mark.start === a ? `mark-${mark.n}` : null }, chunk));
    } else {
      current.node.append(chunk);
    }
  }
  return out;
}

function marksFor(entry) {
  const rows = [];
  for (const part of entry.field.occurrences.parts) {
    for (const o of part.occurrences) rows.push({ ...o, part: part.part });
  }
  rows.sort((a, b) => (b.own - a.own) || (a.start - b.start));
  const years = new Map(page.publications.map(p => [p.id, p.year]));
  return rows.map((o, n) => ({
    ...o,
    n,
    label: `selected value ${n + 1} of ${rows.length}${o.own ? ', own passage' : o.publicationId ? `, passage of ${years.get(o.publicationId) ?? 'undated'}` : ', outside the publication passages'}`,
  }));
}

function select(key, { fromHash = false } = {}) {
  if (!page) return;
  const entry = key ? valueIndex.get(key) : null;
  for (const [k, v] of valueIndex) v.button.setAttribute('aria-pressed', String(k === key && !!entry));
  document.querySelectorAll('.inline-passage').forEach(el => { el.hidden = true; el.replaceChildren(); });
  document.querySelectorAll('.publication.is-current, .passage.is-current').forEach(el => el.classList.remove('is-current'));
  const status = document.getElementById('mark-status');
  const textBox = document.getElementById('source-text');
  const marks = entry ? marksFor(entry) : [];
  textBox.replaceChildren(...renderText(page.source.text, marks));

  if (!fromHash) {
    const params = readHash();
    if (entry) params.set('sel', key); else params.delete('sel');
    writeHash(params, { replace: true });
  }
  if (!entry) { status.textContent = ''; return; }

  const value = String(entry.field.value);
  if (entry.ownPubId) {
    document.querySelector(`.publication[data-pub="${CSS.escape(entry.ownPubId)}"]`)?.classList.add('is-current');
    textBox.querySelector(`.passage[data-pub="${CSS.escape(entry.ownPubId)}"]`)?.classList.add('is-current');
  }
  status.textContent = marks.length
    ? `"${value}": ${plural(marks.length, 'occurrence', 'occurrences')} marked. Esc clears the mark.`
    : `"${value}": ${NO_EXACT}.`;

  const inline = document.querySelector(`.inline-passage[data-for="${CSS.escape(key)}"]`);
  if (inline) {
    inline.hidden = false;
    if (marks.length) {
      const first = marks[0];
      const pub = page.publications.find(p => p.id === first.publicationId);
      const [from, to] = pub ? [pub.textStart, pub.textEnd] : excerptBounds(page.source.text, first);
      inline.append(
        h('p', { class: 'source-head' }, `Source passage of the first occurrence${marks.length > 1 ? `; ${marks.length - 1} more in the source text` : ''}`),
        h('div', { class: 'source-text' }, renderText(page.source.text, [first], { from, to })));
    } else {
      inline.append(h('p', { class: 'part-results' }, NO_EXACT));
    }
  }
  const pane = document.querySelector('.source-pane');
  const target = textBox.querySelector('#mark-0');
  if (target && pane && pane.scrollHeight > pane.clientHeight) {
    const top = target.getBoundingClientRect().top - pane.getBoundingClientRect().top + pane.scrollTop;
    pane.scrollTop = Math.max(0, top - 48);
  }
}

/** The source line around an occurrence outside every passage, cut at word boundaries where the line is long. */
function excerptBounds(text, mark) {
  let from = text.lastIndexOf('\n', mark.start - 1) + 1;
  let to = text.indexOf('\n', mark.end);
  if (to === -1) to = text.length;
  if (mark.start - from > 240) from = Math.min(mark.start, text.indexOf(' ', mark.start - 200) + 1);
  if (to - mark.end > 240) to = Math.max(mark.end, text.lastIndexOf(' ', mark.end + 200));
  return [from, to];
}

// Citation and export

function citeTargets() {
  const targets = [{ id: 'page', label: `Page ${page.pageId}, the page-level record` }];
  page.publications.forEach((p, i) => targets.push({ id: String(i), label: `Publication ${p.year ?? 'undated'}, ${p.imprint || p.id}` }));
  return targets;
}

function toolsRow() {
  const select = h('select', { id: 'cite-target' }, citeTargets().map(t => h('option', { value: t.id }, t.label)));
  const field = h('textarea', { id: 'cite-text', readonly: true, rows: 4 });
  const status = h('p', { class: 'status', role: 'status' });
  const update = () => { field.value = citeText(select.value); };
  select.addEventListener('change', update);
  update();
  const exportAs = kind => {
    const target = select.value;
    const stem = target === 'page' ? `klawiter-lab-page-${page.pageId}` : `klawiter-lab-${page.publications[Number(target)].id.split('/').pop()}`;
    const ctx = exportContext(target);
    const [text, ext, type] = kind === 'bib' ? [bibtex(ctx), 'bib', 'application/x-bibtex']
      : kind === 'ris' ? [ris(ctx), 'ris', 'application/x-research-info-systems']
        : [JSON.stringify(jsonExport(ctx), null, 2), 'json', 'application/json'];
    download(`${stem}.${ext}`, text, type);
    status.textContent = `Downloaded ${stem}.${ext}.`;
  };
  return h('div', { class: 'tool-row' },
    h('section', { 'aria-labelledby': 'cite-h' },
      h('h2', { class: 'section-label', id: 'cite-h' }, 'Cite and export'),
      h('label', { for: 'cite-target' }, 'Cite or export '), select,
      h('label', { class: 'visually-hidden', for: 'cite-text' }, 'Citation'),
      field,
      h('div', { class: 'actions' },
        h('button', { type: 'button', class: 'btn', onclick: () => copyText(field.value, field, status) }, 'Copy citation'),
        h('button', { type: 'button', class: 'btn', onclick: () => exportAs('bib') }, 'BibTeX'),
        h('button', { type: 'button', class: 'btn', onclick: () => exportAs('ris') }, 'RIS'),
        h('button', { type: 'button', class: 'btn', onclick: () => exportAs('json') }, 'JSON')),
      status),
    h('section', { 'aria-label': 'Data state' }, dataStateBlock(page.dataState),
      h('p', { class: 'note' }, 'Every export carries origin, state and producer of its values in a note field (BibTeX, RIS) or as fields (JSON).')));
}

function targetHash(target) {
  return target === 'page' ? `page=${page.pageId}` : `page=${page.pageId}&pub=${encodeURIComponent(page.publications[Number(target)].id)}`;
}

function citeText(target) {
  const url = citeUrl('judge.html', targetHash(target));
  if (target === 'page') {
    return citation({ what: `"${page.title}", wiki page ${page.pageId}, page-level record`, identifier: `klawiter page ${page.pageId}`, url, state: page.dataState });
  }
  const pub = page.publications[Number(target)];
  return citation({ what: `"${pub.title || page.title}", ${pub.imprint || 'imprint not recorded'}, ${pub.year ?? 'no year recorded'}, publication on wiki page ${page.pageId}`, identifier: pub.id, url, state: page.dataState });
}

/** What the export formats of record-export.js need from this view. */
function exportContext(target) {
  return {
    page, meta, target,
    url: citeUrl('judge.html', targetHash(target)),
    accessed: accessDate(),
    zweigAuthored: typeof ZWEIG_AUTHOR_TYPES !== 'undefined' && ZWEIG_AUTHOR_TYPES.includes(page.entryType),
  };
}

// Print volumes (E6, local run only)

const ROUTES = {
  alignment: 'text alignment',
  field: 'field match (title, year and a second field)',
  'title-year': 'title and year',
};

function printPane() {
  return h('section', { class: 'print-pane', id: 'print-pane', 'aria-labelledby': 'print-h' },
    h('h2', { class: 'section-label', id: 'print-h' }, 'Print volumes, local only'),
    h('p', { class: 'status', role: 'status' }, 'Looking for local print matches.'));
}

/** Wording for an alignment match; a label in the file wins, else the spec's thresholds, never the score. */
function alignmentWords(m) {
  if (m.label) return m.label;
  const seen = m.firstSeen ? m.firstSeen.slice(0, 10) : 'unknown date';
  if (m.score >= 0.9) return `near-verbatim in a wiki revision of ${seen}`;
  if (m.score >= 0.8) return `largely the same wording in a wiki revision of ${seen}`;
  return `partial text alignment with a wiki revision of ${seen}`;
}

function printMatch(m) {
  return h('li', {},
    h('p', {}, h('b', {}, `${volumeWords(m)}${m.address ? `, PDF page ${m.pdfPage}` : ''}`)),
    h('p', { class: 'state' }, h('b', {}, 'proposed'), `, by ${ROUTES[m.route] || m.route}`,
      m.route === 'alignment' ? `: ${alignmentWords(m)}` : ''),
    h('div', { class: 'source-text print-text' }, m.text));
}

/** A local file, or null where the published lab has none. */
async function loadLocal(path) {
  try {
    const resp = await fetch(path);
    return resp.ok ? await resp.json() : null;
  } catch {
    return null;
  }
}

const FIELD_LIMIT = 5;
const VALUE_FIELDS = { publisher: 'Publisher', place: 'Place', translator: 'Translator', extent: 'Extent' };

function volumeWords(m) {
  const volume = m.volume === 'I' ? 'Volume I' : m.volume === 'A1' ? 'Addendum I' : m.volume === 'A2' ? 'Addendum II' : `Volume ${m.volume}`;
  return `${volume}, ${m.address || `PDF page ${m.pdfPage}`}`;
}

/** S6.2: one line per value of a publication with candidate print entries. */
function agreementLines(pubAgreement, byId) {
  return h('ul', { class: 'agreement' }, pubAgreement.values.map(v => {
    const label = `${VALUE_FIELDS[v.field]} "${v.value}": `;
    if (!v.foundIn.length) {
      return h('li', {}, label, `not found in exactly this form in the matched print ${pubAgreement.entries.length > 1 ? 'entries' : 'entry'}; the print may spell it differently or its extracted text may be faulty, so this is no disagreement`);
    }
    const hits = v.foundIn.map(id => agreementHit(id, pubAgreement, byId));
    return h('li', {}, label, `also in print, ${hits.join('; ')}; the value stands in that entry, which does not show that it describes this publication there; consistency within the compiler's work, not independent support`);
  }));
}

function agreementHit(id, pubAgreement, byId) {
  const entry = pubAgreement.entries.find(e => e.printId === id);
  const route = entry.route === 'field' ? 'field match' : 'text alignment';
  const several = entry.candidates > 1 ? `, one of ${entry.candidates} candidate editions` : '';
  return `${volumeWords(byId.get(id))} (proposed, ${route}${several})`;
}

/**
 * The per-page files docs/lab/local/print/<pageId>.json and
 * docs/lab/local/agreement/<pageId>.json, written by pipeline/lab/
 * split_print_links.py and print_agreement.py. Git ignores both because the
 * print rights are unresolved; a published lab has neither.
 */
async function loadPrint() {
  const pane = document.getElementById('print-pane');
  const status = pane.querySelector('.status');
  // The index names the pages that have a print file, so absent files are not requested.
  printFiles = loadLocal('local/print/index.json').then(async index => {
    if (!index || !index.perPage?.[page.pageId]) return { index, data: null, agreement: null };
    const [data, agreement] = await Promise.all([
      loadLocal(`local/print/${page.pageId}.json`),
      loadLocal(`local/agreement/${page.pageId}.json`),
    ]);
    return { index, data, agreement };
  });
  const { index, data, agreement } = await printFiles;
  const state = printPaneState(!!index, data);
  if (state.kind !== 'matches') {
    status.textContent = state.sentence;
    return;
  }
  const byId = new Map(data.print.map(m => [m.printId, m]));
  const attached = id => agreement?.attachments?.[id]?.publicationIds || [];
  const candidatesOf = m => [...(m.publicationIds || []), ...(m.route === 'alignment' ? attached(m.printId) : [])];
  const own = new Set(page.publications.map(p => p.id));
  for (const block of document.querySelectorAll('.pub-print')) {
    const matches = data.print.filter(m => m.route !== 'title-year' && candidatesOf(m).includes(block.dataset.pub));
    if (!matches.length) continue;
    block.hidden = false;
    const pubAgreement = agreement?.publications?.[block.dataset.pub];
    fill(block,
      h('ul', { class: 'rows' }, matches.map(m => {
        const n = candidatesOf(m).length;
        const byLab = !(m.publicationIds || []).length;
        return h('li', {},
          h('p', {}, h('b', {}, volumeWords(m))),
          h('p', { class: 'state' }, h('b', {}, 'proposed'), `, ${m.route === 'field' ? 'field match' : `text alignment, ${alignmentWords(m)}`}, candidate for this edition${n > 1 ? `, one of ${n} candidate editions` : ''}${byLab ? ', attached by a lab rule (word overlap with this passage), not reviewed' : ''}`),
          h('div', { class: 'source-text print-text' }, m.text));
      })),
      pubAgreement ? agreementLines(pubAgreement, byId) : null);
  }
  const pageLevel = data.print.filter(m => !candidatesOf(m).some(id => own.has(id)));
  const alignment = pageLevel.filter(m => m.route === 'alignment');
  const field = pageLevel.filter(m => m.route === 'field');
  const noisy = pageLevel.filter(m => m.route === 'title-year');
  status.replaceWith(add(document.createDocumentFragment(),
    h('p', { class: 'print-notice' }, 'Local and unpublished, the rights to the print volumes are unresolved. Every match is proposed, none is confirmed. The print text is shown as extracted, its encoding is not corrected.'),
    alignment.length ? h('ul', { class: 'rows' }, alignment.map(printMatch)) : null,
    field.length > FIELD_LIMIT
      ? h('details', { class: 'group' },
        h('summary', {}, `${plural(field.length, 'field match', 'field matches')} at page level, not reviewed, often unrelated on work and collection pages`),
        h('ul', { class: 'rows' }, field.map(printMatch)))
      : field.length ? h('ul', { class: 'rows' }, field.map(printMatch)) : null,
    noisy.length ? h('details', { class: 'group' },
      h('summary', {}, `${plural(noisy.length, 'match', 'matches')} by title and year alone, noisy`),
      h('ul', { class: 'rows' }, noisy.map(printMatch))) : null));
}

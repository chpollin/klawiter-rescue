/**
 * Prototype 3, Record history (knowledge/lab-frontend.md, E4, blog explainer).
 *
 * Route: history.html#page=<id>[&stage=<1..6>] for one card, or &all=1 for the
 * text version of every card. The start state shows the finished record, so
 * a reader who does not step through still sees origins and states.
 *
 * The stages are assembled from the page file, meta.json and the page's
 * `history` block, so every page has a history. Values after the parse stage
 * are reconstructed from the published origins and marked as such.
 */

import {
  loadJSON, h, fill, readHash, writeHash, dataStateBlock, initHeader, errorBlock, plural,
} from './lab.js';
import { placeStateText } from './labels.js';

const main = document.getElementById('main');
const LABELS = {
  title: 'Title', year: 'Year', publisher: 'Publisher', location: 'Place',
  language: 'Language', translator: 'Translator', pageCount: 'Page count', locationSameAs: 'Wikidata link of the place',
};
const ORIGIN = { regex: 'rule', llm: 'LLM gap fill', editor: 'editor', missing: 'no value recorded' };
const NO_VALUE = 'no value recorded';

let records = null;
let current = null;
let meta = null;
let pendingFocus = null;

initHeader();
window.addEventListener('hashchange', route);
route();

async function referenceRecords() {
  if (records) return records;
  const refs = await loadJSON('reference-records.json');
  const reasons = {
    breakdownBoundaryFires: 'a page-level value belongs to another publication',
    noBreakdownSeveralYears: 'no publication breakdown, several years',
    contestedPlaceRuleValue: 'contested place',
  };
  records = Object.entries(refs.classes).filter(([, c]) => c.pageId)
    .map(([key, c]) => ({ pageId: c.pageId, reason: reasons[key] || key }));
  records.push({ pageId: 448, reason: refs.page448.reason });
  return records;
}

async function route() {
  const params = readHash();
  try {
    const list = await referenceRecords();
    meta = meta || await loadJSON('meta.json');
    const id = Number(params.get('page')) || 448;
    if (!list.some(r => r.pageId === id)) list.push({ pageId: id, reason: 'opened by page id' });
    if (!current || current.pageId !== id) {
      current = buildHistory(await loadJSON(`pages/${id}.json`), meta);
      render(params);
      main.focus({ preventScroll: true });
    } else {
      render(params, { keepFocus: true });
    }
  } catch (error) {
    fill(main, h('h1', {}, 'How a record comes about'), errorBlock(error, route));
  }
}

/** The six stage cards of one record, from the page view and meta.json. */
function buildHistory(page, m) {
  const rec = page.record.fields;
  const facts = page.history || {};
  const base = m.baseline;
  const llmFields = Object.keys(rec).filter(f => rec[f].origin === 'llm');
  const afterParse = Object.fromEntries(Object.entries(rec).map(([f, v]) => [f, v.origin === 'llm'
    ? { value: null, note: 'empty after the rule stage, reconstructed from the gap-filler contract' }
    : { value: v.value, origin: v.origin, reconstructed: true }]));
  const place = page.placeDecision;
  const changes = (facts.changes || []).map(c => ({ ...c, beforeCommit: base.commit, afterCommit: base.changedIn }));
  let placeActor = 'none, the record has no place';
  if (place?.decision) placeActor = place.producer;
  else if (place) placeActor = `none, no Wikidata decision is recorded for "${place.place}"`;
  return {
    pageId: page.pageId,
    title: page.title,
    dataState: page.dataState,
    stages: [
      { stage: 1, name: 'Wiki text', actor: 'MediaWiki dump, current revision of the page',
        values: { textId: page.source.textId, textLength: page.source.text.length, restoredRevision: page.source.restoredRevision },
        notStored: ['the raw wikitext with markup is not published; the lab shows the plain text the pipeline derived from it', m.texts.sliceHash] },
      { stage: 2, name: 'Repair', actor: 'rule (encoding repair)', values: { encodingRepaired: facts.encodingRepaired || [] },
        summary: 'no change on this record recorded', notStored: ['the text and values before repair are not published'] },
      { stage: 3, name: 'Parse', actor: 'rule', values: afterParse, publications: page.publications.length,
        notStored: ['intermediate stage outputs are regenerable and not tracked; the values after this stage are reconstructed from the published origins'] },
      { stage: 4, name: 'Fill gaps', actor: `LLM ${m.llm.model}, answers frozen on ${String(m.llm.frozenAt).slice(0, 10)}`,
        promptTemplateSha256: m.llm.promptSha256, values: Object.fromEntries(llmFields.map(f => [f, rec[f]])),
        summary: 'no value of this record is an LLM gap fill', notStored: [m.llmNotStored] },
      { stage: 5, name: 'Link places', actor: placeActor,
        values: place, notStored: place?.decision && !place.decision.date ? ['no decision date recorded'] : [] },
      { stage: 6, name: 'Published record', actor: 'pipeline stages 05 and 06, patch replay',
        values: rec,
        editorFields: Object.keys(rec).filter(f => rec[f].origin === 'editor'),
        changesSinceBaseline: changes,
        baseline: { commit: base.commit, commitDate: base.commitDate, changedIn: base.changedIn, changedInDate: base.changedInDate,
          note: base.commit ? 'baseline is the published data before the last commit that changed the published records' : 'no baseline available' } },
    ],
  };
}

function value(v) {
  if (v === null || v === undefined || v === '') return h('span', { class: 'gap' }, NO_VALUE);
  return h('span', { class: 'value-plain' }, String(v));
}

function originWord(origin) {
  return origin && ORIGIN[origin] ? h('span', { class: 'origin' }, ` ${ORIGIN[origin]}`) : null;
}

function dateOf(commit) {
  const b = current.stages[5].baseline;
  if (commit === b.commit) return b.commitDate;
  if (commit === b.changedIn) return b.changedInDate;
  return null;
}

function commitRef(commit) {
  const date = dateOf(commit);
  return `commit ${commit.slice(0, 7)}${date ? ` of ${date}` : ''}`;
}

/** Which stage card a change belongs to: LLM involvement to 4, the place link to 5, the rest to 3. */
function stageOfChange(change) {
  if (change.field === 'locationSameAs') return 5;
  if (change.before?.origin === 'llm' || change.after?.origin === 'llm') return 4;
  return 3;
}

function changeBlock(change) {
  const b = change.before || {};
  const a = change.after || {};
  return h('div', { class: 'change' },
    h('p', {}, h('b', {}, LABELS[change.field] || change.field), ' changed in the regeneration after the October pipeline fixes.'),
    h('p', {}, 'Before: ', value(b.value), originWord(b.origin), h('span', { class: 'muted sans' }, `, ${commitRef(change.beforeCommit)}`)),
    h('p', {}, 'After: ', value(a.value), originWord(a.origin), h('span', { class: 'muted sans' }, `, ${commitRef(change.afterCommit)}`)),
    change.beforeReview ? h('p', { class: 'note' }, `The earlier link was published on the basis of ${change.beforeReview.decider}, as ${change.beforeReview.status}.`) : null);
}

function notStored(list) {
  if (!list || !list.length) return null;
  return h('div', {}, h('h4', {}, 'Not stored'), h('ul', { class: 'evidence-list' }, list.map(t => h('li', {}, `${t[0].toUpperCase()}${t.slice(1)}.`))));
}

function valuesTable(values, { showNotes = false } = {}) {
  return h('dl', { class: 'fields' }, Object.entries(values).map(([field, v]) => [
    h('dt', {}, LABELS[field] || field),
    h('dd', {},
      v.note ? h('span', { class: 'gap' }, v.note) : [value(v.value), originWord(v.value === null || v.value === '' ? null : v.origin),
        v.reconstructed && v.value !== null ? h('span', { class: 'origin' }, ', reconstructed') : null],
      showNotes && v.verification === 'not-found' ? h('p', { class: 'warn' }, 'The automatic check did not find this value in the raw text. The check covers page-level values only.') : null,
      showNotes && v.boundary?.fires ? v.boundary.parts.filter(p => p.result === 'fires').map(p => h('p', { class: 'warn' },
        `"${p.part}" occurs only in the passage of the ${p.heldBy.map(x => x.year).join(' and ')} publication.`)) : null),
  ]));
}

function placeSentence(pd) {
  if (!pd) return h('p', {}, 'The record has no place, so no link is decided.');
  return h('p', { class: 'state' }, placeStateText(pd, 'this record'));
}

function stageBody(stage, changes) {
  const v = stage.values;
  const own = changes.filter(c => stageOfChange(c) === stage.stage);
  const parts = [];
  switch (stage.stage) {
    case 1:
      parts.push(h('dl', { class: 'fields' },
        h('dt', {}, 'Text'), h('dd', {}, `text ${v.textId}, ${plural(v.textLength, 'character', 'characters')} of plain text`),
        h('dt', {}, 'Revision'), h('dd', {}, v.restoredRevision
          ? `restored human revision ${v.restoredRevision.humanRevision?.revisionId} of ${v.restoredRevision.humanRevision?.timestamp?.slice(0, 10)}, from before a Redirect fixer overwrite`
          : 'the current revision of the page; its revision id is not in the lab data')),
      h('p', {}, h('a', { href: `judge.html#page=${current.pageId}` }, 'Read the source text in the record view')));
      break;
    case 2:
      parts.push(v.encodingRepaired.length
        ? h('p', {}, `Repaired encoding in: ${v.encodingRepaired.join(', ')}.`)
        : h('p', {}, `${stage.summary[0].toUpperCase()}${stage.summary.slice(1)}.`));
      break;
    case 3:
      parts.push(h('p', {}, `The rules split the page into ${plural(stage.publications, 'publication', 'publications')} and read the page-level record:`), valuesTable(v));
      break;
    case 4:
      parts.push(h('p', { class: 'sans' }, `Prompt template hash: `, h('code', {}, stage.promptTemplateSha256)));
      if (Object.keys(v).length) parts.push(h('p', {}, 'The LLM filled these values that were empty after the rule stage:'), valuesTable(v, { showNotes: true }));
      else if (own.length) parts.push(h('p', {}, 'In the current data no value of this record is an LLM gap fill. The regeneration changed this:'));
      else parts.push(h('p', {}, `${stage.summary[0].toUpperCase()}${stage.summary.slice(1)} in the current data.`));
      break;
    case 5:
      parts.push(placeSentence(v));
      if (v?.decision) {
        parts.push(h('dl', { class: 'fields' },
          h('dt', {}, 'Producer'), h('dd', {}, v.producer),
          h('dt', {}, 'Basis'), h('dd', {}, v.decision.basis || 'no basis recorded'),
          h('dt', {}, 'Date'), h('dd', {}, v.decision.date || 'no date recorded')));
        parts.push(h('p', { class: 'note' }, `${meta.texts.placeScope[0].toUpperCase()}${meta.texts.placeScope.slice(1)}.`));
      }
      for (const claim of v?.claims || []) {
        if (claim.status !== 'contested') continue;
        parts.push(h('div', { class: 'contested-block' },
          h('p', {}, 'Readings, none shown as the value:'),
          h('ul', { class: 'evidence-list' }, claim.readings.map(r => h('li', {}, `${r.label}${r.object ? ` (${r.object.split('/').pop()})` : ''}`)))));
      }
      if (own.length) parts.push(h('p', { class: 'note' }, meta.fixtureDemotion));
      break;
    case 6:
      parts.push(valuesTable(v, { showNotes: true }));
      parts.push(stage.editorFields.length
        ? h('p', {}, `Corrected by an editor: ${stage.editorFields.map(f => LABELS[f] || f).join(', ')}.`)
        : h('p', {}, 'No field of this record was corrected by an editor.'));
      if (changes.length) {
        parts.push(h('h4', {}, 'Changes of the regeneration'), changes.map(changeBlock));
      } else {
        parts.push(h('p', {}, 'The regeneration after the October pipeline fixes changed nothing on this record.'));
      }
      parts.push(h('p', { class: 'note' }, `${stage.baseline.note[0].toUpperCase()}${stage.baseline.note.slice(1)}.`));
      break;
    default:
      break;
  }
  if (stage.stage !== 6 && own.length) parts.push(own.map(changeBlock));
  parts.push(notStored(stage.notStored));
  return parts;
}

function actorLine(stage) {
  let actor = stage.actor;
  if (stage.stage === 4) actor = actor.replace(/(\d{4}-\d{2}-\d{2})T[^,]*/, '$1');
  return h('p', { class: 'actor' }, h('span', { class: 'muted' }, 'Actor: '), actor);
}

function card(stage, changes, { headingLevel = 'h2', id = null } = {}) {
  return h('section', { class: 'stage-card', id, 'aria-labelledby': `${id || 'card'}-h-${stage.stage}` },
    h(headingLevel, { id: `${id || 'card'}-h-${stage.stage}` }, `${stage.stage} ${stage.name}`),
    actorLine(stage),
    stageBody(stage, changes));
}

function finishedRecord(changes) {
  const final = current.stages[5];
  const place = current.stages[4].values;
  return h('section', { class: 'finished', 'aria-labelledby': 'fin-h' },
    h('h2', { id: 'fin-h' }, 'The finished record'),
    valuesTable(final.values, { showNotes: true }),
    placeSentence(place),
    changes.length ? h('p', { class: 'note' }, `${plural(changes.length, 'value was', 'values were')} changed by the regeneration after the October pipeline fixes; the stages show where.`) : null);
}

function render(params, { keepFocus = false } = {}) {
  const changes = current.stages[5].changesSinceBaseline || [];
  const all = params.has('all');
  const stageNo = Math.min(6, Math.max(1, Number(params.get('stage')) || 1));
  document.title = `${current.title}, Record history, Klawiter Bibliography Lab`;

  const picker = h('select', { id: 'record', onchange: () => {
    const next = new URLSearchParams();
    next.set('page', picker.value);
    if (all) next.set('all', '1');
    writeHash(next);
    route();
  } }, records.map(r => h('option', { value: r.pageId, selected: r.pageId === current.pageId || null }, `Page ${r.pageId}: ${r.reason}`)));

  const head = [
    h('h1', {}, 'How a record comes about'),
    h('p', { class: 'prose' }, 'Every core value shows where it comes from. Step through the stages that produced one record, from the wiki text to the published record.'),
    h('div', { class: 'filters' }, h('div', { class: 'field' }, h('label', { for: 'record' }, 'Record'), picker)),
    h('p', { class: 'subline' }, `Page ${current.pageId}, "${current.title}". `, h('a', { href: `judge.html#page=${current.pageId}` }, 'Open in the record view')),
    finishedRecord(changes),
  ];
  const tail = [
    h('section', { class: 'intervene', 'aria-label': 'Where a person can intervene' },
      h('p', {}, 'Where a person can intervene today: field corrections and place decisions in the local edit mode of the production app.')),
    dataStateBlock(current.dataState),
  ];

  if (all) {
    fill(main, head,
      h('p', {}, h('a', { href: `#page=${current.pageId}` }, 'Step through the stages instead')),
      h('div', { class: 'all-cards' }, current.stages.map(s => card(s, changes, { headingLevel: 'h3', id: 'all' }))),
      tail);
    return;
  }

  const tabs = current.stages.map(s => {
    const changed = changes.some(c => stageOfChange(c) === s.stage) || (s.stage === 6 && changes.length);
    return h('button', {
      type: 'button', role: 'tab', id: `tab-${s.stage}`, 'aria-selected': String(s.stage === stageNo),
      'aria-controls': 'stage-panel', tabindex: s.stage === stageNo ? '0' : '-1',
      onclick: () => go(s.stage, false),
    }, `${s.stage} ${s.name}${changed ? ', changed' : ''}`);
  });
  const tablist = h('div', { class: 'stage-tabs', role: 'tablist', 'aria-label': 'Stages' }, tabs);
  tablist.addEventListener('keydown', event => {
    if (event.ctrlKey || event.metaKey || event.altKey) return;
    const keys = { ArrowRight: stageNo + 1, ArrowDown: stageNo + 1, ArrowLeft: stageNo - 1, ArrowUp: stageNo - 1, Home: 1, End: 6 };
    if (!(event.key in keys)) return;
    event.preventDefault();
    go(Math.min(6, Math.max(1, keys[event.key])), true);
  });
  const stage = current.stages[stageNo - 1];
  const panel = h('div', { id: 'stage-panel', role: 'tabpanel', 'aria-labelledby': `tab-${stageNo}`, tabindex: '0' },
    card(stage, changes),
    h('div', { class: 'stage-nav' },
      stageNo > 1 ? h('button', { type: 'button', class: 'btn', onclick: () => go(stageNo - 1, false, 'prev') }, 'Previous') : null,
      stageNo < 6 ? h('button', { type: 'button', class: 'btn', onclick: () => go(stageNo + 1, false, 'next') }, 'Next') : null));
  fill(main, head,
    h('h2', { class: 'section-label' }, 'Stages'),
    tablist, panel,
    h('p', {}, h('a', { href: `#page=${current.pageId}&all=1` }, 'Text version of all stage cards')),
    tail);

  if (keepFocus && pendingFocus) {
    const target = pendingFocus === 'tab' ? document.getElementById(`tab-${stageNo}`)
      : main.querySelector(pendingFocus === 'prev' ? '.stage-nav .btn' : '.stage-nav .btn:last-child');
    (target || document.getElementById(`tab-${stageNo}`))?.focus();
    pendingFocus = null;
  }
}

function go(n, fromKeys, button) {
  const next = readHash();
  next.set('page', current.pageId);
  next.set('stage', String(n));
  pendingFocus = fromKeys ? 'tab' : button || 'tab';
  writeHash(next, { replace: true });
  route();
}

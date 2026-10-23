/**
 * Lab entry and acceptance page. Each user story of knowledge/lab-frontend.md
 * stands with its acceptance criterion and deep links into the views that
 * demonstrate it. The checkboxes are the operator's acceptance marks and
 * persist in localStorage only; nothing else is stored.
 */

import { loadJSON, h, fill, initHeader, dataStateBlock, errorBlock } from './lab.js';

const main = document.getElementById('main');
const STORE = 'klawiter-lab-acceptance';

const PROTOTYPES = [
  { href: 'judge.html#page=448', title: 'Judge a value', covers: 'E2, S3.2', text: 'The record view of one wiki page: publications beside the source text, the page-level record with its boundary check, state with producer, citation and export.', status: null },
  { href: 'find.html', title: 'Find and cite a work', covers: 'E1, E3, E5, S6.1', text: 'A work-centred entry with search, a language facet, the three relations of a work kept apart by their evidence, and the scope and coverage page.', status: null },
  { href: 'history.html#page=448', title: 'Record history', covers: 'E4', text: 'A step-through of the stages that produced a record, from the wiki text to the published record, with the changes of the October regeneration.', status: null },
];

const STORIES = [
  ['S1.1', 'Find a work under any title form', 'Search folds diacritics and umlauts, matches substrings in page titles, publication titles and bracketed original titles, and lists works before single pages.',
    [['find.html#q=netrpelivost', 'search "netrpelivost" finds "Netrpělivost srdce"'], ['find.html#q=ungeduld', 'search "ungeduld": works first, then pages matched by bracketed original title']]],
  ['S1.2', 'See the editions of a work by language and year', 'An indented list with three separately counted parts, pages the compiler linked to the work page, translations the work page lists as text, and pages that cite the original title in brackets, the last marked as found by a lab rule; every count names its unit and opens exactly those records; a page in more than one part is marked in each and counted once in a union total beside the part counts; publications without a recorded language and without a year form their own groups; where no German work page exists the view says so; appearances inside anthologies and collected volumes are not covered, and the scope panel says so.',
    [['find.html#work=lab-work%2F54', 'Ungeduld des Herzens'], ['find.html#work=lab-work%2F6820', 'Schachnovelle'], ['find.html#work=lab-work%2F7460&open=p3-variants', 'Brief einer Unbekannten with the possibly-same-title list'], ['find.html#work=lab-work%2F54&from=1950&to=1990', 'year filter 1950 to 1990']]],
  ['S1.3', 'Know what the work view leaves out', 'The denominator is the set of namespace-0 pages whose entry type belongs to ZWEIG_AUTHOR_TYPES in docs/js/constants.js; the view states how many of these any work view reaches and lists the uncovered pages by kind.',
    [['find.html#scope', 'scope page, section "What the work views leave out"'], ['find.html#list=un.essay', 'essays no work view reaches']]],
  ['S1.4', 'Browse by language', 'A language facet on the start view, with a group for publications whose language is not recorded.',
    [['find.html#lang=Czech', 'Czech'], ['find.html#lang=none', 'language not recorded']]],
  ['S2.1', 'See where a value comes from', 'Matching respects word boundaries and matches each part of a comma-separated value; an occurrence inside the publication\'s own passage is marked first; where no exact occurrence exists the interface says "no exact occurrence, the value may be normalised".',
    [['judge.html#page=448&sel=p0-place-0', 'page 448, place "Praha", own passage first'], ['judge.html#page=1846&sel=r-translator', 'page 1846, a comma-separated translator matched part by part'], ['judge.html#page=530&sel=r-publisher', 'page 530, no exact occurrence']]],
  ['S2.2', 'Notice a page-level value that belongs to another publication', 'The check runs on pages that have a publication breakdown, is deterministic and names the publication whose passage holds the value; where several publications share the record\'s year, a value found in any of them passes; where no publication has the record\'s year, the check does not run and the record says so; on pages without a breakdown that carry more than one year, the record states that its values may come from different publications.',
    [['judge.html#page=42&sel=r-translator', 'page 42, translator occurs only in the 2000 passage'], ['judge.html#page=5', 'page 5, shared year'], ['judge.html#page=9', 'page 9, the record\'s year matches no publication'], ['judge.html#page=90', 'page 90, no breakdown, several years']]],
  ['S2.3', 'See the state of a place link and who produced it', 'Labels follow the provisional mapping and name the object, "Wikidata link Q1085"; the state of each publication\'s edition assignment appears at the publication heading; no state relies on colour.',
    [['judge.html#page=90', 'page 90, confirmed by independent agents'], ['judge.html#page=1741', 'page 1741, confirmed by the main agent'], ['judge.html#page=363', 'page 363, agent review without source occurrence'], ['judge.html#page=87', 'page 87, candidate rejected'], ['judge.html#page=54', 'page 54, confirmed edition assignments'], ['judge.html#page=448', 'page 448, no decision recorded (the fixture decisions no longer occur in the data)']]],
  ['S2.4', 'See where the automatic verification disagrees', 'A value of publisher, place, translator or page count whose verification status is a false positive carries the note "the automatic check did not find this value in the raw text"; the note states that the check covers page-level values only; the status name is not shown.',
    [['judge.html#page=1846', 'page 1846, translator'], ['judge.html#page=103', 'page 103, place']]],
  ['S2.5', 'See competing readings of a contested statement', 'Readings appear side by side with their evidence lines and review history; none is shown as the value; evidence from other pages names its page.',
    [['judge.html#page=4819', 'page 4819, Saint-Aignan']]],
  ['S3.1', 'Cite a record with its data state', 'The citation names the identifier, the Git commit of the data the lab was built from, a short content hash of its inputs and the access date; work groups carry an identifier derived from the anchor page and are labelled as lab-derived; the interface state is addressable by URL.',
    [['judge.html#page=448', 'page and publication citation at the foot of the record'], ['find.html#work=lab-work%2F54', 'work citation at the foot of the work view']]],
  ['S3.2', 'Export with state and producer', 'BibTeX and RIS exports carry state, producer and origin in a note field; the JSON export carries them as fields.',
    [['judge.html#page=90', 'page 90 exports (LLM gap fill, confirmed place link)']]],
  ['S4.1', 'Follow a record through the workflow', 'One card per stage with the record\'s state after it; where the regeneration after the October pipeline fixes changed a value, the card shows both states with their commits; states the artefacts do not hold are named precisely.',
    [['history.html#page=448&stage=4', 'page 448, stage 4 Fill gaps'], ['history.html#page=448&stage=6', 'page 448, stage 6 with the changes of the regeneration']]],
  ['S5.1', 'See coverage per field with its denominator', 'An absent value reads "no value recorded, a gap in the source and a value not extracted are not yet distinguished"; the verification stage\'s count of values it found in the raw text but the record lacks is shown separately; every count names its unit and denominator and opens exactly the counted records.',
    [['find.html#scope', 'coverage table'], ['find.html#list=cov.publisher.noValueRecorded', 'publisher, no value recorded']]],
  ['S5.2', 'Know what the bibliography holds', 'A scope panel reachable from every view that names the printed states, the wiki\'s editing period and the latest publication years it records, what the lab shows, the work grouping rules with their exclusions, and the modelling limits.',
    [['find.html#scope', 'scope panel (header link "Scope" on every view)']]],
  ['S6.1', 'See whether the print volumes have been compared', 'The scope panel states once that the published lab shows wiki data only. In a local run with the optional print file, a page with matches lists them at page level and says that matching is by page and not yet by edition, with volume, address or PDF page and route; alignment labels in words, no score; title-and-year matches behind a collapsed count marked as noisy; a persistent notice that the print data is local and unpublished.',
    [['find.html#scope', 'scope statement'], ['judge.html#page=448', 'print pane of page 448 (local run only)']]],
  ['Cross-cutting', 'Every prototype', 'Works with the keyboard alone, shows a visible focus, conveys no state by colour alone, reflows at 320 px width and 200 % zoom without hiding the source text behind a disclosure, uses English interface text and loads no library or font from a network.',
    [['judge.html#page=4819', 'contested state with word and colour'], ['history.html#page=448', 'tab list with arrow keys']]],
];

function readMarks() {
  try { return JSON.parse(localStorage.getItem(STORE) || '{}'); } catch { return {}; }
}

function writeMarks(marks) {
  try { localStorage.setItem(STORE, JSON.stringify(marks)); } catch { /* storage unavailable: marks last for this visit */ }
}

async function render() {
  const marks = readMarks();
  const stateSlot = h('div', {});
  fill(main, 
    h('h1', {}, 'Klawiter Bibliography Lab'),
    h('p', { class: 'prose' }, 'Three prototypes show the rescued wiki data so that every value can be traced to its source passage, its origin and its review state. They run on the same prepared data and are compared on the same tasks. The lab shows wiki data only.'),
    h('h2', {}, 'Prototypes'),
    h('ul', { class: 'prototypes' }, PROTOTYPES.map(p => h('li', {},
      h('h3', {}, h('a', { href: p.href }, p.title)),
      h('p', { class: 'muted sans' }, `Covers ${p.covers}${p.status ? `, ${p.status}` : ''}`),
      h('p', {}, p.text)))),
    h('h2', {}, 'Data state'),
    stateSlot,
    h('h2', {}, 'Acceptance by user story'),
    h('p', { class: 'note' }, 'Each story with its acceptance criterion and the views that demonstrate it. The marks are kept in this browser only.'),
    h('ol', { class: 'stories' }, STORIES.map(([id, title, criterion, links]) => {
      const box = h('input', { type: 'checkbox', id: `acc-${id}`, checked: marks[id] || null, onchange: () => {
        const next = readMarks();
        if (box.checked) next[id] = true; else delete next[id];
        writeMarks(next);
      } });
      return h('li', {},
        h('div', { class: 'story-head' }, box, h('label', { for: `acc-${id}` }, `${id} ${title}`)),
        h('div', { class: 'story-body' },
          h('p', { class: 'criterion' }, h('span', { class: 'muted' }, 'Acceptance: '), criterion),
          h('ul', { class: 'story-links' }, links.map(([href, text]) => h('li', {}, h('a', { href }, text))))));
    })));
  try {
    const meta = await loadJSON('meta.json');
    const s = meta.dataState;
    fill(stateSlot, 
      h('dl', { class: 'fields' },
        h('dt', {}, 'Data commit'), h('dd', {}, h('code', {}, s.commit), ` (ref ${s.ref})`),
        h('dt', {}, 'Input hash'), h('dd', {}, h('code', {}, s.inputsSha256)),
        h('dt', {}, 'Rules version'), h('dd', {}, s.rulesVersion),
        h('dt', {}, 'Hash rule'), h('dd', {}, meta.inputsHashRule)),
      dataStateBlock(s));
  } catch (error) {
    fill(stateSlot, errorBlock(error, render));
  }
}

initHeader();
render();

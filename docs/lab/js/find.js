/**
 * Prototype 2, Find and cite a work (knowledge/lab-frontend.md, E1, E3, E5, S6.1).
 *
 * Routes, all in the hash so a view is citable:
 *   (none)               start view: works, language facet, year filter
 *   q=<text>             search, works before pages
 *   lang=<language|none> pages and publications in one language (S1.4);
 *                        in the work view the same key filters the rows
 *   from=, to=           year filter
 *   work=<lab-work/id>   work view; open=<group ids> keeps opened groups
 *   scope                scope panel and coverage (S1.3, S5.1, S5.2, S6.1)
 *   list=<key>           exactly the records a coverage count counts
 */

import {
  loadJSON, h, fill, add, readHash, writeHash, fold, typeLabel, dataStateBlock, citation, citeUrl,
  download, copyText, initHeader, errorBlock, yearsSpan, plural,
} from './lab.js';
import { NOT_RECORDED, editionsByLanguage, pageRank, rankWorks } from './editions.js';
import { FIELD_LABELS } from './labels.js';

const main = document.getElementById('main');
const NONE = 'none';
const SEARCH_CAP = 500;
const EXCLUDED_LABELS = {
  'year-or-number': 'with a year or number',
  place: 'naming a place',
  'english-gloss': 'English glosses',
  'several-titles': 'several titles',
};

let index = null;
let pageById = null;

initHeader();
window.addEventListener('hashchange', route);
route();

async function route() {
  const params = readHash();
  // A plain GET from the header form without script lands as ?q=.
  const query = new URLSearchParams(location.search).get('q');
  if (query && !params.has('q')) {
    params.set('q', query);
    history.replaceState(null, '', `${location.pathname}#${params.toString()}`);
  }
  const headerField = document.getElementById('lab-q');
  if (headerField) headerField.value = params.get('q') || '';
  try {
    index = index || await loadJSON('search.json');
    pageById = pageById || new Map(index.pages.map(p => [p.id, p]));
  } catch (error) {
    fill(main, h('h1', {}, 'Find and cite a work'), errorBlock(error, route));
    return;
  }
  try {
    if (params.has('scope')) await renderScope();
    else if (params.has('list')) await renderList(params.get('list'));
    else if (params.has('work')) await renderWork(params);
    else renderStart(params);
  } catch (error) {
    fill(main, h('h1', {}, 'Find and cite a work'), errorBlock(error, route));
  }
}

function focusMain() {
  main.focus({ preventScroll: true });
  window.scrollTo(0, 0);
}

// Filters

function readFilters(params) {
  const num = key => {
    const v = params.get(key);
    return v !== null && v !== '' && Number.isFinite(Number(v)) ? Number(v) : null;
  };
  return { lang: params.get('lang'), from: num('from'), to: num('to') };
}

function filtersActive(f) {
  return f.lang !== null || f.from !== null || f.to !== null;
}

function yearOk(year, f) {
  if (f.from === null && f.to === null) return true;
  if (!Number.isFinite(year)) return false;
  return (f.from === null || year >= f.from) && (f.to === null || year <= f.to);
}

function langOk(language, f) {
  if (f.lang === null) return true;
  if (f.lang === NONE) return !language;
  return language === f.lang;
}

/** Units of a page: its publications, or the page itself where it has no breakdown. */
function unitsOfIndexRow(row) {
  if (row.p) return row.p.map(([id, year, language, imprint]) => ({ id, year, language, imprint }));
  return [{ id: null, years: row.y || [], language: row.l, imprint: null }];
}

function unitOk(unit, f) {
  const years = unit.years || [unit.year];
  return langOk(unit.language, f) && (f.from === null && f.to === null ? true : years.some(y => yearOk(y, f)));
}

function languageOptions() {
  const counts = new Map();
  for (const row of index.pages) {
    for (const u of unitsOfIndexRow(row)) {
      const key = u.language || NONE;
      counts.set(key, (counts.get(key) || 0) + 1);
    }
  }
  return [...counts.entries()].sort((a, b) => (a[0] === NONE) - (b[0] === NONE) || a[0].localeCompare(b[0]));
}

function filterBar(params, { search = true } = {}) {
  const f = readFilters(params);
  const form = h('form', { class: 'filters', role: 'search', 'aria-label': 'Search and filters' });
  const q = h('input', { id: 'f-q', name: 'q', type: 'search', value: params.get('q') || '', autocomplete: 'off' });
  const lang = h('select', { id: 'f-lang', name: 'lang' },
    h('option', { value: '' }, 'any'),
    languageOptions().map(([key]) => h('option', { value: key, selected: f.lang === key }, key === NONE ? 'not recorded' : key)));
  const from = h('input', { id: 'f-from', name: 'from', type: 'number', inputmode: 'numeric', value: f.from ?? '' });
  const to = h('input', { id: 'f-to', name: 'to', type: 'number', inputmode: 'numeric', value: f.to ?? '' });
  add(form, 
    search ? h('div', { class: 'field' }, h('label', { for: 'f-q' }, 'Search titles'), q) : null,
    h('div', { class: 'field' }, h('label', { for: 'f-lang' }, 'Language'), lang),
    h('div', { class: 'field' }, h('label', { for: 'f-from' }, 'Years from'), from),
    h('div', { class: 'field' }, h('label', { for: 'f-to' }, 'to'), to),
    h('button', { class: 'btn btn-primary', type: 'submit' }, search ? 'Search' : 'Apply'),
    filtersActive(f) ? h('button', { class: 'btn', type: 'button', onclick: () => {
      const next = readHash();
      ['lang', 'from', 'to'].forEach(k => next.delete(k));
      writeHash(next);
      route();
    } }, 'Clear filters') : null);
  form.addEventListener('submit', event => {
    event.preventDefault();
    const next = readHash();
    if (search) {
      const text = q.value.trim();
      if (text) next.set('q', text); else next.delete('q');
    }
    for (const [key, field] of [['lang', lang], ['from', from], ['to', to]]) {
      if (field.value !== '') next.set(key, field.value); else next.delete(key);
    }
    if (from.value && to.value && Number(from.value) > Number(to.value)) {
      to.setCustomValidity('The end year lies before the start year.');
      to.reportValidity();
      return;
    }
    to.setCustomValidity('');
    writeHash(next);
    route();
  });
  return form;
}

// Start view, search and language list

function renderStart(params) {
  const f = readFilters(params);
  const q = (params.get('q') || '').trim();
  document.title = 'Find and cite a work, Klawiter Bibliography Lab';
  const content = h('div', {});
  const status = h('p', { class: 'status', role: 'status' });
  fill(main, 
    h('h1', {}, q ? `Search: "${q}"` : f.lang ? `Pages in ${f.lang === NONE ? 'no recorded language' : f.lang}` : 'Find and cite a work'),
    filterBar(params),
    status,
    h('div', { class: 'split' }, content, languageFacet(f)));
  if (q) searchResults(q, f, content, status);
  else if (f.lang) languageList(f, content, status);
  else workList(f, content, status);
  if (!params.has('q')) focusMain();
}

function languageFacet(f) {
  const base = readHash();
  base.delete('work');
  base.delete('q');
  const items = languageOptions().map(([key, count]) => {
    const next = new URLSearchParams(base);
    next.set('lang', key);
    return h('li', {},
      h('a', { href: `#${next.toString()}`, 'aria-current': f.lang === key ? 'true' : null }, key === NONE ? 'Language not recorded' : key),
      h('span', { class: 'count' }, ` ${plural(count, 'publication', 'publications')}`));
  });
  return h('aside', { 'aria-labelledby': 'facet-h' },
    h('h2', { id: 'facet-h' }, 'Browse by language'),
    h('p', { class: 'note' }, 'Counted in publications; a page without a publication breakdown counts as one. Language is recorded per publication.'),
    h('ul', { class: 'facet' }, items));
}

function workList(f, content, status) {
  const works = index.works;
  status.textContent = `${plural(works.length, 'work group', 'work groups')}, anchored on German pages of Zweig's own works.`;
  add(content, 
    h('h2', {}, 'Works'),
    h('p', { class: 'note' }, 'A work is anchored on the compiler\'s German work page (VIST) or, where none exists, on a German page of Zweig\'s own works that other pages link or cite in brackets. Search and the language list reach every page, also those no work view reaches.'),
    h('ul', { class: 'hit-list' }, works.map(w => h('li', {},
      h('a', { href: `#work=${encodeURIComponent(w.id)}` }, w.t),
      h('div', { class: 'why' }, `${w.v ? 'VIST work page' : 'German page'} ${w.a}, ${plural(w.u, 'page', 'pages')} in parts 1 and 3`)))));
}

function pageHit(row, f, why) {
  const units = unitsOfIndexRow(row).filter(u => unitOk(u, f));
  const years = units.flatMap(u => u.years || [u.year]);
  return h('li', {},
    h('a', { href: `judge.html#page=${row.id}`, lang: null }, row.t),
    h('div', { class: 'why' }, [
      `page ${row.id}`, typeLabel(row.e), row.l || 'language not recorded',
      row.p ? plural(row.p.length, 'publication', 'publications') : 'no publication breakdown',
      yearsSpan(years),
    ].join(', ')),
    why ? h('div', { class: 'why' }, why) : null,
    row.w.length ? h('div', { class: 'why' }, 'Work: ', row.w.map((id, n) => [n ? ', ' : '', workLink(id)])) : null);
}

function workLink(id) {
  const w = index.works.find(x => x.id === id);
  return h('a', { href: `find.html#work=${encodeURIComponent(id)}` }, w ? w.t : id);
}

function searchResults(q, f, content, status) {
  const key = fold(q);
  if (key.length < 2) {
    status.textContent = 'Type at least two letters.';
    return;
  }
  const works = rankWorks(index.works, key);
  const pages = [];
  for (const row of index.pages) {
    const rank = pageRank(row, key);
    if (rank === null) continue;
    const why = rank <= 2 ? null : rank === 3 ? 'matched a publication title' : `matched the bracketed original title [${row.b}]`;
    if (filtersActive(f) && !unitsOfIndexRow(row).some(u => unitOk(u, f))) continue;
    pages.push([row, why, rank]);
  }
  pages.sort((a, b) => a[2] - b[2] || a[0].id - b[0].id);
  status.textContent = `${plural(works.length, 'work', 'works')} and ${plural(pages.length, 'page', 'pages')} match "${q}"${filtersActive(f) ? ' within the filters' : ''}. Diacritics and umlauts are folded. Titles equal to the query come first, then titles starting with it, then other matches.`;
  add(content, 
    h('h2', {}, `Works (${works.length})`),
    works.length
      ? h('ul', { class: 'hit-list' }, works.map(w => h('li', {}, h('a', { href: `#work=${encodeURIComponent(w.id)}` }, w.t),
        h('div', { class: 'why' }, `${w.v ? 'VIST work page' : 'German page'} ${w.a}, ${plural(w.u, 'page', 'pages')} in parts 1 and 3`))))
      : h('p', { class: 'gap' }, 'No work title matches.'),
    h('h2', {}, `Pages (${pages.length})`),
    pages.length > SEARCH_CAP ? h('p', { class: 'note' }, `The first ${SEARCH_CAP} of ${pages.length} pages are listed; a longer query narrows the list.`) : null,
    pages.length
      ? h('ul', { class: 'hit-list' }, pages.slice(0, SEARCH_CAP).map(([row, why]) => pageHit(row, f, why)))
      : h('p', { class: 'gap' }, 'No page title, publication title or bracketed original title matches.'));
}

function languageList(f, content, status) {
  const rows = [];
  let units = 0;
  for (const row of index.pages) {
    const matched = unitsOfIndexRow(row).filter(u => unitOk(u, f));
    if (!matched.length) continue;
    units += matched.length;
    rows.push([row, matched]);
  }
  const firstYear = ([, us]) => Math.min(...us.flatMap(u => u.years || [u.year]).filter(Number.isFinite), 9999);
  rows.sort((a, b) => firstYear(a) - firstYear(b) || a[0].id - b[0].id);
  const name = f.lang === NONE ? 'no recorded language' : f.lang;
  status.textContent = `${plural(units, 'publication', 'publications')} on ${plural(rows.length, 'page', 'pages')} in ${name}${f.from !== null || f.to !== null ? ' within the year filter' : ''}.`;
  add(content, 
    h('h2', {}, `${plural(units, 'publication', 'publications')} on ${plural(rows.length, 'page', 'pages')}`),
    h('p', { class: 'note' }, 'Ordered by the first year; a page without a publication breakdown counts as one publication with its page-level language. Chaining through cross-references and contents lines is out of scope for this round.'),
    h('ul', { class: 'hit-list' }, rows.map(([row, us]) => h('li', {},
      h('a', { href: `judge.html#page=${row.id}` }, row.t),
      h('div', { class: 'why' }, `page ${row.id}, ${typeLabel(row.e)}`),
      h('ul', { class: 'pub-lines' }, us.map(u => h('li', {}, u.id
        ? h('a', { href: `judge.html#page=${row.id}&pub=${encodeURIComponent(u.id)}` }, `${u.year ?? 'year not recorded'} ${u.imprint || 'imprint not recorded'}`)
        : `${yearsSpan(u.years)}, no publication breakdown`))),
      row.w.length ? h('div', { class: 'why' }, 'Work: ', row.w.map((id, n) => [n ? ', ' : '', workLink(id)])) : null))));
}

// Work view

async function renderWork(params) {
  const id = params.get('work');
  const data = await loadJSON('works.json');
  const work = data.works.find(w => w.workId === id);
  if (!work) {
    fill(main, h('h1', {}, 'Work not found'), h('p', {}, `No lab work group has the identifier ${id}.`), h('p', {}, h('a', { href: 'find.html' }, 'All works')));
    return;
  }
  const f = readFilters(params);
  const open = new Set((params.get('open') || '').split(',').filter(Boolean));
  const ctx = { f, open, shown: 0, total: 0 };
  document.title = `${work.title}, Find and cite a work, Klawiter Bibliography Lab`;
  const status = h('p', { class: 'status', role: 'status' });
  const union = work.union;
  const rel1Ids = new Set(work.linkedByCompiler.pageIds);
  const rel3Ids = new Set(work.citingTitleInBrackets.pageIds);
  ctx.rel1Ids = rel1Ids;
  ctx.rel3Ids = rel3Ids;
  const zweig = new Set(typeof ZWEIG_AUTHOR_TYPES !== 'undefined' ? ZWEIG_AUTHOR_TYPES : []);
  const ed = editionsByLanguage(work, zweig, f);

  fill(main, 
    h('h1', {}, work.title),
    filterBar(params, { search: false }),
    status,
    anchorBlock(work),
    editionsSection(ed, ctx),
    h('p', { class: 'sans' }, `${plural(union.count, 'page', 'pages')} in parts 1 and 3 (union, each page counted once); ${plural(union.inBothParts.length, 'page stands', 'pages stand')} in both parts and ${union.inBothParts.length === 1 ? 'is' : 'are'} marked in each. Anchor pages are counted apart.`),
    part1(work, ctx),
    part2(work, ctx, ed),
    part3(work, ctx),
    h('p', { class: 'note' }, `${work.scopeNote} See the `, h('a', { href: '#scope' }, 'scope panel'), '.'),
    workTools(work, data.dataState));

  main.querySelectorAll('details.group').forEach(d => d.addEventListener('toggle', () => {
    const next = readHash();
    const ids = new Set((next.get('open') || '').split(',').filter(Boolean));
    if (d.open) ids.add(d.dataset.group); else ids.delete(d.dataset.group);
    if (ids.size) next.set('open', [...ids].join(',')); else next.delete('open');
    writeHash(next, { replace: true });
    refreshWorkCitation(work, data.dataState);
  }));
  status.textContent = filtersActive(f)
    ? `${ctx.shown} of ${ctx.total} listed rows match the filter ${describeFilter(f)}. The counts in the part headings stay those of the whole work.`
    : '';
  if (!params.has('open')) focusMain();
}

function describeFilter(f) {
  const bits = [];
  if (f.lang) bits.push(`language ${f.lang === NONE ? 'not recorded' : f.lang}`);
  if (f.from !== null || f.to !== null) bits.push(`years ${f.from ?? 'any'} to ${f.to ?? 'any'}`);
  return bits.join(', ');
}

function group(ctx, id, summary, body) {
  return h('details', { class: 'group', 'data-group': id, open: ctx.open.has(id) || null },
    h('summary', {}, summary), body);
}

function countText(count, ctx, shown) {
  const base = `${plural(count.pages, 'page', 'pages')}, ${plural(count.publications, 'publication', 'publications')}`;
  const extra = count.pagesWithoutBreakdown ? ` (${count.pagesWithoutBreakdown} without breakdown)` : '';
  return filtersActive(ctx.f) ? `${shown} shown, of ${base}${extra}` : `${base}${extra}`;
}

/** Row units: publications, or the page itself where it has no breakdown. */
function unitsOfWorkRow(row) {
  if (row.publications) return row.publications;
  return [{ id: null, years: row.allYears || [], language: row.language, imprint: null }];
}

function rowsList(rows, ctx, tags = () => []) {
  let shown = 0;
  const items = rows.map(row => {
    const units = unitsOfWorkRow(row).map(u => ({ ...u, language: u.language ?? (u.id ? null : row.language) }));
    const visible = units.filter(u => unitOk(u.id ? u : { ...u, years: u.years }, ctx.f));
    ctx.total += 1;
    if (filtersActive(ctx.f) && !visible.length) return null;
    shown += 1;
    ctx.shown += 1;
    return h('li', {},
      h('a', { class: 'row-title', href: `judge.html#page=${row.pageId}` }, row.title),
      h('div', { class: 'row-meta' }, [`page ${row.pageId}`, typeLabel(row.entryType), row.language || 'language not recorded'].join(', ')),
      tags(row).length ? h('div', { class: 'tag' }, tags(row).join('; ')) : null,
      h('ul', { class: 'pub-lines' }, (filtersActive(ctx.f) ? visible : units).map(u => h('li', {}, u.id
        ? h('a', { href: `judge.html#page=${row.pageId}&pub=${encodeURIComponent(u.id)}` }, `${u.year ?? 'year not recorded'} ${u.imprint || 'imprint not recorded'}${u.language && u.language !== row.language ? `, ${u.language}` : ''}`)
        : `${yearsSpan(u.years)}, no publication breakdown`))));
  }).filter(Boolean);
  return { list: items.length ? h('ul', { class: 'rows' }, items) : h('p', { class: 'gap' }, 'No row matches the filter.'), shown };
}

/** The anchor pages; their publications stand in the editions table below. */
function anchorBlock(work) {
  const a = work.anchor;
  const anchorPage = a.members.find(m => m.pageId === a.pageId);
  return h('section', { class: 'part', 'aria-labelledby': 'anchor-h' },
    h('h2', { id: 'anchor-h' }, 'Anchor'),
    a.germanWorkPage ? null : h('p', { class: 'gap' }, 'No German work page exists for this work.'),
    h('p', {}, `Anchor: "${anchorPage ? anchorPage.title : a.pageId}" (page ${a.pageId})${a.vist ? ', the compiler\'s VIST work page,' : ', a German page without a VIST page,'} and the German pages listed here.`),
    h('ul', { class: 'rows' }, a.members.map(m => h('li', {},
      h('a', { href: `judge.html#page=${m.pageId}` }, m.title), h('span', { class: 'row-meta' }, ` page ${m.pageId}, ${m.reason}`)))));
}

const BASIS_WORDS = { anchor: 'anchor pages', linked: 'linked by the compiler', brackets: 'cites the title in brackets, lab rule' };

/**
 * Editions and translations of the work by language (S1.2): one row per
 * language with first and last year, and every count opens exactly its
 * publications. The parts below keep the evidence of each relation apart.
 */
function editionsSection(ed, ctx) {
  const unitLine = u => {
    const when = u.publicationId ? (u.year ?? 'year not recorded') : `${yearsSpan(u.years)}, page without breakdown`;
    const href = `judge.html#page=${u.pageId}${u.publicationId ? `&pub=${encodeURIComponent(u.publicationId)}` : ''}`;
    return h('li', {},
      h('a', { href }, `${when}${u.imprint ? `, ${u.imprint}` : ''}`),
      h('span', { class: 'row-meta' }, ` ${u.title}, page ${u.pageId}${u.basis === 'brackets' ? ', cites the title in brackets (lab rule, not reviewed)' : u.reason ? `, anchor page: ${u.reason}` : ''}${u.languageFromPage ? ', language recorded for the page only' : ''}`));
  };
  const groupId = lang => `ed-${lang.replace(/[^\p{L}\p{N}]+/gu, '-')}`;
  const rows = ed.rows.map(r => h('tr', {},
    h('th', { scope: 'row' }, r.language === 'language not recorded' ? 'Language not recorded' : r.language),
    h('td', { class: 'num', 'data-label': 'First year' }, r.first ?? 'no publication year'),
    h('td', { class: 'num', 'data-label': 'Last year' }, r.last ?? 'no publication year'),
    h('td', { 'data-label': 'Publications' }, group(ctx, groupId(r.language),
      [`${plural(r.publications, 'publication', 'publications')}${r.withoutBreakdown ? ` and ${plural(r.withoutBreakdown, 'page', 'pages')} without breakdown` : ''} `,
        h('span', { class: 'count' }, `on ${plural(r.pages, 'page', 'pages')}${r.undated ? `, ${r.undated} without a year` : ''}`)],
      h('ul', {}, r.units.map(unitLine)))),
    h('td', { 'data-label': 'Basis' }, Object.entries(r.basis).filter(([, n]) => n).map(([b, n]) => `${BASIS_WORDS[b]} ${n}`).join('; ')),
    h('td', { 'data-label': 'Translations section' }, r.textLines.length ? 'listed, see part 2' : 'not listed')));
  const left = ed.leftOut;
  return h('section', { class: 'part', 'aria-labelledby': 'ed-h' },
    h('h2', { id: 'ed-h' }, 'Editions and translations by language',
      h('span', { class: 'count' }, `${plural(ed.rows.reduce((n, r) => n + r.publications, 0), 'publication', 'publications')} and ${plural(ed.rows.reduce((n, r) => n + r.withoutBreakdown, 0), 'page', 'pages')} without breakdown in ${plural(ed.rows.length, 'language group', 'language groups')}${filtersActive(ctx.f) ? `, within the filter; ${ed.total} in all` : ''}`)),
    h('p', { class: 'part-note' }, 'Publications of the anchor pages, of the translations the compiler linked, and of pages citing the title in brackets (a lab rule, not reviewed). Language and year are those recorded for each publication; where a publication has no language, the language recorded for its page stands in and the line says so. A page without a publication breakdown is listed with the years its page records, which may belong to any publication it mentions, so first and last year count publications only. Rows run German first, then by first year.'),
    ed.rows.length
      ? h('div', { class: 'table-wrap' }, h('table', { class: 'coverage editions' },
        h('caption', {}, 'Editions and translations of the work by language'),
        h('thead', {}, h('tr', {},
          h('th', { scope: 'col' }, 'Language'), h('th', { scope: 'col' }, 'First year'), h('th', { scope: 'col' }, 'Last year'),
          h('th', { scope: 'col' }, 'Publications'), h('th', { scope: 'col' }, 'Basis, in publications'),
          h('th', { scope: 'col' }, 'Compiler\'s Translations section'))),
        h('tbody', {}, rows)))
      : h('p', { class: 'gap' }, 'No publication matches the filter.'),
    left.anchorsWithoutBreakdown.length ? h('p', { class: 'part-note' }, `Not counted as editions: ${left.anchorsWithoutBreakdown.map(a => `"${a.title}" (page ${a.pageId})`).join(', ')}, ${left.anchorsWithoutBreakdown.length === 1 ? 'an anchor page without a publication breakdown, which lists' : 'anchor pages without a publication breakdown, which list'} the whole work.`) : null,
    h('p', { class: 'part-note' }, `Left out: ${plural(left.adaptations, 'page', 'pages')} of adaptations and readings and ${plural(left.secondary, 'page', 'pages')} of secondary literature and other kinds linked by the compiler, ${plural(left.otherTypesInBrackets, 'page', 'pages')} citing the title in brackets whose entry type is not one of Zweig's own works, and ${plural(left.germanPagesNamingTheWorkPage, 'German page', 'German pages')} that only name the work page in their see-also list, mostly other works and volumes (listed in part 1). ${left.possiblySameTitle.pages ? `${plural(left.possiblySameTitle.pages, 'page', 'pages')} with ${plural(left.possiblySameTitle.publications, 'publication', 'publications')} cite a variant form of the title and stay a separate list, "Possibly the same title" in part 3, because the lab does not merge name forms. ` : ''}Appearances inside anthologies and collected volumes are covered only where the work page links the volume, marked "anchor page: linked by the VIST page".`));
}

function part1(work, ctx) {
  const r = work.linkedByCompiler;
  const tags = row => [
    ...(row.direction || []),
    ctx.rel3Ids.has(row.pageId) ? 'also cites the title in brackets' : null,
  ].filter(Boolean);
  const body = [];
  if (!r.count.pages) {
    body.push(h('p', { class: 'gap' }, 'No pages linked by the compiler.'));
  } else {
    const langs = Object.entries(r.translationsByLanguage);
    const trPages = langs.reduce((n, [, g]) => n + g.count.pages, 0);
    if (langs.length) {
      let trShown = 0;
      const inner = langs.map(([lang, g]) => {
        const { list, shown } = rowsList(g.rows, ctx, tags);
        trShown += shown;
        return group(ctx, `p1-tr-${lang}`, [`${lang} `, h('span', { class: 'count' }, countText(g.count, ctx, shown))], list);
      });
      body.push(group(ctx, 'p1-tr', ['Translations ', h('span', { class: 'count' }, `${filtersActive(ctx.f) ? `${trShown} shown, of ` : ''}${plural(trPages, 'page', 'pages')}, by language`)], inner));
    }
    for (const [key, label] of [['germanPagesLinkingTheAnchor', 'German pages of Zweig\'s own works linking the anchor'], ['adaptationsAndReadings', 'Adaptations and readings'], ['secondaryLiteratureAndOther', 'Secondary literature and other']]) {
      const g = r[key];
      if (!g.count.pages) continue;
      const { list, shown } = rowsList(g.rows, ctx, tags);
      body.push(group(ctx, `p1-${key}`, [`${label} `, h('span', { class: 'count' }, countText(g.count, ctx, shown))], list));
    }
    body.push(gapGroups(r, work, ctx, 'p1'));
  }
  return h('section', { class: 'part', 'aria-labelledby': 'p1-h' },
    h('h2', { id: 'p1-h' }, 'Linked by the compiler', h('span', { class: 'count' }, `${filtersActive(ctx.f) ? 'of ' : ''}${plural(r.count.pages, 'page', 'pages')}, ${plural(r.count.publications, 'publication', 'publications')}`)),
    h('p', { class: 'part-note' }, 'Pages named in an anchor page\'s see-also list or naming an anchor page in theirs. The compiler\'s see-also list mixes translations, adaptations and secondary literature, so they are grouped by kind.'),
    body);
}

/** Publications without language or year, each opening exactly its rows. */
function gapGroups(rel, work, ctx, prefix) {
  const g = rel.gapGroups;
  const rowsById = new Map();
  const collect = rows => rows.forEach(r => rowsById.set(r.pageId, r));
  if (rel.translationsByLanguage) {
    Object.values(rel.translationsByLanguage).forEach(x => collect(x.rows));
    ['germanPagesLinkingTheAnchor', 'adaptationsAndReadings', 'secondaryLiteratureAndOther'].forEach(k => collect(rel[k].rows));
  } else {
    Object.values(rel.byEntryType).forEach(langs => Object.values(langs).forEach(x => collect(x.rows)));
  }
  const line = ref => {
    const row = rowsById.get(ref.pageId);
    const pub = ref.publicationId && row?.publications?.find(p => p.id === ref.publicationId);
    const title = row ? row.title : pageById.get(ref.pageId)?.t || `page ${ref.pageId}`;
    return h('li', {},
      h('a', { href: `judge.html#page=${ref.pageId}${ref.publicationId ? `&pub=${encodeURIComponent(ref.publicationId)}` : ''}` }, title),
      h('span', { class: 'row-meta' }, pub ? ` ${pub.year ?? 'year not recorded'} ${pub.imprint || ''}, page ${ref.pageId}` : ` page ${ref.pageId}, no publication breakdown`));
  };
  return [
    group(ctx, `${prefix}-nolang`, ['Language not recorded ', h('span', { class: 'count' }, plural(g.languageNotRecorded.count, 'publication', 'publications'))],
      g.languageNotRecorded.count ? h('ul', { class: 'rows' }, g.languageNotRecorded.rows.map(line)) : h('p', { class: 'gap' }, 'None.')),
    group(ctx, `${prefix}-noyear`, ['Year not recorded ', h('span', { class: 'count' }, plural(g.yearNotRecorded.count, 'publication', 'publications'))],
      g.yearNotRecorded.count ? h('ul', { class: 'rows' }, g.yearNotRecorded.rows.map(line)) : h('p', { class: 'gap' }, 'None.')),
    h('p', { class: 'part-note' }, `Gap groups count ${g.unit}.`),
  ];
}

/**
 * The compiler's "Translations" section (relation 2), German reprint lines
 * first. A line whose language name no row of the editions table carries says
 * so here, the one place the line stands.
 */
function part2(work, ctx, ed) {
  const r = work.listedAsText;
  const withoutRow = new Map(ed.textOnly.map(l => [`${l.pageId}|${l.language}`, l]));
  const body = [];
  if (!r.sources.length) {
    body.push(h('p', { class: 'gap' }, 'The anchor pages carry no "Translations" section.'));
  }
  for (const source of r.sources) {
    const entries = [...source.germanReprints, ...source.languages]
      .filter(e => !ctx.f.lang || ctx.f.lang === NONE || e.language.toLowerCase().startsWith(ctx.f.lang.toLowerCase()));
    body.push(h('p', { class: 'part-note' }, `From the "Translations" section of page ${source.pageId}, as the compiler wrote it.`));
    if (!entries.length) body.push(h('p', { class: 'gap' }, 'No language line matches the language filter.'));
    body.push(entries.map(e => {
      const alone = withoutRow.get(`${source.pageId}|${e.language}`);
      return group(ctx, `p2-${source.pageId}-${e.language}`,
        [`${e.language} `, h('span', { class: 'count' }, e.text.length > 70 ? `${e.text.slice(0, 70)}…` : e.text), alone ? h('span', { class: 'tag' }, ' no table row') : null],
        [h('p', { class: 'compiler-text' }, e.text),
          alone ? h('p', { class: 'part-note' }, `No row of the editions table carries the language name "${e.language}". The compiler's names can differ from the languages recorded for the pages, and the lab does not equate them.${alone.variantPages ? ` ${plural(alone.variantPages, 'page', 'pages')} in this language ${alone.variantPages === 1 ? 'cites' : 'cite'} a variant of the title, see "Possibly the same title" in part 3.` : ''}`) : null]);
    }));
  }
  return h('section', { class: 'part', 'aria-labelledby': 'p2-h' },
    h('h2', { id: 'p2-h' }, 'Listed on the work page as text', h('span', { class: 'count' }, plural(r.languageCount, 'language', 'languages'))),
    h('p', { class: 'part-note' }, `The compiler's "Translations" section, parsed by the lab and shown as written. These lines are not linked to pages; the year filter does not apply to them. ${plural(new Set(ed.textOnly.map(l => l.language)).size, 'language name has', 'language names have')} no row in the editions table.`),
    body);
}

function part3(work, ctx) {
  const r = work.citingTitleInBrackets;
  const tags = row => [row.bracket ? `[${row.bracket}]` : null, row.alsoLinkedByCompiler ? 'also linked by the compiler' : null].filter(Boolean);
  const body = [];
  for (const [type, langs] of Object.entries(r.byEntryType)) {
    let typeShown = 0;
    const typePages = Object.values(langs).reduce((n, g) => n + g.count.pages, 0);
    const inner = Object.entries(langs).map(([lang, g]) => {
      const { list, shown } = rowsList(g.rows, ctx, tags);
      typeShown += shown;
      return group(ctx, `p3-${type}-${lang}`, [`${lang === NOT_RECORDED ? 'Language not recorded' : lang} `, h('span', { class: 'count' }, countText(g.count, ctx, shown))], list);
    });
    body.push(group(ctx, `p3-${type}`, [`${typeLabel(type)} `, h('span', { class: 'count' }, `${filtersActive(ctx.f) ? `${typeShown} shown, of ` : ''}${plural(typePages, 'page', 'pages')}, by language`)], inner));
  }
  if (!r.count.pages) body.push(h('p', { class: 'gap' }, 'No page cites the title in brackets.'));
  body.push(gapGroups(r, work, ctx, 'p3'));
  const excluded = Object.entries(r.excludedBrackets);
  body.push(h('p', { class: 'sans' }, 'Excluded brackets: ', excluded.map(([k, v], n) => [n ? ', ' : '', `${v.count} ${EXCLUDED_LABELS[k] || k}`]), '.'));
  for (const [k, v] of excluded) {
    if (!v.count) continue;
    body.push(group(ctx, `p3-ex-${k}`, [`Excluded, ${EXCLUDED_LABELS[k] || k} `, h('span', { class: 'count' }, plural(v.count, 'page', 'pages'))],
      h('ul', { class: 'rows' }, v.rows.map(row => h('li', {},
        h('a', { href: `judge.html#page=${row.pageId}` }, pageById.get(row.pageId)?.t || `page ${row.pageId}`),
        h('span', { class: 'row-meta' }, ` page ${row.pageId}, [${row.bracket}]`))))));
  }
  const ps = r.possiblySameTitle;
  if (ps.count.pages) {
    const { list, shown } = rowsList(ps.rows, ctx, row => [`[${row.bracket}]`, row.alsoLinkedByCompiler ? 'also linked by the compiler' : null].filter(Boolean));
    body.push(group(ctx, 'p3-variants', ['Possibly the same title, a separate list ', h('span', { class: 'count' }, countText(ps.count, ctx, shown))],
      [h('p', { class: 'part-note' }, `${ps.note[0].toUpperCase()}${ps.note.slice(1)}. These pages are not counted in this part or in the union.`), list]));
  }
  return h('section', { class: 'part', 'aria-labelledby': 'p3-h' },
    h('h2', { id: 'p3-h' }, 'Citing the title in brackets', h('span', { class: 'count' }, `found by a lab rule, not reviewed`)),
    h('p', { class: 'sans' }, `${filtersActive(ctx.f) ? 'Of ' : ''}${plural(r.count.pages, 'page', 'pages')}, ${plural(r.count.publications, 'publication', 'publications')}; ${r.alsoLinkedCount} also linked by the compiler.`),
    h('p', { class: 'part-note' }, 'Pages whose first bracket after the page title holds the work\'s title. This is a statement about the source text, not an identity decision. Appearances in anthologies are not covered.'),
    body);
}

/** The work citation addresses the current hash: work, filters and opened groups. */
function refreshWorkCitation(work, state) {
  const field = document.getElementById('cite-work');
  if (!field) return;
  field.value = citation({
    what: `"${work.title}", lab work group anchored on wiki page ${work.anchor.pageId} (lab-derived, not a bibliographic identifier)`,
    identifier: work.workId,
    url: citeUrl('find.html', readHash().toString()),
    state,
  });
}

function workTools(work, state) {
  const field = h('textarea', { id: 'cite-work', readonly: true, rows: 4 });
  const status = h('p', { class: 'status', role: 'status' });
  queueMicrotask(() => refreshWorkCitation(work, state));
  const exportJson = () => {
    const payload = {
      dataState: state,
      identifier: work.workId,
      identifierNote: work.idNote,
      url: citeUrl('find.html', `work=${encodeURIComponent(work.workId)}`),
      accessed: new Date().toISOString().slice(0, 10),
      title: work.title,
      anchor: { pageId: work.anchor.pageId, vist: work.anchor.vist, members: work.anchor.members },
      parts: {
        linkedByCompiler: { state: 'linked by the compiler in a see-also list', producer: 'compiler', pageIds: work.linkedByCompiler.pageIds },
        listedAsText: { state: 'listed by the compiler as text', producer: 'compiler, parsed by the lab', sources: work.listedAsText.sources },
        citingTitleInBrackets: { state: 'proposed', producer: 'lab rule, not reviewed', pageIds: work.citingTitleInBrackets.pageIds },
      },
      union: work.union,
      scopeNote: work.scopeNote,
    };
    download(`klawiter-lab-${work.workId.replace('/', '-')}.json`, JSON.stringify(payload, null, 2), 'application/json');
    status.textContent = 'Downloaded the work group as JSON.';
  };
  return h('div', { class: 'tool-row' },
    h('section', { 'aria-labelledby': 'cite-h' },
      h('h2', { class: 'section-label', id: 'cite-h' }, 'Cite and export the work'),
      h('label', { class: 'visually-hidden', for: 'cite-work' }, 'Citation of the work group'),
      field,
      h('div', { class: 'actions' },
        h('button', { type: 'button', class: 'btn', onclick: () => copyText(field.value, field, status) }, 'Copy citation'),
        h('button', { type: 'button', class: 'btn', onclick: exportJson }, 'JSON')),
      h('p', { class: 'note' }, 'The citation addresses this view with its filters and opened groups and follows them as they change. BibTeX and RIS of a single record, with origin, state and producer, are in the record view.'),
      status),
    h('section', { 'aria-label': 'Data state' }, dataStateBlock(state)));
}

// Scope and coverage

async function renderScope() {
  const [cov, meta, report] = await Promise.all([loadJSON('coverage.json'), loadJSON('meta.json'), loadJSON('report.json')]);
  document.title = 'Scope and coverage, Klawiter Bibliography Lab';
  const years = new Map();
  for (const row of index.pages) {
    const ys = row.p ? row.p.map(p => p[1]) : row.y || [];
    for (const y of new Set(ys.filter(Number.isFinite))) years.set(y, (years.get(y) || 0) + 1);
  }
  const latest = [...years.keys()].sort((a, b) => b - a).slice(0, 3);
  const d = cov.denominator;
  const pct = n => `${Math.round((n / d.count) * 1000) / 10}%`;
  const listLink = (key, text) => h('a', { href: `#list=${encodeURIComponent(key)}` }, text);
  const reach = cov.workViews;
  const unreached = Object.entries(reach.unreachedByEntryType).sort((a, b) => b[1].count - a[1].count);
  const c = meta.counts;
  fill(main, 
    h('h1', {}, 'Scope and coverage'),
    h('section', { class: 'prose', 'aria-labelledby': 'held-h' },
      h('h2', { id: 'held-h' }, 'What the bibliography holds'),
      h('p', {}, 'The compiler\'s bibliography exists in several states. The 1965 bibliography is not available to the project. The main volume of 1991 and Addendum I of 1999 were printed; Addendum II was never published and survives as the compiler\'s working file. The wiki continued the work online.'),
      h('p', {}, h('strong', {}, 'The published lab shows wiki data only. '), 'No published record has been compared with the print volumes. A local run lists proposed print matches from a file the print strand produces, as candidates for a publication where the match names one, and checks whether each value of that publication stands in the candidate entry; that file is not published. No agreement raises a state, merges a value or reads "confirmed", because the matches are not reviewed and wiki and print are states of one compiler\'s work.'),
      h('p', {}, 'The wiki\'s editing period is not recorded in the lab data. ', latest.length ? `The latest publication years the wiki records are ${latest.map(y => `${y} (${plural(years.get(y), 'page', 'pages')})`).join(', ')}.` : ''),
      h('p', {}, `The lab reads ${plural(c.pages, 'page', 'pages')} of the main namespace. ${plural(c.pagesWithBreakdown, 'page has', 'pages have')} a breakdown into ${plural(c.publications, 'publication', 'publications')}; on the other pages one page-level record stands for everything the page lists.`)),
    h('section', { class: 'prose', 'aria-labelledby': 'rules-h' },
      h('h2', { id: 'rules-h' }, 'How works are grouped'),
      h('ul', {},
        h('li', {}, `Anchor: the compiler's German work page marked VIST with German pages of the same title or linked by it; without a VIST page, a German page of Zweig's own works that other pages link or cite in brackets. ${report.works.vistAnchors} anchors rest on a VIST page, ${report.works.otherAnchors} on a German page.`),
        h('li', {}, 'Linked by the compiler: pages in an anchor page\'s see-also list or naming an anchor page in theirs.'),
        h('li', {}, 'Listed by the compiler as text: the "Translations" section of the anchor page, shown as written.'),
        h('li', {}, 'Citing the title in brackets: the first bracket after a page title holds the work\'s title, found by a lab rule and not reviewed. Brackets holding a year or number, a place, an English gloss or several titles are excluded and listed by kind; variant forms are listed as possibly the same title and never merged.'),
        h('li', {}, 'Not covered: appearances inside anthologies and collected volumes, and chaining through cross-references and contents lines.'))),
    h('section', { class: 'prose', 'aria-labelledby': 'limits-h' },
      h('h2', { id: 'limits-h' }, 'Modelling limits'),
      h('ul', {},
        h('li', {}, 'One wiki page is one page-level record, which search and exports use; it can combine values of different publications of that page.'),
        h('li', {}, 'An absent value is not yet distinguished into a gap in the source, a value that does not apply and a value not extracted.'),
        h('li', {}, 'The published translations field keeps only the first language of the compiler\'s "Translations" section; the work view reads the section itself.'),
        h('li', {}, 'Each page is read in its latest revision; earlier revisions and archived pages are not extracted, except where a page was restored from before a Redirect fixer overwrite.'),
        h('li', {}, 'A place decision concerns the Wikidata identity of a place name on every page that carries it, not the assignment of the place to a publication.'),
        h('li', {}, 'State and producer labels follow a provisional mapping from decider strings until the shared claim schema provides a typed producer class.'))),
    h('section', { 'aria-labelledby': 'cov-h' },
      h('h2', { id: 'cov-h' }, `Coverage of ${d.count} pages of Zweig's own works (data commit ${cov.dataState.commit.slice(0, 7)})`),
      h('p', { class: 'note' }, `Denominator: ${d.unit}, namely ${d.entryTypes.map(typeLabel).join(', ')}. `, listLink('denominator', 'List these pages'), '.'),
      h('div', { class: 'table-wrap' }, h('table', { class: 'coverage' },
        h('thead', {}, h('tr', {}, h('th', { scope: 'col' }, 'Field'), h('th', { scope: 'col' }, 'Value recorded'), h('th', { scope: 'col' }, 'No value recorded*'), h('th', { scope: 'col' }, 'LLM gap fills among the recorded values'))),
        h('tbody', {}, Object.entries(cov.fields).map(([name, v]) => h('tr', {},
          h('th', { scope: 'row' }, FIELD_LABELS[name] || name),
          h('td', {}, listLink(`cov.${name}.valueRecorded`, plural(v.valueRecorded.count, 'page', 'pages')), ` (${pct(v.valueRecorded.count)})`),
          h('td', {}, listLink(`cov.${name}.noValueRecorded`, plural(v.noValueRecorded.count, 'page', 'pages'))),
          h('td', {}, v.llmGapFills.count ? listLink(`cov.${name}.llmGapFills`, plural(v.llmGapFills.count, 'page', 'pages')) : '0 pages')))))),
      h('p', { class: 'note' }, `* ${cov.fields.publisher.noValueRecorded.note[0].toUpperCase()}${cov.fields.publisher.noValueRecorded.note.slice(1)}.`),
      h('p', { class: 'note' }, 'Shown separately: the verification stage found ',
        Object.entries(cov.verificationFalseNegatives).map(([name, v], n) => [n ? ' and ' : '',
          v.count ? listLink(`fn.${name}`, `${v.count} ${FIELD_LABELS[name].toLowerCase()} values`) : `${v.count} ${FIELD_LABELS[name].toLowerCase()} values`]),
        ' in the raw text that the record lacks.'),
      h('h3', {}, 'What the work views leave out'),
      h('p', {}, 'Work views reach ', listLink('reached', `${reach.reached.count} of ${d.count} pages`), '. Not reached, by kind: ',
        unreached.map(([type, v], n) => [n ? ', ' : '', listLink(`un.${type}`, `${typeLabel(type).toLowerCase()} ${v.count}`)]), '.')),
    h('section', { 'aria-label': 'Data state' }, dataStateBlock(meta.dataState)));
  focusMain();
}

async function renderList(key) {
  const cov = await loadJSON('coverage.json');
  const [kind, a, b] = key.split('.');
  let ids = null;
  let what = '';
  const d = cov.denominator;
  if (kind === 'denominator') { ids = d.pageIds; what = `The ${d.count} pages of Zweig's own works`; }
  else if (kind === 'cov' && cov.fields[a]?.[b]) {
    const label = { valueRecorded: 'with a value recorded', noValueRecorded: 'with no value recorded', llmGapFills: 'whose value is an LLM gap fill' }[b];
    ids = cov.fields[a][b].pageIds;
    what = `${FIELD_LABELS[a]}: ${ids.length} of ${d.count} pages of Zweig's own works ${label}`;
  } else if (kind === 'fn' && cov.verificationFalseNegatives[a]) {
    ids = cov.verificationFalseNegatives[a].pageIds;
    what = `${FIELD_LABELS[a]}: ${ids.length} of ${d.count} pages where the verification stage found a value in the raw text that the record lacks`;
  } else if (kind === 'reached') {
    ids = cov.workViews.reached.pageIds;
    what = `${ids.length} of ${d.count} pages of Zweig's own works that a work view reaches`;
  } else if (kind === 'un' && cov.workViews.unreachedByEntryType[a]) {
    ids = cov.workViews.unreachedByEntryType[a].pageIds;
    what = `${typeLabel(a)}: ${ids.length} pages of Zweig's own works that no work view reaches`;
  }
  if (!ids) {
    fill(main, h('h1', {}, 'List not found'), h('p', {}, h('a', { href: '#scope' }, 'Back to scope and coverage')));
    return;
  }
  document.title = `${what}, Klawiter Bibliography Lab`;
  fill(main, 
    h('h1', {}, what),
    h('p', {}, h('a', { href: '#scope' }, 'Back to scope and coverage')),
    kind === 'cov' && b === 'noValueRecorded' ? h('p', { class: 'note' }, `${cov.fields[a].noValueRecorded.note[0].toUpperCase()}${cov.fields[a].noValueRecorded.note.slice(1)}.`) : null,
    h('ul', { class: 'hit-list' }, ids.map(id => {
      const row = pageById.get(id);
      return row ? pageHit(row, { lang: null, from: null, to: null }) : h('li', {}, `page ${id}`);
    })),
    dataStateBlock(cov.dataState));
  focusMain();
}

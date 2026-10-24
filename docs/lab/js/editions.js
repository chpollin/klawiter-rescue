/**
 * Pure rules of the work view (S1.1, S1.2): search order and the editions of
 * a work by language. No DOM, so pipeline/lab/test_lab_js.mjs runs them with
 * node.
 */

export const NOT_RECORDED = 'language not recorded';

/**
 * Search order of work groups: own title equal to the query, own title
 * starting with it, own title containing it, then works found only through an
 * anchor page title. Within a rank VIST works come first, then larger works.
 * The query and the keys are folded the same way (fold in lab.js).
 */
export function workRank(work, key) {
  if (work.k === key) return 0;
  if (work.k.startsWith(key)) return 1;
  if (work.k.includes(key)) return 2;
  if ((work.m || []).some(([, k]) => k.includes(key))) return 3;
  return null;
}

export function rankWorks(works, key) {
  return works
    .map(w => [w, workRank(w, key)])
    .filter(([, rank]) => rank !== null)
    .sort(([a, ra], [b, rb]) => ra - rb || (b.v - a.v) || (b.u - a.u) || a.t.localeCompare(b.t))
    .map(([w]) => w);
}

/** Search order of pages: page title equal, starting with, containing, then publication title, then bracket. */
export function pageRank(row, key) {
  if (row.kt === key) return 0;
  if (row.kt.startsWith(key)) return 1;
  if (row.kt.includes(key)) return 2;
  if (row.kp && row.kp.includes(key)) return 3;
  if (row.kb && row.kb.includes(key)) return 4;
  return null;
}

const BASIS_ORDER = ['anchor', 'linked', 'brackets'];

/**
 * Pages of a work that carry editions of the work itself: the anchor pages
 * with a publication breakdown, the translations of Zweig's own works the
 * compiler linked, and the pages citing the title in brackets whose entry
 * type is one of Zweig's own works. Left out and counted: adaptations,
 * secondary literature, other entry types, anchor pages without a breakdown
 * (work pages such as the VIST page, whose years span everything they
 * mention) and German pages that only name the work page in their see-also
 * list, because those are mostly other works and volumes (on page 7460 the
 * VIST pages of sibling stories and a volume of 1911). A page in parts 1 and
 * 3 counts once, as linked.
 */
function editionPages(work, zweigTypes) {
  const pages = new Map();
  const add = (row, basis) => {
    const known = pages.get(row.pageId);
    if (known) {
      known.alsoBrackets = known.alsoBrackets || basis === 'brackets';
      return;
    }
    pages.set(row.pageId, { row, basis, alsoBrackets: false });
  };
  const anchorsWithoutBreakdown = [];
  for (const m of work.anchor.members) {
    if (m.publications && m.publications.length) add({ ...m, reason: m.reason }, 'anchor');
    else anchorsWithoutBreakdown.push({ pageId: m.pageId, title: m.title });
  }
  const p1 = work.linkedByCompiler;
  for (const g of Object.values(p1.translationsByLanguage)) g.rows.forEach(r => add(r, 'linked'));
  let otherTypePages = 0;
  for (const [type, langs] of Object.entries(work.citingTitleInBrackets.byEntryType)) {
    for (const g of Object.values(langs)) {
      for (const r of g.rows) {
        if (zweigTypes.has(type)) add(r, 'brackets');
        else otherTypePages += 1;
      }
    }
  }
  return {
    pages: [...pages.values()],
    leftOut: {
      adaptations: p1.adaptationsAndReadings.count.pages,
      secondary: p1.secondaryLiteratureAndOther.count.pages,
      otherTypesInBrackets: otherTypePages,
      germanPagesNamingTheWorkPage: p1.germanPagesLinkingTheAnchor.rows.length,
      anchorsWithoutBreakdown,
      possiblySameTitle: work.citingTitleInBrackets.possiblySameTitle.count,
    },
  };
}

/** Units of a page: its publications, or the page itself with its years where it has no breakdown. */
function unitsOf({ row, basis, alsoBrackets }) {
  const base = { pageId: row.pageId, title: row.title, basis, alsoBrackets, reason: row.reason || null };
  if (row.publications && row.publications.length) {
    return row.publications.map(p => ({
      ...base, publicationId: p.id, year: p.year ?? null, years: p.year ? [p.year] : [],
      imprint: p.imprint || null, language: p.language || row.language || null,
      languageFromPage: !p.language && !!row.language,
    }));
  }
  const years = (row.allYears || []).filter(Number.isFinite);
  return [{
    ...base, publicationId: null, year: null, years, imprint: null, language: row.language || null,
  }];
}

/** The language a "Translations" line names: its label up to a space, bracket or slash, case-folded. */
export function labelLanguage(label) {
  return String(label).split(/[\s(/]/)[0].toLowerCase();
}

function yearOk(unit, f) {
  if (f.from === null && f.to === null) return true;
  return unit.years.some(y => (f.from === null || y >= f.from) && (f.to === null || y <= f.to));
}

function langOk(language, f) {
  if (f.lang === null) return true;
  if (f.lang === 'none') return language === NOT_RECORDED;
  return language === f.lang;
}

/**
 * The editions of a work grouped by language (S1.2, evaluation task
 * "characterise the reception of a work").
 *
 * A publication without a recorded language takes the language recorded for
 * its page, marked as such, as part 3 of the work view groups it.
 *
 * Unit: publications; a page without a publication breakdown counts as one
 * unit with the years its page records. Those page years can belong to any
 * publication the page mentions, so first and last year come from
 * publications only. Each language row lists exactly its units, so every
 * count opens what it counts. Rows are ordered German first,
 * then by first year, languages without any year after them and the group
 * "language not recorded" last. Lines of the compiler's "Translations"
 * section attach to the row whose language has exactly the name of the line's
 * label; the compiler's names can differ from the recorded ones, and the lab
 * does not equate them. Lines without a row form a list of their own, because
 * those lines are text, not records.
 */
export function editionsByLanguage(work, zweigTypes, filters = { lang: null, from: null, to: null }) {
  const { pages, leftOut } = editionPages(work, zweigTypes);
  const rows = new Map();
  let total = 0;
  let shown = 0;
  for (const page of pages) {
    for (const unit of unitsOf(page)) {
      total += 1;
      const language = unit.language || NOT_RECORDED;
      if (!langOk(language, filters) || !yearOk(unit, filters)) continue;
      shown += 1;
      if (!rows.has(language)) rows.set(language, { language, units: [], textLines: [] });
      rows.get(language).units.push(unit);
    }
  }
  const textLines = work.listedAsText.sources.flatMap(s => [...s.germanReprints, ...s.languages]
    .map(e => ({ ...e, pageId: s.pageId })));
  // Variant-title pages stay a separate list (never merged); a line without a
  // table row says how many of them carry its language.
  const variantPages = new Map();
  for (const r of work.citingTitleInBrackets.possiblySameTitle.rows) {
    const key = String(r.language || '').toLowerCase();
    variantPages.set(key, (variantPages.get(key) || 0) + 1);
  }
  const textOnly = [];
  for (const line of textLines) {
    const key = labelLanguage(line.language);
    const row = [...rows.values()].find(r => r.language.toLowerCase() === key);
    if (row) row.textLines.push(line);
    else if (filters.lang === null || labelLanguage(filters.lang) === key) {
      textOnly.push({ ...line, variantPages: variantPages.get(key) || 0 });
    }
  }
  const out = [...rows.values()].map(r => {
    const years = r.units.filter(u => u.publicationId).flatMap(u => u.years);
    const pageIds = new Set(r.units.map(u => u.pageId));
    const basis = Object.fromEntries(BASIS_ORDER.map(b => [b, r.units.filter(u => u.basis === b).length]));
    r.units.sort((a, b) => (Math.min(...a.years, 9999) - Math.min(...b.years, 9999)) || a.pageId - b.pageId);
    return {
      ...r,
      pages: pageIds.size,
      first: years.length ? Math.min(...years) : null,
      last: years.length ? Math.max(...years) : null,
      publications: r.units.filter(u => u.publicationId).length,
      withoutBreakdown: r.units.filter(u => !u.publicationId).length,
      undated: r.units.filter(u => u.publicationId && !u.years.length).length,
      basis,
    };
  });
  const order = r => (r.language === 'German' ? -1 : r.language === NOT_RECORDED ? 2 : r.first === null ? 1 : 0);
  out.sort((a, b) => order(a) - order(b) || (a.first ?? 0) - (b.first ?? 0) || a.language.localeCompare(b.language));
  return { rows: out, textOnly, leftOut, total, shown };
}

/**
 * BibTeX, RIS and JSON of one page-level record or one publication (S3.2).
 * Pure functions without DOM, so pipeline/lab/test_lab_js.mjs runs them with
 * node. Every format carries origin, state and producer of its values, in a
 * note field (BibTeX, RIS) or as fields (JSON).
 *
 * `ctx`: { page, meta, target ('page' or a publication index as string), url,
 * accessed (YYYY-MM-DD), zweigAuthored }.
 */

import { FIELD_LABELS, ORIGIN, editionStateText, placeStateText } from './labels.js';

const NO_VALUE = 'no value recorded';

function originText(field) {
  if (field.value === null || field.value === '') return NO_VALUE;
  return ORIGIN[field.origin] || field.origin || 'origin not recorded';
}

/** The record or publication as plain fields plus the provenance statements every format carries. */
function exportModel({ page, meta, target }) {
  if (target === 'page') {
    const f = page.record.fields;
    const warnings = [];
    for (const [name, field] of Object.entries(f)) {
      for (const part of field.boundary?.parts || []) {
        if (part.result === 'fires') warnings.push(`${FIELD_LABELS[name]} "${part.part}" occurs only in the passage of the ${part.heldBy.map(p => p.year).join(' and ')} publication`);
      }
      if (field.verification === 'not-found') warnings.push(`${FIELD_LABELS[name]}: the automatic check did not find this value in the raw text`);
    }
    return {
      id: `klawiter page ${page.pageId}`,
      title: f.title.value, year: f.year.value, publisher: f.publisher.value,
      places: f.location.value ? [f.location.value] : [],
      // Several names stand comma-separated in one page-level value; the export splits them as S2.1 does.
      translators: f.translator.value ? (f.translator.occurrences?.parts.map(p => p.part) || [f.translator.value]) : [],
      extent: f.pageCount.value, language: f.language.value,
      origins: Object.fromEntries(Object.keys(FIELD_LABELS).map(k => [FIELD_LABELS[k], originText(f[k])])),
      states: [placeStateText(page.placeDecision, 'this record'), ...page.publications.map(p => `edition assignment of ${p.year ?? 'undated'}: ${editionStateText(p.editionAssignment)}`)].filter(Boolean),
      warnings,
      scope: meta.texts.record,
    };
  }
  const pub = page.publications[Number(target)];
  const f = pub.fields;
  return {
    id: pub.id,
    title: pub.title || page.title, year: pub.year, publisher: f.publisher.value,
    places: f.places.map(p => p.value), translators: f.translators.map(t => t.value),
    extent: f.extent.value, language: f.language.value,
    origins: {
      Publisher: originText(f.publisher),
      Place: f.places.length ? f.places.map(originText).join(', ') : NO_VALUE,
      Translator: f.translators.length ? f.translators.map(originText).join(', ') : NO_VALUE,
      Extent: originText(f.extent),
      Language: originText(f.language),
    },
    states: [`edition assignment: ${editionStateText(pub.editionAssignment)}`,
      ...pub.placeDecisions.map(pd => placeStateText(pd))].filter(Boolean),
    warnings: [],
    scope: `publication on wiki page ${page.pageId}`,
  };
}

/** `allExtents`: RIS has no field for the extent of a volume, so every extent goes into its note. */
function provenanceNote(m, ctx, { allExtents = false } = {}) {
  const origins = Object.entries(m.origins).map(([k, v]) => `${k}: ${v}`).join('; ');
  const s = ctx.page.dataState;
  return [
    m.extent && (allExtents || !/^\d+$/.test(String(m.extent))) ? `Extent as in the source: ${String(m.extent).replace(/\.$/, '')}.` : null,
    ctx.zweigAuthored ? 'Author Zweig, Stefan: derived from the entry type by a lab rule.' : null,
    `Origin: ${origins}.`,
    `State and producer: ${m.states.join('; ') || 'none recorded'}.`,
    m.warnings.length ? `Warnings: ${m.warnings.join('; ')}.` : null,
    `Klawiter Bibliography Lab, data commit ${s.commit.slice(0, 7)}, inputs ${s.inputsSha256Short}, rules ${s.rulesVersion}.`,
  ].filter(Boolean).join(' ');
}

function bibEscape(value) {
  return String(value).replace(/[{}\\]/g, c => `\\${c}`);
}

export function bibtex(ctx) {
  const m = exportModel(ctx);
  const key = `klawiter${ctx.page.pageId}${ctx.target === 'page' ? '' : '_' + m.id.split('/').pop().replace(/[^\w]/g, '')}`;
  const fields = [
    ctx.zweigAuthored ? ['author', 'Zweig, Stefan'] : null,
    ['title', m.title],
    m.year ? ['year', m.year] : null,
    m.publisher ? ['publisher', m.publisher] : null,
    m.places.length ? ['address', m.places.join(' and ')] : null,
    m.translators.length ? ['translator', m.translators.join(' and ')] : null,
    m.language ? ['language', m.language] : null,
    m.extent && /^\d+$/.test(String(m.extent)) ? ['pagetotal', m.extent] : null,
    ['url', ctx.url],
    ['note', provenanceNote(m, ctx)],
  ].filter(Boolean);
  return `@book{${key},\n${fields.map(([k, v]) => `  ${k} = {${bibEscape(v)}}`).join(',\n')}\n}\n`;
}

export function ris(ctx) {
  const m = exportModel(ctx);
  const lines = [['TY', 'BOOK']];
  if (ctx.zweigAuthored) lines.push(['AU', 'Zweig, Stefan']);
  lines.push(['TI', m.title]);
  if (m.year) lines.push(['PY', m.year]);
  if (m.publisher) lines.push(['PB', m.publisher]);
  for (const place of m.places) lines.push(['CY', place]);
  for (const t of m.translators) lines.push(['A4', t]);
  if (m.language) lines.push(['LA', m.language]);
  lines.push(['UR', ctx.url]);
  lines.push(['N1', provenanceNote(m, ctx, { allExtents: true })]);
  lines.push(['ER', '']);
  return lines.map(([k, v]) => `${k}  - ${v}`).join('\r\n') + '\r\n';
}

function jsonField(field, extra = {}) {
  return { value: field.value ?? null, origin: field.value === null || field.value === '' ? 'missing' : field.origin, ...extra };
}

function placeJson(pd, meta) {
  if (!pd) return null;
  if (!pd.decision) return { qid: null, state: null, producer: 'no decision recorded', link: false };
  return { qid: pd.qid ?? null, state: pd.state, producer: pd.producerShort, producerDetail: pd.producer, warning: pd.warning, link: !!pd.link, scope: meta.texts.placeScope };
}

export function jsonExport(ctx) {
  const { page, meta, target } = ctx;
  const base = { dataState: page.dataState, url: ctx.url, accessed: ctx.accessed, labelMapping: 'provisional' };
  if (target === 'page') {
    const f = page.record.fields;
    return {
      ...base,
      identifier: `klawiter page ${page.pageId}`,
      scope: meta.texts.record,
      fields: Object.fromEntries(Object.keys(FIELD_LABELS).map(k => [k, jsonField(f[k], {
        ...(f[k].verification ? { automaticCheck: f[k].verification === 'found' ? 'found in the raw text' : 'not found in the raw text' } : {}),
        ...(f[k].boundary ? { boundaryCheck: f[k].boundary } : {}),
        ...(k === 'location' ? { wikidataLink: placeJson(page.placeDecision, meta) } : {}),
      })])),
      publications: page.publications.map(p => ({ id: p.id, year: p.year, editionAssignment: p.editionAssignment })),
    };
  }
  const pub = page.publications[Number(target)];
  const f = pub.fields;
  return {
    ...base,
    identifier: pub.id,
    year: pub.year,
    editionAssignment: pub.editionAssignment,
    fields: {
      publisher: jsonField(f.publisher),
      places: f.places.map((p, j) => jsonField(p, { wikidataLink: placeJson(pub.placeDecisions[j], meta) })),
      translators: f.translators.map(t => jsonField(t)),
      extent: jsonField(f.extent),
      language: jsonField(f.language),
      editionStatement: jsonField(f.editionStatement),
      series: jsonField(f.series),
    },
  };
}

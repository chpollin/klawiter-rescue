// The print adapter of the record desk (knowledge/design.md, Record desk):
// print objects as the plain card model that docs/js/record-card.js draws,
// built from the render.js functions the workbench uses, so a print card and
// a wiki card share one anatomy. review_server.py serves this module at
// /viewer/records-print.js beside the print data; a page imports it only once
// that server answers, and nothing here reaches docs/ or a versioned file.
//
// Trust boundary: every string from the print data is escaped here before it
// enters `value.html`, the one model field RecordCard passes through as markup.

import {
  ROUTE_LABEL,
  TYPE_LABEL,
  VOLUME_LABEL,
  WIKI_STATUS,
  candidateRoute,
  candidates,
  cardLines,
  claimsShown,
  fold,
  indexGraph,
  isApparatus,
  isDerived,
  pdfHref,
  rows,
  targetsOf,
  valueName,
  valueText,
  wikiState,
} from "./render.js";

export function escape(s) {
  if (s === null || s === undefined) return "";
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

// The id rule of RecordCard._id, so that a chain id is used as given.
export const safeId = (s) => String(s).replace(/[^A-Za-z0-9_-]+/g, "-");

// In-app addresses of the docs app: a wiki record by its page and publication,
// a print object by its id. `base` is "/" on a page outside the docs app.
export function wikiHash(page, publication = null, base = "") {
  const pub = publication && String(publication).startsWith("klawiter:publication/") ? `&pub=${encodeURIComponent(String(publication).replace(/^klawiter:publication\//, ""))}` : "";
  return `${base}#entry=${Number(page)}${pub}`;
}

// A record id ("I/L/88") names its first object.
export function printHash(id, base = "") {
  const object = String(id).includes("#") ? String(id) : `${id}#1`;
  return `${base}#print=${encodeURIComponent(object)}`;
}

export const LINKS = { wiki: (page, publication) => wikiHash(page, publication), print: (id) => printHash(id) };

// The print surface's committed producer word for a language model; the
// other producers take RecordCard's words (design.md, Open design decisions).
const PRODUCER_WORD = { llm: "LLM proposal" };
const PRODUCER_DETAIL = {
  rule: "read by rule",
  compiler: "read from the compiler's address notation",
  inherited: "inherited by rule from a heading or header",
  llm: "proposed by a language model, not confirmed",
};
const KIND_WORD = { entry: "entry", header: "header", heading: "heading", reference: "cross-reference", index: "index entry", front: "front matter", tail: "tail passage" };
const EXPORTED = { confirmed: "confirmed at the last export", contested: "contested at the last export" };

// Head lines that stand before the types, in the order of render.js HEAD_ORDER.
const BEFORE_TYPES = new Set(["term", "original_title", "variant_titles", "subject", "language"]);

// A concordance value as text: a list joins, anything else that is no string or number is dropped.
function text(v) {
  if (v === null || v === undefined || v === "") return null;
  if (Array.isArray(v)) {
    const parts = v.map(text).filter(Boolean);
    return parts.length ? parts.join(", ") : null;
  }
  return typeof v === "string" || typeof v === "number" ? String(v) : null;
}

// The wiki side of a candidate as label and value pairs.
export function wikiFields(concordance, target, page) {
  const src = (target && concordance?.pubs?.[target]) ?? concordance?.pages?.[String(page)] ?? {};
  return [
    ["Title", text(src.title)],
    ["Imprint", [src.place, src.publisher, src.year].map(text).filter(Boolean).join(", ") || null],
    ["Extent", text(src.extent)],
    ["Translator", text(src.translator)],
  ].filter(([, v]) => v);
}

// The candidates of a state grouped by wiki page (D16): one page once, its
// routes under it in route order with the words that agreed, every one proposed.
export function candidatePages(state, concordance = null, links = LINKS) {
  const pages = new Map();
  for (const c of candidates(state)) {
    let page = pages.get(c.page);
    if (!page) {
      page = { page: c.page, href: links.wiki(c.page), fields: wikiFields(concordance, null, c.page), routes: [] };
      pages.set(c.page, page);
    }
    const publication = String(c.target || "").startsWith("klawiter:publication/") ? c.target : null;
    page.routes.push({
      key: c.key,
      route: c.route,
      words: candidateRoute(c),
      agreeing: c.agreeing ?? [],
      state: c.state,
      claims: c.claims,
      stale: c.stale,
      publication: publication ? publication.replace(/^klawiter:publication\//, "") : null,
      href: publication ? links.wiki(c.page, publication) : null,
      fields: publication && concordance?.pubs?.[publication] ? wikiFields(concordance, publication, c.page) : null,
    });
  }
  return [...pages.values()];
}

// The relation mark of a slip and a card: always a proposal until a person decides.
function relationOf(w) {
  const [, words] = WIKI_STATUS[w.status];
  const first = w.status === "conflict" ? null : [...w.align, ...w.same, ...w.cand][0];
  return { state: "proposed", status: w.status, route: w.status === "conflict" ? "fields differ" : first ? ROUTE_LABEL[first.route] ?? null : null, words };
}

function wikiOf(w, concordance, links) {
  const d = w.diff;
  return {
    status: w.status,
    words: WIKI_STATUS[w.status][1],
    long: WIKI_STATUS[w.status][2],
    candidates: candidatePages(w, concordance, links),
    diff: d
      ? { page: d.page, href: links.wiki(d.page, d.wiki), agree: d.agree ?? [], rows: (d.differ ?? []).map((f) => [f, text(d.printFields?.[f]) ?? "not read", text(d.wikiFields?.[f]) ?? "not given"]) }
      : null,
    notes: Object.entries(w.totals ?? {}).map(([key, n]) => claimsShown(key, w[key]?.length ?? 0, n)),
  };
}

// Address targets at their value, as links to the objects they resolve to.
export function targetsHtml(targets, links = LINKS) {
  if (!targets.length) return "";
  const shown = targets.slice(0, 6).map((t) => (t.record ? `<a href="${escape(links.print(t.record))}">${escape(t.normalized)}</a>` : `<span class="unresolved">${escape(t.normalized)} unresolved</span>`));
  if (targets.length > 6) shown.push(`<span>${targets.length - 6} more in the chain</span>`);
  return ` <span class="targets"><span aria-hidden="true">→</span><span class="visually-hidden">resolves to </span>${shown.join(" ")}</span>`;
}

// The separator a value carries before it: ", " inside one item of a group, " / " between items.
export const sepHtml = (sep) => (sep ? `<span class="sep">${escape(sep)}</span>` : "");

// Marks that RecordCard.sourceBody draws: inside the text, nested, never crossing.
function drawable(marks, length) {
  const valid = marks.filter((mk) => Number.isInteger(mk.start) && Number.isInteger(mk.end) && mk.start >= 0 && mk.end > mk.start && mk.end <= length).sort((a, b) => a.start - b.start || b.end - a.end);
  const kept = new Set();
  const stack = [{ start: 0, end: length, kind: "root" }];
  for (const mk of valid) {
    while (stack.length > 1 && mk.start >= stack[stack.length - 1].end) stack.pop();
    if (mk.end > stack[stack.length - 1].end) continue;
    if (mk.kind === "block" && stack.some((n) => n.kind === "block")) continue;
    kept.add(mk);
    stack.push(mk);
  }
  return kept;
}

// One value of the card model with its chain from the literal to the source file.
function valueOf(object, row, byId, idBase, links, extra = {}) {
  const record = byId.get(row.source);
  const file = record ? byId.get(record.derivedFrom) : null;
  const plan = byId.get(row.rule);
  const own = row.source === object.entry;
  const targets = targetsOf(object, row.field);
  const lines = [];
  if (record && !own) lines.push(`the passage stands in this ${KIND_WORD[record.kind] ?? "record"}, not in the entry of the card`);
  for (const t of targets) lines.push(`${t.normalized} ${t.record ? `resolves to ${t.record}` : "resolves to no record"}`);
  if (object.relation?.target && row.field.startsWith("relation")) lines.push(`relation target ${object.relation.target}`);
  const exported = row.node.reviewAction === "correct" ? "corrected and confirmed at the last export" : EXPORTED[row.node.reviewState];
  const chainId = safeId(`${idBase}-v${row.index}`);
  const shown = row.text ?? valueText(row);
  return {
    text: shown,
    html: `${sepHtml(extra.sep)}${extra.sub ? `<span class="rc-sub">${escape(shown)}</span>` : escape(shown)}${targetsHtml(targets, links)}`,
    sep: extra.sep ?? "",
    sub: Boolean(extra.sub),
    index: row.index,
    field: row.field,
    name: row.name ?? valueName(row.field),
    producer: row.producer,
    producerWord: PRODUCER_WORD[row.producer],
    state: row.node.reviewState ?? row.state ?? "not-reviewed",
    stateText: exported,
    derivedFrom: isDerived(row.node) ? "the passage by its rule" : undefined,
    own,
    targets,
    chainId,
    chain: {
      passage: { text: row.exact, textStart: row.start, textEnd: row.end, scope: own ? "" : `of record ${row.source}, not the entry shown`, markId: null },
      record: record
        ? { id: record.id, type: KIND_WORD[record.kind] ?? record.kind, volume: record.volume, part: record.part, address: record.address || undefined, pdfPage: record.pdfPage, pdfPageEnd: record.pdfPageEnd, line: record.line, sha256: record.sha256, extra: lines }
        : { extra: [`record ${row.source} is not in this chunk`] },
      sourceFile: file ? { file: file.fileName, sha256: file.sha256Prefix } : { words: "source file not named in the chunk" },
      producer: { words: PRODUCER_DETAIL[row.producer] ?? "", rule: plan ? plan.label : row.rule, model: plan?.llm_model ?? undefined },
    },
  };
}

// The row RecordCard.head builds for the title, so that its chain resolves.
export const titleRow = (m) => ({ key: "title", label: "Title", idBase: `${m.id}-title`, values: [m.titleValue] });

// Every chain of a model by the id its button controls: {r, i} for RecordCard.chainSteps(m, r, i).
export function chainRows(m) {
  const map = new Map();
  if (m.titleValue?.chain) map.set(m.titleValue.chainId, { r: titleRow(m), i: 0 });
  for (const g of m.groups ?? []) for (const r of g.rows) r.values.forEach((v, i) => v?.chain && map.set(v.chainId, { r, i }));
  return map;
}

/**
 * The card model of one print object (record-card.js): head, one group of
 * value rows in reading order with a chain per value, the entry text with the
 * object and its own passages marked, the relation and the wiki candidates.
 * `entry` is the object's index row; `siblings` the object ids of its entry.
 */
export function cardModel({ entry = null, object, byId, concordance = null, siblings = null, links = LINKS, idBase = null }) {
  const record = byId.get(object.entry);
  const base = idBase ?? `print-${object.id}`;
  const all = rows(object).map((r) => ({ ...r, name: valueName(r.field), text: valueText(r) }));
  const lines = cardLines(all);
  const value = (row, extra) => valueOf(object, row, byId, base, links, extra);
  const listed = (items, key, label, sepOf) => ({ key, label, idBase: `${base}-${key}`, separator: "", values: items.map((it, i) => value(it.row ?? it, { sep: sepOf(it, i, items), sub: it.sub })) });
  const groupRows = [];
  const [title, ...moreTitles] = lines.title;
  if (moreTitles.length) groupRows.push(listed(moreTitles, "title", "Title", (it, i) => (i ? ", " : "")));
  if (lines.subtitle.length) groupRows.push(listed(lines.subtitle, "subtitle", "Subtitle", (it, i) => (i ? ", " : "")));
  const types = lines.types.length ? listed(lines.types, "types", lines.types.length > 1 ? "Types" : "Type", (it, i) => (i ? ", " : "")) : null;
  let typesPlaced = !types;
  for (const line of lines.lines) {
    if (!typesPlaced && !BEFORE_TYPES.has(line.key)) {
      groupRows.push(types);
      typesPlaced = true;
    }
    groupRows.push(listed(line.items, line.key, line.label, (it, i, items) => (i === 0 ? "" : it.item === items[i - 1].item ? ", " : " / ")));
  }
  if (!typesPlaced) groupRows.push(types);

  const position = siblings && siblings.length > 1 ? `object ${siblings.indexOf(object.id) + 1} of ${siblings.length} in the entry` : "";
  const titleValue = title ? value(title, {}) : null;
  const typeWord = types ? null : isApparatus(object) ? TYPE_LABEL[record?.kind] ?? "apparatus" : TYPE_LABEL[entry?.types?.[0]] ?? "no type read";
  const m = {
    kind: "print",
    id: object.id,
    permalink: links.print(object.id),
    volume: object.volume,
    address: object.address || "",
    sourceSign: { label: VOLUME_LABEL[object.volume] ?? object.volume, pdfPage: record?.pdfPage },
    pdfHref: record ? pdfHref(object.volume, record.pdfPage) : null,
    position,
    title: titleValue ? titleValue.text : entry?.title || object.address || "Untitled",
    titleValue,
    type: typeWord,
    review: { state: entry?.review ? "open" : "not-reviewed", producer: "no person", contested: false },
    snippet: entry?.snippet ?? "",
    groups: [{ rows: groupRows }],
    sourceText: { label: "Entry text", text: record?.text ?? "", marks: [] },
  };
  const w = wikiState(concordance, object.id, object.entry);
  m.relation = relationOf(w);
  m.wiki = wikiOf(w, concordance, links);

  // The object's span is a block; a value that spans exactly the object marks nothing in it.
  const span = object.selector;
  const marks = [{ start: span.start, end: span.end, kind: "block", label: position ? `Object ${siblings.indexOf(object.id) + 1} of ${siblings.length}` : "This object" }];
  const byMark = new Map();
  for (const v of [titleValue, ...groupRows.flatMap((r) => r.values)].filter(Boolean)) {
    const p = v.chain.passage;
    if (!v.own || (p.textStart === span.start && p.textEnd === span.end)) continue;
    const mk = { start: p.textStart, end: p.textEnd, kind: "value", key: v.field, valueIndex: v.index, id: `mark-${v.chainId}` };
    marks.push(mk);
    byMark.set(mk, v);
  }
  const kept = drawable(marks, m.sourceText.text.length);
  for (const [mk, v] of byMark) if (kept.has(mk)) v.chain.passage.markId = mk.id;
  m.sourceText.marks = marks.filter((mk) => kept.has(mk));
  return m;
}

// A slip of one index row: two lines and three marks, nothing else.
function slipModel(o, concordance, links) {
  return {
    kind: "print",
    id: o.id,
    // The entry an object belongs to, so a list can count entries rather than objects.
    entry: o.entry,
    permalink: links.print(o.id),
    volume: o.volume,
    part: o.part,
    address: o.address || "",
    sourceSign: { label: VOLUME_LABEL[o.volume] ?? o.volume, pdfPage: o.page },
    title: o.title || "",
    snippet: o.snippet || "",
    type: o.types?.length ? TYPE_LABEL[o.types[0]] ?? o.types[0] : null,
    relation: relationOf(wikiState(concordance, o.id, o.entry)),
    review: { state: o.review ? "open" : "not-reviewed", producer: "no person", contested: false },
  };
}

// The loaded print data of this page; null until load() succeeds.
let store = null;

/**
 * Loads the print index, vocabulary and wiki concordance once from the review
 * server. Throws where the index does not answer, which the caller reads as
 * "print unavailable"; without the concordance every relation reads "No candidate".
 */
// The browser's fetch must be called on its window, so the default wraps it.
export async function load({ origin = globalThis.location?.origin, fetch: get = (...args) => globalThis.fetch(...args) } = {}) {
  if (store) return { objects: store.index.length };
  const url = (name) => new URL(`/viewer/${name}`, origin);
  const index = await get(url("index.json"));
  if (!index.ok) throw new Error(`index.json: ${index.status}`);
  const rowsOf = await index.json();
  if (!Array.isArray(rowsOf)) throw new Error("index.json is no list of objects");
  const vocab = await get(url("vocab.json")).then((r) => (r.ok ? r.json() : null)).catch(() => null);
  const concordance = await get(url("wiki_concordance.json")).then((r) => (r.ok ? r.json() : null)).catch(() => null);
  const siblings = new Map();
  for (const o of rowsOf) siblings.set(o.entry, [...(siblings.get(o.entry) ?? []), o.id]);
  store = { origin, get, index: rowsOf, byId: new Map(rowsOf.map((o) => [o.id, o])), vocab, concordance, siblings, chunks: new Map() };
  return { objects: rowsOf.length };
}

function loaded() {
  if (!store) throw new Error("records-print: load() first");
  return store;
}

/**
 * The slips the filter selects, in printed order: {q, volume, part, kind,
 * wiki, review}. `q` matches the folded search field; `review: "sample"`
 * keeps the review sample; `wiki` is a status of render.js WIKI_STATUS.
 */
export function list(filter = {}) {
  const s = loaded();
  const q = filter.q ? fold(String(filter.q)) : "";
  const out = [];
  for (const o of s.index) {
    if (q && !o.search.includes(q)) continue;
    if (filter.volume && o.volume !== filter.volume) continue;
    if (filter.part && o.part !== filter.part) continue;
    if (filter.kind && !(o.types ?? []).includes(filter.kind)) continue;
    if (filter.review === "sample" && !o.review) continue;
    const slip = slipModel(o, s.concordance, LINKS);
    if (filter.wiki && slip.relation.status !== filter.wiki) continue;
    out.push(slip);
  }
  return out;
}

async function graph(o) {
  const s = loaded();
  const url = new URL(o.chunk, `${s.origin}/viewer/`).href;
  if (!s.chunks.has(url)) {
    const response = await s.get(url);
    if (!response.ok) throw new Error(`${o.chunk}: ${response.status}`);
    s.chunks.set(url, indexGraph(await response.json()));
  }
  return s.chunks.get(url);
}

/** The card model of one print object by its id, or null where no object has it. */
export async function model(id) {
  const s = loaded();
  const o = s.byId.get(id);
  if (!o) return null;
  const g = await graph(o);
  const object = g.byId.get(id);
  return object ? cardModel({ entry: o, object, byId: g.byId, concordance: s.concordance, siblings: s.siblings.get(o.entry) }) : null;
}

/** Forgets the loaded data; for tests that load another fixture. */
export function reset() {
  store = null;
}

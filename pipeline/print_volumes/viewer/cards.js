// The print card workbench (knowledge/design.md, Card workbench). Every print object is
// a card; three views lay them out (sections beside a card, source lanes
// beside a card, a grid of cards), and review decisions go to review_server.py
// on the same origin. Data come from p12 beside this page (index.json,
// vocab.json, wiki_concordance.json and the JSON-LD chunks); nothing is fetched
// from elsewhere.
//
// The decisions feed the measurement of p13, so three guards hold throughout:
// exactly one card is active, and keys act on it only while it holds the focus
// and lies in view (acceptsKeys); a card that is loading or saving takes no
// key; and a decision names a value the card displays, posted only while that
// card is still the one on screen.
//
// A card is drawn by the record desk's shared card (/js/record-card.js, see
// knowledge/design.md, Record desk) from the model of the print adapter
// (records-print.js), so a print card here and in Records has one anatomy:
// every value names its producer on a button that opens its own chain. The
// workbench adds its decision layer to that model: each value becomes a pick
// button with its decision sign, and the card keeps its foot of decisions.

import { cardModel, chainRows, escape, safeId, sepHtml, targetsHtml, titleRow, wikiHash } from "./records-print.js";
import {
  DECISION_WORD,
  SECTION_NAME,
  STATE_DECISION,
  TYPE_LABEL,
  VOLUME_LABEL,
  VOLUME_SHORT,
  WIKI_STATUS,
  WIKI_STATUS_ORDER,
  about,
  acceptsKeys,
  confirmable,
  correctionValue,
  decisionLine,
  effective,
  findPassage,
  fold,
  history as decisionHistory,
  inSight,
  indexGraph,
  isApparatus,
  isInherited,
  laneOf,
  missingLabel,
  naturalAddressKey,
  objectName,
  objectReview,
  ownDecisions,
  pdfHref,
  rows,
  sectionCode,
  segments,
  sortRecords,
  targetOf,
  valueName,
  valueText,
  vocabFor,
  wikiState,
} from "./render.js";

// record-card.js is a classic script whose `const RecordCard` is a global
// binding rather than a property of globalThis; a module sees that binding.
const Card = globalThis.RecordCard ?? (typeof RecordCard === "undefined" ? null : RecordCard);

// Links of this page: a print object stays in the workbench, a wiki record
// opens in the local docs app the review server serves at its root.
const objectUrl = (id) => {
  const object = id.includes("#") ? id : `${id}#1`;
  return `#/?${new URLSearchParams({ q: object.split("#")[0], o: object })}`;
};
const LINKS = { wiki: (page, publication) => wikiHash(page, publication, "/"), print: objectUrl };
const STACKED = "(max-width: 60rem)";
const reducedMotion = () => Boolean(window.matchMedia?.("(prefers-reduced-motion: reduce)").matches);

const TRAY = 30;
const VIEWS = new Set(["axis", "lanes", "board"]);
const LANES = [
  ["print", "Print, no wiki candidate"],
  ["shared", "Print with a wiki candidate"],
  ["wiki", "Wiki, no print candidate"],
];
const SORTS = [
  ["book", "Printed order"],
  ["wiki", "Wiki candidates first"],
  ["address", "Address"],
  ["title", "Title"],
  ["year-asc", "First year in the text, oldest"],
  ["year-desc", "First year in the text, newest"],
  ["review", "Open sample first"],
];
const SECTION_SORTS = [
  ["default", "A to R"],
  ["count", "Most cards"],
  ["wiki", "Most wiki candidates"],
  ["name", "Name"],
];
// Years the first-year sort reads from an index line; a sort aid, never a value.
const YEAR = /\b(1[5-9]\d\d|20[0-2]\d)\b/;

const el = (id) => document.getElementById(id);
const data = {
  index: [],
  records: [],
  byId: new Map(),
  // The objects of each entry in printed order, to say which one a card is.
  siblings: new Map(),
  vocab: { roles: [], types: [], languages: [], missingFields: [] },
  wiki: { links: {}, pages: {}, pubs: {}, wikiOnlyPages: [] },
  chunks: new Map(),
};
// The log holds only the decisions of the reviewer it was loaded for.
const review = { recording: false, log: [], active: new Map(), loadedFor: "" };
const ui = { section: "", sectionSort: "default", laneSorts: { print: "book", shared: "wiki", wiki: "address" }, order: new Map(), dragged: null };

// The cards on screen by id, the active one, and the guards of the review.
const cards = new Map();
let activeId = null;
let loadToken = 0;
let loading = false;
let busy = false;
let pending = null;
let renderSeq = 0;
let sessionName = "";

function make(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === undefined || value === null || value === false) continue;
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else node.setAttribute(key, value === true ? "" : value);
  }
  for (const child of children) if (child !== null && child !== undefined && child !== false) node.append(child);
  return node;
}

const SVG_NS = "http://www.w3.org/2000/svg";
const ICONS = {
  pdf: ["M3 2.5h6.5L13 6v7.5a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1v-10a1 1 0 0 1 1-1z", "M9 2.5V6h3.5", "M5 9.5h6", "M5 12h4"],
  wiki: ["M8 14A6 6 0 1 0 8 2a6 6 0 0 0 0 12z", "M2.3 8h11.4", "M8 2c1.8 1.7 2.7 3.7 2.7 6S9.8 12.3 8 14c-1.8-1.7-2.7-3.7-2.7-6S6.2 3.7 8 2z"],
  text: ["M2.5 4h11", "M2.5 7h11", "M2.5 10h7", "M11.5 9.5l2 2-2 2"],
  fields: ["M2.5 3h11v10h-11z", "M2.5 6.5h11", "M2.5 10h11", "M6.5 3v10"],
  titleYear: ["M8 14A6 6 0 1 0 8 2a6 6 0 0 0 0 12z", "M6.3 6.2a1.8 1.8 0 1 1 2.4 1.7c-.5.2-.7.6-.7 1.1", "M8 11.3h.01"],
  check: ["M3 8.5l3.2 3.2L13 4.8"],
  checkAll: ["M1.8 8.5l2.8 2.8L10.5 5", "M6.5 8.5l2.8 2.8L14.5 5"],
  edit: ["M11.5 2.5l2 2L5.5 12.5 2.5 13.5l1-3 8-8z"],
  question: ["M6.2 6a2 2 0 1 1 2.6 1.9c-.6.3-.8.7-.8 1.4", "M8 12.2h.01"],
  info: ["M8 14A6 6 0 1 0 8 2a6 6 0 0 0 0 12z", "M8 7.5v3.8", "M8 4.8h.01"],
  plus: ["M8 3.5v9", "M3.5 8h9"],
  alert: ["M8 2.2L1.6 13.5h12.8L8 2.2z", "M8 6.5v3.5", "M8 11.8h.01"],
  arrow: ["M3 8h9", "M9 5l3 3-3 3"],
};

function icon(name) {
  const svg = document.createElementNS(SVG_NS, "svg");
  for (const [k, v] of Object.entries({ viewBox: "0 0 16 16", fill: "none", stroke: "currentColor", "stroke-width": "1.6", "stroke-linecap": "round", "stroke-linejoin": "round", "aria-hidden": "true", class: "ico" })) {
    svg.setAttribute(k, v);
  }
  for (const d of ICONS[name] ?? []) {
    const p = document.createElementNS(SVG_NS, "path");
    p.setAttribute("d", d);
    svg.append(p);
  }
  return svg;
}

// The same icon as markup, for cards drawn from strings.
const iconHtml = (name) =>
  `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" class="ico">${(ICONS[name] ?? []).map((d) => `<path d="${d}"/>`).join("")}</svg>`;

// Card markup is built from escaped parts only, so parsing it adds no markup of the data.
function fromHtml(html) {
  const t = document.createElement("template");
  t.innerHTML = html;
  return t.content.firstElementChild;
}

const hidden = (text) => make("span", { class: "visually-hidden", text });
const count = (n) => n.toLocaleString("en-US");

// Route and messages

function params() {
  const query = location.hash.includes("?") ? location.hash.split("?")[1] : "";
  return new URLSearchParams(query);
}

function readFilters() {
  const p = params();
  const raw = p.get("q") || "";
  return {
    raw,
    q: fold(raw),
    volume: p.get("v") || "",
    part: p.get("part") || "",
    kind: p.get("k") || "",
    wiki: p.get("w") || "",
    review: p.get("r") || "",
    sort: p.get("sort") || "book",
    view: VIEWS.has(p.get("d")) ? p.get("d") : "axis",
    page: Math.max(1, Number(p.get("page")) || 1),
    object: p.get("o") || "",
  };
}

function hashWith(changes) {
  const p = params();
  for (const [key, value] of Object.entries(changes)) {
    if (value) p.set(key, value);
    else p.delete(key);
  }
  const query = p.toString();
  return query ? `#/?${query}` : "#/";
}

// Links of the replaced single-object viewer keep working.
function legacyRoute() {
  const object = location.hash.match(/^#\/o\/([^/?]+)/);
  if (object) {
    const id = decodeURIComponent(object[1]);
    history.replaceState(null, "", `#/?${new URLSearchParams({ q: id.split("#")[0], o: id })}`);
  } else if (location.hash.startsWith("#/review")) {
    history.replaceState(null, "", "#/?r=open");
  } else if (location.hash.startsWith("#/help")) {
    history.replaceState(null, "", "#/");
    el("help-dialog").showModal();
  }
}

function showError(message) {
  el("error").textContent = message;
  el("error").hidden = false;
}

function say(text) {
  el("message").textContent = text;
}

// Review state

function completeIds() {
  const done = new Set();
  for (const d of review.active.values()) if (d.decision === "complete") done.add(d.object);
  return done;
}

const sample = () => data.index.filter((o) => o.review);

function nextOpenSample(currentId = null) {
  const done = completeIds();
  const list = sample();
  const at = currentId ? list.findIndex((o) => o.id === currentId) : -1;
  return [...list.slice(at + 1), ...list.slice(0, at + 1)].find((o) => !done.has(o.id) && o.id !== currentId) ?? null;
}

function reviewerName() {
  try {
    return localStorage.getItem("print-reviewer") || "";
  } catch {
    return "";
  }
}

// Asks for the reviewer once; the name stays in this browser.
function askReviewer() {
  return new Promise((resolve) => {
    const dialog = el("reviewer-dialog");
    el("reviewer-input").value = reviewerName() || sessionName;
    const done = () => {
      dialog.removeEventListener("close", done);
      const name = dialog.returnValue === "ok" ? el("reviewer-input").value.trim() : "";
      if (name) {
        try {
          localStorage.setItem("print-reviewer", name);
        } catch {
          // Storage may be refused; the name then holds for this page only.
          sessionName = name;
        }
      }
      renderHeader();
      resolve(name || reviewerName() || sessionName);
    };
    dialog.returnValue = "";
    dialog.addEventListener("close", done);
    dialog.showModal();
  });
}

async function reviewer() {
  return reviewerName() || sessionName || (await askReviewer());
}

function renderHeader() {
  const done = completeIds();
  const list = sample();
  const reviewView = params().get("r") === "open";
  el("nav-review").textContent = review.recording ? `Review sample (${list.filter((o) => done.has(o.id)).length}/${list.length})` : "Review sample";
  for (const [id, current] of [["nav-review", reviewView], ["nav-desk", !reviewView]]) {
    if (current) el(id).setAttribute("aria-current", "page");
    else el(id).removeAttribute("aria-current");
  }
  el("reviewer-line").hidden = !review.recording;
  el("reviewer-name").textContent = reviewerName() || sessionName || "not set";
}

// Data

async function chunk(url) {
  if (!data.chunks.has(url)) {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`${url}: ${response.status}`);
    data.chunks.set(url, indexGraph(await response.json()));
  }
  return data.chunks.get(url);
}

const canDecide = (model) => review.recording && Boolean(model.object) && !isApparatus(model.object);

function inReview(o, mode, done) {
  if (!o.review) return false;
  if (mode === "open") return !done.has(o.id);
  if (mode === "done") return done.has(o.id);
  return true;
}

// The records the filters select, and per wiki status how many there are.
function filterRecords(f, done) {
  const hits = [];
  const counts = Object.fromEntries(WIKI_STATUS_ORDER.map((s) => [s, 0]));
  let all = 0;
  for (const o of data.records) {
    if (f.q && !o.search.includes(f.q)) continue;
    if (f.part && o.part !== f.part) continue;
    if (f.kind && (f.kind === "(none)" ? o.types.length !== 0 : !o.types.includes(f.kind))) continue;
    if (f.review && !inReview(o, f.review, done)) continue;
    if (f.volume && o.volume !== f.volume) continue;
    counts[o.wiki.status] += 1;
    // Wiki pages without a print candidate join a list where it asks for
    // them: by their filter or volume, in the source lanes, or by a search.
    const wikiShown = f.volume === "WIKI" || f.view === "lanes" || f.wiki === "wiki-only" || Boolean(f.q);
    if (o.isWikiOnly && !wikiShown) continue;
    all += 1;
    if (f.wiki && o.wiki.status !== f.wiki) continue;
    hits.push(o);
  }
  return { hits, counts, all };
}

// Header strip: scope, source filters, pager

function renderStrip(f, counts, all, hits) {
  const scope = [];
  if (f.volume === "WIKI" || f.wiki === "wiki-only") scope.push("MediaWiki pages");
  else if (f.volume) scope.push(VOLUME_LABEL[f.volume]);
  else scope.push(f.view === "lanes" || f.q ? "Print volumes and wiki pages" : "All print volumes");
  if (f.part) scope.push(`part ${f.part}`);
  if (f.kind) scope.push(f.kind === "(none)" ? "no type read" : TYPE_LABEL[f.kind] ?? f.kind);
  el("scope-heading").textContent = `${scope.join(", ")} (${count(hits.length)})`;
  const pill = (value, label, n) =>
    make("button", { type: "button", class: "stat-pill", "data-wiki": value, "aria-pressed": String(f.wiki === value), title: value ? WIKI_STATUS[value][2] : null }, value ? icon(WIKI_STATUS[value][0]) : null, `${label} (${count(n)})`);
  el("source-pills").replaceChildren(
    pill("", "All", all),
    ...WIKI_STATUS_ORDER.filter((s) => counts[s] > 0 || f.wiki === s).map((s) => pill(s, WIKI_STATUS[s][1], counts[s]))
  );
  el("reset-filters").hidden = !(f.raw || f.volume || f.part || f.kind || f.wiki || f.review || f.sort !== "book");
}

function renderPager(page, pages, text) {
  for (const id of ["page", "page-bottom"]) el(id).textContent = text;
  for (const id of ["prev", "prev-bottom"]) el(id).disabled = page <= 1;
  for (const id of ["next", "next-bottom"]) el(id).disabled = page >= pages;
}

// The tray of a list: the page holding the requested object, else the page asked for.
function tray(list, f) {
  const pages = Math.max(1, Math.ceil(list.length / TRAY));
  const at = f.object ? list.findIndex((o) => o.id === f.object) : -1;
  const page = at >= 0 ? Math.floor(at / TRAY) + 1 : Math.min(pages, f.page);
  const start = (page - 1) * TRAY;
  return { page, pages, start, slice: list.slice(start, start + TRAY) };
}

function ordered(slice, key) {
  const saved = ui.order.get(key);
  if (!saved) return slice;
  const pos = new Map(saved.map((id, i) => [id, i]));
  return [...slice].sort((a, b) => (pos.get(a.id) ?? 1e9) - (pos.get(b.id) ?? 1e9));
}

function sortSelect(attr, value, options, label, target = "") {
  const select = make("select", { class: "col-select", [attr]: target, "aria-label": label }, ...options.map(([v, t]) => make("option", { value: v, text: t })));
  select.value = value;
  return select;
}

// Slips: one line per record on an axis, opened with a click or Enter

function wikiSign(status) {
  const [name, label, long] = WIKI_STATUS[status];
  return make("span", { class: `wiki-sign status-${status}`, title: long }, icon(name), label);
}

function titleNode(entry, cls) {
  if (entry.title) return make("span", { class: cls, text: entry.title });
  const start = (entry.snippet || "").replace(/[\s.,;:]+$/, "");
  return make("span", { class: `${cls} untitled` }, hidden("No title read, the text begins "), start ? `${start}…` : "No title read");
}

function buildSlip(entry, listKey, done) {
  const where = entry.isWikiOnly
    ? `MediaWiki, ${entry.part}`
    : `${VOLUME_LABEL[entry.volume]}, ${sectionCode(entry.part)} ${SECTION_NAME[sectionCode(entry.part)] ?? ""}, PDF page ${entry.page}`.replace(/ ,/, ",");
  const kind = entry.types.length ? TYPE_LABEL[entry.types[0]] ?? entry.types[0] : entry.isWikiOnly ? entry.wikiType.replaceAll("-", " ") : "";
  const open = make(
    "button",
    { type: "button", class: "slip-open", "data-open": entry.id },
    make(
      "span",
      { class: "slip-line" },
      make("span", { class: "card-address", text: entry.address || (entry.isWikiOnly ? "" : "Unnumbered") }),
      kind ? make("span", { class: "slip-kind", text: kind }) : null,
      wikiSign(entry.wiki.status),
      done.has(entry.id) ? make("span", { class: "done-sign", title: "Review complete" }, icon("check"), hidden("review complete")) : null
    ),
    titleNode(entry, "slip-title"),
    make("span", { class: "slip-meta", text: where })
  );
  const move = (delta, label, arrow) =>
    make("button", { type: "button", class: "slip-move", "data-move": String(delta), "aria-label": label, title: label, tabindex: "-1", text: arrow });
  const slip = make(
    "li",
    { class: "slip", "data-id": entry.id, "data-list": listKey, draggable: "true" },
    open,
    make("span", { class: "slip-moves" }, move(-1, "Move up in this list", "↑"), move(1, "Move down in this list", "↓"))
  );
  if (activeId === entry.id) setActive(slip, true);
  return slip;
}

function slipList(key, entries, done, label) {
  return make("ol", { class: "slip-list", "data-list": key, "aria-label": label }, ...entries.map((e) => buildSlip(e, key, done)));
}

function column(cls, title, control, ...body) {
  return make(
    "section",
    { class: `col ${cls}`, "aria-label": title },
    make("div", { class: "col-head" }, make("h2", { class: "col-title", text: title }), control),
    make("div", { class: "col-body" }, ...body)
  );
}

// Below the stacking width the card comes first, and this pager above it
// steps through the slips of its list without scrolling past them (D15).
function inspectorColumn() {
  const step = (delta, label, text) => make("button", { type: "button", class: "text-btn", "data-step": String(delta), "aria-label": label, text });
  const pager = make("nav", { class: "slip-pager", "aria-label": "Entries of the list" }, step(-1, "Previous entry", "‹ Previous"), make("span", { class: "tray-range", id: "slip-position" }), step(1, "Next entry", "Next ›"));
  return column("detail-col", "Card", pager, make("div", { id: "inspector" }));
}

// The pager says where the active slip stands in its list.
function renderSlipPager(id) {
  const where = el("slip-position");
  if (!where) return;
  const slip = document.querySelector(`.slip[data-id="${CSS.escape(id)}"]`);
  const all = slip ? [...slip.closest(".slip-list").querySelectorAll(".slip")] : [];
  const at = all.indexOf(slip);
  where.textContent = at >= 0 ? `${count(at + 1)} of ${count(all.length)}` : "";
  for (const b of document.querySelectorAll(".slip-pager [data-step]")) {
    const target = all[at + Number(b.dataset.step)];
    b.disabled = at < 0 || !target;
    b.dataset.target = target?.dataset.id ?? "";
  }
}

// Views

function renderAxis(f, hits, done) {
  const groups = new Map();
  for (const o of hits) {
    const code = o.isWikiOnly ? "" : sectionCode(o.part);
    const key = o.isWikiOnly ? `wiki:${o.part}` : code;
    if (!groups.has(key)) groups.set(key, { key, code, label: o.isWikiOnly ? o.part : SECTION_NAME[code] ?? `Part ${o.part}`, items: [], wiki: 0 });
    const g = groups.get(key);
    g.items.push(o);
    if (o.wiki.status !== "none") g.wiki += 1;
  }
  const list = [...groups.values()];
  const by = {
    count: (a, b) => b.items.length - a.items.length,
    wiki: (a, b) => b.wiki / b.items.length - a.wiki / a.items.length,
    name: (a, b) => a.label.localeCompare(b.label, "en"),
    default: (a, b) => (a.code || "~").localeCompare(b.code || "~", "en") || a.label.localeCompare(b.label, "en"),
  };
  list.sort(by[ui.sectionSort] ?? by.default);
  // The compiler's sections A to R come first; apparatus parts and wiki
  // categories follow under headings of their own (D17).
  const kinds = [
    ["", list.filter((g) => /^[A-R]$/.test(g.code))],
    ["Apparatus", list.filter((g) => g.code && !/^[A-R]$/.test(g.code))],
    ["Wiki pages", list.filter((g) => !g.code)],
  ];
  if (ui.section && !groups.has(ui.section)) ui.section = "";
  const group = ui.section ? groups.get(ui.section) : null;
  const items = group ? group.items : hits;
  const { page, pages, start, slice } = tray(items, f);
  const key = `axis:${ui.section || "all"}:${page}`;
  renderPager(page, pages, items.length ? `${count(start + 1)}–${count(start + slice.length)} of ${count(items.length)}` : "None");

  const section = (g) =>
    make(
      "button",
      {
        type: "button",
        class: "section-item",
        "data-section": g ? g.key : "",
        "aria-pressed": String(ui.section === (g ? g.key : "")),
        title: g ? `${g.label}, ${count(g.items.length)} cards, ${count(g.wiki)} with a wiki candidate` : null,
      },
      make("span", { class: "section-code", text: g ? g.code || "Wiki" : "All" }),
      make("span", { class: "section-name", text: g ? g.label : "All sections" }),
      make("span", { class: "section-count", text: count(g ? g.items.length : hits.length) })
    );
  const sections = kinds.flatMap(([heading, items]) => (items.length ? [heading ? make("h3", { class: "section-group", text: heading }) : null, ...items.map(section)] : []));
  el("desk").replaceChildren(
    column("section-col", "Sections", sortSelect("data-section-sort", ui.sectionSort, SECTION_SORTS, "Order of the sections"), section(null), ...sections),
    column(
      "slip-col",
      `${group ? group.label : "All entries"} (${count(items.length)})`,
      sortSelect("data-sort", f.sort, SORTS, "Order of the entries"),
      slipList(key, ordered(slice, key), done, "Entries")
    ),
    inspectorColumn()
  );
  return slice;
}

function renderLanes(f, hits, done) {
  const buckets = { print: [], shared: [], wiki: [] };
  for (const o of hits) buckets[laneOf(o.wiki.status)].push(o);
  const longest = Math.max(...Object.values(buckets).map((b) => b.length));
  const pages = Math.max(1, Math.ceil(longest / TRAY));
  const page = Math.min(pages, f.page);
  const start = (page - 1) * TRAY;
  renderPager(page, pages, longest ? `Tray ${page} of ${pages}` : "None");
  const shown = [];
  const cols = LANES.map(([lane, title]) => {
    const key = `lane:${lane}:${page}`;
    const slice = ordered(sortRecords(buckets[lane], ui.laneSorts[lane], done).slice(start, start + TRAY), key);
    shown.push(...slice);
    return column("lane-col", `${title} (${count(buckets[lane].length)})`, sortSelect("data-lane-sort", ui.laneSorts[lane], SORTS.filter(([v]) => v !== "review"), `Order of ${title}`, lane), slipList(key, slice, done, title));
  });
  el("desk").replaceChildren(...cols, inspectorColumn());
  return shown;
}

async function renderBoard(f, hits, seq) {
  const { page, pages, start, slice } = tray(hits, f);
  renderPager(page, pages, hits.length ? `${count(start + 1)}–${count(start + slice.length)} of ${count(hits.length)}` : "None");
  await Promise.all([...new Set(slice.filter((o) => !o.isWikiOnly).map((o) => o.chunk))].map(chunk));
  if (seq !== renderSeq) return null;
  const nodes = [];
  for (const entry of slice) {
    const model = entry.isWikiOnly ? buildWikiCard(entry) : buildCardFor(entry, data.chunks.get(entry.chunk));
    if (!model) continue;
    cards.set(entry.id, model);
    nodes.push(model.dom.article);
  }
  el("desk").replaceChildren(...nodes);
  return slice;
}

async function renderDesk() {
  const seq = ++renderSeq;
  el("error").hidden = true;
  closeForm();
  renderHeader();
  const f = readFilters();
  if (document.activeElement !== el("q")) el("q").value = f.raw;
  for (const [id, value] of [["volume", f.volume], ["kind", f.kind], ["review-filter", f.review], ["view", f.view]]) el(id).value = value;
  if (el("board-sort-wrap")) {
    el("board-sort-wrap").hidden = f.view !== "board";
    el("board-sort").value = f.sort;
  }
  const desk = el("desk");
  desk.className = `desk view-${f.view}`;
  // Nothing on screen takes a key until the new cards are there.
  cards.clear();
  loading = true;
  desk.replaceChildren(make("p", { class: "loading", text: "Loading the cards…" }));
  const done = completeIds();
  const { hits, counts, all } = filterRecords(f, done);
  const list = sortRecords(hits, f.sort, done);
  renderStrip(f, counts, all, list);
  let shown;
  try {
    if (f.view === "axis") shown = renderAxis(f, list, done);
    else if (f.view === "lanes") shown = renderLanes(f, list, done);
    else shown = await renderBoard(f, list, seq);
  } finally {
    if (seq === renderSeq) loading = false;
  }
  if (!shown || seq !== renderSeq) return;
  const keep = [f.object, activeId].find((id) => id && shown.some((o) => o.id === id));
  const first = keep ?? shown[0]?.id;
  activeId = null;
  if (first) await activate(first);
}

// The active card

// The active slip and card carry aria-current beside their colour, and only
// the active slip's move buttons are tab stops.
function markActive(id) {
  for (const node of document.querySelectorAll(".slip.is-active, .card.is-active")) setActive(node, false);
  for (const node of document.querySelectorAll(`.slip[data-id="${CSS.escape(id)}"]`)) setActive(node, true);
  const article = cards.get(id)?.dom.article;
  if (article) setActive(article, true);
  renderSlipPager(id);
}

function setActive(node, on) {
  node.classList.toggle("is-active", on);
  const target = node.matches(".slip") ? node.querySelector(".slip-open") : node;
  if (on) target.setAttribute("aria-current", "true");
  else target.removeAttribute("aria-current");
  for (const b of node.querySelectorAll(".slip-move")) b.tabIndex = on ? 0 : -1;
}

// Makes a card the one active card. Beside the slips the card is mounted
// anew; the old one leaves the screen at once, so that no key or post can
// reach it while the next loads.
async function activate(id, { focus = false } = {}) {
  if (id === activeId && cards.has(id)) {
    if (focus) focusSelected(cards.get(id));
    return;
  }
  closeForm();
  activeId = id;
  history.replaceState(null, "", hashWith({ o: id }));
  const entry = data.byId.get(id);
  document.title = `${entry?.title || entry?.address || id}, print cards`;
  markActive(id);
  const holder = el("inspector");
  if (!holder) {
    if (focus && cards.has(id)) focusSelected(cards.get(id));
    return;
  }
  const token = ++loadToken;
  loading = true;
  cards.clear();
  holder.replaceChildren(make("p", { class: "loading", text: "Loading the card…" }));
  try {
    const model = entry?.isWikiOnly ? buildWikiCard(entry) : entry ? buildCardFor(entry, await chunk(entry.chunk)) : null;
    if (token !== loadToken) return;
    if (!model) {
      holder.replaceChildren(make("p", { class: "loading", text: `No record ${id}.` }));
      return;
    }
    holder.replaceChildren(model.dom.article);
    cards.set(id, model);
    markActive(id);
    if (model.dom.drawer && model.wiki.status === "conflict") toggleDrawer(model, true);
    if (focus) focusSelected(model);
    // Stacked, the column with its slip pager comes into view; smoothly only where motion is welcome (D26).
    if (window.matchMedia?.(STACKED).matches && focus) {
      (holder.closest(".col") ?? holder).scrollIntoView({ behavior: reducedMotion() ? "auto" : "smooth", block: "start" });
    }
  } catch (e) {
    if (token === loadToken) showError(e.message);
  } finally {
    if (token === loadToken) loading = false;
  }
}

// The card a key may act on, or null.
function keyCard() {
  const model = cards.get(activeId);
  if (!model?.object) return null;
  const article = model.dom.article;
  const box = article.getBoundingClientRect();
  return acceptsKeys({
    loading,
    busy,
    connected: article.isConnected,
    focusWithin: article.contains(document.activeElement),
    inView: box.bottom > 0 && box.top < window.innerHeight,
  })
    ? model
    : null;
}

// A decision may be sent only while its card is still the active one on screen.
const isShown = (model) => cards.get(activeId) === model && model.dom.article.isConnected;

function focusSelected(model) {
  if (!model.object) {
    model.dom.article.querySelector("a, button")?.focus();
    return;
  }
  const pick = model.selected ?? firstOpen(model);
  if (pick === undefined) model.dom.article.querySelector("button")?.focus();
  else selectValue(model, pick, { focus: true });
}

const firstOpen = (model) => model.order.find((i) => !model.state.byIndex.has(i)) ?? model.order[0];

// Cards

function buildCardFor(entry, loaded) {
  const object = loaded?.byId.get(entry.id);
  return object ? buildCard(entry, object, loaded.byId.get(object.entry), loaded.byId) : null;
}

const GLYPH = { confirm: "✓", correct: "✗", unresolved: "?" };

function signHtml(decision) {
  if (!decision) return "";
  return `<span class="sign sign-${decision}"><span aria-hidden="true">${GLYPH[decision]}</span><span class="visually-hidden">${DECISION_WORD[decision]}</span></span>`;
}

// One value as the reviewer decides it: a pick button with its decision sign,
// its correction and its address targets. The producer word that follows it
// is the shared card's button, so a tag no longer repeats it.
function tokenHtml(model, row, sub = false) {
  const d = model.state.byIndex.get(row.index);
  // Read only, the state the last export recorded stands for the decision.
  const decision = d?.decision ?? (review.recording ? null : (row.node.reviewAction ?? STATE_DECISION[row.node.reviewState]));
  let html = `<span class="token${sub ? " sub" : ""}"><button type="button" class="pick${decision ? ` decided-${decision}` : ""}" data-index="${row.index}" aria-label="${escape(`${row.name}, ${row.text}`)}">${escape(row.text)}</button>${signHtml(decision)}`;
  if (isInherited(row, model.object) && row.producer !== "inherited") html += '<span class="tag quiet">inherited</span>';
  if (d?.decision === "correct") {
    const c = d.correction;
    // A flag is right at a passage, every other value is right as a value.
    const right = !c?.span ? "should not exist" : typeof c.value === "boolean" ? `right at "${model.record.text.slice(c.span[0], c.span[1])}"` : `right is "${valueText({ field: row.field, value: c.value })}"`;
    html += `<span class="correction">${escape(right)}</span>`;
  }
  return `${html}${targetsHtml(model.card.values.get(row.index)?.targets ?? [], LINKS)}</span>`;
}

// The review history of one value in words, the State of its chain.
function historyText(model, row) {
  const { object, state } = model;
  const past = decisionHistory(review.log, object.id, row.field);
  if (past.length) {
    const current = state.byIndex.get(row.index);
    return past.map((d) => `${decisionLine(d)}, ${d === current ? "in force" : state.stale.includes(d) ? "no longer applies, the value changed since" : "replaced or withdrawn"}`).join("; ");
  }
  // The export carries every reviewer's decisions; while recording, a reviewer sees only their own.
  if (row.node.reviewState && !review.recording) return `${row.node.reviewAction === "correct" ? "corrected and confirmed" : row.node.reviewState} at the last export`;
  return isApparatus(object) ? "not part of the review" : "no decision yet";
}

function entryText(model) {
  const { object, record, all } = model;
  // A value spanning the whole object (its types) marks nothing in the text.
  const whole = (r) => r.start === object.selector.start && r.end === object.selector.end;
  const own = all.filter((r) => r.source === object.entry && !whole(r));
  const box = make("p", { class: "card-entry" });
  for (const s of segments(record.text, [...own, { start: object.selector.start, end: object.selector.end, index: -1 }])) {
    const marks = s.marks.filter((m) => m >= 0);
    const node = marks.length ? make("mark", { "data-marks": marks.join(" "), text: s.text }) : document.createTextNode(s.text);
    box.append(make("span", { class: s.marks.includes(-1) ? "object" : "outside" }, node));
  }
  return box;
}

const definitionHtml = (pairs, cls = "compare-dl") => (pairs.length ? `<dl class="${cls}">${pairs.map(([k, v]) => `<dt>${escape(k)}</dt><dd>${escape(v)}</dd>`).join("")}</dl>` : "");

// The wiki side of a card: every candidate the concordance proposes, one wiki
// page once with its routes under it in route order, each a claim in the
// state p07 gave it with the words that agreed, and the page's fields (D16).
function drawerHtml(model) {
  const w = model.card.wiki;
  let html = `<section class="wiki-drawer" id="w-${model.uid}" hidden aria-label="Wiki candidates">`;
  if (w.status === "none") return `${html}<p class="quiet">The concordance proposes no wiki page for this object.</p></section>`;
  html += '<p class="drawer-note">Proposed by the concordance and not confirmed by anyone.</p>';
  if (w.diff) {
    const d = w.diff;
    html += `<p>Field conflict with <a href="${escape(d.href)}" target="_blank" rel="noopener">wiki page ${escape(d.page)}</a>${d.agree.length ? `, agreeing in ${escape(d.agree.join(", "))}` : ""}</p>`;
    html += `<table class="conflict"><thead><tr><th scope="col">Field</th><th scope="col">Print</th><th scope="col">Wiki</th></tr></thead><tbody>${d.rows
      .map(([field, print, wiki]) => `<tr><th scope="row">${iconHtml("alert")} ${escape(field)}</th><td>${escape(print)}</td><td>${escape(wiki)}</td></tr>`)
      .join("")}</tbody></table>`;
  }
  html += '<ol class="candidates">';
  for (const page of w.candidates) {
    const routes = page.routes
      .map((r) => {
        // Claim identifiers are for tracing, not reading: they stand in the title.
        const claims = r.claims.length === 1 ? "1 claim" : `${r.claims.length} claims`;
        const publication = r.href ? ` <a href="${escape(r.href)}" target="_blank" rel="noopener">publication ${escape(r.publication)}</a>` : "";
        const agreeing = r.agreeing.length ? `<span class="cand-agree">agreeing words: ${escape(r.agreeing.join(", "))}</span>` : "";
        return `<li><p class="cand-line"><span class="cand-route">${escape(r.words)}</span>${publication} <span class="cand-claim" title="${escape(r.claims.join(", "))}">${escape(`${r.state}, ${claims}`)}</span>${r.stale ? ' <span class="tag">record text changed since</span>' : ""}</p>${agreeing}${r.fields ? definitionHtml(r.fields) : ""}</li>`;
      })
      .join("");
    html += `<li><p class="cand-head"><a href="${escape(page.href)}" target="_blank" rel="noopener">${iconHtml("wiki")}Wiki page ${escape(page.page)}</a></p>${definitionHtml(page.fields)}<ul class="cand-routes">${routes}</ul></li>`;
  }
  html += "</ol>";
  // The projection keeps the first claims of a long route; totals give the full count.
  for (const note of w.notes) html += `<p class="quiet">${escape(note)}</p>`;
  return `${html}</section>`;
}

function toggleDrawer(model, open = null) {
  const show = open ?? model.dom.drawer.hidden;
  model.dom.drawer.hidden = !show;
  model.dom.wikiButton.setAttribute("aria-expanded", String(show));
}

// The head: address, the source sign as the link to the PDF page, the
// object's place in its entry, the title with its producer, and the
// relation, flag and progress words.
function headHtml(model) {
  const { card: m, entry, object, record, state } = model;
  const status = m.wiki.status;
  const t = m.titleValue;
  const untitled = () => {
    const start = (entry.snippet || "").replace(/[\s.,;:]+$/, "");
    return `<span class="untitled-title"><span class="visually-hidden">No title read, the text begins </span>${escape(start ? `${start}…` : "No title read")}</span>`;
  };
  const title = t ? `<span data-provenance-for="title">${Card.valueHtml(titleRow(m), t, 0)}</span>` : untitled();
  const slot = t ? Card._slot(titleRow(m), t, 0) : "";
  const progress = canDecide(model)
    ? `<span class="card-progress${state.complete ? " is-complete" : ""}" title="${state.complete ? "Review complete" : `${state.decided} of ${model.all.length} values decided`}">${state.complete ? `${iconHtml("check")}complete` : `${state.decided}/${model.all.length}`}</span>`
    : `<span class="card-progress">${isApparatus(object) ? "not reviewed" : "read only"}</span>`;
  // The red edge of a flagged card has this word beside it.
  const flagged = model.flagged ? `<span class="card-flagged" title="A value is marked wrong or unsure, or a missing value or a boundary is flagged">${iconHtml("alert")}flagged</span>` : "";
  return `<header class="rc-head card-head" data-region="head">`
    + `<p class="rc-head-line card-id"><span class="card-address">${escape(objectName(object, record, "Unnumbered"))}</span>`
    + `<a class="pdf-link" href="${escape(m.pdfHref)}" target="_blank" rel="noopener" title="${escape(`${VOLUME_LABEL[object.volume]}, PDF page ${record.pdfPage}`)}">${Card.sourceSign(m)}</a>`
    + `${m.position ? `<span class="rc-position card-sibling">${escape(m.position)}</span>` : ""}</p>`
    + `<h2 class="rc-title card-title" id="t-${model.uid}">${title}</h2>${slot}`
    + `<p class="rc-head-line card-status">${m.type ? `<span class="badge rc-type">${escape(m.type)}</span>` : ""}`
    + `<button type="button" class="wiki-sign status-${status}" data-card-act="wiki" aria-expanded="false" aria-controls="w-${model.uid}" title="${escape(WIKI_STATUS[status][2])}">${iconHtml(WIKI_STATUS[status][0])}${Card.relationMark(m)}</button>`
    + `${flagged}${progress}</p></header>`;
}

// What the reviewer added to a card, each with the control that removes it.
function addedHtml(model) {
  const rowsOf = [];
  for (const d of model.state.own) {
    if (d.decision !== "missing" && d.decision !== "boundary") continue;
    const text = d.decision === "missing" ? `${missingLabel(d.correction.field)}, "${valueText({ field: d.correction.field, value: d.correction.value })}"` : d.note;
    const label = d.decision === "missing" ? `Remove the added value ${text}` : "Remove the boundary flag";
    const remove = canDecide(model) ? ` <button type="button" class="withdraw" data-withdraw="${escape(d.id)}" aria-label="${escape(label)}" title="${escape(label)}">Remove</button>` : "";
    rowsOf.push(`<div class="meta-row rc-row added"><div class="meta-label">${d.decision === "missing" ? "Added" : "Boundary"}</div><div class="meta-value">${escape(text)}${remove}</div></div>`);
  }
  return rowsOf.length ? `<div class="meta-table card-added">${rowsOf.join("")}</div>` : "";
}

function cardFoot(model) {
  const foot = make("footer", { class: "card-foot" });
  const tools = make("div", { class: "value-tools", role: "group", "aria-label": "The selected value" }, make("span", { class: "active-field" }));
  if (canDecide(model)) {
    for (const [act, name, label, key] of [["confirm", "check", "Right", "R"], ["correct", "edit", "Wrong", "W"], ["unresolved", "question", "Unsure", "U"]]) {
      tools.append(make("button", { type: "button", class: `act act-${act}`, "data-act": act, "aria-pressed": "false", "aria-keyshortcuts": key }, icon(name), label));
    }
  }
  tools.append(make("a", { class: "pdf-link value-pdf", target: "_blank", rel: "noopener" }, icon("pdf"), make("span")));
  foot.append(tools);
  if (canDecide(model)) {
    const decided = model.state.decided >= model.all.length;
    foot.append(
      make(
        "div",
        { class: "card-actions" },
        make("button", { type: "button", "data-card-act": "all-right", disabled: decided, "aria-keyshortcuts": "A", title: "Mark every undecided value on this card right" }, icon("checkAll"), "All right"),
        make("button", { type: "button", class: "primary", "data-card-act": "complete", disabled: !model.state.complete && !decided, "aria-keyshortcuts": "C", title: "Mark the card complete and open the next open card" }, icon("check"), model.state.complete ? "Next" : "Complete"),
        make("button", { type: "button", "data-card-act": "missing", "aria-keyshortcuts": "M", title: "Add a value the rules did not read" }, icon("plus"), "Missing"),
        make("button", { type: "button", "data-card-act": "boundary", "aria-keyshortcuts": "B", title: "The object begins or ends in the wrong place" }, icon("alert"), "Boundary")
      )
    );
  }
  return foot;
}

let uid = 0;

// Every value of a card model, the title included, in the order it shows.
const modelValues = (m) => [m.titleValue, ...m.groups.flatMap((g) => g.rows.flatMap((r) => r.values))].filter(Boolean);

function buildCard(entry, object, record, byId) {
  const all = rows(object).map((r) => ({ ...r, name: valueName(r.field), text: valueText(r) }));
  const model = {
    uid: ++uid,
    entry,
    object,
    record,
    byId,
    all,
    byIndex: new Map(all.map((r) => [r.index, r])),
    state: objectReview(object, all, review.active, record.sha256),
    wiki: entry.wiki,
    selected: null,
    dom: {},
  };
  model.flagged = !model.state.complete && ([...model.state.byIndex.values()].some((d) => d.decision !== "confirm") || model.state.own.some((d) => d.decision === "boundary" || d.decision === "missing"));
  const m = cardModel({ entry, object, byId, concordance: data.wiki, siblings: data.siblings.get(entry.entry), links: LINKS, idBase: `c${model.uid}` });
  m.values = new Map(modelValues(m).map((v) => [v.index, v]));
  model.card = m;
  // The decision layer on the shared model: a pick per value, the review history as its State.
  for (const v of m.values.values()) {
    const row = model.byIndex.get(v.index);
    v.html = `${sepHtml(v.sep)}${tokenHtml(model, row, v.sub)}`;
    v.stateText = historyText(model, row);
    // Selecting the value marks its passage in the entry text; no second way to it.
    v.chain.passage.markId = null;
  }
  model.chains = chainRows(m);
  const classes = ["card"];
  if (record.kind === "header" || entry.types.includes("collection")) classes.push("is-guide");
  if (model.state.complete) classes.push("is-complete");
  else if (model.flagged) classes.push("is-contested");
  if (isApparatus(object)) classes.push("is-apparatus");
  const stale = model.state.stale.length
    ? `<p class="card-stale">${iconHtml("alert")} ${model.state.stale.length} earlier decision${model.state.stale.length > 1 ? "s" : ""} no longer appl${model.state.stale.length > 1 ? "y" : "ies"}, because a rebuild changed the value.</p>`
    : "";
  // The entry text stands above the values, so the passage of the selected value is in view as it is decided.
  const article = fromHtml(
    `<article class="${classes.join(" ")}" data-card-id="${escape(object.id)}" data-kind="print" aria-labelledby="t-${model.uid}">`
      + headHtml(model)
      + drawerHtml(model)
      + `<section class="rc-source" data-region="source"><h3 class="rc-group-heading">${escape(m.sourceText.label)}</h3></section>`
      + `<div class="rc-values" data-region="values">${m.groups.map((g) => Card.group(g)).join("")}${addedHtml(model)}</div>`
      + stale
      + "</article>"
  );
  model.dom.article = article;
  model.dom.drawer = article.querySelector(".wiki-drawer");
  model.dom.wikiButton = article.querySelector('[data-card-act="wiki"]');
  model.dom.entry = entryText(model);
  article.querySelector(".rc-source").append(model.dom.entry);
  model.dom.foot = cardFoot(model);
  article.append(model.dom.foot);
  // J and K follow the values in the order the card shows them.
  model.order = [...article.querySelectorAll("button.pick[data-index]")].map((b) => Number(b.dataset.index));
  const pick = firstOpen(model);
  if (pick !== undefined) selectValue(model, pick);
  return model;
}

// A wiki page no print candidate names. Its values come from the local
// projection of the wiki pages, and each chain says so and leads to the
// record in the docs app, where its own chains stand.
function buildWikiCard(entry) {
  const page = entry.pageInfo;
  const model = { uid: ++uid, entry, object: null, wiki: entry.wiki, dom: {} };
  const href = wikiHash(entry.page, null, "/");
  const type = (entry.wikiType || "").replaceAll("-", " ");
  const chainOf = () => ({
    passage: { gap: "not-located", reason: "the local projection of the wiki pages carries no offsets; the record in Records holds them" },
    record: { id: `klawiter:entry/${entry.page}`, type: type || undefined, sign: `Wiki page ${entry.page}` },
    sourceFile: { words: "wiki_concordance.json, the local projection of the wiki pages" },
    producer: { words: "projected from the wiki record" },
  });
  const value = (key, text) => ({ text, producer: "derived", state: "not-reviewed", chainId: safeId(`c${model.uid}-${key}`), chain: chainOf() });
  const m = {
    kind: "wiki",
    id: `klawiter:entry/${entry.page}`,
    title: entry.title || "Untitled wiki page",
    titleValue: entry.title ? value("title", entry.title) : null,
    relation: { state: "proposed", words: WIKI_STATUS["wiki-only"][1] },
    groups: [
      {
        rows: [
          ["category", "Category", page.category],
          ["imprint", "Imprint", [page.place, page.publisher, page.year].filter(Boolean).join(", ")],
          ["editions", "Editions", page.pubCount ? `${page.pubCount} on the page` : null],
        ]
          .filter(([, , text]) => text)
          .map(([key, label, text]) => ({ key, label, idBase: `c${model.uid}-${key}`, values: [value(key, String(text))] })),
      },
    ],
    sourceText: { label: "Excerpt of the wiki text", text: page.snippet || "No text excerpt.", marks: [] },
  };
  model.card = m;
  model.chains = chainRows(m);
  const t = m.titleValue;
  const title = t ? `<span data-provenance-for="title">${Card.valueHtml(titleRow(m), t, 0)}</span>` : escape(m.title);
  const search = (entry.title || "").split(/[:([]/)[0].trim();
  model.dom.article = fromHtml(
    `<article class="card is-wiki" data-card-id="${escape(entry.id)}" data-kind="wiki" aria-labelledby="t-${model.uid}">`
      + `<header class="rc-head card-head" data-region="head"><p class="rc-head-line card-id"><a class="card-address" href="${escape(href)}" target="_blank" rel="noopener">Wiki page ${escape(entry.page)}</a>${type ? `<span class="badge rc-type">${escape(type)}</span>` : ""}</p>`
      + `<h2 class="rc-title card-title" id="t-${model.uid}">${title}</h2>${t ? Card._slot(titleRow(m), t, 0) : ""}`
      + `<p class="rc-head-line card-status"><span class="wiki-sign status-wiki-only">${iconHtml("wiki")}${Card.relationMark(m)}</span></p></header>`
      + Card.source(m)
      + `<div class="rc-values" data-region="values">${m.groups.map((g) => Card.group(g)).join("")}</div>`
      + `<footer class="card-foot"><div class="card-actions"><a href="${escape(href)}" target="_blank" rel="noopener">${iconHtml("wiki")}Open the record</a>`
      + `${search ? `<button type="button" data-card-act="search" data-search="${escape(search)}">${iconHtml("pdf")}Search the print for this title</button>` : ""}</div></footer>`
      + "</article>"
  );
  return model;
}

// Selecting a value marks its passage and fills the tools with its name.
function selectValue(model, index, { focus = false } = {}) {
  const row = model.byIndex.get(index);
  if (!row) return;
  model.selected = index;
  const { article, entry, foot } = model.dom;
  for (const b of article.querySelectorAll("button.pick")) b.classList.toggle("is-current", Number(b.dataset.index) === index);
  for (const m of entry.querySelectorAll("mark")) m.classList.toggle("current", m.dataset.marks.split(" ").includes(String(index)));
  const d = model.state.byIndex.get(index);
  foot.querySelector(".active-field").textContent = row.name;
  for (const b of foot.querySelectorAll("button.act")) b.setAttribute("aria-pressed", String(d?.decision === b.dataset.act));
  // A value leads to the page of the record its passage stands in; where that
  // is the page the head already links, the foot does not repeat it.
  const source = model.byId.get(row.source) ?? model.record;
  const pdf = foot.querySelector(".value-pdf");
  pdf.hidden = source.volume === model.record.volume && source.pdfPage === model.record.pdfPage;
  pdf.href = pdfHref(source.volume, source.pdfPage);
  pdf.title = `The passage of ${row.name} on PDF page ${source.pdfPage}`;
  pdf.lastChild.textContent = `${VOLUME_SHORT[source.volume]} p. ${source.pdfPage}`;
  const button = article.querySelector(`button.pick[data-index="${index}"]`);
  if (focus) button?.focus();
  const mark = entry.querySelector("mark.current");
  if (mark && entry.scrollHeight > entry.clientHeight) entry.scrollTop = Math.max(0, mark.offsetTop - entry.offsetTop - entry.clientHeight / 3);
}

// Opens or closes the chain of one value under its producer button. The
// chain is drawn when it opens, so it shows the review history as it stands;
// opening it selects its value, so a key then acts on the value it explains.
function toggleChain(model, button, open = null) {
  const id = button.getAttribute("aria-controls");
  const hit = model.chains?.get(id);
  const panel = hit ? model.dom.article.querySelector(`#${CSS.escape(id)}`) : null;
  if (!panel) return;
  const show = open ?? button.getAttribute("aria-expanded") !== "true";
  if (show) panel.innerHTML = Card.chainSteps(model.card, hit.r, hit.i);
  panel.hidden = !show;
  button.setAttribute("aria-expanded", String(show));
  const index = hit.r.values[hit.i].index;
  if (show && model.object && model.selected !== index) selectValue(model, index);
}

// The values whose chains stand open on a card, to open them again on its rebuild.
const openChains = (model) =>
  [...model.dom.article.querySelectorAll('button.prov-badge[aria-expanded="true"]')]
    .map((b) => model.chains.get(b.getAttribute("aria-controls")))
    .filter(Boolean)
    .map(({ r, i }) => r.values[i].index);

function reopenChains(model, indices) {
  for (const index of indices) {
    const id = model.card.values.get(index)?.chainId;
    const button = id && model.dom.article.querySelector(`button.prov-badge[aria-controls="${CSS.escape(id)}"]`);
    if (button) toggleChain(model, button, true);
  }
}

// Decisions

async function send(model, name, body) {
  const payload = { object: model.object.id, entry_sha256: model.record.sha256, reviewer: name, ...body };
  let response;
  try {
    response = await fetch("/review/decisions", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
  } catch (e) {
    say(about(nameOf(model), "Not saved", `the review server did not answer (${e.message})`));
    return null;
  }
  const answer = await response.json().catch(() => ({}));
  if (response.status !== 201) {
    const details = (answer.details || []).map((d) => `${d.loc.join(".")} ${d.msg}`).join("; ");
    say(about(nameOf(model), "Not saved", `${answer.error || response.status}${details ? ` (${details})` : ""}`));
    return null;
  }
  review.log.push(answer);
  review.active = effective(review.log);
  return answer;
}

const nameOf = (model) => objectName(model.object, model.record);

// Runs one review action on a card: never twice at once, only while the card
// is the one on screen, and with the reviewer known. Keys wait meanwhile.
async function act(model, task) {
  if (busy || !isShown(model) || !canDecide(model)) return false;
  busy = true;
  try {
    const name = await reviewer();
    if (!name) {
      say(about(nameOf(model), "Not saved", "a reviewer name or role is needed"));
      return false;
    }
    // A reviewer named only now may have decisions on record; the card is
    // then rebuilt with them before anything is posted.
    if (await useReviewer(name)) {
      say(about(nameOf(model), "Not saved", `the decisions of ${name} are loaded now, decide again on the card as it shows them`));
      renderDesk().catch((e) => showError(e.message));
      return false;
    }
    if (!isShown(model)) {
      say(about(nameOf(model), "Not saved", "another card is on screen now"));
      return false;
    }
    return await task(name);
  } finally {
    busy = false;
  }
}

// Rebuilds a card after a decision, keeping what the reviewer had open. An
// open form goes with the old card, so that no key waits on it. A card that
// left the screen while its decision was posted is not rebuilt; the message
// names it all the same. Null in that case.
function refresh(model, selected, message) {
  closeForm();
  if (message) say(message);
  if (!isShown(model)) return null;
  const next = buildCard(model.entry, model.object, model.record, model.byId);
  const scroll = window.scrollY;
  const chains = openChains(model);
  model.dom.article.replaceWith(next.dom.article);
  cards.set(model.entry.id, next);
  setActive(next.dom.article, true);
  if (!model.dom.drawer.hidden) toggleDrawer(next, true);
  reopenChains(next, chains);
  selectValue(next, next.byIndex.has(selected) ? selected : firstOpen(next), { focus: true });
  window.scrollTo(0, scroll);
  renderHeader();
  for (const node of document.querySelectorAll(`.slip[data-id="${CSS.escape(model.entry.id)}"] .slip-line`)) {
    if (next.state.complete && !node.querySelector(".done-sign")) node.append(make("span", { class: "done-sign", title: "Review complete" }, icon("check"), hidden("review complete")));
  }
  return next;
}

const nextUndecided = (model, index) => model.order.slice(model.order.indexOf(index) + 1).find((i) => !model.state.byIndex.has(i));

function decide(model, action, row) {
  if (!row) return;
  if (action === "correct") {
    openForm(model, "correct", row);
    return;
  }
  act(model, async (name) => {
    if (!(await send(model, name, { decision: action, target: targetOf(row) }))) return false;
    const next = refresh(model, row.index, about(nameOf(model), "Saved", `${row.name} ${DECISION_WORD[action]}`));
    if (next) selectValue(next, nextUndecided(next, row.index) ?? row.index, { focus: true });
    return true;
  });
}

// The box of a node is displayed when it lies inside the viewport and every
// scrolling ancestor up to the page, and nothing hides it. Stacked, the
// decision bar sticks to the bottom of the window, and a value behind it is
// not displayed.
function displayed(node) {
  if (!node.checkVisibility({ visibilityProperty: true, opacityProperty: true })) return false;
  const viewport = { top: 0, left: 0, bottom: window.innerHeight, right: window.innerWidth };
  const foot = node.closest("article")?.querySelector(".card-foot");
  if (foot && !foot.contains(node) && getComputedStyle(foot).position === "sticky") viewport.bottom = Math.min(viewport.bottom, foot.getBoundingClientRect().top);
  const clips = [viewport];
  for (let up = node.parentElement; up && up !== document.body; up = up.parentElement) {
    const style = getComputedStyle(up);
    if (style.overflowX !== "visible" || style.overflowY !== "visible") clips.push(up.getBoundingClientRect());
  }
  return inSight(node.getBoundingClientRect(), clips);
}

// "All right" confirms the undecided values the card displays, one decision
// each, and stops as soon as the card leaves the screen.
function allRight(model) {
  act(model, async (name) => {
    const shown = new Set([...model.dom.article.querySelectorAll("button.pick[data-index]")].filter(displayed).map((b) => Number(b.dataset.index)));
    const open = confirmable(model.all, model.state.byIndex, shown);
    const unseen = model.all.filter((r) => !model.state.byIndex.has(r.index) && !shown.has(r.index));
    if (unseen.length) {
      say(about(nameOf(model), "Not saved", `${unseen.length} undecided value${unseen.length > 1 ? "s are" : " is"} not in view; scroll them into view or decide them one by one`));
      return false;
    }
    if (!open.length) {
      say(about(nameOf(model), "Nothing saved", "every value carries a decision"));
      return false;
    }
    let saved = 0;
    for (const row of open) {
      if (!isShown(model)) break;
      if (!(await send(model, name, { decision: "confirm", target: targetOf(row) }))) break;
      saved += 1;
    }
    const left = open.length - saved;
    const detail = `${saved} value${saved === 1 ? "" : "s"} right${left ? `, ${left} not, the card left the screen or the server refused` : ""}`;
    const next = refresh(model, model.selected, about(nameOf(model), "Saved", detail));
    next?.dom.foot.querySelector('[data-card-act="complete"]')?.focus();
    return true;
  });
}

async function complete(model) {
  if (!canDecide(model)) return;
  const left = model.all.length - model.state.decided;
  if (!model.state.complete && left > 0) {
    say(about(nameOf(model), "Not complete", `${left} value${left > 1 ? "s are" : " is"} still undecided`));
    return;
  }
  if (!model.state.complete) {
    const ok = await act(model, async (name) => {
      if (!(await send(model, name, { decision: "complete" }))) return false;
      return refresh(model, model.selected, about(nameOf(model), "Saved", "the card is complete")) !== null;
    });
    if (!ok) return;
  }
  await openNext(model.entry.id);
}

// The next open card after a complete one: the next slip of the list that is
// not complete, else the next open object of the review sample.
async function openNext(currentId) {
  const done = completeIds();
  const slips = [...document.querySelectorAll(".slip[data-id]")].map((s) => s.dataset.id);
  const at = slips.indexOf(currentId);
  const next = [...slips.slice(at + 1), ...slips.slice(0, Math.max(0, at))].find((id) => !done.has(id) && !data.byId.get(id)?.isWikiOnly);
  if (next) {
    await activate(next, { focus: true });
    document.querySelector(`.slip[data-id="${CSS.escape(next)}"]`)?.scrollIntoView({ block: "nearest" });
    return;
  }
  openNextSample(currentId);
}

function openNextSample(currentId = activeId) {
  const next = nextOpenSample(currentId);
  if (!next) {
    say("Every object of the review sample is complete.");
    return;
  }
  if (cards.has(next.id) || document.querySelector(`.slip[data-id="${CSS.escape(next.id)}"]`)) {
    activate(next.id, { focus: true });
    return;
  }
  location.hash = `#/?${new URLSearchParams({ r: "open", o: next.id })}`;
}

function withdraw(model, id) {
  const what = model.state.own.find((d) => d.id === id)?.decision === "boundary" ? "the boundary flag removed" : "the added value removed";
  act(model, async (name) => {
    if (!(await send(model, name, { decision: "withdraw", supersedes: id }))) return false;
    refresh(model, model.selected, about(nameOf(model), "Saved", what));
    return true;
  });
}

// The decision form opens in the card, before its footer. A passage is typed
// or selected in the entry text; both give the same characters.
function closeForm() {
  pending?.form.remove();
  pending = null;
}

// The open form, or null; a form that left the page holds nothing open.
function openFormNow() {
  if (pending && !pending.form.isConnected) pending = null;
  return pending;
}

function openForm(model, kind, row = null) {
  if (!canDecide(model) || !isShown(model) || busy) return;
  closeForm();
  const inherited = kind === "correct" && isInherited(row, model.object);
  const field = make("select", {}, ...data.vocab.missingFields.map((f) => make("option", { value: f, text: missingLabel(f) })));
  const vocab = make("select");
  const passage = make("input", { type: "text", autocomplete: "off", spellcheck: "false" });
  const found = make("span", { class: "found", "aria-live": "polite" });
  const remove = make("input", { type: "checkbox" });
  const note = make("textarea", { rows: "2", maxlength: "2000" });
  remove.checked = inherited;
  remove.disabled = inherited;
  const what = {
    correct: `${row?.name} "${row?.text}" is wrong`,
    missing: "A value the rules did not read",
    boundary: "The object begins or ends in the wrong place",
  }[kind];
  const hint = inherited
    ? "The value is inherited from a heading or header, so it can only be marked as one that should not exist. Say in the note what it should be."
    : {
        correct: "Type the right passage or select it in the entry text, or mark that the value should not exist.",
        missing: "Choose the field, then type its passage or select it in the entry text.",
        boundary: "Say in the note where the object should begin or end.",
      }[kind];
  const vocabRow = make("label", { hidden: true }, "Right value", vocab);
  const passageRow = make("label", {}, "Passage", passage, found);
  const removeRow = make("label", { class: "inline", hidden: kind !== "correct" }, remove, "The value should not exist");
  const save = make("button", { type: "submit", class: "primary", text: "Save" });
  const cancel = make("button", { type: "button", "data-form": "cancel", text: "Cancel" });
  const form = make(
    "form",
    { class: "decision-form", "aria-label": what },
    make("p", { class: "decision-what", text: what }),
    make("p", { class: "quiet", text: hint }),
    make("label", { hidden: kind !== "missing" }, "Field", field),
    vocabRow,
    passageRow,
    removeRow,
    make("label", {}, kind === "boundary" ? "Note" : "Note, optional", note),
    make("p", { class: "form-actions" }, save, cancel)
  );
  // A boundary flag names no field; it carries only its note.
  const path = () => (kind === "missing" ? field.value : kind === "correct" ? row.field : null);
  const sync = () => {
    const options = path() ? vocabFor(data.vocab, path()) : null;
    const off = kind === "boundary" || remove.checked;
    vocabRow.hidden = off || !options;
    passageRow.hidden = off;
    if (options && !vocab.options.length) vocab.replaceChildren(...options.map((v) => make("option", { value: v, text: TYPE_LABEL[v] ?? v })));
  };
  field.addEventListener("change", () => {
    vocab.replaceChildren();
    sync();
  });
  remove.addEventListener("change", sync);
  passage.addEventListener("input", () => setPassage(findPassage(model.record.text, passage.value, row ? row.start : model.object.selector.start, [model.object.selector.start, model.object.selector.end]), false));
  sync();
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    submitForm(path(), vocab.value, remove.checked, note.value.trim());
  });
  model.dom.foot.before(form);
  // Only a mounted form is pending, so that a failure above leaves no key blocked.
  pending = { model, kind, row, inherited, span: null, form, passage, found };
  const selection = selectedSpan(model);
  if (selection && !passageRow.hidden) setPassage(selection, true);
  (kind === "boundary" || inherited ? note : kind === "missing" ? field : passage).focus({ preventScroll: true });
  form.scrollIntoView({ block: "nearest" });
}

function setPassage(span, fill) {
  if (!pending) return;
  const text = pending.model.record.text;
  pending.span = span;
  if (fill && span) pending.passage.value = text.slice(span[0], span[1]);
  pending.found.textContent = span ? ` found at characters ${span[0]} to ${span[1]}` : pending.passage.value.trim() ? " not in the entry text" : "";
}

function submitForm(path, choice, removing, note) {
  const { model, kind, row, span } = pending;
  let body;
  if (kind === "boundary") {
    if (!note) {
      say(about(nameOf(model), "Not saved", "a boundary flag says in its note what is wrong"));
      return;
    }
    body = { decision: "boundary", note };
  } else if (removing) {
    body = { decision: "correct", target: targetOf(row), correction: {}, note };
  } else {
    if (!span) {
      say(about(nameOf(model), "Not saved", "type or select the passage in the entry text first"));
      pending.passage.focus();
      return;
    }
    const value = correctionValue(path, model.record.text.slice(span[0], span[1]), choice);
    if (value === null) {
      say(about(nameOf(model), "Not saved", `the passage gives no ${missingLabel(path.replace(/\[\d+\]/g, "")).toLowerCase()}`));
      return;
    }
    if (kind === "correct" && span[0] === row.start && span[1] === row.end && value === row.value) {
      say(about(nameOf(model), "Not saved", "that is the value as read; choose Right, or another passage"));
      return;
    }
    const correction = { value, span };
    if (kind === "missing") correction.field = path;
    body = { decision: kind, correction, note };
    if (kind === "correct") body.target = targetOf(row);
  }
  act(model, async (name) => {
    if (!(await send(model, name, body))) return false;
    const detail = kind === "boundary" ? "boundary flagged" : kind === "missing" ? "missing value added" : `${row.name} wrong`;
    const next = refresh(model, row ? row.index : model.selected, about(nameOf(model), "Saved", detail));
    if (next && row) selectValue(next, nextUndecided(next, row.index) ?? row.index, { focus: true });
    return true;
  });
}

// Character offset of a point inside the entry text: the rendered text equals
// the record text, so the length of the text before the point is the offset.
function offsetIn(container, node, offset) {
  const range = document.createRange();
  range.selectNodeContents(container);
  range.setEnd(node, offset);
  return range.toString().length;
}

function selectedSpan(model) {
  const sel = window.getSelection();
  const box = model.dom.entry;
  if (!sel || sel.rangeCount === 0 || sel.isCollapsed) return null;
  const r = sel.getRangeAt(0);
  if (!box.contains(r.startContainer) || !box.contains(r.endContainer)) return null;
  const text = model.record.text;
  let a = offsetIn(box, r.startContainer, r.startOffset);
  let b = offsetIn(box, r.endContainer, r.endOffset);
  while (a < b && /\s/.test(text[a])) a++;
  while (b > a && /\s/.test(text[b - 1])) b--;
  return a < b ? [a, b] : null;
}

// Keys

function moveValue(model, delta) {
  const at = model.order.indexOf(model.selected);
  const next = model.order[at + delta];
  if (next !== undefined) selectValue(model, next, { focus: true });
}

function moveSlip(slip, delta) {
  const all = [...slip.closest(".slip-list").querySelectorAll(".slip")];
  all[all.indexOf(slip) + delta]?.querySelector(".slip-open").focus();
}

const DECISION_KEYS = new Set(["r", "w", "u", "a", "c", "m", "b"]);

function onKey(e) {
  if (e.ctrlKey || e.metaKey || e.altKey || document.querySelector("dialog[open]")) return;
  const form = openFormNow();
  // Escape cancels a form only from inside its card; in the search field it
  // keeps its own meaning.
  if (e.key === "Escape" && form && form.model.dom.article.contains(e.target)) {
    e.preventDefault();
    const { model, row } = form;
    closeForm();
    if (row) selectValue(model, row.index, { focus: true });
    else focusSelected(model);
    return;
  }
  if (e.target.closest("input, textarea, select")) return;
  const key = e.key.length === 1 ? e.key.toLowerCase() : e.key;
  if (key === "n") {
    e.preventDefault();
    if (!loading && !busy) openNextSample();
    return;
  }
  const slip = e.target.closest?.(".slip");
  if (slip) {
    if (key === "ArrowDown" || key === "j" || key === "ArrowUp" || key === "k") {
      e.preventDefault();
      moveSlip(slip, key === "ArrowDown" || key === "j" ? 1 : -1);
    }
    return;
  }
  const model = keyCard();
  if (!model) {
    if (DECISION_KEYS.has(key) && !loading && !busy) say("Keys act on the card that holds the focus. Open a card or select one of its values first.");
    return;
  }
  if (key === "Escape") {
    document.querySelector(`.slip[data-id="${CSS.escape(model.entry.id)}"] .slip-open`)?.focus();
    return;
  }
  if (openFormNow()) return;
  const row = model.byIndex.get(model.selected);
  const acts = {
    ArrowDown: () => moveValue(model, 1),
    j: () => moveValue(model, 1),
    ArrowUp: () => moveValue(model, -1),
    k: () => moveValue(model, -1),
    r: () => canDecide(model) && decide(model, "confirm", row),
    w: () => canDecide(model) && decide(model, "correct", row),
    u: () => canDecide(model) && decide(model, "unresolved", row),
    a: () => canDecide(model) && allRight(model),
    c: () => complete(model),
    m: () => openForm(model, "missing"),
    b: () => openForm(model, "boundary"),
  };
  if (acts[key]) {
    e.preventDefault();
    acts[key]();
  }
}

// Wiring

function wire() {
  const go = ({ replace = false } = {}) => {
    const p = new URLSearchParams();
    for (const [key, id] of [["q", "q"], ["v", "volume"], ["k", "kind"], ["r", "review-filter"], ["d", "view"]]) {
      const value = el(id).value;
      if (value && !(key === "d" && value === "axis")) p.set(key, value);
    }
    const keep = params();
    for (const key of ["part", "w", "sort"]) if (keep.get(key)) p.set(key, keep.get(key));
    const hash = p.toString() ? `#/?${p}` : "#/";
    if (replace) {
      history.replaceState(null, "", hash);
      renderDesk().catch((e) => showError(e.message));
    } else {
      location.hash = hash;
    }
  };
  el("filters").addEventListener("submit", (e) => e.preventDefault());
  el("q").addEventListener("input", () => go({ replace: true }));
  for (const id of ["volume", "kind", "review-filter", "view"]) el(id).addEventListener("change", () => go());
  el("board-sort")?.addEventListener("change", (e) => {
    location.hash = hashWith({ sort: e.target.value === "book" ? "" : e.target.value, page: "", o: "" });
  });
  el("reset-filters").addEventListener("click", () => {
    ui.section = "";
    const view = el("view").value;
    location.hash = view !== "axis" ? `#/?d=${view}` : "#/";
  });
  const turn = (delta) => {
    location.hash = hashWith({ page: String(Math.max(1, readFilters().page + delta)), o: "" });
  };
  for (const [id, delta] of [["prev", -1], ["prev-bottom", -1], ["next", 1], ["next-bottom", 1]]) el(id).addEventListener("click", () => turn(delta));

  document.addEventListener("change", (e) => {
    const t = e.target;
    if (t.matches("[data-section-sort]")) {
      ui.sectionSort = t.value;
      renderDesk();
    } else if (t.matches("[data-sort]")) {
      location.hash = hashWith({ sort: t.value === "book" ? "" : t.value, page: "", o: "" });
    } else if (t.matches("[data-lane-sort]")) {
      ui.laneSorts[t.dataset.laneSort] = t.value;
      renderDesk();
    }
  });

  document.addEventListener("click", (e) => {
    const pill = e.target.closest("button[data-wiki]");
    if (pill) {
      // Wiki pages have no print volume and print records no wiki volume.
      const wikiOnly = pill.dataset.wiki === "wiki-only";
      const volume = el("volume").value;
      ui.section = "";
      location.hash = hashWith({ w: pill.dataset.wiki, v: wikiOnly || volume === "WIKI" ? "" : volume, page: "", o: "" });
      return;
    }
    const section = e.target.closest("button[data-section]");
    if (section) {
      const val = section.dataset.section;
      ui.section = val;
      const partVal = val.startsWith("wiki:") ? "" : val;
      history.replaceState(null, "", hashWith({ part: partVal, page: "", o: "" }));
      renderDesk();
    }
  });

  const desk = el("desk");
  desk.addEventListener("click", (e) => {
    const move = e.target.closest("button[data-move]");
    if (move) {
      const slip = move.closest(".slip");
      const list = slip.closest(".slip-list");
      const all = [...list.children];
      const target = all[all.indexOf(slip) + Number(move.dataset.move)];
      if (target) {
        list.insertBefore(slip, Number(move.dataset.move) < 0 ? target : target.nextSibling);
        ui.order.set(list.dataset.list, [...list.children].map((s) => s.dataset.id));
        move.focus();
      }
      return;
    }
    const open = e.target.closest("button[data-open]");
    if (open) {
      // Pointer and Enter alike open the card; on keyboard or narrow screens focus moves into it.
      activate(open.dataset.open, { focus: e.detail === 0 || window.matchMedia?.(STACKED).matches });
      return;
    }
    const step = e.target.closest(".slip-pager button[data-step]");
    if (step) {
      if (step.dataset.target) activate(step.dataset.target, { focus: true });
      return;
    }
    const article = e.target.closest("article.card");
    if (!article) return;
    const model = cards.get(article.dataset.cardId);
    if (!model) return;
    if (activeId !== model.entry.id) {
      activate(model.entry.id);
      if (!e.target.closest("button, a, mark")) return;
    }
    const out = e.target.closest("button.withdraw");
    if (out) return withdraw(model, out.dataset.withdraw);
    const pick = e.target.closest("button.pick");
    if (pick) return selectValue(model, Number(pick.dataset.index), { focus: true });
    // A producer button opens its value's chain; Enter and Space reach it as a click.
    const producer = e.target.closest("button.prov-badge[aria-controls]");
    if (producer) return toggleChain(model, producer);
    const mark = e.target.closest("mark[data-marks]");
    if (mark && model.object) {
      const indices = mark.dataset.marks.split(" ").map(Number);
      const main = indices.find((i) => !model.card.values.get(i)?.sub);
      return selectValue(model, main ?? indices[0], { focus: true });
    }
    const button = e.target.closest("button.act");
    if (button) return decide(model, button.dataset.act, model.byIndex.get(model.selected));
    const cardAct = e.target.closest("[data-card-act]")?.dataset.cardAct;
    if (cardAct === "wiki") toggleDrawer(model);
    else if (cardAct === "all-right") allRight(model);
    else if (cardAct === "complete") complete(model);
    else if (cardAct === "missing" || cardAct === "boundary") openForm(model, cardAct);
    else if (cardAct === "search") {
      el("q").value = e.target.closest("button").dataset.search;
      el("volume").value = "";
      location.hash = `#/?${new URLSearchParams({ q: el("q").value })}`;
    } else if (e.target.closest('button[data-form="cancel"]') && pending) {
      const { row } = pending;
      closeForm();
      if (row) selectValue(model, row.index, { focus: true });
    }
  });
  // In the grid, focus entering a card makes it the active one.
  desk.addEventListener("focusin", (e) => {
    const article = e.target.closest("article.card");
    if (!article) return;
    const model = cards.get(article.dataset.cardId);
    if (!model) return;
    if (activeId !== model.entry.id) activate(model.entry.id);
    const pick = e.target.closest("button.pick");
    if (pick && model.selected !== Number(pick.dataset.index)) selectValue(model, Number(pick.dataset.index));
    // A key pressed on a value's producer button acts on that value.
    const producer = model.object && e.target.closest("button.prov-badge[aria-controls]");
    const hit = producer && model.chains.get(producer.getAttribute("aria-controls"));
    if (hit && model.selected !== hit.r.values[hit.i].index) selectValue(model, hit.r.values[hit.i].index);
  });

  desk.addEventListener("dragstart", (e) => {
    const slip = e.target.closest(".slip");
    if (!slip) return;
    ui.dragged = slip;
    slip.classList.add("dragging");
    e.dataTransfer.effectAllowed = "move";
  });
  desk.addEventListener("dragend", () => {
    ui.dragged?.classList.remove("dragging");
    ui.dragged = null;
  });
  desk.addEventListener("dragover", (e) => {
    const over = e.target.closest(".slip");
    const list = over?.closest(".slip-list");
    if (!over || !ui.dragged || over === ui.dragged || list !== ui.dragged.parentElement) return;
    e.preventDefault();
    const box = over.getBoundingClientRect();
    list.insertBefore(ui.dragged, e.clientY > box.top + box.height / 2 ? over.nextSibling : over);
    ui.order.set(list.dataset.list, [...list.children].map((s) => s.dataset.id));
  });

  document.addEventListener("selectionchange", () => {
    if (!pending || pending.kind === "boundary" || pending.inherited) return;
    const span = selectedSpan(pending.model);
    if (span) setPassage(span, true);
  });

  el("reviewer-change").addEventListener("click", async () => {
    if (await useReviewer(await askReviewer())) renderDesk().catch((e) => showError(e.message));
  });
  el("skip-card").addEventListener("click", () => {
    const model = cards.get(activeId);
    if (model?.dom.article.isConnected) focusSelected(model);
    else say("No card is open yet.");
  });
  el("reviewer-cancel").addEventListener("click", () => el("reviewer-dialog").close(""));
  el("nav-help").addEventListener("click", () => el("help-dialog").showModal());
  el("help-close").addEventListener("click", () => el("help-dialog").close());
  // Stacked, the filters fold behind one button, so the card reaches the first screen (D15).
  el("filters-toggle").addEventListener("click", (e) => {
    const open = e.currentTarget.getAttribute("aria-expanded") !== "true";
    e.currentTarget.setAttribute("aria-expanded", String(open));
    el("filters").classList.toggle("is-open", open);
  });
  // Escape closes the chain the focus is in or on before any other Escape
  // acts, and the focus returns to the value's producer button. The capture
  // phase runs this ahead of onKey, which would leave the card.
  document.addEventListener(
    "keydown",
    (e) => {
      if (e.key !== "Escape" || e.ctrlKey || e.metaKey || e.altKey || !e.target.closest) return;
      const panel = e.target.closest(".rc-chain:not([hidden])");
      const button = panel ? document.querySelector(`button.prov-badge[aria-controls="${CSS.escape(panel.id)}"]`) : e.target.closest('button.prov-badge[aria-expanded="true"]');
      if (!button) return;
      e.preventDefault();
      e.stopPropagation();
      const model = cards.get(button.closest("article.card")?.dataset.cardId);
      if (model) toggleChain(model, button, false);
      else {
        (panel ?? document.getElementById(button.getAttribute("aria-controls"))).hidden = true;
        button.setAttribute("aria-expanded", "false");
      }
      button.focus();
    },
    true
  );
  document.addEventListener("keydown", onKey);
  window.addEventListener("hashchange", () => {
    legacyRoute();
    renderDesk().catch((e) => showError(e.message));
  });
}

// Loads the decisions of one reviewer. A server without the reviewer filter
// answers 404 to it and is asked for the whole log, which ownDecisions cuts to
// the same reviewer. True when the reviewer has decisions on record.
async function loadDecisions(name) {
  let log = [];
  if (name) {
    let response = await fetch(`/review/decisions?${new URLSearchParams({ reviewer: name })}`);
    if (response.status === 404) response = await fetch("/review/decisions");
    if (!response.ok) throw new Error(`the decision log answered ${response.status}`);
    log = ownDecisions(await response.json(), name);
  }
  review.log = log;
  review.active = effective(log);
  review.loadedFor = name;
  return log.length > 0;
}

function showReviewError(reason) {
  el("review-error").textContent = `Decisions are not being recorded: ${reason}. The cards are read only until review_server.py can read its decision log; reload the page then.`;
  el("review-error").hidden = false;
}

// Read only without a review server (a static copy); a server that cannot
// read its log says why, and the page shows it instead of going quiet.
async function startReview() {
  let status;
  try {
    const response = await fetch("/review/status");
    if (!response.ok) return;
    status = await response.json();
  } catch {
    return;
  }
  if (status.error) showReviewError(status.error);
  if (status.recording !== true) return;
  try {
    await loadDecisions(reviewerName() || sessionName);
    review.recording = true;
  } catch (e) {
    showReviewError(e.message);
  }
}

// Switches to another reviewer's decisions; true when the cards change.
async function useReviewer(name) {
  if (!review.recording || name === review.loadedFor) return false;
  const had = review.log.length > 0;
  try {
    return (await loadDecisions(name)) || had;
  } catch (e) {
    review.recording = false;
    showReviewError(e.message);
    return true;
  }
}

function wikiOnlyRecords() {
  return (data.wiki.wikiOnlyPages || []).map((pid) => {
    const page = data.wiki.pages[String(pid)] || {};
    return {
      id: `wiki:${pid}`,
      entry: `wiki:${pid}`,
      isWikiOnly: true,
      volume: "WIKI",
      part: page.category || "MediaWiki",
      address: `Wiki page ${pid}`,
      page: pid,
      title: page.title || "",
      snippet: page.snippet || "",
      types: [],
      wikiType: page.type || "",
      review: false,
      year: page.year ? Number(page.year) : null,
      wiki: { status: "wiki-only" },
      pageInfo: page,
      addrKey: [0, "Wiki", Number(pid)],
      search: fold([pid, page.title, page.publisher, page.place, page.snippet].filter(Boolean).join(" ")),
    };
  });
}

async function start() {
  if (!Card) {
    showError("The shared card (/js/record-card.js) did not load. Start review_server.py and open the page it names.");
    return;
  }
  try {
    const response = await fetch("index.json");
    if (!response.ok) throw new Error(`index.json: ${response.status}`);
    data.index = await response.json();
    const vocab = await fetch("vocab.json");
    if (vocab.ok) data.vocab = await vocab.json();
    // Without the concordance nothing is known about the wiki, and every card says so.
    const wiki = await fetch("wiki_concordance.json").catch(() => null);
    if (wiki?.ok) data.wiki = await wiki.json();
  } catch (e) {
    showError(`The record index could not be loaded (${e.message}). Start review_server.py and open the page it names.`);
    return;
  }
  for (const o of data.index) {
    o.wiki = wikiState(data.wiki, o.id, o.entry);
    o.addrKey = naturalAddressKey(o.address);
    const year = o.search.match(YEAR);
    o.year = year ? Number(year[1]) : null;
  }
  data.records = [...data.index, ...wikiOnlyRecords()];
  data.byId = new Map(data.records.map((o) => [o.id, o]));
  for (const o of data.index) data.siblings.set(o.entry, [...(data.siblings.get(o.entry) ?? []), o.id]);
  await startReview();
  el("help-sample").textContent = review.recording ? `${sample().length} objects` : "a frozen set of objects";
  const kinds = [...new Set(data.index.flatMap((o) => o.types))].sort((a, b) => (TYPE_LABEL[a] ?? a).localeCompare(TYPE_LABEL[b] ?? b));
  el("kind").append(...kinds.map((t) => make("option", { value: t, text: TYPE_LABEL[t] ?? t })), make("option", { value: "(none)", text: "no type read" }));
  el("review-sample-all").textContent = `Sample, all (${sample().length})`;
  wire();
  legacyRoute();
  await renderDesk();
}

start();

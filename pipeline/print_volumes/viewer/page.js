// Page check: one PDF page beside everything the print strand read from it.
// Read only; review decisions stay in the card workbench. The data come from
// review_server.py (/check/page/<volume>/<n>.json and .png, page_render.py)
// and hold print text, so the view is local like the PDF.
import {
  VOLUME_LABEL,
  TYPE_LABEL,
  valueName,
  valueText,
  wikiState,
  candidates,
  candidateRoute,
  claimsShown,
  wikiHref,
  pdfHref,
} from "./render.js";

const VOLUMES = ["I", "A1", "A2"];
const SVG_NS = "http://www.w3.org/2000/svg";
// Characters of line text kept on each side of a passage.
const CONTEXT = 32;
const ROLE_WORD = {
  value: "in a value",
  record: "in a record, outside every value",
  heading: "heading or reference",
  apparatus: "apparatus",
  outside: "held by no record",
  furniture: "page furniture",
};
const KIND_WORD = {
  entry: "entry",
  heading: "heading",
  reference: "cross-reference",
  index: "index entry",
  front: "front matter",
  tail: "tail passage",
};
const BY_WORD = {
  rule: "rule",
  compiler: "compiler's address notation",
  inherited: "inherited by rule",
  llm: "LLM proposal",
};
const TYPES_PATH = /^types\[\d+\]$/;
const PAGE_NUMBER = /^[1-9]\d{0,4}$/;

const el = (id) => document.getElementById(id);

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

function svg(tag, attrs = {}) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  return node;
}

const state = {
  token: 0,
  data: null,
  // PDF pages per volume, from the pages loaded so far; a failed load names the range.
  pageCounts: new Map(),
  lines: new Map(),
  records: new Map(),
  // value key -> lines of this page; line -> value keys
  valueLines: new Map(),
  lineValues: new Map(),
  values: new Map(),
  hover: null,
  value: null,
  line: null,
  // The record a jump asked for; its lines stay lit until a line or value is chosen.
  record: null,
};

// The hash holds what a link can point at: volume, page, and optionally a record and a line.
// A part that names nothing is replaced, and the correction is said.
function readHash(hash) {
  const p = new URLSearchParams(hash.replace(/^#/, ""));
  const asked = p.get("v");
  const volume = VOLUMES.includes(asked) ? asked : "I";
  const rawPage = p.get("p");
  const page = PAGE_NUMBER.test(rawPage ?? "") ? Number(rawPage) : 1;
  const line = /^\d+$/.test(p.get("l") ?? "") ? Number(p.get("l")) : null;
  const corrections = [];
  if (asked !== null && asked !== volume) corrections.push(`There is no volume "${asked}"; the main volume is shown.`);
  if (rawPage !== null && !PAGE_NUMBER.test(rawPage)) corrections.push(`"${rawPage}" is no PDF page; page 1 is shown.`);
  return { volume, page, record: p.get("r") || null, line, corrections };
}

function hashFor({ volume, page, record = null, line = null }) {
  const p = new URLSearchParams({ v: volume, p: String(page) });
  if (record) p.set("r", record);
  if (line !== null) p.set("l", String(line));
  return `#${p}`;
}

// A passage in its line: [before, passage, after], cut to CONTEXT characters each side.
function passage(text, start, end) {
  const a = Math.max(0, start - CONTEXT);
  const b = Math.min(text.length, end + CONTEXT);
  return [(a > 0 ? "…" : "") + text.slice(a, start), text.slice(start, end), text.slice(end, b) + (b < text.length ? "…" : "")];
}

const valueKey = (object, value) => `${object.id}|${value.path}`;
const cardsHref = (record, object) => `cards.html#/?${new URLSearchParams({ q: record.id, o: object.id })}`;
// A record by its address where it has one, as its heading in the list names it.
const recordName = (id) => state.records.get(id)?.address || id;
const pageName = (volume, page) => `${VOLUME_LABEL[volume]}, PDF page ${page}`;

// The status line carries what an action did or why it did nothing; the page itself is named by the title.
function status(text) {
  el("pc-status").textContent = text;
}

// Scrolls a node into view inside its own pane, so that the other pane stays
// where it is. Below the two-pane width the list scrolls with the window and
// the page stays in its sticky strip, so the window scrolls the list there.
function reveal(node, block = "nearest") {
  if (!node) return;
  const pane = node.closest(".pc-page, .pc-extract");
  if (!pane || !/(auto|scroll)/.test(getComputedStyle(pane).overflowY)) {
    node.scrollIntoView({ block: "start" });
    return;
  }
  const view = pane.getBoundingClientRect();
  // Sticky children (pane heading, legend, selected line) cover the top of the pane.
  let top = view.top;
  for (const child of pane.children) {
    if (!child.hidden && getComputedStyle(child).position === "sticky") top = Math.max(top, child.getBoundingClientRect().bottom);
  }
  const box = node.getBoundingClientRect();
  const gap = 8;
  let delta = 0;
  if (block === "center") delta = box.top + box.height / 2 - (top + (view.bottom - top) / 2);
  else if (block === "start" || box.top < top) delta = box.top - top - gap;
  else if (box.bottom > view.bottom) delta = Math.min(box.bottom - view.bottom + gap, box.top - top - gap);
  pane.scrollTop += delta;
}

async function load() {
  const want = readHash(location.hash);
  const normal = hashFor(want);
  if (normal !== location.hash) history.replaceState(null, "", normal);
  const token = ++state.token;
  // A match list belongs to the search that made it.
  el("pc-matches").hidden = true;
  el("pc-matches").replaceChildren();
  el("pc-volume").value = want.volume;
  el("pc-page").value = String(want.page);
  status(`Loading ${pageName(want.volume, want.page)}.`);
  let response;
  let body;
  try {
    response = await fetch(`/check/page/${encodeURIComponent(want.volume)}/${want.page}.json`);
    body = await response.json();
  } catch (error) {
    if (token === state.token) fail(want, `the review server did not answer (${error.message})`);
    return;
  }
  if (token !== state.token) return;
  if (!response.ok) {
    fail(want, body?.error ?? response.statusText);
    return;
  }
  const focusInside = [el("pc-records"), el("pc-figure"), el("pc-selected")].some((node) => node.contains(document.activeElement));
  // A new page starts at its top in both panes.
  for (const pane of document.querySelectorAll(".pc-extract, .pc-page")) pane.scrollTop = 0;
  index(body);
  state.pageCounts.set(body.volume, body.pages);
  renderHead();
  renderFigure();
  renderRecords();
  state.hover = null;
  state.value = null;
  state.line = want.line !== null && state.lines.has(want.line) ? want.line : null;
  const target = want.record ? document.querySelector(`[data-record="${CSS.escape(want.record)}"]`) : null;
  state.record = target ? want.record : null;
  renderSelected();
  paint();
  const notes = [...want.corrections];
  if (want.record && !target && !body.withheld) notes.push(`Record ${want.record} holds no line of this page.`);
  status(notes.join(" "));
  if (target) {
    target.classList.add("is-target");
    const first = state.data.lines.find((ln) => ln.records.includes(want.record));
    if (first) reveal(el("pc-figure").querySelector(`[data-line="${first.line}"]`), "center");
    reveal(target, "start");
    target.querySelector("h3").focus({ preventScroll: true });
  } else if (focusInside) {
    // The focused node was replaced; the pane heading takes the focus.
    el("pc-extract-heading").focus();
  }
}

// A page that did not load leaves nothing of the page before it on screen.
function fail(want, reason) {
  const focusInside = [el("pc-records"), el("pc-figure"), el("pc-selected")].some((node) => node.contains(document.activeElement));
  index(null);
  const name = pageName(want.volume, want.page);
  el("pc-title").textContent = `Page check, ${name}`;
  document.title = `Page check ${want.volume} p. ${want.page}, Klawiter bibliography`;
  el("pc-prev").disabled = true;
  el("pc-next").disabled = true;
  el("pc-of").textContent = "";
  el("pc-legend").hidden = true;
  el("pc-figure").replaceChildren();
  renderSelected();
  const known = state.pageCounts.get(want.volume);
  const range = known ? ` ${VOLUME_LABEL[want.volume]} has PDF pages 1 to ${known}.` : "";
  el("pc-records").replaceChildren(make("p", { class: "review-error", role: "alert", text: `${name} could not be loaded: ${reason}.${range}` }));
  status("");
  if (focusInside) el("pc-extract-heading").focus();
}

function index(data) {
  state.data = data;
  state.lines = new Map((data?.lines ?? []).map((ln) => [ln.line, ln]));
  state.records = new Map((data?.records ?? []).map((r) => [r.id, r]));
  state.valueLines = new Map();
  state.lineValues = new Map();
  state.values = new Map();
  state.hover = null;
  state.value = null;
  state.line = null;
  state.record = null;
  for (const record of data?.records ?? []) {
    for (const object of record.objects) {
      for (const value of object.values) {
        const key = valueKey(object, value);
        state.values.set(key, { record, object, value });
        const here = value.lines.filter((s) => s.page === data.page).map((s) => s.line);
        state.valueLines.set(key, here);
        for (const n of here) {
          if (!state.lineValues.has(n)) state.lineValues.set(n, []);
          if (!state.lineValues.get(n).includes(key)) state.lineValues.get(n).push(key);
        }
      }
    }
  }
}

function renderHead() {
  const { volume, page, pages } = state.data;
  el("pc-title").textContent = `Page check, ${pageName(volume, page)}`;
  document.title = `Page check ${volume} p. ${page}, Klawiter bibliography`;
  el("pc-page").max = String(pages);
  el("pc-of").textContent = `of ${pages}`;
  el("pc-prev").disabled = page <= 1;
  el("pc-next").disabled = page >= pages;
  el("pc-pdf").href = pdfHref(volume, page);
}

function renderFigure() {
  const { volume, page, size, renderer } = state.data;
  const figure = el("pc-figure");
  el("pc-legend").hidden = !state.data.lines.length;
  if (!size) {
    figure.replaceChildren(fallback(renderer));
    return;
  }
  const sheet = make("div", { class: "pc-sheet" });
  const img = make("img", {
    src: `/check/page/${encodeURIComponent(volume)}/${page}.png`,
    alt: pageName(volume, page),
    width: String(Math.round(size.width * 2)),
    height: String(Math.round(size.height * 2)),
    decoding: "async",
  });
  img.addEventListener("error", () => figure.replaceChildren(fallback("the page image could not be rendered")), { once: true });
  const overlay = svg("svg", { class: "pc-overlay", viewBox: `0 0 ${size.width} ${size.height}`, role: "group", "aria-label": "Extracted lines; arrow keys move between them" });
  const first = state.data.lines[0]?.line;
  for (const ln of state.data.lines) {
    const label = `Line ${ln.line}, ${ROLE_WORD[ln.role]}${ln.defect ? ", defect characters" : ""}: ${ln.text.trim()}`;
    const height = Math.max(ln.bottom - ln.top + 2, 4);
    // A defect is marked in the margin, so that the hatch never covers the characters to be read.
    if (ln.defect) overlay.append(svg("rect", { class: "pc-defect-tab", x: String(Math.max(0, ln.x0 - 8)), y: String(ln.top - 1), width: "5", height: String(height), "aria-hidden": "true" }));
    const box = svg("rect", {
      class: `pc-box role-${ln.role}`,
      x: String(ln.x0 - 1.5),
      y: String(ln.top - 1),
      width: String(Math.max(ln.x1 - ln.x0 + 3, 4)),
      height: String(height),
      "data-line": String(ln.line),
      tabindex: ln.line === first ? "0" : "-1",
      role: "button",
      "aria-label": label,
    });
    const title = svg("title");
    title.textContent = label;
    box.append(title);
    overlay.append(box);
  }
  // The selected line gets a second, outer frame, so that the selection keeps the role's pattern visible.
  overlay.append(svg("rect", { id: "pc-selection", class: "pc-selection", display: "none", "aria-hidden": "true" }));
  overlay.addEventListener("click", (e) => {
    const box = e.target.closest("[data-line]");
    if (box) selectLine(Number(box.dataset.line), { from: "page" });
  });
  overlay.addEventListener("keydown", onBoxKey);
  sheet.append(img, overlay);
  figure.replaceChildren(sheet);
}

function fallback(reason) {
  const { volume, page } = state.data;
  return make(
    "div",
    { class: "pc-fallback" },
    make("p", { class: "pc-note", text: `Line boxes are not drawn: ${reason}. The PDF viewer shows the page instead.` }),
    make("iframe", { src: pdfHref(volume, page), title: pageName(volume, page), class: "pc-frame" }),
  );
}

function onBoxKey(e) {
  const box = e.target.closest("[data-line]");
  if (!box) return;
  const boxes = [...el("pc-figure").querySelectorAll("[data-line]")];
  const at = boxes.indexOf(box);
  let next = null;
  if (e.key === "ArrowDown" || e.key === "ArrowRight") next = boxes[Math.min(at + 1, boxes.length - 1)];
  else if (e.key === "ArrowUp" || e.key === "ArrowLeft") next = boxes[Math.max(at - 1, 0)];
  else if (e.key === "Home") next = boxes[0];
  else if (e.key === "End") next = boxes.at(-1);
  else if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    selectLine(Number(box.dataset.line), { from: "page" });
    return;
  } else return;
  e.preventDefault();
  selectLine(Number(next.dataset.line), { from: "page" });
  next.focus({ preventScroll: true });
  reveal(next);
}

function renderRecords() {
  if (state.data.withheld) {
    el("pc-records").replaceChildren(make("p", { class: "pc-withheld", text: state.data.withheld }));
    return;
  }
  const outside = state.data.lines.filter((ln) => ln.role === "outside");
  const parts = [];
  if (outside.length) {
    parts.push(
      make(
        "section",
        { class: "pc-outside", "aria-labelledby": "pc-outside-heading" },
        make("h3", { id: "pc-outside-heading", text: "Lines held by no record" }),
        make("ul", {}, ...outside.map((ln) => make("li", {}, lineRef(ln.line), " ", make("span", { class: "pc-print", text: ln.text.trim() })))),
      ),
    );
  }
  if (!state.data.records.length && !outside.length) {
    parts.push(make("p", { class: "quiet", text: "No line of this page is held by a record." }));
  }
  for (const record of state.data.records) parts.push(recordBlock(record));
  el("pc-records").replaceChildren(...parts);
  // The values of the page are one tab stop; the arrow keys move between them.
  el("pc-records").querySelector(".pc-pick")?.setAttribute("tabindex", "0");
}

// A line of this page is a button that selects it; a line elsewhere is text.
// In a value row it is no tab stop: the value itself is, and selecting it lights its lines.
function lineRef(n, page = state.data.page, { inRow = false } = {}) {
  if (page !== state.data.page) return make("span", { class: "pc-line-no", text: `p. ${page}, l. ${n}` });
  return make("button", { type: "button", class: "link pc-line-no", "data-select-line": String(n), tabindex: inRow ? "-1" : null, text: `l. ${n}` });
}

function recordBlock(record) {
  const own = record.pages.filter((p) => p === state.data.page).length;
  const here = state.data.lines.filter((ln) => ln.records.includes(record.id)).map((ln) => ln.line);
  const span = here.length ? (here.length > 1 ? `lines ${here[0]} to ${here.at(-1)}` : `line ${here[0]}`) : "";
  const other = record.pages.filter((p) => p !== state.data.page);
  const details = [KIND_WORD[record.kind] ?? record.kind, `part ${record.part}`, own ? span : "", other.length ? `also on p. ${other.join(", ")}` : ""].filter(Boolean).join(", ");
  const head = make(
    "h3",
    { tabindex: "-1" },
    make("span", { class: "pc-ident", text: record.address || record.id }),
    " ",
    record.address ? make("span", { class: "pc-id", text: record.id }) : null,
    " ",
    make("span", { class: "pc-details", text: details }),
  );
  const objects = record.objects.length
    ? record.objects.map((object) => objectBlock(record, object))
    : [make("p", { class: "quiet", text: "No object read from this record." })];
  return make("article", { class: "pc-record", "data-record": record.id }, head, ...objects);
}

function objectBlock(record, object) {
  const types = object.values.filter((v) => TYPES_PATH.test(v.path));
  const rows = object.values.filter((v) => !TYPES_PATH.test(v.path));
  const typeText = types.length
    ? types.map((t) => `${TYPE_LABEL[t.value] ?? String(t.value).replaceAll("_", " ")} (${BY_WORD[t.by] ?? t.by} ${t.rule})`).join("; ")
    : object.kind
      ? TYPE_LABEL[object.kind] ?? object.kind
      : "no type read";
  const name = [`Object ${object.position}`, object.address && object.address !== record.address ? object.address : ""].filter(Boolean).join(", ");
  const head = make(
    "div",
    { class: "pc-object-head" },
    make("h4", {}, make("span", { text: name }), " ", make("span", { class: "pc-id", text: object.id })),
    make("span", { class: "pc-type", text: typeText }),
    make("a", { href: cardsHref(record, object), class: "pc-card-link" }, "Open in card workbench", make("span", { class: "visually-hidden", text: ` (${object.id})` })),
  );
  const table = rows.length ? valueTable(record, object, rows) : make("p", { class: "quiet", text: "No value read." });
  return make("section", { class: "pc-object", "aria-label": `${name}, ${object.id}` }, head, table, record.apparatus ? null : candidateBlock(record, object));
}

function valueTable(record, object, rows) {
  const body = make("tbody");
  for (const value of rows) {
    const key = valueKey(object, value);
    const field = make("th", { scope: "row" }, valueName(value.field));
    // Where the passage is located, its p. and l. name the source; the record id is said only when it is not.
    const located = value.lines.length > 0;
    if (value.inherited) field.append(make("span", { class: "pc-inherited", text: located ? "inherited" : `inherited from ${value.source}` }));
    else if (value.source !== record.id && !located) field.append(make("span", { class: "pc-inherited", text: `from ${value.source}` }));
    const producer = make("td", {}, `${BY_WORD[value.by] ?? value.by} `, make("code", { text: value.rule ?? "" }));
    if (value.state) producer.append(make("span", { class: "pc-state", text: value.state }));
    const pick = make("button", { type: "button", class: "pc-pick", "data-pick": key, tabindex: "-1" }, valueText(value));
    const tr = make("tr", { "data-value": key }, field, make("td", { class: "pc-value" }, pick), producer, make("td", { class: "pc-passage" }, ...passageCells(value)));
    body.append(tr);
  }
  return make(
    "table",
    { class: "pc-values" },
    make("caption", { class: "visually-hidden", text: `Values of ${object.id}; up and down arrows move between the values of the page` }),
    make("thead", {}, make("tr", {}, make("th", { scope: "col", text: "Field" }), make("th", { scope: "col", text: "Value" }), make("th", { scope: "col", text: "Read by" }), make("th", { scope: "col", text: "Passage in its line" }))),
    body,
  );
}

function passageCells(value) {
  if (!value.lines.length) return [make("span", { class: "pc-missing", text: "passage not located in the lines" })];
  return value.lines.map((s) => {
    const line = s.page === state.data.page ? state.lines.get(s.line) : null;
    const text = line ? line.text : s.text ?? "";
    const [before, mark, after] = passage(text, s.start, s.end);
    return make(
      "span",
      { class: "pc-piece" },
      lineRef(s.line, s.page, { inRow: true }),
      line?.defect ? make("span", { class: "pc-defect", text: "defect" }) : null,
      " ",
      make("span", { class: "pc-print" }, before, make("mark", { text: mark }), after),
    );
  });
}

function candidateBlock(record, object) {
  const st = wikiState({ links: state.data.links }, object.id, record.id);
  const list = candidates(st);
  const items = list.map((c) => {
    const title = state.data.wikiPages[String(c.page)];
    const publication = c.target?.startsWith("klawiter:publication/") ? c.target : null;
    // Two publications of one wiki page differ only by their identifier.
    const which = publication ? `, publication ${publication.replace(/^klawiter:publication\//, "").replace(new RegExp(`^${c.page}-`), "")}` : "";
    return make(
      "li",
      {},
      make("a", { href: wikiHref(c.page, publication), target: "_blank", rel: "noopener", text: `Wiki page ${c.page}${title ? `, ${title}` : ""}${which}` }),
      `, ${candidateRoute(c)}, `,
      make("span", { class: "pc-state", text: c.state }),
      c.stale ? ", read from a record text that changed since" : "",
    );
  });
  const notes = Object.entries(st.totals ?? {}).map(([key, total]) => make("p", { class: "quiet", text: claimsShown(key, (st[key] ?? []).length, total) }));
  const diff = st.diff
    ? make("p", {}, `Field conflict with ${st.diff.wiki}: ${st.diff.differ.join(", ")} differ, `, make("span", { class: "pc-state", text: st.diff.state }))
    : null;
  if (!items.length && !diff) return make("p", { class: "pc-cands quiet", text: "No wiki candidate." });
  return make("div", { class: "pc-cands" }, make("h5", { text: "Wiki candidates, proposed by the concordance" }), items.length ? make("ul", {}, ...items) : null, ...notes, diff);
}

function renderSelected() {
  const box = el("pc-selected");
  const ln = state.line !== null ? state.lines.get(state.line) : null;
  if (!ln) {
    box.hidden = true;
    box.replaceChildren();
    return;
  }
  // The values themselves are the lit rows of the list; this names how many and leads to the first.
  const keys = (state.lineValues.get(ln.line) ?? []).filter((key) => !TYPES_PATH.test(state.values.get(key).value.path));
  const held = ln.records.length ? `Held by ${ln.records.map(recordName).join(", ")}` : "Held by no record";
  box.replaceChildren(
    make("h3", { text: `Line ${ln.line}, ${ROLE_WORD[ln.role]}${ln.defect ? ", defect characters" : ""}` }),
    make("p", { class: "pc-print", text: ln.text }),
    make(
      "p",
      { class: "quiet" },
      `${held}. `,
      keys.length
        ? make("button", { type: "button", class: "link", "data-goto-value": keys[0], text: `${keys.length} value${keys.length > 1 ? "s" : ""} on this line, marked in the list` })
        : "No value lies on this line.",
    ),
  );
  box.hidden = false;
}

// Classes follow the state: the selected line, the lines of the hovered or
// selected value or of the record a jump asked for, and the values of the selected line.
function paint() {
  const lit = new Set([...(state.valueLines.get(state.hover) ?? []), ...(state.valueLines.get(state.value) ?? [])]);
  if (state.record) for (const ln of state.data.lines) if (ln.records.includes(state.record)) lit.add(ln.line);
  const figure = el("pc-figure");
  for (const box of figure.querySelectorAll("[data-line]")) {
    const n = Number(box.dataset.line);
    box.classList.toggle("is-lit", lit.has(n));
    box.setAttribute("aria-pressed", String(n === state.line));
  }
  const frame = figure.querySelector("#pc-selection");
  const chosen = state.line !== null ? figure.querySelector(`[data-line="${state.line}"]`) : null;
  if (frame && chosen) {
    const pad = 2.5;
    for (const [name, grow] of [["x", -pad], ["y", -pad], ["width", 2 * pad], ["height", 2 * pad]]) frame.setAttribute(name, String(Number(chosen.getAttribute(name)) + grow));
    frame.removeAttribute("display");
  } else frame?.setAttribute("display", "none");
  const onLine = new Set(state.lineValues.get(state.line) ?? []);
  for (const row of el("pc-records").querySelectorAll("tr[data-value]")) {
    const key = row.dataset.value;
    row.classList.toggle("is-lit", onLine.has(key) || key === state.hover);
    row.classList.toggle("is-current", key === state.value);
    const pick = row.querySelector(".pc-pick");
    if (key === state.value) pick.setAttribute("aria-current", "true");
    else pick.removeAttribute("aria-current");
  }
}

function selectLine(n, { from }) {
  state.line = n;
  state.value = null;
  state.record = null;
  history.replaceState(null, "", hashFor({ ...readHash(location.hash), line: n }));
  renderSelected();
  paint();
  // The focused box becomes the page's tab stop.
  for (const box of el("pc-figure").querySelectorAll("[data-line]")) box.setAttribute("tabindex", Number(box.dataset.line) === n ? "0" : "-1");
  status("");
  if (from === "page") {
    // The first value on the line, in list order; a hovered row is lit as well and does not count.
    const onLine = new Set(state.lineValues.get(n) ?? []);
    const first = [...el("pc-records").querySelectorAll("tr[data-value]")].find((row) => onLine.has(row.dataset.value)) ?? el("pc-records").querySelector(`[data-select-line="${n}"]`);
    reveal(first ?? el("pc-selected"), "center");
  } else reveal(el("pc-figure").querySelector(`[data-line="${n}"]`));
}

function selectValue(key) {
  state.value = key;
  state.record = null;
  paint();
  const { value } = state.values.get(key);
  const here = state.valueLines.get(key) ?? [];
  if (!here.length) {
    const elsewhere = value.lines.map((s) => `p. ${s.page}, l. ${s.line}`);
    status(elsewhere.length ? `${valueName(value.field)} lies on ${elsewhere.join(", ")}, not on this page.` : `${valueName(value.field)}: passage not located.`);
    return;
  }
  status("");
  reveal(el("pc-figure").querySelector(`[data-line="${here[0]}"]`));
}

function go(volume, page, extra = {}) {
  const hash = hashFor({ volume, page, ...extra });
  if (hash === location.hash) load();
  else location.hash = hash;
}

function step(delta) {
  if (!state.data) return;
  const page = state.data.page + delta;
  if (page < 1 || page > state.data.pages) {
    status(`This is the ${delta < 0 ? "first" : "last"} page of the volume.`);
    return;
  }
  go(state.data.volume, page);
}

async function find(query) {
  const list = el("pc-matches");
  list.hidden = true;
  list.replaceChildren();
  let found;
  try {
    const response = await fetch(`/check/find.json?${new URLSearchParams({ q: query })}`);
    found = await response.json();
    if (!response.ok) {
      status(`Search for "${query}": ${found?.error ?? response.statusText}.`);
      return;
    }
  } catch (error) {
    status(`The review server did not answer the search for "${query}": ${error.message}`);
    return;
  }
  if (!found.length) {
    status(`No record is named "${query}".`);
    return;
  }
  if (found.length === 1) {
    go(found[0].volume, found[0].page, { record: found[0].id });
    return;
  }
  list.replaceChildren(
    ...found.map((r) =>
      make(
        "li",
        {},
        make("a", { href: `page.html${hashFor({ volume: r.volume, page: r.page, record: r.id })}`, text: r.address || r.id }),
        `${r.address ? ` ${r.id}` : ""}, ${pageName(r.volume, r.page)}, ${KIND_WORD[r.kind] ?? r.kind}`,
      ),
    ),
  );
  list.hidden = false;
  status(`${found.length} records match "${query}"${found.length >= 20 ? ", the first 20 shown" : ""}.`);
  list.querySelector("a").focus();
}

// The value buttons of the page form one tab stop; the arrow keys move between them.
function onPickKey(e) {
  const pick = e.target.closest(".pc-pick");
  if (!pick) return;
  const picks = [...el("pc-records").querySelectorAll(".pc-pick")];
  const at = picks.indexOf(pick);
  let next = null;
  if (e.key === "ArrowDown") next = picks[Math.min(at + 1, picks.length - 1)];
  else if (e.key === "ArrowUp") next = picks[Math.max(at - 1, 0)];
  else if (e.key === "Home") next = picks[0];
  else if (e.key === "End") next = picks.at(-1);
  else return;
  e.preventDefault();
  next.focus({ preventScroll: true });
  reveal(next.closest("tr"));
}

function wire() {
  // Skip links are buttons: a fragment link would change the hash, which names the page.
  for (const skip of document.querySelectorAll("[data-skip]")) skip.addEventListener("click", () => el(skip.dataset.skip).focus());
  el("pc-goto").addEventListener("submit", (e) => {
    e.preventDefault();
    const page = Number.parseInt(el("pc-page").value, 10);
    if (!Number.isInteger(page) || page < 1) {
      status("A PDF page is a whole number from 1.");
      return;
    }
    go(el("pc-volume").value, page);
  });
  el("pc-volume").addEventListener("change", () => go(el("pc-volume").value, 1));
  el("pc-prev").addEventListener("click", () => step(-1));
  el("pc-next").addEventListener("click", () => step(1));
  el("pc-find").addEventListener("submit", (e) => {
    e.preventDefault();
    const query = el("pc-query").value.trim();
    if (query) find(query);
  });
  const records = el("pc-records");
  const rowOf = (e) => e.target.closest?.("tr[data-value]");
  records.addEventListener("mouseover", (e) => {
    const key = rowOf(e)?.dataset.value ?? null;
    if (key !== state.hover) {
      state.hover = key;
      paint();
    }
  });
  records.addEventListener("mouseleave", () => {
    state.hover = null;
    paint();
  });
  records.addEventListener("focusin", (e) => {
    const pick = e.target.closest(".pc-pick");
    if (pick) for (const other of records.querySelectorAll(".pc-pick")) other.setAttribute("tabindex", other === pick ? "0" : "-1");
    state.hover = rowOf(e)?.dataset.value ?? null;
    paint();
  });
  // Focus leaving the list ends the hover it set.
  records.addEventListener("focusout", (e) => {
    if (records.contains(e.relatedTarget)) return;
    state.hover = null;
    paint();
  });
  records.addEventListener("click", (e) => {
    const lineBtn = e.target.closest("[data-select-line]");
    if (lineBtn) {
      selectLine(Number(lineBtn.dataset.selectLine), { from: "list" });
      return;
    }
    if (e.target.closest("a")) return;
    const row = rowOf(e);
    if (row) selectValue(row.dataset.value);
  });
  records.addEventListener("keydown", onPickKey);
  el("pc-selected").addEventListener("click", (e) => {
    const button = e.target.closest("[data-goto-value]");
    if (!button) return;
    const pick = records.querySelector(`[data-pick="${CSS.escape(button.dataset.gotoValue)}"]`);
    selectValue(button.dataset.gotoValue);
    reveal(pick?.closest("tr"), "center");
    pick?.focus({ preventScroll: true });
  });
  // [ and ] page through the volume; PageUp and PageDown stay with the scrolling panes.
  document.addEventListener("keydown", (e) => {
    if (e.altKey || e.ctrlKey || e.metaKey || e.defaultPrevented) return;
    if (e.target.closest?.("input, select, textarea, iframe")) return;
    if (e.key === "[") {
      e.preventDefault();
      step(-1);
    } else if (e.key === "]") {
      e.preventDefault();
      step(1);
    }
  });
  window.addEventListener("hashchange", load);
}

wire();
if (!location.hash) history.replaceState(null, "", hashFor({ volume: "I", page: 1 }));
load();

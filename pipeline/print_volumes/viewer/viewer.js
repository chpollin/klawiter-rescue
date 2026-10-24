// The local print viewer (knowledge/print-viewer.md): the review of one object
// at a time, a table of all records, data-cleaning questions (questions.js) and
// a help page. Data come from p12
// (index.json, vocab.json and the JSON-LD chunks next to this page); review
// decisions come from and go to review_server.py on the same origin. Nothing
// is fetched from elsewhere.

import {
  REVIEW_STATE,
  TYPE_LABEL,
  VOLUME_LABEL,
  chain,
  effective,
  fieldLabel,
  fold,
  grouped,
  history as decisionHistory,
  indexGraph,
  objectReview,
  rows,
  segments,
  targetsOf,
  valueText,
} from "./render.js";
import { initQuestions, loadQuestions, openAsk, renderQuestion, renderQuestions, wireQuestion } from "./questions.js";

const PAGE = 100;
const el = (id) => document.getElementById(id);
const chunks = new Map();
let index = [];
let byIdIndex = new Map();
let vocab = { roles: [], types: [], languages: [], missingFields: [] };
let wikiConcordance = { links: {}, pages: {}, pubs: {} };
// Without a concordance file nothing is known about the wiki, so the board
// claims nothing (no pipeline stage writes wiki_concordance.json yet).
let wikiLoaded = false;
// Review: whether the server records decisions, the full log, the decisions in force.
const review = { recording: false, log: [], active: new Map() };
// The object on screen, its selected value and the decision being prepared.
let shown = null;
let pending = null;

function make(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === undefined || value === null || value === false) continue;
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else node.setAttribute(key, value === true ? "" : value);
  }
  for (const child of children) if (child !== null && child !== undefined) node.append(child);
  return node;
}

const objectHash = (id, i = null) => `#/o/${encodeURIComponent(id)}${i === null ? "" : `/${i}`}`;

function params() {
  const query = location.hash.includes("?") ? location.hash.split("?")[1] : "";
  return new URLSearchParams(query);
}

function showError(message) {
  el("error").textContent = message;
  el("error").hidden = false;
}

function say(text) {
  el("message").textContent = text;
}

// Sample state

function completeIds() {
  const done = new Set();
  for (const d of review.active.values()) if (d.decision === "complete") done.add(d.object);
  return done;
}

function sample() {
  return index.filter((o) => o.review);
}

// The next open sample object after the given one, wrapping round.
function nextOpen(currentId = null) {
  const done = completeIds();
  const list = sample();
  const at = currentId ? list.findIndex((o) => o.id === currentId) : -1;
  const ordered = [...list.slice(at + 1), ...list.slice(0, at + 1)];
  return ordered.find((o) => !done.has(o.id) && o.id !== currentId) || null;
}

function sampleProgress() {
  const done = completeIds();
  const list = sample();
  return { done: list.filter((o) => done.has(o.id)).length, total: list.length };
}

function renderHeader(view) {
  for (const [id, name] of [["nav-review", "review"], ["nav-browse", "browse"], ["nav-questions", "questions"], ["nav-help", "help"]]) {
    if (name === view) el(id).setAttribute("aria-current", "page");
    else el(id).removeAttribute("aria-current");
  }
  const name = reviewerName() || sessionName;
  el("reviewer-line").hidden = !review.recording;
  el("reviewer-name").textContent = name ? `Reviewer: ${name}.` : "No reviewer set.";
  el("reviewer-change").textContent = name ? "Change" : "Set";
}

function showView(view) {
  el("browse-view").hidden = view !== "browse";
  el("object-view").hidden = view !== "object";
  el("help-view").hidden = view !== "help";
  el("questions-view").hidden = view !== "questions";
  el("question-view").hidden = view !== "question";
}

// Browse

function kindLabels(o) {
  return o.types.length ? o.types.map((t) => TYPE_LABEL[t] ?? t).join(", ") : "no type read";
}

function getWikiLink(objectId, entryId) {
  const objInfo = wikiConcordance.links[objectId] || {};
  const recInfo = wikiConcordance.links[entryId] || {};
  const align = objInfo.align || recInfo.align || null;
  const same = objInfo.same || recInfo.same || null;
  const cand = objInfo.cand || recInfo.cand || null;
  const diff = objInfo.diff || recInfo.diff || null;
  if (diff) return { status: "conflict", align, same, cand, diff };
  if (same || align) return { status: "matched", align, same, cand, diff: null };
  if (cand) return { status: "candidate", align: null, same: null, cand, diff: null };
  return { status: "print-only", align: null, same: null, cand: null, diff: null };
}

function renderBrowseWikiStrip(object, record) {
  if (!wikiLoaded) return null;
  const w = getWikiLink(object.id, record.id);
  const box = make("div", { class: `board-wiki-strip wiki-${w.status}` });
  if (w.status === "print-only") {
    box.append(make("div", { class: "board-wiki-head", text: "No wiki match found by the concordance" }));
    return box;
  }
  if (w.status === "conflict" && w.diff) {
    const d = w.diff;
    box.append(
      make("div", { class: "board-wiki-head", text: `Wiki conflict on ${d.wiki} (differ: ${d.differ.join(", ")})` })
    );
    return box;
  }
  if (w.same && w.same.length) {
    const top = w.same[0];
    const pub = wikiConcordance.pubs[top.target];
    const page = wikiConcordance.pages[String(top.page)];
    const agreed = top.secondField?.length ? ` (agreed on title, year + ${top.secondField.join(", ")})` : "";
    box.append(
      make("div", { class: "board-wiki-head", text: `Wiki match: page ${top.page}${pub ? `, ${top.target}` : ""}${agreed}` })
    );
    if (pub) {
      box.append(
        make("div", {
          class: "board-wiki-detail",
          text: `Wiki data: "${pub.title}", ${[pub.place, pub.publisher, pub.year, pub.extent].filter(Boolean).join(", ")}`,
        })
      );
    } else if (page) {
      box.append(
        make("div", {
          class: "board-wiki-detail",
          text: `Wiki page: "${page.title}", ${[page.place, page.publisher, page.year].filter(Boolean).join(", ")}`,
        })
      );
    }
    return box;
  }
  if (w.align && w.align.length) {
    const top = w.align[0];
    const pct = Math.round((top.score || 0) * 100);
    box.append(make("div", { class: "board-wiki-head", text: `Wiki text aligned: Page #${top.page} (${pct}% 5-gram overlap)` }));
    return box;
  }
  if (w.cand && w.cand.length) {
    const top = w.cand[0];
    const page = wikiConcordance.pages[String(top.page)];
    box.append(
      make("div", {
        class: "board-wiki-head",
        text: `Wiki candidate (title + year only): Page #${top.page}${page ? ` "${page.title}"` : ""}`,
      })
    );
  }
  return box;
}

function filtered(p) {
  const q = fold(p.get("q") || "");
  const volume = p.get("v") || "";
  const part = p.get("part") || "";
  const kind = p.get("k") || "";
  const wf = p.get("w") || "";
  const rv = p.get("r") || "";
  const done = completeIds();
  return index.filter((o) => {
    if (q && !o.search.includes(q)) return false;
    if (volume && o.volume !== volume) return false;
    if (part && o.part !== part) return false;
    if (kind && (kind === "(none)" ? o.types.length !== 0 : !o.types.includes(kind))) return false;
    if (rv && (!o.review || (rv === "open" ? done.has(o.id) : rv === "done" ? !done.has(o.id) : false))) return false;
    if (wf && wikiLoaded) {
      const w = getWikiLink(o.id, o.entry);
      if (wf === "matched" && w.status !== "matched" && w.status !== "conflict") return false;
      if (wf === "candidate" && w.status !== "candidate") return false;
      if (wf === "print-only" && w.status !== "print-only") return false;
      if (wf === "conflict" && w.status !== "conflict") return false;
    }
    return true;
  });
}

function buildBrowseCard(entry, object, record) {
  const all = rows(object).map((r) => ({ ...r, label: fieldLabel(r.field).label, text: valueText(r) }));
  const state = objectReview(object, all, review.active, record.sha256);
  const isGuide = entry.types.includes("collection") || record.kind === "header";
  const classes = ["board-card"];
  if (isGuide) classes.push("is-guide");
  if (state.complete) classes.push("is-complete");

  const addressText = object.address || (isGuide ? "Collection header" : "unnumbered");
  const titleNode = make(
    "h2",
    { class: `board-card-title${entry.title ? "" : " untitled"}` },
    make("a", { href: objectHash(entry.id), text: entry.title || "No title read" })
  );
  const head = make(
    "header",
    { class: "board-card-head" },
    make(
      "div",
      { class: "board-card-top" },
      make("span", { class: "board-card-address", text: `${addressText}, ${VOLUME_LABEL[object.volume]}, part ${object.part}, PDF page ${record.pdfPage}` }),
      make("span", { class: "board-card-where", text: `${kindLabels(entry)}${entry.review ? `, review ${state.complete ? "complete" : `${state.decided} of ${all.length} decided`}` : ""}` })
    ),
    titleNode
  );

  const wikiStrip = renderBrowseWikiStrip(object, record);

  const whole = (r) => r.start === object.selector.start && r.end === object.selector.end;
  const own = all.filter((r) => r.source === object.entry && !whole(r));
  const entryBox = make("p", { class: "board-card-entry" });
  const span = { start: object.selector.start, end: object.selector.end, index: -1 };
  for (const s of segments(record.text, [...own, span])) {
    const marks = s.marks.filter((m) => m >= 0);
    const inside = s.marks.includes(-1);
    const node = marks.length ? make("mark", { text: s.text }) : document.createTextNode(s.text);
    entryBox.append(inside ? make("span", { class: "object" }, node) : make("span", { class: "outside" }, node));
  }

  const table = make(
    "table",
    { class: "board-card-values" },
    make(
      "thead",
      { class: "visually-hidden" },
      make("tr", {}, make("th", { scope: "col", text: "Field" }), make("th", { scope: "col", text: "Value" }))
    )
  );
  const body = make("tbody");
  const contentsGroups = [];
  const COMPACT_GROUPS = /^(?:persons|imprints|extent|edition_notes|series|references|work_refs)/;
  for (const g of grouped(all)) {
    if (g.group.startsWith("contents[")) {
      contentsGroups.push(g);
      continue;
    }
    if (COMPACT_GROUPS.test(g.group) && g.rows.length > 1) {
      body.append(
        make(
          "tr",
          {},
          make("th", { scope: "row", class: "field", text: g.heading || g.rows[0].label }),
          make("td", { class: "value", text: g.rows.map((r) => r.text).join("; ") })
        )
      );
      continue;
    }
    for (const row of g.rows) {
      body.append(
        make(
          "tr",
          {},
          make("th", { scope: "row", class: "field", text: g.heading && g.rows.length === 1 ? g.heading : row.label }),
          make("td", { class: "value", text: row.text })
        )
      );
    }
  }
  table.append(body);

  let contentsDisclosure = null;
  if (contentsGroups.length > 0) {
    contentsDisclosure = make(
      "details",
      { class: "board-card-disclosure" },
      make("summary", { text: `Contents (${contentsGroups.length} items)` }),
      make("p", { class: "board-card-meta", text: contentsGroups.map((g) => g.rows.map((r) => r.text).join(" ")).join("; ") })
    );
  }

  const foot = make(
    "footer",
    { class: "board-card-foot" },
    make("a", { href: objectHash(entry.id), text: "Review single object" }),
    make("a", { href: `cards.html#/?q=${encodeURIComponent(entry.address || entry.id.split("#")[0])}`, text: "Interactive card desk" })
  );

  return make("article", { class: classes.join(" ") }, head, wikiStrip, entryBox, table, contentsDisclosure, foot);
}

const BOARD_PAGE = 18;

async function renderBrowse() {
  showView("browse");
  renderHeader("browse");
  document.title = "Records, Klawiter print volumes";
  const p = params();
  el("q").value = p.get("q") || "";
  el("volume").value = p.get("v") || "";
  if (el("part")) el("part").value = p.get("part") || "";
  el("kind").value = p.get("k") || "";
  if (el("wiki-filter")) el("wiki-filter").value = p.get("w") || "";
  el("review-filter").value = p.get("r") || "";
  // The table is the browse display of the contract; the board is optional.
  const mode = p.get("m") || "table";
  if (el("display-mode")) el("display-mode").value = mode;
  const { done, total } = sampleProgress();
  const next = nextOpen();
  const callout = el("review-callout");
  // Without the review server the decisions are unknown here, so no count.
  if (!review.recording) callout.replaceChildren("Read only: review decisions cannot be shown or recorded in this view.");
  else {
    callout.replaceChildren(`Review sample: ${done} of ${total} objects complete.`);
    if (next) callout.append(" ", make("a", { href: "#/review", text: "Continue the review" }));
  }
  const hits = filtered(p);
  const perPage = mode === "board" ? BOARD_PAGE : PAGE;
  const pages = Math.max(1, Math.ceil(hits.length / perPage));
  const page = Math.min(pages, Math.max(1, Number(p.get("page") || 1)));
  const slice = hits.slice((page - 1) * perPage, page * perPage);
  el("count").textContent = `${hits.length} object${hits.length === 1 ? "" : "s"}`;
  el("page").textContent = `Page ${page} of ${pages}`;
  el("prev").disabled = page <= 1;
  el("next").disabled = page >= pages;
  const doneIds = completeIds();

  if (mode === "board" && el("board")) {
    el("records").hidden = true;
    el("board").hidden = false;
    const uniqueChunks = [...new Set(slice.map((o) => o.chunk))];
    await Promise.all(uniqueChunks.map((c) => chunk(c)));
    const cards = [];
    for (const entry of slice) {
      const { byId, objects } = await chunk(entry.chunk);
      const object = objects.find((o) => o.id === entry.id);
      if (!object) continue;
      const record = byId.get(object.entry);
      cards.push(buildBrowseCard(entry, object, record));
    }
    el("board").replaceChildren(...cards);
    return;
  }

  if (el("board")) el("board").hidden = true;
  el("records").hidden = false;
  const body = el("records").tBodies[0];
  body.replaceChildren(
    ...slice.map((o) => {
      const title = o.title
        ? make("a", { href: objectHash(o.id), text: o.title })
        : make("a", { href: objectHash(o.id), class: "snippet" }, make("span", { class: "visually-hidden", text: "No title read, text begins: " }), `${o.snippet.replace(/[\s.,;:]+$/, "")}…`);
      return make(
        "tr",
        {},
        make("td", { class: "address", text: o.address || "unnumbered" }),
        make("td", { text: VOLUME_LABEL[o.volume] }),
        make("td", { text: o.part }),
        make("td", { class: "num", text: String(o.page) }),
        make("td", { class: "title" }, title),
        make("td", { text: kindLabels(o) }),
        make("td", { text: o.review && review.recording ? (doneIds.has(o.id) ? "complete" : "open") : o.review ? "sample" : "" })
      );
    })
  );
}

// Object

async function chunk(url) {
  if (!chunks.has(url)) {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`${url}: ${response.status}`);
    chunks.set(url, indexGraph(await response.json()));
  }
  return chunks.get(url);
}

const isApparatus = (object) => object.type === "kp:ApparatusItem";
const canDecide = () => review.recording && shown && !isApparatus(shown.object);

function describe(step) {
  switch (step.step) {
    case "value":
      return ["Value", `${JSON.stringify(step.value)}, ${step.derived ? "derived from the passage by its rule" : "the passage itself"}`];
    case "passage":
      return ["Passage", null];
    case "record":
      return [
        step.own ? "Record" : "Record it was inherited from",
        `${VOLUME_LABEL[step.volume]}, part ${step.part}${step.address ? `, ${step.address}` : ""}, PDF page ${step.pdfPage}${step.pdfPageEnd !== step.pdfPage ? `–${step.pdfPageEnd}` : ""}, line ${step.line}; identifier ${step.id}, text SHA-256 ${step.sha256.slice(0, 12)}…`,
      ];
    case "file":
      return ["Source file", `${step.fileName}, SHA-256 beginning ${step.sha256Prefix}`];
    case "producer":
      return [
        step.producer === "llm" ? "Proposed by an LLM" : step.producer === "compiler" ? "Read from the compiler's address notation" : step.producer === "inherited" ? "Inherited by rule" : "Read by rule",
        `${step.producer === "llm" ? "prompt" : "rule"} ${step.rule}${step.model ? `, model ${step.model}` : ""}${step.state ? `, state ${step.state}` : ""}`,
      ];
    case "target":
      return ["Address target", `${step.normalized} resolves to ${step.record ?? "no record with this address"}`];
    case "relation":
      return ["Relation target", step.target];
    default:
      return [step.step, ""];
  }
}

function decisionLine(d, text) {
  const what = {
    confirm: "right",
    correct: d.correction?.span ? `wrong, corrected to ${JSON.stringify(d.correction.value)}` : "wrong, the value should not exist",
    unresolved: "unsure",
  }[d.decision];
  return `${what}, by ${d.reviewer}, ${d.at.replace("T", " ").replace("Z", " UTC")}${d.note ? `. Note: ${d.note}` : ""}${text ? `. ${text}` : ""}`;
}

function renderChain(row) {
  const { object, byId, state } = shown;
  el("provenance").hidden = false;
  const items = chain(object, row, byId).map((step) => {
    const [label, text] = describe(step);
    const li = make("li", {}, make("span", { class: "label", text: label }));
    if (step.step === "passage") {
      li.append(make("span", { class: "exact", text: step.exact }), ` characters ${step.start}–${step.end}`);
    } else if (step.step === "record" && !step.own) {
      li.append(text);
      const box = make("p", { class: "record-text" });
      for (const s of segments(step.text, [{ start: row.start, end: row.end, index: 0 }])) {
        box.append(s.marks.length ? make("mark", { class: "current", text: s.text }) : s.text);
      }
      li.append(box);
    } else if ((step.step === "target" && step.record) || step.step === "relation") {
      const id = step.step === "target" ? step.record : step.target;
      li.append(make("a", { href: objectHash(id.includes("#") ? id : `${id}#1`), text }));
    } else {
      li.append(text);
    }
    return li;
  });
  const past = decisionHistory(review.log, object.id, row.field);
  const li = make("li", {}, make("span", { class: "label", text: "Review" }));
  if (past.length) {
    const list = make("ol", { class: "history" });
    const current = state.byIndex.get(row.index);
    for (const d of past) {
      const note = d === current ? "In force." : state.stale.includes(d) ? "No longer applies: the value has changed since." : "Replaced or withdrawn.";
      list.append(make("li", { text: decisionLine(d, note) }));
    }
    li.append(list);
  } else if (row.node.reviewState) {
    li.append(`${row.node.reviewState} at the last export`);
  } else {
    li.append(isApparatus(object) ? "not part of the review" : "no decision yet");
  }
  items.push(li);
  el("chain-steps").replaceChildren(...items);
}

// Character offset of a point inside the entry text: the rendered text equals
// the record text, so the length of the text before the point is the offset.
function offsetIn(container, node, offset) {
  const range = document.createRange();
  range.selectNodeContents(container);
  range.setEnd(node, offset);
  return range.toString().length;
}

function selectedSpan() {
  const sel = window.getSelection();
  const box = el("entry-text");
  if (!sel || sel.rangeCount === 0 || sel.isCollapsed) return null;
  const r = sel.getRangeAt(0);
  if (!box.contains(r.startContainer) || !box.contains(r.endContainer)) return null;
  let a = offsetIn(box, r.startContainer, r.startOffset);
  let b = offsetIn(box, r.endContainer, r.endOffset);
  const text = shown.record.text;
  while (a < b && /\s/.test(text[a])) a++;
  while (b > a && /\s/.test(text[b - 1])) b--;
  return a < b ? [a, b] : null;
}

function leaf(path) {
  return path.replace(/\[\d+\]/g, "").split(".").pop();
}

// The typed value a passage gives a field, as _review.py checks it.
function typedValue(path, passage) {
  if (["year", "year_end", "years"].includes(leaf(path))) {
    const m = passage.match(/\d{4}/);
    return m ? Number(m[0]) : null;
  }
  return passage;
}

function vocabFor(path) {
  const name = leaf(path);
  if (name === "roles") return vocab.roles;
  if (name === "types") return vocab.types;
  if (name === "language") return vocab.languages;
  return null;
}

function fillVocab(path) {
  const options = vocabFor(path);
  el("vocab-label").hidden = !options;
  if (options) el("vocab").replaceChildren(...options.map((v) => make("option", { value: v, text: TYPE_LABEL[v] ?? v })));
}

// The decision form opens in place: under the value it corrects, or after
// the object actions for a missing value or a boundary.
function openForm(kind, row = null) {
  // An inherited value's passage lies in another record: it can only be
  // marked wrong, with the right value in the note (_review.py).
  const inherited = kind === "correct" && row.source !== shown.object.entry;
  pending = { kind, row, span: null, inherited, opener: document.activeElement };
  say("");
  const form = el("decision-form");
  form.hidden = false;
  el("note").value = "";
  el("remove").checked = inherited;
  el("remove").disabled = inherited;
  el("passage-input").value = "";
  el("selection-preview").textContent = "";
  el("field-label").hidden = kind !== "missing";
  el("remove-row").hidden = kind !== "correct";
  if (kind === "boundary" || inherited) {
    el("vocab-label").hidden = true;
    el("selection-row").hidden = true;
  } else {
    fillVocab(row ? row.field : el("missing-field").value);
    el("selection-row").hidden = false;
  }
  el("decision-what").textContent = {
    correct: `Wrong: ${row?.label}, "${row?.text}"`,
    missing: "A value the rules did not read",
    boundary: "This object begins or ends in the wrong place",
  }[kind];
  el("decision-hint").textContent = inherited
    ? "This value is inherited from a heading or header. Give the right value in the note."
    : {
        correct: "Select the right passage in the entry text or type it, or tick that the value should not exist.",
        missing: "Choose the field, then select its passage in the entry text or type it.",
        boundary: "Say in the note where the object should begin or end.",
      }[kind];
  if (kind === "correct") {
    const tr = el("values").querySelector(`tr[data-index="${row.index}"]`);
    const holder = make("tr", { class: "form-row" }, make("td", { colspan: "3" }));
    tr.after(holder);
    holder.firstChild.append(form);
  } else {
    el("object-actions").after(form);
  }
  const first = kind === "boundary" || inherited ? el("note") : kind === "missing" ? el("missing-field") : el("vocab-label").hidden ? el("passage-input") : el("vocab");
  first.focus({ preventScroll: true });
  form.scrollIntoView({ block: "nearest" });
}

// Sets the passage of the pending decision and shows where it lies.
function setPassage(span) {
  pending.span = span;
  el("selection-preview").textContent = span ? `characters ${span[0]}–${span[1]}` : "not found in the entry text";
}

// A typed passage: its occurrence in the object nearest the value, else the
// first in the entry.
function findPassage(text) {
  const t = text.trim();
  if (!t) return null;
  const hay = shown.record.text;
  const hits = [];
  for (let at = hay.indexOf(t); at >= 0; at = hay.indexOf(t, at + 1)) hits.push(at);
  if (!hits.length) return null;
  const { start, end } = shown.object.selector;
  const near = pending.row ? pending.row.start : start;
  const inside = hits.filter((a) => a >= start && a + t.length <= end);
  const pool = inside.length ? inside : hits;
  const at = pool.reduce((best, a) => (Math.abs(a - near) < Math.abs(best - near) ? a : best), pool[0]);
  return [at, at + t.length];
}

function cancelForm() {
  const { row, opener } = pending || {};
  closeForm();
  if (row) select(row.index, { focus: true, scroll: false });
  else opener?.focus();
}

function closeForm() {
  pending = null;
  el("remove").disabled = false;
  const form = el("decision-form");
  form.hidden = true;
  el("object-actions").after(form);
  for (const tr of el("values").querySelectorAll("tr.form-row")) tr.remove();
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
    el("reviewer-input").value = reviewerName();
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
      renderHeader(currentView());
      resolve(name || reviewerName() || sessionName);
    };
    dialog.returnValue = "";
    dialog.addEventListener("close", done);
    dialog.showModal();
  });
}
let sessionName = "";

async function reviewer() {
  return reviewerName() || sessionName || (await askReviewer());
}

async function post(body) {
  const name = await reviewer();
  if (!name) {
    say("Not saved: a reviewer name or role is needed.");
    return null;
  }
  const payload = { object: shown.object.id, entry_sha256: shown.record.sha256, reviewer: name, ...body };
  let response;
  try {
    response = await fetch("/review/decisions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (e) {
    say(`Not saved: the review server did not answer (${e.message}).`);
    return null;
  }
  const answer = await response.json().catch(() => ({}));
  if (response.status !== 201) {
    const details = (answer.details || []).map((d) => `${d.loc.join(".")}: ${d.msg}`).join("; ");
    say(`Not saved: ${answer.error || response.status}${details ? ` (${details})` : ""}.`);
    return null;
  }
  review.log.push(answer);
  review.active = effective(review.log);
  return answer;
}

function targetOf(row) {
  return { path: row.field, value: row.value, span: [row.start, row.end], source: row.source };
}

async function rerender(selected, message = "") {
  const box = el("entry-text");
  const keep = { box: box.scrollTop, page: window.scrollY };
  await renderObject(shown.object.id, selected, { keepScroll: true });
  box.scrollTop = keep.box;
  window.scrollTo(0, keep.page);
  if (message) say(message);
}

async function decide(action, row) {
  if (!canDecide()) return;
  if (action === "correct") {
    openForm("correct", row);
    return;
  }
  closeForm();
  if (await post({ decision: action, target: targetOf(row) })) {
    await rerender(nextUndecided(row.index) ?? row.index, `Saved: ${row.label} ${action === "confirm" ? "right" : "unsure"}.`);
  }
}

// The values in the order the page shows them.
function displayOrder() {
  return [...el("values").querySelectorAll("tr[data-index]")].map((tr) => Number(tr.dataset.index));
}

// The next undecided value below the given one, as a reviewer reads down.
function nextUndecided(index) {
  const order = displayOrder();
  return order.slice(order.indexOf(index) + 1).find((i) => !shown.state.byIndex.has(i));
}

async function remainingRight() {
  if (!canDecide()) return;
  closeForm();
  const open = shown.all.filter((r) => !shown.state.byIndex.has(r.index));
  if (!open.length) {
    say("Every value already carries a decision.");
    return;
  }
  let saved = 0;
  for (const row of open) {
    if (!(await post({ decision: "confirm", target: targetOf(row) }))) break;
    saved += 1;
  }
  await rerender(shown.selected, `Saved: ${saved} value${saved === 1 ? "" : "s"} right.`);
  el("complete-next").focus();
}

async function completeAndNext() {
  if (!canDecide()) return;
  const { state, all, object } = shown;
  if (!state.complete) {
    if (state.decided < all.length) {
      say(`Not complete: ${all.length - state.decided} value${all.length - state.decided === 1 ? "" : "s"} still undecided.`);
      return;
    }
    if (!(await post({ decision: "complete" }))) return;
  }
  const next = nextOpen(object.id);
  if (next) location.hash = objectHash(next.id);
  else location.hash = "#/";
}

function stateLine(object, entry, state, all) {
  if (isApparatus(object)) {
    const kind = TYPE_LABEL[object.kind];
    return `${kind.charAt(0).toUpperCase()}${kind.slice(1)}, not part of the review.`;
  }
  const parts = [entry.review ? "Review sample" : "Outside the review sample"];
  if (!review.recording) return `${parts[0]}.`;
  if (state.complete) parts.push("complete");
  const missing = state.own.filter((d) => d.decision === "missing").length;
  if (missing) parts.push(`${missing} missing value${missing > 1 ? "s" : ""} added`);
  if (state.own.some((d) => d.decision === "boundary")) parts.push("boundary flagged as wrong");
  if (state.stale.length) parts.push(`${state.stale.length} decision${state.stale.length > 1 ? "s" : ""} no longer apply because a rebuild changed the value`);
  return parts.join(", ") + ".";
}

function whereLine(object, entry, record) {
  const siblings = index.filter((o) => o.entry === entry.entry);
  const parts = [VOLUME_LABEL[object.volume], `part ${object.part}`];
  if (object.address) parts.push(object.address);
  parts.push(`PDF page ${record.pdfPage}${record.pdfPageEnd !== record.pdfPage ? `–${record.pdfPageEnd}` : ""}`);
  if (siblings.length > 1) parts.push(`object ${siblings.findIndex((o) => o.id === object.id) + 1} of ${siblings.length} in this entry`);
  return parts.join(", ");
}

const DECISIONS = [
  ["confirm", "Right", "R"],
  ["correct", "Wrong", "W"],
  ["unresolved", "Unsure", "U"],
];

function valueCell(row, d) {
  const cell = make("td", { class: "value" });
  cell.append(make("button", { type: "button", class: "pick", "data-index": String(row.index), text: row.text }));
  if (row.producer === "llm") cell.append(" ", make("span", { class: "tag", text: "LLM proposal, unconfirmed" }));
  // A resolved address leads to the entries it names.
  const targets = targetsOf(shown.object, row.field).filter((t) => t.record);
  if (targets.length) {
    const list = make("span", { class: "targets" });
    for (const t of targets.slice(0, 6)) {
      const id = t.record.includes("#") ? t.record : `${t.record}#1`;
      const to = byIdIndex.get(id);
      const label = to ? to.title || `${to.snippet.slice(0, 40).replace(/[\s.,;:]+$/, "")}…` : t.record;
      list.append(make("a", { href: objectHash(id), text: `${t.normalized}: ${label}` }));
    }
    if (targets.length > 6) list.append(make("span", { text: `and ${targets.length - 6} more in the provenance` }));
    cell.append(list);
  }
  if (d?.decision === "correct") {
    const value = d.correction?.span ? valueText({ field: row.field, value: d.correction.value }) : null;
    cell.append(make("span", { class: "correction", text: value === null ? "should not exist" : `corrected to "${value}"` }));
  }
  return cell;
}

function decisionCell(row, d) {
  const cell = make("td", { class: "decide" });
  if (!canDecide()) {
    // Read only: the state the last export recorded, if any.
    const state = d ? REVIEW_STATE[d.decision] : row.node.reviewState;
    if (state) cell.append(make("span", { class: "state", text: state }));
    return cell;
  }
  const group = make("div", { role: "group", "aria-label": `Decision on ${row.label}` });
  for (const [action, label, key] of DECISIONS) {
    group.append(
      make(
        "button",
        { type: "button", class: `act act-${action}`, "data-act": action, "data-index": String(row.index), "aria-pressed": String(d?.decision === action) },
        label,
        make("kbd", { text: key })
      )
    );
  }
  cell.append(group);
  return cell;
}

function renderValues() {
  const { all, state } = shown;
  const table = el("values");
  for (const body of [...table.tBodies]) body.remove();
  for (const g of grouped(all.map((r) => ({ ...r, text: valueText(r) })))) {
    const body = make("tbody", { class: "group" });
    if (g.heading) body.append(make("tr", { class: "group-head" }, make("th", { colspan: "3", scope: "colgroup", text: g.heading })));
    for (const row of g.rows) {
      const d = state.byIndex.get(row.index);
      shown.byIndex.set(row.index, row);
      body.append(
        make(
          "tr",
          { "data-index": String(row.index), class: d ? `decided decided-${d.decision}` : "" },
          make("th", { scope: "row", class: "field", text: row.label }),
          valueCell(row, d),
          decisionCell(row, d)
        )
      );
    }
    table.append(body);
  }
  // Object decisions a reviewer may take back.
  const own = state.own.filter((d) => d.decision === "missing" || d.decision === "boundary");
  if (own.length) {
    const body = make("tbody", { class: "group" }, make("tr", { class: "group-head" }, make("th", { colspan: "3", scope: "colgroup", text: "Added by review" })));
    for (const d of own) {
      const remove = canDecide() ? make("button", { type: "button", class: "withdraw", "data-withdraw": d.id, text: "Remove" }) : null;
      const [label, text] = d.decision === "missing" ? [missingLabel(d.correction.field), String(d.correction.value)] : ["Boundary wrong", d.note];
      body.append(make("tr", { class: "decided" }, make("th", { scope: "row", class: "field", text: label }), make("td", { class: "value", text }), make("td", { class: "decide" }, remove)));
    }
    table.append(body);
  }
}

async function withdraw(id) {
  if (!canDecide()) return;
  if (await post({ decision: "withdraw", supersedes: id })) await rerender(shown.selected, "Removed.");
}

function renderEntryText() {
  const { object, record, all } = shown;
  // A value spanning the whole object (its types) marks nothing in the text.
  const whole = (r) => r.start === object.selector.start && r.end === object.selector.end;
  const own = all.filter((r) => r.source === object.entry && !whole(r));
  const box = el("entry-text");
  box.replaceChildren();
  const span = { start: object.selector.start, end: object.selector.end, index: -1 };
  for (const s of segments(record.text, [...own, span])) {
    const marks = s.marks.filter((m) => m >= 0);
    const inside = s.marks.includes(-1);
    const node = marks.length ? make("mark", { "data-marks": marks.join(" "), text: s.text }) : document.createTextNode(s.text);
    box.append(inside ? make("span", { class: "object" }, node) : make("span", { class: "outside" }, node));
  }
}

// Marks the selected value in the table and the text, without a rerender.
function select(i, { focus = false, scroll = true, pageScroll = true } = {}) {
  if (!shown || !shown.byIndex.has(i)) return;
  shown.selected = i;
  history.replaceState(null, "", objectHash(shown.object.id, i));
  for (const tr of el("values").querySelectorAll("tr.current")) tr.classList.remove("current");
  el("values").querySelector(`tr[data-index="${i}"]`)?.classList.add("current");
  let first = null;
  for (const m of el("entry-text").querySelectorAll("mark")) {
    const hit = m.dataset.marks.split(" ").includes(String(i));
    m.classList.toggle("current", hit);
    if (hit && !first) first = m;
  }
  if (scroll && first) scrollInto(el("entry-text"), first);
  renderChain(shown.byIndex.get(i));
  if (focus) el("values").querySelector(`button.pick[data-index="${i}"]`)?.focus({ preventScroll: !pageScroll });
}

// Scrolls a box, not the page, so that the node is in view.
function scrollInto(box, node) {
  const top = node.offsetTop - box.offsetTop;
  if (top < box.scrollTop + 8 || top > box.scrollTop + box.clientHeight - 40) box.scrollTop = Math.max(0, top - box.clientHeight / 3);
}

async function renderObject(id, selected = null, { keepScroll = false } = {}) {
  showView("object");
  const entry = byIdIndex.get(id);
  renderHeader(entry && /^(?:index|front|tail)$/.test(entry.types[0] ?? "") ? "browse" : "review");
  if (!entry) {
    showError(`No record ${id}.`);
    return;
  }
  const { byId, objects } = await chunk(entry.chunk);
  const object = objects.find((o) => o.id === id);
  const record = byId.get(object.entry);
  const all = rows(object).map((r) => ({ ...r, label: fieldLabel(r.field).label, text: valueText(r) }));
  if (!shown || shown.object.id !== id) closeForm();
  const state = objectReview(object, all, review.active, record.sha256);
  shown = { object, record, all, entry, byId, state, byIndex: new Map(), selected: null };
  document.title = `${entry.title || "Untitled object"}, Klawiter print volumes`;
  const heading = el("object-heading");
  heading.className = entry.title ? "" : "untitled";
  heading.textContent = entry.title || "No title read";
  el("object-where").textContent = whereLine(object, entry, record);
  el("object-state").textContent = stateLine(object, entry, state, all);
  renderEntryText();
  renderValues();
  const decidable = canDecide();
  el("object-actions").hidden = !decidable;
  el("ask-question").hidden = !review.recording;
  el("action-bar").hidden = isApparatus(object);
  el("all-right").hidden = !decidable;
  el("complete-next").hidden = !decidable;
  el("decided").textContent = decidable
    ? state.complete
      ? "Object complete."
      : `${state.decided} of ${all.length} values decided.`
    : "Read only.";
  el("complete-next").disabled = !state.complete && state.decided < all.length;
  const next = nextOpen(object.id);
  el("skip").hidden = !next;
  if (next) el("skip").href = objectHash(next.id);
  say("");
  el("provenance").hidden = true;
  if (!keepScroll) window.scrollTo(0, 0);
  fitSource();
  if (!keepScroll) {
    const start = el("entry-text").querySelector(".object");
    if (start) scrollInto(el("entry-text"), start);
  }
  const order = displayOrder();
  const pick = selected !== null && shown.byIndex.has(selected) ? selected : (order.find((i) => !state.byIndex.has(i)) ?? order[0]);
  // The first focus must not scroll the page past the object's head.
  if (pick !== undefined) select(pick, { focus: true, scroll: !keepScroll || selected !== null, pageScroll: keepScroll });
}

// The entry text box fills the space between its top and the action bar on
// wide screens, so that its last line never lies under the bar.
function fitSource() {
  const box = el("entry-text");
  if (el("object-view").hidden || !matchMedia("(min-width: 64.01rem)").matches) {
    box.style.maxHeight = "";
    return;
  }
  const bar = el("action-bar");
  const barTop = bar.hidden ? window.innerHeight : bar.getBoundingClientRect().top;
  const top = Math.max(box.getBoundingClientRect().top, 8);
  box.style.maxHeight = `${Math.max(160, Math.min(barTop, window.innerHeight) - top - 12)}px`;
}

// A field of the missing-value list ("imprints.year") in words ("Imprint, year").
function missingLabel(field) {
  const [head, ...rest] = field.split(".");
  const f = fieldLabel(rest.length || head === "notes" ? `${head}[0]${rest.length ? `.${rest.join(".")}` : ""}` : head);
  if (!f.heading || head === "notes") return f.label;
  return `${f.heading.replace(/ \d+$/, "")}, ${f.label.toLowerCase()}`;
}

function renderHelp() {
  showView("help");
  renderHeader("help");
  document.title = "Help, Klawiter print volumes";
}

function currentView() {
  if (location.hash.startsWith("#/help")) return "help";
  if (location.hash.startsWith("#/questions") || location.hash.startsWith("#/q/")) return "questions";
  if (location.hash.startsWith("#/o/") || location.hash.startsWith("#/review")) return "review";
  return "browse";
}

function route() {
  el("error").hidden = true;
  const match = location.hash.match(/^#\/o\/([^/]+)(?:\/(\d+))?$/);
  if (match) {
    renderObject(decodeURIComponent(match[1]), match[2] !== undefined ? Number(match[2]) : null).catch((e) => showError(e.message));
  } else if (location.hash.startsWith("#/review")) {
    const next = nextOpen();
    if (next) location.replace(objectHash(next.id));
    else {
      location.replace("#/");
    }
  } else if (location.hash.startsWith("#/help")) {
    renderHelp();
  } else if (location.hash.startsWith("#/questions")) {
    renderQuestions(params());
  } else if (location.hash.startsWith("#/q/")) {
    renderQuestion(location.hash.slice(4).split("?")[0], params());
  } else {
    renderBrowse().catch((e) => showError(e.message));
  }
}

// Keys act on the review only; typing in a field and an open dialog keep them.
function onKey(e) {
  if (e.ctrlKey || e.metaKey || e.altKey || el("reviewer-dialog").open || el("ask-dialog").open) return;
  const typing = e.target.closest("input, textarea, select");
  if (e.key === "Escape" && pending) {
    e.preventDefault();
    cancelForm();
    return;
  }
  if (pending && e.key === "Enter" && e.target.tagName !== "TEXTAREA" && e.target.tagName !== "BUTTON") {
    e.preventDefault();
    el("decision-form").requestSubmit();
    return;
  }
  if (typing || el("object-view").hidden || !shown) return;
  const order = [...el("values").querySelectorAll("tr[data-index]")].map((tr) => Number(tr.dataset.index));
  const at = order.indexOf(shown.selected);
  const row = shown.byIndex.get(shown.selected);
  const key = e.key.length === 1 ? e.key.toLowerCase() : e.key;
  const acts = {
    ArrowDown: () => at < order.length - 1 && select(order[at + 1], { focus: true }),
    j: () => at < order.length - 1 && select(order[at + 1], { focus: true }),
    ArrowUp: () => at > 0 && select(order[at - 1], { focus: true }),
    k: () => at > 0 && select(order[at - 1], { focus: true }),
    r: () => row && decide("confirm", row),
    w: () => row && decide("correct", row),
    u: () => row && decide("unresolved", row),
    a: () => remainingRight(),
    c: () => completeAndNext(),
    m: () => canDecide() && openForm("missing"),
    b: () => canDecide() && openForm("boundary"),
    n: () => !el("skip").hidden && (location.hash = el("skip").getAttribute("href")),
    q: () => askAboutShown(),
  };
  if (acts[key]) {
    e.preventDefault();
    acts[key]();
  }
}

function wire() {
  const update = () => {
    const p = new URLSearchParams();
    for (const [key, id] of [
      ["q", "q"],
      ["v", "volume"],
      ["part", "part"],
      ["k", "kind"],
      ["w", "wiki-filter"],
      ["r", "review-filter"],
      ["m", "display-mode"],
    ]) {
      const node = el(id);
      if (node && node.value && !(key === "m" && node.value === "table")) p.set(key, node.value);
    }
    return `#/?${p}`;
  };
  el("filters").addEventListener("submit", (e) => e.preventDefault());
  // Typing replaces the history entry instead of adding one per key.
  el("q").addEventListener("input", () => {
    history.replaceState(null, "", update());
    renderBrowse().catch((e) => showError(e.message));
  });
  for (const id of ["volume", "part", "kind", "wiki-filter", "review-filter", "display-mode"]) {
    el(id)?.addEventListener("change", () => {
      location.hash = update();
    });
  }
  const turn = (delta) => {
    const p = params();
    p.set("page", String(Math.max(1, Number(p.get("page") || 1) + delta)));
    location.hash = `#/?${p}`;
  };
  el("prev").addEventListener("click", () => turn(-1));
  el("next").addEventListener("click", () => turn(1));
  el("values").addEventListener("click", (e) => {
    const pick = e.target.closest("button.pick");
    if (pick) {
      select(Number(pick.dataset.index), { focus: false });
      return;
    }
    const act = e.target.closest("button.act");
    if (act) decide(act.dataset.act, shown.byIndex.get(Number(act.dataset.index)));
    const out = e.target.closest("button.withdraw");
    if (out) withdraw(out.dataset.withdraw);
  });
  el("values").addEventListener("focusin", (e) => {
    const pick = e.target.closest("button.pick");
    if (pick && Number(pick.dataset.index) !== shown?.selected) select(Number(pick.dataset.index));
  });
  el("add-missing").addEventListener("click", () => openForm("missing"));
  el("boundary").addEventListener("click", () => openForm("boundary"));
  el("all-right").addEventListener("click", remainingRight);
  el("complete-next").addEventListener("click", completeAndNext);
  el("missing-field").addEventListener("change", () => fillVocab(el("missing-field").value));
  document.addEventListener("selectionchange", () => {
    if (!pending || pending.kind === "boundary" || pending.inherited) return;
    const span = selectedSpan();
    if (span) {
      el("passage-input").value = shown.record.text.slice(span[0], span[1]);
      setPassage(span);
    }
  });
  el("passage-input").addEventListener("input", () => {
    if (pending) setPassage(el("passage-input").value.trim() ? findPassage(el("passage-input").value) : null);
  });
  el("cancel").addEventListener("click", cancelForm);
  el("decision-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!pending) return;
    const { kind, row, span } = pending;
    const note = el("note").value.trim();
    const path = kind === "missing" ? el("missing-field").value : row?.field;
    let body;
    if (kind === "boundary") {
      body = { decision: "boundary", note };
    } else {
      const removing = kind === "correct" && el("remove").checked;
      const options = vocabFor(path);
      if (!removing && !span) {
        el("selection-preview").textContent = "select or type the passage first";
        el("passage-input").focus();
        return;
      }
      const passage = span ? shown.record.text.slice(span[0], span[1]) : null;
      const value = removing ? null : options ? el("vocab").value : typedValue(path, passage);
      if (kind === "correct" && !removing && span[0] === row.start && span[1] === row.end && value === row.value) {
        el("selection-preview").textContent = "that is the value as read: choose Right, or a different passage";
        return;
      }
      const correction = removing ? {} : { value, span };
      if (kind === "missing") correction.field = path;
      body = { decision: kind, correction, note };
      if (kind === "correct") body.target = targetOf(row);
    }
    if (await post(body)) {
      closeForm();
      const target = row ? nextUndecided(row.index) ?? row.index : shown.selected;
      await rerender(target, kind === "boundary" ? "Saved: boundary flagged." : kind === "missing" ? "Saved: missing value added." : `Saved: ${row.label} wrong.`);
    }
  });
  el("reviewer-change").addEventListener("click", () => askReviewer());
  el("reviewer-cancel").addEventListener("click", () => el("reviewer-dialog").close(""));
  document.addEventListener("keydown", onKey);
  window.addEventListener("hashchange", route);
  let fitting = false;
  const refit = () => {
    if (fitting) return;
    fitting = true;
    requestAnimationFrame(() => {
      fitting = false;
      fitSource();
    });
  };
  window.addEventListener("resize", refit);
  window.addEventListener("scroll", refit, { passive: true });
}

// A question about the object on screen, with its selected value as the case.
function askAboutShown() {
  if (!review.recording || !shown) return;
  const row = shown.byIndex.get(shown.selected);
  const where = [VOLUME_LABEL[shown.object.volume], shown.object.part, shown.object.address || `PDF page ${shown.entry.page}`].filter(Boolean).join(", ");
  openAsk({ object: shown.object.id, path: row?.field, label: row ? `${where}, ${row.label}` : where });
}

async function startReview() {
  try {
    const status = await fetch("/review/status");
    review.recording = status.ok && (await status.json()).recording === true;
    if (review.recording) {
      const log = await fetch("/review/decisions");
      if (log.ok) review.log = await log.json();
      review.active = effective(review.log);
    }
  } catch {
    review.recording = false;
  }
}

async function start() {
  try {
    const response = await fetch("index.json");
    if (!response.ok) throw new Error(`index.json: ${response.status}`);
    index = await response.json();
    byIdIndex = new Map(index.map((o) => [o.id, o]));
    const v = await fetch("vocab.json");
    if (v.ok) vocab = await v.json();
    const w = await fetch("wiki_concordance.json").catch(() => null);
    if (w && w.ok) {
      wikiConcordance = await w.json();
      wikiLoaded = true;
    }
    const wikiLabel = el("wiki-filter")?.closest("label");
    if (wikiLabel) wikiLabel.hidden = !wikiLoaded;
  } catch (e) {
    showError(`The record index could not be loaded (${e.message}). Serve the folder data/print/derived over a local web server.`);
    return;
  }
  await startReview();
  const parts = [...new Set(index.map((o) => o.part).filter(Boolean))].sort();
  el("part")?.append(...parts.map((p) => make("option", { value: p, text: p })));
  const kinds = [...new Set(index.flatMap((o) => o.types))].sort((a, b) => (TYPE_LABEL[a] ?? a).localeCompare(TYPE_LABEL[b] ?? b));
  el("kind").append(...kinds.map((t) => make("option", { value: t, text: TYPE_LABEL[t] ?? t })), make("option", { value: "(none)", text: "no type read" }));
  el("missing-field").append(...vocab.missingFields.map((f) => make("option", { value: f, text: missingLabel(f) })));
  initQuestions({
    make,
    say,
    showView,
    renderHeader,
    reviewer,
    objectHash,
    recording: () => review.recording,
    indexEntry: (id) => byIdIndex.get(id),
    volumeLabel: (v) => VOLUME_LABEL[v] ?? v,
  });
  await loadQuestions();
  wireQuestion();
  el("ask-question").addEventListener("click", askAboutShown);
  wire();
  route();
}

start();

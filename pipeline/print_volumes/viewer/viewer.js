// The local print viewer: a searchable list of all objects and, per object,
// every value with its provenance chain and its review. Data come from p12
// (index.json, vocab.json and the JSON-LD chunks next to this page); review
// decisions come from and go to review_server.py on the same origin. Nothing
// is fetched from elsewhere.

import {
  REVIEW_STATE,
  chain,
  effective,
  fold,
  history,
  indexGraph,
  objectReview,
  rows,
  segments,
} from "./render.js";

const PAGE = 100;
const el = (id) => document.getElementById(id);
const chunks = new Map();
let index = [];
let vocab = { roles: [], types: [], languages: [], missingFields: [] };
// Review: whether the server records decisions, the full log, the decisions in force.
const review = { recording: false, log: [], active: new Map() };
// The object on screen and the decision being prepared.
let shown = null;
let pending = null;

function make(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else node.setAttribute(key, value);
  }
  for (const child of children) node.append(child);
  return node;
}

function params() {
  const query = location.hash.includes("?") ? location.hash.split("?")[1] : "";
  return new URLSearchParams(query);
}

function showError(message) {
  el("error").textContent = message;
  el("error").hidden = false;
}

function completeIds() {
  const done = new Set();
  for (const d of review.active.values()) if (d.decision === "complete") done.add(d.object);
  return done;
}

function filtered(p) {
  const q = fold(p.get("q") || "");
  const volume = p.get("v") || "";
  const type = p.get("t") || "";
  const producer = p.get("p") || "";
  const rv = p.get("r") || "";
  const done = completeIds();
  return index.filter(
    (o) =>
      (!q || o.search.includes(q)) &&
      (!volume || o.volume === volume) &&
      (!type || (type === "(none)" ? o.types.length === 0 : o.types.includes(type))) &&
      (!producer || o.producers.includes(producer)) &&
      (!rv ||
        (o.review && (rv === "sample" || (rv === "open" ? !done.has(o.id) : done.has(o.id)))))
  );
}

function setHash(p) {
  location.hash = "#/?" + p.toString();
}

function progressText() {
  const sample = index.filter((o) => o.review);
  const done = completeIds();
  const n = sample.filter((o) => done.has(o.id)).length;
  const mode = review.recording
    ? "Decisions are recorded by the local review server."
    : "Read only: start review_server.py to record decisions.";
  return `Review sample: ${n} of ${sample.length} objects complete. ${mode}`;
}

function renderList() {
  el("object-view").hidden = true;
  el("list-view").hidden = false;
  const p = params();
  el("q").value = p.get("q") || "";
  el("volume").value = p.get("v") || "";
  el("type").value = p.get("t") || "";
  el("producer").value = p.get("p") || "";
  el("review-filter").value = p.get("r") || "";
  el("progress").textContent = progressText();
  const hits = filtered(p);
  const pages = Math.max(1, Math.ceil(hits.length / PAGE));
  const page = Math.min(pages, Math.max(1, Number(p.get("page") || 1)));
  el("count").textContent = `${hits.length} of ${index.length} objects`;
  el("page").textContent = `Page ${page} of ${pages}`;
  el("prev").disabled = page <= 1;
  el("next").disabled = page >= pages;
  const done = completeIds();
  const items = hits.slice((page - 1) * PAGE, page * PAGE).map((o) =>
    make(
      "li",
      {},
      make(
        "a",
        { href: `#/o/${encodeURIComponent(o.id)}` },
        make("span", { class: "where", text: `${o.address || o.entry} · ${o.volume} p. ${o.page}` }),
        make("span", { class: "title", text: o.title }),
        make("span", {
          class: "types",
          text:
            (o.types.length ? o.types.join(", ") : "no type read") +
            (o.review ? (done.has(o.id) ? ", review sample, complete" : ", review sample, open") : ""),
        })
      )
    )
  );
  el("results").replaceChildren(...items);
}

async function chunk(url) {
  if (!chunks.has(url)) {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`${url}: ${response.status}`);
    chunks.set(url, indexGraph(await response.json()));
  }
  return chunks.get(url);
}

function describe(step) {
  switch (step.step) {
    case "value":
      return [
        "Value",
        `${JSON.stringify(step.value)} in field ${step.field}, ${step.derived ? "derived from the passage by its rule" : "the passage itself"}`,
      ];
    case "passage":
      return ["Passage", null];
    case "record":
      return [
        step.own ? "Record (the entry itself)" : "Record (inherited from)",
        `${step.id}${step.address ? ` (${step.address})` : ""}, ${step.kind}, volume ${step.volume}, part ${step.part}, PDF page ${step.pdfPage}${step.pdfPageEnd !== step.pdfPage ? `–${step.pdfPageEnd}` : ""}, line ${step.line}, text SHA-256 ${step.sha256.slice(0, 12)}…`,
      ];
    case "file":
      return ["Source file", `${step.fileName}, SHA-256 beginning ${step.sha256Prefix}`];
    case "producer":
      return [
        "Producer",
        `${step.producer}, ${step.producer === "llm" ? "prompt" : "rule"} ${step.rule}${step.model ? `, model ${step.model}` : ""}${step.state ? `, state ${step.state}` : ""}`,
      ];
    case "target":
      return ["Address target", `${step.normalized} → ${step.record ?? "no record with this address"}`];
    case "relation":
      return ["Relation target", step.target];
    default:
      return [step.step, ""];
  }
}

function decisionLine(d, text) {
  const what = {
    confirm: "confirmed as right in its context",
    correct: d.correction?.span ? `corrected to ${JSON.stringify(d.correction.value)}` : "marked as a value that should not exist",
    unresolved: "left open, the reviewer could not decide",
  }[d.decision];
  const passage = d.correction?.span ? ` (characters ${d.correction.span[0]}–${d.correction.span[1]} of the entry)` : "";
  return `${what}${passage} by ${d.reviewer}, ${d.at}${d.note ? `. Note: ${d.note}` : ""}${text ? `. ${text}` : ""}`;
}

function renderChain(object, row, byId, state) {
  const steps = chain(object, row, byId);
  const items = steps.map((step) => {
    const [label, text] = describe(step);
    const li = make("li", {}, make("span", { class: "label", text: label }));
    if (step.step === "passage") {
      li.append(make("span", { class: "exact", text: step.exact }), ` characters ${step.start}–${step.end}`);
    } else if (step.step === "record") {
      li.append(text);
      const box = make("p", { class: "record-text" });
      for (const s of segments(step.text, [{ start: row.start, end: row.end, index: 0 }])) {
        box.append(s.marks.length ? make("mark", { class: "current", text: s.text }) : s.text);
      }
      li.append(box);
    } else if ((step.step === "target" && step.record) || step.step === "relation") {
      const id = step.step === "target" ? step.record : step.target;
      li.append(make("a", { href: `#/o/${encodeURIComponent(id.includes("#") ? id : id + "#1")}`, text }));
    } else {
      li.append(text);
    }
    return li;
  });
  // The review step: every logged decision on this value, the one in force last.
  const past = history(review.log, object.id, row.field);
  const li = make("li", {}, make("span", { class: "label", text: "Review" }));
  if (past.length) {
    const list = make("ol", { class: "history" });
    const current = state.byIndex.get(row.index);
    for (const d of past) {
      const note = d === current ? "In force." : state.stale.includes(d) ? "Stale: the value has changed since." : "Superseded or withdrawn.";
      list.append(make("li", { text: decisionLine(d, note) }));
    }
    li.append(list);
  } else if (row.node.reviewState) {
    li.append(`${row.node.reviewState} at the last export (${row.node.review})`);
  } else {
    li.append("no person has decided on this value");
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
  const name = leaf(path);
  if (["year", "year_end", "years"].includes(name)) {
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

function openForm(kind, row = null) {
  pending = { kind, row, span: null };
  const form = el("decision-form");
  form.hidden = false;
  el("note").value = "";
  el("remove").checked = false;
  el("selection-preview").textContent = "";
  el("field-label").hidden = kind !== "missing";
  el("remove-row").hidden = kind !== "correct";
  el("use-selection").parentElement.hidden = kind === "boundary";
  const path = row ? row.field : el("missing-field").value;
  const options = kind === "boundary" ? null : vocabFor(path);
  el("vocab-label").hidden = !options;
  if (options) el("vocab").replaceChildren(...options.map((v) => make("option", { text: v })));
  el("decision-what").textContent = {
    correct: `Correct ${row?.field}: ${JSON.stringify(row?.value)}`,
    missing: "Add a value the rules did not read",
    boundary: "This object is split or joined wrongly",
  }[kind];
  el("decision-hint").textContent = {
    correct: "Select the right passage in the entry text and use it, or mark that the value should not exist.",
    missing: "Choose the field, select its passage in the entry text and use it.",
    boundary: "Say in the note where the object should begin or end.",
  }[kind];
  (kind === "boundary" ? el("note") : kind === "missing" ? el("missing-field") : el("use-selection")).focus();
}

function closeForm() {
  pending = null;
  el("decision-form").hidden = true;
}

function selectedIndex() {
  const m = location.hash.match(/^#\/o\/[^/]+\/(\d+)$/);
  return m ? Number(m[1]) : null;
}

async function submit(body, focus = null) {
  el("review-message").textContent = "";
  const reviewer = el("reviewer").value.trim();
  if (!reviewer) {
    el("review-message").textContent = "Enter a reviewer name or role first.";
    el("reviewer").focus();
    return false;
  }
  try {
    localStorage.setItem("print-reviewer", reviewer);
  } catch {
    // The name is a convenience; the decision carries it either way.
  }
  const payload = {
    object: shown.object.id,
    entry_sha256: shown.record.sha256,
    reviewer,
    ...body,
  };
  let response;
  try {
    response = await fetch("/review/decisions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (e) {
    el("review-message").textContent = `Not saved: the review server did not answer (${e.message}).`;
    return false;
  }
  const answer = await response.json().catch(() => ({}));
  if (response.status !== 201) {
    const details = (answer.details || []).map((d) => `${d.loc.join(".")}: ${d.msg}`).join("; ");
    el("review-message").textContent = `Not saved: ${answer.error || response.status}${details ? ` (${details})` : ""}.`;
    return false;
  }
  review.log.push(answer);
  review.active = effective(review.log);
  el("review-message").textContent = `Saved: ${answer.decision}.`;
  await renderObject(shown.object.id, selectedIndex(), focus);
  return true;
}

function targetOf(row) {
  return { path: row.field, value: row.value, span: [row.start, row.end], source: row.source };
}

function nextOpen(currentId) {
  const done = completeIds();
  const open = index.filter((o) => o.review && !done.has(o.id) && o.id !== currentId);
  return open[0] || null;
}

function renderReview(object, all, state, inSample) {
  const controls = el("review-controls");
  if (object.type === "kp:ApparatusItem") {
    // The review layer covers print objects only (_review.py checks them).
    controls.hidden = true;
    el("review-status").textContent = "Index entries, front matter and tail passages are shown with their provenance; review decisions cover the print objects only.";
    el("next-sample").hidden = true;
    return;
  }
  controls.hidden = !review.recording;
  const parts = [
    inSample ? "This object belongs to the frozen review sample, whose complete objects measure field correctness." : "This object is outside the review sample; decisions on it are development reviews and enter no measurement.",
    `${state.decided} of ${all.length} values carry a decision.`,
    state.complete ? "Marked complete." : "Not marked complete.",
  ];
  const missing = state.own.filter((d) => d.decision === "missing").length;
  if (missing) parts.push(`${missing} missing value${missing > 1 ? "s" : ""} added.`);
  if (state.own.some((d) => d.decision === "boundary")) parts.push("Boundary marked wrong.");
  if (state.stale.length) parts.push(`${state.stale.length} decision${state.stale.length > 1 ? "s" : ""} no longer apply because a rebuild changed the value.`);
  if (!review.recording) parts.push("Read only: start review_server.py to record decisions.");
  el("review-status").textContent = parts.join(" ");
  el("complete").disabled = state.decided < all.length || state.complete;
  el("complete").textContent = state.complete
    ? "Object marked complete"
    : state.decided < all.length
      ? `Mark object complete (${all.length - state.decided} values still undecided)`
      : "Mark object complete";
  const next = nextOpen(object.id);
  el("next-sample").hidden = !next;
  if (next) el("next-sample").href = `#/o/${encodeURIComponent(next.id)}`;
}

async function renderObject(id, selected, focus = null) {
  el("list-view").hidden = true;
  el("object-view").hidden = false;
  const entry = index.find((o) => o.id === id);
  if (!entry) {
    showError(`No object ${id}.`);
    return;
  }
  const { byId, objects } = await chunk(entry.chunk);
  const object = objects.find((o) => o.id === id);
  const record = byId.get(object.entry);
  const all = rows(object);
  if (!shown || shown.object.id !== id) closeForm();
  shown = { object, record, all, entry };
  const state = objectReview(object, all, review.active, record.sha256);
  el("object-heading").textContent = entry.title;
  el("object-meta").textContent = `${object.id}${object.address ? `, address ${object.address}` : ""}, volume ${object.volume}, part ${object.part}, PDF page ${record.pdfPage}, ${entry.types.length ? entry.types.join(", ") : "no type read"}, ${all.length} values`;
  const own = all.filter((r) => r.source === object.entry);
  const text = el("entry-text");
  text.replaceChildren();
  const span = { start: object.selector.start, end: object.selector.end };
  for (const s of segments(record.text, [...own, { ...span, index: -1 }])) {
    const marks = s.marks.filter((m) => m >= 0);
    const inside = s.marks.includes(-1);
    let node = s.text;
    if (marks.length) node = make("mark", { class: marks.includes(selected) ? "current" : "", text: s.text });
    text.append(inside ? node : make("span", { class: "outside" }, node));
  }
  renderReview(object, all, state, entry.review);
  const body = el("values").tBodies[0];
  body.replaceChildren(
    ...all.map((r) => {
      const d = state.byIndex.get(r.index);
      const cell = make("td", { class: "review" }, make("span", { class: `state${d?.decision === "correct" || d?.decision === "unresolved" ? " attention" : ""}`, text: d ? REVIEW_STATE[d.decision] : "no decision" }));
      if (review.recording && object.type !== "kp:ApparatusItem") {
        for (const [action, label] of [["confirm", "Right"], ["correct", "Wrong"], ["unresolved", "Unsure"]]) {
          cell.append(
            " ",
            make("button", {
              type: "button",
              class: "act",
              "data-act": action,
              "data-index": String(r.index),
              "aria-pressed": String(d?.decision === action),
              "aria-label": `${label}: ${r.field}`,
              text: label,
            })
          );
        }
      }
      return make(
        "tr",
        { class: r.index === selected ? "current" : "" },
        make("td", { class: "field", text: r.field }),
        make("td", { class: "value" }, make("button", { type: "button", class: "pick", "data-index": String(r.index), text: String(r.value) })),
        make("td", { class: r.producer === "llm" ? "producer-llm" : "", text: r.producer + (r.state ? ` (${r.state})` : "") }),
        cell
      );
    })
  );
  if (selected !== null && all[selected]) {
    renderChain(object, all[selected], byId, state);
  } else {
    el("chain-steps").replaceChildren();
  }
  // Restore focus after the table was replaced.
  const target = focus
    ? body.querySelector(`button[data-act="${focus.act}"][data-index="${focus.index}"]`)
    : selected !== null
      ? body.querySelector(`button.pick[data-index="${selected}"]`)
      : null;
  target?.focus();
}

function route() {
  el("error").hidden = true;
  const match = location.hash.match(/^#\/o\/([^/]+)(?:\/(\d+))?$/);
  if (match) {
    renderObject(decodeURIComponent(match[1]), match[2] !== undefined ? Number(match[2]) : null).catch((e) =>
      showError(e.message)
    );
  } else {
    renderList();
  }
}

function wire() {
  const update = () => {
    const p = new URLSearchParams();
    for (const [key, id] of [["q", "q"], ["v", "volume"], ["t", "type"], ["p", "producer"], ["r", "review-filter"]]) {
      if (el(id).value) p.set(key, el(id).value);
    }
    setHash(p);
  };
  el("filters").addEventListener("submit", (e) => e.preventDefault());
  el("q").addEventListener("input", update);
  for (const id of ["volume", "type", "producer", "review-filter"]) el(id).addEventListener("change", update);
  const turn = (delta) => {
    const p = params();
    p.set("page", String(Math.max(1, Number(p.get("page") || 1) + delta)));
    setHash(p);
  };
  el("prev").addEventListener("click", () => turn(-1));
  el("next").addEventListener("click", () => turn(1));
  el("values").addEventListener("click", (e) => {
    const pick = e.target.closest("button.pick");
    if (pick) {
      const id = location.hash.match(/^#\/o\/([^/]+)/)[1];
      location.hash = `#/o/${id}/${pick.dataset.index}`;
      return;
    }
    const act = e.target.closest("button.act");
    if (!act) return;
    const row = shown.all[Number(act.dataset.index)];
    if (act.dataset.act === "correct") {
      openForm("correct", row);
    } else {
      closeForm();
      submit({ decision: act.dataset.act, target: targetOf(row) }, { act: act.dataset.act, index: row.index });
    }
  });
  el("add-missing").addEventListener("click", () => openForm("missing"));
  el("boundary").addEventListener("click", () => openForm("boundary"));
  el("complete").addEventListener("click", () => submit({ decision: "complete" }));
  el("missing-field").addEventListener("change", () => {
    const options = vocabFor(el("missing-field").value);
    el("vocab-label").hidden = !options;
    if (options) el("vocab").replaceChildren(...options.map((v) => make("option", { text: v })));
  });
  el("use-selection").addEventListener("click", () => {
    const span = selectedSpan();
    if (!span) {
      el("selection-preview").textContent = "Select a passage inside the entry text first.";
      return;
    }
    pending.span = span;
    el("selection-preview").textContent = shown.record.text.slice(span[0], span[1]);
  });
  el("cancel").addEventListener("click", closeForm);
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
      if (!removing && !span) {
        el("selection-preview").textContent = "Select and use the passage that holds the right value.";
        return;
      }
      const options = vocabFor(path);
      const passage = span ? shown.record.text.slice(span[0], span[1]) : null;
      const value = removing ? null : options ? el("vocab").value : typedValue(path, passage);
      const correction = removing ? {} : { value, span };
      if (kind === "missing") correction.field = path;
      body = { decision: kind, correction, note };
      if (kind === "correct") body.target = targetOf(row);
    }
    if (await submit(body, row ? { act: "correct", index: row.index } : null)) closeForm();
  });
  window.addEventListener("hashchange", route);
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
  try {
    el("reviewer").value = localStorage.getItem("print-reviewer") || "";
  } catch {
    // Private windows may refuse storage; the field then starts empty.
  }
}

async function start() {
  try {
    const response = await fetch("index.json");
    if (!response.ok) throw new Error(`index.json: ${response.status}`);
    index = await response.json();
    const v = await fetch("vocab.json");
    if (v.ok) vocab = await v.json();
  } catch (e) {
    showError(`The object index could not be loaded (${e.message}). Serve the folder data/print/derived over a local web server.`);
    return;
  }
  await startReview();
  const types = [...new Set(index.flatMap((o) => o.types))].sort();
  el("type").append(...types.map((t) => make("option", { text: t })), make("option", { value: "(none)", text: "no type read" }));
  el("missing-field").append(...vocab.missingFields.map((f) => make("option", { text: f })));
  wire();
  route();
}

start();

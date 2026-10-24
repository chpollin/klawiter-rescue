// Data-cleaning questions (knowledge/print-viewer.md, Questions): a list with
// filters, one question with its cases, proposal, answer and history, and the
// form that asks a new question or adds a case from the object view. Events go
// to review_server.py (_questions.py); without the server the view is empty.

import { fieldLabel } from "./render.js";

export const CATEGORY_LABEL = {
  reading: "Reading",
  boundary: "Boundary",
  notation: "Notation",
  source: "Source",
  model: "Data model",
  vocabulary: "Vocabulary",
  concordance: "Print and wiki",
  other: "Other",
};
export const ANSWERER_LABEL = {
  operator: "Operator",
  "domain-expert": "Domain expert",
  "data-analysis": "Data analysis",
  "printed-copy": "Printed copy",
};
export const RESOLUTION_LABEL = {
  "change-rule": "Change the rule",
  "change-model": "Change the data model",
  "keep-as-read": "Keep as read",
  "source-error": "Error in the print",
  "needs-expert": "Needs an expert",
  "out-of-scope": "Out of scope",
};
const BY_LABEL = { person: "", rule: "rule", agent: "LLM agent" };
const CASES_SHOWN = 40;

let ctx = null;
const questions = { state: new Map(), loaded: false };
const el = (id) => document.getElementById(id);

export function initQuestions(context) {
  ctx = context;
  el("question-filters").addEventListener("change", () => {
    const p = new URLSearchParams();
    for (const [key, id] of [["s", "q-status"], ["c", "q-category"], ["a", "q-answerer"]]) if (el(id).value) p.set(key, el(id).value);
    location.hash = `#/questions?${p}`;
  });
  el("q-new").addEventListener("click", () => openAsk(null));
  el("ask-form").addEventListener("submit", submitAsk);
  el("ask-cancel").addEventListener("click", () => el("ask-dialog").close());
  el("ask-which").addEventListener("change", syncAsk);
  fillSelect(el("q-category"), CATEGORY_LABEL, "all");
  fillSelect(el("q-answerer"), ANSWERER_LABEL, "all");
  fillSelect(el("ask-category"), CATEGORY_LABEL, "not yet");
  fillSelect(el("ask-answerer"), ANSWERER_LABEL, "not yet");
}

function fillSelect(select, labels, empty) {
  select.append(ctx.make("option", { value: "", text: empty }), ...Object.entries(labels).map(([value, text]) => ctx.make("option", { value, text })));
}

// The server folds the log (_questions.fold); the page only shows the state.
export async function loadQuestions() {
  if (!ctx.recording()) return;
  const response = await fetch("/review/questions").catch(() => null);
  if (response && response.ok) {
    questions.state = new Map((await response.json()).map((q) => [q.id, q]));
    questions.loaded = true;
  }
}

async function send(body) {
  const author = await ctx.reviewer();
  if (!author) return { error: "a reviewer name or role is needed" };
  let response;
  try {
    response = await fetch("/review/questions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ author, by: "person", ...body }),
    });
  } catch (e) {
    return { error: `the review server did not answer (${e.message})` };
  }
  const answer = await response.json().catch(() => ({}));
  if (response.status !== 201) {
    const details = (answer.details || []).map((d) => `${d.loc.join(".")}: ${d.msg}`).join("; ");
    return { error: `${answer.error || response.status}${details ? ` (${details})` : ""}` };
  }
  await loadQuestions();
  return { stored: answer };
}

const producer = (who) => (who.by === "person" ? who.author : `${who.author}, ${BY_LABEL[who.by]}`);
const day = (at) => at.slice(0, 10);
const stateText = (q) => (q.answer ? RESOLUTION_LABEL[q.answer.resolution] : "open");

export function renderQuestions(p) {
  ctx.showView("questions");
  ctx.renderHeader("questions");
  document.title = "Questions, Klawiter print volumes";
  const body = el("question-rows");
  el("q-new").hidden = !ctx.recording();
  if (!questions.loaded) {
    el("question-count").textContent = "Questions are kept by the review server; this page is not served by it.";
    body.replaceChildren();
    return;
  }
  el("q-status").value = p.get("s") ?? "";
  el("q-category").value = p.get("c") ?? "";
  el("q-answerer").value = p.get("a") ?? "";
  const all = [...questions.state.values()];
  const shown = all.filter(
    (q) =>
      (!el("q-status").value || (el("q-status").value === "open") === !q.answer) &&
      (!el("q-category").value || q.category === el("q-category").value) &&
      (!el("q-answerer").value || q.answerer === el("q-answerer").value),
  );
  const open = all.filter((q) => !q.answer).length;
  el("question-count").textContent = `${shown.length} of ${all.length} questions shown; ${open} open.`;
  body.replaceChildren(
    ...shown.map((q) =>
      ctx.make(
        "tr",
        {},
        ctx.make("td", {}, ctx.make("a", { href: `#/q/${q.id}`, text: q.text })),
        ctx.make("td", { text: CATEGORY_LABEL[q.category] ?? "not yet" }),
        ctx.make("td", { text: ANSWERER_LABEL[q.answerer] ?? "not yet" }),
        ctx.make("td", { class: "num", text: q.cases.length === 1 ? "1 case" : `${q.cases.length} cases` }),
        ctx.make("td", { text: stateText(q) }),
        ctx.make("td", { text: producer(q.asked) }),
      ),
    ),
  );
}

function caseRow(c) {
  const o = ctx.indexEntry(c.object);
  const title = o ? o.title || o.snippet || "" : "";
  const where = o ? [ctx.volumeLabel(o.volume), o.part, o.address || `PDF page ${o.page}`].filter(Boolean).join(", ") : "no longer in the records";
  return ctx.make(
    "tr",
    {},
    ctx.make("td", {}, o ? ctx.make("a", { href: ctx.objectHash(c.object), text: where }) : ctx.make("span", { text: `${c.object}: ${where}` })),
    ctx.make("td", { text: title }),
    ctx.make("td", { text: c.path ? fieldLabel(c.path).label : "" }),
    ctx.make("td", { text: c.note ?? "" }),
  );
}

export function renderQuestion(id, p) {
  ctx.showView("question");
  ctx.renderHeader("questions");
  const q = questions.state.get(id);
  if (!q) {
    el("question-heading").textContent = questions.loaded ? "No such question" : "Questions are kept by the review server";
    for (const part of ["question-meta", "question-proposal", "question-answer", "answer-form", "question-cases-block", "question-history-block"]) el(part).hidden = true;
    return;
  }
  document.title = `${q.text.slice(0, 60)}, questions`;
  el("question-heading").textContent = q.text;
  const editable = ctx.recording();
  el("question-meta").hidden = false;
  el("qd-category").replaceChildren();
  el("qd-answerer").replaceChildren();
  fillSelect(el("qd-category"), CATEGORY_LABEL, "not yet");
  fillSelect(el("qd-answerer"), ANSWERER_LABEL, "not yet");
  el("qd-category").value = q.category ?? "";
  el("qd-answerer").value = q.answerer ?? "";
  el("qd-category").disabled = el("qd-answerer").disabled = !editable;
  el("qd-asked").textContent = `Asked by ${producer(q.asked)}, ${day(q.asked.at)}.`;
  el("question-proposal").hidden = !q.proposal;
  el("qd-proposal").textContent = q.proposal;
  el("question-answer").hidden = !q.answer;
  if (q.answer) {
    el("qd-resolution").textContent = RESOLUTION_LABEL[q.answer.resolution];
    el("qd-answer-text").textContent = q.answer.text;
    el("qd-answered").textContent = `Answered by ${q.answer.author}, ${day(q.answer.at)}.`;
  }
  el("qd-reopen").hidden = !(q.answer && editable);
  el("answer-form").hidden = !!q.answer || !editable;
  if (!q.answer) {
    el("af-resolution").replaceChildren();
    fillSelect(el("af-resolution"), RESOLUTION_LABEL, "choose");
    el("af-text").value = "";
  }
  el("question-cases-block").hidden = false;
  el("qd-cases-count").textContent = q.cases.length ? `${q.cases.length} cases` : "No cases yet. Add one from an object with Q.";
  const all = p.get("all") === "1";
  el("qd-cases").replaceChildren(...(all ? q.cases : q.cases.slice(0, CASES_SHOWN)).map(caseRow));
  el("qd-more").hidden = all || q.cases.length <= CASES_SHOWN;
  el("qd-more").href = `#/q/${q.id}?all=1`;
  el("qd-more").textContent = `Show all ${q.cases.length} cases`;
  el("question-history-block").hidden = false;
  el("qd-history").replaceChildren(
    ...q.events.map((e) => ctx.make("li", { text: `${day(e.at)}: ${EVENT_TEXT[e.event](e)}, ${producer(e)}.` })),
  );
  el("question-message").textContent = "";
  el("question-view").dataset.question = q.id;
}

const EVENT_TEXT = {
  ask: () => "asked",
  categorize: (e) => `set ${[e.category && CATEGORY_LABEL[e.category], e.answerer && `to be answered by ${ANSWERER_LABEL[e.answerer].toLowerCase()}`].filter(Boolean).join(", ")}`,
  case: (e) => `added ${e.cases === 1 ? "a case" : `${e.cases} cases`}`,
  answer: (e) => `answered: ${RESOLUTION_LABEL[e.resolution].toLowerCase()}`,
  reopen: () => "reopened",
};

export function wireQuestion() {
  const current = () => el("question-view").dataset.question;
  const report = (result, done) => {
    if (!result.error) renderQuestion(current(), new URLSearchParams());
    el("question-message").textContent = result.error ? `Not saved: ${result.error}.` : done;
  };
  for (const [id, key] of [["qd-category", "category"], ["qd-answerer", "answerer"]]) {
    el(id).addEventListener("change", async () => {
      if (!el(id).value) return;
      report(await send({ event: "categorize", question: current(), [key]: el(id).value }), "Saved.");
    });
  }
  el("answer-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!el("af-resolution").value) {
      el("question-message").textContent = "Choose a resolution first.";
      el("af-resolution").focus();
      return;
    }
    report(await send({ event: "answer", question: current(), resolution: el("af-resolution").value, text: el("af-text").value.trim() }), "Saved: answered.");
  });
  el("qd-reopen").addEventListener("click", async () => report(await send({ event: "reopen", question: current() }), "Saved: open again."));
}

// The ask dialog: a new question, or the case added to an existing one.
let asking = null;

export function openAsk(target) {
  if (!ctx.recording()) return;
  asking = target;
  el("ask-which").replaceChildren(
    ctx.make("option", { value: "", text: "a new question" }),
    ...[...questions.state.values()].filter((q) => !q.answer).map((q) => ctx.make("option", { value: q.id, text: q.text.length > 90 ? `${q.text.slice(0, 89)}…` : q.text })),
  );
  el("ask-which-label").hidden = !target;
  el("ask-case").textContent = target ? `Case: ${target.label}` : "";
  el("ask-text").value = "";
  el("ask-category").value = "";
  el("ask-answerer").value = "";
  el("ask-note").value = "";
  el("ask-message").textContent = "";
  syncAsk();
  el("ask-dialog").showModal();
  (target ? el("ask-which") : el("ask-text")).focus();
}

function syncAsk() {
  const existing = !!el("ask-which").value;
  for (const id of ["ask-text-label", "ask-category-label", "ask-answerer-label"]) el(id).hidden = existing;
  el("ask-note-label").hidden = !asking;
  el("ask-text").required = !existing;
}

async function submitAsk(e) {
  e.preventDefault();
  const cases = asking ? [{ object: asking.object, ...(asking.path ? { path: asking.path } : {}), note: el("ask-note").value.trim() }] : [];
  const which = el("ask-which").value;
  const body = which
    ? { event: "case", question: which, cases }
    : {
        event: "ask",
        text: el("ask-text").value.trim(),
        cases,
        ...(el("ask-category").value ? { category: el("ask-category").value } : {}),
        ...(el("ask-answerer").value ? { answerer: el("ask-answerer").value } : {}),
      };
  const result = await send(body);
  if (result.error) {
    el("ask-message").textContent = `Not saved: ${result.error}.`;
    return;
  }
  el("ask-dialog").close();
  ctx.say(which ? "Saved: case added to the question." : "Saved: question asked.");
  if (!asking) location.hash = `#/q/${result.stored.id}`;
}

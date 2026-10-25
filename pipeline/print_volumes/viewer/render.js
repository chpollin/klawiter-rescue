// Pure functions of the card workbench, shared by the page (cards.js) and the
// checks (check_render.mjs over all exported data, check_review.mjs over the
// review rules). They turn a JSON-LD chunk of p12 into the rows, card lines
// and provenance chains the page shows, project the wiki concordance onto an
// object, and decide on which card a key may act. Nothing here touches the DOM.

export function fold(text) {
  return text
    .toLowerCase()
    .replaceAll("ä", "ae")
    .replaceAll("ö", "oe")
    .replaceAll("ü", "ue")
    .replaceAll("ß", "ss")
    .normalize("NFD")
    .replace(/\p{M}/gu, "");
}

export function isValue(node) {
  if (node === null || typeof node !== "object") return false;
  const types = Array.isArray(node.type) ? node.type : [node.type];
  return types.includes("kp:Value");
}

// Text and years equal their passage; roles, types, kinds and languages are
// derived from it.
export function isDerived(node) {
  return Array.isArray(node.type) && node.type.includes("kp:DerivedValue");
}

// Every value node below an object, in document order.
export function valueNodes(node, out = []) {
  if (Array.isArray(node)) {
    for (const child of node) valueNodes(child, out);
  } else if (node !== null && typeof node === "object") {
    if (isValue(node)) {
      out.push(node);
    } else {
      for (const [key, child] of Object.entries(node)) {
        if (key !== "selector") valueNodes(child, out);
      }
    }
  }
  return out;
}

// Address targets travel beside the address value they resolve.
export function targetsOf(node, field) {
  const found = [];
  const walk = (n) => {
    if (Array.isArray(n)) n.forEach(walk);
    else if (n && typeof n === "object" && !isValue(n)) {
      if (n.address && isValue(n.address) && n.address.field === field && n.targets) {
        for (const t of n.targets) found.push(t);
      }
      Object.values(n).forEach(walk);
    }
  };
  walk(node);
  return found;
}

export function indexGraph(doc) {
  const byId = new Map();
  const objects = [];
  for (const node of doc["@graph"]) {
    if (node.id) byId.set(node.id, node);
    // Index entries, front matter and tail passages are listed like objects.
    if (node.type === "kp:PrintObject" || node.type === "kp:ApparatusItem") objects.push(node);
  }
  return { byId, objects };
}

export const isApparatus = (object) => object.type === "kp:ApparatusItem";

// What names an object on its card and in a message about it: the address,
// else the header or apparatus part, else the given fallback.
export function objectName(object, record, unnumbered = `unnumbered object ${object.id}`) {
  if (object.address) return object.address;
  if (record?.kind === "header") return `Header ${object.part}`;
  return isApparatus(object) ? object.part : unnumbered;
}

// One row per value: what the page lists for an object.
export function rows(object) {
  return valueNodes(object).map((v, index) => ({
    index,
    field: v.field,
    value: v.value,
    producer: v.producer,
    rule: v.rule,
    state: v.state ?? null,
    derived: isDerived(v),
    source: v.source,
    start: v.selector.start,
    end: v.selector.end,
    exact: v.selector.exact,
    node: v,
  }));
}

// A status line about a decision names the object it concerns, so that a
// message standing beside the next card never reads as one about it.
export const about = (name, verdict, detail) => `${verdict} on ${name}${detail ? `, ${detail}` : ""}.`;

// The provenance chain of one value, from its literal to the source file.
export function chain(object, row, byId) {
  const steps = [];
  steps.push({ step: "value", field: row.field, value: row.value, derived: row.derived });
  steps.push({ step: "passage", exact: row.exact, start: row.start, end: row.end });
  const record = byId.get(row.source);
  if (record) {
    steps.push({
      step: "record",
      id: record.id,
      kind: record.kind,
      volume: record.volume,
      part: record.part,
      address: record.address,
      pdfPage: record.pdfPage,
      pdfPageEnd: record.pdfPageEnd,
      line: record.line,
      sha256: record.sha256,
      own: record.id === object.entry,
      text: record.text,
    });
    const file = byId.get(record.derivedFrom);
    if (file) {
      steps.push({ step: "file", id: file.id, fileName: file.fileName, sha256Prefix: file.sha256Prefix });
    }
  }
  const plan = byId.get(row.rule);
  steps.push({
    step: "producer",
    producer: row.producer,
    rule: plan ? plan.label : row.rule,
    model: plan?.llm_model ?? null,
    state: row.state,
  });
  for (const target of targetsOf(object, row.field)) {
    steps.push({ step: "target", normalized: target.normalized, record: target.record ?? null });
  }
  if (object.relation && row.field.startsWith("relation") && object.relation.target) {
    steps.push({ step: "relation", target: object.relation.target });
  }
  return steps;
}

// A chain is complete when it reaches the passage, a record holding exactly
// that passage, the source file and the producer's plan.
export function chainComplete(steps) {
  const record = steps.find((s) => s.step === "record");
  const passage = steps.find((s) => s.step === "passage");
  return Boolean(
    record &&
      passage &&
      record.text.slice(passage.start, passage.end) === passage.exact &&
      steps.some((s) => s.step === "file") &&
      steps.some((s) => s.step === "producer" && s.rule)
  );
}

// Where a record stands: its page in the print volume, served by
// review_server.py, and a wiki page's permalink in the production frontend,
// the only home the wiki pages have since the wiki went offline.
export const WIKI_SITE = "https://chpollin.github.io/klawiter-rescue/";

export function pdfHref(volume, page) {
  return `/print/${encodeURIComponent(volume)}.pdf#page=${Number(page)}`;
}

export function wikiHref(page, publication = null) {
  const pub = publication ? `&pub=${encodeURIComponent(publication.replace(/^klawiter:publication\//, ""))}` : "";
  return `${WIKI_SITE}#entry=${Number(page)}${pub}`;
}

// The step of a provenance chain in words: [label, text].
export function describeStep(step) {
  switch (step.step) {
    case "value":
      return ["Value", `${JSON.stringify(step.value)}, ${step.derived ? "derived from the passage by its rule" : "the passage itself"}`];
    case "passage":
      return ["Passage", `characters ${step.start} to ${step.end}`];
    case "record":
      return [
        step.own ? "Record" : "Inherited from",
        `${VOLUME_LABEL[step.volume]}, part ${step.part}${step.address ? `, ${step.address}` : ""}, PDF page ${step.pdfPage}${step.pdfPageEnd && step.pdfPageEnd !== step.pdfPage ? ` to ${step.pdfPageEnd}` : ""}, line ${step.line}, ${step.id}`,
      ];
    case "file":
      return ["Source file", `${step.fileName}, SHA-256 ${step.sha256Prefix}`];
    case "producer":
      return [
        PRODUCER_LABEL[step.producer] ?? "Read by rule",
        `${step.producer === "llm" ? "prompt" : "rule"} ${step.rule}${step.model ? `, model ${step.model}` : ""}${step.state ? `, state ${step.state}` : ""}`,
      ];
    case "target":
      return ["Address target", `${step.normalized} ${step.record ? `resolves to ${step.record}` : "resolves to no record"}`];
    case "relation":
      return ["Relation target", step.target];
    default:
      return [step.step, ""];
  }
}

const PRODUCER_LABEL = {
  rule: "Read by rule",
  compiler: "Read from the compiler's address notation",
  inherited: "Inherited by rule",
  llm: "Proposed by an LLM",
};

// Review decisions (pipeline/print_volumes/_review.py). The page holds one
// reviewer's log (ownDecisions), over which effective() below equals
// _review.in_force() for that reviewer, so that the page shows the state p13
// will count for them.
// The exported state of a value (p12) as the decision that produced it.
export const STATE_DECISION = { confirmed: "confirm", contested: "unresolved" };
export const DECISION_WORD = { confirm: "right", correct: "wrong", unresolved: "unsure" };

export function decisionKey(d) {
  // An adjudication settles two reviewers' decisions; it never stands in for one (_review.key_of).
  if (d.decision === "adjudicate") return `${d.object}|adjudicate|${d.target ? d.target.path : [...(d.settles ?? [])].sort().join("/")}`;
  if (d.target) return `${d.object}|value|${d.target.path}`;
  if (d.decision === "missing") return `${d.object}|missing|${d.id}`;
  return `${d.object}|${d.decision}`;
}

// The decisions in force after supersession and withdrawal, by key.
export function effective(decisions) {
  const active = new Map();
  const keyOf = new Map();
  const byId = new Map(decisions.map((d) => [d.id, d]));
  for (const d of decisions) {
    if (d.decision === "withdraw") {
      const key = keyOf.get(d.supersedes);
      if (key && active.get(key) === byId.get(d.supersedes)) active.delete(key);
      continue;
    }
    const key = decisionKey(d);
    active.set(key, d);
    keyOf.set(d.id, key);
  }
  return active;
}

// A value decision applies while the value is as the reviewer saw it.
export function applies(d, row) {
  const t = d.target;
  return (
    t.path === row.field &&
    t.value === row.value &&
    t.span[0] === row.start &&
    t.span[1] === row.end &&
    t.source === row.source
  );
}

// The review state of one object: the decision in force per value row, the
// stale ones, the object decisions, and how many values carry a decision.
export function objectReview(object, all, active, sha256) {
  const byIndex = new Map();
  const stale = [];
  const own = [];
  for (const d of active.values()) {
    if (d.object !== object.id || d.decision === "adjudicate") continue;
    if (d.entry_sha256 !== sha256) {
      stale.push(d);
    } else if (d.target) {
      const row = all.find((r) => r.field === d.target.path);
      if (row && applies(d, row)) byIndex.set(row.index, d);
      else stale.push(d);
    } else {
      own.push(d);
    }
  }
  const complete = own.some((d) => d.decision === "complete");
  return { byIndex, stale, own, complete, decided: byIndex.size };
}

// A reviewer sees only their own decisions, so that a second reviewer stays
// blind to the first. The server filters by ?reviewer=; this filter holds the
// same rule where a server returns the whole log.
export function ownDecisions(log, name) {
  return name ? log.filter((d) => d.reviewer === name) : [];
}

// Every logged decision on one value, oldest first: its review history.
export function history(decisions, objectId, path) {
  return decisions.filter((d) => d.object === objectId && d.target && d.target.path === path && d.decision !== "adjudicate");
}

export function decisionLine(d) {
  const what = {
    confirm: "right",
    correct: d.correction?.span ? `wrong, corrected to ${JSON.stringify(d.correction.value)}` : "wrong, the value should not exist",
    unresolved: "unsure",
  }[d.decision];
  return `${what}, by ${d.reviewer}, ${d.at.replace("T", " ").replace("Z", " UTC")}${d.note ? `, note "${d.note}"` : ""}`;
}

export function targetOf(row) {
  return { path: row.field, value: row.value, span: [row.start, row.end], source: row.source };
}

export function leaf(path) {
  return path.replace(/\[\d+\]/g, "").split(".").pop();
}

const YEAR_LEAVES = ["year", "year_end", "years"];
const FLAG_LEAVES = ["year_bracketed", "circa"];

export function vocabFor(vocab, path) {
  const name = leaf(path);
  if (name === "roles") return vocab.roles;
  if (name === "types") return vocab.types;
  if (name === "language") return vocab.languages;
  return null;
}

// The value a passage gives a field, typed as _review.check requires it: a
// year is the number of its four digits, a flag the boolean true at the
// passage that shows it, a vocabulary word the chosen word, any other value
// the passage itself. Null when the passage holds no such value.
export function correctionValue(path, passage, choice = null) {
  const name = leaf(path);
  if (YEAR_LEAVES.includes(name)) {
    const m = passage.match(/\d{4}/);
    return m ? Number(m[0]) : null;
  }
  if (FLAG_LEAVES.includes(name)) return true;
  if (["roles", "types", "language"].includes(name)) return choice || null;
  return passage;
}

// An inherited value's passage lies in another record, so the only
// correction is that it should not exist (_review.check).
export const isInherited = (row, object) => row.source !== object.entry;

// A typed passage: its occurrence inside the object nearest the value, else
// the first in the entry nearest it. Null when the text does not hold it.
export function findPassage(text, typed, near, objectSpan) {
  const t = typed.trim();
  if (!t) return null;
  const hits = [];
  for (let at = text.indexOf(t); at >= 0; at = text.indexOf(t, at + 1)) hits.push(at);
  if (!hits.length) return null;
  const [start, end] = objectSpan;
  const inside = hits.filter((a) => a >= start && a + t.length <= end);
  const pool = inside.length ? inside : hits;
  const at = pool.reduce((best, a) => (Math.abs(a - near) < Math.abs(best - near) ? a : best), pool[0]);
  return [at, at + t.length];
}

// Keys act on one card only: the active card that holds the focus and lies
// in the viewport, never while a card loads or a decision is being saved.
export function acceptsKeys({ loading, busy, connected, focusWithin, inView }) {
  return !loading && !busy && connected && focusWithin && inView;
}

// A value is displayed when its box lies inside every clip around it: each
// scrolling ancestor and the viewport. checkVisibility() alone ignores
// scrolling, so a value scrolled out of its column would count as shown.
export function inSight(box, clips, tolerance = 1) {
  if (!(box.width > 0 && box.height > 0)) return false;
  return clips.every(
    (c) => box.top >= c.top - tolerance && box.bottom <= c.bottom + tolerance && box.left >= c.left - tolerance && box.right <= c.right + tolerance
  );
}

// The rows "all right" may confirm: the undecided values the card displays.
// A value the card does not display is never confirmed with the others.
export function confirmable(all, decided, shown) {
  return all.filter((r) => !decided.has(r.index) && shown.has(r.index));
}

// Readable names. A value's field is a path of the schema
// ("persons[0].roles[1]"); the page shows it in a group ("Person 1") with a
// label ("Role 2"), so that no code path reaches the reader.
export const VOLUME_LABEL = { I: "Main volume", A1: "Addendum I", A2: "Addendum II", WIKI: "MediaWiki" };
export const VOLUME_SHORT = { I: "I", A1: "A1", A2: "A2" };
export const TYPE_LABEL = {
  book_edition: "book edition",
  translation: "translation",
  collection_contribution: "contribution to a collection",
  periodical_contribution: "periodical contribution",
  review: "review",
  event: "event",
  holding: "holding",
  reference: "cross-reference",
  collection: "collection header",
  index: "index entry",
  front: "front matter",
  tail: "tail passage",
};
// Section names of the contents of 1991, as docs/js/home.js shows them.
export const SECTION_NAME = {
  A: "Collected Works",
  B: "Selected Works",
  C: "Essays and Lectures in Book Form",
  D: "Poetry",
  E: "Dramas",
  F: "Fiction",
  G: "Historical and Biographical Studies",
  H: "Essays, Lectures and Reviews",
  I: "Translations by Zweig",
  J: "Forewords and Afterwords by Zweig",
  K: "Correspondence",
  L: "Secondary Literature",
  M: "Reviews of Zweig's Works",
  N: "Film Versions of Zweig's Works",
  O: "Zweig's Works Set to Music",
  P: "Zweig Symposia",
  Q: "Works Dedicated to Zweig",
  R: "Handwritten Dedications",
};

// "FA1" and "F" are the same section in different volumes; index parts keep their name.
export function sectionCode(part) {
  const m = String(part || "").match(/^([A-R])(?:A1|A2)?$/);
  return m ? m[1] : String(part || "");
}

const KEY_LABEL = {
  title: "Title",
  subtitle: "Subtitle",
  original_title: "Original title",
  variant_titles: "Variant title",
  subject: "Subject",
  language: "Language",
  term: "Term",
  passage: "Passage",
  name: "Name",
  roles: "Role",
  place: "Place",
  publisher: "Publisher",
  year: "Year",
  year_end: "End year",
  year_bracketed: "Year in brackets",
  circa: "Circa",
  raw: "As printed",
  parts: "Segment",
  volumes: "Volumes",
  illustrations: "Illustrations",
  years: "Year",
  number: "Number",
  siglum: "Siglum",
  volume: "Volume",
  issue: "Issue",
  date: "Date",
  pages: "Pages",
  locator: "Locator",
  address: "Address",
  kind: "Kind",
  repository: "Repository",
  medium: "Medium",
  persons: "Person",
  imprints: "Imprint",
  extent: "Extent",
  edition_notes: "Edition note",
  series: "Series",
  work_refs: "Work reference",
  types: "Type",
  informants: "Informant",
  notes: "Note",
};
// Top-level keys in reading order; HEAD keys form the untitled first group,
// LISTS one group per item, the rest one group each.
const ORDER = [
  "head",
  "persons",
  "imprints",
  "extent",
  "edition_notes",
  "series",
  "periodicals",
  "hosts",
  "reviewed",
  "event",
  "contents",
  "holdings",
  "informants",
  "notes",
  "references",
  "work_refs",
  "relation",
  "inherited",
];
const HEAD_ORDER = ["term", "title", "subtitle", "original_title", "variant_titles", "subject", "language", "types", "passage"];
const HEAD = new Set(HEAD_ORDER);
const LISTS = new Set(["persons", "imprints", "edition_notes", "series", "periodicals", "hosts", "reviewed", "contents", "holdings", "references", "work_refs"]);
const GROUP_LABEL = {
  persons: "Person",
  imprints: "Imprint",
  extent: "Extent",
  edition_notes: "Edition note",
  series: "Series",
  periodicals: "Periodical",
  hosts: "Published in",
  reviewed: "Reviewed work",
  event: "Event",
  contents: "Contents item",
  holdings: "Holding",
  informants: "Informants",
  notes: "Notes",
  references: "Reference",
  work_refs: "Work reference",
  relation: "Relation",
  inherited: "From a heading or header",
};
// The short label of a card line, one line per group of the bibliography.
const LINE_LABEL = {
  persons: "Persons",
  imprints: "Imprint",
  extent: "Extent",
  edition_notes: "Edition",
  series: "Series",
  periodicals: "Periodical",
  hosts: "In",
  reviewed: "Reviewed",
  event: "Event",
  contents: "Contents",
  holdings: "Holding",
  informants: "Informants",
  notes: "Notes",
  references: "References",
  work_refs: "Work refs",
  relation: "Relation",
  inherited: "Inherited",
};

function pathSegments(path) {
  return path.split(".").map((part) => {
    const m = part.match(/^([a-z_]+)(?:\[(\d+)\])?$/);
    return { key: m[1], index: m[2] === undefined ? null : Number(m[2]) };
  });
}

// The group and label of a value's field.
export function fieldLabel(path) {
  const segs = pathSegments(path);
  const first = segs[0];
  let group;
  let heading;
  let rest;
  if (HEAD.has(first.key)) {
    group = "head";
    heading = "";
    rest = segs;
  } else if (LISTS.has(first.key)) {
    group = `${first.key}[${first.index}]`;
    heading = `${GROUP_LABEL[first.key]} ${first.index + 1}`;
    rest = segs.slice(1);
  } else {
    group = first.key;
    heading = GROUP_LABEL[first.key] ?? first.key;
    rest = ["informants", "notes"].includes(first.key) ? segs : segs.slice(1);
  }
  // "address.address" and "parts[1].text" name one thing each.
  const words = [];
  rest.forEach((s, i) => {
    if (s.key === "text" && i > 0) return;
    if (s.key === "address" && i < rest.length - 1) return;
    const base = KEY_LABEL[s.key] ?? s.key.replaceAll("_", " ");
    words.push(s.index !== null && s.index > 0 ? `${base} ${s.index + 1}` : base);
  });
  const label = words.length
    ? words.map((w, i) => (i ? w.toLowerCase() : w)).join(", ")
    : first.key === "relation"
      ? "Kind"
      : "Value";
  const order = ORDER.indexOf(group.replace(/\[\d+\]$/, ""));
  return { group, heading, label: label.charAt(0).toUpperCase() + label.slice(1), order: order < 0 ? ORDER.length : order, item: first.index ?? 0 };
}

// The full name of a value, group and label in one ("Person 1, role 2").
export function valueName(path) {
  const { heading, label } = fieldLabel(path);
  return heading ? `${heading}, ${label.toLowerCase()}` : label;
}

// A field of the missing-value list ("imprints.year") in words ("Imprint, year").
export function missingLabel(field) {
  const [head, ...rest] = field.split(".");
  const f = fieldLabel(rest.length || head === "notes" ? `${head}[0]${rest.length ? `.${rest.join(".")}` : ""}` : head);
  if (!f.heading || head === "notes") return f.label;
  return `${f.heading.replace(/ \d+$/, "")}, ${f.label.toLowerCase()}`;
}

// A derived value in words: types and kinds without underscores.
export function valueText(row) {
  // A flag reads as what it states ("year in brackets"), never as a bare "yes".
  if (typeof row.value === "boolean") return row.value ? KEY_LABEL[leaf(row.field)].toLowerCase() : `not ${KEY_LABEL[leaf(row.field)].toLowerCase()}`;
  if (/(?:^|\.)types\[\d+\]$/.test(row.field)) return TYPE_LABEL[row.value] ?? String(row.value);
  return String(row.value).replaceAll("_", " ");
}

// Rows in reading order, grouped: [{group, heading, rows}].
export function grouped(all) {
  const groups = new Map();
  for (const row of all) {
    const f = fieldLabel(row.field);
    if (!groups.has(f.group)) groups.set(f.group, { group: f.group, heading: f.heading, order: f.order, item: f.item, rows: [] });
    groups.get(f.group).rows.push({ ...row, label: f.label });
  }
  const head = groups.get("head");
  if (head) {
    const rank = (row) => HEAD_ORDER.indexOf(row.field.split(/[.[]/)[0]);
    head.rows.sort((a, b) => rank(a) - rank(b) || a.index - b.index);
  }
  return [...groups.values()].sort((a, b) => a.order - b.order || a.item - b.item);
}

// Segments that refine a value printed beside them: shown smaller, decided on their own.
const SUB_FIELD = /^(?:extent\.parts\[\d+\]\.text|references\[\d+\]\.kind)$/;

// What a card shows of its values, every value exactly once: the title and
// subtitle in its head, the types beside its address, every other value as a
// token on one line per group, items of a list group in their order.
export function cardLines(all) {
  const out = { title: [], subtitle: [], types: [], lines: [] };
  const byKey = new Map();
  for (const g of grouped(all)) {
    for (const row of g.rows) {
      if (row.field === "title") out.title.push(row);
      else if (row.field === "subtitle") out.subtitle.push(row);
      else if (/^types\[\d+\]$/.test(row.field)) out.types.push(row);
      else {
        const head = g.group === "head";
        const key = head ? row.field.replace(/\[\d+\]$/, "") : g.group.replace(/\[\d+\]$/, "");
        if (!byKey.has(key)) {
          const line = { key, label: head ? row.label.replace(/ \d+$/, "") : LINE_LABEL[key] ?? g.heading, items: [] };
          byKey.set(key, line);
          out.lines.push(line);
        }
        byKey.get(key).items.push({ row, item: g.group, sub: SUB_FIELD.test(row.field) });
      }
    }
  }
  return out;
}

// Every row a card shows, by index, from its lines.
export function shownIndices(lines) {
  const out = [];
  for (const r of [...lines.types, ...lines.title, ...lines.subtitle]) out.push(r.index);
  for (const line of lines.lines) for (const item of line.items) out.push(item.row.index);
  return out;
}

// Segments of a text with the spans of the given rows marked.
export function segments(text, marks) {
  const cuts = new Set([0, text.length]);
  for (const m of marks) {
    cuts.add(Math.max(0, Math.min(text.length, m.start)));
    cuts.add(Math.max(0, Math.min(text.length, m.end)));
  }
  const points = [...cuts].sort((a, b) => a - b);
  const out = [];
  for (let i = 0; i < points.length - 1; i++) {
    const [a, b] = [points[i], points[i + 1]];
    const covering = marks.filter((m) => m.start <= a && b <= m.end);
    out.push({ text: text.slice(a, b), marks: covering.map((m) => m.index) });
  }
  return out;
}

// The wiki concordance (_viewer_data.py) projected onto one print object:
// the p07 claims about the object or its record, all proposed, and the p08
// field conflict. The page names them candidates; nothing here is a match.
// Status by route: a field conflict, a text alignment, a field match, a
// title and year block, or no candidate.
export function wikiState(concordance, objectId, entryId) {
  const links = concordance?.links ?? {};
  const own = links[objectId] ?? {};
  const rec = links[entryId] ?? {};
  const pick = (key) => own[key] ?? rec[key] ?? [];
  const state = {
    align: pick("align"),
    same: pick("same"),
    cand: pick("cand"),
    diff: own.diff ?? rec.diff ?? null,
    totals: own.totals ?? rec.totals ?? {},
  };
  state.status = state.diff
    ? "conflict"
    : state.align.length
      ? "text"
      : state.same.length
        ? "fields"
        : state.cand.length
          ? "title-year"
          : "none";
  return state;
}

// One sign per state: [icon, short label, long label].
export const WIKI_STATUS = {
  conflict: ["alert", "Field conflict", "A proposed wiki publication whose fields differ from the print"],
  text: ["text", "Text candidate", "A wiki page proposed by text alignment"],
  fields: ["fields", "Field candidate", "A wiki publication proposed by title, year and a second field"],
  "title-year": ["titleYear", "Title-year candidate", "A wiki page proposed by title and year only"],
  none: ["pdf", "No candidate", "The concordance proposes no wiki page"],
  "wiki-only": ["wiki", "Wiki only", "A wiki page that no print candidate names"],
};
export const WIKI_STATUS_ORDER = ["conflict", "text", "fields", "title-year", "none", "wiki-only"];
// The source lanes: print without a candidate, print with one, wiki without one.
export const LANE_OF = { none: "print", "wiki-only": "wiki" };
export const laneOf = (status) => LANE_OF[status] ?? "shared";

// Route and method names the drawer prints; a candidate is never called a match.
export const ROUTE_LABEL = {
  alignment: "text alignment",
  "field-match": "field agreement",
  "title-year": "title and year",
};
export const METHOD_LABEL = {
  "title-year-field": "title, year and a second field",
  "subtitle-year-field": "title, subtitle, year and a second field",
  "short-title-year-field": "short title, year and a second field",
  "structured-pub-field": "a structured publication",
  "shingle-alignment": "shared runs of five words",
  "title-year": "title and year",
};
// The keys of the concordance projection by route.
const KEY_ROUTE = { align: "alignment", same: "field-match", cand: "title-year" };

const FIELD_LABEL = { place: "the place", publisher: "the publisher", translator: "the translator", extent: "the extent" };
// Identity needs no words; the two containment predicates of p07 do.
const RELATION_LABEL = { containedIn: "listed as an item of it", contains: "naming it as the host of the item" };

// How the concordance proposes one candidate, in words.
export function candidateRoute(c) {
  const route = ROUTE_LABEL[c.route] ?? "an unnamed route";
  if (c.route === "alignment") return `${route}, score ${Number(c.score ?? 0).toFixed(2)}`;
  const second = c.secondField?.length ? `, agreeing on ${c.secondField.map((f) => FIELD_LABEL[f] ?? f).join(" and ")}` : "";
  const relation = RELATION_LABEL[c.relation] ? `, ${RELATION_LABEL[c.relation]}` : "";
  const method = METHOD_LABEL[c.method] ?? "an unnamed method";
  // A method that only repeats its route is said once.
  return `${route}${method === route ? "" : `, by ${method}`}${relation}${second}`;
}

// The note under a route whose claims the projection cut short.
export function claimsShown(key, shown, total) {
  return `${shown.toLocaleString("en-US")} of ${total.toLocaleString("en-US")} claims by ${ROUTE_LABEL[KEY_ROUTE[key]] ?? "another route"} shown.`;
}

// The candidates of a state in route order, one per wiki target, with the
// claims that propose it.
export function candidates(state) {
  const out = [];
  const seen = new Map();
  for (const [key, list] of [["align", state.align], ["same", state.same], ["cand", state.cand]]) {
    for (const c of list) {
      const target = c.target ?? `klawiter:entry/${c.page}`;
      const id = `${key}|${target}`;
      if (seen.has(id)) {
        seen.get(id).claims.push(c.claim);
        continue;
      }
      // The agreeing words are folded tokens of both sides, not one value per field (p07).
      const item = { key, target, page: c.page, route: c.route, method: c.method, score: c.score, relation: c.relation ?? "samePublicationAs", secondField: c.secondField ?? [], agreeing: c.secondFieldValues ?? [], stale: Boolean(c.stale), state: c.state ?? "proposed", claims: [c.claim].filter(Boolean) };
      seen.set(id, item);
      out.push(item);
    }
  }
  return out;
}

export function naturalAddressKey(addr) {
  if (!addr) return [1, "", 999999];
  const m = addr.match(/^([A-Za-z0-9]+)\s+(\d+)/);
  if (m) return [0, m[1], Number(m[2])];
  return [0, addr, 0];
}

// Orders of a list of index entries; "book" keeps the printed order.
export function sortRecords(list, sortBy, done) {
  if (!sortBy || sortBy === "book") return list;
  const copy = [...list];
  const rank = Object.fromEntries(WIKI_STATUS_ORDER.map((s, i) => [s, i]));
  const compare = {
    title: (a, b) => (a.title || a.snippet || "").localeCompare(b.title || b.snippet || "", "de"),
    "year-asc": (a, b) => (a.year || 9999) - (b.year || 9999),
    "year-desc": (a, b) => (b.year || 0) - (a.year || 0),
    address: (a, b) => a.addrKey[0] - b.addrKey[0] || a.addrKey[1].localeCompare(b.addrKey[1]) || a.addrKey[2] - b.addrKey[2],
    wiki: (a, b) => rank[a.wiki.status] - rank[b.wiki.status],
    review: (a, b) => (a.review ? (done.has(a.id) ? 1 : 0) : 2) - (b.review ? (done.has(b.id) ? 1 : 0) : 2),
  }[sortBy];
  return compare ? copy.sort(compare) : list;
}

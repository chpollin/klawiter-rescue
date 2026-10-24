// Pure functions of the print viewer, shared by the page (viewer.js) and the
// coverage check (check_render.mjs): they turn a JSON-LD chunk of p12 into
// the rows and provenance chains the page shows, so the check proves that
// every value of every object has a row and a complete chain.

export const KP = "kp:";

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

// Review decisions (pipeline/print_volumes/_review.py). The functions below
// mirror its effective() and check(), so that the page shows the state p13
// will count.
export const REVIEW_STATE = { confirm: "confirmed", correct: "corrected", unresolved: "contested" };

export function decisionKey(d) {
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
    if (d.object !== object.id) continue;
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

// Every logged decision on one value, oldest first: its review history.
export function history(decisions, objectId, path) {
  return decisions.filter((d) => d.object === objectId && d.target && d.target.path === path);
}

// Readable names. A value's field is a path of the schema
// ("persons[0].roles[1]"); the page shows it in a group ("Person 1") with a
// label ("Role 2"), so that no code path reaches the reader.
export const VOLUME_LABEL = { I: "Main volume", A1: "Addendum I", A2: "Addendum II" };
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

// A derived value in words: types and kinds without underscores.
export function valueText(row) {
  if (typeof row.value === "boolean") return row.value ? "yes" : "no";
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

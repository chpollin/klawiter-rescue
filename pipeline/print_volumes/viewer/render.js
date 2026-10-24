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
function targetsOf(node, field) {
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

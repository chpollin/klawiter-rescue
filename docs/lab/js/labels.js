/**
 * Pure label rules of the lab views: no DOM, so pipeline/lab/test_lab_js.mjs
 * runs them with node. Producer labels come from the prepared data; these
 * functions only arrange them into the visible state line.
 */

export const ORIGIN = { regex: 'rule', llm: 'LLM gap fill', editor: 'editor' };

/** Origin word of a value, or null for a gap. */
export function originLabel(origin) {
  return ORIGIN[origin] || null;
}

/**
 * The visible state line of a place link (S2.3): object, state word, warning,
 * short producer and the scope sentence, as plain text parts. `scope` names
 * what the decision is not about, "this publication" or "this record".
 */
export function placeStateParts(pd, scope = 'this publication') {
  if (!pd || !pd.decision) return null;
  const object = pd.qid ? `Wikidata link ${pd.qid}` : 'Wikidata link';
  const scopeText = `for the name '${pd.place}', not for ${scope}`;
  if (pd.state === 'contested') {
    return { object, state: 'contested', warning: null, producer: pd.producerShort, scope: scopeText };
  }
  if (pd.state === null) {
    return { object, state: 'no link', warning: null, producer: pd.producer, scope: scopeText };
  }
  return { object, state: pd.state, warning: pd.warning || null, producer: pd.producerShort, scope: scopeText };
}

/** One-line text form of the place state, for exports and history. */
export function placeStateText(pd, scope) {
  const p = placeStateParts(pd, scope);
  if (!p) return pd ? `${pd.place}: no Wikidata decision recorded, no link` : null;
  const warning = p.warning ? `, warning: ${p.warning}` : '';
  return `${p.object}: ${p.state}${warning}, ${p.producer}, ${p.scope}`;
}

/** Edition assignment of a publication: state, short producer and date. */
export function editionStateText(ea) {
  const date = ea.date ? ` (${ea.date})` : '';
  return `${ea.state}, ${ea.producerShort}${date}`;
}

/**
 * The three print-pane cases of S6.1. Without the local index the page was
 * not compared; with the index and no matches it was compared without a
 * match; otherwise its matches are listed.
 */
export function printPaneState(indexLoaded, pageFile) {
  if (!indexLoaded) {
    return { kind: 'not-compared', sentence: 'Not compared with the print volumes. The published lab shows wiki data only.' };
  }
  if (!pageFile || !Array.isArray(pageFile.print) || !pageFile.print.length) {
    return { kind: 'no-match', sentence: 'Compared locally, no match found.' };
  }
  return { kind: 'matches', sentence: null };
}

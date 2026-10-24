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

const cap = text => `${text[0].toUpperCase()}${text.slice(1)}`;

function occurrenceStep(occ, ownWord, years) {
  if (!occ) return null;
  if (occ.noExactOccurrence) return 'No exact occurrence in the source text; the value may be normalised.';
  const parts = occ.parts.map(p => {
    if (p.noExactOccurrence) return `"${p.part}": no exact occurrence`;
    const own = p.occurrences.filter(o => o.own).length;
    const other = p.occurrences.filter(o => !o.own && o.publicationId).map(o => years.get(o.publicationId) ?? 'undated');
    const outside = p.occurrences.filter(o => !o.publicationId).length;
    const bits = [
      own ? `${own} in ${ownWord}` : `none in ${ownWord}`,
      other.length ? `${other.length} in the passage of ${[...new Set(other)].join(', ')}` : null,
      outside ? `${outside} outside the publication passages` : null,
    ].filter(Boolean);
    return `${occ.parts.length > 1 ? `"${p.part}": ` : ''}${bits.join(', ')}`;
  });
  return `Exact occurrences: ${parts.join('; ')}.`;
}

/**
 * The provenance chain of one value (S2.6): an ordered list of the steps the
 * lab data hold, each with its producer, ending with who checked the value.
 * A step the data do not hold is named as missing.
 *
 * `input`: { kind: 'publication' | 'record', label, field (the value's data),
 * page, pub (publication of the value, for kind 'publication'), pd (the
 * place decision of a place value), pubFieldKey (record values: the matching
 * publication field), print: { kind: 'not-compared' | 'no-candidate' | 'compared',
 * value (agreement row), entries (its print entries, already in reader words) },
 * meta }.
 */
export function provenanceSteps(input) {
  const { kind, label, field, page, pub, pd, print, meta } = input;
  const years = new Map(page.publications.map(p => [p.id, p.year]));
  const steps = [];
  const restored = page.source.restoredRevision;
  steps.push({
    step: 'Source',
    text: `Wiki page ${page.pageId}, text ${page.source.textId}; ${meta.texts.source}.${restored ? ` ${cap(meta.texts.restored)}.` : ''}`,
  });

  const own = kind === 'publication' ? `the passage of the ${pub.year ?? 'undated'} publication` : 'the page text';
  let extraction;
  if (field.origin === 'regex') {
    extraction = kind === 'publication'
      ? `Extraction rule of the publication layer, from ${own}.`
      : 'Extraction rule of the page-level record.';
  } else if (field.origin === 'llm') {
    const llm = meta.llm || {};
    extraction = `LLM gap fill: the extraction rules left this field empty and the language model ${llm.model || '(model not recorded)'} filled it; answers frozen on ${(llm.frozenAt || 'no date recorded').slice(0, 10)}; ${meta.llmNotStored}.`;
  } else if (field.origin === 'editor') {
    extraction = 'Entered by an editor in the local curation tool.';
  } else {
    extraction = `${cap(meta.texts.noValue)}.`;
  }
  steps.push({ step: 'Extraction', text: extraction });
  if (kind === 'record' && field.origin === 'llm' && field.value !== null) {
    const same = page.publications.filter(p => (p.fields[input.pubFieldKey] ? [].concat(p.fields[input.pubFieldKey]) : [])
      .some(v => v && v.value === field.value && v.origin === 'regex'));
    if (same.length) {
      steps.push({ step: 'Extraction', text: `The publication layer reads the same value by rule in the passage of the ${same.map(p => p.year ?? 'undated').join(' and ')} ${same.length > 1 ? 'publications' : 'publication'}.` });
    }
  }

  const checks = [];
  const occText = occurrenceStep(field.occurrences, kind === 'publication' ? 'its own passage' : 'the passage of the year-supplying publication', years);
  if (occText) checks.push(`${occText} An exact occurrence shows that the value exists in the source, not that it is the relevant value or complete. Producer: lab rule.`);
  if (kind === 'record' && field.boundary) {
    const fired = field.boundary.parts.filter(p => p.result !== 'pass');
    checks.push(fired.length
      ? `Boundary check: ${fired.map(p => p.result === 'fires'
        ? `"${p.part}" occurs only in the passage of the ${p.heldBy.map(h => h.year ?? 'undated').join(' and ')} publication`
        : `"${p.part}" occurs only outside the publication passages`).join('; ')}. Producer: lab rule.`
      : 'Boundary check: passed, the value occurs in the passage of the publication that supplies the record\'s year. Producer: lab rule.');
  }
  if (kind === 'record' && field.verification) {
    checks.push(field.verification === 'found'
      ? 'Verification stage of the pipeline: found this value in the raw text. Producer: pipeline rule.'
      : `Verification stage of the pipeline: ${meta.texts.verificationNotFound}. Producer: pipeline rule.`);
  }
  if (kind === 'record' && field.verificationCandidate) {
    checks.push(`Verification stage of the pipeline: reported "${field.verificationCandidate.value}" in the raw text while the record is empty; no rule and no person adopted it. Producer: pipeline rule.`);
  }
  if (kind === 'publication') checks.push('Verification stage of the pipeline: not run, it covers page-level values only.');
  for (const text of checks) steps.push({ step: 'Check', text });

  if (pd) {
    steps.push({ step: 'Decision', text: placeStateText(pd, kind === 'publication' ? 'this publication' : 'this record') + '.' });
  } else {
    steps.push({ step: 'Decision', text: 'No decision is recorded for this value.' });
  }

  if (!print || print.kind === 'not-compared') {
    steps.push({ step: 'Print volumes', text: 'Not compared with the print volumes; the published lab shows wiki data only.' });
  } else if (kind === 'record') {
    steps.push({ step: 'Print volumes', text: page.publications.length
      ? 'Print entries are matched per publication; the publication values carry the comparison.'
      : 'Print entries are matched per publication; this page has no publication breakdown, so no value is compared.' });
  } else if (print.kind === 'no-candidate' || !print.value) {
    steps.push({ step: 'Print volumes', text: 'Compared locally; no print entry is matched to this publication, so the value rests on the wiki alone.' });
  } else if (print.value.foundIn.length) {
    steps.push({ step: 'Print volumes', text: `Also in print: ${print.entries.join('; ')}. A proposed match, not reviewed. The value stands in that entry, which does not show that it describes this publication there, for example when it stands in a contents note. Wiki and print are states of one compiler's work, so this shows consistency, not independent support.` });
  } else {
    steps.push({ step: 'Print volumes', text: 'Not found in exactly this form in the matched print entries; the print may spell it differently or its extracted text may be faulty, so this is no disagreement.' });
  }

  const checkers = [];
  if (field.occurrences) checkers.push(`lab rules (occurrence${kind === 'record' && field.boundary ? ', boundary' : ''})`);
  if (kind === 'record' && (field.verification || field.verificationCandidate)) checkers.push('the pipeline\'s verification stage');
  if (pd && pd.decision) checkers.push(pd.person ? 'a person (Wikidata link of the place name)' : 'LLM agents (Wikidata link of the place name only)');
  if (print && print.kind === 'compared' && kind === 'publication' && print.value) checkers.push('a lab rule comparing with the matched print entry');
  const person = pd && pd.decision && pd.person;
  steps.push({
    step: 'Checked by',
    text: `${person ? 'A person decided the Wikidata link.' : 'No person has checked this value.'} ${checkers.length ? `Checks without a person: ${checkers.join(', ')}.` : 'No check applies.'}`,
  });
  return steps.map(s => ({ ...s, label }));
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

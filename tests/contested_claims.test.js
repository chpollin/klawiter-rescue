'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const claim = {
  claimId: 'klawiter:claim/work-binding/4916-2016-b',
  claimStatus: 'contested',
  decisionStatus: 'open',
  subject: 'klawiter:edition/4916-2016-b',
  predicate: 'schema:exampleOfWork',
  source: {
    sourcePageId: 4916,
    selector: [6866, 7104],
    sliceSha256: 'f'.repeat(64),
  },
  interpretations: [
    {
      interpretationId: 'klawiter:interpretation/original',
      label: 'Original work',
      basis: 'Source-page grouping',
      proposedObject: 'klawiter:work/4916',
      status: 'contested',
    },
    {
      interpretationId: 'klawiter:interpretation/adaptation',
      label: 'Adaptation work',
      basis: 'Graphic-novel wording',
      proposedObject: 'klawiter:work-candidate/adaptation',
      status: 'contested',
    },
  ],
  reviewHistory: [
    {
      reviewId: 'klawiter:review/a',
      reviewer: 'klawiter:agent/reviewer-a',
      outcome: 'escalate',
      basis: null,
    },
  ],
};

function load(file, context, exported) {
  vm.createContext(context);
  const source = fs.readFileSync(path.join(__dirname, '..', 'docs', 'js', file), 'utf8');
  vm.runInContext(`${source}\n;this.${exported} = ${exported};`, context);
  return context[exported];
}

{
  const entry = { sourcePageId: 4916, title: 'Schachnovelle / Volume', entryType: 'fiction' };
  const context = {
    App: { entryMap: new Map([[4916, entry]]) },
    Edit: { editionClaimsFor: () => [claim], contestedAuthorityClaims: [] },
    JsonldPlayground: {
      _toCompactJsonld: () => ({
        '@context': { schema: 'https://schema.org/', klawiter: 'https://example.test/' },
        '@id': 'klawiter:entry/4916',
      }),
    },
    downloadBlob: () => {},
    location: {},
    navigator: {},
    document: {},
    setTimeout,
  };
  const Export = load('export.js', context, 'Export');
  const payload = Export._jsonldPayload(entry);
  assert.strictEqual(payload['@graph'].length, 2);
  assert.strictEqual(payload['@graph'][1]['klawiter:claimStatus'], 'contested');
  assert.strictEqual(payload['@graph'][1]['klawiter:decisionStatus'], 'open');
  assert.ok(!('schema:exampleOfWork' in payload['@graph'][0]));
  assert.strictEqual(payload['@graph'][1]['klawiter:interpretation'].length, 2);
  assert.strictEqual(payload['@graph'][0]['klawiter:hasContestedClaim'][0]['@id'], claim.claimId);
}

{
  // The download keeps what the playground view leaves out: the published
  // place link, the review state with the field it covers, and the authority
  // claims the entry carries.
  const entry = { sourcePageId: 4819, title: 'Adam Lux', entryType: 'secondary-literature',
    location: 'Saint-Aignan', locationSameAs: 'http://www.wikidata.org/entity/Q1',
    review: { status: 'contested', reviewed_by: 'independent-verification-agent',
      fields: { location: 'unresolved' } } };
  const place = {
    claimId: 'klawiter:claim/reconciliation/location/d728', claimStatus: 'contested',
    decisionStatus: 'open', entityType: 'location',
    subject: { '@id': 'klawiter:location/Saint-Aignan', name: 'Saint-Aignan' },
    predicate: { '@id': 'schema:sameAs' },
    interpretations: [{ interpretationId: 'i1', label: 'Mont-Saint-Aignan', status: 'contested',
      proposedObject: { '@id': 'http://www.wikidata.org/entity/Q1055925' } }],
    sourceEvidence: [{ '@id': 'klawiter:sourceOccurrence/location/4819/34446/1' }],
    reviewHistory: [{ reviewId: 'r1', decisionId: 'location/Saint-Aignan/unresolved',
      action: 'unresolved', decidedBy: 'independent-verification-agent' }],
  };
  const context = {
    App: { entryMap: new Map([[4819, entry]]) },
    Edit: { editionClaimsFor: () => [], authorityClaimsFor: () => [place],
      locationReconciliation: () => ({ decision: { decisionId: 'location/Saint-Aignan/unresolved' } }) },
    JsonldPlayground: {
      CONTEXT: {}, FRONTEND_TO_JSONLD: {},
      _toCompactJsonld: () => ({ '@context': { klawiter: 'https://example.test/' },
        '@id': 'klawiter:entry/4819' }),
    },
    downloadBlob: () => {}, location: {}, navigator: {}, document: {}, setTimeout,
  };
  const Export = load('export.js', context, 'Export');
  const [record, node] = Export._jsonldPayload(entry)['@graph'];
  assert.strictEqual(record['klawiter:locationSameAs']['@id'], entry.locationSameAs);
  assert.strictEqual(record['klawiter:reviewStatus'], 'contested');
  const action = record['klawiter:hasReviewAction'][0];
  assert.strictEqual(action['klawiter:reviewOutcome'], 'unresolved');
  assert.strictEqual(action['schema:about']['@id'], 'klawiter:locationSameAs');
  assert.strictEqual(action['klawiter:decisionId'], 'location/Saint-Aignan/unresolved');
  assert.strictEqual(record['klawiter:hasContestedClaim'][0]['@id'], place.claimId);
  assert.strictEqual(node['klawiter:claimSubject']['schema:name'], 'Saint-Aignan');
  assert.strictEqual(node['klawiter:interpretation'][0]['klawiter:proposedObject']['@id'],
    'http://www.wikidata.org/entity/Q1055925');
}

{
  const context = {
    App: { state: { editMode: false } },
    Edit: { editionClaimsFor: () => [claim], authorityClaimsFor: () => [] },
    esc: value => String(value),
  };
  const Detail = load('detail.js', context, 'Detail');
  const html = Detail._contestedClaimsBlock({ sourcePageId: 4916 });
  assert.match(html, /Contested work identity/);
  assert.match(html, /decision open/);
  assert.match(html, /Original work/);
  assert.match(html, /Adaptation work/);
}

{
  const reconciliation = JSON.parse(fs.readFileSync(
    path.join(__dirname, '..', 'docs', 'data', 'reconciliation.json'),
    'utf8'
  ));
  // Page 4269 carries the open place claim on Tyresö in its imprint. Page 299
  // no longer serves: its line names Varna and Sofija for two different
  // contributions, which is no evidence for a compound place.
  const realClaim = reconciliation.contestedClaims.find(item =>
    item.subject && item.subject.name === 'Tyresö' && item.decisionStatus !== 'decided');
  assert.ok(realClaim, 'the open Tyresö place claim must exist');
  assert.ok(!reconciliation.contestedClaims.some(item =>
    (item.sourceEvidence || []).some(evidence => evidence.sourcePageId === 299)),
    'no claim takes evidence from a page that does not carry its subject');
  assert.ok(reconciliation.contestedClaims.every(item => item.decisionStatus === 'open'),
    'the contested list holds open claims only');
  assert.ok((reconciliation.decidedClaims || []).some(item =>
    item.subject.name === 'Sofija, Varna' && item.decisionStatus === 'decided'),
    'a decided compound claim keeps its record');

  const editContext = { App: { state: {} } };
  const Edit = load('edit.js', editContext, 'Edit');
  Edit.contestedAuthorityClaims = reconciliation.contestedClaims;
  // Page 4269 prints "Inko, Tyresö, Sweden" and holds Tyresö as its place.
  const entry = { sourcePageId: 4269, title: 'Ŝaknovelo', location: 'Tyresö' };
  const matchedClaims = Edit.authorityClaimsFor(entry);
  assert.ok(matchedClaims.some(item => item.claimId === realClaim.claimId));
  assert.ok(realClaim.claimId, 'projected claims carry a claimId');
  assert.strictEqual(Edit.openClaimOnValue(entry, 'Tyresö'), realClaim);

  // A claim reaches a page only through a value it names word for word or
  // through source text that literally carries its subject: pages 299 and
  // 3324 print neither place of "Sofija, Varna", and page 1725 shows Sofija
  // as a value of its own, which no compound subject contests.
  const compound = reconciliation.contestedClaims.filter(item =>
    item.subject && /,/.test(item.subject.name));
  for (const pid of [299, 3324]) {
    const page = { sourcePageId: pid, location: 'Wien',
      fullBibliographicEntry: 'Herbert Reichner Verlag, Wien' };
    assert.ok(!Edit.authorityClaimsFor(page).some(item => compound.includes(item)), String(pid));
  }
  const magelan = { sourcePageId: 1725, location: 'Sofija', publicationPlaces: ['Sofija', 'Varna'],
    fullBibliographicEntry: '[1939]: Slavcho Atanasov, Sofija' };
  assert.strictEqual(Edit.openClaimOnValue(magelan, 'Sofija'), null);

  const context = {
    App: { state: { editMode: false } },
    Edit: { editionClaimsFor: () => [], authorityClaimsFor: () => matchedClaims },
    esc: value => String(value),
  };
  const Detail = load('detail.js', context, 'Detail');
  const html = Detail._contestedAuthorityCell(entry);
  // The heading names what is contested; every open authority claim of the
  // holding is a place assignment.
  assert.match(html, /Contested place assignment/);
  assert.match(html, /Competing interpretations/);
  assert.match(html, /Source evidence/);
  assert.match(html, /Review history/);
  assert.match(html, /SHA-256/);
  assert.match(html, /schema:sameAs/);
}


{
  // A decided claim keeps its record: both readings with their status, the
  // decision in the history with its date, and what it left open.
  const decided = {
    ...claim,
    claimStatus: 'resolved',
    decisionStatus: 'decided',
    interpretations: [
      { ...claim.interpretations[0], status: 'rejected' },
      { ...claim.interpretations[1], status: 'accepted' },
    ],
    reviewHistory: [
      ...claim.reviewHistory,
      { reviewId: 'klawiter:review/decision', reviewer: 'klawiter:agent/main-instance',
        outcome: 'confirm', basis: 'Decided after delegation; revisable.', date: '2026-09-22' },
    ],
    reviewNotes: ['Page 4916 gives 120p., page 5110 gives 128p.'],
  };
  const context = {
    App: { state: { editMode: false } },
    Edit: { editionClaimsFor: () => [decided], authorityClaimsFor: () => [] },
    esc: value => String(value),
  };
  const Detail = load('detail.js', context, 'Detail');
  const html = Detail._contestedClaimsBlock({ sourcePageId: 4916 });
  assert.match(html, /Work identity decided/);
  assert.doesNotMatch(html, /decision open/);
  assert.match(html, /Original work \(rejected\)/);
  assert.match(html, /Adaptation work \(accepted\)/);
  assert.match(html, /confirm, 2026-09-22/);
  assert.match(html, /Open for review/);
  assert.match(html, /120p\./);
  assert.match(html, /aria-label="Decided claims"/);
}

console.log('all contested-claim checks passed');

{
  // A restored page names the revision it is published from in its download.
  const entry = {
    sourcePageId: 35,
    sourceRevision: {
      decisionId: 'source-revision/35/restore-human-revision',
      action: 'restore-human-revision',
      reason: 'The Redirect fixer revision replaced a content page with a redirect.',
      humanRevision: { revisionId: 33251, timestamp: '2017-09-25T20:31:36Z', actor: 'Klawiter', textId: 32391 },
      fixerRevisions: [{ revisionId: 33773, timestamp: '2017-10-08T20:25:29Z', comment: '' }],
    },
  };
  const context = {
    console,
    App: { entryMap: new Map([[35, entry]]) },
    Edit: { editionClaimsFor: () => [], contestedAuthorityClaims: [] },
    JsonldPlayground: {
      _toCompactJsonld: () => ({
        '@context': { schema: 'https://schema.org/', klawiter: 'https://example.test/' },
        '@id': 'klawiter:entry/35',
      }),
    },
    downloadBlob: () => {},
    location: {},
    navigator: {},
    document: {},
    setTimeout,
  };
  const Export = load('export.js', context, 'Export');
  const revision = Export._jsonldPayload(entry)['klawiter:sourceRevision'];
  assert.strictEqual(revision['schema:identifier'], '33251');
  assert.strictEqual(revision['klawiter:sourceTextId'], 32391);
  assert.strictEqual(revision['klawiter:decisionId'], 'source-revision/35/restore-human-revision');
}

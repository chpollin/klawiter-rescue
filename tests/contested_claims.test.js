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
  const realClaim = reconciliation.contestedClaims.find(item =>
    (item.sourceEvidence || []).some(evidence => evidence.sourcePageId === 299)
  );
  assert.ok(realClaim, 'real compound-location claim must exist');

  const editContext = { App: { state: {} } };
  const Edit = load('edit.js', editContext, 'Edit');
  Edit.contestedAuthorityClaims = reconciliation.contestedClaims;
  const entry = { sourcePageId: 299, title: 'Buried candlestick', location: 'Varna' };
  const matchedClaims = Edit.authorityClaimsFor(entry);
  assert.ok(matchedClaims.some(item => item.claimId === realClaim.claimId));
  assert.ok(realClaim.claimId, 'projected claims carry a claimId');

  const context = {
    App: { state: { editMode: false } },
    Edit: { editionClaimsFor: () => [], authorityClaimsFor: () => matchedClaims },
    esc: value => String(value),
  };
  const Detail = load('detail.js', context, 'Detail');
  const html = Detail._contestedAuthorityCell(entry);
  assert.match(html, /Contested authority assignment/);
  assert.match(html, /Competing interpretations/);
  assert.match(html, /Source evidence/);
  assert.match(html, /Review history/);
  assert.match(html, /SHA-256/);
  assert.match(html, /schema:sameAs/);
}

console.log('all contested-claim checks passed');

/**
 * Pins the ordering contract of the data-quality authority queue
 * (docs/js/curate.js): open subjects first, ordered by reach (occurrences,
 * descending), then pending, then decided, then published; name as the
 * deterministic tie-break. The fail-closed status derivation (publishable >
 * decision > pending > open) is part of the contract.
 */
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function loadCurate(overrides = {}) {
  const ctx = {
    document: { addEventListener() {}, getElementById() { return null; } },
    console,
    ...overrides,
  };
  vm.createContext(ctx);
  const source = fs.readFileSync(
    path.join(__dirname, '..', 'docs', 'js', 'curate.js'),
    'utf8'
  );
  return vm.runInContext(source + '\nCurate', ctx);
}

test('agent queue orders open-by-reach first and derives fail-closed status', () => {
  const Curate = loadCurate();
  const agents = {
    'person/A': { kind: 'person', name: 'A', occurrences: 5, candidates: [], decision: null, publishable: null },
    'person/B': { kind: 'person', name: 'B', occurrences: 40, candidates: [], decision: null, publishable: null },
    'publisher/C': { kind: 'publisher', name: 'C', occurrences: 90, candidates: [], decision: { action: 'confirm' }, publishable: { qid: 'Q1' } },
    'publisher/D': { kind: 'publisher', name: 'D', occurrences: 10, candidates: [], decision: { action: 'reject' }, publishable: null },
    'person/E': { kind: 'person', name: 'E', occurrences: 60, candidates: [], decision: null, publishable: null },
  };
  const pending = { 'agent:person/E': { action: 'confirm' } };

  const rows = Curate.agentQueue(agents, pending);
  // JSON comparison: the queue rows come from a vm realm, whose object
  // prototypes fail deepStrictEqual's cross-realm identity check.
  assert.strictEqual(
    JSON.stringify(rows.map(r => [r.name, r.status])),
    JSON.stringify([
      ['B', 'open'],       // open before everything, highest reach first
      ['A', 'open'],
      ['E', 'pending'],    // unsaved session decision
      ['D', 'decided'],    // frozen decision without published link
      ['C', 'published'],  // evidence-bearing confirm reached publication
    ])
  );
});

test('equal status and reach fall back to the name for a stable order', () => {
  const Curate = loadCurate();
  const agents = {
    'person/Z': { kind: 'person', name: 'Z', occurrences: 7, candidates: [], decision: null, publishable: null },
    'person/M': { kind: 'person', name: 'M', occurrences: 7, candidates: [], decision: null, publishable: null },
  };
  const rows = Curate.agentQueue(agents, {});
  assert.strictEqual(JSON.stringify(rows.map(r => r.name)), JSON.stringify(['M', 'Z']));
});

test('one queue key event is handled once after repeated render, decision and undo', () => {
  const persistentListeners = [];
  let currentList;
  const row = { dataset: { kind: 'person', name: 'A' }, classList: { contains() { return true; } } };
  const host = {
    set innerHTML(value) {
      currentList = { listeners: [], addEventListener(type, fn) { this.listeners.push(fn); } };
    },
    querySelector() { return currentList; },
    querySelectorAll() { return [row]; },
    addEventListener(type, fn) { persistentListeners.push(fn); },
  };
  const hint = {};
  const Edit = {
    agents: { 'person/A': { kind: 'person', name: 'A', occurrences: 2, candidates: [] } },
    pendingReconciliation: {},
  };
  const Curate = loadCurate({
    document: { addEventListener() {}, getElementById(id) { return id === 'agent-queue' ? host : hint; } },
    Edit, App: { state: { isLocal: true, editMode: true } },
  });
  Curate._agentRow = () => '<div class="agent-queue-row"></div>';
  let handled = 0;
  Curate._queueKey = () => { handled++; };
  for (const pending of [{}, { 'agent:person/A': { action: 'reject' } }, {}, {}]) {
    Edit.pendingReconciliation = pending;
    Curate._renderAgentQueue();
  }
  const event = { key: 'j', target: { closest() { return row; } } };
  for (const fn of [...currentList.listeners, ...persistentListeners]) fn(event);
  assert.strictEqual(handled, 1);
});

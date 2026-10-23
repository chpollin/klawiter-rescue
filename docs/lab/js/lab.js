/**
 * Shared helpers of the lab prototypes: data loading, DOM building, hash
 * state, search folding, data-state line, citation and download.
 *
 * The production constants (ENTRY_TYPE_LABELS, SITE_URL) come from
 * ../js/constants.js, loaded as a classic script before the modules, so the
 * lab reads the same type labels as the production app without copying them.
 */

const DATA = 'data/';
const cache = new Map();

/** Fetch a prepared JSON file once per session; reject with a readable cause. */
export function loadJSON(path) {
  if (!cache.has(path)) {
    const promise = fetch(DATA + path).then(resp => {
      if (!resp.ok) throw new Error(`${path} could not be loaded (HTTP ${resp.status})`);
      return resp.json();
    });
    promise.catch(() => cache.delete(path));
    cache.set(path, promise);
  }
  return cache.get(path);
}

/**
 * Build an element. Strings become text nodes, so data values are never
 * parsed as markup; null, undefined and false children are skipped.
 */
export function h(tag, attrs, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs || {})) {
    if (value === null || value === undefined || value === false) continue;
    if (key === 'class') node.className = value;
    else if (key === 'text') node.textContent = value;
    else if (key.startsWith('on')) node.addEventListener(key.slice(2), value);
    else if (key === 'dataset') Object.assign(node.dataset, value);
    else node.setAttribute(key, value === true ? '' : value);
  }
  append(node, children);
  return node;
}

function append(node, children) {
  for (const child of children) {
    if (child === null || child === undefined || child === false) continue;
    if (Array.isArray(child)) append(node, child);
    else node.append(child instanceof Node ? child : String(child));
  }
}

const FOLD_LETTERS = { 'ı': 'i', 'ł': 'l', 'ø': 'o', 'đ': 'd', 'æ': 'ae', 'œ': 'oe', 'þ': 'th' };

/** Mirror of fold_search in pipeline/lab/lab_rules.py; keep both in step. */
export function fold(text) {
  let s = String(text || '').normalize('NFKC').toLowerCase()
    .replace(/ß/g, 'ss')
    .replace(/[ıłøđæœþ]/g, c => FOLD_LETTERS[c]);
  s = s.normalize('NFD').replace(/[\p{M}\p{Lm}\p{Sk}'’‘`´]/gu, '');
  s = s.replace(/ae/g, 'a').replace(/oe/g, 'o').replace(/ue/g, 'u');
  return s.replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
}

/** Hash state as URLSearchParams ("#page=448&sel=r-translator"). */
export function readHash() {
  return new URLSearchParams(location.hash.slice(1));
}

export function writeHash(params, { replace = false } = {}) {
  const text = params.toString();
  const url = `${location.pathname}${location.search}${text ? '#' + text : ''}`;
  if (replace) history.replaceState(null, '', url);
  else history.pushState(null, '', url);
}

export function typeLabel(type) {
  return (typeof ENTRY_TYPE_LABELS !== 'undefined' && ENTRY_TYPE_LABELS[type]) || type;
}

export function dataStateLine(state) {
  return `Data: commit ${state.commit.slice(0, 7)}, inputs ${state.inputsSha256Short}, rules ${state.rulesVersion}`;
}

/** The footer data line, with the full commit and input hash as text a reader can copy. */
export function dataStateBlock(state) {
  return h('p', { class: 'data-state' },
    dataStateLine(state),
    h('span', { class: 'visually-hidden' },
      ` (full commit ${state.commit}, full input hash ${state.inputsSha256})`));
}

export function accessDate() {
  const d = new Date();
  const pad = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/**
 * Address of a lab view for a citation. A localhost or file:// run cites the
 * published location, as the production exports do, so the link resolves for
 * a reader.
 */
export function citeUrl(file, hash) {
  const local = location.protocol === 'file:' || ['localhost', '127.0.0.1'].includes(location.hostname);
  const base = local && typeof SITE_URL !== 'undefined'
    ? `${SITE_URL}lab/`
    : new URL('.', location.href).href;
  return `${base}${file}${hash ? '#' + hash : ''}`;
}

/** True while the lab runs from a local server or file; the lab is not published yet. */
export function isLocalRun() {
  return location.protocol === 'file:' || ['localhost', '127.0.0.1'].includes(location.hostname);
}

export function citation({ what, identifier, url, state }) {
  const planned = isLocalRun() ? ' (planned address, not yet published)' : '';
  return `${what}. Identifier: ${identifier}. Klawiter Bibliography Lab, data commit ${state.commit.slice(0, 7)}, inputs ${state.inputsSha256Short} (SHA-256 prefix), rules ${state.rulesVersion}. ${url}${planned}. Accessed ${accessDate()}.`;
}

export function download(name, text, type = 'text/plain') {
  const url = URL.createObjectURL(new Blob([text], { type: `${type};charset=utf-8` }));
  const link = h('a', { href: url, download: name });
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Copy text; a denied clipboard leaves the text selected in its field instead. */
export async function copyText(text, field, status) {
  try {
    await navigator.clipboard.writeText(text);
    status.textContent = 'Copied.';
  } catch {
    field.focus();
    field.select();
    status.textContent = 'The clipboard is not available; the text is selected for copying.';
  }
}

/** In a local run with print matches the footer says so instead of "wiki data only". */
async function initFooter() {
  const line = document.querySelector('.lab-footer p');
  if (!line) return;
  try {
    const resp = await fetch('local/print/index.json');
    if (!resp.ok) return;
  } catch {
    return;
  }
  line.firstChild.textContent = 'Lab prototypes on the rescued wiki data of the Klawiter bibliography. This local run also shows proposed matches from the unpublished print volumes; none is confirmed. The production application is ';
}

/** Header search: hands the query to the find prototype. */
export function initHeader() {
  initFooter();
  const form = document.querySelector('.lab-search');
  if (!form) return;
  form.addEventListener('submit', event => {
    event.preventDefault();
    const q = form.elements.q.value.trim();
    const params = new URLSearchParams();
    if (q) params.set('q', q);
    const target = `find.html${q ? '#' + params.toString() : ''}`;
    if (location.pathname.endsWith('/find.html')) {
      writeHash(params);
      window.dispatchEvent(new HashChangeEvent('hashchange'));
    } else {
      location.href = target;
    }
  });
}

/** A visible error in place of a view that could not load. */
export function errorBlock(error, retry) {
  return h('div', { class: 'load-error', role: 'alert' },
    h('p', {}, `The view could not be shown: ${error.message}`),
    retry ? h('button', { type: 'button', class: 'btn', onclick: retry }, 'Try again') : null);
}

export function yearsSpan(years) {
  const list = years.filter(y => Number.isFinite(y)).sort((a, b) => a - b);
  if (!list.length) return 'no year recorded';
  return list[0] === list[list.length - 1] ? String(list[0]) : `${list[0]} to ${list[list.length - 1]}`;
}

export function plural(n, one, many) {
  return `${n} ${n === 1 ? one : many}`;
}

/** replaceChildren that skips null, undefined and false and flattens arrays, as h() does. */
export function fill(node, ...children) {
  node.replaceChildren();
  append(node, children);
  return node;
}

/** append that skips null, undefined and false and flattens arrays, as h() does. */
export function add(node, ...children) {
  append(node, children);
  return node;
}

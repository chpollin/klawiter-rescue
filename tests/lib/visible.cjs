/**
 * What a reader can see of a rendered card, read from its HTML string.
 *
 * Shared by the record coverage test, the print adapter test and the print
 * render check (pipeline/print_volumes/viewer/check_render.mjs, through
 * createRequire), so the wiki and the print card are held to one predicate:
 * a value has a visible chain when a <button class="prov-badge"> with
 * aria-controls stands outside every hidden element, and the nearest
 * ancestor carrying data-provenance-for names its key. A wrapper further out
 * never lends its key to a button, and a hidden element stands for nothing.
 */
'use strict';

const VOID_TAGS = new Set(['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr']);
const TAG_RE = /<(\/?)([a-zA-Z][\w-]*)((?:"[^"]*"|'[^']*'|[^>"'])*)>/g;

/** Every element of the html with the offsets of its opening tag and its end. */
function elements(html) {
  const found = [];
  const stack = [];
  for (const m of html.matchAll(TAG_RE)) {
    const tag = m[2].toLowerCase();
    const after = m.index + m[0].length;
    if (m[1]) {
      const at = stack.map(el => el.tag).lastIndexOf(tag);
      if (at === -1) continue;
      for (const el of stack.splice(at)) el.end = after;
    } else {
      const el = { tag, attrs: m[3], start: m.index, open: after, end: html.length };
      found.push(el);
      if (!VOID_TAGS.has(tag) && !m[3].trimEnd().endsWith('/')) stack.push(el);
      else el.end = after;
    }
  }
  return found;
}

const hasAttr = (el, name) => new RegExp(`(^|\\s)${name}(\\s|=|$)`).test(el.attrs);

function attr(el, name) {
  const m = new RegExp(`(?:^|\\s)${name}="([^"]*)"`).exec(el.attrs);
  return m ? m[1] : null;
}

const hasClass = (el, name) => (attr(el, 'class') || '').split(/\s+/).includes(name);

/** The html with every element that carries the hidden attribute cut out, contents included. */
function stripHidden(html) {
  let out = '';
  let at = 0;
  for (const el of elements(html)) {
    if (!hasAttr(el, 'hidden') || el.start < at) continue;
    out += html.slice(at, el.start);
    at = el.end;
  }
  return out + html.slice(at);
}

function decode(s) {
  return s.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'")
    .replace(/&amp;/g, '&');
}

/** The text a reader sees: hidden elements gone, tags as spaces, entities decoded, space collapsed. */
function visibleText(html) {
  return decode(stripHidden(html).replace(/<[^>]*>/g, ' ')).replace(/\s+/g, ' ').trim();
}

/**
 * Every visible chain button: {key, controls, word}. `key` is the
 * data-provenance-for of the nearest ancestor that has one, or null.
 */
function chainButtons(html) {
  const shown = stripHidden(html);
  const els = elements(shown);
  const owners = els.filter(el => attr(el, 'data-provenance-for') !== null);
  const out = [];
  for (const el of els) {
    if (el.tag !== 'button' || !hasClass(el, 'prov-badge')) continue;
    const controls = attr(el, 'aria-controls');
    if (!controls) continue;
    let owner = null;
    for (const o of owners) {
      if (o.start < el.start && o.end >= el.end && (!owner || o.start > owner.start)) owner = o;
    }
    out.push({ key: owner ? attr(owner, 'data-provenance-for') : null, controls,
      word: visibleText(shown.slice(el.start, el.end)) });
  }
  return out;
}

/** Every id in the html, hidden elements included: a chain panel is an empty hidden slot until opened. */
function ids(html) {
  const out = new Set();
  for (const el of elements(html)) {
    const id = attr(el, 'id');
    if (id !== null) out.add(id);
  }
  return out;
}

/**
 * Elements that name a key with data-provenance-for but hold no visible chain
 * button of their own, the hidden markers this predicate refuses to count.
 */
function markersWithoutButton(html) {
  const shown = stripHidden(html);
  const els = elements(shown);
  const buttons = els.filter(el => el.tag === 'button' && hasClass(el, 'prov-badge') && attr(el, 'aria-controls'));
  const bare = [];
  const removed = elements(html).filter(el => attr(el, 'data-provenance-for') !== null).length
    - els.filter(el => attr(el, 'data-provenance-for') !== null).length;
  for (const el of els) {
    const key = attr(el, 'data-provenance-for');
    if (key === null) continue;
    if (!buttons.some(b => b.start > el.start && b.end <= el.end)) bare.push(key);
  }
  for (let i = 0; i < removed; i++) bare.push('(hidden)');
  return bare;
}

module.exports = { elements, stripHidden, visibleText, chainButtons, ids, markersWithoutButton, hasAttr, attr };

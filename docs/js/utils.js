/**
 * Shared utility functions.
 */

/** Escape HTML entities to prevent XSS */
function esc(s) {
  if (!s) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/** Alternation regex for the query words worth marking, or null. */
function _hlPattern(query) {
  const words = String(query == null ? '' : query).split(/\s+/).filter(w => w.length > 1);
  if (!words.length) return null;
  const alt = words.map(w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|');
  return new RegExp(alt, 'gi');
}

/**
 * Escape text and mark the query inside it.
 *
 * Marking must run on the raw text and escaping on the resulting segments.
 * Highlighting escaped text matched against the entity spellings instead of
 * the characters: a query with an apostrophe or an ampersand never matched,
 * and the query "amp" tore `&amp;` apart into invalid markup.
 */
function hlEsc(text, query) {
  const s = String(text == null ? '' : text);
  const re = query ? _hlPattern(query) : null;
  if (!re) return esc(s);
  let out = '';
  let last = 0;
  let m;
  while ((m = re.exec(s)) !== null) {
    out += esc(s.slice(last, m.index)) + '<mark>' + esc(m[0]) + '</mark>';
    last = m.index + m[0].length;
  }
  return out + esc(s.slice(last));
}

/** Escape BibTeX special characters */
function escapeBibtex(s) {
  if (!s) return '';
  return String(s)
    .replace(/\\/g, '\\textbackslash{}')
    .replace(/([{}&%#_^~])/g, '\\$1');
}

/** Count entries by a field value. Returns { value: count } sorted descending. */
function countByField(entries, field) {
  const counts = {};
  for (const e of entries) {
    const val = e[field];
    if (val) counts[val] = (counts[val] || 0) + 1;
  }
  return counts;
}

/** Top-N field values by frequency. Returns array of [value, count] pairs, descending. */
function topN(entries, field, n) {
  return Object.entries(countByField(entries, field))
    .sort((a, b) => b[1] - a[1])
    .slice(0, n);
}

/** Locale-consistent integer formatting, shared by every Explore surface. */
function fmt(n) {
  const v = Number(n);
  return Number.isFinite(v) ? v.toLocaleString('en') : String(n);
}

/** Normalize translator name: strip trailing location/edition info */
function normalizeTranslator(raw) {
  if (!raw) return '';
  let name = raw.trim();
  // Strip trailing location-like patterns: "Name. City" or "Name. xxii"
  name = name.replace(/\.\s+[A-Z][a-zà-ÿ]+(\s+[a-zà-ÿ]+)*\s*$/, '');
  name = name.replace(/\.\s+[xivlc]+\s*$/i, '');
  return name.trim();
}

/**
 * Final tokens that cannot end a personal name. A value ending on one of them
 * was cut off in the source, not spelled that way.
 */
const NAME_TRUNCATION_STOPWORDS = new Set([
  'and', 'und', 'by', 'de', 'del', 'della', 'di', 'da', 'du', 'van', 'von',
  'der', 'den', 'dem', 'des', 'of', 'with', 'aus', 'the', 'le', 'la', 'et',
]);

/**
 * Conservative truncation probe. Only unambiguous signals count, because a
 * false positive silently drops a real translator from the analysis: a
 * dangling hyphen or ellipsis, or a final token that cannot end a name.
 */
function isTruncatedName(name) {
  const s = String(name == null ? '' : name).trim();
  if (!s) return true;
  if (/[-‐-―]$/.test(s)) return true;
  if (/(\.\.\.|…)$/.test(s)) return true;
  const last = s.split(/\s+/).pop().replace(/[.,;:]+$/, '').toLowerCase();
  return NAME_TRUNCATION_STOPWORDS.has(last);
}

/**
 * Split a translator field into the individual people it names.
 * Klawiter records joint translations as "Eden and Cedar Paul" or "X & Y";
 * counting that string as one agent invents a translator who never existed.
 * Each part is normalized and recognizably truncated parts are dropped.
 */
function splitTranslators(raw) {
  if (!raw) return [];
  return String(raw)
    .split(/\s+(?:and|und)\s+|\s*&\s*/i)
    .map(part => normalizeTranslator(part))
    .filter(part => part.length >= 2 && !isTruncatedName(part));
}

/** Translator keys an entry contributes to (multi-name aware). */
function translatorKeys(entry) {
  return entry && entry.translator ? splitTranslators(entry.translator) : [];
}

/**
 * Whether the viewer asked for reduced motion. Evaluated once: the media
 * query result is read on every chart redraw and does not change mid-session
 * often enough to justify a live listener.
 */
const PREFERS_REDUCED_MOTION = typeof matchMedia === 'function'
  && matchMedia('(prefers-reduced-motion: reduce)').matches;

/** Transition duration honouring the reduced-motion preference. */
function motionMs(ms) {
  return PREFERS_REDUCED_MOTION ? 0 : ms;
}

// Basic Latin through Combining Diacritics, Latin Extended Additional,
// general punctuation, currency symbols, letterlike symbols. Together these
// cover the transliterations Klawiter used.
const LATIN_RANGES = [[0x0000, 0x036F], [0x1E00, 0x1EFF], [0x2000, 0x206F],
  [0x20A0, 0x20CF], [0x2100, 0x214F]];

/** True when the string uses no script beyond Latin and its companions. */
function isRomanized(text) {
  for (const ch of String(text == null ? '' : text)) {
    const c = ch.codePointAt(0);
    if (!LATIN_RANGES.some(([lo, hi]) => c >= lo && c <= hi)) return false;
  }
  return true;
}

/**
 * Language and direction attributes for a title element.
 *
 * `lang` comes from the record's languageCode. Almost every title in this
 * corpus is a romanization (Klawiter transliterated Arabic, Hebrew, Chinese
 * and others into Latin script), so a Latin-script title of a language
 * customarily written otherwise gets the `-Latn` subtag; without it a screen
 * reader would voice Latin letters with Arabic or Chinese phonetics.
 *
 * `dir="auto"` instead of a script probe: the only titles in the current data
 * that contain characters from an RTL block carry a single stray Arabic
 * diacritic inside otherwise Latin text, where dir="rtl" would reverse a
 * left-to-right line. dir="auto" resolves those to ltr by their first strong
 * character and still runs a genuinely Hebrew or Arabic title right-to-left.
 */
function titleAttrs(entry, text) {
  const code = entry && entry.languageCode;
  if (!code || !/^[a-z]{2,3}$/.test(code)) return ' dir="auto"';
  const tag = NON_LATIN_SCRIPT_LANGS.has(code) && isRomanized(text) ? `${code}-Latn` : code;
  return ` lang="${tag}" dir="auto"`;
}

/** Trigger a file download from in-memory content */
function downloadBlob(content, filename, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

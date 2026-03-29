/**
 * Shared utility functions.
 */

/** Escape HTML entities to prevent XSS */
function esc(s) {
  if (!s) return '';
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

/** Highlight search terms in text */
function hl(text, query) {
  if (!query || !text) return text;
  const words = query.split(/\s+/).filter(w => w.length > 1);
  if (!words.length) return text;
  const re = new RegExp(`(${words.map(w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`, 'gi');
  return text.replace(re, '<mark>$1</mark>');
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

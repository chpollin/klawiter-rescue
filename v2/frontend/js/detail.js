/**
 * Detail view for a single bibliography entry.
 * Shows all available fields + JSON-LD export.
 */
const Detail = {
  render(entry) {
    const container = document.getElementById('detail-content');
    if (!entry) {
      container.innerHTML = '<p class="text-gray-500">Eintrag nicht gefunden.</p>';
      return;
    }

    const fields = [];

    // Title
    fields.push(this.field('Titel', entry.title));
    if (entry.originalTitle) {
      fields.push(this.field('Originaltitel', entry.originalTitle));
    }

    // Type badge
    const typeLabel = ENTRY_TYPE_LABELS[entry.entryType] || entry.entryType;
    fields.push(this.field('Typ', `<span class="badge badge-${entry.entryType}">${esc(typeLabel)}</span>`));

    // Year + Period
    if (entry.year) {
      const period = PERIOD_LABELS[entry.timePeriod] || '';
      fields.push(this.field('Jahr', `${entry.year}${period ? ' — ' + period : ''}`));
    }

    // Publisher
    if (entry.publisher) fields.push(this.field('Verlag', entry.publisher));

    // Location
    if (entry.location) fields.push(this.field('Ort', entry.location));
    if (entry.allLocations && entry.allLocations.length > 1) {
      fields.push(this.field('Weitere Orte', entry.allLocations.join(', ')));
    }

    // Language
    if (entry.language) {
      fields.push(this.field('Sprache', `${entry.language}${entry.languageCode ? ' (' + entry.languageCode + ')' : ''}`));
    }

    // Page count
    if (entry.pageCount) fields.push(this.field('Seitenzahl', entry.pageCount));

    // Translator
    if (entry.translator) fields.push(this.field('Übersetzer/in', entry.translator));

    // Categories
    if (entry.categories && entry.categories.length) {
      const catLinks = entry.categories.map(c => {
        const main = c.split('/')[0].trim();
        return `<a href="#type=${encodeURIComponent(main.toLowerCase())}" class="text-blue-600 hover:underline text-sm">${esc(c)}</a>`;
      });
      fields.push(this.field('Kategorien', catLinks.join('<br>')));
    }

    // See also
    if (entry.seeAlso && entry.seeAlso.length) {
      const refs = entry.seeAlso.map(ref => this.makeLink(ref));
      fields.push(this.field('Siehe auch', refs.join(', ')));
    }

    // Reprints
    if (entry.reprints && entry.reprints.length) {
      const items = entry.reprints.map(r => `<li class="text-sm">${esc(r)}</li>`);
      fields.push(this.field('Nachdrucke', `<ul class="list-disc list-inside">${items.join('')}</ul>`));
    }

    // Translations
    if (entry.translations && entry.translations.length) {
      const items = entry.translations.map(t => `<li class="text-sm">${esc(t)}</li>`);
      fields.push(this.field('Übersetzungen', `<ul class="list-disc list-inside">${items.join('')}</ul>`));
    }

    // Content items (for collected works)
    if (entry.contentItems && entry.contentItems.length) {
      const items = entry.contentItems.map((c, i) => `<li class="text-sm">${esc(c)}</li>`);
      fields.push(this.field('Inhalt', `<ol class="list-decimal list-inside">${items.join('')}</ol>`));
    }

    // Full bibliographic entry
    if (entry.fullBibliographicEntry) {
      const formatted = esc(entry.fullBibliographicEntry)
        .replace(/\n/g, '<br>');
      fields.push(this.field('Vollständiger Eintrag', `<div class="text-sm font-mono bg-gray-50 p-3 rounded">${formatted}</div>`));
    }

    // JSON-LD export button
    const jsonldBtn = `<button onclick="Detail.exportJsonLd(${entry.sourcePageId})"
      class="text-sm text-blue-600 hover:text-blue-800 mt-2">JSON-LD herunterladen</button>`;

    // Provenance
    const provenance = `<div class="text-xs text-gray-400 mt-4">
      Page ID: ${entry.sourcePageId} | Text ID: ${entry.sourceTextId || '—'} | Blob: ${entry.sourceBlobId || '—'}
    </div>`;

    container.innerHTML = `
      <h2 class="text-xl font-semibold mb-4">${esc(entry.title || 'Ohne Titel')}</h2>
      ${fields.join('')}
      ${jsonldBtn}
      ${provenance}
    `;
  },

  field(label, value) {
    return `<div class="detail-field">
      <div class="detail-label">${esc(label)}</div>
      <div class="detail-value">${value}</div>
    </div>`;
  },

  makeLink(title) {
    // Try to find the entry by title for deep-linking
    const entry = App.data.entries.find(e => e.title === title);
    if (entry) {
      return `<a href="#entry=${entry.sourcePageId}" class="text-blue-600 hover:underline">${esc(title)}</a>`;
    }
    // Try redirect map
    const pid = App.data.redirects[title];
    if (pid) {
      return `<a href="#entry=${pid}" class="text-blue-600 hover:underline">${esc(title)}</a>`;
    }
    return esc(title);
  },

  exportJsonLd(pageId) {
    const entry = App.data.entries.find(e => e.sourcePageId === pageId);
    if (!entry) return;
    // Reconstruct JSON-LD with context
    const jsonld = {
      "@context": {
        "klawiter": "https://klawiter-rescue.github.io/vocab/"
      },
      "@type": entry['@type'] || `klawiter:${entry.entryType}Entry`,
      "@id": entry['@id'] || `klawiter:entry/${pageId}`,
    };
    for (const [k, v] of Object.entries(entry)) {
      if (!k.startsWith('@')) {
        jsonld[`klawiter:${k}`] = v;
      }
    }
    const blob = new Blob([JSON.stringify(jsonld, null, 2)], { type: 'application/ld+json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `klawiter-entry-${pageId}.jsonld`;
    a.click();
    URL.revokeObjectURL(url);
  },
};

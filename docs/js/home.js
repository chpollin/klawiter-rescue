/**
 * Home: search, the build of the data, and the compiler's sections as a table
 * across the sources of the bibliography (knowledge/frontend.md, Start page).
 *
 * The rows are the sections A to R of the printed bibliography, named as its
 * contents of 1991 name them (transcribed on wiki page 2101). The wiki column
 * places each entry type in the section it corresponds to; that mapping is the
 * project's, stated in SECTION_ROWS. A type that covers two adjacent sections
 * spans their rows (covers); essays cover C and H, which are not adjacent, so
 * the count stands at C and H points to it (seeAlso). The print columns
 * appear only on localhost when the print strand has written
 * lab/local/print-structure.json (pipeline/print_volumes/print_structure.py),
 * because the rights to the print volumes are unresolved.
 */
const SECTION_ROWS = [
  { code: 'A', name: 'Collected Works', range: 170, wiki: 'collected-works', covers: 'B' },
  { code: 'B', name: 'Selected Works', range: 15, coveredBy: 'A' },
  { code: 'C', name: 'Essays and Lectures in Book Form', range: 70, wiki: 'essay', alsoIn: 'H' },
  { code: 'D', name: 'Poetry', range: 227, wiki: 'poetry' },
  { code: 'E', name: 'Dramas', range: 58, wiki: 'drama' },
  { code: 'F', name: 'Fiction', range: 723, wiki: 'fiction' },
  { code: 'G', name: 'Historical and Biographical Studies', range: 1126, wiki: 'historical-study' },
  { code: 'H', name: 'Essays, Lectures and Reviews', range: 802, seeAlso: 'C' },
  { code: 'I', name: 'Translations by Zweig', range: 169, wiki: 'translation' },
  { code: 'J', name: 'Forewords and Afterwords by Zweig', range: 75, wiki: 'foreword' },
  { code: 'K', name: 'Correspondence', range: 767, wiki: 'correspondence' },
  { code: 'L', name: 'Secondary Literature', range: 1895, wiki: 'secondary-literature' },
  { code: 'M', name: "Reviews of Zweig's Works", range: 157 },
  { code: 'N', name: "Film Versions of Zweig's Works", range: 39, wiki: 'film', covers: 'O' },
  { code: 'O', name: "Zweig's Works Set to Music", range: 17, coveredBy: 'N' },
  { code: 'P', name: 'Zweig Symposia', range: 6, wiki: 'symposium' },
  { code: 'Q', name: 'Works Dedicated to Zweig', range: 25 },
  { code: 'R', name: 'Handwritten Dedications' },
];

// The address form is how the compiler cites an entry of each volume.
const PRINT_VOLUMES = [
  { key: 'I', name: 'Main volume', year: '1991', icon: 'book', what: 'printed 1991', address: 'F 61' },
  { key: 'A1', name: 'Addendum I', year: '1999', icon: 'book', what: 'printed 1999', address: 'FA1 3' },
  { key: 'A2', name: 'Addendum II', year: '2009', icon: 'file', what: 'unpublished working file, 2009', address: 'FA2 3' },
];

// Inline marks for the sources and the info control; no icon font.
const ICONS = {
  book: '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2 2.5h4.5A1.5 1.5 0 0 1 8 4v9.5A1.5 1.5 0 0 0 6.5 12H2zM14 2.5H9.5A1.5 1.5 0 0 0 8 4v9.5A1.5 1.5 0 0 1 9.5 12H14z" fill="none" stroke="currentColor" stroke-width="1.2"/></svg>',
  file: '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3.5 1.5h6l3 3v10h-9zM9.5 1.5v3h3M5.5 8h5M5.5 10.5h5" fill="none" stroke="currentColor" stroke-width="1.2"/></svg>',
  wiki: '<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="6.5" fill="none" stroke="currentColor" stroke-width="1.2"/><path d="M1.5 8h13M8 1.5c-2 2-2 11 0 13M8 1.5c2 2 2 11 0 13" fill="none" stroke="currentColor" stroke-width="1.2"/></svg>',
  info: '<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="6.5" fill="none" stroke="currentColor" stroke-width="1.2"/><path d="M8 7v4.5M8 4.6v.1" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>',
};

const homeCount = (n) => n.toLocaleString('en');

const Home = {
  print: null,
  printRequested: false,

  render(entries) {
    // The print structure loads once; the page is drawn again when it arrives.
    if (App.state.isLocal && !this.printRequested) {
      this.printRequested = true;
      this.loadPrint().then(() => {
        const view = document.getElementById('view-home');
        const typing = document.activeElement?.id === 'home-search-input';
        if (this.print && view && view.offsetParent !== null && !typing) this.render(entries);
      });
    }
    const container = document.getElementById('view-home');
    const counts = countByField(entries, 'entryType');
    const print = this.print;
    const mapped = new Set(SECTION_ROWS.map(r => r.wiki).filter(Boolean));
    const wikiOnly = Object.keys(counts).filter(t => !mapped.has(t) && counts[t]);

    container.innerHTML = `
      <div class="home-intro">
        <h1 class="home-title">Stefan Zweig Bibliography</h1>
        <div class="home-intro-row">
        <p class="home-text">Publications by and about Stefan Zweig, compiled by Randolph J. Klawiter.</p>
        <div class="home-search">
          <input type="search" id="home-search-input"
                 aria-label="Search every entry"
                 value="${esc(App.state.query || '')}"
                 placeholder="Search titles, persons, places and full text">
          <svg class="home-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
          </svg>
        </div>
        <p class="home-browse"><a href="#browse">Browse the wiki pages</a></p>
        </div>
      </div>
      <section class="home-data" aria-labelledby="home-data-heading">
        ${this.model(entries, counts, print)}
        ${this.table(counts, wikiOnly, print)}
      </section>
    `;

    const homeSearch = document.getElementById('home-search-input');
    homeSearch.addEventListener('input', (ev) => App.onSearchInput(ev.target.value));
    homeSearch.addEventListener('keydown', (ev) => {
      if (ev.key === 'Enter') {
        ev.preventDefault();
        App.commitSearch(ev.target.value);
      }
    });
  },

  // The local print structure; absent on the published site, so no request is
  // made there and the page keeps its wiki side only.
  async loadPrint() {
    if (!App.state.isLocal) return;
    try {
      const response = await fetch('lab/local/print-structure.json');
      if (response.ok) this.print = await response.json();
    } catch {
      this.print = null;
    }
  },

  // The levels below the sections, each counted in its own unit: the unit of
  // the source (print entry or wiki page), the publication, where the sources
  // meet, and the value. Sources and sections are the table below.
  model(entries, counts, print) {
    const info = this.info(print);
    const levels = ['Unit of the source', 'Publication', 'Value'];
    const row = (cells) => cells.map(c => `<td>${c}</td>`).join('');
    const pubs = App.data?._meta?.publicationCoverage;
    const wiki = row([
      `<b>${homeCount(entries.length)}</b> pages`,
      pubs ? `<b>${homeCount(pubs.publications)}</b> publications on ${homeCount(pubs.pages)} pages` : '',
      'fields with passage',
    ]);
    let printRow = '';
    if (print) {
      const t = Object.values(print.totals);
      const sum = (key) => t.reduce((n, v) => n + v[key], 0);
      printRow = `<tr><th scope="row">${ICONS.book}Print</th>${row([
        `<b>${homeCount(sum('numbered'))}</b> numbered, <b>${homeCount(sum('unnumbered'))}</b> unnumbered entries`,
        `<b>${homeCount(sum('publications'))}</b> publications, <b>${homeCount(sum('other'))}</b> other objects`,
        `<b>${homeCount(sum('values'))}</b> values with passage`,
      ])}</tr>`;
    }
    return `
      <table class="home-model">
        <thead><tr><td class="home-data-head">
          <h2 id="home-data-heading">How the data is built</h2>
          <details class="home-info">
            <summary aria-label="What this shows" title="What this shows">${ICONS.info}</summary>
            <div class="home-info-body">${info}</div>
          </details></td>${levels.map(l => `<th scope="col">${l}</th>`).join('')}</tr></thead>
        <tbody>${printRow}<tr><th scope="row">${ICONS.wiki}Wiki</th>${wiki}</tr></tbody>
      </table>`;
  },

  info(print) {
    return `<ul>
      <li>Each source has a unit of its own: in print an entry, numbered with an address such as F 61 (main volume), FA1 3 (Addendum I) or FA2 3 (Addendum II), or unnumbered, as most of Addendum II; in the wiki a page. Entries and pages do not correspond; the sources meet at the publication.</li>
      <li>Other objects are archival holdings, events, series, references and objects whose type was not read. Wiki pages outside the publication layer are not yet segmented into publications. Every value is bound to the passage it was read from.</li>
      <li>The wiki cites print addresses; a cited address is a reference, not proof that two records are the same publication.</li>
      <li>Rows of the table are the sections in the printed order, named as the contents of 1991 name them. R exists only in Addendum I.</li>
      <li>A print count is the number of entries of that section in the volume, numbered and unnumbered, as read from the file. A wiki count is the number of wiki pages of the entry type. The units differ and the sources overlap, so the counts do not add up.</li>
      <li>A dash means the section does not exist in that volume. A bracket means one wiki type covers two sections; essays belong to C and H and are counted at C. The wiki types are placed in the sections by this project, not by the compiler.</li>
      ${print ? '<li>The print side appears only on this computer, because the rights to the print volumes are unresolved.</li>' : ''}
    </ul>`;
  },

  // Labels left, counts right, one column per source; a count is a link and
  // its tooltip says what it counts.
  table(counts, wikiOnly, print) {
    const volumes = print ? PRINT_VOLUMES.filter(v => print.volumes[v.key]) : [];
    const source = (icon, name, year, address) => `<th scope="col" class="num">
      <span class="source">${ICONS[icon]}${esc(name)}</span>
      <span class="source-year">${esc(year)}</span>
      ${address ? `<span class="source-address" title="Address form">${esc(address)}</span>` : ''}</th>`;
    const head = (print ? volumes.map(v => source(v.icon, v.name, v.year, v.address)).join('') : source('book', 'Contents', '1991', 'F 1–723'))
      + source('wiki', 'Wiki', 'pages', '');
    const rows = SECTION_ROWS.map(r => `
      <tr>
        <th scope="row" title="${esc(r.range ? `Numbered ${r.code} 1 to ${r.range} in the contents of 1991` : 'Only in Addendum I')}"><span class="section-code">${r.code}</span>${esc(r.name)}</th>
        ${print ? volumes.map(v => this.printCell(print, v, r)).join('') : `<td class="num" data-label="1991">${r.range ? `${r.code} 1&ndash;${homeCount(r.range)}` : '<span class="absent" title="Not in the contents of 1991">&ndash;</span>'}</td>`}
        ${this.wikiCell(r, counts)}
      </tr>`).join('');
    const indexRow = volumes.length ? `
      <tr class="aside">
        <th scope="row">Indexes</th>
        ${volumes.map(v => this.indexCell(print, v)).join('')}
        <td></td>
      </tr>` : '';
    const onlyRow = wikiOnly.length ? `
      <tr class="aside">
        <th scope="row">Only in the wiki</th>
        <td class="only" colspan="${(print ? volumes.length : 1) + 1}">${wikiOnly.map(t => this.wikiLink(t, counts[t], true)).join('')}</td>
      </tr>` : '';
    return `
      <table class="home-sections">
        <caption class="visually-hidden">Sections of the bibliography by source</caption>
        <thead><tr><th scope="col">Section</th>${head}</tr></thead>
        <tbody>${rows}${indexRow}${onlyRow}</tbody>
      </table>`;
  },

  printCell(print, volume, row) {
    const part = print.volumes[volume.key][row.code];
    if (!part || !part.entries) return `<td class="num" data-label="${esc(volume.year)}"><span class="absent" title="No section ${row.code} in ${esc(volume.name)}">&ndash;</span></td>`;
    const href = `${print.viewer}#/?v=${volume.key}&part=${encodeURIComponent(row.code)}`;
    const what = `${homeCount(part.entries)} ${part.entries === 1 ? 'entry' : 'entries'} in section ${row.code} of ${volume.name}${part.highest ? `, numbered up to ${part.highest}` : ''}`;
    return `<td class="num" data-label="${esc(volume.year)}"><a href="${esc(href)}" title="${esc(what)}" aria-label="${esc(what)}">${homeCount(part.entries)}</a></td>`;
  },

  indexCell(print, volume) {
    const parts = Object.entries(print.volumes[volume.key]).filter(([, p]) => p.kind === 'index');
    if (!parts.length) return `<td class="num" data-label="${esc(volume.year)}"><span class="absent" title="No index in ${esc(volume.name)}">&ndash;</span></td>`;
    const total = parts.reduce((sum, [, p]) => sum + p.entries, 0);
    const what = `${homeCount(total)} index entries in ${parts.map(([name]) => name).join(', ')} of ${volume.name}`;
    return `<td class="num" data-label="${esc(volume.year)}"><a href="${esc(`${print.viewer}#/?v=${volume.key}&k=index`)}" title="${esc(what)}" aria-label="${esc(what)}">${homeCount(total)}</a></td>`;
  },

  wikiCell(row, counts) {
    if (row.coveredBy) return '';
    if (row.seeAlso) return `<td class="num" data-label="Wiki"><span class="see" title="Essays are counted at ${row.seeAlso}">&uarr; ${row.seeAlso}</span></td>`;
    if (!row.wiki || !counts[row.wiki]) return '<td class="num" data-label="Wiki"></td>';
    const span = row.covers ? ' rowspan="2"' : '';
    const cls = row.covers ? 'num spans' : 'num';
    return `<td class="${cls}"${span} data-label="Wiki">${this.wikiLink(row.wiki, counts[row.wiki], false, row)}</td>`;
  },

  wikiLink(type, count, named, row = null) {
    const label = ENTRY_TYPE_LABELS[type] || type;
    const scope = row && (row.covers || row.alsoIn) ? `, sections ${row.code} and ${row.covers || row.alsoIn}` : '';
    const what = `${homeCount(count)} wiki ${count === 1 ? 'page' : 'pages'} of type ${label}${scope}`;
    return `<button type="button" class="wiki-count" data-act="filter-type" data-type="${esc(type)}" title="${esc(what)}" aria-label="${esc(what)}">${named ? `<span class="wiki-name">${esc(label)}</span> ` : ''}${homeCount(count)}</button>`;
  },

  _dispatch(el) {
    if (el.dataset.act === 'filter-type') App.setFilter('type', el.dataset.type);
  },
};

// A wiki type is a real button, so one click listener is the whole keyboard
// path as well; the print cells are links into the local print viewer.
document.addEventListener('click', (ev) => {
  const el = ev.target.closest('#view-home [data-act]');
  if (!el) return;
  Home._dispatch(el);
});

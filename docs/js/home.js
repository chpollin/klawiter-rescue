/**
 * Home: search, the build of the data, and the compiler's sections as a table
 * across the sources of the bibliography (knowledge/frontend-architecture.md, Start page).
 *
 * The rows are the sections A to R of the printed bibliography, named as its
 * contents of 1991 name them (transcribed on wiki page 2101). The wiki column
 * places each entry type in the section it corresponds to; that mapping is the
 * project's, stated in SECTION_ROWS. A type that covers two adjacent sections
 * spans their rows (covers); essays cover C and H, which are not adjacent, so
 * the count stands at C and H points to it (seeAlso). The print columns
 * appear only on localhost when the print strand has written
 * local/print-structure.json (pipeline/print_volumes/print_structure.py),
 * because the rights to the print volumes are unresolved, and their counts
 * open Records only where Records can show print records (Records.probePrint):
 * the review server can, a plain static server over docs/ cannot.
 *
 * Every count opens Records in its own unit: a count of wiki pages the pages,
 * a count of print entries the entries rather than the objects they hold. A
 * count of values has no list of values to open and stands as text.
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

// The address form is how the compiler cites an entry of each volume; the
// phrase is how a count names the volume it opens.
const PRINT_VOLUMES = [
  // The file of the main volume is the compiler's working copy kept after 2001, not the print of 1991.
  { key: 'I', name: 'Main volume', year: '1991, later working copy', icon: 'book', phrase: 'the main volume', address: 'F 61' },
  { key: 'A1', name: 'Addendum I', year: '1999', icon: 'book', phrase: 'Addendum I', address: 'FA1 3' },
  { key: 'A2', name: 'Addendum II', year: 'working file to 2009', icon: 'file', phrase: 'the Addendum II working file', address: 'FA2 3' },
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
  printReady: false,   // Records can show print records on this server

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
        <p class="home-browse"><a href="#records">Browse the records</a></p>
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
  // made there and the page keeps its wiki side only. Records asks the same
  // file once for both pages, and whether it can show print records here.
  async loadPrint() {
    if (!App.state.isLocal || typeof Records === 'undefined') return;
    this.print = await Records.printStructure();
    this.printReady = !!this.print && await Records.probePrint();
  },

  /** The Records address of a print count, in its unit. */
  printHref(filter) {
    return typeof Records !== 'undefined' ? Records.printHref(filter) : '';
  },

  // The levels below the sections, each counted in its own unit: the unit of
  // the source (print entry or wiki page), the publication, where the sources
  // meet, and the value. Sources and sections are the table below.
  model(entries, counts, print) {
    const info = this.info(print);
    const levels = ['Unit of the source', 'Publication', 'Value'];
    const row = (cells) => cells.map((c, i) => `<td data-label="${esc(levels[i])}">${c}</td>`).join('');
    const pubs = App.data?._meta?.publicationCoverage;
    // A wiki value counts where its evidence names a located passage, as a
    // print value does; values from category markup, the page title or a gap
    // have none and are not counted here.
    const wikiVals = entries.reduce((sum, e) => sum + Object.values(e.fieldEvidence || {})
      .reduce((n, list) => n + (Array.isArray(list)
        ? list.filter(v => v && Number.isInteger(v.textStart)).length : 0), 0), 0);
    // The publications of the wiki stand on pages, and Records lists pages, so
    // the link is the count of those pages.
    const wiki = row([
      `<a href="#records"><b>${homeCount(entries.length)}</b> pages</a>`,
      pubs ? `<b>${homeCount(pubs.publications)}</b> publications on <a href="#records&amp;layer=publication"><b>${homeCount(pubs.pages)}</b> pages</a>` : '',
      `<b>${homeCount(wikiVals)}</b> values with passage`,
    ]);
    let printRow = '';
    if (print) {
      const t = Object.values(print.totals);
      const sum = (key) => t.reduce((n, v) => n + v[key], 0);
      // Without print records in Records the figures stand as text rather
      // than dead links.
      const open = (html, filter) => (this.printReady
        ? `<a href="${esc(this.printHref(filter))}">${html}</a>` : html);
      printRow = `<tr><th scope="row">${ICONS.book}Print</th>${row([
        open(`<b>${homeCount(sum('numbered'))}</b> numbered, <b>${homeCount(sum('unnumbered'))}</b> unnumbered entries`, { unit: 'entry' }),
        open(`<b>${homeCount(sum('publications'))}</b> publications, <b>${homeCount(sum('other'))}</b> other objects`, {}),
        `<b>${homeCount(sum('values'))}</b> values with passage`,
      ])}</tr>`;
    }
    return `
      <div class="home-data-head">
        <div class="home-data-title">
          <h2 id="home-data-heading">How the data is built</h2>
          <details class="home-info">
            <summary aria-label="What this shows" title="What this shows">${ICONS.info}</summary>
            <div class="home-info-body">${info}</div>
          </details>
        </div>
        <p class="home-data-lead">Print entries and wiki pages meet at the publication, and every value names the passage it was read from or why it has none.</p>
      </div>
      <table class="home-model">
        <thead><tr><th scope="col" class="home-model-source"><span class="visually-hidden">Source</span></th>${levels.map(l => `<th scope="col">${l}</th>`).join('')}</tr></thead>
        <tbody>${printRow}<tr><th scope="row">${ICONS.wiki}Wiki</th>${wiki}</tr></tbody>
      </table>`;
  },

  info(print) {
    return `<ul>
      <li>Each source has a unit of its own: in print an entry, numbered with an address such as F 61 (main volume), FA1 3 (Addendum I) or FA2 3 (Addendum II), or unnumbered, as most of Addendum II; in the wiki a page. Entries and pages do not correspond; the sources meet at the publication.</li>
      <li>Other objects are archival holdings, events, series, references and objects whose type was not read. Wiki pages outside the publication layer are not yet segmented into publications. A value read from the text is bound to its passage; values from wiki categories or the page title, and gaps, carry no passage and are not counted as values with passage.</li>
      <li>The wiki cites print addresses; a cited address is a reference, not proof that two records are the same publication.</li>
      <li>Rows of the table are the sections in the printed order, named as the contents of 1991 name them. R exists only in Addendum I.</li>
      <li>A print count is the number of entries of that section in the volume, numbered and unnumbered, as read from the file. A wiki count is the number of wiki pages of the entry type. The units differ and the sources overlap, so the counts do not add up.</li>
      <li>A dash means the section does not exist in that volume. The wiki types are placed in the sections by this project, not by the compiler.</li>
      ${print ? '<li>The print side appears only on this computer, because the rights to the print volumes are unresolved.</li>' : ''}
    </ul>`;
  },

  // Labels left, counts right, one column per source. The head names the unit
  // of a column and what its counts open, once for the column, and keeps the
  // address form in its tooltip; a count names its target in its label.
  table(counts, wikiOnly, print) {
    const volumes = print ? PRINT_VOLUMES.filter(v => print.volumes[v.key]) : [];
    const source = (icon, name, year, unit, tip) => `<th scope="col" class="num" title="${esc(tip)}">
      <span class="source">${ICONS[icon]}${esc(name)}</span>
      ${year ? `<span class="source-year">${esc(year)}</span>` : ''}
      <span class="source-unit">${esc(unit)}</span></th>`;
    const head = (print
      ? volumes.map(v => source(v.icon, v.name, v.year, this.printReady ? 'entries · open in Records' : 'entries',
        `Entries of ${v.phrase}, cited by addresses such as ${v.address}`)).join('')
      : source('book', 'Contents', '1991', 'numbers',
        'The number range of each section in the contents of 1991, such as F 1–723'))
      + source('wiki', 'Wiki', '', 'pages · open in Records',
        'Wiki pages of the entry type placed at the section, addressed by page ID such as page 448');
    const rows = SECTION_ROWS.map(r => `
      <tr>
        <th scope="row" title="${esc(r.range ? `Numbered ${r.code} 1 to ${r.range} in the contents of 1991` : 'Only in Addendum I')}"><span class="section-code">${r.code}</span>${esc(r.name)}</th>
        ${print ? volumes.map(v => this.printCell(print, v, r)).join('') : `<td class="num" data-label="Contents 1991">${r.range ? `${r.code} 1&ndash;${homeCount(r.range)}` : '<span class="absent" title="Not in the contents of 1991">&ndash;</span>'}</td>`}
        ${this.wikiCell(r, counts)}
      </tr>`).join('');
    const indexRow = volumes.length ? `
      <tr class="aside">
        <th scope="row">Indexes</th>
        ${volumes.map(v => this.indexCell(print, v)).join('')}
        <td class="num" data-label="Wiki"><span class="absent" title="No separate index pages in the wiki">&ndash;</span></td>
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
      </table>
      ${this.legend(volumes.length > 0 && this.printReady)}`;
  },

  // One line for the two marks of the table that no head explains. Where the
  // table stacks, the bracket gives way to a label and its item is hidden,
  // while the heads are hidden and the item on the targets takes their place.
  legend(printLinks) {
    const targets = printLinks ? 'print and wiki counts open their records' : 'wiki counts open their records';
    const items = [
      `<li class="legend-targets">${targets}</li>`,
      '<li class="legend-covers"><span class="legend-bracket" aria-hidden="true"></span>one wiki type covers two sections</li>',
    ];
    for (const r of SECTION_ROWS.filter(row => row.seeAlso)) {
      items.push(`<li><span class="legend-see">&uarr; ${r.seeAlso}</span> counted at section ${r.seeAlso}</li>`);
    }
    return `<ul class="home-legend" aria-label="Marks in the table">${items.join('')}</ul>`;
  },

  // A print count opens its records where Records shows print and is plain
  // text otherwise; its tooltip says what it counts in either case.
  printTarget(href, what, text, note = '') {
    if (!this.printReady) return `<span class="print-count" title="${esc(note ? `${what}, ${note}` : what)}">${text}</span>`;
    const label = `Open the ${what} in Records${note ? ` (${note})` : ''}`;
    return `<a class="print-count" href="${esc(href)}" title="${esc(label)}" aria-label="${esc(label)}">${text}</a>`;
  },

  printCell(print, volume, row) {
    const part = print.volumes[volume.key][row.code];
    if (!part || !part.entries) return `<td class="num" data-label="${esc(volume.name)}"><span class="absent" title="No section ${row.code} in ${esc(volume.phrase)}">&ndash;</span></td>`;
    const href = this.printHref({ volume: volume.key, part: row.code, unit: 'entry' });
    const what = `${homeCount(part.entries)} ${part.entries === 1 ? 'entry' : 'entries'} of section ${row.code} of ${volume.phrase}`;
    const note = part.highest ? `numbered up to ${part.highest}` : '';
    return `<td class="num" data-label="${esc(volume.name)}">${this.printTarget(href, what, homeCount(part.entries), note)}</td>`;
  },

  indexCell(print, volume) {
    const parts = Object.entries(print.volumes[volume.key]).filter(([, p]) => p.kind === 'index');
    if (!parts.length) return `<td class="num" data-label="${esc(volume.name)}"><span class="absent" title="No index in ${esc(volume.phrase)}">&ndash;</span></td>`;
    const total = parts.reduce((sum, [, p]) => sum + p.entries, 0);
    const what = `${homeCount(total)} index entries of ${volume.phrase} (${parts.map(([name]) => name).join(', ')})`;
    const href = this.printHref({ volume: volume.key, kind: 'index', unit: 'entry' });
    return `<td class="num" data-label="${esc(volume.name)}">${this.printTarget(href, what, homeCount(total))}</td>`;
  },

  wikiCell(row, counts) {
    if (row.coveredBy) return '';
    if (row.seeAlso) {
      const target = SECTION_ROWS.find(r => r.code === row.seeAlso);
      const type = target ? target.wiki : 'essay';
      const n = counts[type] || 0;
      const what = `Essays belong to sections ${row.seeAlso} and ${row.code} and are counted at ${row.seeAlso}. `
        + `Open the ${homeCount(n)} wiki ${n === 1 ? 'page' : 'pages'} of type ${ENTRY_TYPE_LABELS[type] || type} in Records`;
      return `<td class="num" data-label="Wiki"><button type="button" class="wiki-count see" data-act="filter-type" data-type="${esc(type)}" title="${esc(what)}" aria-label="${esc(what)}">&uarr; ${row.seeAlso}</button></td>`;
    }
    if (!row.wiki || !counts[row.wiki]) {
      return `<td class="num" data-label="Wiki"><span class="absent" title="No wiki entry type for section ${row.code}">&ndash;</span></td>`;
    }
    if (row.covers) {
      // The bracket drawn along both rows takes this cell's tooltip as its words.
      const label = ENTRY_TYPE_LABELS[row.wiki] || row.wiki;
      const tip = `One wiki type, ${label}, covers sections ${row.code} and ${row.covers}`;
      return `<td class="num spans" rowspan="2" title="${esc(tip)}" data-label="Wiki (${row.code} and ${row.covers})">${this.wikiLink(row.wiki, counts[row.wiki], false, row)}</td>`;
    }
    return `<td class="num" data-label="Wiki">${this.wikiLink(row.wiki, counts[row.wiki], false, row)}</td>`;
  },

  wikiLink(type, count, named, row = null) {
    const label = typeof App.typeLabel === 'function' ? App.typeLabel(type) : (ENTRY_TYPE_LABELS[type] || type);
    const other = row && (row.covers || row.alsoIn);
    const scope = row ? ` (${other ? `sections ${row.code} and ${other}` : `section ${row.code}`})` : '';
    const what = `Open the ${homeCount(count)} wiki ${count === 1 ? 'page' : 'pages'} of type ${label}${scope} in Records`;
    return `<button type="button" class="wiki-count" data-act="filter-type" data-type="${esc(type)}" title="${esc(what)}" aria-label="${esc(what)}">${named ? `<span class="wiki-name">${esc(label)}</span> ` : ''}${homeCount(count)}</button>`;
  },

  _dispatch(el) {
    if (el.dataset.act === 'filter-type') App.setFilter('type', el.dataset.type);
  },
};

// A wiki type is a real button, so one click listener is the whole keyboard
// path as well; the print cells are links into Records.
document.addEventListener('click', (ev) => {
  const el = ev.target.closest('#view-home [data-act]');
  if (!el) return;
  Home._dispatch(el);
});

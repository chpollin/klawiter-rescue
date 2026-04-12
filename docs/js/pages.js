/**
 * Static content pages — About, Methodology, Help, Data, Imprint.
 * Each method returns an HTML string rendered into #view-page.
 */
const Pages = {

  render(slug) {
    const container = document.getElementById('view-page');
    const renderer = this[slug];
    if (renderer) {
      container.innerHTML = renderer.call(this);
      window.scrollTo(0, 0);
    }
    document.title = this.titles[slug] || 'Klawiter Bibliography';
  },

  titles: {
    about: 'About — Klawiter Bibliography',
    methodology: 'Methodology — Klawiter Bibliography',
    help: 'Help — Klawiter Bibliography',
    data: 'Data Access — Klawiter Bibliography',
    jsonld: 'JSON-LD Playground — Klawiter Bibliography',
    imprint: 'Imprint — Klawiter Bibliography',
  },

  // ---------------------------------------------------------------------------
  // About
  // ---------------------------------------------------------------------------
  about() {
    return `<div class="page-content">
      <h1>About the Klawiter Bibliography</h1>

      <p>
        The Klawiter Bibliography is one of the most comprehensive reference works
        on Stefan Zweig (1881&ndash;1942). It documents over 6,200 publications by and about
        the Austrian author &mdash; spanning fiction, essays, poetry, drama, correspondence,
        secondary literature, translations, and collected editions in more than 40 languages.
      </p>

      <h2>The Compiler</h2>
      <p>
        The bibliography was compiled by Dr. Randolph J. Klawiter, Professor Emeritus
        of German at the University of Notre Dame (Indiana, USA). Over the course of
        several decades, Klawiter assembled a systematic record of Zweig&rsquo;s published
        works and the scholarly literature about them. The result is a reference work
        that covers Zweig&rsquo;s entire publishing history from the earliest editions
        to contemporary reprints and translations.
      </p>

      <h2>The Original Wiki</h2>
      <p>
        Klawiter&rsquo;s bibliography was made available online as a MediaWiki instance,
        allowing researchers to browse the entries by category and search across the
        full dataset. Over time, the wiki accumulated 6,725 pages, including 6,296
        bibliography entries, 1,545 redirect pages (cross-references and title
        variants), and 420 category descriptions.
      </p>
      <p>
        When the hosting infrastructure was discontinued, the wiki went offline.
        The underlying data &mdash; an SQL database dump and eight binary content files
        totalling 363&nbsp;MB &mdash; survived as the sole remaining record of the
        bibliography in digital form.
      </p>

      <h2>The Rescue Project</h2>
      <p>
        This digital edition is the result of a data rescue effort: the raw database
        files were parsed, cleaned, and transformed into structured
        <a href="#data">JSON-LD</a> using a custom extraction pipeline. The goal
        was to make the Klawiter Bibliography openly accessible again, in a format
        that is both human-readable and machine-processable.
      </p>
      <p>
        The pipeline extracts structured metadata (title, year, publisher, location,
        language, translator, page count) from the wiki markup of each entry, repairs
        character encoding errors, classifies entries into 16 types and 5 time periods,
        and produces a JSON-LD dataset with a vocabulary based on Schema.org, Dublin Core,
        and a domain-specific extension namespace.
      </p>
      <p>
        For a detailed description of the extraction process, see the
        <a href="#methodology">Methodology</a> page.
      </p>

      <h2>Stefan Zweig Digital</h2>
      <p>
        This project is connected to
        <a href="https://stefanzweig.digital/" target="_blank" rel="noopener">Stefan Zweig Digital</a>,
        a research initiative at the Stefan Zweig Centre Salzburg that provides
        digital access to Zweig&rsquo;s literary estate (Nachlass). The Klawiter
        Bibliography complements the SZD collection by documenting the publication
        history that the Nachlass materials produced.
      </p>
      <p>
        The visual design of this site follows the SZD design language to signal
        its affiliation with the broader Zweig research ecosystem.
      </p>
    </div>`;
  },

  // ---------------------------------------------------------------------------
  // Methodology
  // ---------------------------------------------------------------------------
  methodology() {
    return `<div class="page-content">
      <h1>Methodology</h1>

      <p>
        This page documents how the digital edition was produced from the raw
        database files. Transparency about the extraction process, its tools, and
        its limitations is essential for assessing the reliability of the data.
      </p>

      <h2>Source Data</h2>
      <p>
        The source material consists of a MediaWiki SQL database dump
        (<code>zweig_part_01.sql</code>, 33&nbsp;MB) and eight binary content files
        (<code>zt_00</code> to <code>zt_07</code>, 330&nbsp;MB combined). Together,
        they contain the full content of the original Klawiter wiki: 6,725 pages
        with 53,016 text revisions.
      </p>
      <p>
        The database stores content in a four-layer chain
        (page &rarr; revision &rarr; slot &rarr; content &rarr; text ID in BLOB file).
        The pipeline resolves this chain for each page and retrieves the latest
        revision of each entry.
      </p>

      <h2>Extraction Pipeline</h2>
      <p>
        The pipeline is implemented in Python and runs without external database
        software. It processes the raw files in seven steps:
      </p>
      <ol>
        <li>
          <strong>Extract</strong> &mdash;
          Parse SQL INSERT statements and binary BLOB files directly. Resolve the
          page&ndash;revision&ndash;slot&ndash;content chain to retrieve the latest
          text for each of the 6,296 main-namespace pages.
        </li>
        <li>
          <strong>Fix Encoding</strong> &mdash;
          Detect and repair Mojibake (character encoding errors caused by
          Latin-1/UTF-8 misinterpretation). This step corrected 61% of all entries
          and reduced the Mojibake rate to zero.
        </li>
        <li>
          <strong>Parse</strong> &mdash;
          Extract structured metadata from MediaWiki markup using regular expressions:
          title, year, publisher, location, language, translator, page count,
          categories, cross-references, reprints, and table-of-contents items.
        </li>
        <li>
          <strong>LLM Enrichment</strong> (optional) &mdash;
          Fill gaps in publisher, location, translator, and page count fields using
          a large language model (Gemini 3.1 Flash Lite). The model reads the
          bibliographic text and extracts metadata that the regex patterns missed.
          All LLM-generated values pass a Mojibake validation filter.
        </li>
        <li>
          <strong>Classify</strong> &mdash;
          Assign each entry one of 16 types (fiction, essay, poetry, drama, etc.)
          based on its MediaWiki categories, and one of 5 time periods based on
          the publication year.
        </li>
        <li>
          <strong>Convert to JSON-LD</strong> &mdash;
          Transform the tabular data into a JSON-LD document using a vocabulary
          that blends Schema.org, Dublin Core, and a domain-specific
          <code>klawiter:</code> namespace.
        </li>
        <li>
          <strong>Validate</strong> &mdash;
          Generate a quality report with field coverage statistics, distribution
          analyses, and a list of entries with potential issues.
        </li>
      </ol>

      <h2>LLM-Assisted Metadata Extraction</h2>
      <p>
        Step 4 of the pipeline uses a large language model to supplement the
        regex-based extraction. This step is optional; the pipeline produces valid
        output without it, but with lower field coverage.
      </p>
      <p>
        The LLM processes entries in batches, receiving the raw bibliographic text
        and returning structured JSON with publisher, location, translator, and
        page count fields. A validation layer rejects values that contain Mojibake
        characters or other encoding artifacts. The enrichment improved coverage as
        follows:
      </p>
      <table class="page-table">
        <thead>
          <tr><th>Field</th><th>Before (regex only)</th><th>After (regex + LLM)</th><th>Improvement</th></tr>
        </thead>
        <tbody>
          <tr><td>Publisher</td><td>34.5%</td><td>55.6%</td><td>+21.1 pp.</td></tr>
          <tr><td>Location</td><td>67.8%</td><td>87.5%</td><td>+19.7 pp.</td></tr>
          <tr><td>Translator</td><td>35.1%</td><td>41.9%</td><td>+6.8 pp.</td></tr>
          <tr><td>Page count</td><td>51.0%</td><td>54.1%</td><td>+3.1 pp.</td></tr>
        </tbody>
      </table>

      <h2>Quality Assurance</h2>
      <p>
        The pipeline is validated by a test suite of 315 automated tests covering
        encoding repair, regex patterns, wiki markup parsing, entry classification,
        and real-data extraction. Additionally, a round-trip verification script
        compares the final JSON-LD output against the original wiki content for
        every entry.
      </p>
      <p>
        An LLM-as-a-Judge evaluation uses a language model to assess extraction
        quality on a stratified sample of entries, identifying both false positives
        (incorrectly extracted values) and false negatives (missed information).
      </p>

      <h2>Known Limitations</h2>
      <p>
        The dataset has the following known coverage gaps. In many cases, the
        missing information is genuinely absent from the source text, not a
        failure of extraction.
      </p>
      <ul>
        <li>
          <strong>Publisher</strong> (55.6% coverage): Many entries in the original
          bibliography do not include publisher information, particularly shorter
          entries and journal articles.
        </li>
        <li>
          <strong>Translator</strong> (41.9% coverage): A large portion of entries
          are German-language originals or editions that do not name a translator.
        </li>
        <li>
          <strong>Location</strong> (87.5% coverage): Good coverage overall.
          Remaining gaps are mostly entries without publication location in the
          source text.
        </li>
        <li>
          <strong>Year</strong> (93.2% coverage): A small number of entries lack
          a publication year in the source data.
        </li>
        <li>
          One entry (page ID 2979, &ldquo;A unidade espiritual do mundo&rdquo;) could
          not be extracted because its text content is not present in any of the
          BLOB files.
        </li>
        <li>
          Approximately 20% of redirect entries (314 of 1,545) cannot be resolved
          because the target title does not exactly match an existing entry.
        </li>
      </ul>

      <h2>Data Model</h2>
      <p>
        Each bibliography entry is represented as a JSON-LD node with a type drawn
        from a controlled vocabulary of 16 entry types (fiction, essay, poetry, drama,
        correspondence, historical study, secondary literature, collected works,
        foreword, translation, film/opera, symposium, dramatic reading, newspaper
        article, other). The vocabulary is documented at
        <a href="vocab/index.html">the namespace resolution page</a>.
      </p>
      <p>
        For full details on the data format, fields, and download options, see the
        <a href="#data">Data Access</a> page.
      </p>
    </div>`;
  },

  // ---------------------------------------------------------------------------
  // Help
  // ---------------------------------------------------------------------------
  help() {
    return `<div class="page-content">
      <h1>How to Use This Site</h1>

      <p>
        This site provides access to the Klawiter Bibliography through search,
        filtering, and export functions. All data is loaded client-side; no
        server requests are needed after the initial page load.
      </p>

      <h2>Searching</h2>
      <p>
        Use the search field in the header or on the home page to search across
        all entry fields: titles, publishers, locations, languages, translators,
        and the full bibliographic text. Search results are ranked by relevance.
      </p>
      <p>
        The search uses a client-side full-text index (FlexSearch) that supports
        prefix matching. Typing <em>Schach</em> will match entries containing
        <em>Schachnovelle</em>, <em>Schachspieler</em>, etc.
      </p>

      <h2>Browsing by Category</h2>
      <p>
        The <a href="#">home page</a> displays entry types as tiles, grouped
        into Works, Reception &amp; Impact, and Editions. Click any tile to
        see all entries of that type. The number on each tile indicates how many
        entries belong to that category.
      </p>

      <h2>Filtering</h2>
      <p>
        In the results view, the sidebar offers faceted filters for:
      </p>
      <ul>
        <li><strong>Type</strong> &mdash; Entry type (fiction, essay, secondary literature, etc.)</li>
        <li><strong>Language</strong> &mdash; Publication language</li>
        <li><strong>Period</strong> &mdash; Time period (pre-Zweig, lifetime, post-WWII, late 20th century, contemporary)</li>
        <li><strong>Location</strong> &mdash; Publication location</li>
      </ul>
      <p>
        Filters can be combined with each other and with a search query. Active
        filters appear as chips above the results and can be removed individually
        by clicking the &times; button.
      </p>
      <p>
        On mobile devices, filters are accessible via the filter button in the
        bottom-right corner of the screen.
      </p>

      <h2>Sorting</h2>
      <p>
        Results can be sorted by relevance (default for search queries), year
        (ascending or descending), or title (alphabetical). Use the sort dropdown
        in the results header.
      </p>

      <h2>Entry Details</h2>
      <p>
        Click any result card to expand it and see the full entry details:
      </p>
      <ul>
        <li>Structured metadata (title, year, publisher, location, language, translator, page count)</li>
        <li>Full bibliographic entry as recorded in the original Klawiter wiki</li>
        <li>Reprints and later editions (where available)</li>
        <li>Translations (where available)</li>
        <li>Table of contents for anthologies and collected works</li>
        <li>Cross-references to related entries (&ldquo;See also&rdquo;)</li>
      </ul>

      <h2>Exporting</h2>
      <p>
        Several export options are available from the expanded entry view:
      </p>
      <ul>
        <li>
          <strong>BibTeX</strong> &mdash; Export a single entry or all filtered results
          as a <code>.bib</code> file for use in reference managers.
        </li>
        <li>
          <strong>RIS</strong> &mdash; Export a single entry in RIS format, compatible
          with EndNote, Mendeley, and other reference management software.
        </li>
        <li>
          <strong>JSON-LD</strong> &mdash; Download the structured data for a single
          entry in JSON-LD format for use in Linked Data workflows.
        </li>
        <li>
          <strong>Permalink</strong> &mdash; Copy a stable URL for any entry to your
          clipboard. Permalinks use the format <code>#entry=&lt;pageId&gt;</code>
          and remain valid as long as this site is hosted.
        </li>
      </ul>
      <p>
        For the full dataset download, see the <a href="#data">Data Access</a> page
        or the <a href="#stats">Statistics</a> page.
      </p>

      <h2>Using with Zotero</h2>
      <p>
        The BibTeX and RIS export formats are directly compatible with
        <a href="https://www.zotero.org/" target="_blank" rel="noopener">Zotero</a>
        and other reference managers. To import entries into your Zotero library:
      </p>
      <ol>
        <li>
          <strong>Single entry:</strong> Expand an entry card, click
          <em>Export BibTeX</em> or <em>Export RIS</em>. A file will be downloaded.
        </li>
        <li>
          <strong>Multiple entries:</strong> Filter the results to the set you need
          (e.g. all Fiction in French), then click <em>Export BibTeX</em> in the
          results header to download all filtered entries as one file.
        </li>
        <li>
          In Zotero, go to <strong>File &rarr; Import&hellip;</strong> and select the
          downloaded <code>.bib</code> or <code>.ris</code> file.
        </li>
        <li>
          Zotero will create entries with title, author, year, publisher, location,
          language, and page count pre-filled.
        </li>
      </ol>
      <p>
        <strong>Tip:</strong> The batch BibTeX export is particularly useful for
        building a Zweig research bibliography. Use the type and language filters
        to select a coherent subset, then export everything at once.
      </p>

      <h2>Frequently Asked Questions</h2>

      <h3>Why are some fields missing for certain entries?</h3>
      <p>
        Not all entries in the original bibliography include complete metadata.
        Many shorter entries or journal articles do not specify a publisher or
        location. German-language originals typically do not name a translator.
        The coverage rates are documented on the <a href="#methodology">Methodology</a> page.
      </p>

      <h3>Can I download the entire dataset?</h3>
      <p>
        Yes. The full dataset is available as a JSON-LD file from the
        <a href="#data">Data Access</a> page or via the download button on the
        <a href="#stats">Statistics</a> page.
      </p>

      <h3>How should I cite this resource?</h3>
      <p>
        Citation recommendations are provided on the <a href="#imprint">Imprint</a> page.
      </p>

      <h3>I found an error. How can I report it?</h3>
      <p>
        Please open an issue on the
        <a href="https://github.com/chpollin/klawiter-rescue/issues" target="_blank" rel="noopener">GitHub repository</a>.
        Include the entry title or page ID and a description of the problem.
      </p>
    </div>`;
  },

  // ---------------------------------------------------------------------------
  // Data
  // ---------------------------------------------------------------------------
  data() {
    const entryCount = App.entries ? App.entries.length.toLocaleString('en') : '4,700+';
    return `<div class="page-content">
      <h1>Data Access &amp; Reuse</h1>

      <p>
        The Klawiter Bibliography dataset is available for download in structured
        formats. It is intended for use in scholarly research, digital humanities
        projects, and library cataloguing.
      </p>

      <h2>Dataset Download</h2>
      <p>
        The complete dataset contains ${entryCount} bibliography entries with
        structured metadata in JSON-LD format.
      </p>
      <div class="page-actions">
        <button class="action-btn page-download-btn" onclick="Export.fullDataset()">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          Download Full Dataset (JSON-LD)
        </button>
      </div>

      <h2>Data Format</h2>
      <p>
        Each entry is a JSON-LD node with the following core fields:
      </p>
      <table class="page-table">
        <thead>
          <tr><th>Field</th><th>Type</th><th>Description</th></tr>
        </thead>
        <tbody>
          <tr><td><code>title</code></td><td>String</td><td>Work title (cleaned of wiki markup)</td></tr>
          <tr><td><code>year</code></td><td>Integer</td><td>Publication year</td></tr>
          <tr><td><code>publisher</code></td><td>String</td><td>Publisher name</td></tr>
          <tr><td><code>location</code></td><td>String</td><td>Publication location</td></tr>
          <tr><td><code>language</code></td><td>String</td><td>Language (English name)</td></tr>
          <tr><td><code>languageCode</code></td><td>String</td><td>ISO 639-1 code</td></tr>
          <tr><td><code>translator</code></td><td>String</td><td>Translator name</td></tr>
          <tr><td><code>pageCount</code></td><td>Integer</td><td>Number of pages</td></tr>
          <tr><td><code>entryType</code></td><td>String</td><td>One of 16 entry types</td></tr>
          <tr><td><code>timePeriod</code></td><td>String</td><td>Historical period classification</td></tr>
          <tr><td><code>categories</code></td><td>Array</td><td>MediaWiki categories</td></tr>
          <tr><td><code>fullBibliographicEntry</code></td><td>String</td><td>Original text from the wiki</td></tr>
        </tbody>
      </table>
      <p>
        Additional fields include <code>reprints</code>, <code>translations</code>,
        <code>contentItems</code> (table of contents), <code>seeAlso</code>
        (cross-references), and provenance fields (<code>sourcePageId</code>,
        <code>sourceTextId</code>).
      </p>

      <h2>Vocabulary</h2>
      <p>
        The JSON-LD context uses a blend of established vocabularies and a
        domain-specific namespace:
      </p>
      <ul>
        <li><strong>Schema.org</strong> &mdash; Standard bibliographic properties (name, datePublished, publisher, inLanguage)</li>
        <li><strong>Dublin Core</strong> &mdash; Provenance and identifier fields (source, identifier)</li>
        <li><strong><code>klawiter:</code></strong> &mdash; Domain-specific types and fields for the Zweig bibliography</li>
      </ul>
      <p>
        The <code>klawiter:</code> namespace resolves to
        <a href="vocab/index.html">the vocabulary documentation</a>.
      </p>

      <h2>Direct Access</h2>
      <p>
        The frontend data file can be accessed directly at
        <a href="data/klawiter.json"><code>data/klawiter.json</code></a>.
        This is a single JSON file containing all entries and the redirect map.
        The file is approximately 9&nbsp;MB.
      </p>

      <h2>License</h2>
      <p>
        The bibliographic data is provided for scholarly and non-commercial use.
        The source code of the extraction pipeline and this website is available
        on <a href="https://github.com/chpollin/klawiter-rescue" target="_blank" rel="noopener">GitHub</a>.
        A formal license designation is forthcoming.
      </p>

      <h2>Citation</h2>
      <p>
        When citing the dataset, please credit both the original compiler and
        this digital edition:
      </p>
      <blockquote>
        Klawiter, Randolph J.: <em>Stefan Zweig &mdash; An International
        Bibliography.</em> Digital edition, 2026.
        Available at: <code>https://chpollin.github.io/klawiter-rescue/</code>
      </blockquote>
    </div>`;
  },

  // ---------------------------------------------------------------------------
  // JSON-LD Playground
  // ---------------------------------------------------------------------------
  jsonld() {
    // Render HTML first, then init interactive parts after DOM update
    setTimeout(() => JsonldPlayground.init(), 0);

    return `<div class="page-content page-content-wide">
      <h1>JSON-LD Playground</h1>

      <p>
        Explore the Linked Data structure of the Klawiter Bibliography. Each entry
        is a JSON-LD node combining
        <a href="https://schema.org" target="_blank" rel="noopener">Schema.org</a>,
        <a href="http://purl.org/dc/terms/" target="_blank" rel="noopener">Dublin Core</a>,
        and the domain-specific
        <a href="vocab/index.html"><code>klawiter:</code> namespace</a>.
      </p>

      <h2>Select an Entry</h2>
      <div class="jsonld-controls">
        <div class="jsonld-search-wrap">
          <input type="text" id="jsonld-search" class="jsonld-search"
                 placeholder="Search by title..." autocomplete="off">
          <div id="jsonld-suggestions" class="jsonld-suggestions hidden"></div>
        </div>
        <button class="action-btn" id="jsonld-random">Random Entry</button>
      </div>

      <div id="jsonld-stats" class="jsonld-stats"></div>

      <div class="jsonld-tabs">
        <button class="jsonld-tab active" data-tab="compact">Compact</button>
        <button class="jsonld-tab" data-tab="expanded">Expanded</button>
        <button class="jsonld-tab" data-tab="triples">Triples</button>
      </div>

      <div id="jsonld-compact" class="jsonld-panel jsonld-code"></div>
      <div id="jsonld-expanded" class="jsonld-panel jsonld-code hidden"></div>
      <div id="jsonld-triples" class="jsonld-panel hidden"></div>

      <h2>Vocabulary</h2>
      <table class="page-table">
        <thead><tr><th>Prefix</th><th>Namespace</th><th>Usage</th></tr></thead>
        <tbody>
          <tr>
            <td><code>schema:</code></td>
            <td><code>https://schema.org/</code></td>
            <td>Standard bibliographic properties (name, datePublished, publisher, inLanguage, numberOfPages, translator, locationCreated, author)</td>
          </tr>
          <tr>
            <td><code>dcterms:</code></td>
            <td><code>http://purl.org/dc/terms/</code></td>
            <td>Full bibliographic citation text (bibliographicCitation)</td>
          </tr>
          <tr>
            <td><code>klawiter:</code></td>
            <td><code>chpollin.github.io/klawiter-rescue/vocab/</code></td>
            <td>Domain-specific: entryType, timePeriod, categories, sourcePageId, and 16 entry type classes</td>
          </tr>
          <tr>
            <td><code>xsd:</code></td>
            <td><code>w3.org/2001/XMLSchema#</code></td>
            <td>Typed literals: integer (page counts, IDs), gYear (publication dates)</td>
          </tr>
        </tbody>
      </table>

      <h2>@context Explained</h2>
      <p>
        The <code>@context</code> maps short property names to full IRIs. For example,
        <code>"name"</code> expands to <code>https://schema.org/name</code>, and
        <code>"entryType"</code> expands to
        <code>https://chpollin.github.io/klawiter-rescue/vocab/entryType</code>.
        This means the same JSON data is both human-readable and machine-processable
        as RDF.
      </p>
      <p>
        The <strong>Compact</strong> tab shows the entry as a JSON-LD processor would
        receive it. The <strong>Expanded</strong> tab shows all URIs fully resolved.
        The <strong>Triples</strong> tab shows the RDF statements a processor would
        extract.
      </p>
      <p>
        The full dataset (${App.entries ? App.entries.length.toLocaleString('en') : '5,000+'} entries)
        is available as <a href="data/klawiter.json">JSON</a> (frontend format) and as
        <a href="https://github.com/chpollin/klawiter-rescue/blob/main/data/output/klawiter.jsonld" target="_blank" rel="noopener">JSON-LD</a>
        (semantic format with @context).
      </p>
    </div>`;
  },

  // ---------------------------------------------------------------------------
  // Imprint
  // ---------------------------------------------------------------------------
  imprint() {
    return `<div class="page-content">
      <h1>Imprint</h1>

      <h2>Project</h2>
      <p>
        This digital edition of the Klawiter Bibliography was produced as part of
        a data rescue effort to preserve and make accessible the Stefan Zweig
        bibliography compiled by Dr. Randolph J. Klawiter. It is a scholarly
        resource intended for academic research and non-commercial use.
      </p>

      <h2>Credits</h2>
      <ul>
        <li>
          <strong>Bibliography</strong> &mdash;
          Dr. Randolph J. Klawiter, Professor Emeritus of German,
          University of Notre Dame, Indiana, USA
        </li>
        <li>
          <strong>Stefan Zweig Centre Salzburg</strong> &mdash;
          Institutional context and connection to the
          <a href="https://stefanzweig.digital/" target="_blank" rel="noopener">Stefan Zweig Digital</a>
          research infrastructure
        </li>
        <li>
          <strong>Digital Edition</strong> &mdash;
          Data extraction pipeline, frontend development, and publication
        </li>
      </ul>

      <h2>Citation</h2>
      <p>
        When referencing this resource in academic publications, please use the
        following citation:
      </p>
      <blockquote>
        Klawiter, Randolph J.: <em>Stefan Zweig &mdash; An International
        Bibliography.</em> Digital edition, 2026.
        URL: <code>https://chpollin.github.io/klawiter-rescue/</code>
      </blockquote>
      <p>
        To cite a specific entry, use its permalink URL
        (e.g. <code>https://chpollin.github.io/klawiter-rescue/#entry=3</code>).
      </p>

      <h2>License</h2>
      <p>
        The source code for the extraction pipeline and this website is available
        on GitHub. A formal license for the bibliographic data and the code is
        forthcoming.
      </p>
      <ul>
        <li>
          <a href="https://github.com/chpollin/klawiter-rescue" target="_blank" rel="noopener">GitHub Repository</a>
          &mdash; Source code, pipeline scripts, documentation
        </li>
        <li>
          <a href="https://github.com/chpollin/klawiter-rescue/issues" target="_blank" rel="noopener">Issue Tracker</a>
          &mdash; Report errors or suggest improvements
        </li>
      </ul>

      <h2>Contact</h2>
      <p>
        For questions, corrections, or collaboration inquiries, please use the
        <a href="https://github.com/chpollin/klawiter-rescue/issues" target="_blank" rel="noopener">GitHub issue tracker</a>.
      </p>

      <h2>Technical Information</h2>
      <p>
        This site is a static web application deployed on GitHub Pages. It uses
        no server-side processing; all data is loaded and rendered in the browser.
        The extraction pipeline is written in Python. The full technical
        documentation is available in the
        <a href="https://github.com/chpollin/klawiter-rescue" target="_blank" rel="noopener">project repository</a>.
      </p>
    </div>`;
  },
};

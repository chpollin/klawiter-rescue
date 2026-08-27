/**
 * Static content pages — About (project, methodology, help, imprint) and
 * Data (model, specification, downloads, playground, quality pointer).
 * Each method returns an HTML string rendered into #view-page.
 *
 * Counts come from App.data._meta so the prose cannot drift away from the
 * shipped dataset. The document title is set by App._updateTitle alone.
 */
const Pages = {

  render(slug) {
    const container = document.getElementById('view-page');
    const renderer = this[slug];
    if (!renderer) return;
    container.innerHTML = renderer.call(this);
    window.scrollTo(0, 0);
  },

  // --- Shared helpers ---------------------------------------------------

  _meta() {
    return (App.data && App.data._meta) || {};
  },

  _num(value) {
    return typeof value === 'number' ? value.toLocaleString('en') : '—';
  },

  /** Coverage percentage of a field, from the shipped baseline. */
  _cov(field) {
    const cov = this._meta().fieldCoverage || {};
    return cov[field] ? `${cov[field].pct}%` : '—';
  },

  _typeCount() {
    const types = this._meta().entryTypes;
    return types ? Object.keys(types).length : Object.keys(ENTRY_TYPE_LABELS).length;
  },

  _yearRange() {
    const r = this._meta().yearRange;
    return r ? `${r.min}–${r.max}` : '';
  },

  /** In-page anchor navigation; hrefs are real routes ('#about/help'). */
  _anchorNav(slug, items) {
    const links = items.map(([id, label]) =>
      `<a href="#${slug}${id ? '/' + id : ''}">${esc(label)}</a>`).join('');
    return `<nav class="page-anchors" aria-label="Sections">${links}</nav>`;
  },

  // ---------------------------------------------------------------------------
  // About — project, methodology, help, imprint in one page
  // ---------------------------------------------------------------------------
  about() {
    const m = this._meta();
    const entries = this._num(m.ns0Count);
    return `<div class="page-content">
      <h1>About</h1>
      ${this._anchorNav('about', [
        ['', 'About the project'],
        ['methodology', 'Methodology'],
        ['help', 'Help'],
        ['imprint', 'Imprint'],
      ])}

      <section id="sec-about">
        <h2>About the project</h2>
        <p>
          The Klawiter Bibliography is one of the most comprehensive reference
          works on Stefan Zweig (1881&ndash;1942). It holds ${entries}
          bibliographic records of publications by and about the Austrian author,
          covering fiction, essays, poetry, drama, correspondence, secondary
          literature, translations and collected editions in
          ${this._num(m.languageCount)} languages
          (${this._yearRange()}).
        </p>
        <p>
          It was compiled by Dr. Randolph J. Klawiter, Professor Emeritus of
          German at the University of Notre Dame (Indiana, USA), over several
          decades, and published online as a MediaWiki instance. That wiki held
          6,725 pages: the bibliography entries republished here, 1,546 redirect
          pages for cross-references and title variants, and a few hundred
          category descriptions.
        </p>
        <p>
          When the hosting infrastructure was discontinued, the wiki went
          offline. An SQL database dump and eight binary content files survived
          as the sole remaining record in digital form. This site is the result
          of the rescue: the raw files were parsed, cleaned and transformed into
          a structured dataset that is both readable and machine-processable.
          How that was done is described under
          <a href="#about/methodology">Methodology</a>; the published files and
          the vocabulary are documented on the <a href="#data">Data</a> page.
        </p>
        <p>
          The project is connected to
          <a href="https://stefanzweig.digital/" target="_blank" rel="noopener">Stefan Zweig Digital</a>,
          a research initiative at the Stefan Zweig Centre Salzburg providing
          digital access to Zweig&rsquo;s literary estate. The bibliography
          complements that collection by documenting the publication history the
          estate materials produced, and the visual design follows the Stefan
          Zweig Digital design language to signal the affiliation.
        </p>
      </section>

      <section id="sec-methodology">
        <h2>Methodology</h2>
        <p>
          The source material is a MediaWiki SQL database dump and eight binary
          content files holding the full content of the original wiki. The
          database stores content in a four-layer chain
          (page &rarr; revision &rarr; slot &rarr; content &rarr; text ID in a
          BLOB file); the pipeline resolves that chain per page and takes the
          latest revision. It is written in Python and needs no database server.
        </p>
        <ol>
          <li>
            <strong>Extract</strong> &mdash; parse the SQL INSERT statements and
            the BLOB files directly and retrieve the latest text of every
            main-namespace page.
          </li>
          <li>
            <strong>Fix encoding</strong> &mdash; detect and repair Mojibake
            (character corruption from Latin-1/UTF-8 misinterpretation), which
            brings the measured Mojibake rate to zero.
          </li>
          <li>
            <strong>Parse</strong> &mdash; extract title, year, publisher,
            location, language, translator, page count, categories,
            cross-references, reprints and table-of-contents items from the wiki
            markup with regular expressions.
          </li>
          <li>
            <strong>LLM enrichment</strong> &mdash; fill remaining gaps in
            publisher, location, translator and page count with
            <code>gemini-3.1-flash-lite-preview</code>, replayed from a frozen
            cache; the production run makes no network calls. Every derived
            value passes a Mojibake validation filter and is marked as
            model-derived in the provenance layer.
          </li>
          <li>
            <strong>Classify</strong> &mdash; assign each entry one of
            ${this._typeCount()} entry types from its wiki categories and one of
            five time periods from its publication year.
          </li>
          <li>
            <strong>Convert</strong> &mdash; emit the canonical JSON-LD graphs
            and the flat frontend projection this site loads.
          </li>
          <li>
            <strong>Validate</strong> &mdash; produce a quality report with
            field coverage, distributions and the entries carrying open signals.
          </li>
        </ol>
        <p>
          Quality assurance runs as an automated suite over encoding repair,
          regex patterns, markup parsing, classification and real-data
          extraction, plus SHACL contracts over both published graphs. A
          round-trip verification compares the final output against the original
          wiki text for every entry, a source census proves that every wiki page
          reaches the published data, and an LLM-as-a-judge evaluation assesses
          extraction quality on a stratified sample.
        </p>
        <h3>Known limitations</h3>
        <p>
          Field coverage in the shipped dataset: year ${this._cov('year')},
          location ${this._cov('location')}, language ${this._cov('language')},
          page count ${this._cov('pageCount')}, publisher
          ${this._cov('publisher')}, translator ${this._cov('translator')}. In
          most cases the missing value is genuinely absent from the source text
          rather than missed by the extraction; shorter entries and journal
          articles often name no publisher, and German-language originals name
          no translator.
        </p>
        <ul>
          <li>
            One entry (page ID 2979, &ldquo;A unidade espiritual do
            mundo&rdquo;) could not be extracted because its text is present in
            none of the BLOB files.
          </li>
          <li>
            Some cross-references point to titles that no entry and no redirect
            carries. They remain unresolvable red links and are listed
            individually in the <a href="#quality">Data Quality</a> workbench.
          </li>
          <li>
            The flat entry layer cannot fully separate edition-specific fields
            on pages that describe several editions. The edition graph is
            authoritative for those cases.
          </li>
        </ul>
      </section>

      <section id="sec-help">
        <h2>Help</h2>
        <p>
          All files are static; there is no server-side processing. Search,
          filtering and export run in the browser.
        </p>
        <h3>Search, browse, filter</h3>
        <p>
          The search field in the header and on the start page searches titles,
          publishers, locations, languages, translators and the full
          bibliographic text through a client-side index with prefix matching,
          so <em>Schach</em> matches <em>Schachnovelle</em>. The start page
          lists the entry types as groups; a click opens all entries of a type.
          In the result view the sidebar filters by type, language, period and
          location; filters combine with each other and with a query, appear as
          chips above the results and are removed individually. On small screens
          the filter button in the lower right opens the same panel. Results
          sort by relevance, year or title.
        </p>
        <h3>Entry details and export</h3>
        <p>
          A click on a result card expands it to the structured metadata, the
          original Klawiter entry, reprints, translations, table of contents and
          cross-references. From there an entry exports as BibTeX or RIS for
          reference managers, as JSON-LD for Linked Data workflows, or as a
          permalink of the form <code>#entry=&lt;pageId&gt;</code>. The result
          header exports the whole filtered set as one BibTeX file, which is the
          quickest way to build a working bibliography: filter to the subset,
          then import the file in Zotero through
          <strong>File &rarr; Import&hellip;</strong>. The full dataset is on the
          <a href="#data">Data</a> page.
        </p>
        <h3>Explore and data quality</h3>
        <p>
          <a href="#stats">Explore</a> offers a timeline, a geographic view and a
          Connections view with a ranked list of the most-referenced entries and
          a translator flow diagram. <a href="#quality">Data Quality</a> shows
          the processing state: field completeness per entry type, open review
          queues, unresolvable cross-references and the authority candidate
          queue for translators and publishers. Every list opens the affected
          entries directly.
        </p>
        <h3>Reporting an error</h3>
        <p>
          Please open an issue in the
          <a href="https://github.com/chpollin/klawiter-rescue/issues" target="_blank" rel="noopener">GitHub repository</a>
          with the entry title or page ID and a description of the problem.
        </p>
      </section>

      <section id="sec-imprint">
        <h2>Imprint</h2>
        <p>
          This digital edition preserves and reopens the Stefan Zweig
          bibliography compiled by Dr. Randolph J. Klawiter. It is a scholarly
          resource for academic research and non-commercial use.
        </p>
        <ul>
          <li>
            <strong>Bibliography</strong> &mdash; Dr. Randolph J. Klawiter,
            Professor Emeritus of German, University of Notre Dame, Indiana, USA
          </li>
          <li>
            <strong>Stefan Zweig Centre Salzburg</strong> &mdash; institutional
            context and connection to the
            <a href="https://stefanzweig.digital/" target="_blank" rel="noopener">Stefan Zweig Digital</a>
            research infrastructure
          </li>
          <li>
            <strong>Digital edition</strong> &mdash; data extraction pipeline,
            frontend development and publication
          </li>
        </ul>
        <h3>Citation</h3>
        <p>
          When referencing this resource in academic publications, please use:
        </p>
        <blockquote>
          Klawiter, Randolph J.: <em>Stefan Zweig &mdash; An International
          Bibliography.</em> Digital edition, 2026.
          URL: <code>https://chpollin.github.io/klawiter-rescue/</code>
        </blockquote>
        <p>
          To cite a single entry, use its permalink
          (e.g. <code>https://chpollin.github.io/klawiter-rescue/#entry=3</code>).
        </p>
        <h3>License and contact</h3>
        <p>
          The bibliographic dataset and the documentation are licensed under
          <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener">CC BY 4.0</a>,
          the source code of the extraction pipeline and this website under the
          MIT License. Source code, pipeline and documentation are in the
          <a href="https://github.com/chpollin/klawiter-rescue" target="_blank" rel="noopener">GitHub repository</a>;
          questions, corrections and collaboration inquiries go to its
          <a href="https://github.com/chpollin/klawiter-rescue/issues" target="_blank" rel="noopener">issue tracker</a>.
        </p>
      </section>
    </div>`;
  },

  // ---------------------------------------------------------------------------
  // Data — model, specification, downloads, playground, quality
  // ---------------------------------------------------------------------------
  data() {
    // The playground binds its own controls once the markup is in the DOM.
    setTimeout(() => JsonldPlayground.init(), 0);

    const gh = 'https://github.com/chpollin/klawiter-rescue/blob/main';
    return `<div class="page-content page-content-wide">
      <h1>Data</h1>
      ${this._anchorNav('data', [
        ['', 'The data model'],
        ['spec', 'Specification & vocabulary'],
        ['downloads', 'Downloads'],
        ['playground', 'JSON-LD Playground'],
        ['quality', 'Data quality'],
      ])}

      <section id="sec-model">
        <h2>The data model</h2>
        <p>
          The dataset has two layers. The <strong>edition graph</strong> is the
          canonical publication: a work node carries its editions, an edition
          carries the publication facts of one concrete issue, and an annotation
          binds each asserted value to the source text slice it comes from.
          The <strong>flat entry layer</strong> is a declared projection of that
          graph, one record per wiki page, and it is what this site loads. The
          projection is lossy by design: where a wiki page describes several
          editions, the flat record cannot separate their fields, and the
          edition graph stays authoritative.
        </p>
        <p>
          Cases where the source text supports more than one reading are not
          silently resolved. A <strong>contested claim</strong> keeps the source
          value, the competing interpretations, the review history and the open
          status side by side, and it is exported as such. A candidate that has
          not been decided never becomes a confirmed authority link in the
          interface.
        </p>
        <p>
          Every asserted field carries its <strong>provenance</strong>: whether
          it was read from the markup by a regular expression, derived by the
          language model, or set by an editor. The interface shows this as an
          R/L/E badge, and the <a href="#quality">Data Quality</a> workbench
          lists the model-derived values as their own work queue.
        </p>
      </section>

      <section id="sec-spec">
        <h2>Specification &amp; vocabulary</h2>
        <p>
          The <code>klawiter:</code> namespace resolves to
          <a href="vocab/index.html">the vocabulary documentation</a>, which
          publishes 91 terms, each with its own resolvable page: the entry type
          classes, the bibliographic and provenance properties, and the terms of
          the contested-claim model. Alongside it the entries use
          <a href="https://schema.org" target="_blank" rel="noopener">Schema.org</a>
          for standard bibliographic properties and
          <a href="http://purl.org/dc/terms/" target="_blank" rel="noopener">Dublin Core</a>
          for the full citation text; the JSON-LD <code>@context</code> maps the
          short property names onto these IRIs and travels with the canonical
          graphs.
        </p>
        <p>
          Both published graphs are constrained by SHACL shapes in the
          repository:
          <a href="${gh}/data/schema/flat-shapes.ttl" target="_blank" rel="noopener"><code>data/schema/flat-shapes.ttl</code></a>
          for the flat entry layer and
          <a href="${gh}/data/schema/work-edition-shapes.ttl" target="_blank" rel="noopener"><code>data/schema/work-edition-shapes.ttl</code></a>
          for the edition graph. Validation runs as part of the pipeline test
          suite.
        </p>
      </section>

      <section id="sec-downloads">
        <h2>Downloads</h2>
        <p>
          These files are served by this site and can be fetched directly:
        </p>
        <table class="page-table">
          <thead><tr><th>File</th><th>Role</th></tr></thead>
          <tbody>
            <tr>
              <td><a href="data/klawiter.json"><code>data/klawiter.json</code></a></td>
              <td>The flat entry layer this site runs on: all entries, the
                  redirect map and the coverage baseline in
                  <code>_meta</code>. Frontend key names, no
                  <code>@context</code>. About 10&nbsp;MB.</td>
            </tr>
            <tr>
              <td><a href="data/reconciliation.json"><code>data/reconciliation.json</code></a></td>
              <td>Authority work: location, translator and publisher
                  candidates with their source occurrences, the decisions taken
                  so far, and the contested claims left open.</td>
            </tr>
            <tr>
              <td><a href="data/locations.json"><code>data/locations.json</code></a></td>
              <td>Publication places with their Wikidata reconciliation.</td>
            </tr>
            <tr>
              <td><a href="data/triage.json"><code>data/triage.json</code></a></td>
              <td>Per-entry review signals: round-trip deviations, census
                  anomalies, missing or model-derived provenance.</td>
            </tr>
          </tbody>
        </table>
        <div class="page-actions">
          <button class="action-btn page-download-btn" data-page-act="download-dataset">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/>
              <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            Download dataset (JSON)
          </button>
        </div>
        <p>
          The button downloads the loaded flat dataset together with the
          contested edition and authority claims of the current session. It is
          the frontend projection in frontend key names, not the JSON-LD
          serialization.
        </p>
        <p>
          The canonical graphs are <strong>not</strong> served by this site;
          they live in the repository and are reachable through GitHub only:
        </p>
        <ul>
          <li>
            <a href="${gh}/data/output/klawiter.jsonld" target="_blank" rel="noopener"><code>data/output/klawiter.jsonld</code></a>
            &mdash; the flat entry layer as JSON-LD, with <code>@context</code>
          </li>
          <li>
            <a href="${gh}/data/output/editions/work-editions.jsonld" target="_blank" rel="noopener"><code>data/output/editions/work-editions.jsonld</code></a>
            &mdash; the canonical work/edition/annotation graph
          </li>
          <li>
            <a href="https://github.com/chpollin/klawiter-rescue/tree/main/data/output/reconciliation" target="_blank" rel="noopener"><code>data/output/reconciliation/</code></a>
            &mdash; candidates, decisions, contested claims, provenance and
            validation reports of the authority work
          </li>
        </ul>
        <p>
          The dataset is licensed under
          <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener">CC BY 4.0</a>,
          the code under MIT. The citation recommendation is in the
          <a href="#about/imprint">Imprint</a>.
        </p>
      </section>

      <section id="sec-playground">
        <h2>Try it: JSON-LD Playground</h2>
        <p>
          Pick an entry and see it as a JSON-LD processor would: compact with
          the <code>@context</code> applied, expanded with all IRIs resolved,
          and as the RDF triples a processor extracts.
        </p>
        <div class="jsonld-controls">
          <div class="jsonld-search-wrap">
            <input type="text" id="jsonld-search" class="jsonld-search"
                   placeholder="Search by title..." autocomplete="off"
                   aria-label="Search entries by title">
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
              <td>Domain-specific: entryType, timePeriod, categories, sourcePageId, the entry type classes and the contested-claim terms</td>
            </tr>
            <tr>
              <td><code>xsd:</code></td>
              <td><code>w3.org/2001/XMLSchema#</code></td>
              <td>Typed literals: integer (page counts, IDs), gYear (publication dates)</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section id="sec-quality">
        <h2>Data quality</h2>
        <p>
          The <a href="#quality">Data Quality</a> workbench answers what is still
          open in the data: field completeness per entry type, the entries whose
          values are unverified or model-derived, the unresolvable
          cross-references and the undecided authority candidates, each list
          opening the affected entries directly.
        </p>
      </section>
    </div>`;
  },
};

// Delegated actions inside the static pages. Scoped to its own attribute so it
// cannot collide with the workbench dispatcher on the same container.
document.addEventListener('click', (ev) => {
  const el = ev.target.closest('#view-page [data-page-act]');
  if (!el) return;
  if (el.dataset.pageAct === 'download-dataset') Export.fullDataset();
});

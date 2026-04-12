---
title: Exploration
aliases: [visualization, D3]
tags: [exploration, visualization]
created: 2026-03-29
updated: 2026-04-12
---

# Exploration Interface

Design concept for the interactive exploration tool of the Klawiter Bibliography.

## Research Questions

The Klawiter Bibliography documents Stefan Zweig's global literary reception across 200 years, 41 languages, and 400+ publication locations. The exploration interface should help researchers answer:

1. **Temporal**: How did publication volume evolve over time? When were the major waves of Zweig reception?
2. **Linguistic**: Which languages dominated in which era? How did Zweig spread from German to Chinese, French, Arabic?
3. **Geographic**: Where was Zweig published? How did publication centers shift over time?
4. **Typological**: What types of works dominate? How does the ratio of primary works to secondary literature change?
5. **Relational**: How are entries connected? Which works were most reprinted, translated, or referenced?

## Design Rationale

### Why not a dashboard?

Standard dashboards (4 separate charts in a grid) fail for exploratory research because:
- Each chart is isolated — no visual connection between dimensions
- No progressive drill-down — what you see is what you get
- No narrative — dashboards present facts, not stories
- No serendipity — users can't discover unexpected patterns

### Why three modes?

Different research questions require different visual encodings. A single visualization cannot optimally serve temporal, categorical, and relational analysis simultaneously. Instead, three purpose-built modes share a common state and detail panel:

| Mode | Research Focus | Visual Encoding |
|------|---------------|-----------------|
| **Timeline** | Temporal + linguistic/typological | Stacked bar chart (year x language or type) |
| **Geography** | Spatial + temporal | Bubble map with brushed linking from Timeline |
| **Connections** | Relational | Force-directed network graph |

Note: The Overview mode (4 linked small multiples) was removed in Session 14 to focus on three strong modes rather than four mediocre ones.

### Progressive disclosure

- **Default**: Timeline mode — most familiar chart type, answers the broadest question
- **On demand**: Mode tabs for Geography and Connections
- **Detail panel**: Appears on selection (not always visible) — maximizes chart space
- **Exit to browse**: Double-click or "View entries" button navigates to the faceted search

## Data Landscape

### Dimensions available

| Dimension | Cardinality | Coverage | Notes |
|-----------|------------|----------|-------|
| Year | 1815–2020 | 93.2% | Integer, sparse before 1880 |
| Language | 41 unique | 89.4% | Top: German, Chinese, French, English, Spanish |
| Location | 402 unique | 87.5% | Top: Paris, Beijing, Berlin, Wien, Frankfurt |
| Entry Type | 16 types | 100% | Secondary Lit (29%), Fiction (23%), Essays (19%) |
| Time Period | 5 buckets | 100% | Derived from year |
| Publisher | ~1,000+ | 55.6% | Weak coverage, many missing |
| Translator | ~500+ | 41.9% | Weak coverage |
| Page Count | integer | 54.1% | Previously 81.6%, corrected after pp. N-M FP removal |

### Array fields (relational data)

| Field | Entries with data | Potential |
|-------|-------------------|-----------|
| categories | ~2,000+ | Category hierarchy, subcategory faceting |
| seeAlso | 683 (13.2%) | Internal cross-references → network graph |
| contentItems | 936 (18.1%) | Collections with chapter/story breakdown |
| reprints | 418 (8.1%) | Edition history |
| translations | 177 (3.4%) | Translation chains |

### Key patterns in the data

- **Zweig's lifetime peak** (1920s–1930s): Heavy German-language output
- **Post-exile shift** (1933+): Publications move from Berlin/Leipzig to Amsterdam, London, Buenos Aires
- **Post-war wave** (1950s–1970s): Global translations expand (Chinese, Arabic, Spanish)
- **Contemporary revival** (2000s+): Largest decade by volume — secondary literature + new translations
- **Chinese boom**: Chinese becomes the #2 language after German from 2000s onward

## Visualization Techniques

### Timeline: Three Visualization Modes

**D3 implementation**: `d3.stack()` + `rect`/`path`/`line` + `d3.brushX()`. File: `explore-timeline.js` (~750 LOC).

The Timeline offers three chart modes, each answering different research questions:

| Mode | Encoding | Research Question |
|------|----------|-------------------|
| **Bars** (default) | Stacked bars, decade-aggregated at full extent | "How did publication volume evolve?" (Q1) |
| **Sparklines** | Small multiples — one line per language | "Which languages dominated in which era?" (Q2) — direct comparison via individual baselines |
| **Ranks** | Bump chart — language rank per decade | "When did Chinese overtake German?" — shows rank transitions as crossing points |

**Design rationale (Session 15):** Stacked bars cannot answer Q2 because non-adjacent layers share neither a common baseline nor a common top (Cleveland & McGill 1984). Sparklines solve this by giving each language its own baseline. A streamgraph (`d3.stackOffsetWiggle`) was tested and removed — it smoothed discrete data with `curveBasis`, removed the baseline via wiggle offset, and provided no analytical advantage over the alternatives.

**Decade aggregation**: At full extent (>50 years), data is aggregated to decades (~21 bars at ~30px width instead of ~140 bars at ~6px). On brush-zoom to <50 years, switches to individual year bars. Matches the existing semantic zoom on x-axis labels.

**Features (Session 14–15):**
- **Layer toggle**: Switch between "by Language" (top 10 + Other) and "by Type" (top 10 entry types + other). Uses `Explore.colors.languages` and `Explore.colors.types`.
- **Semantic zoom**: At full extent: decade labels. On brush to <30 years: individual year labels. Dynamic tick formatting based on domain width.
- **Brush-state event**: Every brush update fires `explore:filterChange` CustomEvent on `document` with `Explore.filters.yearRange`. Consumed by Geography and Connections views for cross-view filtering.
- **Provenance overlay**: Global toggle "Data quality" in filter chips area (persists across tab switches). Shows semi-transparent bars per year with regex (green) / LLM (gold) / missing (burgundy) proportions. Only available in Bars mode (Sparklines/Ranks have no fixed baseline).
- **Annotations**: 5 markers — Born 1881, WWI 1914, Exile 1933, WWII 1939, Death 1942. Collision avoidance staggers overlapping labels. Hover shows detail text.
- **URL hash persistence**: Explore state (mode, filters, chart mode, layer mode, provenance) encoded in URL hash (`#stats/timeline?language=German&years=1920-1940&chart=sparklines`). Enables back/forward navigation and shareable links.

**Stack order**: `d3.stackOrderInsideOut` — largest category in center for visual stability.

**Zweig's lifetime**: Subtle gold band from 1881 to 1942 provides biographical context.

**Layout**: Full-width chart (no sidebar by default). Detail panel appears only on selection. Compact inline legend in controls bar above chart. Stats as text line in header ("4,751 entries . 41 languages . 15 types . 1815-2020").

### Connections: Two-Level Network

**D3 implementation**: `d3.forceSimulation()` with two view levels (semantic zoom for networks). File: `explore-network.js` (1,470 LOC).

**Sub-mode 1 — Cross-References:**

374 entries participate in seeAlso cross-references (~399 edges, 7.9% coverage). A flat force-directed layout of all nodes is unreadable at this scale, so the visualization uses a two-level approach analogous to the Geography semantic zoom (countries → cities):

**Level 1 — Community Overview (default):** Connected components are detected via BFS and aggregated into meta-nodes. Each meta-node represents one community, sized by member count, colored distinctly (d3.schemeTableau10), and labeled with the hub title. Small communities (< 3 members) are grouped into a "Small clusters" aggregate. Cross-community edges are shown as weighted meta-links (stroke: textLight #6B6B6B at 0.35 opacity, width 1.5-7px by weight). Coverage transparency: "374 of 4,751 entries connected (7.9%) in N communities" prominently displayed. The detail panel lists all communities with their hub and dominant type, plus coverage stats.

**Level 2 — Community Detail (click to drill down):** Clicking a community expands it into a standard force-directed layout of its members. Hub highlighting (top 10 by degree, with halo + permanent labels), degree filter slider (live transitions), and entry-type coloring. A back button returns to the overview. For large communities (100+ nodes), the degree filter starts at 2 to suppress leaf nodes. Hub labels follow nodes during drag.

**Sub-mode 2 — Translation Flows (Sankey Diagram):**

Three-column Sankey flow diagram: **Entry Type → Language → Translator**. Based on SankeyNetwork (2025, doi:10.1016/j.mex.2025.103230) — Sankey diagrams for bibliometric flow visualization. Uses `d3-sankey` plugin via CDN.

**Visual encoding:** Link width ∝ entry count. Links colored by language. Nodes: types (type palette), languages (language palette), translators (inherit dominant language color). Top 12 languages, 20 translators, 8 types; rest aggregated.

**Period filter:** Five buttons (All, 1881-1942, 1943-1980, 1981-2000, 2001+) redraw the Sankey, revealing temporal shifts (French dominance → Chinese boom).

**Interaction:** Hover node → highlight connected flows. Hover link → highlight single path. Click node → detail panel with entries.

**Design rationale:** Replaced force-directed language bubbles (Session 15) because: no insight from circles, no temporal dimension, no visible flows, unclear interaction. Sankey addresses all translator user stories: language activity (node height), top translators (visible without clicking), temporal change (period filter), translation pathways (flow paths), immediate comprehension (left→right reading).

The visualization reveals:
- Which works are most cross-referenced? (hub highlighting in cross-references)
- What clusters exist in the cross-reference network? (community overview)
- How do Zweig's work types flow into different languages? (Sankey left→middle)
- Who are the key translators per language? (Sankey middle→right)
- How do translation patterns shift across periods? (period filter)

## Interaction Design

### Shared across all modes

- **Detail panel** (right sidebar): Shows selected entries with full metadata
- **Tooltip on hover**: Lightweight preview without commitment
- **Double-click → browse**: Navigates to filtered results view
- **Filter chips**: Show active selections, removable with ×

### Mode-specific

| Mode | Primary interaction | Secondary |
|------|-------------------|-----------|
| Timeline | Brush time range | Click language layer |
| Geography | Click bubble / drag globe | Scroll to zoom (semantic zoom) |
| Connections | Click community/translator | Degree filter, drag nodes |

### Mode transitions

Switching modes preserves context where possible:
- Timeline → Overview: Brushed year range → decade filter
- Overview → Timeline: Type/language filters → highlighted streams
- Any → Connections: Selected entries' seeAlso links → highlighted nodes
- Connections → Any: Selected node's type/language/year → filters

## Technology

- **D3.js v7** via CDN — standard for academic information visualization
- **Replaces Chart.js** — D3 provides brushing, force simulation, stacked bars, bubble maps
- **4 JS modules**: `explore.js` (controller), `explore-timeline.js`, `explore-geography.js`, `explore-network.js`
- **Cross-view communication**: `explore:filterChange` CustomEvent on `document` — all views can react to filter changes from any other view
- **SVG rendering** — lightweight, exportable, accessible via DOM

## Color Palette

Extended from the existing SZD design system:

| Use | Color | Hex |
|-----|-------|-----|
| German (primary stream) | Burgundy | #7A1B2D |
| Chinese | Gold | #B8963E |
| French | Olive | #6B7A3A |
| English | Slate | #5B5040 |
| Spanish | Terracotta | #8B5C3A |
| Arabic | Purple | #5B3A7A |
| Bulgarian | Teal | #3A5B6B |
| Albanian | Sienna | #7A4A1B |
| Russian | Navy | #3A3A5B |
| Croatian | Dusty Rose | #6B3A4A |
| Other | Light Gray | #9E9585 |
| Zweig lifetime band | Gold (20% opacity) | #C2A360 |
| Grid lines | Warm gray | #EDE8DF |

## Information Seeking Mantra Assessment

The design follows Shneiderman's Visual Information Seeking Mantra (Overview first, zoom and filter, then details-on-demand) extended to seven tasks. Assessment as of Session 14 (2026-04-12):

| Task | Timeline | Geography | Connections |
|------|----------|-----------|-------------|
| Overview | Good (stacked area) | Good (globe + semantic zoom) | Good (community meta-nodes + language clusters) |
| Zoom | Good (brush = semantic zoom) | Good (geometric + semantic country→city) | Good (semantic: community→detail, language→translators) |
| Filter | Good (brush, chips) | Good (click, cross-filter) | Good (degree filter, cross-filter via events) |
| Details | Good (panel + tooltips) | Good (panel + tooltips) | Good (panel + tooltips, coverage stats) |
| Relate | Good (cross-mode filters) | Good (brushed linking from Timeline) | Good (cross-filter from Timeline/Geography) |
| History | Missing | Missing | Missing |
| Extract | JSON-LD download only | — | — |

### Design Decisions (2026-04-12)

**Overview-View not expanded.** The Overview (6 linked small multiples) remains as built but is not the focus of further development. Effort concentrates on three strong modes (Timeline, Geography, Connections) rather than four moderate ones.

**Personas.** Each view has an analytical identity guiding its development:
- L1 Temporal Analyst (Timeline) — time series, periodisation, trends
- L2 Spatial Analyst (Geography) — spaces, diffusion, cartography
- L3 Network Analyst (Connections) — graphs, hubs, communities, centrality

**Geography prioritisation.** A) Brushed Linking Timeline → Geography (highest impact: shows Zweig reception migration Wien/Berlin → Amsterdam/London → Beijing/Barcelona). B) Animated Playback (Play button through decades). C) Semantic Zoom (country aggregation by default, city bubbles on zoom-in).

**Brushed Linking (Geo-temporal Coupling).** The core cross-view feature: when a brush is set on the Timeline, Geography bubbles resize in real time via `explore:filterChange` events on `Explore.filters.yearRange`. This makes the spatial shift of Zweig reception visible as a continuous animation rather than a static snapshot.

### Connections Decisions (2026-04-12)

**Two-level architecture.** 574 nodes in a flat force-directed layout are unreadable. Two-level semantic zoom (community overview → detail drill-down) reduces this to ~20 readable meta-nodes. Same principle as Geography semantic zoom (countries → cities), applied to graph topology.

**Meta-link visibility.** Initial meta-links used `gridLine` (#EDE8DF) at 0.5 opacity — invisible on cream background. Fixed: `textLight` (#6B6B6B) at 0.35 opacity, width 1.5-7px. Effective rendered color ~#B4AFA8 — visible but not dominant.

**Coverage transparency.** The network shows only 7.9% of all entries. This is prominently displayed ("374 of 4,751 entries connected (7.9%)") so researchers understand the scope. The data gap is not a bug — most entries have no seeAlso links.

**Translator: force graph → Sankey diagram.** Force-directed language bubbles (Session 15) were replaced by a three-column Sankey (Entry Type → Language → Translator) because: (1) circles on white background gave no insight, (2) no temporal dimension, (3) no visible flows, (4) unclear interaction. The Sankey shows flows naturally (width ∝ count), has a period filter for temporal analysis, and is immediately readable left→right. Scientific basis: SankeyNetwork (2025, doi:10.1016/j.mex.2025.103230).

### Geography Implementation (2026-04-12, updated)

**Dual projection.** Globe (`d3.geoOrthographic()`, default) + flat map (`d3.geoNaturalEarth1()`) via toggle. Globe reduces overlap through hemisphere clipping — preferred by users for spatial exploration. Flat map shows all data simultaneously. Toggle switches without SVG teardown (`_rebuildProjection()`).

**Architecture (~790 LOC):**
- `_initProjection()`: globe or flat based on `projectionMode`
- `_initInteractions()`: globe = drag-to-rotate + wheel-zoom; flat = d3.zoom pan/zoom
- Semantic zoom: 2× threshold, ~82 country bubbles (r:[4,16]) ↔ ~366 city bubbles (r:[3,24])
- 382/382 locations with ISO Alpha-2 country codes (82 countries)
- Click = dims non-selected to 0.35 + filter chip + cross-view event (no destructive filter)
- Click ocean/land = deselect. Interactive legend = `toggleFilter()`. Animated playback = decade iteration.

**All original issues resolved** (click semantics, playback, labels, contrast, reset, legend).

## References

See [[references#information-visualization]] for full citations.

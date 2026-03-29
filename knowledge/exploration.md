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
| **Timeline** | Temporal + linguistic | Stacked area chart (year x language) |
| **Overview** | Multi-dimensional | 4 linked small multiples (cross-filtering) |
| **Connections** | Relational | Force-directed network graph |

### Progressive disclosure

- **Default**: Timeline mode — most familiar chart type, answers the broadest question
- **On demand**: Mode tabs for Overview and Connections
- **Detail panel**: Shows selected entries without leaving the visualization
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
| Page Count | integer | 81.6% | |

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

### Timeline: Stacked Area Chart

**D3 implementation**: `d3.area()` + `d3.stack()` + `d3.brushX()`

The stacked area chart shows publication volume over time, with layers colored by language. This encodes two dimensions simultaneously (time + language composition) and reveals patterns like the post-war translation wave and the Chinese boom.

**Stack order**: `d3.stackOrderInsideOut` places the largest streams in the center for visual stability. German (dominant) sits in the middle; smaller languages are at the edges.

**Zweig's lifetime**: A subtle gold band from 1881 to 1942 provides biographical context without dominating the visualization.

**Annotations**: Vertical lines at 1881 (birth), 1914 (WWI), 1933 (exile from Austria), 1942 (death in Petrópolis). These anchor the temporal narrative.

### Overview: Linked Small Multiples

**D3 implementation**: 4 sub-views in a 2x2 grid, sharing a filter state via cross-filtering.

1. **Decade histogram** (`d3.bin()` + rect): Temporal overview with brush
2. **Type treemap** (`d3.treemap()`): Hierarchical composition of entry types
3. **Language bars** (`d3.scaleBand()`): Top 15 languages, horizontal
4. **Location lollipop** (line + circle): Top 20 locations

Cross-filtering logic: clicking any element in any view filters the data across all four views. Active filters appear as removable chips. This follows the established paradigm of Shneiderman's "overview first, zoom and filter, then details-on-demand."

### Connections: Force-Directed Graph

**D3 implementation**: `d3.forceSimulation()` with link, charge, center, and collide forces.

Nodes represent entries that participate in seeAlso relationships (~500 nodes, ~500 edges). Node size encodes degree (number of connections), node color encodes entry type.

The graph reveals structural patterns:
- Which works are most cross-referenced?
- Are there clusters by type or language?
- Which entries serve as "hubs" connecting different parts of the bibliography?

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
| Overview | Click element in any view | Shift+click for multi-select |
| Connections | Click node | Drag to reposition, zoom/pan |

### Mode transitions

Switching modes preserves context where possible:
- Timeline → Overview: Brushed year range → decade filter
- Overview → Timeline: Type/language filters → highlighted streams
- Any → Connections: Selected entries' seeAlso links → highlighted nodes
- Connections → Any: Selected node's type/language/year → filters

## Technology

- **D3.js v7** via CDN — standard for academic information visualization
- **Replaces Chart.js** — D3 provides brushing, force simulation, stacked area, treemaps
- **4 JS modules**: `explore.js` (controller), `explore-timeline.js`, `explore-overview.js`, `explore-network.js`
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

## References

- Shneiderman, B. (1996). "The Eyes Have It: A Task by Data Type Taxonomy for Information Visualizations." IEEE Symposium on Visual Languages.
- Moretti, F. (2005). *Graphs, Maps, Trees: Abstract Models for Literary History.* Verso.
- Jänicke, S. et al. (2015). "On Close and Distant Reading in Digital Humanities." Eurographics Conference on Visualization.

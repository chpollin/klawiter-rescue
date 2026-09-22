/**
 * Shared constants — colors, entry type labels, period labels, category groupings.
 */

/** Canonical color palette (mirrors CSS custom properties in styles.css) */
const COLORS = {
  burgundy: '#631a34',
  burgundyDark: '#4A1228',
  burgundyLight: '#7A2D45',
  gold: '#C2A360',
  goldLight: '#D4B87A',
  cream: '#FAF8F3',
  gridLine: '#EDE8DF',
  textLight: '#6B6B6B',
};
/** Chart dimensions for explore visualizations */
const CHART_DIMS = {
  timeline: { height: 440 },
  geography: { height: 560 },
  network: { height: 560 },
};

const ENTRY_TYPE_LABELS = {
  'fiction': 'Fiction',
  'essay': 'Essays',
  'poetry': 'Poetry',
  'drama': 'Drama',
  'correspondence': 'Correspondence',
  'film': 'Film / Opera',
  'historical-study': 'Historical Studies',
  'secondary-literature': 'Secondary Literature',
  'collected-works': 'Collected Works',
  'foreword': 'Forewords / Afterwords',
  'translation': 'Translations (by Zweig)',
  'symposium': 'Symposia / Exhibitions',
  'dramatic-reading': 'Dramatic Readings',
  'newspaper': 'Newspaper Articles',
  'other': 'Other',
};

const PERIOD_LABELS = {
  'pre-zweig': 'Pre-Zweig (–1880)',
  'lifetime': 'Lifetime (1881–1942)',
  'post-wwii': 'Post-WWII (1943–1980)',
  'late-20c': 'Late 20th C. (1981–2000)',
  'contemporary': 'Contemporary (2001–)',
};

/**
 * Inclusive year bounds of the periods, mirroring the pipeline vocabulary that
 * writes `timePeriod`. A page carries one period per publication year, while
 * the flat field states the period of its first publication alone, so the
 * period axis has to be derived from the years rather than read off.
 */
const PERIOD_BOUNDS = {
  'pre-zweig': [-Infinity, 1880],
  'lifetime': [1881, 1942],
  'post-wwii': [1943, 1980],
  'late-20c': [1981, 2000],
  'contemporary': [2001, Infinity],
};

/**
 * Language codes occurring in the data whose customary script is not Latin.
 * A title of one of these languages written in Latin letters is a
 * transliteration and is tagged `<code>-Latn` (see titleAttrs in utils.js).
 */
const NON_LATIN_SCRIPT_LANGS = new Set([
  'ar', 'bg', 'bn', 'el', 'fa', 'he', 'hi', 'hy', 'ja', 'ka', 'ko',
  'ru', 'sr', 'uk', 'ur', 'yi', 'zh',
]);

/**
 * Published location of the site. Citation exports must carry a URL that
 * resolves for the reader, so a localhost or file:// run cites this instead of
 * its own origin.
 */
const SITE_URL = 'https://chpollin.github.io/klawiter-rescue/';

/** Category groupings for the home page */
const CATEGORY_GROUPS = [
  {
    heading: 'Works',
    types: ['fiction', 'essay', 'poetry', 'drama', 'correspondence', 'historical-study', 'foreword'],
  },
  {
    heading: 'Reception & Impact',
    types: ['secondary-literature', 'film', 'symposium', 'dramatic-reading', 'newspaper'],
  },
  {
    heading: 'Editions',
    types: ['collected-works', 'translation'],
  },
];

/** Groups of CATEGORY_GROUPS holding what Zweig wrote himself. */
const ZWEIG_OWN_GROUPS = ['Works', 'Editions'];

/**
 * Entry types that are about Zweig rather than by Zweig, derived from the
 * grouping the Overview already publishes: Works and Editions are his own,
 * Reception & Impact and everything the grouping leaves out is about him. A
 * second hand-kept list drifted from that grouping, which is how a historical
 * study by Zweig came to be exported without its author.
 */
const ABOUT_ZWEIG_TYPES = Object.keys(ENTRY_TYPE_LABELS).filter(type =>
  !CATEGORY_GROUPS.some(group =>
    ZWEIG_OWN_GROUPS.includes(group.heading) && group.types.includes(type)));

/**
 * Entry types whose page is indexed under the author of the translated or
 * prefaced text rather than under Zweig. Zweig's part there is a translator or
 * contributor credit, so a citation takes its author from the page title.
 */
const TITLE_AUTHOR_TYPES = ['translation', 'foreword'];

/**
 * Entry types whose pages hold Zweig's own texts and are cited under him: the
 * Works group without the forewords, and the collected works. Derived from the
 * grouping for the same reason as ABOUT_ZWEIG_TYPES.
 */
const ZWEIG_AUTHOR_TYPES = [
  ...CATEGORY_GROUPS.find(group => group.heading === 'Works').types,
  'collected-works',
].filter(type => !TITLE_AUTHOR_TYPES.includes(type));

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
 * Language codes occurring in the data whose customary script is not Latin.
 * A title of one of these languages written in Latin letters is a
 * transliteration and is tagged `<code>-Latn` (see titleAttrs in utils.js).
 */
const NON_LATIN_SCRIPT_LANGS = new Set([
  'ar', 'bg', 'bn', 'el', 'fa', 'he', 'hi', 'hy', 'ja', 'ka', 'ko',
  'ru', 'sr', 'uk', 'ur', 'yi', 'zh',
]);

/** Entry types that are about Zweig (not by Zweig) */
const ABOUT_ZWEIG_TYPES = ['secondary-literature', 'historical-study', 'symposium', 'other'];

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

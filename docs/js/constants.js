/**
 * Shared constants — entry type labels, period labels, category groupings.
 */
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

/** Entry types that are about Zweig (not by Zweig) */
const ABOUT_ZWEIG_TYPES = ['secondary-literature', 'symposium', 'film', 'dramatic-reading'];

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

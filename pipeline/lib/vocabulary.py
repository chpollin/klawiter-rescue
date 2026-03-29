"""
Klawiter Bibliography JSON-LD vocabulary definition.
Domain-specific vocabulary — can be mapped to Schema.org/DC/BibFrame later.
"""

CONTEXT = {
    "@context": {
        "klawiter": "https://klawiter-rescue.github.io/vocab/",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "klawiter:year": {"@type": "xsd:integer"},
        "klawiter:pageCount": {"@type": "xsd:integer"},
        "klawiter:sourcePageId": {"@type": "xsd:integer"},
        "klawiter:sourceTextId": {"@type": "xsd:integer"},
        "klawiter:sourceBlobId": {"@type": "xsd:integer"},
        "klawiter:translationOf": {"@type": "@id"},
        "klawiter:reprintOf": {"@type": "@id"},
        "klawiter:seeAlso": {"@type": "@id", "@container": "@set"},
        "klawiter:categories": {"@container": "@set"},
        "klawiter:contentItems": {"@container": "@list"},
    }
}

# Entry types derived from actual data
ENTRY_TYPES = {
    "fiction": "Fiction (novels, novellas, stories)",
    "essay": "Essays and articles",
    "poetry": "Poetry (individual poems, collections)",
    "drama": "Dramatic works (plays, libretti)",
    "correspondence": "Letters and correspondence",
    "film": "Film adaptations, operas, performances",
    "historical-study": "Historical and academic studies",
    "secondary-literature": "Secondary literature about Zweig",
    "collected-works": "Collected and selected works",
    "foreword": "Forewords, afterwords, editorial contributions",
    "translation": "Translations by Zweig of other authors",
    "symposium": "Symposia, exhibitions, conferences",
    "dramatic-reading": "Dramatic readings and performances",
    "newspaper": "Newspaper articles",
    "redirect": "Redirect to another entry",
    "other": "Unclassified entry",
}

TIME_PERIODS = {
    "pre-zweig": {"label": "Pre-Zweig", "range": (None, 1880)},
    "lifetime": {"label": "During Zweig's Lifetime", "range": (1881, 1942)},
    "post-wwii": {"label": "Post-WWII", "range": (1943, 1980)},
    "late-20c": {"label": "Late 20th Century", "range": (1981, 2000)},
    "contemporary": {"label": "Contemporary", "range": (2001, None)},
}

# Category → entry type mapping
CATEGORY_TYPE_MAP = {
    "Fiction": "fiction",
    "Essays": "essay",
    "Poetry": "poetry",
    "Dramas": "drama",
    "Correspondence": "correspondence",
    "Films": "film",
    "Historical Studies": "historical-study",
    "Secondary Literature": "secondary-literature",
    "Collected and Selected Works": "collected-works",
    "Forewords and Afterwords": "foreword",
    "Translations by Zweig": "translation",
    "Symposia and Exhibitions": "symposium",
    "Dramatic Readings": "dramatic-reading",
    "Newspapers": "newspaper",
}

# ISO 639-1 language mapping
LANGUAGE_MAP = {
    "German": "de", "English": "en", "French": "fr", "Spanish": "es",
    "Italian": "it", "Portuguese": "pt", "Russian": "ru", "Chinese": "zh",
    "Japanese": "ja", "Arabic": "ar", "Hebrew": "he", "Hindi": "hi",
    "Turkish": "tr", "Polish": "pl", "Czech": "cs", "Dutch": "nl",
    "Swedish": "sv", "Danish": "da", "Norwegian": "no", "Finnish": "fi",
    "Hungarian": "hu", "Romanian": "ro", "Greek": "el", "Korean": "ko",
    "Serbian": "sr", "Croatian": "hr", "Bulgarian": "bg", "Slovak": "sk",
    "Slovenian": "sl", "Lithuanian": "lt", "Latvian": "lv", "Estonian": "et",
    "Albanian": "sq", "Georgian": "ka", "Armenian": "hy", "Catalan": "ca",
    "Basque": "eu", "Galician": "gl", "Persian": "fa", "Urdu": "ur",
    "Bengali": "bn", "Thai": "th", "Vietnamese": "vi", "Indonesian": "id",
    "Malay": "ms", "Tagalog": "tl", "Ukrainian": "uk", "Belarusian": "be",
    "Yiddish": "yi", "Esperanto": "eo", "Latin": "la",
}


def classify_time_period(year):
    if year is None:
        return None
    for key, info in TIME_PERIODS.items():
        lo, hi = info["range"]
        if (lo is None or year >= lo) and (hi is None or year <= hi):
            return key
    return None


def category_to_entry_type(main_category):
    if not main_category:
        return "other"
    for prefix, entry_type in CATEGORY_TYPE_MAP.items():
        if main_category.startswith(prefix):
            return entry_type
    return "other"


def language_to_iso(language_name):
    if not language_name:
        return None
    # Direct match
    if language_name in LANGUAGE_MAP:
        return LANGUAGE_MAP[language_name]
    # Case-insensitive
    for name, code in LANGUAGE_MAP.items():
        if name.lower() == language_name.lower():
            return code
    # Already an ISO code?
    if len(language_name) == 2 and language_name.lower() in LANGUAGE_MAP.values():
        return language_name.lower()
    return None

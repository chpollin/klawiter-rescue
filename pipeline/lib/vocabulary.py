"""
Klawiter Bibliography JSON-LD vocabulary definition.
Blends Schema.org (standard bibliographic fields), Dublin Core (citation/provenance),
and klawiter: (domain-specific extensions for Stefan Zweig bibliography types).
"""

CONTEXT = {
    "@context": {
        # --- Namespace prefixes ---
        "schema": "https://schema.org/",
        "dcterms": "http://purl.org/dc/terms/",
        "klawiter": "https://klawiter-rescue.github.io/vocab/",
        "xsd": "http://www.w3.org/2001/XMLSchema#",

        # --- Schema.org mappings ---
        "name": "schema:name",
        "datePublished": "schema:datePublished",
        "publisher": "schema:publisher",
        "inLanguage": "schema:inLanguage",
        "numberOfPages": {"@id": "schema:numberOfPages", "@type": "xsd:integer"},
        "translator": "schema:translator",
        "locationCreated": "schema:locationCreated",
        "sameAs": {"@id": "schema:sameAs", "@type": "@id"},
        "isRelatedTo": {"@id": "schema:isRelatedTo", "@container": "@set"},
        "workTranslation": {"@id": "schema:workTranslation", "@container": "@set"},
        "hasPart": {"@id": "schema:hasPart", "@container": "@list"},
        "author": {"@id": "schema:author", "@type": "@id"},

        # --- Dublin Core mappings ---
        "bibliographicCitation": "dcterms:bibliographicCitation",

        # --- Domain-specific (klawiter:) ---
        "entryType": "klawiter:entryType",
        "timePeriod": "klawiter:timePeriod",
        "categories": {"@id": "klawiter:categories", "@container": "@set"},
        "contentItems": {"@id": "klawiter:contentItems", "@container": "@list"},
        "mainCategory": "klawiter:mainCategory",
        "originalTitle": "klawiter:originalTitle",
        "languageCode": "klawiter:languageCode",
        "allYears": {"@id": "klawiter:allYears", "@container": "@set"},
        "allLocations": {"@id": "klawiter:allLocations", "@container": "@set"},
        "reprints": {"@id": "klawiter:reprints", "@container": "@set"},
        "sourcePageId": {"@id": "klawiter:sourcePageId", "@type": "xsd:integer"},
        "sourceTextId": {"@id": "klawiter:sourceTextId", "@type": "xsd:integer"},
        "sourceBlobId": {"@id": "klawiter:sourceBlobId", "@type": "xsd:integer"},
        "pageNamespace": "klawiter:pageNamespace",
        "isRedirect": "klawiter:isRedirect",
        "redirectTarget": "klawiter:redirectTarget",
    }
}

# Schema.org @type mapping for entry types
# Each entry gets an array: [Schema.org type, klawiter: domain type]
SCHEMA_TYPE_MAP = {
    "fiction": ["schema:Book", "klawiter:FictionEntry"],
    "essay": ["schema:Article", "klawiter:EssayEntry"],
    "poetry": ["schema:CreativeWork", "klawiter:PoetryEntry"],
    "drama": ["schema:Play", "klawiter:DramaEntry"],
    "film": ["schema:Movie", "klawiter:FilmEntry"],
    "correspondence": ["schema:Message", "klawiter:CorrespondenceEntry"],
    "collected-works": ["schema:Collection", "klawiter:CollectedWorksEntry"],
    "secondary-literature": ["schema:ScholarlyArticle", "klawiter:SecondaryLiteratureEntry"],
    "historical-study": ["schema:ScholarlyArticle", "klawiter:HistoricalStudyEntry"],
    "translation": ["schema:Book", "klawiter:TranslationEntry"],
    "foreword": ["schema:CreativeWork", "klawiter:ForewordEntry"],
    "symposium": ["schema:Event", "klawiter:SymposiumEntry"],
    "dramatic-reading": ["schema:CreativeWork", "klawiter:DramaticReadingEntry"],
    "newspaper": ["schema:NewsArticle", "klawiter:NewspaperEntry"],
    "redirect": ["klawiter:RedirectEntry"],
    "other": ["schema:CreativeWork", "klawiter:OtherEntry"],
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

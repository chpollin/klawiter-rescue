"""
Klawiter Bibliography JSON-LD vocabulary definition.
Blends Schema.org (standard bibliographic fields), Dublin Core (citation/provenance),
and klawiter: (domain-specific extensions for Stefan Zweig bibliography types).
"""

CONTEXT = {
    "@context": {
        "@version": 1.1,
        # --- Namespace prefixes ---
        "schema": "https://schema.org/",
        "dcterms": "http://purl.org/dc/terms/",
        "klawiter": "https://chpollin.github.io/klawiter-rescue/vocab/",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        # --- Schema.org mappings ---
        "name": "schema:name",
        "description": "schema:description",
        "creator": "schema:creator",
        "sourceOrganization": "schema:sourceOrganization",
        "datePublished": {"@id": "schema:datePublished", "@type": "xsd:gYear"},
        "publisher": "schema:publisher",
        "inLanguage": "schema:inLanguage",
        "numberOfPages": {"@id": "schema:numberOfPages", "@type": "xsd:integer"},
        "translator": "schema:translator",
        "locationCreated": "schema:locationCreated",
        "sameAs": {"@id": "schema:sameAs", "@type": "@id"},
        "workTranslation": {"@id": "schema:workTranslation", "@container": "@set"},
        "hasPart": {"@id": "schema:hasPart", "@container": "@set"},
        "author": "schema:author",
        # --- Dublin Core mappings ---
        "bibliographicCitation": "dcterms:bibliographicCitation",
        "relation": {"@id": "dcterms:relation", "@container": "@set"},
        "license": {"@id": "dcterms:license", "@type": "@id"},
        # --- Domain-specific (klawiter:) ---
        "entryType": "klawiter:entryType",
        "timePeriod": "klawiter:timePeriod",
        "totalEntries": {"@id": "klawiter:totalEntries", "@type": "xsd:integer"},
        "entries": {"@id": "klawiter:entries", "@container": "@set"},
        "categories": {"@id": "klawiter:categories", "@container": "@set"},
        "contentItems": {"@id": "klawiter:contentItems", "@container": "@set"},
        "languageName": "klawiter:languageName",
        "seeAlsoText": {"@id": "klawiter:seeAlsoText", "@container": "@set"},
        "decomposedAsWork": {"@id": "klawiter:decomposedAsWork", "@type": "@id"},
        "mainCategory": "klawiter:mainCategory",
        "originalTitle": "klawiter:originalTitle",
        "languageCode": "klawiter:languageCode",
        "allYears": {"@id": "klawiter:allYears", "@container": "@set"},
        "allLocations": {"@id": "klawiter:allLocations", "@container": "@set"},
        "locationSameAs": {"@id": "klawiter:locationSameAs", "@type": "@id"},
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
    # The vocabulary deliberately records only skos:closeMatch to
    # schema:Message: the record describes correspondence, it is not the
    # message itself. The emitted type follows that decision.
    "correspondence": ["schema:CreativeWork", "klawiter:CorrespondenceEntry"],
    "collected-works": ["schema:Collection", "klawiter:CollectedWorksEntry"],
    "secondary-literature": [
        "schema:ScholarlyArticle",
        "klawiter:SecondaryLiteratureEntry",
    ],
    "historical-study": ["schema:ScholarlyArticle", "klawiter:HistoricalStudyEntry"],
    "translation": ["schema:Book", "klawiter:TranslationEntry"],
    "foreword": ["schema:CreativeWork", "klawiter:ForewordEntry"],
    # A symposium record is the bibliographic description of the event,
    # not the event; schema:Event would put work properties (datePublished,
    # numberOfPages) on an Event node.
    "symposium": ["schema:CreativeWork", "klawiter:SymposiumEntry"],
    "dramatic-reading": ["schema:CreativeWork", "klawiter:DramaticReadingEntry"],
    "newspaper": ["schema:NewsArticle", "klawiter:NewspaperEntry"],
    "redirect": ["klawiter:RedirectEntry"],
    "other": ["schema:CreativeWork", "klawiter:OtherEntry"],
    # Wiki infrastructure pages (category, template, help, file, mediawiki
    # namespaces) are preserved as source structure, typed as their own
    # class and never as bibliographic works.
    "category": ["klawiter:WikiInfrastructurePage"],
    "mediawiki": ["klawiter:WikiInfrastructurePage"],
    "template": ["klawiter:WikiInfrastructurePage"],
    "help": ["klawiter:WikiInfrastructurePage"],
    "file": ["klawiter:WikiInfrastructurePage"],
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

# BCP-47 language subtags, retaining historical source labels.
LANGUAGE_MAP = {
    "German": "de",
    "English": "en",
    "French": "fr",
    "Spanish": "es",
    "Italian": "it",
    "Portuguese": "pt",
    "Russian": "ru",
    "Chinese": "zh",
    "Japanese": "ja",
    "Arabic": "ar",
    "Hebrew": "he",
    "Hindi": "hi",
    "Turkish": "tr",
    "Polish": "pl",
    "Czech": "cs",
    "Dutch": "nl",
    "Swedish": "sv",
    "Danish": "da",
    "Norwegian": "no",
    "Finnish": "fi",
    "Hungarian": "hu",
    "Romanian": "ro",
    "Greek": "el",
    "Korean": "ko",
    "Serbian": "sr",
    "Croatian": "hr",
    # IANA retains sh for the macrolanguage; the source does not narrow it.
    "Serbo-Croatian": "sh",
    "Afrikaans": "af",
    "Bulgarian": "bg",
    "Slovak": "sk",
    "Slovenian": "sl",
    "Lithuanian": "lt",
    "Latvian": "lv",
    "Estonian": "et",
    "Albanian": "sq",
    "Georgian": "ka",
    "Armenian": "hy",
    "Catalan": "ca",
    "Basque": "eu",
    "Galician": "gl",
    "Persian": "fa",
    "Urdu": "ur",
    "Bengali": "bn",
    "Thai": "th",
    "Vietnamese": "vi",
    "Indonesian": "id",
    "Malay": "ms",
    "Tagalog": "tl",
    "Ukrainian": "uk",
    "Belarusian": "be",
    "Yiddish": "yi",
    "Esperanto": "eo",
    "Latin": "la",
}


def resource_iri(kind, name):
    """Stable instance IRI for an agent or place named in the source.

    Percent-encoding keeps names with spaces or non-ASCII letters valid
    as IRIs while staying deterministic and reversible.
    """
    from urllib.parse import quote

    return f"klawiter:{kind}/{quote(name, safe='')}"


def plain_value(value):
    """Flatten an RDF-shaped value (language-tagged literal or resource
    node) back to its display string; plain values pass through."""
    if isinstance(value, dict):
        return value.get("@value") or value.get("name") or ""
    return value


def to_rdf_entry(entry, agent_links=None):
    """Serialize the internal flat entry to its published RDF shape.

    The pipeline works on flat display values throughout; only the written
    JSON-LD carries language-tagged titles and resource nodes for agents
    and places. Everything downstream of the written dataset reads through
    plain_value. agent_links maps (kind, name) to a reviewed Wikidata URI
    (fail-closed: only confirmed decisions reach this map).
    """
    agent_links = agent_links or {}
    rdf = dict(entry)
    code = rdf.get("inLanguage")
    if code and rdf.get("name"):
        rdf["name"] = {"@value": rdf["name"], "@language": code}
    publisher = rdf.get("publisher")
    if publisher:
        node = {
            "@id": resource_iri("publisher", publisher),
            "@type": "schema:Organization",
            "name": publisher,
        }
        link = agent_links.get(("publisher", publisher))
        if link:
            node["sameAs"] = link
        rdf["publisher"] = node
    translator = rdf.get("translator")
    if translator:
        node = {
            "@id": resource_iri("person", translator),
            "@type": "schema:Person",
            "name": translator,
        }
        link = agent_links.get(("person", translator))
        if link:
            node["sameAs"] = link
        rdf["translator"] = node
    location = rdf.get("locationCreated")
    if location:
        place = {
            "@id": resource_iri("place", location),
            "@type": "schema:Place",
            "name": location,
        }
        same_as = rdf.pop("locationSameAs", None)
        if same_as:
            place["sameAs"] = same_as
        rdf["locationCreated"] = place
    # The as-written reference text is display data of the referencing
    # entry; asserting it as a name of the TARGET would give target
    # entries a second schema:name in the merged graph.
    relation = rdf.get("relation")
    if relation:
        rdf["relation"] = [{"@id": item["@id"]} for item in relation]
    return rdf


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

"""
Regex patterns for extracting bibliographic metadata from Klawiter entries.
"""

import re

from lib.config import MAX_VALID_YEAR, MIN_VALID_YEAR

# Year patterns
YEAR_RE = re.compile(r"\b(1[789]\d{2}|20[0-3]\d)\b")

# Publisher patterns (expanded beyond the original 3)
PUBLISHER_PATTERNS = [
    # Explicit labels
    re.compile(
        r"(?:Verlag|Publisher|Press|Publishing|Éditions?|Editore|Editorial|Editora|Wydawnictwo|Издательство)[\s:]+([^\n,.;()\[\]]{3,80})",
        re.IGNORECASE,
    ),
    # "published by" variants
    re.compile(
        r"(?:published by|verlegt bei|herausgegeben von|édité par|publicado por)\s+([^\n,.;()\[\]]{3,80})",
        re.IGNORECASE,
    ),
    # Known publisher name patterns (ends with Verlag, Press, etc.)
    re.compile(
        r"\b([\w\s&.-]{2,60}(?:Verlag|Press|Publishers?|Books|Edition|Éditions?|Editore|House))\b",
        re.IGNORECASE,
    ),
]

# Location patterns — cities commonly found in the bibliography
KNOWN_LOCATIONS = [
    "Wien",
    "Vienna",
    "Berlin",
    "Frankfurt",
    "Frankfurt am Main",
    "Leipzig",
    "London",
    "New York",
    "Paris",
    "Zurich",
    "Zürich",
    "Hamburg",
    "Munich",
    "München",
    "Salzburg",
    "Stockholm",
    "Amsterdam",
    "Bern",
    "Basel",
    "Prague",
    "Prag",
    "Praha",
    "Budapest",
    "Warsaw",
    "Warszawa",
    "Moscow",
    "Moskau",
    "Москва",
    "St. Petersburg",
    "Rome",
    "Roma",
    "Milan",
    "Milano",
    "Madrid",
    "Barcelona",
    "Lisbon",
    "Lisboa",
    "Buenos Aires",
    "Rio de Janeiro",
    "São Paulo",
    "Tokyo",
    "Tōkyō",
    "Beijing",
    "Shanghai",
    "Taipei",
    "Delhi",
    "New Delhi",
    "Mumbai",
    "Bombay",
    "Calcutta",
    "Kolkata",
    "Cairo",
    "Beirut",
    "Istanbul",
    "Tel Aviv",
    "Jerusalem",
    "Bucharest",
    "București",
    "Sofia",
    "Belgrade",
    "Beograd",
    "Zagreb",
    "Ljubljana",
    "Bratislava",
    "Vilnius",
    "Riga",
    "Tallinn",
    "Helsinki",
    "Oslo",
    "Copenhagen",
    "København",
    "Mexico City",
    "México",
    "Bogotá",
    "Santiago",
    "Lima",
    "Havana",
    "Sydney",
    "Melbourne",
    "Toronto",
    "Montreal",
    "Montréal",
    "Krems",
    "Krems an der Donau",
    "Graz",
    "Innsbruck",
    "Linz",
    "Wiesbaden",
    "Stuttgart",
    "Köln",
    "Cologne",
    "Düsseldorf",
    "Dresden",
    "Weimar",
    "Jena",
    "Göttingen",
    "Heidelberg",
    "Tübingen",
    "Freiburg",
    "Darmstadt",
    "Bonn",
    "Marburg",
    "Mainz",
    "Braunschweig",
]

# Build a regex for location detection (sorted by length descending to match longer names first)
_loc_sorted = sorted(KNOWN_LOCATIONS, key=len, reverse=True)
_loc_pattern = "|".join(re.escape(loc) for loc in _loc_sorted)
LOCATION_RE = re.compile(rf"\[?\b({_loc_pattern})\b\]?")

# Edition-header year grammar, the single origin shared with lib/editions.py:
# a header year is '1943' or 'ca. 1943' (any case). Both layers build their
# header regexes from this fragment so '[ca. YEAR]' parses identically in the
# flat extraction and in the edition segmentation.
EDITION_YEAR_PREFIX = r"(?:ca\.\s*)?\d{4}"

# Publication line: the bold citation that opens an edition block,
# '''[YEAR]: Publisher, Location'''. The separator after the year bracket is a
# colon in most entries but a period in some ('''[1983]. Verlag, Stadt'''), so
# both are accepted; this is a superset of the colon-only form and cannot change
# the colon entries. Constraining location extraction to this header keeps a city
# inside a chapter title (e.g. "Karlsbad und Weimar") from being taken as the
# place of publication. IGNORECASE only affects the 'ca.' literal.
PUBLICATION_LINE_RE = re.compile(
    rf"'''\s*\[{EDITION_YEAR_PREFIX}[^\]]*\]\s*[:.]\s*(.+?)'''", re.IGNORECASE
)
# Headerless excerpt/review entries carry the place in a [City, year] reference.
BRACKET_PLACE_RE = re.compile(r"\[([A-ZÀ-Ý][^\[\];]{1,38}?),\s*\d{4}")
# A known city sitting right after an opening bracket, e.g. "[London]", "[Wien],".
BRACKET_KNOWN_RE = re.compile(rf"\[({_loc_pattern})\b")
# Two-letter uppercase token, e.g. a US state code trailing "City, ST".
_US_STATE_RE = re.compile(r"^[A-Z]{2}$")

# Imprint place qualifiers. A header such as "Inko, Tyresö, Sweden" or "Ariadne
# Press, Riverside, CA" ends in a segment that qualifies the place before it;
# lib/editions.split_imprint reads such a trailing segment as part of the place,
# never as the place itself. Only the fixed lists below qualify, so an unknown
# trailing segment keeps its old reading and its review flag.
#
# United States Postal Service, Publication 28, Appendix B: the two-letter state,
# district and territory abbreviations, and the state names. "New York" and
# "Washington" are left out of the names because the corpus uses both as the
# city of publication ("Longmans, Green & Company, New York").
US_POSTAL_CODES = frozenset(
    """AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN
    MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI
    WY AS GU MP PR VI""".split()
)
US_STATE_NAMES = frozenset(
    {
        "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
        "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
        "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine",
        "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi",
        "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey",
        "New Mexico", "North Carolina", "North Dakota", "Ohio", "Oklahoma",
        "Oregon", "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
        "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "West Virginia",
        "Wisconsin", "Wyoming",
    }
)  # fmt: skip
# Canada Post: the two-letter province and territory symbols.
CA_POSTAL_CODES = frozenset("AB BC MB NB NL NS NT NU ON PE QC SK YT".split())
# ISO 3166-2:BR: the two-letter codes of the Brazilian federative units
# ("L&PM, Porto Alegre, RS" on page 3556).
BR_STATE_CODES = frozenset(
    """AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC
    SP SE TO""".split()
)
# Country names of the Natural Earth 1:110m country layer, exactly as vendored in
# docs/vendor/countries-110m.json (world-atlas 2); tests/test_publications.py
# asserts this list equals the names in that file.
NATURAL_EARTH_COUNTRY_NAMES = frozenset(
    {
        'Afghanistan', 'Albania', 'Algeria', 'Angola', 'Antarctica', 'Argentina',
        'Armenia', 'Australia', 'Austria', 'Azerbaijan', 'Bahamas', 'Bangladesh',
        'Belarus', 'Belgium', 'Belize', 'Benin', 'Bhutan', 'Bolivia',
        'Bosnia and Herz.', 'Botswana', 'Brazil', 'Brunei', 'Bulgaria',
        'Burkina Faso', 'Burundi', 'Cambodia', 'Cameroon', 'Canada',
        'Central African Rep.', 'Chad', 'Chile', 'China', 'Colombia', 'Congo',
        'Costa Rica', 'Croatia', 'Cuba', 'Cyprus', 'Czechia', "Côte d'Ivoire",
        'Dem. Rep. Congo', 'Denmark', 'Djibouti', 'Dominican Rep.', 'Ecuador',
        'Egypt', 'El Salvador', 'Eq. Guinea', 'Eritrea', 'Estonia', 'Ethiopia',
        'Falkland Is.', 'Fiji', 'Finland', 'Fr. S. Antarctic Lands', 'France',
        'Gabon', 'Gambia', 'Georgia', 'Germany', 'Ghana', 'Greece', 'Greenland',
        'Guatemala', 'Guinea', 'Guinea-Bissau', 'Guyana', 'Haiti', 'Honduras',
        'Hungary', 'Iceland', 'India', 'Indonesia', 'Iran', 'Iraq', 'Ireland',
        'Israel', 'Italy', 'Jamaica', 'Japan', 'Jordan', 'Kazakhstan', 'Kenya',
        'Kosovo', 'Kuwait', 'Kyrgyzstan', 'Laos', 'Latvia', 'Lebanon', 'Lesotho',
        'Liberia', 'Libya', 'Lithuania', 'Luxembourg', 'Macedonia', 'Madagascar',
        'Malawi', 'Malaysia', 'Mali', 'Mauritania', 'Mexico', 'Moldova',
        'Mongolia', 'Montenegro', 'Morocco', 'Mozambique', 'Myanmar', 'N. Cyprus',
        'Namibia', 'Nepal', 'Netherlands', 'New Caledonia', 'New Zealand',
        'Nicaragua', 'Niger', 'Nigeria', 'North Korea', 'Norway', 'Oman',
        'Pakistan', 'Palestine', 'Panama', 'Papua New Guinea', 'Paraguay', 'Peru',
        'Philippines', 'Poland', 'Portugal', 'Puerto Rico', 'Qatar', 'Romania',
        'Russia', 'Rwanda', 'S. Sudan', 'Saudi Arabia', 'Senegal', 'Serbia',
        'Sierra Leone', 'Slovakia', 'Slovenia', 'Solomon Is.', 'Somalia',
        'Somaliland', 'South Africa', 'South Korea', 'Spain', 'Sri Lanka', 'Sudan',
        'Suriname', 'Sweden', 'Switzerland', 'Syria', 'Taiwan', 'Tajikistan',
        'Tanzania', 'Thailand', 'Timor-Leste', 'Togo', 'Trinidad and Tobago',
        'Tunisia', 'Turkey', 'Turkmenistan', 'Uganda', 'Ukraine',
        'United Arab Emirates', 'United Kingdom', 'United States of America',
        'Uruguay', 'Uzbekistan', 'Vanuatu', 'Venezuela', 'Vietnam', 'W. Sahara',
        'Yemen', 'Zambia', 'Zimbabwe', 'eSwatini',
    }
)  # fmt: skip
# State and region names the source headers use as a trailing qualifier that the
# lists above lack, each with the page whose header attests it.
SOURCE_REGION_NAMES = {
    "Bayern": 34,
    "Bosnia": 1855,
    "Brasil": 4429,
    "Czech Republic": 34,
    "Czechoslovakia": 4477,
    "England": 886,
    "Faeroe Islands": 374,
    "Kerala": 5829,
    "New South Wales": 4689,
    "República Argentina": 2087,
    "USA": 2294,
}
# "D.F." is the Mexican Distrito Federal ("Editorial Diana, México, D.F.", page
# 2524); the source writes it with and without the inner space.
_FEDERAL_DISTRICT = frozenset({"D.F.", "D. F."})
PLACE_QUALIFIERS = (
    US_POSTAL_CODES
    | US_STATE_NAMES
    | CA_POSTAL_CODES
    | BR_STATE_CODES
    | NATURAL_EARTH_COUNTRY_NAMES
    | frozenset(SOURCE_REGION_NAMES)
    | _FEDERAL_DISTRICT
)
# Country and region names can stand alone as a film's country of production
# ("'''[1991]: Germany'''", page 4630); postal codes never do.
PLACE_NAMES_STANDING_ALONE = NATURAL_EARTH_COUNTRY_NAMES | frozenset(
    SOURCE_REGION_NAMES
)
# Legal-form and designation segments that belong to the publisher name before
# them ("Pocket Books, Inc., New York", page 890), each attested in a header.
CORPORATE_SUFFIXES = frozenset(
    {
        "Inc.",  # 890
        "Ltd.",  # 502
        "Ltda.",  # 3058
        "S. A.",  # 217
        "S. A. U.",  # 2873
        "S. L.",  # 3668
        "s.l.u.",  # 2893
        "S. R. L.",  # 5008
        "S. r. o.",  # 3612
        "SIA",  # 854
        "Éditeurs",  # 672
        "Editeur",  # 6667
    }
)
# Sine loco / sine nomine: the cataloguing marks for a place or publisher the
# item does not state ("[s.n.], [s.l.]", page 4269). They record an absence.
ABSENCE_MARKS = frozenset({"[s.l.]", "s.l.", "[s.n.]", "s.n."})

# Page count patterns
# Note: pp. N-M is a page RANGE (start-end), not a page count.
# Pattern 2 requires the number to NOT be followed by a hyphen+digit (range).
# The \b after \d+ prevents backtracking from shortening the number match.
PAGE_COUNT_PATTERNS = [
    re.compile(
        r"(\d{1,5})\s*(?:pp?\.|pages?|Seiten|S\.)", re.IGNORECASE
    ),  # 500p. (standard)
    re.compile(r"(\d{1,5})/\(\d+\)\s*p\.", re.IGNORECASE),  # 253/(2)p. notation
    re.compile(
        r"pp?\.\s*(\d{1,5})\b(?!\s*[-–—]\s*[\d(])", re.IGNORECASE
    ),  # pp. 153 (NOT pp. 7-(19))
    re.compile(r"(\d{1,5})\s*p\b"),  # 38p
]

# These labels introduce citation locators, including a single referenced page.
_PAGE_LOCATOR_LABEL_RE = re.compile(
    r"\b(?:Zweig\s+references?|references?|annotations?|commentary|notes?)"
    r"(?:\s+\d+)?\s*,\s*(?:pp?\.\s*[^\n]*,\s*)?$",
    re.IGNORECASE,
)

# Translator patterns — only match explicit "Translated by Name" patterns.
# Unicode letters preserve names; initials and abbreviated name parts keep periods.
_NAME_LETTER = r"[^\W\d_]"
_NAME_WORD = rf"[’']?{_NAME_LETTER}(?:{_NAME_LETTER}|[\u0300-\u036f’-]|'(?!'))*"
_NAME_INITIALS = (
    rf"(?:(?:{_NAME_LETTER}[’']?\.)+|"
    rf"(?:St|Ep|An|Ch|Th|Ce)\.(?=[ \t]+{_NAME_LETTER}))"
)
_NAME_TOKEN = rf"(?:{_NAME_INITIALS}|{_NAME_WORD})"
_TRANSLATOR_NAME = rf"({_NAME_TOKEN}(?:[ \t]+{_NAME_TOKEN})*)"
_TRANSLATOR_NAME_RE = re.compile(_TRANSLATOR_NAME)
# The permissive form the credit selection has always used; it overruns into
# the following sentence, so credited_name repairs it with the name grammar.
_LOOSE_CREDIT_NAME_RE = re.compile(r"([A-Z][a-zA-ZÀ-ÿ \t.\'-]{2,60})")
# Keep the existing credit selection; repair only the name at that same anchor.
TRANSLATOR_PATTERNS = [
    re.compile(prefix + r"([A-Z][a-zA-ZÀ-ÿ \t.\'-]{2,60})")
    for prefix in (
        r"[Tt]ranslated\s+by\s+",
        r"[Tt]ranslation\s+by\s+",
        r"[Üü]bersetzt\s+von\s+",
        r"[Üü]bertragen\s+von\s+",
        r"[Tt]raduit\s+par\s+",
        r"[Tt]raducción\s+(?:de|por)\s+",
        r"[Tt]raduzione\s+di\s+",
        r"[Tt]rans\.\s+",
    )
]
_TRANSLATOR_NOTE_RE = re.compile(
    r"\s+(?:from|into)\s+|\s+in$|"
    r"(?<=\.)\s+(?=Cover\b|Edited\b|Illustrated\b|Foreword\b|Preface\b|Afterword\b)"
)

# Page range patterns (shared by verify.py and 03b_llm_enrich.py)
# N/(M)p. — numbered + unnumbered pages (e.g. 285/(3)p. → 288 total)
PARENS_PAGE_RE = re.compile(r"(\d+)/\((\d+)\)\s*p", re.IGNORECASE)
# pp. (X)-Y or pp. X-Y — page range
PAGE_RANGE_RE = re.compile(r"pp?\.\s*\(?(\d+)\)?[-–](\d+)")

# Language detection from category names
CATEGORY_LANGUAGE_RE = re.compile(r"\(([\w-]+)\)\s*$")


def extract_year(text):
    """Extract the most likely publication year from text."""
    if not text:
        return None
    matches = YEAR_RE.findall(text)
    if not matches:
        return None
    # Prefer years near the beginning of the text
    years = [int(y) for y in matches]
    # Filter out obviously wrong years (page numbers, etc.)
    valid = [y for y in years if MIN_VALID_YEAR <= y <= MAX_VALID_YEAR]
    return valid[0] if valid else None


def extract_all_years(text):
    """Extract all years from text."""
    if not text:
        return []
    matches = YEAR_RE.findall(text)
    return sorted(
        set(int(y) for y in matches if MIN_VALID_YEAR <= int(y) <= MAX_VALID_YEAR)
    )


# Phrases that are metadata, not publisher names
_PUBLISHER_REJECT = [
    "comments concerning",
    "staff of the",
    "see also",
    "contents",
]

# A contribution credit is never an imprint. The third publisher pattern ends
# on words such as "Edition", which matches the word inside a credit sentence
# ("Translated by X. 1st edition"); this predicate refuses that reading.
_CONTRIBUTION_CREDIT_RE = re.compile(
    r"\b(?:translat\w+|edited|editing|illustrated|compiled|selected|adapted"
    r"|revised|arranged)\b.{0,40}?\bby\b",
    re.IGNORECASE | re.DOTALL,
)


def names_a_contribution_credit(value):
    """Whether a candidate value states who translated, edited or illustrated."""
    return bool(value and _CONTRIBUTION_CREDIT_RE.search(value))


def extract_publisher(text):
    """Extract publisher name from text."""
    if not text:
        return None
    for pattern in PUBLISHER_PATTERNS:
        m = pattern.search(text)
        if m:
            pub = m.group(1).strip().rstrip(".,;:")
            # Clean wiki markup from publisher
            pub = re.sub(r"'{2,3}", "", pub).strip()
            if len(pub) < 3:
                continue
            # Reject metadata phrases
            if any(p in pub.lower() for p in _PUBLISHER_REJECT):
                continue
            if names_a_contribution_credit(pub):
                continue
            return pub
    return None


def _clean_location(value):
    """Strip bold markup, reduce a 'Primary [Alternate]' form to the primary
    name, and trim brackets and trailing punctuation from a location token."""
    value = re.sub(r"'{2,3}", "", value).strip()
    value = re.split(r"\s*\[", value, maxsplit=1)[0]
    return value.strip().strip("[]").strip().rstrip(".,;:").strip()


def _location_from_header(header):
    """Pick the location out of a publication-line header body (the text after
    '[YEAR]:'). The location is the segment after the last comma; a trailing US
    state code falls back to the city segment before it. A known city is
    preferred where the tail contains one, otherwise the literal source token is
    kept so non-Western places absent from the known list are still recovered."""
    parts = [p.strip() for p in header.split(",") if p.strip()]
    if len(parts) >= 2:
        tail = _clean_location(parts[-1])
        if _US_STATE_RE.match(tail) and len(parts) >= 3:
            tail = _clean_location(parts[-2])
        m = LOCATION_RE.search(tail)
        if m:
            return m.group(1).strip("[]")
        if tail and 2 <= len(tail) <= 40 and not re.search(r"\d", tail):
            return tail
    m = LOCATION_RE.search(header)
    if m:
        return m.group(1).strip("[]")
    return None


def extract_location(text):
    """Extract the publication location, preferring the publication line.

    Reads the bold '''[YEAR]: Publisher, Location''' header first, so a city in a
    chapter title cannot be taken as the place of publication. Headerless entries
    (excerpts, reviews, secondary literature) prefer a bracketed place, a
    [City, year] or [KnownCity] reference, and only fall back to a whole-text
    known-city search when no bracketed place is present, which keeps the
    location of entries that never had a publication header."""
    if not text:
        return None
    m = PUBLICATION_LINE_RE.search(text)
    if m:
        loc = _location_from_header(m.group(1))
        if loc:
            return loc
        # Header present but carries no location: fall through to body heuristics.
    # A bracketed known city (the original journal's place, e.g. "[Berlin]") is
    # preferred over a [City, year] reprint reference, so an article keeps its
    # first place of publication rather than the city of a later anthology.
    bk = BRACKET_KNOWN_RE.search(text)
    if bk:
        return bk.group(1)
    bm = BRACKET_PLACE_RE.search(text)
    if bm:
        cleaned = _clean_location(bm.group(1))
        if cleaned:
            return cleaned
    m2 = LOCATION_RE.search(text)
    if m2:
        return m2.group(1).strip("[]")
    return None


def extract_all_locations(text):
    """Extract all locations mentioned in text."""
    if not text:
        return []
    return list(
        dict.fromkeys(m.group(1).strip("[]") for m in LOCATION_RE.finditer(text))
    )


def extract_page_count(text):
    """Extract page count from text."""
    if not text:
        return None
    for pattern in PAGE_COUNT_PATTERNS:
        m = pattern.search(text)
        if m:
            if re.match(r"pp?\.", m.group(0), re.IGNORECASE):
                before = text[text.rfind("\n", 0, m.start()) + 1 : m.start()]
                after = text[m.end() :]
                if _PAGE_LOCATOR_LABEL_RE.search(before) or re.match(
                    r"\s*[,;]\s*\(?\d+\b", after
                ):
                    continue
            count = int(m.group(1))
            if 1 <= count <= 10000:
                return count
    return None


def credited_name(text, start):
    """Read the person name credited at ``start``, the position after a 'by'.

    Shared by the flat translator scalar and the publication-scoped credit
    layer, so both read one name grammar. Returns None where no name stands at
    that anchor.
    """
    loose = _LOOSE_CREDIT_NAME_RE.match(text, start)
    if not loose:
        return None
    legacy_name = loose.group(1).strip().rstrip(".,;:")
    legacy_name = re.sub(r"\s*'''.*$", "", legacy_name)
    legacy_name = legacy_name.strip().rstrip(".,;:")
    if len(legacy_name) < 3:
        return None
    name_match = _TRANSLATOR_NAME_RE.match(text, start)
    if name_match:
        # A stray period before an initial can be internal name punctuation.
        if re.match(r"\.[ \t]+[A-Z]\.", text[name_match.end() :]):
            return legacy_name
        name = _TRANSLATOR_NOTE_RE.split(name_match.group(1), maxsplit=1)[0]
        name = name.strip()
        if len(name) >= 3:
            return name
    return legacy_name


def extract_translator(text):
    """Extract a credit's name; this compatibility scalar does not resolve scope."""
    if not text:
        return None
    for pattern in TRANSLATOR_PATTERNS:
        m = pattern.search(text)
        if m:
            name = credited_name(text, m.start(1))
            if name:
                return name
    return None


def extract_language_from_category(categories):
    """Infer language from category names like 'Poetry / Individual Poems (German)'."""
    if not categories:
        return None
    missing_language = None
    for cat in categories:
        m = CATEGORY_LANGUAGE_RE.search(cat)
        if m:
            lang = m.group(1)
            # Fill gaps without changing an existing multilingual scalar choice.
            if lang in ("Serbo-Croatian", "Estonian", "Afrikaans"):
                missing_language = missing_language or lang
            # Common language names in categories
            if lang in (
                "German",
                "English",
                "French",
                "Spanish",
                "Italian",
                "Portuguese",
                "Russian",
                "Chinese",
                "Japanese",
                "Arabic",
                "Hebrew",
                "Hindi",
                "Turkish",
                "Polish",
                "Czech",
                "Dutch",
                "Swedish",
                "Danish",
                "Norwegian",
                "Finnish",
                "Hungarian",
                "Romanian",
                "Greek",
                "Korean",
                "Serbian",
                "Croatian",
                "Bulgarian",
                "Slovak",
                "Slovenian",
                "Albanian",
                "Georgian",
                "Armenian",
                "Catalan",
                "Persian",
                "Urdu",
                "Bengali",
                "Thai",
                "Vietnamese",
                "Indonesian",
                "Ukrainian",
                "Yiddish",
                "Esperanto",
                "Latin",
            ):
                return lang
    return missing_language

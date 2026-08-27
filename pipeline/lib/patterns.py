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

# Translator patterns — only match explicit "Translated by Name" patterns.
# The last pattern (Tr./Trans.) was too greedy and matched word fragments.
TRANSLATOR_PATTERNS = [
    re.compile(r"[Tt]ranslated\s+by\s+([A-Z][a-zA-ZÀ-ÿ \t.\'-]{2,60})", re.UNICODE),
    re.compile(r"[Tt]ranslation\s+by\s+([A-Z][a-zA-ZÀ-ÿ \t.\'-]{2,60})", re.UNICODE),
    re.compile(r"[Üü]bersetzt\s+von\s+([A-Z][a-zA-ZÀ-ÿ \t.\'-]{2,60})", re.UNICODE),
    re.compile(r"[Üü]bertragen\s+von\s+([A-Z][a-zA-ZÀ-ÿ \t.\'-]{2,60})", re.UNICODE),
    re.compile(r"[Tt]raduit\s+par\s+([A-Z][a-zA-ZÀ-ÿ \t.\'-]{2,60})", re.UNICODE),
    re.compile(
        r"[Tt]raducción\s+(?:de|por)\s+([A-Z][a-zA-ZÀ-ÿ \t.\'-]{2,60})", re.UNICODE
    ),
    re.compile(r"[Tt]raduzione\s+di\s+([A-Z][a-zA-ZÀ-ÿ \t.\'-]{2,60})", re.UNICODE),
    re.compile(r"[Tt]rans\.\s+([A-Z][a-zA-ZÀ-ÿ \t.\'-]{2,60})", re.UNICODE),
]

# Page range patterns (shared by verify.py and 03b_llm_enrich.py)
# N/(M)p. — numbered + unnumbered pages (e.g. 285/(3)p. → 288 total)
PARENS_PAGE_RE = re.compile(r"(\d+)/\((\d+)\)\s*p", re.IGNORECASE)
# pp. (X)-Y or pp. X-Y — page range
PAGE_RANGE_RE = re.compile(r"pp?\.\s*\(?(\d+)\)?[-–](\d+)")

# Language detection from category names
CATEGORY_LANGUAGE_RE = re.compile(r"\((\w+)\)\s*$")


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
            count = int(m.group(1))
            if 1 <= count <= 10000:
                return count
    return None


def extract_translator(text):
    """Extract translator name from text."""
    if not text:
        return None
    for pattern in TRANSLATOR_PATTERNS:
        m = pattern.search(text)
        if m:
            name = m.group(1).strip().rstrip(".,;:")
            # Remove trailing wiki markup that leaked into the name
            name = re.sub(r"\s*'''.*$", "", name)
            name = name.strip().rstrip(".,;:")
            if len(name) >= 3:
                return name
    return None


def extract_language_from_category(categories):
    """Infer language from category names like 'Poetry / Individual Poems (German)'."""
    if not categories:
        return None
    for cat in categories:
        m = CATEGORY_LANGUAGE_RE.search(cat)
        if m:
            lang = m.group(1)
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
    return None

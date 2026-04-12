"""
Regex patterns for extracting bibliographic metadata from Klawiter entries.
"""

import re

from lib.config import MIN_VALID_YEAR, MAX_VALID_YEAR

# Year patterns
YEAR_RE = re.compile(r'\b(1[789]\d{2}|20[0-3]\d)\b')

# Publisher patterns (expanded beyond the original 3)
PUBLISHER_PATTERNS = [
    # Explicit labels
    re.compile(r'(?:Verlag|Publisher|Press|Publishing|Éditions?|Editore|Editorial|Editora|Wydawnictwo|Издательство)[\s:]+([^\n,.;()\[\]]{3,80})', re.IGNORECASE),
    # "published by" variants
    re.compile(r'(?:published by|verlegt bei|herausgegeben von|édité par|publicado por)\s+([^\n,.;()\[\]]{3,80})', re.IGNORECASE),
    # Known publisher name patterns (ends with Verlag, Press, etc.)
    re.compile(r'\b([\w\s&.-]{2,60}(?:Verlag|Press|Publishers?|Books|Edition|Éditions?|Editore|House))\b', re.IGNORECASE),
]

# Location patterns — cities commonly found in the bibliography
KNOWN_LOCATIONS = [
    "Wien", "Vienna", "Berlin", "Frankfurt", "Frankfurt am Main", "Leipzig",
    "London", "New York", "Paris", "Zurich", "Zürich", "Hamburg", "Munich",
    "München", "Salzburg", "Stockholm", "Amsterdam", "Bern", "Basel",
    "Prague", "Prag", "Praha", "Budapest", "Warsaw", "Warszawa",
    "Moscow", "Moskau", "Москва", "St. Petersburg",
    "Rome", "Roma", "Milan", "Milano", "Madrid", "Barcelona",
    "Lisbon", "Lisboa", "Buenos Aires", "Rio de Janeiro", "São Paulo",
    "Tokyo", "Tōkyō", "Beijing", "Shanghai", "Taipei",
    "Delhi", "New Delhi", "Mumbai", "Bombay", "Calcutta", "Kolkata",
    "Cairo", "Beirut", "Istanbul", "Tel Aviv", "Jerusalem",
    "Bucharest", "București", "Sofia", "Belgrade", "Beograd",
    "Zagreb", "Ljubljana", "Bratislava", "Vilnius", "Riga", "Tallinn",
    "Helsinki", "Oslo", "Copenhagen", "København",
    "Mexico City", "México", "Bogotá", "Santiago", "Lima", "Havana",
    "Sydney", "Melbourne", "Toronto", "Montreal", "Montréal",
    "Krems", "Krems an der Donau", "Graz", "Innsbruck", "Linz",
    "Wiesbaden", "Stuttgart", "Köln", "Cologne", "Düsseldorf", "Dresden",
    "Weimar", "Jena", "Göttingen", "Heidelberg", "Tübingen", "Freiburg",
    "Darmstadt", "Bonn", "Marburg", "Mainz", "Braunschweig",
]

# Build a regex for location detection (sorted by length descending to match longer names first)
_loc_sorted = sorted(KNOWN_LOCATIONS, key=len, reverse=True)
_loc_pattern = '|'.join(re.escape(loc) for loc in _loc_sorted)
LOCATION_RE = re.compile(rf'\[?\b({_loc_pattern})\b\]?')

# Page count patterns
# Note: pp. N-M is a page RANGE (start-end), not a page count.
# Pattern 2 requires the number to NOT be followed by a hyphen+digit (range).
# The \b after \d+ prevents backtracking from shortening the number match.
PAGE_COUNT_PATTERNS = [
    re.compile(r'(\d{1,5})\s*(?:pp?\.|pages?|Seiten|S\.)', re.IGNORECASE),
    re.compile(r'pp?\.\s*(\d{1,5})\b(?!\s*[-–—]\s*\d)', re.IGNORECASE),
    re.compile(r'(\d{1,5})\s*p\b'),
]

# Translator patterns — only match explicit "Translated by Name" patterns.
# The last pattern (Tr./Trans.) was too greedy and matched word fragments.
TRANSLATOR_PATTERNS = [
    re.compile(r'[Tt]ranslated\s+by\s+([A-Z][a-zA-ZÀ-ÿ \t.\'-]{2,60})', re.UNICODE),
    re.compile(r'[Tt]ranslation\s+by\s+([A-Z][a-zA-ZÀ-ÿ \t.\'-]{2,60})', re.UNICODE),
    re.compile(r'[Üü]bersetzt\s+von\s+([A-Z][a-zA-ZÀ-ÿ \t.\'-]{2,60})', re.UNICODE),
    re.compile(r'[Üü]bertragen\s+von\s+([A-Z][a-zA-ZÀ-ÿ \t.\'-]{2,60})', re.UNICODE),
    re.compile(r'[Tt]raduit\s+par\s+([A-Z][a-zA-ZÀ-ÿ \t.\'-]{2,60})', re.UNICODE),
    re.compile(r'[Tt]raducción\s+(?:de|por)\s+([A-Z][a-zA-ZÀ-ÿ \t.\'-]{2,60})', re.UNICODE),
    re.compile(r'[Tt]raduzione\s+di\s+([A-Z][a-zA-ZÀ-ÿ \t.\'-]{2,60})', re.UNICODE),
    re.compile(r'[Tt]rans\.\s+([A-Z][a-zA-ZÀ-ÿ \t.\'-]{2,60})', re.UNICODE),
]

# Page range patterns (shared by verify.py and 03b_llm_enrich.py)
# N/(M)p. — numbered + unnumbered pages (e.g. 285/(3)p. → 288 total)
PARENS_PAGE_RE = re.compile(r'(\d+)/\((\d+)\)\s*p', re.IGNORECASE)
# pp. (X)-Y or pp. X-Y — page range
PAGE_RANGE_RE = re.compile(r'pp?\.\s*\(?(\d+)\)?[-–](\d+)')

# Language detection from category names
CATEGORY_LANGUAGE_RE = re.compile(r'\((\w+)\)\s*$')


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
    return sorted(set(int(y) for y in matches if MIN_VALID_YEAR <= int(y) <= MAX_VALID_YEAR))


def extract_publisher(text):
    """Extract publisher name from text."""
    if not text:
        return None
    for pattern in PUBLISHER_PATTERNS:
        m = pattern.search(text)
        if m:
            pub = m.group(1).strip().rstrip('.,;:')
            if len(pub) >= 3:
                return pub
    return None


def extract_location(text):
    """Extract publication location from text."""
    if not text:
        return None
    m = LOCATION_RE.search(text)
    if m:
        return m.group(1).strip('[]')
    return None


def extract_all_locations(text):
    """Extract all locations mentioned in text."""
    if not text:
        return []
    return list(dict.fromkeys(m.group(1).strip('[]') for m in LOCATION_RE.finditer(text)))


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
            name = m.group(1).strip().rstrip('.,;:')
            # Remove trailing wiki markup that leaked into the name
            name = re.sub(r"\s*'''.*$", '', name)
            name = name.strip().rstrip('.,;:')
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
            if lang in ("German", "English", "French", "Spanish", "Italian",
                       "Portuguese", "Russian", "Chinese", "Japanese", "Arabic",
                       "Hebrew", "Hindi", "Turkish", "Polish", "Czech", "Dutch",
                       "Swedish", "Danish", "Norwegian", "Finnish", "Hungarian",
                       "Romanian", "Greek", "Korean", "Serbian", "Croatian",
                       "Bulgarian", "Slovak", "Slovenian", "Albanian", "Georgian",
                       "Armenian", "Catalan", "Persian", "Urdu", "Bengali",
                       "Thai", "Vietnamese", "Indonesian", "Ukrainian", "Yiddish",
                       "Esperanto", "Latin"):
                return lang
    return None

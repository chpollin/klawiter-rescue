"""
Encoding utilities for fixing Mojibake and normalizing text.
Handles the common case where UTF-8 bytes were misinterpreted as Latin-1/CP1252.
"""

import re
import unicodedata

# HTML entities that may appear in wiki content
HTML_ENTITIES = {
    "&nbsp;": " ",
    "&mdash;": "—",
    "&ndash;": "–",
    "&amp;": "&",
    "&lt;": "<",
    "&gt;": ">",
    "&quot;": '"',
    "&apos;": "'",
    "&#39;": "'",
    "&#34;": '"',
}

# Regex to detect any Ã+continuation-byte sequence (the universal Mojibake signature)
_MOJIBAKE_RE = re.compile(r'Ã[\x80-\xbf]|Â[\xa0-\xff]|Ã[\x80-\x9f]')


def fix_mojibake(text):
    """Fix UTF-8 bytes misinterpreted as Latin-1/CP1252.

    Strategy: encode the entire string as latin-1, then decode as utf-8.
    This reverses the original corruption. We apply it per-line to limit
    blast radius — if a line fails, we keep the original.
    """
    if not text:
        return text

    if not _MOJIBAKE_RE.search(text):
        return text  # No Mojibake detected, skip

    # Process line by line to avoid corrupting clean lines
    lines = text.split('\n')
    fixed_lines = []
    for line in lines:
        if _MOJIBAKE_RE.search(line):
            try:
                fixed = line.encode('latin-1').decode('utf-8')
                fixed_lines.append(fixed)
            except (UnicodeDecodeError, UnicodeEncodeError):
                # Line has mixed encoding or non-latin-1 chars — keep original
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)

    result = '\n'.join(fixed_lines)
    return unicodedata.normalize('NFC', result)


def fix_html_entities(text):
    """Replace HTML entities with their Unicode equivalents."""
    if not text:
        return text
    result = text
    for entity, char in HTML_ENTITIES.items():
        result = result.replace(entity, char)
    # Numeric entities
    result = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), result)
    result = re.sub(r'&#x([0-9a-fA-F]+);', lambda m: chr(int(m.group(1), 16)), result)
    return result


def fix_encoding(text):
    """Apply all encoding fixes in order."""
    if not text:
        return text
    text = fix_mojibake(text)
    text = fix_html_entities(text)
    return text


def has_mojibake(text):
    """Detect whether text contains likely Mojibake patterns."""
    if not text:
        return False
    return bool(_MOJIBAKE_RE.search(text))


# --- Comparison utilities (used by verify.py) ---

# Common mojibake substitution pairs for encoding-aware comparison
ENCODING_PAIRS = [
    ('ä', 'Ã¤'), ('ö', 'Ã¶'), ('ü', 'Ã¼'), ('ß', 'Ã\x9f'),
    ('é', 'Ã©'), ('è', 'Ã¨'), ('ê', 'Ãª'), ('ë', 'Ã«'),
    ('á', 'Ã¡'), ('à', 'Ã '), ('â', 'Ã¢'), ('ã', 'Ã£'),
    ('ó', 'Ã³'), ('ò', 'Ã²'), ('ô', 'Ã´'), ('õ', 'Ãµ'),
    ('ú', 'Ãº'), ('ù', 'Ã¹'), ('û', 'Ã»'),
    ('ñ', 'Ã±'), ('ø', 'Ã¸'), ('å', 'Ã¥'), ('æ', 'Ã¦'),
    ('ş', 'Å\x9f'), ('ţ', 'Å£'), ('ă', 'Ä'), ('ē', 'Ä'),
    ('š', 'Å¡'), ('č', 'Ä\x8d'), ('ž', 'Å¾'), ('ř', 'Å\x99'),
    ('ī', 'Ä«'), ('ū', 'Å«'),
    ("'", 'â'), ("'", 'â'),
]


def normalize_text(text):
    """Normalize text for comparison: lowercase, collapse whitespace."""
    if not text:
        return ''
    return ' '.join(str(text).lower().split())


def strip_encoding_artifacts(text):
    """Strip common mojibake artifacts for looser comparison."""
    if not text:
        return ''
    result = text
    for clean, garbled in ENCODING_PAIRS:
        result = result.replace(garbled, clean)
    result = re.sub(r'[\u0300-\u036f]', '', result)
    return result

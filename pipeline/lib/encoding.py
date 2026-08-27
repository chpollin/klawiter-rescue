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

# UTF-8 multibyte data decoded as Latin-1 leaves a run of one lead char
# (U+00C2..U+00F4, the Latin-1 view of a UTF-8 lead byte) followed by one or
# more continuation chars (U+0080..U+00BF). This is the universal mojibake
# signature; it does not occur in clean NFC text, where a Latin letter is
# followed by an ASCII letter or space, not a C1 control or Latin-1 symbol.
# Matching whole runs lets one pass repair 2-, 3- and 4-byte sequences alike
# (umlauts, the Latin Extended-A diacritics of transliterated titles, and
# double-encoded smart quotes).
_MOJIBAKE_RE = re.compile("[\u00c2-\u00f4][\u0080-\u00bf]+")


def _redecode_run(match):
    """Reverse one mojibake run: re-encode as Latin-1, decode as UTF-8.

    Self-validating. The run consists only of U+0080..U+00F4, so the Latin-1
    re-encode never fails; if the bytes are not valid UTF-8 the decode raises
    and the original run is kept, so an accidental match on clean text (a
    Latin letter that happens to precede a Latin-1 symbol) is left untouched.
    A result that still carries a C1 control is rejected for the same reason.
    """
    run = match.group(0)
    try:
        fixed = run.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return run
    if any("\u0080" <= c <= "\u009f" for c in fixed):
        return run
    return fixed


def fix_mojibake(text):
    """Fix UTF-8 bytes misinterpreted as Latin-1/CP1252.

    Repairs each mojibake run independently rather than re-decoding whole
    lines, so clean characters on the same line are preserved and the repair
    is idempotent (a repaired character is no longer in the lead-byte range).
    """
    if not text:
        return text
    if not _MOJIBAKE_RE.search(text):
        return text  # No Mojibake detected, skip
    result = _MOJIBAKE_RE.sub(_redecode_run, text)
    return unicodedata.normalize("NFC", result)


# Unicode ranges of the Arabic script (Arabic, Arabic Supplement, Arabic
# Extended-A, and the presentation-form blocks). A combining mark from these
# ranges is genuine vocalization only when it sits on an Arabic base letter.
_ARABIC_SCRIPT_RANGES = (
    (0x0600, 0x06FF),
    (0x0750, 0x077F),
    (0x08A0, 0x08FF),
    (0xFB50, 0xFDFF),
    (0xFE70, 0xFEFF),
)


def _is_arabic_script(char):
    cp = ord(char)
    return any(lo <= cp <= hi for lo, hi in _ARABIC_SCRIPT_RANGES)


def _is_arabic_mark(char):
    return _is_arabic_script(char) and unicodedata.category(char) == "Mn"


def strip_orphan_arabic_marks(text):
    """Drop Arabic combining marks that have no Arabic base character.

    Source artifact: a kasra typed with an Arabic keyboard layout, where
    Shift+A produces U+0650, survives in front of a Latin capital A
    ("[<kasra>Abu Dhabi]"). Such a mark combines with nothing, renders as a
    lone diacritic and misleads language attribution of the title.

    The rule is narrow. Only a mark of Unicode category Mn from the Arabic
    script ranges is considered, and only where the base character it would
    attach to is absent or not Arabic script; intervening marks are skipped
    so a stacked sequence is judged by its real base. Vocalized Arabic text
    keeps every mark, and Latin combining diacritics (U+0300..U+036F) are out
    of range by construction.
    """
    if not text:
        return text
    if not any(_is_arabic_mark(c) for c in text):
        return text
    result = []
    base = ""  # last character that was not a combining mark
    for char in text:
        if _is_arabic_mark(char):
            if base and _is_arabic_script(base):
                result.append(char)
            continue
        if unicodedata.category(char) != "Mn":
            base = char
        result.append(char)
    return "".join(result)


def fix_html_entities(text):
    """Replace HTML entities with their Unicode equivalents."""
    if not text:
        return text
    result = text
    for entity, char in HTML_ENTITIES.items():
        result = result.replace(entity, char)
    # Numeric entities
    result = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), result)
    result = re.sub(r"&#x([0-9a-fA-F]+);", lambda m: chr(int(m.group(1), 16)), result)
    return result


def fix_encoding(text):
    """Apply all encoding fixes in order."""
    if not text:
        return text
    text = fix_mojibake(text)
    text = fix_html_entities(text)
    text = strip_orphan_arabic_marks(text)
    return text


def has_mojibake(text):
    """Detect whether text contains repairable Mojibake.

    A run that matches the byte signature but is not valid UTF-8 once
    re-encoded (a clean accented letter before a Latin-1 guillemet, e.g.
    Catalan "nació»") is not reported, so the validator does not flag
    text the repair correctly leaves untouched."""
    if not text:
        return False
    for m in _MOJIBAKE_RE.finditer(text):
        if _redecode_run(m) != m.group(0):
            return True
    return False


# --- Comparison utilities (used by verify.py) ---

# Common mojibake substitution pairs for encoding-aware comparison
ENCODING_PAIRS = [
    ("ä", "Ã¤"),
    ("ö", "Ã¶"),
    ("ü", "Ã¼"),
    ("ß", "Ã\x9f"),
    ("é", "Ã©"),
    ("è", "Ã¨"),
    ("ê", "Ãª"),
    ("ë", "Ã«"),
    ("á", "Ã¡"),
    ("à", "Ã "),
    ("â", "Ã¢"),
    ("ã", "Ã£"),
    ("ó", "Ã³"),
    ("ò", "Ã²"),
    ("ô", "Ã´"),
    ("õ", "Ãµ"),
    ("ú", "Ãº"),
    ("ù", "Ã¹"),
    ("û", "Ã»"),
    ("ñ", "Ã±"),
    ("ø", "Ã¸"),
    ("å", "Ã¥"),
    ("æ", "Ã¦"),
    ("ş", "Å\x9f"),
    ("ţ", "Å£"),
    ("ă", "Ä"),
    ("ē", "Ä"),
    ("š", "Å¡"),
    ("č", "Ä\x8d"),
    ("ž", "Å¾"),
    ("ř", "Å\x99"),
    ("ī", "Ä«"),
    ("ū", "Å«"),
    ("'", "â"),
    ("'", "â"),
]


def normalize_text(text):
    """Normalize text for comparison: lowercase, collapse whitespace."""
    if not text:
        return ""
    return " ".join(str(text).lower().split())


def strip_encoding_artifacts(text):
    """Strip common mojibake artifacts for looser comparison."""
    if not text:
        return ""
    result = text
    for clean, garbled in ENCODING_PAIRS:
        result = result.replace(garbled, clean)
    result = re.sub(r"[\u0300-\u036f]", "", result)
    return result

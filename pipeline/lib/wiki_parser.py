"""
MediaWiki markup parser for Klawiter bibliography entries.
Extracts structured data from wiki-formatted bibliography content.
"""

import re


def parse_redirect(content):
    """Extract redirect target from #REDIRECT markup."""
    m = re.match(r"#REDIRECT\s*\[\[(.+?)\]\]", content, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None


def is_redirect(content):
    """Check if content is a redirect."""
    return bool(content and content.strip().startswith("#REDIRECT"))


CATEGORY_LINK_RE = re.compile(r"\[\[Category:([^\]]+)\]\]")
# The removal steps of the delivered text, each a pattern and its replacement
# (a group number or a literal). lib/value_spans.py replays the same steps
# with offsets, so the displayed text and its map to the raw text cannot drift.
CATEGORY_STRIP = (re.compile(r"\[\[Category:[^\]]+\]\]\s*"), "")
SORTKEY_STRIP = (re.compile(r"\{\{DEFAULTSORTKEY:[^}]+\}\}\s*"), "")
MARKUP_STEPS = (
    # Wiki links: [[target|display]] → display, [[target]] → target
    (re.compile(r"\[\[([^\]|]+)\|([^\]]+)\]\]"), 2),
    (re.compile(r"\[\[([^\]]+)\]\]"), 1),
    # Orphaned wiki brackets (unmatched [[ or ]])
    (re.compile(r"\]\]"), ""),
    (re.compile(r"\[\["), ""),
    # External links: [url text] → text
    (re.compile(r"\[https?://\S+\s+([^\]]+)\]"), 1),
    (re.compile(r"\[https?://\S+\]"), ""),
    # Bold/italic: '''text''' → text, ''text'' → text
    (re.compile(r"'''(.+?)'''"), 1),
    (re.compile(r"''(.+?)''"), 1),
    # List tags: <lst type=bracket start=N> ... </lst>
    (re.compile(r"<lst[^>]*>"), ""),
    (re.compile(r"</lst>"), ""),
    # Other HTML tags
    (re.compile(r"<br\s*/?>"), "\n"),
    (re.compile(r"</?[a-zA-Z][^>]*>"), ""),
    # MediaWiki magic words
    (re.compile(r"__(?:TOC|NOTOC|FORCETOC|NOEDITSECTION)__"), ""),
    # DEFAULTSORT key
    (re.compile(r"\{\{DEFAULTSORT(?:KEY)?:[^}]*\}\}", re.IGNORECASE), ""),
    # Section headers: ==text== → text, ===text=== → text
    (re.compile(r"^={2,6}\s*(.+?)\s*={2,6}$", re.MULTILINE), 1),
    # Unpaired bold markers (start of line + any remaining)
    (re.compile(r"^'''\s*", re.MULTILINE), ""),
    (re.compile(r"'''"), ""),
    # Escaped quotes from CSV
    (re.compile(r'\\(")'), 1),
    # Normalize whitespace
    (re.compile(r"\n{3,}"), "\n\n"),
    (re.compile(r"[ \t]+"), " "),
)


def apply_step(step, text):
    """One removal step on a plain string."""
    pattern, replacement = step
    if isinstance(replacement, int):
        return pattern.sub(lambda match: match.group(replacement), text)
    return pattern.sub(lambda _match: replacement, text)


def extract_categories(content):
    """Extract all [[Category:...]] tags and return (categories_list, content_without_categories).

    A category link may carry a sort key after a pipe
    ([[Category:Fiction| 1 German]]); the sort key orders the category
    listing and is not part of the name. MediaWiki also collapses internal
    whitespace in titles, so the names match zweig_categorylinks exactly.
    """
    cats = CATEGORY_LINK_RE.findall(content)
    cleaned = apply_step(CATEGORY_STRIP, content)
    names = (category_name(c) for c in cats)
    return [n for n in names if n], cleaned.strip()


def category_name(link_body):
    """The category name of a link body, as MediaWiki stores it: the sort key
    after a pipe dropped, whitespace runs collapsed, the first letter
    uppercased."""
    name = " ".join(link_body.split("|", 1)[0].split())
    return name[:1].upper() + name[1:]


def extract_defaultsortkey(content):
    """Extract and remove {{DEFAULTSORTKEY:...}} from content."""
    m = re.search(r"\{\{DEFAULTSORTKEY:\s*(.+?)\}\}", content)
    sortkey = m.group(1).strip() if m else None
    cleaned = apply_step(SORTKEY_STRIP, content)
    return sortkey, cleaned.strip()


def remove_wiki_markup(text):
    """Remove MediaWiki formatting, preserving text content."""
    if not text:
        return text
    result = text
    for step in MARKUP_STEPS:
        result = apply_step(step, result)
    return result.strip()


def extract_title(content):
    """Extract the main title from wiki content.
    Titles are typically in '''bold''' at the start, or "quoted" at the start.

    Special case: Collected works entries use '''[year]: Publisher, Location'''
    which is NOT a title — skip these and look for the actual work title elsewhere.
    """
    found = find_title(content)
    return found[0] if found else None


def find_title(content):
    """The title of extract_title with the span of content it was read from."""
    if not content:
        return None

    # Strip leading magic words only — __TOC__ at the start is not a title,
    # but removing it mid-content would shift the first-line fallback
    magic = re.match(r"^\s*__(?:TOC|NOTOC|FORCETOC|NOEDITSECTION)__\s*\n?", content)
    rest_of_page = content[magic.end() :] if magic else content
    base = (
        (magic.end() if magic else 0) + len(rest_of_page) - len(rest_of_page.lstrip())
    )
    content = rest_of_page.strip()
    if not content:
        return None

    def at(span):
        return base + span[0], base + span[1]

    # Pattern 1: '''Bold text''' at start — but reject if it looks like [year]: Publisher
    # Bold italic ('''''X''''') is read whole, so no '' residue stays behind.
    m = re.match(r"\s*'''''(.+?)'''''|\s*'''(.+?)'''", content)
    if m:
        # A bold line directly above a list heads that list (a language, "Printed
        # in", an index group such as "Der Amokläufer" on page 513), not the page.
        if re.match(r"[ \t]*\n<lst\b", content[m.end() :]):
            return None
        group = 1 if m.group(1) is not None else 2
        bold_text = m.group(group).strip()
        # Reject: [1922]: Insel-Verlag, Leipzig (publisher/year pattern, not a title)
        if not re.match(r"\[\d{4}\]\s*:", bold_text):
            return bold_text, at(m.span(group))

    # Pattern 2: "Title" in escaped or regular quotes at start
    m = re.match(r'\s*(?:\\")?"(.+?)"', content)
    if m:
        title = m.group(1).strip()
        # Clean orphaned ]] from titles (e.g. unclosed wiki links in source)
        title = re.sub(r"\]\]", "", title).strip()
        return title, at(m.span(1))

    # Pattern 3: For collected-works entries with '''[year]: Publisher''' format,
    # look for the page_title or the first meaningful text line
    first_line_raw, _, rest = content.partition("\n")
    first_line = first_line_raw.strip()
    # A section heading ("==Essays (English)==", page 185) names a part of the
    # page, not the work.
    if re.match(r"={2,6}[^=].*={2,6}$", first_line):
        return None
    if first_line and len(first_line) < 300:
        cleaned = remove_wiki_markup(first_line)
        # Reject lines that are just category/structural markers
        if cleaned and not cleaned.startswith("[[") and not cleaned.startswith("{{"):
            # A quoted title whose container opens the next line ('"Sameeksha:
            # ...']"' \n"in ''India.Com''..."', page 6503) is a citation split
            # across lines, the shape the citation class of 03_parse_entries
            # reads when the container follows on the same line.
            if re.match(r"\s*in\b", rest, re.IGNORECASE):
                return None
            return cleaned, at((0, len(first_line_raw)))

    return None


# The title statement of a page or of its first publication block: an italic,
# bold or quoted title opening the line, followed by the bracket in which the
# source gives the original title ("''Je Joueur d'échecs'' [Schachnovelle]",
# page 675; "''Graditelji svijeta'' [Baumeister der Welt]", page 846).
# A title may hold a single apostrophe ("Je Joueur d'échecs"), never markup.
_TITLE_TEXT = r"(?:[^'\n]|'(?!'))+?"
_TITLE_WITH_BRACKET_RE = re.compile(
    rf"^\s*(?:'''''{_TITLE_TEXT}'''''|'''{_TITLE_TEXT}'''|''{_TITLE_TEXT}''"
    r"|\\?\"[^\"\n]+\\?\")"
    r"\s*\[([^\[\]\n]+)\]"
)
_HEADER_LINE_RE = re.compile(r"^\s*'''\s*\[")
# A credit the source appends inside the bracket ("[Schachnovelle. Translated
# by A'. Salykbai']", page 4779) is no part of the original title.
_BRACKET_CREDIT_RE = re.compile(
    r"\.\s+(?=(?:Translated|Translation|Übersetzt|Edited|Illustrated|Adapted|"
    r"Retold|Abridged)\b)"
)


# An editorial note in the bracket ("[This is a review of the novel Le Feu …]",
# page 5768).
_BRACKET_NOTE_RE = re.compile(
    r"(?:This|These|See|Excerpt|An excerpt|A review|Review|Individual|"
    r"Original version)\b"
)


def extract_original_title(content):
    """The original title the source brackets after the page's title statement.

    Only the first statement line counts: the page's first line, or the first
    line after a leading publication header. A bracket that opens with a digit
    states a date or a list number ("[30 November-2 December 1981]", page 971),
    not a title. A bracket elsewhere on the page belongs to a part of the work
    ("'''Tri majstora''' [Drei Meister]" in the contents of page 846) and is
    never read. None where the title statement brackets nothing.
    """
    found = find_original_title(content)
    return found[0] if found else None


def find_original_title(content):
    """The original title of extract_original_title with the span of the
    bracket content it was read from."""
    if not content:
        return None
    for line, offset in _lines_with_offsets(content):
        if not line.strip() or _HEADER_LINE_RE.match(line):
            continue
        if re.match(r"\s*__[A-Z]+__\s*$", line):
            continue
        match = _TITLE_WITH_BRACKET_RE.match(line)
        if not match:
            return None
        candidate = _BRACKET_CREDIT_RE.split(match.group(1), maxsplit=1)[0]
        candidate = remove_wiki_markup(candidate).strip().rstrip(".,;:").strip()
        if not candidate or candidate[0].isdigit() or _BRACKET_NOTE_RE.match(candidate):
            return None
        return candidate, (offset + match.start(1), offset + match.end(1))
    return None


def _lines_with_offsets(text):
    """The lines of text as str.splitlines() yields them, each with its offset."""
    offset = 0
    for chunk in text.splitlines(keepends=True):
        parts = chunk.splitlines()
        yield (parts[0] if parts else ""), offset
        offset += len(chunk)


def link_target(link):
    """The page a [[target|label]] link points to, as MediaWiki reads it.

    The label after the pipe is display text, not part of the target, and
    MediaWiki collapses whitespace runs in a title before it looks the page
    up; a reference written with a double space reaches the same page.
    """
    return " ".join(link.split("|", 1)[0].split())


def extract_see_references(content):
    """Extract '''See:''' and '''See also:''' cross-references as link targets."""
    return [ref for ref, _ in find_see_references(content)]


def find_see_references(content):
    """The references of extract_see_references, each with the span of the
    link it was read from."""
    refs = []
    # See: [[target]]
    for m in re.finditer(r"'''See(?:\s+also)?:?'''\s*\[\[([^\]]+)\]\]", content):
        ref = link_target(m.group(1))
        if ref:
            refs.append((ref, (m.start(1) - 2, m.end(1) + 2)))
    # See: [[target1]], [[target2]]
    see_block = re.search(
        r"'''See(?:\s+also)?:?'''\s*(.+?)(?:\n\n|\Z)", content, re.DOTALL
    )
    if see_block:
        known = {ref for ref, _ in refs}
        base = see_block.start(1)
        for m in re.finditer(r"\[\[([^\]]+)\]\]", see_block.group(1)):
            ref = link_target(m.group(1))
            if ref and ref not in known:
                known.add(ref)
                refs.append((ref, (base + m.start(), base + m.end())))
    return refs


# A translations block lists one bold language heading per paragraph
# ('''Bulgarian:''' ... blank line ... '''Dutch:'''); such a heading continues
# the block. Section words, edition headers ('''[1982]: ...''') and numbered
# parts end it.
_LANGUAGE_HEAD = (
    r"(?!(?:Secondary|Contents|Reprinted|Translations?\b|Excerpts|Reviews"
    r"|Part\b|Individual|Article|Collected|L\.))"
    r"[A-Z][^\W\d_]+(?:[ /-][^\W\d_]+)*(?: \([^)\n]*\))?:?'''"
)


def _wiki_section(content, pattern, inner_head=None):
    """The match of a bold-header section; group 1 holds the block body.

    The block ends at the next bold paragraph start unless that bold text
    matches inner_head, which marks a sub-heading inside the block.
    """
    stop = r"\n\n'''" if inner_head is None else rf"\n\n'''(?!{inner_head})"
    return re.search(
        pattern + rf"\s*(.+?)(?:{stop}|\n\n\[\[Category|\Z)", content, re.DOTALL
    )


def _extract_wiki_section(content, pattern, min_length=5, inner_head=None):
    """Generic extractor for bold-header wiki sections (Reprinted in, Translations, Contents)."""
    return [
        item for item, _ in _section_items(content, pattern, min_length, inner_head)
    ]


def _section_items(content, pattern, min_length=5, inner_head=None):
    """The items of a bold-header section, each with the span of its line."""
    items = []
    block = _wiki_section(content, pattern, inner_head)
    if block:
        offset = block.start(1)
        for raw_line in block.group(1).split("\n"):
            line = raw_line.strip()
            start = offset + len(raw_line) - len(raw_line.lstrip())
            offset += len(raw_line) + 1
            if not line or line.startswith("<") or line.startswith("</"):
                continue
            if len(line) > min_length:
                items.append((remove_wiki_markup(line), (start, start + len(line))))
    return items


# The section readers of extract_structured_data, by the field they fill.
_TRANSLATIONS_HEAD = r"'''Translations?:?'''"
# The section readers of extract_structured_data by the field they fill:
# heading pattern, minimum item length, sub-heading pattern.
SECTION_READERS = {
    "reprints": (r"'''Reprinted in:?'''", 10, None),
    "translations": (_TRANSLATIONS_HEAD, 5, _LANGUAGE_HEAD),
    "content_items": (r"'''Contents:?'''", 3, None),
}


def section_item_spans(content):
    """The items of the reprint, translation and contents sections of
    content, each with the span of its line, by field."""
    return {
        field: _section_items(content, *reader)
        for field, reader in SECTION_READERS.items()
    }


def extract_reprints(content):
    """Extract '''Reprinted in:''' references."""
    return _extract_wiki_section(content, *SECTION_READERS["reprints"])


def extract_translations_block(content):
    """Extract '''Translations:''' or '''Translation:''' block."""
    return _extract_wiki_section(content, *SECTION_READERS["translations"])


def blank_translations_block(content):
    """The content with the translations section blanked in place.

    The section is the one extract_translations_block reads; its credits
    belong to the translations it lists. Blanking keeps every offset.
    """
    block = _wiki_section(content or "", _TRANSLATIONS_HEAD, _LANGUAGE_HEAD)
    if not block:
        return content
    start, end = block.start(), block.end(1)
    return content[:start] + " " * (end - start) + content[end:]


def extract_contents_block(content):
    """Extract '''Contents''' section (for collected works)."""
    return _extract_wiki_section(content, *SECTION_READERS["content_items"])


def extract_structured_data(content):
    """Parse a bibliography entry into structured components.
    Returns a dict with all extractable fields.
    """
    if not content:
        return {}

    result = {}

    # Redirect
    redirect_target = parse_redirect(content)
    if redirect_target:
        result["redirect_target"] = redirect_target
        result["is_redirect"] = True
        return result

    result["is_redirect"] = False

    # Categories
    categories, content_no_cats = extract_categories(content)
    if categories:
        result["categories"] = categories

    # Sort key
    sortkey, content_clean = extract_defaultsortkey(content_no_cats)
    if sortkey:
        result["sortkey"] = sortkey

    # Title. Text glued to a category link on its line is the tail of a broken
    # link ("[[Category:Symposia and ]]Exhibitions", page 3923), not a title.
    title = extract_title(content_clean)
    category_tails = {
        remove_wiki_markup(m.group(1))
        for m in re.finditer(r"\[\[Category:[^\]]*\]\][ \t]*([^\n]+)", content)
    }
    if title and title not in category_tails:
        result["title"] = title

    # Original title
    orig_title = extract_original_title(content_clean)
    if orig_title:
        result["original_title"] = orig_title

    # Cross-references
    see_refs = extract_see_references(content_clean)
    if see_refs:
        result["see_also"] = see_refs

    # Reprints
    reprints = extract_reprints(content_clean)
    if reprints:
        result["reprints"] = reprints

    # Translations
    translations = extract_translations_block(content_clean)
    if translations:
        result["translations"] = translations

    # Contents (collected works)
    contents = extract_contents_block(content_clean)
    if contents:
        result["content_items"] = contents

    # Clean content (markup removed)
    result["clean_content"] = remove_wiki_markup(content_clean)

    return result

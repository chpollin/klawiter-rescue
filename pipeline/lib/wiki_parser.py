"""
MediaWiki markup parser for Klawiter bibliography entries.
Extracts structured data from wiki-formatted bibliography content.
"""

import re


def parse_redirect(content):
    """Extract redirect target from #REDIRECT markup."""
    m = re.match(r'#REDIRECT\s*\[\[(.+?)\]\]', content, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None


def is_redirect(content):
    """Check if content is a redirect."""
    return bool(content and content.strip().startswith('#REDIRECT'))


def extract_categories(content):
    """Extract all [[Category:...]] tags and return (categories_list, content_without_categories)."""
    cats = re.findall(r'\[\[Category:([^\]]+)\]\]', content)
    cleaned = re.sub(r'\[\[Category:[^\]]+\]\]\s*', '', content)
    return [c.strip() for c in cats], cleaned.strip()


def extract_defaultsortkey(content):
    """Extract and remove {{DEFAULTSORTKEY:...}} from content."""
    m = re.search(r'\{\{DEFAULTSORTKEY:\s*(.+?)\}\}', content)
    sortkey = m.group(1).strip() if m else None
    cleaned = re.sub(r'\{\{DEFAULTSORTKEY:[^}]+\}\}\s*', '', content)
    return sortkey, cleaned.strip()


def remove_wiki_markup(text):
    """Remove MediaWiki formatting, preserving text content."""
    if not text:
        return text

    result = text

    # Wiki links: [[target|display]] → display, [[target]] → target
    result = re.sub(r'\[\[([^\]|]+)\|([^\]]+)\]\]', r'\2', result)
    result = re.sub(r'\[\[([^\]]+)\]\]', r'\1', result)

    # External links: [url text] → text
    result = re.sub(r'\[https?://\S+\s+([^\]]+)\]', r'\1', result)
    result = re.sub(r'\[https?://\S+\]', '', result)

    # Bold/italic: '''text''' → text, ''text'' → text
    result = re.sub(r"'''(.+?)'''", r'\1', result)
    result = re.sub(r"''(.+?)''", r'\1', result)

    # List tags: <lst type=bracket start=N> ... </lst>
    result = re.sub(r'<lst[^>]*>', '', result)
    result = re.sub(r'</lst>', '', result)

    # Other HTML tags
    result = re.sub(r'<br\s*/?>', '\n', result)
    result = re.sub(r'</?[a-zA-Z][^>]*>', '', result)

    # Escaped quotes from CSV
    result = result.replace('\\"', '"')

    # Normalize whitespace
    result = re.sub(r'\n{3,}', '\n\n', result)
    result = re.sub(r'[ \t]+', ' ', result)

    return result.strip()


def extract_title(content):
    """Extract the main title from wiki content.
    Titles are typically in '''bold''' at the start, or "quoted" at the start.

    Special case: Collected works entries use '''[year]: Publisher, Location'''
    which is NOT a title — skip these and look for the actual work title elsewhere.
    """
    if not content:
        return None

    # Pattern 1: '''Bold text''' at start — but reject if it looks like [year]: Publisher
    m = re.match(r"\s*'''(.+?)'''", content)
    if m:
        bold_text = m.group(1).strip()
        # Reject: [1922]: Insel-Verlag, Leipzig (publisher/year pattern, not a title)
        if not re.match(r'\[\d{4}\]\s*:', bold_text):
            return bold_text

    # Pattern 2: "Title" in escaped or regular quotes at start
    m = re.match(r'\s*(?:\\")?"(.+?)"', content)
    if m:
        return m.group(1).strip()

    # Pattern 3: For collected-works entries with '''[year]: Publisher''' format,
    # look for the page_title or the first meaningful text line
    first_line = content.split('\n')[0].strip()
    if first_line and len(first_line) < 300:
        cleaned = remove_wiki_markup(first_line)
        # Reject lines that are just category/structural markers
        if cleaned and not cleaned.startswith('[[') and not cleaned.startswith('{{'):
            return cleaned

    return None


def extract_original_title(content):
    """Extract original title if present (often in parentheses or brackets after main title)."""
    # Pattern: (Original Title) or [Original Title] after main title
    m = re.search(r"'''[^']+'''\s*\(([^)]+)\)", content)
    if m:
        return m.group(1).strip()
    m = re.search(r"'''[^']+'''\s*\[([^\]]+)\]", content)
    if m:
        return m.group(1).strip()
    return None


def extract_see_references(content):
    """Extract '''See:''' and '''See also:''' cross-references."""
    refs = []
    # See: [[target]]
    for m in re.finditer(r"'''See(?:\s+also)?:?'''\s*\[\[([^\]]+)\]\]", content):
        refs.append(m.group(1).strip())
    # See: [[target1]], [[target2]]
    see_block = re.search(r"'''See(?:\s+also)?:?'''\s*(.+?)(?:\n\n|\Z)", content, re.DOTALL)
    if see_block:
        for m in re.finditer(r'\[\[([^\]]+)\]\]', see_block.group(1)):
            ref = m.group(1).strip()
            if ref not in refs:
                refs.append(ref)
    return refs


def extract_reprints(content):
    """Extract '''Reprinted in:''' references."""
    reprints = []
    block = re.search(r"'''Reprinted in:?'''\s*(.+?)(?:\n\n'''|\n\n\[\[Category|\Z)", content, re.DOTALL)
    if block:
        text = block.group(1)
        # Each reprint is typically on its own line or in a <lst> block
        for line in text.split('\n'):
            line = line.strip()
            if not line or line.startswith('<') or line.startswith('</'):
                continue
            # Extract wiki links
            link_match = re.search(r'\[\[([^\]]+)\]\]', line)
            if link_match:
                reprints.append(remove_wiki_markup(line))
            elif len(line) > 10:
                reprints.append(remove_wiki_markup(line))
    return reprints


def extract_translations_block(content):
    """Extract '''Translations:''' or '''Translation:''' block."""
    translations = []
    block = re.search(r"'''Translations?:?'''\s*(.+?)(?:\n\n'''|\n\n\[\[Category|\Z)", content, re.DOTALL)
    if block:
        text = block.group(1)
        for line in text.split('\n'):
            line = line.strip()
            if not line or line.startswith('<') or line.startswith('</'):
                continue
            if len(line) > 5:
                translations.append(remove_wiki_markup(line))
    return translations


def extract_contents_block(content):
    """Extract '''Contents''' section (for collected works)."""
    items = []
    block = re.search(r"'''Contents:?'''\s*(.+?)(?:\n\n'''|\n\n\[\[Category|\Z)", content, re.DOTALL)
    if block:
        text = block.group(1)
        for line in text.split('\n'):
            line = line.strip()
            if not line or line.startswith('<') or line.startswith('</'):
                continue
            if len(line) > 3:
                items.append(remove_wiki_markup(line))
    return items


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
        result['redirect_target'] = redirect_target
        result['is_redirect'] = True
        return result

    result['is_redirect'] = False

    # Categories
    categories, content_no_cats = extract_categories(content)
    if categories:
        result['categories'] = categories

    # Sort key
    sortkey, content_clean = extract_defaultsortkey(content_no_cats)
    if sortkey:
        result['sortkey'] = sortkey

    # Title
    title = extract_title(content_clean)
    if title:
        result['title'] = title

    # Original title
    orig_title = extract_original_title(content_clean)
    if orig_title:
        result['original_title'] = orig_title

    # Cross-references
    see_refs = extract_see_references(content_clean)
    if see_refs:
        result['see_also'] = see_refs

    # Reprints
    reprints = extract_reprints(content_clean)
    if reprints:
        result['reprints'] = reprints

    # Translations
    translations = extract_translations_block(content_clean)
    if translations:
        result['translations'] = translations

    # Contents (collected works)
    contents = extract_contents_block(content_clean)
    if contents:
        result['content_items'] = contents

    # Clean content (markup removed)
    result['clean_content'] = remove_wiki_markup(content_clean)

    return result

"""What kind of wiki page a namespace-0 source page is, read by rule.

The flat holdings model one MediaWiki page as one entry, while the compiler
wrote pages of different kinds: a work hub that gathers a work's editions and
translations, an edition page of one item in one language with its
publications, and an author page indexed under a person. This module names the
kind of every namespace-0 content page from its page title, its categories and
its source text, and returns the rule that decided it with the evidence it
read. A page no rule decides is "undetermined", never a guess.

The kind belongs to the source page. It asserts no identity between pages and
no work relation; the publication layer's ``pageKind`` (author-page,
edition-page, single-publication) is a separate card label for pages with
publication headers and keeps its meaning.

Offsets in the evidence are character offsets into the page's source text in
dump form, the text the publication layer's ``sourceSlice`` and the Gate-1
selectors address. The evidence values have the dump's quote escape resolved.
"""

from __future__ import annotations

import re

from lib.encoding import unescape_dump_quotes

WIKI_PAGE_KINDS = (
    "work-hub",
    "edition-page",
    "author-page",
    "other",
    "undetermined",
)

# The compiler's note on the VIST pages, e.g. page 7460: "VIST = Volumes /
# Individual Stories / Translations". The title disambiguator is the rule; the
# note is reported where the page carries it.
_VIST_TITLE_RE = re.compile(r"\(VIST\)\s*$")
_VIST_NOTE_RE = re.compile(
    r"VIST\s*=\s*Volumes\s*/\s*Individual\s+Stories\s*/\s*Translations"
)
# The heading stage 03 reads the translations section from
# (lib.wiki_parser._TRANSLATIONS_HEAD); a page listing its work's translations
# is the hub of that work.
_TRANSLATIONS_HEAD_RE = re.compile(r"'''Translations?:?'''")
_CATEGORY_LINK_RE = re.compile(r"\[\[Category:[^\]]*\]\]")
_SORTKEY_RE = re.compile(r"\{\{DEFAULTSORT(?:KEY)?:[^}]*\}\}")
# A page whose whole body is one See statement with wiki links, such as
# "'''See:''' [[Brief einer Unbekannten (VIST)]]" on page 7459.
_PAGE_LINK = r"\[\[(?!Category:)[^\[\]]+\]\]"
_POINTER_BODY_RE = re.compile(
    r"(?:'''\s*)?See(?:\s+also)?\s*:?\s*(?:'''\s*)?"
    rf"{_PAGE_LINK}(?:[\s,;/&]*(?:and\s+)?{_PAGE_LINK})*"
)
# "Surname, Given" as the compiler indexes a person ("Barbusse, Henri",
# "Djevdet (Cevdet), Abdullah"); a title with a sentence break before the
# comma is a work title.
_INVERTED_NAME_RE = re.compile(r"^[^\W\d_][^,.:;!?\"/\[\]]*, [^\W\d_][^/]*$")
_CATEGORY_LANGUAGE_RE = re.compile(r"\(([^()]+)\)\s*$")

# Category roots of Zweig's own works and of secondary-literature items. A page
# filed under them is one item (volume, story, essay, poem, letter, foreword,
# translation, title about Zweig) in the compiler's scheme.
_OWN_WORK_ROOTS = frozenset(
    {
        "Fiction",
        "Essays",
        "Poetry",
        "Dramas",
        "Historical Studies",
        "Correspondence",
        "Collected and Selected Works",
        "Collected and Selected Works in Translation",
        "Forewords and Afterwords",
        "Translations by Zweig",
    }
)
_ITEM_ROOTS = _OWN_WORK_ROOTS | {"Secondary Literature"}
# Roots of pages about an adaptation, a performance, an event or a periodical:
# none of them is an edition of a work by Zweig or an item about him.
_OTHER_ROOT_RULES = {
    "Films": "adaptation-category",
    "Dramatic Readings": "adaptation-category",
    "Symposia and Exhibitions": "event-category",
    # The broken link "[[Category:Symposia and ]]Exhibitions" of page 3923.
    "Symposia and": "event-category",
    "Newspapers": "periodical-category",
}


def _root(category: str) -> str:
    return category.split("(")[0].split(" / ")[0].strip()


def _is_authors(category: str) -> bool:
    # The same reading as the publication layer's pageKind.
    return "Authors" in category.split("(")[0]


def _languages(categories: list[str]) -> list[str]:
    found = []
    for category in categories:
        match = _CATEGORY_LANGUAGE_RE.search(category)
        if match and match.group(1) not in found:
            found.append(match.group(1))
    return found


def _body(text: str) -> str:
    return _SORTKEY_RE.sub("", _CATEGORY_LINK_RE.sub("", text)).strip()


def _text_evidence(match: re.Match) -> dict:
    return {
        "sourceField": "sourceText",
        "sourceValue": unescape_dump_quotes(match.group(0)),
        "sourceStart": match.start(),
        "sourceEnd": match.end(),
    }


def _category_evidence(categories: list[str]) -> list[dict]:
    return [{"sourceField": "categories", "sourceValue": c} for c in categories]


def _title_evidence(value: str) -> dict:
    return {"sourceField": "pageTitle", "sourceValue": value}


def _result(kind: str, rule: str, evidence: list[dict]) -> dict:
    return {
        "wikiPageKind": kind,
        "wikiPageKindRule": rule,
        "wikiPageKindEvidence": evidence,
    }


def classify_wiki_page(page_title: str, text: str, categories: list[str]) -> dict:
    """The kind of one namespace-0 content page, its rule and its evidence.

    The rules apply in this order, and the first that matches decides:
    no-source-body, no-category, cross-reference-page, vist-title,
    conflicting-categories, authors-category, translations-section,
    translated-author, adaptation/event/periodical-category, index-page,
    item-category, several-category-languages, unrecognised-category.
    """
    text = text or ""
    title = unescape_dump_quotes(page_title or "")
    body = _body(text)
    if not body:
        return _result("undetermined", "no-source-body", [])
    if not categories:
        return _result("undetermined", "no-category", [])

    # The body is the source text without category links and sort key; the
    # evidence is the See statement where it stands in the source text.
    statement = _POINTER_BODY_RE.search(text)
    if _POINTER_BODY_RE.fullmatch(body) and statement:
        return _result("other", "cross-reference-page", [_text_evidence(statement)])

    vist = _VIST_TITLE_RE.search(title)
    if vist:
        evidence = [_title_evidence(vist.group(0).strip())]
        note = _VIST_NOTE_RE.search(text)
        if note:
            evidence.append(_text_evidence(note))
        return _result("work-hub", "vist-title", evidence)

    roots = {_root(c) for c in categories}
    authors = [c for c in categories if _is_authors(c)]
    if authors:
        work = [c for c in categories if _root(c) in _OWN_WORK_ROOTS]
        if work and not _INVERTED_NAME_RE.match(title.split(" / ")[0]):
            # Filed as an author and as a work of Zweig's, under a title that
            # names no person (page 6840): the categories disagree.
            return _result(
                "undetermined",
                "conflicting-categories",
                _category_evidence(authors + work),
            )
        return _result("author-page", "authors-category", _category_evidence(authors))

    items = [c for c in categories if _root(c) in _ITEM_ROOTS]
    # Only a page of Zweig's own works: page 2154, a secondary-literature
    # title, transcribes the print volume's contents with a section headed
    # "Translations" that lists entry ranges, not translations of a work.
    own_work = [c for c in items if _root(c) in _OWN_WORK_ROOTS]
    heading = _TRANSLATIONS_HEAD_RE.search(text)
    if own_work and heading:
        return _result(
            "work-hub",
            "translations-section",
            [_text_evidence(heading), *_category_evidence(own_work)],
        )

    if roots == {"Translations by Zweig"} and _INVERTED_NAME_RE.match(title):
        # Indexed under the author Zweig translated ("Barbusse, Henri"); a
        # title naming a work as well ("Verhaeren, Emile / Rubens") is an item.
        return _result(
            "author-page",
            "translated-author",
            [_title_evidence(title), *_category_evidence(categories)],
        )

    if roots <= _OTHER_ROOT_RULES.keys():
        rules = {_OTHER_ROOT_RULES[root] for root in roots}
        rule = rules.pop() if len(rules) == 1 else "adaptation-or-event-category"
        return _result("other", rule, _category_evidence(categories))

    if title.startswith("Index by "):
        return _result("other", "index-page", [_title_evidence("Index by")])

    if roots <= _ITEM_ROOTS | _OTHER_ROOT_RULES.keys() and items:
        languages = _languages(items)
        if len(languages) <= 1:
            return _result("edition-page", "item-category", _category_evidence(items))
        return _result(
            "undetermined", "several-category-languages", _category_evidence(items)
        )
    return _result(
        "undetermined", "unrecognised-category", _category_evidence(categories)
    )

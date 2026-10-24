"""Rule readings of a print object into the structured form of _schema.py.

Every reader works on the entry text and returns values whose span points into
it. Text values are cut from the source, never composed, so each one equals
its passage. Values from another record (headings, collection headers) are
read on that record's text and marked by p03 (inherit()).

The readers follow the notations counted by probe_notations.py and documented
in knowledge/print-volumes.md (Entry anatomy):
- own zone: the object's citation runs up to the first label that introduces
  another publication or a cross-reference (Rep:, REV:, Contents, See, ...);
  title, imprint, extent, edition statements, persons and series are read
  there only, so that a reprint's imprint is not the object's.
- host: a contribution names its host volume by title ("in Title. Ed. ...") or
  by address ("in D 2, p. 8", "A 147, pp. (11)-83"); credits, imprint, extent
  and series after the host's start belong to the host, not to the object.
- reviewed work: the citation after REV: or "Review of:".
- persons: credit phrases ("Trl./Intro.", "Edited with an afterword by") give
  one role per role word, each spanning its own word, applied to every name of
  the list that follows; "Trl. not indicated" is a role without a name.
- imprint: "Place: Publisher, Year", several imprints split at " / ", a year
  printed once belonging only to the imprint it follows.
- periodical: the siglum form of the main volume (invented: "BOTE, 4:12 (1 May
  1913), 20-21") and the spelled form of the addenda (invented: "in Die Zeitung
  (Wien), 3 May 1912 (No. 41), pp. (2)-4"); a story printed in several issues
  has several citations.
- types: derive_types() decides them from the fields, so p10 can recompute them.
"""

import re

from _addresses import REFERENCE, SUFFIX_TO_VOLUME, parse_items
from _common import MONTH, REPRINTED, SECTIONS
from _objects import manuscript_item
from _schema import LANGUAGE_VARIANTS, LANGUAGES, iter_values

LANGUAGE_BY_FOLD = {name.lower(): name for name in LANGUAGES} | LANGUAGE_VARIANTS
# Highest entry number per section, from the volumes' tables of contents.
TOC_MAX = {
    volume: {k: v for k, v in spec["toc_max"].items() if not k.startswith("_")}
    for volume, spec in SECTIONS["volumes"].items()
    if spec.get("toc_max")
}
NUMBER_PREFIX = re.compile(r"^(?:[A-R](?:A[12])? ?)?\d{1,4}[a-z]?\s+")
ITEM_MARK = re.compile(r"\[(?:\d{1,3}[a-z]?|X|[a-z]|-)\]\s?\.\s*")
STUB_MARK = re.compile(r"\*{1,5}\s+")
# Patterns applied with pattern.match(text, pos) carry no "^": it would only
# match at the start of the entry text, not at pos.
VOLUME_PREFIX = re.compile(r"(?P<number>Vols?\.\s?[\dIVXL]+[a-z]?)\s?[.:]\s+")
YEAR_PREFIX = re.compile(r"(?:1[5-9]|20)\d\d(?:/\d{2,4})?:\s+")
LANGUAGE_PREFIX = re.compile(r"([A-Z][A-Za-z-]+)(?::|\.)?\s+(?=\S)")
# A bracket after a contents title that credits or describes its item rather
# than naming its original: "[Foreword by ...]", "[Annotations by ...]",
# "[F. G. Surname]", "[Surname: "Title", pp. 3-9]".
CREDIT_GLOSS = re.compile(
    r"\b(?:by|[Ff]oreword|[Aa]fterword|[Aa]nnotations?|[Nn]otes|[Cc]omments?|"
    r"[Ii]ntroduction|[Pp]reface|[Cc]ommentary|[Ee]ditorial|Vorwort|Nachwort|"
    r"Einleitung|Anmerkungen|Comp|Eds?|Illus|[Nn]otes?|chapters|[Vv]ocabulary|"
    r"[Gg]lossary|[Bb]ibliography|[Cc]hronology|[Ii]ndex)\b|\b[A-Z]\.\s?[A-Z]|,\s?pp?\b|"
    r"[’']s\s(?:foreword|afterword|preface|introduction)|"
    r"^[A-ZÀ-Þ][\w-]+ [A-ZÀ-Þ][\w-]+ (?:and|&) [A-ZÀ-Þ]"
)
SECTION_ADDRESS_ONLY = re.compile(
    r"[A-R]{1,2}A2(?:\s\d{1,4}[a-z]?)?(?:\s?/\s?[A-R]{1,2}A2(?:\s\d{1,4}[a-z]?)?)*"
)
HOST_CODE = re.compile(
    r"(?P<code>[A-R]{1,2}A2(?:\s+\d{1,4}[a-z]?(?=\s+[A-ZÀ-ÞĀ-ž„“\"‘]|\s?/))?"
    r"(?:\s?/\s?[A-R]{1,2}A2(?:\s\d{1,4}[a-z]?)?)*)\.?(?:\s+|$)"
)
# "F. Surname. Title" or "F. G. Surname" alone: a host's author, forename in
# initials, before the host title.
INITIAL_AUTHOR = re.compile(
    r"(?P<name>(?:[A-ZÀ-Þ][a-z]?\.\s?){1,3}[A-ZÀ-ÞĀ-ž][\w'’-]+(?:[ -][A-ZÀ-ÞĀ-ž][\w'’-]+)?)"
    r"(?:\.\s+(?=[A-ZÀ-ÞĀ-ž\"“„‘(\[])|$)"
)
# "Forename Surname", "Forename F. von Surname": a name forename first, no
# article and not Zweig's, whose name titles the studies about him.
_FORE = r"[A-ZÀ-ÞĀ-ž][a-zß-ÿā-ž'’]+(?:-[A-ZÀ-ÞĀ-ž]?[a-zß-ÿā-ž'’]+)?"
FORENAME = re.compile(
    r"(?!(?:Der|Die|Das|Ein|Eine|The|A|An|Le|La|Les|Il|Lo|El|Los|Las|Un|Une)\s|Stefan Zweig\b)"
    rf"{_FORE}(?:\s(?:{_FORE}|[A-Z][a-z]?\.)){{0,2}}\s(?:(?:von|van|de|der|da|di|du)\s){{0,2}}{_FORE}"
)
FORENAME_AUTHORS = re.compile(
    rf"{FORENAME.pattern}(?:(?:,\s(?:and\s)?|\s&\s|\sand\s){FORENAME.pattern})*"
)
# What follows a cited title sentence: an imprint ("Place: Publisher, 1964",
# "(Place): ..."), a credit, a volume or an extent or edition in figures.
IMPRINT_AHEAD = re.compile(
    r"\(?[A-ZÀ-ÞĀ-ž][\w'’/ .-]{1,40}\)?: [^.:]{2,80}, [\[(]?(?:1[5-9]|20)\d\d"
)
CITATION_AFTER_TITLE = re.compile(
    rf"{IMPRINT_AHEAD.pattern}|(?:Eds?|Comp|Trl?s?|Sel|Intro|Frw|Aftw|Illus|Vol|Bd)\.\s|\d"
)
# A dot after a number that follows an article or preposition is an ordinal
# ("zum 50. Todestag", "des 19. Jahrhunderts"), and one before a month a
# date's ("28. November"); neither ends a sentence.
ORDINAL_BEFORE = re.compile(
    r"\b(?:des|der|dem|den|das|die|zum|zur|am|im|vom|bis|ab|seit|um|ins|beim)\s\d{1,3}$"
)
# A sentence after the title that names an issue or the book's form, no
# subtitle: "No", "Jg", "Braille edition", "Library binding".
FORMAT_NOTE = re.compile(
    r"(?:No|Nr|Nos|Jg|Vol|Bd|Heft)\.?|[\w’' .-]{0,30}\b(?:[Ee]dition|binding)"
)
EDITOR_GLOSS = re.compile(r"\s?\[(?P<role>Eds?|Editors?)\.?\]\.?\s+")
VOLUME_WORD = re.compile(r"(?:Band|Bd\.|Vol\.|Teil|Heft|Tome|Book|Buch)\s?[\dIVXL]")
# An imprint place before its colon. It holds a dot only after an
# abbreviation of one or two letters ("St. Gallen", "Frankfurt a. M."), so
# that "Title. Subtitle. Place: " ends the title before the place, not
# before the subtitle.
IMPRINT_PLACE_RUN = (
    r"[A-ZÀ-ÞĀ-ž](?:[\w'’ /-]|(?:(?<=\b[A-Za-z])|(?<=\b[A-Z][a-z]))\.){1,40}: "
)
# Where a host title read after its author ends: an imprint, an editor, a
# volume, an extent, a page locator or a bracket. The dot of an initial ends
# no title ("E. M. Surname: Title").
HOST_TITLE_END = re.compile(
    rf"(?<!\b[A-Z])\.\s+(?={IMPRINT_PLACE_RUN}"
    r"|Eds?\.|Vol\.|Bd\.|\d|\(|\[)"
    r"|,\s?(?:pp?\.|Vol\.|S\.)|\s\[|\.?$"
)
YEAR_OF_TITLE = re.compile(
    r"\b(?:[Jj]ahr|[Jj]ahres|[Jj]ahre|[Yy]ear|[Aa]nno|Almanach|Kalender|Jahrbuch|"
    r"[Aa]lmanac|[Yy]earbook|für|for)$"
)
VOLUME_BREAK = re.compile(
    r"\.\s+(?:(?:Vol|Vols|Bd|Tome|Tom)\.\s?[\dIVXL]+[a-z]?(?:\s?[-–]\s?[\dIVXL]+)?"
    r"(?:\s\([^()]{1,30}\))?\s?[.:]"
    r"|(?:New edition|Neuausgabe|New ed\.)\s?:)"
)
REVIEWED_HEAD = re.compile(
    r"(?!(?:Der|Die|Das|Ein|Eine|The|A|An|Le|La|Les|Il|Lo|El|Los|Las|Un|Une)\s)"
    r"(?P<name>[A-ZÀ-ÞĀ-ž][\w'’-]+(?: (?:von |van |de |du |di |da |le |la )?[A-ZÀ-ÞĀ-ž][\w'’-]+){1,2})"
    r"\.\s+(?=[A-ZÀ-ÞĀ-ž\"“„‘])"
)
CODE_LANGUAGE = re.compile(r"[A-R]{1,2}A2\s\[(?P<lang>[A-Z][a-z-]+)\],?\s+")
# "French:" and "Spanish [Reviews of the 1951 ed.]:" switch the language.
LANGUAGE_LABEL = re.compile(
    # The print may leave the outer bracket open before the colon.
    r"\b([A-Z][a-z]+(?:-[A-Z][a-z]+)?)(?:\s\[(?:[^\[\]]|\[[^\[\]]*\]){1,240}\]?)?:\s"
)
YEAR = re.compile(r"(?<!\d)(1[5-9]\d\d|20[0-2]\d)(?!\d)")

ZONE_END = re.compile(
    r"\b(?:Rep|REP|REV(?: VERSION)?|Rev\. version|EXC(?:ERPTS?)?|Excerpts?|"
    r"Contents|Con-\s?tents|Contains|TRANSLATIONS?|Translations|FIE|"
    rf"Sub\. (?:eds?|imprs?)\.(?:/imprs?\.)?|{REPRINTED}|Further editions|"
    r"(?:Non-)?Fischer Editions/Reprints|Book editions?|Reviews?|Re-?\s?view of|First printing|"
    r"(?:Manuscripts?|Typescripts?)(?: versions?| cop(?:y|ies))?)\s?:"
    # "See-Verlag" is a publisher.
    r"|\bSee\b(?!-)|\bReprinted\b|\bSub\. (?:eds?|imprs?)\.(?:/imprs?\.)?"
)
# Each opening quote with its closing ones; single quotes may stand inside
# double ones (“… ‘…’ …”).
QUOTED = re.compile(
    r"“(?P<a>[^”“\"]{2,300})[”\"]|\"(?P<b>[^\"”“]{2,300})[\"”“]|„(?P<c>[^“”\"]{2,300})[“”\"]"
    r"|«(?P<d>[^»]{2,300})»|[‘`'](?P<e>[^’'`\"“”]{2,300})[’']"
)
QUOTE_OPEN = frozenset("\"“„«‘`'")

ROLE_WORDS = {
    "tr": "translator",
    "trl": "translator",
    "trls": "translator",
    "translated": "translator",
    "translation": "translator",
    "translations": "translator",
    "translator": "translator",
    "translators": "translator",
    "ed": "editor",
    "eds": "editor",
    "edited": "editor",
    "editor": "editor",
    "editors": "editor",
    "comp": "editor",
    "compiled": "editor",
    "sel": "editor",
    "selected": "editor",
    "selection": "editor",
    "assembled": "editor",
    "editorial": "editor",
    "intro": "introduction",
    "introduction": "introduction",
    "introductory": "introduction",
    "frw": "introduction",
    "foreword": "introduction",
    "pref": "introduction",
    "preface": "introduction",
    "prefatory": "introduction",
    "presented": "introduction",
    "aftw": "afterword",
    "afterword": "afterword",
    "postface": "afterword",
    "illus": "illustrator",
    "illustrated": "illustrator",
    "illustrations": "illustrator",
    "illustration": "illustrator",
    "drawings": "illustrator",
    "cover": "illustrator",
    "photographs": "illustrator",
    "frontispiece": "illustrator",
    "woodcuts": "illustrator",
    "notes": "contributor",
    "annotations": "contributor",
    "endnotes": "contributor",
    "comt": "contributor",
    "commentary": "contributor",
    "dir": "contributor",
    "directed": "contributor",
    "director": "contributor",
    "screenplay": "contributor",
    "music": "contributor",
    "starring": "contributor",
    "libretto": "contributor",
    "readers": "contributor",
    "prod": "contributor",
    "produced": "contributor",
    "camera": "contributor",
    "essay": "contributor",
    "read": "contributor",
    "reading": "contributor",
    "script": "contributor",
    "text": "contributor",
    "adapted": "contributor",
    "adaptation": "contributor",
    "staging": "contributor",
    "musical": "contributor",
    "commentaries": "contributor",
    "vocab": "contributor",
}
ABBREVIATED = r"(?:Tr|Trls?|Eds?|Comp|Sel|Intro|Frw|Pref|Aftw|Illus|Comt|Dir|Prod)\."
CREDIT = re.compile(
    # A credit opens a sentence, also after the double space of a joined line
    # or right after "].".
    r"(?:^|(?<=[.\];:] )|(?<=[.\];:]  )|(?<=\[)|(?<=\]\.))"
    rf"(?P<phrase>{ABBREVIATED}(?:\s?/\s?[A-Z][a-z]+\.?(?: [a-z]+\.)?)*"
    r"|(?:Translator|Translators|Trl\.|Tr\.) not indicated"
    r"|[A-Z][a-z]+(?:[ /-](?:[a-z’']+|[A-Z][a-z]+)){0,10}? by"
    r"|Starring:?|Readers:|General editors?|Editor[- ]in[- ]chief"
    r"|Editorial [Ss]taff|Cover(?: design| illustration)?"
    r"|(?:Preface|Foreword|Afterword|Introduction|Drawings|Illustrations|Notes|"
    r"Photographs|Frontispiece|Essay|Screenplay)(?:/\s?[A-Z][a-z]+\.?)*(?=\s[A-ZÀ-ÞĀ-ž]))"
    r"(?:\s+|(?=[.\]]))"
)
# A sentence that opens with a credit in a form CREDIT does not read (a
# German credit, "Translated" without "by", a credit after a double space
# left by a joined line), an extent or a bracketed imprint ends a title.
CREDIT_SENTENCE = re.compile(
    rf"(?:{ABBREVIATED}|(?:Translated|Compiled|Compiler|Edited|Herausgegeben|"
    r"Übersetzt|Ausgewählt|Eingeleitet|By|Illustrated)\b|Hrsg\.|"
    r"[A-Z][a-z]+(?:\s+[a-z]+){0,4}\s+by\b|\d+(?:/\(\d+\))?p\.?(?=[\s.,]|$)|"
    r"\([A-ZÀ-ÞĀ-ž][\w'’ -]{1,40}: )"
)
NOT_INDICATED = re.compile(r"\bnot indicated\b")
# A name list runs to a sentence end that is no initial or abbreviation.
NAME_END = re.compile(
    r"(?<![A-Z])(?<!\b[A-Z][a-z])(?<!\bJr)(?<!\bSr)(?<!\bSt)(?<!\bDr)\.(?=\s|$)"
    r"|[\[(;:]|\s\d|\.$|\]|\s(?=(?:from|with|in|after|on|based|for)\s)"
)
NAME_SPLIT = re.compile(r",\s(?:and\s)?|\s&\s|\sand\s|\set\s")
NAME_DROP = re.compile(r"^(?:et al\.?|resp\.?|u\. ?a\.?)$")
NAME_OK = re.compile(r"^[A-ZÀ-ÞĀ-ž(\[][^\d:]{1,59}$")
# "Surname, Forename.", "Surname, F. G. H.", "SURNAME, FORENAME." and the
# subject form "SURNAME, FORENAME / ": given names are words or
# initials, so the name ends at the first sentence end that is no initial.
_WORD = r"(?:[A-ZÀ-ÞĀ-ž][A-Za-zÀ-ÿĀ-ž'’-]+|\([\w.]+\))"
_PARTICLE = r"(?:von|van|de|der|du|di|da|y|zu)"
# Words, then initials ("Forename F."), or initials alone ("F. G. H."); a word
# after an initial opens the title ("Surname, F. G. H. Title").
_GIVEN = (
    rf"(?:{_WORD}(?:[ -](?:{_WORD}|{_PARTICLE})){{0,4}}(?:\s[A-Z]\.)*"
    r"|[A-Z]\.(?:\s?[A-Z]\.)*)"
)
# A title of nobility ("Surname, Forename, Freiherr von.") or a gloss in
# parentheses ("SURNAME, FORENAME (other name).") closes a given name.
_TITLE_OF_NOBILITY = (
    r"(?:,\s(?:Freiherr|Graf|Baron|Ritter|Sir|Vicomte)(?:\s(?:von|de|zu))?)?"
    r"(?:\s\([^()]{1,40}\))?"
)
# A title-reference code of Addendum II ("LA2 Surname, ...") opens no name; a
# subject may carry life dates or a gloss before its slash ("Surname,
# Forename [birth-death] / ").
SURNAME_HEAD = re.compile(
    r"^(?![A-R]{1,2}A[12]\s)(?P<name>[A-ZÀ-ÞĀ-ž(][\w'’()-]*(?:[ -](?:[\w'’()-]+)){0,3}, "
    rf"{_GIVEN}{_TITLE_OF_NOBILITY})"
    r"(?:(?<=\.)\s+(?=[\"“„‘`'A-ZÀ-ÞĀ-ž(\[\d])|\s?\.\s+(?=[\"“„‘`'A-ZÀ-ÞĀ-ž(\[\d])"
    r"|\.(?=See\b)|\s(?=\([A-R](?:A[12])? \d)|(?:\s\[[^\[\]]{1,40}\]){0,2}\s+/\s+)"
)
_SURNAME = r"[A-ZÀ-ÞĀ-ž(][\w'’()-]*(?:[ -](?:[\w'’()-]+)){0,3}"
# A bracket after the head names its roles ("[Ed./Intro.]", "[Editor]") or
# glosses it ("[other name]", "[Exhibition/Catalogue]").
HEAD_WITH_CREDIT = re.compile(
    rf"^(?P<name>{_SURNAME}, {_GIVEN}{_TITLE_OF_NOBILITY})\s\[(?P<credit>[^\[\]]{{1,200}})\]"
    r"(?:\.\s|\s/\s|:\s|\.(?=[A-Z]))"
)
HEAD_PAIR = re.compile(
    rf"^(?P<name>{_SURNAME}, {_GIVEN})\s(?:&|and)\s"
    r"(?P<second>[A-ZÀ-ÞĀ-ž][\w'’-]+(?:\s(?:[A-ZÀ-ÞĀ-ž][\w'’.-]*|von|van|de|der)){0,4})\.\s"
)
INITIALS_HEAD = re.compile(r"^(?P<name>(?:[A-Z][a-z]?\.\s?){1,3})\s?(?=[\"“„‘`'])")
SPEAKER = re.compile(
    r"(?P<name>(?:[A-Z][a-z]{0,3}\.\s)*[A-ZÀ-ÞĀ-ž][\w'’.-]*(?:\s(?:[A-ZÀ-ÞĀ-ž][\w'’.-]*|von|van|de|der)){0,4})"
    r"(?:\s\([^()]{1,80}\)|,\s[A-ZÀ-ÞĀ-ž][\w'’-]+(?:[ -][A-ZÀ-ÞĀ-ž][\w'’-]+)?)?:\s"
)
FORENAME_HEAD = re.compile(
    r"^(?P<name>\[?[A-ZÀ-ÞĀ-ž][A-Za-zÀ-ÿĀ-ž'’.-]*(?: [A-ZÀ-ÞĀ-ža-z][A-Za-zÀ-ÿĀ-ž'’.-]*){0,4}\??\]?)"
    r"[.?]?\s(?=[\"“„‘`'])"
)
TRAILING_NAME = re.compile(r"\((?P<name>[A-ZÀ-ÞĀ-ž][^()\d;]{1,40} [^()\d;]{1,40})\)")
HEAD_ROLE = {
    "L": "author",
    "J": "author",
    "Q": "author",
    "I": "author",
    "O": "contributor",
    "K": "subject",
    "H": "subject",
    "M": "author",
}
LABEL_WORDS = frozenset(
    "contents contains see rep rev fie exc excerpts note nb cover translations "
    "reprinted review reviews premiere dedication correspondence starring "
    "readers music camera vol vols no nos book editions edition further "
    "words concerning catalogue catalog translated edited".split()
)
LABEL_PHRASES = frozenset(("new edition", "new ed.", "new ed", "new special edition"))
PLACE_ABBREVIATION = re.compile(r"\b(?:St|Ste|S|a|N|Mt|Ft|Bad)\.\s$")
# Joined lines leave double spaces ("Publisher,  2005"), hence \s{1,2}.
IMPRINT_YEAR = re.compile(
    r",\s{1,2}(?P<open>[\[(])?(?P<circa>ca\.\s)?(?P<year>1[5-9]\d\d|20[0-2]\d)(?P<close>[\])])?"
    r"(?:\s?[-/–]\s?[\[(]?(?P<end>1[5-9]\d\d|20[0-2]\d)[\])]?)?(?!\d)"
)
COLON_YEAR = re.compile(
    r": (?P<open>[\[(])?(?P<year>1[5-9]\d\d|20[0-2]\d)(?P<close>[\])])?(?![\d.:/-])"
)
NO_DATE = re.compile(
    r", (?:No date|no date|[Dd]ate not indicated|n\. ?d\.|s\. ?d\.|o\. ?J\.)"
)
EXTENT = re.compile(
    r"(?<![\w/(\[.])(?P<raw>(?:[\[(]?(?:[ivxlc]+|\d+)[\])]{0,2})"
    r"(?:\s?/\s?[\[(]?(?:[ivxlc]+|\d+)[\])]{0,2})*)\s?(?:p\.|leaves\b|cols\.)"
)
EXTENT_PIECE = re.compile(r"[\[(]?(?:[ivxlc]+|\d+)[\])]{0,2}")
VOLUMES = re.compile(r"\b\d+ vols\.")
ILLUSTRATIONS = re.compile(
    r"\b(?:\d+ )?(?:illus\.|port\.|Illustrated\b|illustrations\b)(?! [A-Z][a-z])"
)
EDITION_NOTES = (
    ("thousand", re.compile(r"\(?\d+\.\s?(?:-\s?\d+\.\s?)?Tsd\.\)?")),
    (
        "printing",
        re.compile(
            r"\(?\d+\.(?:\s?-\s?\d+\.)? Auflage\)?|\b\d+(?:st|nd|rd|th)"
            r"(?:/\d+(?:st|nd|rd|th))? imprs?\.|\b\d+\. impr\.|"
            r"\b(?:New|First|Second|Third|\d+(?:st|nd|rd|th))(?: private)? printing\b"
        ),
    ),
    (
        "edition",
        re.compile(
            r"\b(?:\d+(?:st|nd|rd|th)|New|Rev\.|Revised|Large print|Pktbk\.|Prbk\.|"
            r"Paperback|Definitive|Enlarged|Special|Book [Cc]lub|Bookclub) ed(?:\.|ition)"
        ),
    ),
    (
        "copies",
        re.compile(r"\b\d[\d,.]* (?:numbered (?:and signed )?)?(?:Expl\.|copies)"),
    ),
    ("licensed", re.compile(r"\bLic\. ed\.?|\bLicensed edition|\bLizenzausgabe")),
    (
        "reprint",
        re.compile(
            r"\[(?:Rep|REP)\.?\s(?:\d+(?:st|nd|rd|th) impr\. )?(?:1[5-9]|20)\d\d"
            r"[^\[\]]{0,60}\]|\[Reprinted (?:1[5-9]|20)\d\d[^\[\]]{0,60}\]|"
            r"\bMicrocard reprint\b"
        ),
    ),
)
SERIES = re.compile(
    r"\s?(?P<open>[(\[])(?P<title>[A-Z][^()\[\]]{1,80}?)"
    r"(?:,\s?(?P<number>(?:No\. |Nr\. |Vol\. |Bd\. )?[\dA-Z][\w./ -]{0,15}?))?"
    r"(?P<close>[)\]])"
)
SERIES_STOP = re.compile(
    r"^(?:Rep|REP|Lic|Printed|This|The |See|Facsim|ca\.|Under|Here|Orig|Vols?\.|"
    r"Reprinted|Licensed|Translations|Contains|Concerning|First|Stage|\d)"
    r"|\b(?:ed\.|copies|impr|Tsd\.)|\b[Ee]dition\b"
)
# "[EXC]" and "[FAC]" are the volumes' general abbreviations (excerpt,
# facsimile), no informant sigla.
INFORMANT = re.compile(r"\[(?P<sigla>(?!(?:EXC|FAC)\])[A-Z]{2,5}(?:/[A-Z]{2,5})*)\]")
BRACKET = re.compile(r"\[(?P<inner>[^\[\]]{3,600})\]")
VARIANT = re.compile(
    r"\[(?:Under the titles? |Here entitled |Released (?:also |in [^,\]]{2,30} )?"
    r"under the titles? )[^\]]*\]"
)
SIGLUM_PERIODICAL = re.compile(
    r"(?<![\w-])(?P<siglum>[A-ZÄÖÜÉÈÀ][A-ZÄÖÜÉÈÀ0-9]{2,9})"
    r"(?:, (?P<extra>[A-Z][^,()\[\]]{2,40}?))?, "
    r"(?:(?P<volume>(?:No\. |Nr\. |Heft |Sonderheft )?[\dIVXLC]+(?:/\d+)?)"
    r"(?::\s?(?P<issue>[\d/]+[a-z]?))?\s?"
    # "SIGLUM, 17:1 (Place) (Jan. 1964)": a place in parentheses may precede
    # the date, which holds a digit.
    r"(?:\([^()\d]{2,30}\)\s?)?"
    rf"[(\[](?P<date>[^()\[\]]{{0,38}}\d[^()\[\]]{{0,38}})[)\]]|(?P<ndate>\d{{1,2}}(?:/\d{{1,2}})?\.? "
    rf"(?:{MONTH}\s?-\s?\d{{1,2}}\.? )?{MONTH} (?:1[89]|20)\d\d)"
    rf"|(?P<mdate>{MONTH} (?:1[89]|20)\d\d))"
    r"(?:,\s?(?:pp?\.|cols?\.)?\s?(?P<pages>(?=[()\[\]]*[\divxlc])[\divxlc()\[\]]+"
    r"(?:\s?-\s?[\divxlc()\[\]]+)?))?"
)
_SPELLED = (
    r"(?P<title>[A-ZÀ-ÞĀ-ž][^()\[\]“”\"„]{1,150}?)\s+[(\[](?P<place>[A-ZÀ-ÞĀ-ž][^()\[\]]{1,50})"
    r"[)\]],\s*"
    r"(?:(?P<volume>(?:Year \d+ / )?(?:Vol\. )?\d+)(?::\s?(?P<issue>[\d/]+))?\s+"
    r"[(\[](?P<date>[^()\[\]]{3,40})[)\]]"
    rf"|(?P<ndate>\d{{1,2}}(?:/\d{{1,2}})?\.?\s+{MONTH}\s+(?:1[89]|20)\d\d)"
    r"(?: [(\[](?:No\.|Nr\.) (?P<nissue>\d+)[)\]])?"
    r"|(?:Nos?\.|Nr\.|Folge|Heft) (?P<sissue>[\d/-]+)"
    r"(?: [(\[](?P<sdate>[^()\[\]]{3,40})[)\]])?)"
    r"(?:,\s?(?:pp?\.|cols?\.|columns)?\s?(?P<pages>(?=[()\[\]]*[\divxlc])[\divxlc()\[\]]+"
    r"(?:\s?[-–]\s?[\divxlc()\[\]]+)?))?"
)
SPELLED_PERIODICAL = re.compile(r"\bin\s+" + _SPELLED)
# A reprint segment may open with the periodical itself: "REP: Journal
# Title (Place), 4 (1995), 35-50."
SPELLED_AT_START = re.compile(_SPELLED)
# A further issue of the same periodical: "11:11 (1937), 340-342" or
# "Nr. 166 (12 May 1929), 15".
CONTINUED_ISSUE = re.compile(
    r"[.;]\s(?:(?P<volume>\d+)(?::(?P<issue>[\d/]+))?|(?:No\.|Nr\.)\s?(?P<nissue>\d+))"
    r" [(\[](?P<date>[^()\[\]]{3,40})[)\]],\s?(?P<pages>(?=[()\[\]]*\d)[\d()\[\]]+(?:\s?-\s?[\d()\[\]]+)?)"
)
# Used with match() right after the title and its brackets: a host follows as
# "” in Title" (addenda) or "\", Title" (main volume).
HOST_TITLE = re.compile(
    r"\s*(?:\.\s)?(?:in\s+|,\s+)(?P<title>(?![A-R](?:A[12])? \d)(?![A-ZÄÖÜÉ]{3,9}, )"
    r"[A-ZÀ-ÞĀ-ž„“\"][^\[\]]{1,160}?)"
    r"(?=\. Ed\.|\. Edited|\. Hrsg|\. [A-Z][^.:]{1,40}: |,? (?:Vol\.|pp?\.|No\.)|"
    r"\s+\[[A-R](?:A[12])? ?\d|\s+\[(?:1[5-9]|20)\d\d\]|\.?$"
    # "in Forename Surname [Ed.]. Title. Place: ..." names the host's editor
    # first (_split_author).
    r"|\s?\[(?:Eds?|Editors?)\.?\]\.?\s"
    # A translated host glosses its title in brackets ("Title [German
    # title]. Translated by ... 429p. Place: Publisher, 2004") before its
    # credits, extent or imprint.
    r"|\s\[(?!(?:Eds?|Editors?|Hrsg|Comp|Trl?s?)\b)[^\[\]\d]{2,160}\]\.\s+"
    r"(?=\d+(?:/\(\d+\))?p\.|(?:Edited|Translated|Compiled|"
    rf"Selected|Introduction|Foreword|Afterword|Annotations?)\b|{ABBREVIATED}|"
    r"\(?[A-ZÀ-ÞĀ-ž][\w'’/ .-]{1,40}\)?: [^.:]{2,80}, [\[(]?(?:1[5-9]|20)\d\d))"
)
# "“Essay” in LA2 Title 1942 [12], pp. 116-117": a contribution cites its
# host as a title reference of Addendum II.
IN_LEAD = re.compile(r"\s*(?:\.\s)?in\s+")
HOST_ADDRESS = re.compile(
    r"(?<![\w-])(?P<address>[A-R](?:A[12])? \d{1,4}[a-z]?)"
    r"(?=(?:,? (?:Vol\. [\dIVX]+|\[[^\]]{1,20}\]))?, pp?\.|, p\.)"
    r"|\bin (?P<inaddress>[A-R](?:A[12])? \d{1,4}[a-z]?)\b"
)
PAGES = re.compile(
    r"\bpp?\.\s*(?P<pages>(?=[()\[\]]*[\divxlc])[\divxlc()\[\]]+(?:\s?[-–]\s?[\divxlc()\[\]]+)?)"
)
# "SIGL: Zweig to X, 1 letter, 27 Oct. 1912." runs past the dot of a
# month to the end of the holding.
HOLDING_REPOSITORY = re.compile(
    # A short note before a comma ("1 letter [Copy], 15 Aug. 1940") stays.
    r"(?P<repo>[A-Z][A-Z]{1,5}): (?P<text>[^;]+?)"
    r"(?=;\s|;?$|\s\[(?![^\[\]]{1,40}\],)|\.?$|\.\s(?![\da-z]))"
)
HOLDING_LETTERS = re.compile(
    r"(?:Zweig|[A-ZÀ-Þ][\w’'-]+(?: (?:von |van |de |der |du |di |da |zu )?[A-ZÀ-Þ][\w’'-]+){0,3}) to "
    r"(?:Zweig|[A-ZÀ-Þ][\w’'()-]+(?: (?:von |van |de |der |du |di |da |zu )?[A-ZÀ-Þ][\w’'()-]+){0,3}), "
    r"(?:\d+|one|two) (?:letters?|postcards?|cards?|notes?|telegrams?|"
    r"calling cards?)"
    # The holding runs past the dot of a month, "ca." and "n. d.", of a date in
    # figures ("18.12.1912") and past a short note ("1 letter [Copy], 15 Aug.").
    r"(?:\b(?:Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept?|Oct|Nov|Dec|ca|n\.\s?d)\.|\.(?=\d)"
    r"|\[[^\[\]]{1,40}\](?=,)|[^.;\[])*"
)
# A letters item that opens with a name and its place in parentheses names
# the source of the letters, an archive, library or dealer: "[1]. Archive,
# Publisher (Place),", "[2]. Dealer (Place), Katalog 5, ...". The name ends
# in a letter, so a bracketed imprint place after a sentence does not count.
LETTER_SOURCE = re.compile(
    r"[A-ZÀ-ÞĀ-ž][^()\[\]\d:;\"“„]{0,118}[^\W\d_] \([A-ZÀ-ÞĀ-ž][^()\[\]\d]{1,40}\)"
    r"(?=[,.:]|\s*$)"
)
# After the source, a title with an address in brackets cites a publication.
CITED_AFTER_SOURCE = re.compile(r",\s+(?=[^\[\],]{2,120}?\s\[[A-R](?:A[12])? ?\d)")
# The repository runs to the end of its sentence or to its shelfmark.
LOCATED = re.compile(
    r"\b(?:is|are) located (?:in|at) (?:the )?(?P<repo>[A-Z][\w ,.-]{1,80}?)"
    r"(?=\.(?:\s|$)|\s?\[|\sunder the (?:number|shelfmark|signature)\b|$)"
)
MANUSCRIPT = re.compile(r"\b(?:[Tt]ypescript|[Mm]anuscript|Typeschrift|proof sheets)\b")
# A reprint item of Addendum II cites its collection by section code, title,
# year and contents number: "DA2 4 Title. Subtitle 1901, No. 7, p. 18",
# "AA2 18/EA2 Title 1964 [12], pp. (685)-(709)".
TITLE_REF = re.compile(
    r"(?:(?P<code>[A-R]{1,2}A2(?:\s\d{1,4}[a-z]?)?(?:\s?/\s?[A-R]{1,2}A2(?:\s\d{1,4}[a-z]?)?)*)\s+)?"
    r"(?P<title>[A-ZÀ-ÞĀ-ž„“\"‘][^\[\]()]{1,160}?)(?:\s\([A-Z][^()\d]{1,30}\))?"
    r"(?:\s[\[(](?P<byear>1[5-9]\d\d|20[0-2]\d)(?:/\s?\d{2,4})?[\])]"
    r"|\s(?P<year>1[5-9]\d\d|20[0-2]\d)(?:/\s?\d{2,4})?)?"
    r"(?:\.?\s(?:Vol\.|Bd\.) [\dIVX]+[^,\[]{0,80})?"
    r"(?:\s?\[(?P<no>(?!(?:1[5-9]|20)\d\d\])[\dA-Z][\w ,-]{0,8})\]|,\s?(?:No\.?|Nr\.)\s?(?P<no2>\d+))?"
    r"(?:,\s+(?:pp?\.|p)\s*(?P<pages>(?=[()\[\]]*[\divxlc])[\divxlc()\[\]]+(?:\s?[-–]\s?[\divxlc()\[\]]+)?))"
)
# Under "Fischer Editions/Reprints:" an item opens with its publisher.
EDITION_PUBLISHER = re.compile(
    r"(?P<publisher>(?:[A-Z]\.\s)*[A-Z][^.\[\]:\d]{1,60}?(?:Verlag|Bücherei|Buchgemeinschaft|Press|"
    r"Fischer|Insel|Suhrkamp|Reclam|Diogenes|Ullstein|Rowohlt|Buchklub|Club|"
    r"Taschenbuch|Library|Books|Éditions|Editions|Editorial|Editora|Libri)\b[^.\[\]:\d]{0,30}?)"
    r"(?=\s?[.\[])"
)
# "Title. Place, 1922, p. 13" names place and year without a publisher.
PLACE_YEAR_PAGES = re.compile(
    r"(?<=\.\s)(?P<place>[A-ZÀ-ÞĀ-ž][A-Za-zÀ-ÿĀ-ž'’/ -]{2,40}), (?P<open>[\[(])?"
    r"(?P<year>1[5-9]\d\d|20[0-2]\d)(?P<close>[\])])?, pp?\.\s?[\divxlc(]"
)
SUBJECT_SLASH = re.compile(r"^(?P<name>[A-ZÀ-ÞĀ-ž][A-ZÀ-ÞĀ-ž'’ .-]{2,40}?)\s+/\s+")
EXTENT_PLACE_YEAR = re.compile(
    r"(?:p\.|leaves|vols\.)(?:\s(?:\d+ )?(?:illus\.|Illustrated\.?|port\.))?\s"
    r"(?P<place>[A-Z][\w'’/ .-]{1,40}?), (?P<open>[\[(])?(?P<year>1[5-9]\d\d|20[0-2]\d)(?P<close>[\])])?"
)
STANDALONE_YEAR = re.compile(
    r"(?<=[.\]] )(?P<open>[\[(])?(?P<year>1[5-9]\d\d|20[0-2]\d)(?P<close>[\])])?(?=[.;,]|\s\[|$)"
)
EVENT_WORD = re.compile(
    r"\b(?:Premiere|Simultaneous premiere|Radio drama|Radio production|Radio opera|"
    r"TV film|Dramatic reading|Stage production|Symposium|Exhibition|Ausstellung|"
    r"Lesung|Colloque|Congress|Kongress|A\s+movie|Theater program|Hörspiel)\b"
)
EVENT_PARTS = frozenset("NP")
# Parts that list Zweig's works and their editions (sections A to J, and the
# stage, film and music versions N and O).
WORK_PARTS = frozenset("ABCDEFGHIJNO")
WORD_EVENT_EXCLUDED = frozenset("HJKLMQR")
# A month as the volumes spell it, and nothing longer: "Janowitz" is no month.
MONTH_WORD = (
    r"(?:[Jj]an(?:uary|uar)?|[Ff]eb(?:ruary|ruar)?|[Mm]ar(?:ch)?|März|[Aa]pr(?:il)?|"
    r"[Mm]ay|Mai|[Jj]une?|Juni|[Jj]uly?|Juli|[Aa]ug(?:ust)?|[Ss]ept?(?:ember)?|"
    r"[Oo]ct(?:ober)?|Okt(?:ober)?|[Nn]ov(?:ember)?|[Dd]ec(?:ember)?|Dez(?:ember)?|"
    r"JAN(?:UARY)?|FEB(?:RUARY)?|MAR(?:CH)?|APR(?:IL)?|MAY|JUNE?|JULY?|AUG(?:UST)?|"
    r"SEPT?(?:EMBER)?|OCT(?:OBER)?|NOV(?:EMBER)?|DEC(?:EMBER)?)\.?(?![A-Za-zÀ-ÿ])"
)
EVENT_DATE = re.compile(
    rf"(?:\d{{1,2}}\.?\s?(?:-\s?\d{{1,2}}\.?\s?)?{MONTH_WORD}"
    rf"(?:\s?-\s?\d{{1,2}}\.?\s?{MONTH_WORD})?,? (?:1[89]|20)\d\d"
    rf"|{MONTH_WORD} \d{{1,2}}(?:\s?-\s?(?:{MONTH_WORD} )?\d{{1,2}})?,? (?:1[89]|20)\d\d"
    rf"|(?:1[89]|20)\d\d\s+{MONTH_WORD}(?: \d{{1,2}})?(?:\s?-\s?(?:{MONTH_WORD} )?\d{{1,2}})?"
    rf"|{MONTH_WORD} (?:1[89]|20)\d\d)"
)
EVENT_PLACE = re.compile(
    r"\]\.\s(?P<place>[A-Z][\w./ -]{1,40}?),\s(?=\d|[A-Z][a-z]+ \d)"
    r"|Premiere(?: \w+)?[,:]\s(?P<pplace>[^.]{3,80}?),\s(?=\d{1,2} \w+\.? \d{4})"
)
REVIEW_LABEL = re.compile(r"\bREV:\s?|\bRe-?\s?view of:\s?")
CONTENTS_LABEL = re.compile(
    r"\b(?:Contents(?:\s?\[[^\]]{1,40}\])?\s?[:.]|Con-\s?tents\s?:|Contains\s?:"
    r"|Zweig references\s?:|Letters, [^:]{3,60}:)"
)
CONTENTS_END = re.compile(r"\bSee\b|\bFIE\s?:|Editions/Reprints\s?:")
CONTENT_ITEM = re.compile(r"\[(?:\d{1,3}[a-z]?|X|[a-z])\]\s?\.\s*")
VOLUME_LABEL = re.compile(r"(?:Vols?|Bd|Tome|Tom)\.\s?[\dIVXL]")
# A sentence end inside a titled contents item; "pp. 353" and "Vol. 2" go on.
CONTENT_SENTENCE_END = re.compile(
    r"(?<!\bpp)(?<!\bp)(?<!\bVol)(?<!\bNo)\.\s+(?=[A-ZÀ-Þ])|\.$"
)
# An edition line opens with its publisher ("Publisher: 383p. Place,
# 1952", "Publisher: Ed. Forename Surname. viii/82p. Place, 1962").
EDITION_LINE = re.compile(
    r"(?P<publisher>(?:[A-Z]\. )*[A-ZÀ-ÞĀ-ž][^:.\[\]\d]{1,60}?):\s"
    rf"(?=[\[(]?\d|[ivxlc]+/\d|{ABBREVIATED}|Shortened|Bilingual|Paperback|New ed|"
    r"Cover design|Drawings|Frontispiece|Photographs)"
)
PLACE_YEAR = re.compile(
    r"(?<![\w-])(?P<place>[A-Z][\w'’/ -]{1,60}?), (?P<open>[\[(])?(?:ca\. )?"
    r"(?P<year>1[5-9]\d\d|20[0-2]\d)(?P<close>[\])])?"
)
MARKER = re.compile(
    r"(?P<marker>Correction to|Cont\.(?: of)?|Rep:|REP:|Reprinted(?: in| as)?:?|"
    r"Contents:|Con-\s?tents:|Contains:?|See(?: also)?:?|see(?: also)?:?|Index|"
    r"EXC(?:ERPTS?)?:?|Excerpts?(?: from)?:?|TRANSLATIONS?:|Translations?:|"
    r"Concerning|Based on|REV:|Reviews?:?|=)\s*$"
)
MARKER_KIND = (
    ("Correction", "correction"),
    ("Cont", "continuation"),
    ("Rep", "reprint"),
    ("REP", "reprint"),
    ("Con", "contents"),
    ("See", "see"),
    ("see", "see"),
    ("Index", "index"),
    ("EXC", "excerpt"),
    ("Exc", "excerpt"),
    ("TRANS", "translation"),
    ("Trans", "translation"),
    ("Concerning", "concerning"),
    ("Based", "based_on"),
    ("REV", "review"),
    ("Review", "review"),
    ("=", "related"),
)
LOCATOR = re.compile(
    r"(?::\s?(?:Kassette|Cassette|Bd\.|Band) [\dIVXL]+"
    r"|,? (?:Vol\. [\dIVXL]+(?:, pp?\. [\divxlc()\[\]-]+)?|pp?\. [\divxlc()\[\]-]+)"
    r"|\s?\((?:\d+|[ivx]+)\)|\[[\dA-Za-z, ./-]{1,24}\])"
)


def quoted_span(m: re.Match) -> tuple[int, int]:
    """Span of the quoted text inside a QUOTED match."""
    name = next(g for g in "abcde" if m.group(g) is not None)
    return m.start(name), m.end(name)


def _strip_span(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start] in " ,;":
        start += 1
    while end > start and text[end - 1] in " ,;":
        end -= 1
    return start, end


def _item_start(item: dict | None) -> int:
    """Where a contents item begins in the entry, for printed order."""
    if not item:
        return -1
    if item.get("title"):
        return item["title"]["span"][0]
    return item["address"]["address"]["span"][0]


def marker_kind(marker: str) -> str:
    return next(kind for prefix, kind in MARKER_KIND if marker.startswith(prefix))


def value(val, start: int, end: int, rule: str, by: str = "rule", source=None) -> dict:
    out = {"value": val, "span": [start, end], "by": by, "rule": rule}
    if source:
        out["from"] = source
    return out


IMPRINT_PLACE = re.compile(
    r"(?<![\w-])(?P<place>[A-ZÀ-ÞĀ-ž][\w'’-]+(?: [A-ZÀ-ÞĀ-ž][\w'’-]+)?): "
    r"[^.;:\[\]]{2,60}?, [\[(]?(?:1[5-9]|20)\d\d"
)
PLACE_MIN = 3
# A place right after one of these words belongs to the title ("Briefe aus
# Place 1980 [3]").
PLACE_GUARD = frozenset(
    "aus in im von nach bei zu zur zum de of from to in à en a au di da w v iz u na "
    "at on och i till y e do od ve".split()
)


def place_lexicon(texts) -> frozenset[str]:
    """Imprint places ("Place: Publisher, 1983") printed at least PLACE_MIN
    times in the corpus: a deterministic gazetteer of the volumes' own places."""
    counts: dict[str, int] = {}
    for text in texts:
        for m in IMPRINT_PLACE.finditer(text):
            counts[m.group("place")] = counts.get(m.group("place"), 0) + 1
    return frozenset(p for p, n in counts.items() if n >= PLACE_MIN)


def author_head(segment: str) -> re.Match | None:
    """An inverted author name opening a cited title ("Surname, Forename.
    Title"). Titles about Zweig ("Stefan Zweig, Noun. ...") and
    titles with a year before the comma share the shape and are no names."""
    head = SURNAME_HEAD.match(segment)
    if not head or re.search(r"\d", head.group("name")):
        return None
    if head.group("name").startswith("Stefan Zweig"):
        return None
    return head


def text_value(text: str, start: int, end: int, rule: str, **kw) -> dict | None:
    """A text value cut from text[start:end], trimmed of spaces and edge punctuation."""
    while start < end and text[start] in " ,;:":
        start += 1
    while end > start and text[end - 1] in " ,;:":
        end -= 1
    if (
        end > start
        and text[end - 1] == "."
        and not re.search(
            r"(?:\b[A-Z]|\b(?:St|Jr|Dr|ed|Co|Inc|Lit|Izd|al|Verl|Nachf|Bros))\.$",
            text[start:end],
        )
    ):
        end -= 1
    # A closing bracket the passage does not open belongs to the context.
    for opening, closing in (("(", ")"), ("[", "]")):
        while (
            end > start
            and text[end - 1] == closing
            and (text.count(opening, start, end) < text.count(closing, start, end))
        ):
            end -= 1
    if end <= start:
        return None
    return value(text[start:end], start, end, rule, **kw)


def language_value(text: str, start: int, end: int, rule: str, **kw) -> dict | None:
    name = LANGUAGE_BY_FOLD.get(text[start:end].lower())
    return value(name, start, end, rule, **kw) if name else None


def inherit(node, source: str):
    """A deep copy of node with every value marked as inherited from source."""
    if isinstance(node, dict):
        if "span" in node and "by" in node:
            return {**node, "by": "inherited", "from": source}
        return {k: inherit(v, source) for k, v in node.items()}
    if isinstance(node, list):
        return [inherit(v, source) for v in node]
    return node


class Reader:
    """Reads one object of an entry; spans are offsets into the entry text.

    ctx holds the address index, the governing label, the next object's start
    and the record identifier; the reader adds what derive_types needs.
    """

    def __init__(self, entry: dict, span: tuple[int, int], ctx: dict):
        self.entry = entry
        self.text = entry["text"]
        self.start, self.end = span
        self.ctx = ctx
        self.out: dict = {}
        self.used: list[tuple[int, int]] = []

    def run(self) -> dict:
        pos = self._prefixes(self.start)
        zone_end = self._zone_end(pos)
        self.zone = (pos, zone_end)
        pos = self._head_person(pos, zone_end)
        title_end = self._title(pos, zone_end)
        self._after_title(title_end, zone_end)
        self._variants(self.start, self.end)
        # A periodical is cited after a quoted title, never inside it; an
        # unquoted first sentence may be the periodical itself ("[1].
        # AUFBNY, 29 Oct. 1982 (Paul F. Proskauer)").
        quoted = (self.out.get("title") or {}).get("rule") == "p03.title-quoted"
        self._periodicals(max(pos, self.after_title) if quoted else pos, zone_end)
        periodical = (self.out.get("periodicals") or [{}])[0]
        first = periodical.get("siglum") or periodical.get("title")
        if (
            not quoted
            and first
            and self.out.get("title")
            and first["span"][0] <= self.out["title"]["span"][0]
        ):
            # The "title" was the periodical's name.
            self.out.pop("title", None)
            self.out.pop("subtitle", None)
        host_start = self._hosts(title_end, zone_end)
        own_end = host_start if host_start is not None else zone_end
        self._own_citation(title_end, own_end)
        title_year = self.ctx.get("title_year")
        if (
            title_year
            and host_start is None
            and not self.out.get("periodicals")
            and not any(i.get("year") for i in self.out.get("imprints", []))
        ):
            year = int(self.text[title_year[0] : title_year[1]])
            self.out.setdefault("imprints", []).insert(
                0, {"year": value(year, *title_year, "p03.title-year")}
            )
        if host_start is not None:
            self._host_citation(host_start, zone_end)
        self._persons(pos, own_end)
        self._edition_notes(title_end, zone_end)
        self._event()
        self._informants(self.start, self.end)
        self._holdings(pos, self.end)
        self._reviewed()
        tail = self._contents()
        refs = self._references(self.start, self.end) + tail
        if refs:
            self.out["references"] = refs
        self._notes(self.start, self.end)
        self._item_as_host()
        self._host_codes()
        return {k: v for k, v in self.out.items() if v not in (None, [], {})}

    def _host_codes(self) -> None:
        """Every cited title, of a host or a periodical, is read alike
        (_normalize_cited), whichever rule found it."""
        for periodical in self.out.get("periodicals", []):
            # "in LA2 Journal Title (Place), 4 (1995)": the schema gives a
            # periodical no address, and its head is no author.
            self._normalize_cited(periodical, author=False, address=False)
        for host in self.out.get("hosts", []):
            self._normalize_cited(host)
        for reviewed in self.out.get("reviewed", []):
            # "Review of: Surname, Forename. Title" names the reviewed
            # work's author before its title.
            self._normalize_cited(reviewed, address=False)

    def _split_code(self, a: int, b: int) -> tuple[dict | None, int, bool]:
        """A cited title led by a section code ("LA2 Title", "AA2 15 Title")
        cites a publication documented in Addendum II: the code with its
        number is the address. A number followed by a lower-case word belongs
        to the title ("FA2 24 words"). Returns (address, title start, coded)."""
        m = HOST_CODE.match(self.text, a, b)
        if not m:
            return None, a, False
        address = None
        if re.search(r"\s\d", m.group("code")):
            refs = self.addresses(m.start("code"), m.end("code"))
            address = refs[0] if refs else None
        return address, m.end(), True

    def _split_author(self, a: int, b: int) -> tuple[list[dict], int, int]:
        """A cited title led by its authors ("Surname, Forename. Title", "F.
        Surname. Title", or the names alone with the title in the next
        sentence). Returns (authors, title start, title end)."""
        text = self.text
        head = author_head(text[a:b]) or INITIAL_AUTHOR.match(text[a:b])
        spans = [(a + head.start("name"), a + head.end("name"))] if head else []
        end = a + head.end() if head else a
        gloss = None if head else EDITOR_GLOSS.match(text, b, self.zone[1])
        if gloss and FORENAME_AUTHORS.fullmatch(text, a, b):
            # "Forename Surname [Ed.]. Title. Place: ..." names the editors,
            # then the title.
            c = gloss.end()
            stop = HOST_TITLE_END.search(text, c, self.zone[1])
            d = self._credit_cut(c, stop.start() if stop else self.zone[1])
            role = gloss.span("role")
            editors = []
            for m in FORENAME.finditer(text, a, b):
                name = text_value(text, *m.span(), "p03.host-editor")
                if name:
                    editors.append(
                        {
                            "name": name,
                            "roles": [value("editor", *role, "p03.host-editor")],
                        }
                    )
            return (editors, c, d) if editors and d > c else ([], a, b)
        if not head:
            # "Forename Surname, Forename Surname. Title: Subtitle. Place:
            # ...": names forename first stand alone where the title was cut
            # before a sentence with a colon, which the cut took for an
            # imprint. Without that colon "Two Words. Subtitle" is a title.
            names = FORENAME_AUTHORS.fullmatch(text, a, b)
            after = re.compile(r"\.\s+").match(text, b, self.zone[1])
            if not names or not after:
                return [], a, b
            at = after.end()
            stop = HOST_TITLE_END.search(text, at, self.zone[1])
            if (
                not stop
                or not re.match(r"\.\s", stop.group())
                or ": " not in text[at : stop.start()]
                # The title sentence ends before an imprint, a credit or an
                # edition; "Two Words. Band 4: Part" is a title's volume.
                or not (
                    CITATION_AFTER_TITLE.match(text, stop.end(), self.zone[1])
                    or CREDIT.match(text, stop.end(), self.zone[1])
                )
                or VOLUME_WORD.match(text, at, self.zone[1])
                or IMPRINT_AHEAD.match(text, at, self.zone[1])
                or CREDIT.match(text, at, self.zone[1])
                or CREDIT_SENTENCE.match(text, at, self.zone[1])
                or any(p.match(text, at, self.zone[1]) for _, p in EDITION_NOTES)
            ):
                return [], a, b
            spans = [m.span() for m in FORENAME.finditer(text, a, b)]
            end = b
        persons = []
        for s, e in spans:
            name = text_value(text, s, e, "p03.head-author")
            if name:
                persons.append(
                    {
                        "name": name,
                        "roles": [value("author", *name["span"], "p03.head-author")],
                    }
                )
        if not persons:
            return [], a, b
        c, d = end, b
        if end >= b:
            # '"Essay", F. Surname. Title: Subtitle. Place: ...': the title is
            # the sentence after the name.
            after = re.match(r"\.\s+", text[spans[-1][1] : self.zone[1]])
            if not after:
                return [], a, b
            c = spans[-1][1] + after.end()
            stop = HOST_TITLE_END.search(text, c, self.zone[1])
            d = self._credit_cut(c, stop.start() if stop else self.zone[1])
        return persons, c, d

    def _unquoted(self, c: int, b: int, rule: str) -> dict | None:
        """A cited title text[c:b]; "LA2 “Title . . .”": quotes that enclose
        the whole title are no part of it, its own final dots are."""
        text = self.text
        if (
            c < b - 1
            and text[c] in QUOTE_OPEN
            and text[b - 1] in '”"“’'
            and not re.search(r'[”"]', text[c + 1 : b - 1])
        ):
            c, b = c + 1, b - 1
            while c < b and text[c].isspace():
                c += 1
            while b > c and text[b - 1].isspace():
                b -= 1
            return value(text[c:b], c, b, rule) if c < b else None
        return text_value(text, c, b, rule)

    def _normalize_cited(
        self, node: dict, author: bool = True, address: bool = True
    ) -> None:
        """Section code to address, a leading author to a person, the rest the title."""
        title = node.get("title")
        if not title:
            return
        text, rule = self.text, title["rule"]
        a, b = title["span"]
        found, c, coded = self._split_code(a, b)
        if coded:
            if address and found and not node.get("address"):
                node["address"] = found
            rest = self._unquoted(c, b, rule)
            if not rest:
                if address and node.get("address"):
                    node.pop("title")
                return
            node["title"] = title = rest
            a, b = title["span"]
        if not author:
            return
        persons, c, d = self._split_author(a, b)
        rest = text_value(text, c, d, rule) if persons else None
        if rest:
            node["persons"] = [*persons, *node.get("persons", [])]
            node["title"] = rest

    def _item_as_host(self) -> None:
        """A reprint or list item that cites a volume with a page locator, or by
        section code, names the host the work appeared in: "[2]. Title. Ed.
        Forename Surname. Place: Publisher, 1983, p. 221". Title, imprint,
        extent, series and editors move to the host. A title led by a section
        code always names a publication documented elsewhere in Addendum II,
        whatever label governs the item."""
        o, text = self.out, self.text
        title = o.get("title")
        if title and o.get("hosts") and SECTION_ADDRESS_ONLY.fullmatch(title["value"]):
            # "[2]. AA2 12" cites its host by address alone, read in _hosts.
            o.pop("title")
            return
        if o.get("hosts") or not (title or o.get("imprints")):
            return
        code = HOST_CODE.match(text, *title["span"]) if title else None
        if o.get("periodicals"):
            if code:
                self._code_host_before_contribution()
            return
        if not code and self.ctx.get("label_kind") not in (
            "reprint",
            "item",
            "excerpt",
            "translation",
            "revised",
        ):
            return
        start = title["span"][1] if title else self.zone[0]
        pages = PAGES.search(text, start, self.zone[1])
        if not pages and not code:
            return
        host: dict = {}
        if title:
            # The whole title moves; _normalize_cited reads its code later.
            a = title["span"][0]
            b = (o.get("subtitle") or title)["span"][1]
            host["title"] = text_value(text, a, b, title["rule"])
        numbered = code and re.search(r"\s\d", code.group("code"))
        if not numbered and len(o.get("work_refs", [])) == 1:
            host["address"] = o["work_refs"][0]
        if not (host.get("title") or host.get("address")):
            # A host that names no title and no address cannot stand; the
            # imprint stays the object's.
            return
        if title:
            o.pop("title")
            o.pop("subtitle", None)
        if host.get("address"):
            o.pop("work_refs")
        for key in ("imprints", "extent", "series"):
            if o.get(key):
                host[key] = o.pop(key)
        editors = [
            p
            for p in o.get("persons", [])
            if all(r["value"] == "editor" for r in p["roles"])
        ]
        if editors:
            host["persons"] = editors
            o["persons"] = [p for p in o["persons"] if p not in editors]
        if pages:
            host["pages"] = text_value(
                text, pages.start("pages"), pages.end("pages"), "p03.host-pages"
            )
        host = {k: v for k, v in host.items() if v}
        if host.get("title") or host.get("address"):
            o["hosts"] = [host]

    def _code_host_before_contribution(self) -> None:
        """In "[6]. FA2 Collection 1963. “Story” [1927] in Periodical, ..." the
        code-led title names the collection, the quoted title the item, and the
        periodical its first printing. The collection's title keeps its code
        for _normalize_cited."""
        o, text = self.out, self.text
        title = o["title"]
        a, b = title["span"]
        _, start, _ = self._split_code(a, b)
        quoted = re.compile(r"\.\s+(?=[“\"„‘])").search(text, start, b)
        if not quoted:
            return
        host = text_value(text, a, quoted.start(), title["rule"])
        c, d = quoted.end() + 1, b
        if d > c and text[d - 1] in '”"“’':
            d -= 1
        item = text_value(text, c, d, title["rule"])
        if not host or not item or quoted.start() <= start:
            return
        o["title"] = item
        o["hosts"] = [{"title": host}]

    # prefixes, zone, head and title

    def _prefixes(self, pos: int) -> int:
        text = self.text
        if pos == 0 and self.entry["address"]:
            m = NUMBER_PREFIX.match(text)
            if m:
                pos = m.end()
        m = ITEM_MARK.match(text, pos) or STUB_MARK.match(text, pos)
        if m:
            pos = m.end()
        m = CODE_LANGUAGE.match(text, pos)
        if m and m.group("lang").lower() in LANGUAGE_BY_FOLD:
            # "[1]. LA2 [French], Title. ..." names the section and the
            # language of the item.
            self.out["language"] = language_value(
                text, m.start("lang"), m.end("lang"), "p03.language-prefix"
            )
            return m.end()
        m = LANGUAGE_PREFIX.match(text, pos)
        if m and m.group(1).lower() in LANGUAGE_BY_FOLD:
            self.out["language"] = language_value(
                text, m.start(1), m.end(1), "p03.language-prefix"
            )
            pos = m.end()
        else:
            self._language_label()
        m = VOLUME_PREFIX.match(text, pos)
        if m:
            number = value(
                m.group("number"), m.start("number"), m.end("number"), "p03.set-volume"
            )
            self.out.setdefault("series", []).append({"number": number})
            pos = m.end()
        m = YEAR_PREFIX.match(text, pos)
        if m:
            pos = m.end()
        return pos

    def _language_label(self) -> None:
        """A language label before an item in the same entry ("French: [1]. ...")."""
        if self.start == 0:
            return
        found = None
        for m in LANGUAGE_LABEL.finditer(self.text, 0, self.start):
            if m.group(1).lower() in LANGUAGE_BY_FOLD:
                found = m
        if found:
            self.out["language"] = language_value(
                self.text,
                found.start(1),
                found.end(1),
                "p03.language-label",
                source=self.entry["id"],
            )

    def _zone_end(self, pos: int) -> int:
        # A label inside brackets ("[H 115 / G 131. See G 200]") ends nothing.
        depth = 0
        depths = []
        for ch in self.text[pos : self.end]:
            depths.append(depth)
            if ch in "[(":
                depth += 1
            elif ch in "])" and depth:
                depth -= 1
        for m in ZONE_END.finditer(self.text, pos, self.end):
            if depths[m.start() - pos] == 0:
                return m.start()
        return self.end

    def _head_person(self, pos: int, zone_end: int) -> int:
        part, text = self.entry["part"], self.text
        role = HEAD_ROLE.get(part)
        # The head may stand right before a label that ends the zone
        # ("Surname, Forename. See: ..."), so it is read to the object's end.
        if not role and self.entry["volume"] == "A1" and part in "CG":
            # Addendum I files its essays and studies under their subject.
            role = "subject"
        code = re.match(
            r"[A-R]{1,2}A2\s+(?=[A-ZÀ-ÞĀ-ž][\w'’-]+, [A-ZÀ-ÞĀ-ž])", text[pos : self.end]
        )
        if code and role and SURNAME_HEAD.match(text[pos + code.end() : self.end]):
            # "LA2 Surname, Forename. ..." cites by section code, then names
            # the author.
            pos += code.end()
        local = text[pos : self.end]
        m = (SURNAME_HEAD.match(local) or INITIALS_HEAD.match(local)) if role else None
        if (
            m
            and part == "K"
            and role == "subject"
            and text[self.start] == "["
            and re.search(r"[a-zß-ÿ]", m.group("name"))
        ):
            # The letters file under the correspondent in capitals; an item
            # "[4]. Surname, Forename. L 12, pp. ..." names the author of a
            # publication that prints the letters.
            role = "author"
        if not m and (
            part in "LM"
            or self.ctx.get("label_kind")
            or (part in "HP" and text[self.start] == "[")
        ):
            # A review, reprint, essay or talk item opens with its author:
            # "[1]. Forename Surname. “Title ...” in ...".
            m = FORENAME_HEAD.match(local)
            if (
                not m
                and self.ctx.get("label_kind") == "review"
                and text[self.start] == "["
            ):
                # "REV: [1]. Forename Surname. Title. Trl. ..." lists the books
                # Zweig reviewed, each opening with its author.
                m = REVIEWED_HEAD.match(local)
            if m:
                role = "author" if role in (None, "subject") else role
        if not m and role in ("author", "subject"):
            # "SURNAME, FORENAME [Ed./Intro.]. Title ..." names the
            # head's roles in brackets; "Surname, Forename & Forename Surname."
            # names two authors.
            m = HEAD_WITH_CREDIT.match(local) or HEAD_PAIR.match(local)
        if not m and role == "subject":
            # "STENDHAL / ..." files an essay under a one-word subject.
            m = SUBJECT_SLASH.match(local)
        if m and re.search(r"\([A-R](?:A[12])? \d", m.group("name")):
            # "Short Title (I 126), Vol. 3, p. 631" cites a volume by its
            # address; a name holds no address.
            return pos
        if not m or not role:
            return pos
        a, b = pos + m.start("name"), pos + m.end("name")
        name = text_value(text, a, b, f"p03.head-{role}")
        if not name:
            return pos
        credit = m.groupdict().get("credit")
        if credit and not any(
            w.rstrip(".").lower() in ROLE_WORDS
            for w in re.findall(r"[A-Za-z]+\.?", credit)
        ):
            credit = None
        if credit:
            roles = [
                value(
                    ROLE_WORDS[w.group().rstrip(".").lower()],
                    pos + m.start("credit") + w.start(),
                    pos + m.start("credit") + w.end(),
                    "p03.credit",
                )
                for w in re.finditer(r"[A-Za-z]+\.?", credit)
                if w.group().rstrip(".").lower() in ROLE_WORDS
            ]
            if roles:
                self.out.setdefault("persons", []).append(
                    {"name": name, "roles": roles}
                )
                return pos + m.end()
        if role == "subject":
            self.out["subject"] = name
        else:
            self.out.setdefault("persons", []).append(
                {
                    "name": name,
                    "roles": [value(role, *name["span"], f"p03.head-{role}")],
                }
            )
            if m.groupdict().get("second"):
                second = text_value(
                    text,
                    pos + m.start("second"),
                    pos + m.end("second"),
                    f"p03.head-{role}",
                )
                if second:
                    self.out["persons"].append(
                        {
                            "name": second,
                            "roles": [value(role, *second["span"], f"p03.head-{role}")],
                        }
                    )
        return pos + m.end()

    def _title(self, pos: int, zone_end: int) -> int:
        text = self.text
        while pos < zone_end and text[pos] == " ":
            pos += 1
        if pos >= zone_end:
            return pos
        if text[pos] in QUOTE_OPEN:
            m = QUOTED.match(text, pos, self.end)
            if m:
                title = text_value(text, *quoted_span(m), "p03.title-quoted")
                if title:
                    self.out["title"] = title
                return m.end()
        # The spelled periodical form belongs to the addenda; the main volume
        # cites periodicals by siglum ("SIGLUM, 54:1358 (19 Oct. 1935)").
        if (
            self.ctx.get("label_kind")
            and self.entry["volume"] != "I"
            and SPELLED_AT_START.match(text, pos, zone_end)
        ):
            self.ctx["periodical_start"] = True
            return pos
        item = text[self.start] == "["
        source = (
            LETTER_SOURCE.match(text, pos, self.end)
            if self.entry["part"] == "K" and item
            else None
        )
        cited = source and CITED_AFTER_SOURCE.match(text, source.end(), self.end)
        if cited:
            # "[1]. Library (Place), Catalogue Title [LA1 10], p. 83, ..."
            # names the source, then the publication that prints the letter.
            pos = cited.end()
        elif source:
            # "[1]. Archive (Place)," before the items it holds, or "[2].
            # Dealer (Place), Katalog 5, ...": the source is no title.
            return pos
        elif self.entry["part"] == "K" and (
            HOLDING_REPOSITORY.match(text, pos, zone_end)
            or (item and HOLDING_LETTERS.search(text, pos, self.end))
        ):
            # "SIGL: Zweig to X, ..." names a repository, "[1]. Dealer
            # (Place), Katalog ..., Zweig to X, 1 letter" its source; neither
            # is a title.
            return pos
        if manuscript_item(text, self.start):
            # "Manuscript versions: [2]. Library, Place, Shelfmark" names
            # where a version is kept, no title.
            return pos
        if self.entry["part"] == "N" and item:
            # A production item opens with its venue and date ("[1].
            # Staatstheater, Dresden (Großes Haus), 1974."); its work is the
            # entry's.
            return pos
        if re.match(r"N\.?B\.?:", text[pos:zone_end]):
            # "NB: See Index A1." is the compiler's note, with no title.
            return pos
        if EDITION_LINE.match(text, pos, zone_end):
            # "Publisher: 299/(2)p. Place, 1984" is an edition line, which
            # also has the shape of an imprint; it carries no title of its
            # own, and p03 inherits the title of its work heading or of the
            # entry it continues.
            self.ctx["edition_line"] = True
            return pos
        # The place holds no dot or digit, so a title sentence before an
        # imprint ("Title. 97p. Place: Publisher, 1942") does not count.
        if re.match(
            r"[A-ZÀ-ÞĀ-ž][A-Za-zÀ-ÿĀ-ž'’/ -]{1,40}?(?:,\s[A-Z]{2})?: [^:]{2,80}?, [\[(]?(?:1[5-9]|20)\d\d",
            text[pos:zone_end],
        ):
            # "[2]. Place: Publisher, Inc., 1984." opens with
            # its imprint.
            return pos
        if self.entry["part"] == "P":
            speaker = SPEAKER.match(text, pos, zone_end)
            if speaker and item:
                # "[1]. Forename Surname (Institution): Talk title ..."
                name = text_value(
                    text, speaker.start("name"), speaker.end("name"), "p03.speaker"
                )
                if name:
                    self.out.setdefault("persons", []).append(
                        {
                            "name": name,
                            "roles": [
                                value("contributor", *name["span"], "p03.speaker")
                            ],
                        }
                    )
                pos = speaker.end()
            else:
                # "FEBRUARY 18 - 23, 1992: Title ..." and
                # "NOVEMBER 30, 1994 - FEBRUARY 3, 1995: ..." open with the
                # event's dates; the title follows the colon.
                colon = text.find(": ", pos, min(zone_end, pos + 60))
                head = text[pos:colon] if colon > 0 else ""
                if (
                    head
                    and YEAR.search(head)
                    and (EVENT_DATE.match(text, pos, colon) or YEAR.match(text, pos))
                ):
                    pos = colon + 2
                    self.ctx["title_after_date"] = True
        ref = (
            TITLE_REF.match(text, pos, self.end)
            if self.entry["volume"] == "A2"
            else None
        )
        if ref and re.search(
            rf"{ABBREVIATED}|\b(?:Edited|Translated)\b|: ", ref.group("title")
        ):
            # A full citation with credits or an imprint is no title reference.
            ref = None
        if ref and (ref.group("code") or ref.group("no") or ref.group("no2")):
            # The title is the collection's, so it belongs to the host.
            self.ctx["title_ref"] = ref
            return pos
        if self.ctx.get("label_kind") == "edition":
            publisher = EDITION_PUBLISHER.match(text, pos, zone_end)
            if publisher:
                self.ctx["edition_publisher"] = publisher.span("publisher")
                # "Publisher Verlag [Series]. ..."
                series = SERIES.match(text, publisher.end(), zone_end)
                if series and not SERIES_STOP.search(series.group("title")):
                    entry = {
                        "title": text_value(
                            text,
                            series.start("title"),
                            series.end("title"),
                            "p03.series",
                        )
                    }
                    if series.group("number"):
                        entry["number"] = text_value(
                            text,
                            series.start("number"),
                            series.end("number"),
                            "p03.series",
                        )
                    entry = {k: v for k, v in entry.items() if v}
                    if entry:
                        self.out.setdefault("series", []).append(entry)
                        self.used.append(series.span())
                return publisher.end()
        address = REFERENCE.match(text, pos, zone_end)
        if address and re.match(
            r"\s?[:,.;]|\s?$", text[address.end() : address.end() + 2]
        ):
            # An item that opens with an address names a volume, not a title.
            return pos
        if EDITION_LINE.match(text, pos, zone_end):
            # An edition line carries no title of its own; p03 inherits the
            # title of its work heading or of the entry it continues.
            self.ctx["edition_line"] = True
            return pos
        if (
            re.match(r"[\d(]", text[pos])
            or CREDIT.match(text, pos, zone_end)
            or any(p.match(text, pos, zone_end) for _, p in EDITION_NOTES)
        ):
            # A printing, a credit ("[1]. Pref. by the author") or an edition
            # statement ("[1]. Large print ed.") names no title.
            return pos
        end = self._title_end(pos, zone_end)
        segment = text[pos:end]
        split = re.search(r": (?=\S)", segment) or next(
            (
                m
                for m in re.finditer(
                    r"(?<![A-Z])(?<!\b[A-Z][a-z])(?<!\bSt)(?<!\bDr)\. (?=[A-ZÀ-ÞĀ-ž])",
                    segment,
                )
                if not ORDINAL_BEFORE.search(segment, 0, m.start())
                and not re.match(MONTH_WORD, segment[m.end() :])
            ),
            None,
        )
        if split:
            title = text_value(text, pos, pos + split.start(), "p03.title")
            subtitle = text_value(text, pos + split.end(), end, "p03.subtitle")
            if (
                subtitle
                and re.search(r"[^\W\d_]", subtitle["value"])
                and not FORMAT_NOTE.fullmatch(subtitle["value"])
            ):
                self.out["subtitle"] = subtitle
        else:
            title = text_value(text, pos, end, "p03.title")
        # "No. 166 (...)" and "pp." open an issue or a locator, no title.
        if (
            title
            and re.search(r"[^\W\d_]{2}", title["value"])
            and not re.fullmatch(r"(?:No|Nr|Nos|pp?)\.?", title["value"])
        ):
            self.out["title"] = title
        else:
            self.out.pop("subtitle", None)
        return end

    def _title_end(self, pos: int, zone_end: int) -> int:
        text = self.text
        stops = [zone_end]
        for pattern in (
            re.compile(r"\s[\[(]"),
            # Joined lines leave double spaces ("Title.  97p."), hence \s+.
            re.compile(
                rf"\.\s+(?={ABBREVIATED}|[A-Z][a-z]+(?: [a-z]+){{0,6}} by\b|By\s|"
                rf"\(?\d|[ivxlc]+/|Vol|(?:Bd|Bde|Band)\.?\s[\dIVXL]|In |in |\[|{IMPRINT_PLACE_RUN}|"
                r"(?:Trl|Tr|Translator)\b)"
            ),
            re.compile(r"\.\s+[^\s]*\d"),
            re.compile(r",\s(?=[A-ZÄÖÜÉ]{4,9}, \d)"),
            # "Title, pp. 12-14" and "Title, G 626, pp. 323" end before the
            # locator.
            re.compile(
                r",\s+(?=(?:[A-R] \d{1,4}[a-z]?,\s+)?(?:pp?\.|S\.)\s*[\divxlc(\[])"
            ),
            re.compile(
                rf"[,.]\s(?={IMPRINT_PLACE_RUN}[^,]{{2,80}}, [\[(]?(?:1[5-9]|20)\d\d)"
            ),
        ):
            m = pattern.search(text, pos, zone_end)
            if m:
                stops.append(m.start())
        # A sentence that opens with a credit or an edition statement ends the
        # title ("... Title. Editor-in-chief ...", "... Large print ed.").
        for m in re.finditer(r"\.\s+", text[pos:zone_end]):
            at = pos + m.end()
            if (
                CREDIT.match(text, at, zone_end)
                or CREDIT_SENTENCE.match(text, at, zone_end)
                or any(p.match(text, at, zone_end) for _, p in EDITION_NOTES)
            ):
                stops.append(pos + m.start())
                break
        # "in" ends a title only where a periodical citation follows; inside a
        # title it is a word ("A Drama in Nine Scenes").
        for m in re.finditer(r"\s(?=in [A-Z„“\"])", text[pos:zone_end]):
            if SPELLED_PERIODICAL.match(text, pos + m.end(), zone_end):
                stops.append(pos + m.start())
                break
        return min(stops)

    def _after_title(self, pos: int, zone_end: int) -> None:
        """Brackets right after the title: work addresses and an original title."""
        text = self.text
        self.after_title = pos
        while pos < zone_end:
            while pos < zone_end and text[pos] in " .":
                pos += 1
            if (
                pos < zone_end
                and text[pos] in QUOTE_OPEN
                and (self.out.get("title") or {}).get("rule") == "p03.title"
            ):
                # "Work [E 11, 15]. "Contribution"" names the work,
                # then the contribution, whose title is the quoted one.
                quoted = QUOTED.match(text, pos, self.end)
                if quoted:
                    self.out["title"] = text_value(
                        text, *quoted_span(quoted), "p03.title-quoted"
                    )
                    self.out.pop("subtitle", None)
                    self.after_title = pos = quoted.end()
                    continue
            if pos >= zone_end or text[pos] not in "[(":
                return
            close = "]" if text[pos] == "[" else ")"
            depth, j = 0, pos
            while j < self.end:
                if text[j] in "[(":
                    depth += 1
                elif text[j] in "])":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            if j >= self.end or text[j] != close:
                return
            inner_start, inner_end = pos + 1, j
            inner = text[inner_start:inner_end]
            year = re.fullmatch(r"\s*((?:1[5-9]|20)\d\d)\s*", inner)
            if year and close == ")":
                # "Surname, F. "Title" (1942) [L 12]" dates the item itself.
                self.ctx["title_year"] = (
                    inner_start + year.start(1),
                    inner_start + year.end(1),
                )
            first = REFERENCE.search(inner)
            if first:
                self.out.setdefault("work_refs", []).extend(
                    self.addresses(inner_start, inner_end)
                )
            head = inner if not first else inner[: first.start()]
            if head.strip() and not self.out.get("original_title"):
                self._original_title(inner_start, head)
            self.used.append((pos, j + 1))
            pos = j + 1
            self.after_title = pos

    def _original_title(self, start: int, head: str) -> None:
        text = self.text
        lead = len(head) - len(head.lstrip())
        quoted = QUOTED.match(text, start + lead, start + len(head))
        if quoted:
            self.out["original_title"] = text_value(
                text, *quoted_span(quoted), "p03.original-title-quoted"
            )
            return
        # A gloss stands in square brackets; "(Berlin)" after a name is a
        # place, "[BVC]" an informant.
        if (
            not self._translated()
            or text[start - 1] != "["
            or not re.match(r"[A-ZÀ-ÞĀ-ž]", head)
            or re.fullmatch(r"[A-Z]{2,5}", head.strip())
        ):
            return
        if re.search(
            r"\d|\b(?:Trl?|Translated|Under|Here|Rep|REP|See|Orig|Based|From|Chapter|"
            r"Excerpt|Paperback|Film|Lic|Printed|Concerning)\b",
            head,
        ):
            return
        cut = re.search(r"\.\s|\s/\s|\.$", head)
        end = start + (cut.start() if cut else len(head))
        # An English gloss ("[The Best of ...]") renders the
        # title; it names no original.
        if re.search(
            r"\b(?:The|of|and|Selected|Works|Collected|Stories)\b", text[start:end]
        ):
            return
        self.out["original_title"] = text_value(
            text, start, end, "p03.original-title-gloss"
        )

    def _translation(self) -> bool:
        """A translator credit read so far, or another language than German in
        the parts that list Zweig's works (secondary literature in French is
        no translation)."""
        return (self._translated() and self.entry["part"] in WORK_PARTS) or any(
            r["value"] == "translator"
            for p in self.out.get("persons", [])
            for r in p["roles"]
        )

    def _names_a_person(self, head: str, extra: list[dict]) -> bool:
        """The words of head are those of a person the object credits."""
        words = set(re.findall(r"[^\W\d_]+", head.lower()))
        for p in [*self.out.get("persons", []), *extra]:
            name = p.get("name")
            if name and words == set(re.findall(r"[^\W\d_]+", name["value"].lower())):
                return True
        return False

    def _translated(self) -> bool:
        own = self.out.get("language")
        if own:
            return own["value"] != "German"
        language = self.ctx.get("language")
        return bool(language) and language != "German"

    def _variants(self, s: int, e: int) -> None:
        for m in VARIANT.finditer(self.text, s, e):
            for q in QUOTED.finditer(self.text, m.start(), m.end()):
                v = text_value(self.text, *quoted_span(q), "p03.variant-title")
                if v:
                    self.out.setdefault("variant_titles", []).append(v)
            self.used.append((m.start(), m.end()))

    # citations

    def _periodicals(self, pos: int, zone_end: int) -> None:
        text = self.text
        found = []
        at_start = (
            SPELLED_AT_START.match(text, pos, zone_end)
            if self.ctx.get("periodical_start")
            else None
        )
        if at_start:
            citation = self._periodical(at_start, "p03.periodical-spelled")
            if citation:
                found.append((at_start.start(), at_start.end(), citation))
        for pattern, rule in (
            (SPELLED_PERIODICAL, "p03.periodical-spelled"),
            (SIGLUM_PERIODICAL, "p03.periodical-siglum"),
        ):
            if found:
                break
            for m in pattern.finditer(text, pos, zone_end):
                if any(a < m.end() and m.start() < b for a, b, _ in found):
                    continue
                citation = self._periodical(m, rule)
                if citation:
                    found.append((m.start(), m.end(), citation))
            if found:
                break
        if not found:
            return
        found.sort(key=lambda f: f[0])
        citations = [c for _, _, c in found]
        # A story printed in several issues: "11:10 (1937), 292-293. 11:11 ..."
        last_end = found[-1][1]
        for m in CONTINUED_ISSUE.finditer(text, last_end, zone_end):
            if m.start() != last_end:
                break
            base = {
                k: v
                for k, v in citations[-1].items()
                if k in ("title", "siglum", "place")
            }
            citation = dict(base)
            for field, group in (
                ("volume", "volume"),
                ("issue", "issue"),
                ("issue", "nissue"),
                ("date", "date"),
                ("pages", "pages"),
            ):
                if m.group(group):
                    citation[field] = text_value(
                        text, m.start(group), m.end(group), "p03.periodical-continued"
                    )
            year = YEAR.search(m.group("date"))
            if year:
                a = m.start("date") + year.start(1)
                citation["year"] = value(
                    int(year.group(1)), a, a + 4, "p03.periodical-continued"
                )
            citations.append({k: v for k, v in citation.items() if v})
            last_end = m.end()
        self.out["periodicals"] = citations
        self.used.extend((a, b) for a, b, _ in found)

    def _periodical(self, m: re.Match, rule: str) -> dict | None:
        text, groups, out = self.text, m.groupdict(), {}
        for field, names in (
            ("title", ("title",)),
            ("siglum", ("siglum",)),
            ("place", ("place",)),
            ("volume", ("volume",)),
            ("issue", ("issue", "nissue", "sissue")),
            ("date", ("date", "ndate", "sdate", "mdate")),
            ("pages", ("pages",)),
        ):
            for name in names:
                if groups.get(name):
                    v = text_value(text, m.start(name), m.end(name), rule)
                    if v:
                        out[field] = v
                    break
        if "siglum" in out and re.fullmatch(r"[IVXLC]+", out["siglum"]["value"]):
            return None
        # "in Journal ... [LA1 3], No. 7" cites the periodical's entry, no place.
        if "place" in out and REFERENCE.fullmatch(out["place"]["value"]):
            del out["place"]
        # "Zweig to X, 1 letter [EXC], 31 Dec. 1910" is a holding: a
        # siglum stands where the place would.
        if "place" in out and re.fullmatch(r"[A-Z]{2,6}", out["place"]["value"]):
            return None
        # "[Reprinted 1997]" or "(Copy. 4 typed pages)" in the place's position
        # is a note, so the citation is no periodical.
        if "place" in out and re.search(r"\d", out["place"]["value"]):
            return None
        if "date" in out:
            year = YEAR.search(out["date"]["value"])
            if year:
                a = out["date"]["span"][0] + year.start(1)
                out["year"] = value(int(year.group(1)), a, a + 4, rule)
        if not (out.get("title") or out.get("siglum")):
            return None
        return out

    def _credit_cut(self, a: int, b: int) -> int:
        """End of a cited title before the first sentence that opens with a
        credit, an edition statement, an extent or a bracketed imprint."""
        # The sentence is matched to the zone's end, since the cut b may fall
        # before the dot that closes its credit ("Title. New ed. Place: ...").
        end = max(b, self.zone[1])
        for m in re.finditer(r"[.?!]\s+", self.text[a:b]):
            at = a + m.end()
            if (
                CREDIT.match(self.text, at, end)
                or CREDIT_SENTENCE.match(self.text, at, end)
                or any(p.match(self.text, at, end) for _, p in EDITION_NOTES)
            ):
                # A question or exclamation mark belongs to the title.
                return a + m.start() + (self.text[a + m.start()] != ".")
        return b

    def _hosts(self, pos: int, zone_end: int) -> int | None:
        """Host volumes; returns where the first host citation starts."""
        if self.out.get("periodicals"):
            return None
        text, hosts, starts = self.text, [], []
        ref = self.ctx.get("title_ref") or self._title_ref_after_in()
        if ref:
            t0, t1 = ref.start("title"), ref.end("title")
            host = {}
            # "Surname, F. “Essay” in Host [1992], ...": the essay is the
            # object, its author the object's. A host's own author ("Surname,
            # Forename. Title 1967 [9]") is read by _normalize_cited.
            authors, c, _ = self._split_author(t0, t1)
            inner = (
                re.compile(r"[“\"„](?P<q>[^”\"“]{2,200})[”\"]\s+in\s+").match(
                    text, c, t1
                )
                if authors
                else None
            )
            if inner:
                self.out["title"] = text_value(
                    text, inner.start("q"), inner.end("q"), "p03.title-reference"
                )
                self.out.setdefault("persons", []).extend(authors)
                t0 = inner.end()
            # "Title Place 1998 [3]" gives the place before the year; a place
            # is a word the volumes print as an imprint place.
            place = None
            tail = re.search(
                r"(?:^|\s)(?P<before>\S+)\s(?P<place>[A-ZÀ-ÞĀ-ž][\w'’-]+(?: [A-ZÀ-ÞĀ-ž][\w'’-]+)?)$",
                text[t0:t1],
            )
            if (
                tail
                and tail.group("place") in self.ctx.get("places", ())
                and tail.group("before").lower() not in PLACE_GUARD
            ):
                place = text_value(
                    text,
                    t0 + tail.start("place"),
                    t0 + tail.end("place"),
                    "p03.title-reference",
                )
                if place:
                    t1 = t0 + tail.start("place")
            host["title"] = self._unquoted(t0, t1, "p03.title-reference")
            code = ref.group("code")
            if code and re.search(r"\d", code):
                refs = self.addresses(ref.start("code"), ref.end("code"))
                if refs:
                    host["address"] = refs[0]
            year = (
                "byear" if ref.group("byear") else "year" if ref.group("year") else None
            )
            if year:
                host["imprints"] = [
                    {
                        "year": value(
                            int(ref.group(year)),
                            ref.start(year),
                            ref.end(year),
                            "p03.title-reference",
                        )
                    }
                ]
                close = re.compile(r"(?:/\s?\d{2,4})?[\])]").match(text, ref.end(year))
                if year == "byear" and close:
                    # "Title [1992], No. 51": the year stands in brackets.
                    host["imprints"][0]["year_bracketed"] = value(
                        True, ref.start(year) - 1, close.end(), "p03.title-reference"
                    )
            if place and host.get("title"):
                host.setdefault("imprints", [{}])[0]["place"] = place
            number = "no" if ref.group("no") else "no2" if ref.group("no2") else None
            if number:
                host["locator"] = value(
                    ref.group(number),
                    ref.start(number),
                    ref.end(number),
                    "p03.title-reference",
                )
            host["pages"] = text_value(
                text, ref.start("pages"), ref.end("pages"), "p03.title-reference"
            )
            host = {k: v for k, v in host.items() if v}
            if host.get("title") or host.get("address"):
                self.out["hosts"] = [host]
                self.used.append(ref.span())
                return ref.start()
        if self.ctx.get("label_kind") in (
            "reprint",
            "item",
            "excerpt",
            "translation",
            "revised",
            "edition",
        ):
            # A reprint item that is only an address ("[1]. D 1, 3.", "[2]. L
            # 571, p. 207", "[2]. AA2 57: Kassette IV") appeared in the volumes
            # it names.
            m = REFERENCE.match(text, self.zone[0])
            rest = text[m.end() : self.end] if m else ""
            if m and re.fullmatch(
                r"(?:,?\s?(?:Vol\.\s?[\dIVXL]+|pp?\.\s?[\divxlc()\[\]-]+|\(\d+\)|\[[^\[\]]*\])"
                r"|:\s?(?:Kassette|Cassette|Vol\.|Bd\.|Band)\s[\dIVXL]+)*[.\s]*",
                rest,
            ):
                refs = self.addresses(m.start(), m.end())
                if refs:
                    host = {"address": refs[0]}
                    pages = PAGES.search(text, m.end(), self.end)
                    if pages:
                        host["pages"] = text_value(
                            text,
                            pages.start("pages"),
                            pages.end("pages"),
                            "p03.host-pages",
                        )
                    self.out["hosts"] = [{k: v for k, v in host.items() if v}]
                    return m.start()
        anchor = getattr(self, "after_title", pos)
        titled = HOST_TITLE.match(text, anchor, zone_end) if anchor < zone_end else None
        if (
            titled
            and "in " not in text[anchor : titled.start("title")]
            and ((self.out.get("title") or {}).get("rule") != "p03.title-quoted")
        ):
            # "Title, Host" is the main volume's form after a quoted title only.
            titled = None
        if titled:
            title = text_value(
                text,
                titled.start("title"),
                self._credit_cut(titled.start("title"), titled.end("title")),
                "p03.host-title",
            )
            if title and re.search(r"[^\W\d_]{3}", title["value"]):
                host = {"title": title}
                bracket = re.compile(r"\s+\[").match(text, titled.end())
                ref = REFERENCE.match(text, bracket.end()) if bracket else None
                refs = self.addresses(ref.start(), ref.end()) if ref else []
                if refs:
                    host["address"] = refs[0]
                hosts.append(host)
                starts.append(titled.start())
        for m in HOST_ADDRESS.finditer(text, pos, zone_end):
            group = "address" if m.group("address") else "inaddress"
            if titled and titled.start() <= m.start() <= titled.end() + 3:
                continue
            refs = self.addresses(m.start(group), m.end(group))
            if refs:
                hosts.append({"address": refs[0]})
                starts.append(m.start())
        if not hosts:
            return None
        if titled and hosts[0].get("title"):
            self._host_year(hosts[0])
        for host, start in zip(hosts, starts):
            nxt = min([s for s in starts if s > start] + [zone_end])
            pages = PAGES.search(text, start, nxt)
            if pages:
                host["pages"] = text_value(
                    text, pages.start("pages"), pages.end("pages"), "p03.host-pages"
                )
        self.out["hosts"] = hosts
        return min(starts)

    def _title_ref_after_in(self) -> re.Match | None:
        """A host cited after "in" in the title-reference form of Addendum
        II, with a section code or a contents number: "“Essay” in LA2 Title
        1942 [12], pp. 116-117", "in GA2 Title: Subtitle 2000 [1], pp. 7-24"."""
        if self.entry["volume"] != "A2" or not self.out.get("title"):
            return None
        lead = IN_LEAD.match(self.text, getattr(self, "after_title", self.zone[0]))
        if not lead or lead.end() > self.zone[1]:
            return None
        ref = TITLE_REF.match(self.text, lead.end(), self.end)
        # A bracket in a number's place may name a periodical's place
        # ("in Journal [Place], pp. 31-40"), so the number holds a digit.
        number = ref and (re.match(r"\d", ref.group("no") or "") or ref.group("no2"))
        if not ref or not (ref.group("code") or number):
            return None
        if ref.group("year") and self.text.startswith("/", ref.end("year")):
            # "in SZ Briefe 1914/19, No. 4": a span of years names the
            # volume, no year of printing.
            return None
        title = ref.group("title")
        if re.search(
            rf"{ABBREVIATED}|\b(?:Edited|Translated)\b|\.\s[A-ZÀ-ÞĀ-ž(][\w'’/() -]{{1,40}}: ",
            title,
        ):
            # A full citation with credits or an imprint ("Title. Place:
            # Publisher, 1919, No. 13") is no title reference; a colon inside
            # the title's first sentence opens its subtitle.
            return None
        return ref

    def _host_year(self, host: dict) -> None:
        """A host title-reference gives its year after the title ("Stefan Zweig.
        Spiegelungen ... [1959], No. 5", "Vida e morte de Stefan Zweig 1942 [35]")."""
        text = self.text
        title = host["title"]
        a, b = title["span"]
        inside = re.search(r"\s(?P<year>1[5-9]\d\d|20[0-2]\d)$", title["value"])
        if inside and YEAR_OF_TITLE.search(title["value"][: inside.start()]):
            # "Almanach auf das Jahr 1912", "Das Buch des Jahres 1928": the year
            # names the title's year, printed the year before.
            inside = None
        after = re.compile(
            r"(?:,?\s(?:Vol\.|Bd\.|No\.)\s?[\dIVXL]+)?\s*[\[(](?P<year>1[5-9]\d\d|20[0-2]\d)[\])]"
        ).match(text, b)
        if inside:
            year = (a + inside.start("year"), a + inside.end("year"))
            trimmed = text_value(text, a, a + inside.start(), title["rule"])
            if trimmed:
                host["title"] = trimmed
        elif after:
            year = after.span("year")
        else:
            return
        imprint = {"year": value(int(text[year[0] : year[1]]), *year, "p03.host-year")}
        if after and not inside:
            imprint["year_bracketed"] = value(
                True, after.start("year") - 1, after.end("year") + 1, "p03.host-year"
            )
        host.setdefault("imprints", []).insert(0, imprint)

    def _host_citation(self, start: int, end: int) -> None:
        """Credits, imprint, extent and series after the host's start are the host's."""
        host = self.out["hosts"][0]
        cited = self._citation(start, end)
        if cited.get("imprints") and not any(i.get("year") for i in cited["imprints"]):
            # A year read after the host title stays when the imprint has none.
            cited["imprints"] = host.get("imprints", []) + cited["imprints"]
        for key in ("imprints", "extent", "series"):
            if cited.get(key):
                host[key] = cited[key]
        title = host.get("title")
        persons = list(
            read_credits(self.text, start, end, [tuple(title["span"])] if title else [])
        )
        if persons:
            host["persons"] = persons

    def _own_citation(self, start: int, end: int) -> None:
        cited = self._citation(start, end)
        for key in ("imprints", "extent", "series"):
            if cited.get(key):
                self.out.setdefault(key, [] if key != "extent" else None)
                if key == "series":
                    self.out["series"].extend(cited[key])
                else:
                    self.out[key] = cited[key]
        if self.ctx.get("edition_line"):
            # "Publisher: 299/(2)p. Place, 1984" read as "Place: Publisher, Year"
            # puts the publisher into the place; the edition line wins.
            edition = EDITION_LINE.match(self.text, self.zone[0], end)
            if edition and any(
                edition.start("publisher")
                <= (i.get("place") or {}).get("span", [-1])[0]
                < edition.end("publisher")
                for i in self.out.get("imprints", [])
            ):
                self.out.pop("imprints")
            if not self.out.get("imprints"):
                self._edition_line(self.zone[0], end)
        if (
            self.out.get("imprints")
            or self.out.get("periodicals")
            or self.out.get("hosts")
        ):
            return
        # Place and year without a publisher after the extent: "8p. Place, 1933."
        located = EXTENT_PLACE_YEAR.search(
            self.text, start, end
        ) or PLACE_YEAR_PAGES.search(self.text, start, end)
        if located:
            imprint = {
                "place": text_value(
                    self.text,
                    located.start("place"),
                    located.end("place"),
                    "p03.extent-place-year",
                ),
                "year": value(
                    int(located.group("year")),
                    *located.span("year"),
                    "p03.extent-place-year",
                ),
            }
            if located.group("open") and located.group("close"):
                imprint["year_bracketed"] = value(
                    True,
                    located.start("open"),
                    located.end("close"),
                    "p03.extent-place-year",
                )
            self.out["imprints"] = [{k: v for k, v in imprint.items() if v}]
            return
        imprint = {}
        publisher = self.ctx.get("edition_publisher")
        if publisher:
            imprint["publisher"] = text_value(
                self.text, *publisher, "p03.edition-publisher"
            )
        # A printing that gives only its year: "1.-3. Tsd. 1984.", "[1]. 1982."
        # It is read in a printing's context only, so that a letter's date
        # ("9 Oct. 1913") is no year of publication.
        printing = (
            self.ctx.get("label_kind") == "edition"
            or publisher
            or any(p.search(self.text, start, end) for _, p in EDITION_NOTES[:3])
            or read_extent(self.text, start, end)
        )
        year = STANDALONE_YEAR.search(self.text, start, end) if printing else None
        before = self.text[max(0, year.start() - 8) : year.start()] if year else ""
        if year and re.search(
            rf"(?:{MONTH}|\bNos?\.|\bNr\.|\bHeft|\bVol\.|\bpp?\.)\s$", before
        ):
            year = None
        if year:
            imprint["year"] = value(
                int(year.group("year")),
                year.start("year"),
                year.end("year"),
                "p03.year-standalone",
            )
            if year.group("open") and year.group("close"):
                imprint["year_bracketed"] = value(
                    True, year.start("open"), year.end("close"), "p03.year-standalone"
                )
        imprint = {k: v for k, v in imprint.items() if v}
        if imprint:
            self.out["imprints"] = [imprint]

    def _citation(self, start: int, end: int) -> dict:
        text, out = self.text, {}
        imprints = read_imprints(text, start, end)
        if imprints:
            out["imprints"] = imprints
        series = list(read_series(text, imprints, end))
        if series:
            out["series"] = [s["value"] for s in series]
            self.used.extend(s["span"] for s in series)
            self.ctx.setdefault("series_spans", []).extend(s["span"] for s in series)
        extent = read_extent(text, start, end)
        if extent:
            out["extent"] = extent
        return out

    def _edition_line(self, pos: int, end: int) -> None:
        text = self.text
        edition = EDITION_LINE.match(text, pos, end)
        if not edition:
            return
        imprint = {
            "publisher": text_value(
                text,
                edition.start("publisher"),
                edition.end("publisher"),
                "p03.edition-line",
            )
        }
        located = PLACE_YEAR.search(text, edition.end(), end)
        if located:
            imprint["place"] = text_value(
                text, located.start("place"), located.end("place"), "p03.edition-line"
            )
            imprint["year"] = value(
                int(located.group("year")),
                located.start("year"),
                located.end("year"),
                "p03.edition-line",
            )
            if located.group("open") and located.group("close"):
                imprint["year_bracketed"] = value(
                    True,
                    located.start("open"),
                    located.end("close"),
                    "p03.edition-line",
                )
        imprint = {k: v for k, v in imprint.items() if v}
        if imprint:
            self.out["imprints"] = [imprint]

    def _persons(self, pos: int, end: int) -> None:
        title = self.out.get("title")
        skip = list(self.ctx.get("series_spans", [])) + (
            [tuple(title["span"])] if title else []
        )
        for person in read_credits(self.text, pos, end, skip):
            self.out.setdefault("persons", []).append(person)
        # "(Forename Surname)" closes a review item of the main volume only.
        if (
            self.entry["part"] == "M"
            and self.entry["volume"] == "I"
            and not any(
                r["value"] == "author"
                for p in self.out.get("persons", [])
                for r in p["roles"]
            )
        ):
            trailing = None
            for trailing in TRAILING_NAME.finditer(self.text, self.start, self.end):
                pass
            if trailing:
                name = text_value(
                    self.text,
                    trailing.start("name"),
                    trailing.end("name"),
                    "p03.review-author",
                )
                if name:
                    self.out.setdefault("persons", []).append(
                        {
                            "name": name,
                            "roles": [
                                value("author", *name["span"], "p03.review-author")
                            ],
                        }
                    )
        for series in self.out.get("series", []):
            if series.get("title"):
                a, b = series["title"]["span"]
                credits = list(read_credits(self.text, a, b, []))
                if credits:
                    series["persons"] = credits

    def _edition_notes(self, pos: int, zone_end: int) -> None:
        text, notes, taken = self.text, [], []
        for kind, pattern in EDITION_NOTES:
            stop = self.end if kind == "reprint" else zone_end
            for m in pattern.finditer(text, pos, stop):
                if any(a < m.end() and m.start() < b for a, b in taken):
                    continue
                taken.append((m.start(), m.end()))
                note = {
                    "kind": kind,
                    "text": value(m.group(), m.start(), m.end(), f"p03.edition-{kind}"),
                }
                if kind == "reprint":
                    note["years"] = [
                        value(
                            int(y.group(1)), y.start(1), y.end(1), "p03.edition-reprint"
                        )
                        for y in YEAR.finditer(text, m.start(), m.end())
                    ]
                notes.append(note)
        notes.sort(key=lambda n: n["text"]["span"][0])
        if notes:
            self.out["edition_notes"] = notes
            self.used.extend(tuple(n["text"]["span"]) for n in notes)

    def _event(self) -> None:
        text, part = self.text, self.entry["part"]
        word = EVENT_WORD.search(text, self.zone[0], self.end)
        # Outside the film, stage and symposium parts an event is a work's
        # premiere, film or reading; in letters, essays and secondary
        # literature such words name a source (an exhibition catalogue).
        if part in WORD_EVENT_EXCLUDED:
            word = None
        # The dates of a cited periodical or reviewed work are theirs, and a
        # "See also" points elsewhere; the event stands before both.
        see = re.compile(r"\bSee\b").search(text, self.zone[0], self.end)
        review = REVIEW_LABEL.search(text, self.zone[0], self.end)
        stop = (
            min(m.start() for m in (see, review) if m) if (see or review) else self.end
        )
        if word and word.start() >= stop:
            word = None
        if part not in EVENT_PARTS and not (word and not self.out.get("imprints")):
            return
        event = {}
        if word:
            event["medium"] = value(
                word.group(), word.start(), word.end(), "p03.event-medium"
            )
        cited = [
            v["span"]
            for key in ("periodicals", "reviewed", "hosts")
            for c in self.out.get(key, [])
            for _, v in iter_values(c)
        ]
        cited_from = min((s[0] for s in cited), default=stop)

        def free(a: int, b: int) -> bool:
            return not any(s[0] <= a < s[1] or s[0] < b <= s[1] for s in cited)

        date = next(
            (
                d
                for d in EVENT_DATE.finditer(text, self.zone[0], stop)
                if free(d.start(), d.end())
            ),
            None,
        )
        if date:
            event["date"] = value(
                date.group(), date.start(), date.end(), "p03.event-date"
            )
            year = YEAR.search(date.group())
            if year:
                a = date.start() + year.start(1)
                event["year"] = value(int(year.group(1)), a, a + 4, "p03.event-date")
        elif part in EVENT_PARTS:
            year = self._event_year(self.zone[0], min(self.zone[1], cited_from))
            if year:
                event["year"] = value(
                    int(year.group(1)), year.start(1), year.end(1), "p03.event-year"
                )
        place = EVENT_PLACE.search(text, self.zone[0], stop)
        if place:
            group = "place" if place.group("place") else "pplace"
            event["place"] = text_value(
                text, place.start(group), place.end(group), "p03.event-place"
            )
        event = {k: v for k, v in event.items() if v}
        if event:
            self.out["event"] = event

    def _event_year(self, a: int, b: int) -> re.Match | None:
        """The first year that dates the event: no page number ("pp.
        1522-1523"), no year of a life ("1881 - 1942"), no film length ("1970
        meters")."""
        text = self.text
        for m in YEAR.finditer(text, a, b):
            before = text[max(a, m.start() - 6) : m.start()]
            after = text[m.end() : m.end() + 9]
            if re.search(r"(?:pp?\.|S\.)\s?$|[-–]\s?$", before):
                continue
            span = re.match(r"\s?[-–]\s?((?:1[5-9]|20)\d\d)", after)
            if span and int(span.group(1)) - int(m.group(1)) > 20:
                continue
            if re.match(r"\s?(?:m|meters|metres|Meter|mm|ft|feet)\b", after):
                continue
            return m
        return None

    def _informants(self, s: int, e: int) -> None:
        found = []
        for m in INFORMANT.finditer(self.text, s, e):
            if re.fullmatch(r"[IVXLC]+", m.group("sigla")):
                continue
            offset = m.start("sigla")
            for siglum in m.group("sigla").split("/"):
                found.append(
                    value(siglum, offset, offset + len(siglum), "p03.informant")
                )
                offset += len(siglum) + 1
            self.used.append((m.start(), m.end()))
        # The head object of an entry whose Contents list closes the entry
        # carries the informant set after that list ("... Contents: ... [AB].").
        text = self.text
        if (
            self.start == 0
            and self.end < len(text)
            and self.ctx.get("next_object_start") == len(text)
        ):
            tail = re.compile(
                r"\[(?P<sigla>[A-Z]{2,5}(?:/[A-Z]{2,5})*)\]\.?\s*$"
            ).search(text, self.end)
            if tail and CONTENTS_LABEL.search(text, self.end, tail.start()):
                offset = tail.start("sigla")
                for siglum in tail.group("sigla").split("/"):
                    found.append(
                        value(
                            siglum,
                            offset,
                            offset + len(siglum),
                            "p03.informant",
                            source=self.entry["id"],
                        )
                    )
                    offset += len(siglum) + 1
        if found:
            self.out["informants"] = found

    def _holdings(self, pos: int, e: int) -> None:
        text, holdings = self.text, []
        m = HOLDING_REPOSITORY.match(text, pos, e)
        if m and self.entry["part"] == "K":
            holdings.append(
                {
                    "repository": value(
                        m.group("repo"),
                        m.start("repo"),
                        m.end("repo"),
                        "p03.holding-repository",
                    ),
                    "text": value(
                        m.group("text"),
                        m.start("text"),
                        m.end("text"),
                        "p03.holding-repository",
                    ),
                }
            )
        else:
            for letters in HOLDING_LETTERS.finditer(text, pos, e):
                v = text_value(
                    text, letters.start(), letters.end(), "p03.holding-letters"
                )
                if v:
                    holdings.append({"text": v})
        located = LOCATED.search(text, pos, e)
        manuscript = manuscript_item(text, self.start)
        if located and (manuscript or MANUSCRIPT.search(text, pos, e)):
            repo = text_value(
                text, located.start("repo"), located.end("repo"), "p03.holding-located"
            )
            sentence = text_value(text, pos, located.end(), "p03.holding-located")
            if repo and sentence:
                holdings.append({"repository": repo, "text": sentence})
        if manuscript and not holdings:
            # The item's first sentence or the text before its first note
            # names where the version is kept.
            stop = re.compile(r"\s\[|\.\s(?=[A-ZÀ-ÞĀ-ž\"“„])").search(text, pos, e)
            kept = text_value(
                text, pos, stop.start() if stop else e, "p03.holding-manuscript"
            )
            if kept:
                holdings.append({"text": kept})
        if holdings:
            self.out["holdings"] = holdings

    def _reviewed(self) -> None:
        text = self.text
        m = REVIEW_LABEL.search(text, self.zone[0], self.end)
        if not m:
            return
        self.ctx["review_label"] = True
        stop = re.compile(r"\bSee\b|\]\s*$|\bREP:|\bRep:").search(
            text, m.end(), self.end
        )
        end = stop.start() if stop else self.end
        cut = m.end()
        pieces = [p for p in re.finditer(r";\s", text[cut:end])]
        bounds = [cut] + [cut + p.end() for p in pieces] + [end]
        for a, b in zip(bounds, bounds[1:]):
            citation = self._reviewed_citation(a, b)
            if citation:
                self.out.setdefault("reviewed", []).append(citation)

    def _reviewed_citation(self, a: int, b: int) -> dict | None:
        text, out = self.text, {}
        pos = a
        while pos < b and text[pos] == " ":
            pos += 1
        # "Review of: EA2 Title. ..." cites the reviewed work by its section
        # code, which is its address when numbered and never an author.
        address, pos, _ = self._split_code(pos, b)
        if address:
            out["address"] = address
        name = re.match(
            r"(?P<name>(?:[A-ZÀ-ÞĀ-ž][a-z]?\.\s?){1,3}[A-ZÀ-ÞĀ-ž][\w'’-]+(?: [A-ZÀ-ÞĀ-ž][\w'’-]+)?"
            r"|[A-ZÀ-ÞĀ-ž][\w'’-]+ [A-ZÀ-ÞĀ-ž][\w'’-]+)\.\s(?=[A-ZÀ-ÞĀ-ž])",
            text[pos:b],
        )
        persons = []
        if name:
            v = text_value(
                text,
                pos + name.start("name"),
                pos + name.end("name"),
                "p03.reviewed-author",
            )
            if v:
                persons.append(
                    {
                        "name": v,
                        "roles": [value("author", *v["span"], "p03.reviewed-author")],
                    }
                )
            pos += name.end()
        title_end = self._title_end(pos, b)
        title = text_value(text, pos, title_end, "p03.reviewed-title")
        if title and re.search(r"[^\W\d_]{2}", title["value"]):
            out["title"] = title
        persons.extend(read_credits(text, title_end, b, []))
        if persons:
            out["persons"] = persons
        imprints = read_imprints(text, title_end, b)
        if imprints:
            out["imprints"] = imprints
        extent = read_extent(text, title_end, b)
        if extent:
            out["extent"] = extent
        return out if out.get("title") else None

    def _contents(self) -> list[dict]:
        """A Contents list after the head object belongs to the object it follows.

        Returns the cross-references that stand outside the object's span: in
        a bracket of the list ("(See G 449)") and after it ("... / L 68. See
        A 48"), so that the review can decide them as the object's values.
        """
        text = self.text
        m = None
        if self.start == 0:
            m = CONTENTS_LABEL.match(text, self.end) or CONTENTS_LABEL.match(
                text, self.end + 1
            )
        if not m:
            m = CONTENTS_LABEL.search(text, self.start, self.end)
        if not m:
            return []
        inside = m.start() < self.end
        stop = self.end if inside else self.ctx.get("next_object_start", len(text))
        # A "See" inside a bracket of the list refers from one item; only one
        # at the list's own level ends it.
        end = next(
            (
                e.start()
                for e in CONTENTS_END.finditer(text, m.end(), stop)
                if self._depth(m.end(), e.start()) == 0
            ),
            stop,
        )
        source = None if inside else self.entry["id"]
        items = []
        marks = list(CONTENT_ITEM.finditer(text, m.end(), end))
        if marks:
            for i, mark in enumerate(marks):
                item_end = marks[i + 1].start() if i + 1 < len(marks) else end
                # The last item of a volume ends where the next volume or a new
                # edition is stated, so their credits stay theirs.
                volume = VOLUME_BREAK.search(text, mark.end(), item_end)
                if volume:
                    item_end = volume.start() + 1
                items.append(self._content_item(mark.end(), item_end, source))
        else:
            for ref in self.addresses(m.end(), end, source=source):
                if not self._see_bracket(m.end(), ref["address"]["span"][0]):
                    items.append({"address": ref})
            items += self._titled_items(m.end(), end, source)
            items.sort(key=_item_start)
        items = [i for i in items if i]
        if items:
            self.out["contents"] = items
        if inside:
            return []
        own = self.entry["id"]
        # In an address list every address outside a See bracket is an item.
        refs = [] if marks else self._references(m.end(), end, source=own)
        if text.startswith("See", end):
            # The See sentence after the list, up to its end or a new list.
            cut = [stop]
            for pattern in (CONTENT_SENTENCE_END, CONTENTS_LABEL, VOLUME_BREAK):
                found = pattern.search(text, end, stop)
                if found:
                    cut.append(found.start() + 1)
            refs += self._references(end, min(cut), source=own)
        return refs

    def _depth(self, start: int, pos: int) -> int:
        """Bracket depth at pos, counted from start."""
        depth = 0
        for ch in self.text[start:pos]:
            if ch in "[(":
                depth += 1
            elif ch in "])" and depth:
                depth -= 1
        return depth

    def _see_bracket(self, start: int, pos: int) -> bool:
        """pos stands in a bracket of the list that opens with "See"."""
        opened: list[int] = []
        for i in range(start, pos):
            ch = self.text[i]
            if ch in "[(":
                opened.append(i)
            elif ch in "])" and opened:
                opened.pop()
        return bool(opened) and self.text[opened[-1] + 1 :].lstrip().startswith("See")

    def _titled_items(self, start: int, end: int, source) -> list[dict]:
        """Items named by title in an address list ("D 141 / Commentaries, pp.
        353-364", "Vorwort / H 45"): a slash at the list's level separates
        them, and a titled item holds no address. The last one ends with its
        sentence, so that what follows the list is no item."""
        text = self.text
        cuts = [
            s.start()
            for s in re.finditer(r"\s/\s", text[start:end])
            if self._depth(start, start + s.start()) == 0
        ]
        if not cuts:
            return []
        bounds = [start, *(start + c for c in cuts), end]
        items = []
        for n in range(len(bounds) - 1):
            a = bounds[n] + (0 if n == 0 else 3)
            b = bounds[n + 1]
            if REFERENCE.search(text, a, b):
                continue
            sentence = CONTENT_SENTENCE_END.search(text, a, b)
            if sentence:
                b = sentence.start() + 1
            a, b = _strip_span(text, a, b)
            segment = text[a:b]
            if (
                not re.search(r"[^\W\d_]{2}", segment)
                or segment.startswith("See")
                or VOLUME_LABEL.match(segment)
            ):
                continue
            item = self._content_item(a, b, source)
            if item:
                items.append(item)
        return items

    def _content_item(self, start: int, end: int, source) -> dict | None:
        text = self.text
        kw = {"source": source} if source else {}
        item: dict = {}
        cut = [end]
        for pattern in (r",\s?pp?\.", r"\s\[", r"\.\s", r"\.$"):
            m = re.compile(pattern).search(text, start, end)
            if m:
                cut.append(m.start())
        title_end = min(cut)
        segment = text[start:title_end].strip()
        if segment and not REFERENCE.fullmatch(segment):
            title = text_value(text, start, title_end, "p03.contents-title", **kw)
            if title and re.search(r"[^\W\d_]{2}", title["value"]):
                item["title"] = title
        refs = self.addresses(start, end, source=source)
        if refs:
            item["address"] = refs[0]
        bracket = re.compile(r"\s\[([^\[\]]{2,200})\]").match(text, title_end, end)
        persons = list(read_credits(text, start, end, [], source=source))
        # Only a translation's contents give original titles in brackets;
        # elsewhere, and for credits, initials or a credited person, the
        # bracket names who wrote or annotated the item.
        if bracket and not REFERENCE.match(bracket.group(1)) and self._translation():
            head = re.split(r"\.\s|\s/\s", bracket.group(1))[0]
            if (
                head
                and not re.search(r"\d|\b(?:Trl?|Translated)\b", head)
                and not CREDIT_GLOSS.search(head)
                and re.search(r"[^\W\d_]{3}", head)
                and not self._names_a_person(head, persons)
            ):
                v = text_value(
                    text,
                    bracket.start(1),
                    bracket.start(1) + len(head),
                    "p03.contents-original-title",
                    **kw,
                )
                if v:
                    item["original_title"] = v
        if persons:
            item["persons"] = persons
        pages = PAGES.search(text, start, end)
        if pages:
            v = text_value(
                text,
                pages.start("pages"),
                pages.end("pages"),
                "p03.contents-pages",
                **kw,
            )
            if v:
                item["pages"] = v
        if not (item.get("title") or item.get("address")):
            return None
        return item

    # addresses

    def addresses(self, start: int, end: int, source=None) -> list[dict]:
        """Printed address groups in text[start:end], each resolved to its targets."""
        text, out = self.text, []
        for m in REFERENCE.finditer(text, start, end):
            letter, suffix, group = m.groups()
            suffix = suffix or ""
            if suffix not in SUFFIX_TO_VOLUME:
                continue
            # "A 1927 port", "Vol. I 1945": a four-digit year after a letter is
            # no address; a four-digit number is one only in a section whose
            # table of contents runs that high (G 1126 and L 1895 of the main
            # volume, LA1 1063), or in L where a volume has no such table.
            head = re.match(r"\d+", group).group()
            toc = TOC_MAX.get(SUFFIX_TO_VOLUME[suffix])
            highest = toc.get(letter, 0) if toc else (1899 if letter == "L" else 0)
            if len(head) == 4 and int(head) > highest:
                continue
            targets, _ = parse_items(group)
            resolved = []
            for n, s in targets:
                normalized = f"{letter}{suffix} {n}{s}"
                if normalized == self.entry["address"]:
                    continue
                resolved.append(
                    {
                        "normalized": normalized,
                        "record": self.ctx["index"].get(normalized),
                    }
                )
            if not resolved:
                continue
            a, b = m.span()
            kw = {"by": "compiler", "source": source}
            address = {
                "address": value(text[a:b], a, b, "p06.address-notation", **kw),
                "targets": resolved,
            }
            # An own locator stays inside the object; one read for another
            # record (source) stays inside the range asked for.
            limit = self.end if source is None else end
            locator = LOCATOR.match(text, b, min(limit, b + 40))
            if locator and locator.group().strip(" ,"):
                lv = text_value(
                    text,
                    locator.start(),
                    locator.end(),
                    "p03.address-locator",
                    source=source,
                )
                if lv:
                    address["locator"] = lv
            out.append(address)
            self.used.append((a, b))
        return out

    def _references(self, s: int, e: int, source=None) -> list[dict]:
        """The cross-references in text[s:e] that no other field holds. With a
        source (the own entry), they stand outside the object's span: the
        references after its Contents list (_contents)."""
        taken = set()
        for ref in self.out.get("work_refs", []):
            taken.add(tuple(ref["address"]["span"]))
        for host in self.out.get("hosts", []):
            if host.get("address"):
                taken.add(tuple(host["address"]["address"]["span"]))
        for item in self.out.get("contents", []):
            if item.get("address"):
                taken.add(tuple(item["address"]["address"]["span"]))
        refs, previous = [], None
        for ref in self.addresses(s, e, source=source):
            a, b = ref["address"]["span"]
            if (a, b) in taken:
                previous = None
                continue
            marker = MARKER.search(self.text, max(s, a - 30), a)
            if marker:
                kind = marker_kind(marker.group("marker"))
                ref["kind"] = value(
                    kind,
                    marker.start("marker"),
                    marker.end("marker"),
                    "p03.reference-marker",
                    source=source,
                )
            elif (
                previous
                and previous[1]["rule"] == "p03.reference-marker"
                and re.fullmatch(r"\s*[/,;&]\s*", self.text[previous[0] : a])
            ):
                # A list continues the marker before it ("See A 48, 49 / G 755").
                ref["kind"] = dict(previous[1])
            else:
                ref["kind"] = value(
                    "related",
                    a,
                    b,
                    "p03.reference-inline",
                    by="compiler",
                    source=source,
                )
            if ref["kind"]["value"] == "contents":
                previous = (b, ref["kind"])
                continue
            refs.append(ref)
            previous = (b, ref["kind"])
        return refs

    def _notes(self, s: int, e: int) -> None:
        notes = []
        for m in BRACKET.finditer(self.text, s, e):
            if any(a <= m.start() and m.end() <= b for a, b in self.used):
                continue
            inner = m.group("inner")
            if REFERENCE.fullmatch(inner.strip()) or INFORMANT.fullmatch(m.group()):
                continue
            v = text_value(
                self.text, m.start("inner"), m.end("inner"), "p03.note-bracket"
            )
            if v:
                notes.append(v)
        if notes:
            self.out["notes"] = notes


def read_extent(text: str, start: int, end: int) -> dict | None:
    m = EXTENT.search(text, start, end)
    volumes = VOLUMES.search(text, start, end)
    if not m and not volumes:
        return None
    out: dict = {}
    if m:
        out["raw"] = value(m.group(), m.start(), m.end(), "p03.extent")
        parts = []
        for piece in EXTENT_PIECE.finditer(text, m.start("raw"), m.end("raw")):
            token = piece.group()
            if not token:
                continue
            core = token.strip("[]()")
            kind = (
                "uncounted"
                if token[0] in "[("
                else "roman"
                if re.fullmatch(r"[ivxlc]+", core)
                else "counted"
            )
            parts.append(
                {
                    "kind": kind,
                    "text": value(token, piece.start(), piece.end(), "p03.extent"),
                }
            )
        if parts:
            out["parts"] = parts
    if volumes:
        out["volumes"] = value(
            volumes.group(), volumes.start(), volumes.end(), "p03.extent-volumes"
        )
        out.setdefault("raw", out["volumes"])
    anchor = m.end() if m else volumes.end()
    illus = ILLUSTRATIONS.search(text, anchor, min(end, anchor + 40))
    if illus:
        out["illustrations"] = value(
            illus.group(), illus.start(), illus.end(), "p03.illustrations"
        )
    return out


def read_imprints(text: str, start: int, end: int) -> list[dict]:
    """Imprint statements "Place: Publisher, Year" in text[start:end]."""
    imprints: list[dict] = []
    pos = start
    while True:
        colon = text.find(": ", pos, end)
        if colon < 0:
            break
        pos = colon + 2
        place = _place_before(text, start, colon)
        if place is None:
            continue
        direct = COLON_YEAR.match(text, colon)
        if direct:
            # "Place/Place: 1959" names no publisher.
            imprint = {
                "place": text_value(text, *place, "p03.imprint"),
                "year": value(
                    int(direct.group("year")), *direct.span("year"), "p03.imprint"
                ),
            }
            if direct.group("open") and direct.group("close"):
                imprint["year_bracketed"] = value(
                    True,
                    direct.start("open"),
                    direct.end("close"),
                    "p03.imprint-bracketed",
                )
            imprints.append({k: v for k, v in imprint.items() if v})
            pos = direct.end()
            continue
        window = min(end, colon + 120)
        year = IMPRINT_YEAR.search(text, colon, window)
        no_date = NO_DATE.search(text, colon, window)
        if no_date and (not year or no_date.start() < year.start()):
            year, stop = None, no_date.start()
        elif year:
            stop = year.start()
        else:
            continue
        publisher_span = (colon + 2, stop)
        publisher = text[publisher_span[0] : publisher_span[1]]
        group = [(place, publisher_span)]
        # "Place: Publisher / Place: Publisher, 1929" names two imprints. The
        # second place holds no digit and no sentence end, so "Title: A / B.
        # 218p. Place: Publisher" is a title, not two imprints.
        for inner in re.finditer(
            r" / (?=[A-ZÀ-ÞĀ-ž](?:[^\W\d_]|[ ,'’()-]|(?:(?<=\b[A-Za-z])|(?<=\b[A-Z][a-z]))\.)"
            r"{1,40}: )",
            publisher,
        ):
            a = publisher_span[0] + inner.start()
            b = publisher_span[0] + inner.end()
            nxt = text.find(": ", b, publisher_span[1])
            last_place, last_pub = group[-1]
            group[-1] = (last_place, (last_pub[0], a))
            group.append(((b, nxt), (nxt + 2, publisher_span[1])))

        def credit_like(segment: str) -> bool:
            # A bracketed publisher may say "by" ("[Private publication
            # by the artist]"); elsewhere "by" marks a credit.
            bracketed = segment.strip().startswith("[") and segment.strip().endswith(
                "]"
            )
            return bool(
                re.search(rf"{ABBREVIATED}|\d+p\.|\bp\.\s\d", segment)
                or (not bracketed and re.search(r"\bby\b", segment))
            )

        if not publisher.strip() or any(
            ": " in text[p[0] : p[1]] or credit_like(text[p[0] : p[1]])
            for _, p in group
        ):
            continue
        for k, (pl, pub) in enumerate(group):
            imprint = {}
            pv = text_value(text, pl[0], pl[1], "p03.imprint")
            if pv:
                imprint["place"] = pv
            bv = text_value(text, pub[0], pub[1], "p03.imprint")
            if bv:
                imprint["publisher"] = bv
            if k == len(group) - 1 and year:
                imprint["year"] = value(
                    int(year.group("year")),
                    year.start("year"),
                    year.end("year"),
                    "p03.imprint",
                )
                if year.group("end"):
                    imprint["year_end"] = value(
                        int(year.group("end")),
                        year.start("end"),
                        year.end("end"),
                        "p03.imprint",
                    )
                if year.group("open") and year.group("close"):
                    imprint["year_bracketed"] = value(
                        True,
                        year.start("open"),
                        year.end("close"),
                        "p03.imprint-bracketed",
                    )
                if year.group("circa"):
                    imprint["circa"] = value(
                        True,
                        year.start("circa"),
                        year.end("circa") - 1,
                        "p03.imprint-circa",
                    )
            if imprint.get("publisher") or imprint.get("year"):
                imprints.append(imprint)
        pos = year.end() if year else stop
    return imprints


def _place_before(text: str, floor: int, colon: int) -> tuple[int, int] | None:
    """The place before an imprint colon, back to the previous sentence boundary."""
    lo = max(floor, colon - 60)
    a = colon
    while a > lo:
        ch = text[a - 1]
        if (
            ch in "[(;"
            or text[max(lo, a - 3) : a] == " / "
            # A missing space after a sentence ("Surname.Place: ...").
            or (
                ch == "."
                and text[a].isupper()
                and a - 2 >= lo
                and text[a - 2].islower()
            )
            or (
                ch == " "
                and a - 2 >= lo
                and text[a - 2] in ".;]"
                and not PLACE_ABBREVIATION.search(text[max(lo, a - 6) : a])
            )
        ):
            break
        a -= 1
    else:
        if a > floor:
            return None
    while a < colon and text[a] in " ([":
        a += 1
    b = colon
    while b > a and text[b - 1] in " )]":
        b -= 1
    place = text[a:b]
    # A substitute-font defect may stand for the first letter ("￿stanbul"),
    # an article may precede it ("al-Qâhirah").
    if (
        not place
        or not re.match(r"(?:al-|el-|'s-)?[A-ZÀ-ÞĀ-ž￿\x00]", place)
        or re.search(r"\d", place)
    ):
        return None
    # A repository siglum before a holding ("SIGL: X to Zweig, ...").
    if re.fullmatch(r"[A-Z]{2,6}", place):
        return None
    if (
        place.split()[0].lower().strip(".") in LABEL_WORDS
        or place.lower() in LABEL_PHRASES
    ):
        return None
    return a, b


def read_series(text: str, imprints: list[dict], zone_end: int):
    for imprint in imprints:
        year = imprint.get("year_end") or imprint.get("year")
        if not year:
            continue
        anchor = year["span"][1]
        if imprint.get("year_bracketed"):
            anchor = max(anchor, imprint["year_bracketed"]["span"][1])
        while anchor < len(text) and text[anchor] in ")]":
            anchor += 1
        m = SERIES.match(text, anchor, min(len(text), anchor + 120))
        if (
            not m
            or SERIES_STOP.search(m.group("title"))
            or re.search(r"\d{4,}", m.group("title"))
        ):
            continue
        if re.fullmatch(r"[A-Z]{2,5}", m.group("title")):
            continue
        title_end = m.end("title")
        credit = re.search(rf"\.\s(?={ABBREVIATED}|[A-Z][a-z]+ by\b)", m.group("title"))
        if credit:
            title_end = m.start("title") + credit.start()
        series = {"title": text_value(text, m.start("title"), title_end, "p03.series")}
        if m.group("number"):
            series["number"] = text_value(
                text, m.start("number"), m.end("number"), "p03.series"
            )
        series = {k: v for k, v in series.items() if v}
        if series:
            yield {"value": series, "span": (m.start("open"), m.end())}


def read_credits(text: str, start: int, end: int, skip, source=None):
    """Persons of credit phrases in text[start:end]."""
    kw = {"source": source} if source else {}
    for m in CREDIT.finditer(text, start, end):
        if any(a <= m.start() < b for a, b in skip):
            continue
        roles = []
        for word in re.finditer(r"[A-Za-z]+\.?", m.group("phrase")):
            role = ROLE_WORDS.get(word.group().rstrip(".").lower())
            if role:
                a = m.start("phrase") + word.start()
                b = a + len(word.group())
                roles.append(value(role, a, b, "p03.credit", **kw))
        if not roles:
            continue
        if NOT_INDICATED.search(m.group("phrase")):
            yield {"roles": roles}
            continue
        names_start = m.end()
        stop = NAME_END.search(text, names_start, end)
        names_end = stop.start() if stop else end
        if (
            stop
            and text.startswith(": ", names_end)
            and re.fullmatch(
                r"[A-ZÀ-ÞĀ-ž][\w'’-]+(?:\s?/\s?[A-ZÀ-ÞĀ-ž][\w'’ -]+)+",
                text[names_start:names_end],
            )
        ):
            # "Illus. Place/Place: Publisher, 1968": a list of places before
            # the imprint's colon is no name.
            continue
        if NOT_INDICATED.match(text, names_start):
            yield {"roles": roles}
            continue
        offset = names_start
        pieces = []
        for piece in NAME_SPLIT.split(text[names_start:names_end]):
            at = text.find(piece, offset, names_end) if piece else -1
            if at < 0:
                continue
            offset = at + len(piece)
            # "Forename & Forename Surname" credits two persons who share a
            # surname; read verbatim it stays one credit, since "Forename
            # Surname" for the first stands nowhere in the text.
            if (
                pieces
                and re.fullmatch(r"[A-ZÀ-ÞĀ-ž][\w'’-]+", pieces[-1][1])
                and re.fullmatch(
                    r"\s(?:&|and|et)\s", text[pieces[-1][0] + len(pieces[-1][1]) : at]
                )
                and " " in piece.strip()
            ):
                start = pieces[-1][0]
                pieces[-1] = (start, text[start : at + len(piece)])
            else:
                pieces.append((at, piece))
        for at, piece in pieces:
            # "Tr. Forename Surname, Forename Surname resp." distributes the roles.
            piece = re.sub(r"\s+resp\.?$", "", piece)
            if NAME_DROP.match(piece.strip()) or not NAME_OK.match(piece.strip()):
                continue
            name = text_value(text, at, at + len(piece), "p03.credit", **kw)
            if name:
                yield {"name": name, "roles": roles}


def summary(obj: dict) -> dict:
    """The first value of each field the concordance and the field check compare.

    A projection for p07, p08 and p09 only; the structured object stays the
    record. The year is the object's own publication year, else that of its
    periodical, host or event.
    """
    inherited = obj.get("inherited") or {}
    host = (obj.get("hosts") or [{}])[0]
    # A volume that gives only its year reads place and publisher from its
    # collection header (p03 _period_imprint).
    placed = [
        i for i in obj.get("imprints") or [] if i.get("place") or i.get("publisher")
    ]
    imprints = (
        placed
        or (obj.get("imprints") and inherited.get("imprints"))
        or obj.get("imprints")
        or host.get("imprints")
        or inherited.get("imprints")
        or []
    )

    def first(values, key):
        return next((v[key]["value"] for v in values if v.get(key)), None)

    year = (
        first(obj.get("imprints") or [], "year")
        or first(obj.get("periodicals") or [], "year")
        or first(host.get("imprints") or [], "year")
        or (obj.get("event") or {}).get("year", {}).get("value")
    )
    # A reprint item cites only its host, whose title the wiki holds.
    title = obj.get("title") or inherited.get("title") or host.get("title") or {}
    translators = [
        p["name"]["value"]
        for p in obj.get("persons", [])
        if p.get("name") and any(r["value"] == "translator" for r in p["roles"])
    ]
    language = obj.get("language") or inherited.get("language") or {}
    inherited_imprint = " / ".join(
        ": ".join(i[k]["value"] for k in ("place", "publisher") if i.get(k))
        for i in inherited.get("imprints", [])
    )
    return {
        "title": title.get("value", ""),
        "year": year,
        "place": first(imprints, "place") or "",
        "publisher": first(imprints, "publisher") or "",
        "translator": translators[0] if translators else "",
        "translators": translators,
        "language": language.get("value", ""),
        "inherited_imprint": inherited_imprint,
    }


def derive_types(obj: dict, record: dict) -> list[str]:
    """Object types from the fields: form first, then translation and review.

    The same function serves p03, which writes the types, and p10, which
    derives them again from the stored fields and the record.
    """
    part, volume = record["part"], record["volume"]
    if record["kind"] == "reference":
        return ["reference"]
    if record.get("collection") and obj["id"].endswith("#1"):
        return ["collection"]
    types = []
    if obj.get("holdings") or (part == "R" and volume == "A1"):
        types.append("holding")
    if obj.get("event"):
        types.append("event")
    if obj.get("periodicals"):
        types.append("periodical_contribution")
    elif obj.get("hosts"):
        types.append("collection_contribution")
    elif (
        obj.get("imprints")
        or obj.get("extent")
        or (obj.get("inherited") or {}).get("imprints")
    ):
        if "holding" not in types and "event" not in types:
            types.append("book_edition")
    if (
        obj.get("reviewed")
        or part == "M"
        or (obj.get("relation") or {}).get("kind", {}).get("value") == "review"
        or record.get("reviews_heading")
    ):
        types.append("review")
    publication = {
        "periodical_contribution",
        "collection_contribution",
        "book_edition",
    } & set(types)
    translated = any(
        r["value"] == "translator" for p in obj.get("persons", []) for r in p["roles"]
    )
    language = (
        obj.get("language") or (obj.get("inherited") or {}).get("language") or {}
    ).get("value")
    # A language heading marks a translation only among Zweig's own works;
    # secondary literature, reviews and letters in a language are no
    # translations unless a translator is credited.
    foreign = language and language != "German" and part in WORK_PARTS
    if publication and (translated or foreign):
        types.append("translation")
    return types

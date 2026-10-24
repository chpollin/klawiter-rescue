"""The structured print object: every value bound to its text passage, with its producer.

This module is the source of schema/print-object.schema.json (written by
p03_records.py). p10_validate.py validates every object against these models
and adds the checks a schema cannot express. Validation is strict: no
coercion, no unknown keys.

A value has the form {value, span, by, rule, from?, state?}:
- span: [start, end) character offsets into the text of the record named in
  "from", or into the object's own entry text when "from" is absent. A value
  without "from" lies inside the object's own span; "from" set to the object's
  own entry marks a value from the entry outside that span (the head of a
  letter or review entry, the label before an item).
- by: "rule" (a regular reading), "compiler" (the compiler's address
  notation, read exactly), "inherited" (only inside the inherited block, always
  with "from") or "llm" (an offset proposed by a model and checked verbatim by
  rule; state "proposed"). A model proposes offsets into the object's own
  entry only, so it never produces an inherited value.
- rule: the reading rule, or the prompt identifier for "llm".

Text values equal the source passage character for character, including the
substitute-font defects and line-end hyphens of the PDFs; normalisation is a
later projection. Typed values (year, role, type, language, flag, kind) are
derived from their passage by the rule they name, and p10_validate.py derives
them again: a year is the digits of its span, a role the credit word of its
span, a language the folded name of its span, a type follows from the fields.
Empty fields are valid: a gap means the rules found nothing, never that the
volume says nothing.

The exported JSON Schema carries the producer conditions and the non-empty
conditions as if/then and anyOf; span order, identifier consistency, verbatim
equality and the derivations are checked by pydantic and p10 only.
"""

from typing import Annotated, Literal

from annotated_types import Len
from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, model_validator

SCHEMA_ID = (
    "https://github.com/chpollin/klawiter-rescue/"
    "pipeline/print_volumes/schema/print-object.schema.json"
)
LANGUAGES = (
    "Albanian Arabic Armenian Azerbaijani Basque Bengali Bosnian Bulgarian "
    "Byelorussian Catalan Chinese Croatian Czech Danish Dutch English Esperanto "
    "Estonian Finnish Flemish French Galician Georgian German Greek Hebrew Hindi "
    "Hungarian Icelandic Indonesian Italian Japanese Kazakh Korean Latvian "
    "Lithuanian Macedonian Malayalam Marathi Moldavian Mongolian Norwegian "
    "Persian Polish Portuguese Romanian Russian Serbian Serbo-Croatian "
    "Slovak Slovenian Spanish Swedish Tamil Thai Turkish Ukrainian "
    "Urdu Uzbek Vietnamese Yiddish"
).split()
# Spellings the volumes use for one language; the typed value is canonical.
LANGUAGE_VARIANTS = {
    "rumanian": "Romanian",
    "slovakian": "Slovak",
    "belorussian": "Byelorussian",
}
ROLES = (
    "author",
    "translator",
    "editor",
    "introduction",
    "afterword",
    "illustrator",
    "contributor",
)
OBJECT_TYPES = (
    "book_edition",
    "translation",
    "collection_contribution",
    "periodical_contribution",
    "review",
    "event",
    "holding",
    "reference",
    "collection",
)
RELATION_KINDS = (
    "reprint",
    "excerpt",
    "translation",
    "edition",
    "revised",
    "review",
    "item",
)
REFERENCE_KINDS = (
    "see",
    "reprint",
    "contents",
    "correction",
    "continuation",
    "excerpt",
    "translation",
    "review",
    "concerning",
    "based_on",
    "index",
    "related",
)
EDITION_KINDS = ("printing", "thousand", "copies", "licensed", "reprint", "edition")
YEAR_MIN, YEAR_MAX = 1450, 2030
RECORD_ID = r"^(I|A1|A2)/[A-R]/[^#\s]+$"
ADDRESS = r"^[A-R](A[12])? \d{1,4}[a-z]?$"

Span = Annotated[list[NonNegativeInt], Len(2, 2)]
RecordId = Annotated[str, Field(pattern=RECORD_ID)]


class _Strict(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", populate_by_name=True)


class _Value(_Strict):
    span: Span
    by: Literal["rule", "llm", "compiler", "inherited"]
    rule: str = Field(min_length=1)
    from_: RecordId | None = Field(default=None, alias="from")
    state: Literal["proposed"] | None = None

    @model_validator(mode="after")
    def _producer(self):
        if self.span[0] >= self.span[1]:
            raise ValueError("span must be non-empty")
        if self.by == "inherited" and not self.from_:
            raise ValueError("an inherited value names its source record")
        if (self.by == "llm") != (self.state == "proposed"):
            raise ValueError("state 'proposed' is required for llm and only for llm")
        return self


class Text(_Value):
    value: str = Field(min_length=1)


class Year(_Value):
    value: int = Field(ge=YEAR_MIN, le=YEAR_MAX)


class Flag(_Value):
    value: Literal[True]


class Role(_Value):
    value: Literal[ROLES]


class ObjectType(_Value):
    value: Literal[OBJECT_TYPES]


class Language(_Value):
    value: Literal[tuple(LANGUAGES)]


class RelationKind(_Value):
    value: Literal[RELATION_KINDS]


class ReferenceKind(_Value):
    value: Literal[REFERENCE_KINDS]


class Target(_Strict):
    normalized: str = Field(pattern=ADDRESS)
    record: RecordId | None = None


class Address(_Strict):
    """A printed address group ("F 33, 455"), resolved to the records it names."""

    address: Text
    targets: list[Target] = Field(min_length=1)
    locator: Text | None = None


class Reference(Address):
    kind: ReferenceKind


class Person(_Strict):
    name: Text | None = None
    roles: list[Role] = Field(min_length=1)


class Imprint(_Strict):
    place: Text | None = None
    publisher: Text | None = None
    year: Year | None = None
    year_end: Year | None = None
    year_bracketed: Flag | None = None
    circa: Flag | None = None

    @model_validator(mode="after")
    def _not_empty(self):
        if not (self.place or self.publisher or self.year):
            raise ValueError("an imprint holds a place, publisher or year")
        return self


class ExtentPart(_Strict):
    kind: Literal["roman", "counted", "uncounted"]
    text: Text


class Extent(_Strict):
    raw: Text
    parts: list[ExtentPart] = []
    volumes: Text | None = None
    illustrations: Text | None = None


class EditionNote(_Strict):
    kind: Literal[EDITION_KINDS]
    text: Text
    years: list[Year] = []


class Periodical(_Strict):
    title: Text | None = None
    siglum: Text | None = None
    place: Text | None = None
    volume: Text | None = None
    issue: Text | None = None
    date: Text | None = None
    year: Year | None = None
    pages: Text | None = None

    @model_validator(mode="after")
    def _not_empty(self):
        if not (self.title or self.siglum):
            raise ValueError("a periodical citation names a periodical")
        return self


class Series(_Strict):
    title: Text | None = None
    number: Text | None = None
    persons: list[Person] = []

    @model_validator(mode="after")
    def _not_empty(self):
        if not (self.title or self.number):
            raise ValueError("a series holds a title or a number")
        return self


class Citation(_Strict):
    """Another publication the object cites: its host volume or a reviewed work."""

    title: Text | None = None
    address: Address | None = None
    persons: list[Person] = []
    imprints: list[Imprint] = []
    extent: Extent | None = None
    series: list[Series] = []
    pages: Text | None = None
    locator: Text | None = None

    @model_validator(mode="after")
    def _not_empty(self):
        if not (self.title or self.address):
            raise ValueError("a citation holds a title or an address")
        return self


class ContentItem(_Strict):
    title: Text | None = None
    original_title: Text | None = None
    address: Address | None = None
    persons: list[Person] = []
    pages: Text | None = None
    notes: list[Text] = []

    @model_validator(mode="after")
    def _not_empty(self):
        if not (self.title or self.address):
            raise ValueError("a contents item holds a title or an address")
        return self


class Holding(_Strict):
    repository: Text | None = None
    text: Text


class Event(_Strict):
    date: Text | None = None
    year: Year | None = None
    place: Text | None = None
    medium: Text | None = None

    @model_validator(mode="after")
    def _not_empty(self):
        if not (self.date or self.year or self.place or self.medium):
            raise ValueError("an event holds a date, year, place or medium")
        return self


class Relation(_Strict):
    """How a further printing, excerpt or item relates to the object it follows."""

    kind: RelationKind
    target: str | None = None


class Inherited(_Strict):
    """Values from outside the object's own span; each names its record in "from"."""

    title: Text | None = None
    subject: Text | None = None
    language: Language | None = None
    work_refs: list[Address] = []
    persons: list[Person] = []
    imprints: list[Imprint] = []
    series: list[Series] = []


class PrintObject(_Strict):
    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        populate_by_name=True,
        json_schema_extra={"$id": SCHEMA_ID},
    )

    id: str = Field(pattern=r"^(I|A1|A2)/[A-R]/[^#\s]+#\d+$")
    entry: RecordId
    entry_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    volume: Literal["I", "A1", "A2"]
    part: str = Field(pattern=r"^[A-R]$")
    address: str
    span: Span
    text: str = Field(min_length=1)
    types: list[ObjectType] = []
    title: Text | None = None
    subtitle: Text | None = None
    original_title: Text | None = None
    variant_titles: list[Text] = []
    subject: Text | None = None
    language: Language | None = None
    work_refs: list[Address] = []
    persons: list[Person] = []
    imprints: list[Imprint] = []
    extent: Extent | None = None
    edition_notes: list[EditionNote] = []
    series: list[Series] = []
    periodicals: list[Periodical] = []
    hosts: list[Citation] = []
    reviewed: list[Citation] = []
    event: Event | None = None
    contents: list[ContentItem] = []
    informants: list[Text] = []
    holdings: list[Holding] = []
    notes: list[Text] = []
    references: list[Reference] = []
    relation: Relation | None = None
    inherited: Inherited = Inherited()

    @model_validator(mode="after")
    def _identity(self):
        if not self.id.startswith(self.entry + "#"):
            raise ValueError("object id must extend its entry id")
        if not self.entry.startswith(f"{self.volume}/{self.part}/"):
            raise ValueError("entry id must start with volume and part")
        if self.span[0] >= self.span[1]:
            raise ValueError("object span must be non-empty")
        return self


NON_EMPTY = {
    "Imprint": ("place", "publisher", "year"),
    "Periodical": ("title", "siglum"),
    "Series": ("title", "number"),
    "Citation": ("title", "address"),
    "ContentItem": ("title", "address"),
    "Event": ("date", "year", "place", "medium"),
}


def json_schema() -> dict:
    """The exported schema, with the conditions JSON Schema can express added."""
    schema = PrintObject.model_json_schema(by_alias=True)
    for name, definition in schema.get("$defs", {}).items():
        props = definition.get("properties", {})
        if "by" in props and "span" in props:
            definition["allOf"] = [
                {
                    "if": {"properties": {"by": {"const": "inherited"}}},
                    "then": {"required": ["from"]},
                },
                {
                    "if": {"properties": {"by": {"const": "llm"}}},
                    "then": {
                        "required": ["state"],
                        "properties": {"state": {"const": "proposed"}},
                    },
                    "else": {
                        "anyOf": [
                            {"not": {"required": ["state"]}},
                            {"properties": {"state": {"type": "null"}}},
                        ]
                    },
                },
            ]
        if name in NON_EMPTY:
            definition["anyOf"] = [
                {
                    "required": [field],
                    "properties": {field: {"not": {"type": "null"}}},
                }
                for field in NON_EMPTY[name]
            ]
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["title"] = "Klawiter print object"
    return schema

"""Offsets an LLM proposed for a print object, checked by rule and merged into gaps.

The model never returns a value, only character offsets into the object's text.
verify() turns each offset into a value of _schema.py only where the passage
holds what the field needs (any text for titles and names, four digits of a
plausible year, a credit word for a role); everything else is rejected and
counted. merge() fills only fields the rules left empty and never overwrites a
rule value. Every accepted value carries by "llm", the prompt identifier as
its rule and the state "proposed".

The cache (llm_cache.json beside this module) is versioned: it holds object
identifiers, keys and offsets, never print text. The key of an entry is an
HMAC of model, prompt and object text under a secret kept with the local print
data (data/print/derived/llm/secret), so a short object text cannot be
recovered from the versioned file by enumeration. A cached response applies
only while model, prompt and the object's text are unchanged; without the
secret every entry is stale, which fails safe.
"""

import hashlib
import hmac
import json
import re
import secrets

from _common import DERIVED_DIR, HERE
from _fields import ROLE_WORDS
from _schema import YEAR_MAX, YEAR_MIN

CACHE = HERE / "llm_cache.json"
SECRET = DERIVED_DIR / "llm" / "secret"
PROMPT_ID = "print-spans-v1"
PROMPT = """You read one entry of a printed bibliography of Stefan Zweig's works.
OBJECT is one publication or holding inside that entry. Return character
offsets into OBJECT (0-based, end exclusive) for what OBJECT states itself:
title, subtitle, place, publisher, year (the four digits of the year of
publication), periodical (the name of a journal or newspaper), date (of an
issue), pages, and persons as name offsets with the offsets of the credit word
that gives their role ("Trl.", "Ed.", "Translated by", "Afterword"). Return
offsets only, never text. Omit every field OBJECT does not state; do not infer.
"""
TEXT_FIELDS = ("title", "subtitle", "place", "publisher", "periodical", "date", "pages")


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _secret(create: bool = False) -> bytes | None:
    if SECRET.exists():
        return SECRET.read_bytes()
    if not create:
        return None
    SECRET.parent.mkdir(parents=True, exist_ok=True)
    SECRET.write_bytes(secrets.token_bytes(32))
    return SECRET.read_bytes()


def cache_key(model: str, obj_text: str, create: bool = False) -> str | None:
    key = _secret(create)
    if key is None:
        return None
    message = f"{model}|{sha(PROMPT)}|{obj_text}".encode("utf-8")
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def load_cache() -> dict:
    if not CACHE.exists():
        return {"about": __doc__.splitlines()[0], "prompt_id": PROMPT_ID, "entries": {}}
    return json.loads(CACHE.read_text(encoding="utf-8"))


def _span(pair, length: int) -> tuple[int, int] | None:
    if not (
        isinstance(pair, list) and len(pair) == 2 and all(type(x) is int for x in pair)
    ):
        return None
    a, b = pair
    return (a, b) if 0 <= a < b <= length else None


def _value(val, a: int, b: int) -> dict:
    return {
        "value": val,
        "span": [a, b],
        "by": "llm",
        "rule": f"llm:{PROMPT_ID}",
        "state": "proposed",
    }


def verify(obj: dict, response: dict) -> tuple[dict, list[str]]:
    """Proposed fields of one object from offsets into its text, and the rejections."""
    text, base = obj["text"], obj["span"][0]
    out: dict = {}
    rejected: list[str] = []

    def text_at(field: str, pair) -> dict | None:
        span = _span(pair, len(text))
        if not span:
            rejected.append(f"{field}: offsets outside the object")
            return None
        a, b = span
        while a < b and text[a] in " ,;:.":
            a += 1
        while b > a and text[b - 1] in " ,;:":
            b -= 1
        if b <= a or not re.search(r"[^\W_]", text[a:b]):
            rejected.append(f"{field}: empty passage")
            return None
        return _value(text[a:b], base + a, base + b)

    for field in TEXT_FIELDS:
        if response.get(field) is not None:
            v = text_at(field, response[field])
            if v:
                out[field] = v
    if response.get("year") is not None:
        span = _span(response["year"], len(text))
        passage = text[span[0] : span[1]] if span else ""
        if re.fullmatch(r"\d{4}", passage) and YEAR_MIN <= int(passage) <= YEAR_MAX:
            out["year"] = _value(int(passage), base + span[0], base + span[1])
        else:
            rejected.append("year: passage is no year")
    persons = []
    for person in response.get("persons") or []:
        name = text_at("person", person.get("name"))
        role_span = _span(person.get("role"), len(text))
        word = text[role_span[0] : role_span[1]] if role_span else ""
        # A credit is a short phrase that opens with a credit word; a long
        # passage would yield every role word it happens to hold.
        first = re.match(r"[A-Za-z]+", word)
        if len(word) > 40 or not first or first.group().lower() not in ROLE_WORDS:
            rejected.append("person: role passage is no credit")
            continue
        if not name and not re.search(
            r"not indicated", text[role_span[0] : role_span[1] + 20]
        ):
            rejected.append("person: no name and no 'not indicated'")
            continue
        roles = [
            _value(
                ROLE_WORDS[w.lower()],
                base + role_span[0] + m.start(),
                base + role_span[0] + m.end(),
            )
            for m in re.finditer(r"[A-Za-z]+\.?", word)
            if (w := m.group().rstrip(".")).lower() in ROLE_WORDS
        ]
        if not roles:
            rejected.append("person: role passage holds no credit word")
            continue
        persons.append({"name": name, "roles": roles} if name else {"roles": roles})
    if persons:
        out["persons"] = persons
    return out, rejected


def merge(obj: dict, proposed: dict) -> list[str]:
    """Fill the object's empty fields from verified proposals; return what was filled."""
    filled = []
    inherited = obj.get("inherited") or {}
    # An inherited title or imprint and a host citation count as filled: the
    # model fills gaps, it does not pre-empt a rule or the inheritance.
    cited = obj.get("periodicals") or obj.get("hosts") or obj.get("reviewed")
    if proposed.get("title") and not obj.get("title") and not inherited.get("title"):
        obj["title"] = proposed["title"]
        filled.append("title")
    if proposed.get("subtitle") and not obj.get("subtitle") and obj.get("title"):
        obj["subtitle"] = proposed["subtitle"]
        filled.append("subtitle")
    imprint = {
        k: proposed[k] for k in ("place", "publisher", "year") if proposed.get(k)
    }
    if (
        imprint
        and not obj.get("imprints")
        and not inherited.get("imprints")
        and not cited
    ):
        obj["imprints"] = [imprint]
        filled.append("imprints")
    if proposed.get("periodical") and not cited and not obj.get("imprints"):
        periodical = {"title": proposed["periodical"]}
        for field in ("date", "pages", "year"):
            if proposed.get(field):
                periodical[field] = proposed[field]
        obj["periodicals"] = [periodical]
        filled.append("periodicals")
    if proposed.get("persons") and not obj.get("persons"):
        obj["persons"] = proposed["persons"]
        filled.append("persons")
    return filled


def apply_cache(obj: dict, cache: dict) -> list[str]:
    """Merge a cached, still valid response for obj; nothing happens without one.

    The entry names its model; a changed prompt or object text invalidates it.
    """
    entry = cache.get("entries", {}).get(obj["id"])
    if not entry or entry.get("key") != cache_key(entry.get("model", ""), obj["text"]):
        return []
    proposed, _ = verify(obj, entry["response"])
    return merge(obj, proposed)

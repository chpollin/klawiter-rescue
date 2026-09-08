"""Value guard of the frozen enrichment layer.

The cache holds model output whose encoding the model itself damaged, and
publisher strings that are in fact contribution credits. Both are corrected
deterministically before a value can reach a record: a misread that the
byte round-trip undoes is repaired, a misread that it cannot undo empties the
field, and a credit phrase is never a publisher.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from lib.llm_extract import repair_or_reject, validate_extraction


def _extraction(**fields):
    base = {
        "page_id": 1,
        "publisher": None,
        "location": None,
        "translator": None,
        "page_count": None,
    }
    base.update(fields)
    return SimpleNamespace(**base)


@pytest.mark.parametrize(
    ("damaged", "repaired"),
    [
        ("Otokar KerÅ¡ovani", "Otokar Keršovani"),
        ("KavkazskiÄ­ Krai", "Kavkazskiĭ Krai"),
        ("Mlada zaloÅ¾ba", "Mlada založba"),
        ("Xiâ€™an", "Xi’an"),
    ],
)
def test_a_reversible_misreading_is_repaired(damaged: str, repaired: str) -> None:
    assert repair_or_reject(damaged) == repaired


def test_an_irreversible_misreading_empties_the_field() -> None:
    """The closing quote of this value was lost before the cache was frozen,
    so no round-trip restores it and an empty field is the honest result."""
    assert repair_or_reject("Izdatelâ€™stvo â€œPravdaâ€") is None


def test_clean_values_pass_unchanged() -> None:
    for value in ("Insel-Verlag", "Kavkazskiĭ Krai", "S. Fischer Verlag"):
        assert repair_or_reject(value) == value


def test_the_repair_reaches_the_validated_result() -> None:
    result = validate_extraction(
        _extraction(publisher="Otokar KerÅ¡ovani", location="Xiâ€™an")
    )
    assert result["publisher"] == "Otokar Keršovani"
    assert result["location"] == "Xi’an"


def test_an_irreparable_value_does_not_reach_the_result() -> None:
    result = validate_extraction(_extraction(publisher="Izdatelâ€™stvo â€œPravdaâ€"))
    assert "publisher" not in result


def test_a_credit_phrase_is_never_a_publisher() -> None:
    result = validate_extraction(
        _extraction(publisher="Translated by A. Druktenis. 343p. 2nd edition")
    )
    assert "publisher" not in result

"""Print addresses the wiki text cites, read syntactically, state "cites".

Every source line below is a verbatim line of the named page in dump form
(data/intermediate/04_classified.csv). The corpus checks run over the
published frontend dataset and the classified source rows.
"""

from __future__ import annotations

import pytest
from lib.encoding import unescape_dump_quotes
from lib.print_addresses import cited_print_addresses


def _addresses(text: str) -> list[str]:
    return [c["printAddress"] for c in cited_print_addresses(text)]


def test_a_bracketed_work_address_after_a_title_is_read() -> None:
    """Page 531 names the translated work and its main-volume address."""
    text = "[Der Amokläufer. F 1] in [[Novelle]] [4], pp. 126-176"
    (citation,) = cited_print_addresses(text)
    assert citation == {
        "printAddress": "F 1",
        "printVolume": "main-volume",
        "printSection": "F",
        "printEntryNumber": 1,
        "citationState": "cites",
        "citationNotation": "bracket",
        "sourceValue": "F 1",
        "sourceStart": 17,
        "sourceEnd": 20,
        "passageText": "[Der Amokläufer. F 1]",
        "passageStart": 0,
        "passageEnd": 21,
    }


def test_a_see_chain_reads_every_coded_address_and_no_bare_number() -> None:
    """Page 212: the numbers after G 201 may be entries or pages, so they
    stay unread."""
    text = (
        "Translated by Eugen Relgis. 248p. Bucureşti: Editura Ştiinţifică, 1996 "
        "(Ardealul). [See H 670, G 131 & H 490, G 445. See G 201, 491, 492]"
    )
    citations = cited_print_addresses(text)
    assert [c["printAddress"] for c in citations] == [
        "H 670",
        "G 131",
        "H 490",
        "G 445",
        "G 201",
    ]
    assert {c["citationNotation"] for c in citations} == {"see"}
    assert citations[0]["passageText"] == "See H 670, G 131 & H 490, G 445"
    assert citations[-1]["passageText"] == "See G 201"


def test_addendum_addresses_are_read_wherever_they_stand() -> None:
    """Page 2155 transcribes the contents of Addendum I."""
    text = (
        "English, 277-285, pp. 129-130. See GA1 47, 55, pp. 82, 83. "
        "JA1 8, 9, pp. 143-144. LA1 229, p. 278"
    )
    citations = cited_print_addresses(text)
    assert [c["printAddress"] for c in citations] == ["GA1 47", "JA1 8", "LA1 229"]
    assert {c["printVolume"] for c in citations} == {"addendum-1"}


def test_a_range_keeps_its_first_and_last_number() -> None:
    """Page 3150."""
    (citation, *_rest) = cited_print_addresses(
        "[1]. Bulgarian [G 796-798]. [2]. Czech [G 800]."
    )
    assert citation["printAddress"] == "G 796-798"
    assert citation["printEntryNumber"] == 796
    assert citation["printEntryNumberEnd"] == 798


def test_a_parenthesis_list_is_read() -> None:
    """Page 2669."""
    assert _addresses("Portuguese (A 74, 85, 98 / C 48, 49)") == ["A 74", "C 48"]


def test_an_unnumbered_addendum_ii_address_runs_to_its_year() -> None:
    """Page 2286 cites Addendum II by code, title and year; page 560 shows that
    a number after an unnumbered code is a title word."""
    text = "[2]. LA2 Stefan Zweig - Triumph und Tragik [1992], No. 2,  pp. 13-14."
    (citation,) = cited_print_addresses(text)
    assert citation["printAddress"] == "LA2"
    assert "printEntryNumber" not in citation
    assert citation["passageText"] == "LA2 Stefan Zweig - Triumph und Tragik [1992]"
    (polish,) = cited_print_addresses("FA2 24 godziny 1928 [3], pp. 85-126")
    assert polish["printAddress"] == "FA2"
    assert "printEntryNumber" not in polish


@pytest.mark.parametrize(
    "text",
    [
        # Page 7460: the article and a year.
        "Risālah min imra'ah majhūlah [A 1962 Arabic film]. [ ].",
        # Page 29: an issue number of a newspaper edition.
        "21 October 1929 [Abendausgabe B 246], p. (5)",
        # Page 661: a number of a Chinese series.
        "[[Ciweige miao yulu]] [Lanzhou, 1991], No. B 15",
        # Page 2052: dates with roman months.
        "20 VIII 1932, 16 I 1933, 25 I 1933, 15 II 1933, 10 V 1935",
        # Page 323: pages of the Börsenblatt supplement.
        "[29 August 1986], Aus dem Antiquariat, pp. A357-A358",
        # Page 501: a series number.
        "187p. [Compass Books, C 99]",
        # Page 2154: A 1, A 143 or an addendum, the notation does not say.
        "Serbo-Croatian, 76, p. 188. See A1 43, p. 18",
    ],
)
def test_tokens_that_only_look_like_addresses_are_not_read(text) -> None:
    assert cited_print_addresses(text) == []


def test_the_unspaced_form_is_read_only_right_after_see() -> None:
    """Page 2154: "See D11, 38, 164, p. 934"."""
    text = "Individual Poems, 7-227, pp. 44-74. See D11, 38, 164, p. 934"
    (citation,) = cited_print_addresses(text)
    assert citation["printAddress"] == "D 11"
    assert citation["sourceValue"] == "D11"


# Corpus checks over the published dataset.


def test_every_cited_address_is_a_bound_cites_reference(
    classified_rows, ns0_by_id
) -> None:
    identity_keys = {"sameAs", "printRecord", "printRecordId", "identity"}
    checked = 0
    for row in classified_rows:
        entry = ns0_by_id.get(int(row["page_id"]))
        if entry is None:
            continue
        text = row["raw_content"]
        for citation in entry.get("printAddressCitations", []):
            assert citation["citationState"] == "cites"
            assert not identity_keys & set(citation)
            start, end = citation["sourceStart"], citation["sourceEnd"]
            assert text[start:end] == citation["sourceValue"]
            passage = text[citation["passageStart"] : citation["passageEnd"]]
            assert unescape_dump_quotes(passage) == citation["passageText"]
            assert citation["passageStart"] <= start and end <= citation["passageEnd"]
            checked += 1
    assert checked, "no page cites a print address"


def test_the_meta_counts_the_cited_addresses(frontend_data, ns0_entries) -> None:
    cited = [e for e in ns0_entries if e.get("printAddressCitations")]
    assert frontend_data["_meta"]["printAddressCitations"] == {
        "pages": len(cited),
        "citations": sum(len(e["printAddressCitations"]) for e in cited),
    }

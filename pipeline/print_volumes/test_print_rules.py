"""Regression cases for reading rules that fresh-context reviews found wrong.

Each case is an invented entry in the notation of one volume, never print
text. It pins the reading a rule fix produced, so that a later change that
undoes it fails here, before the all-records invariants or a review.
"""

import hashlib
import re

import pytest
from _addresses import REFERENCE
from _fields import Reader


def read(text, volume="I", part="F", span=None, **ctx):
    record = {
        "id": f"{volume}/{part}/12",
        "volume": volume,
        "part": part,
        "page": 1,
        "page_end": 1,
        "address": "" if volume == "A2" else f"{part} 12",
        "kind": "entry",
        "text": text,
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "objects": [],
    }
    return Reader(record, span or (0, len(text)), {"index": {}, **ctx}).run()


def val(node, *path):
    for key in path:
        node = node[key]
    return node["value"]


def test_a_section_code_before_a_host_title_is_its_address():
    out = read("[2]. AA2 12 Gesammelte Werke 1990 [3], pp. 10-20.", volume="A2")
    host = out["hosts"][0]
    assert val(host, "address", "address") == "AA2 12"
    assert val(host, "title") == "Gesammelte Werke"


def test_a_number_before_a_lower_case_word_belongs_to_the_title():
    out = read("[2]. FA2 24 stunden. Ort: Verlag, 1990, pp. 10-20.", volume="A2")
    assert val(out["hosts"][0], "title").startswith("24 stunden")
    assert "address" not in out["hosts"][0]


def test_a_host_author_in_initials_is_a_person():
    out = read(
        'L 12 NACHNAME, VORNAME. "Ein Aufsatz", F. Nachname. Das Buch der Essays: '
        "Studien. Ort: Verlag, 1950, pp. 3-9.",
        part="L",
    )
    host = out["hosts"][0]
    assert val(host, "persons", 0, "name") == "F. Nachname"
    assert val(host, "title") == "Das Buch der Essays: Studien"


def test_a_credit_sentence_ends_a_host_title():
    out = read(
        '12 "Ein Aufsatz" in Das Buch der Essays. Edited by Vorname Nachname. '
        "Ort: Verlag, 1950, pp. 3-9.",
        part="H",
    )
    assert val(out["hosts"][0], "title") == "Das Buch der Essays"


def test_the_year_of_an_almanac_title_stays_in_the_title():
    out = read(
        '12 "Ein Gedicht" in Almanach auf das Jahr 1912. Ort: Verlag, 1911, pp. 3-9.',
        part="D",
    )
    host = out["hosts"][0]
    assert val(host, "title") == "Almanach auf das Jahr 1912"
    assert val(host, "imprints", 0, "year") == 1911


def test_a_contents_bracket_is_an_original_title_only_in_a_translation():
    text = "12 TITEL. 99p. Ort: Verlag, 1950. Contents: [1]. Erste Novelle [Vorname Nachname]."
    german = read(text)
    assert "original_title" not in german["contents"][0]
    translated = read(text, language="French")
    assert val(translated["contents"][0], "original_title") == "Vorname Nachname"
    credit = read(text.replace("[Vorname", "[Foreword by Vorname"), language="French")
    assert "original_title" not in credit["contents"][0]


def test_a_letter_holding_runs_past_the_dot_of_a_month():
    out = read(
        "[1]. SIGL: Zweig to Nachname, 2 letters, 31 Oct. 1912 and 3 Nov. 1913.",
        part="K",
    )
    assert any(val(h, "text").endswith("1913") for h in out["holdings"])


def test_an_edition_line_names_publisher_then_place():
    out = read("12 Verlag: 299/(2)p. Ort am Fluss, 1984.", part="G")
    imprint = out["imprints"][0]
    assert (val(imprint, "publisher"), val(imprint, "place"), val(imprint, "year")) == (
        "Verlag",
        "Ort am Fluss",
        1984,
    )


@pytest.mark.parametrize(
    "tail",
    [
        "Screenplay Vorname Nachname. 1970 meters.",
        "Lives of the author 1881 - 1942.",
        "Booklet, pp. 1522-1523.",
    ],
)
def test_an_event_year_is_no_length_life_or_page(tail):
    out = read(f"12 TITEL [F 5]. Land, 1923. {tail}", part="N")
    assert val(out["event"], "year") == 1923


def test_a_month_word_needs_to_end_as_a_month():
    out = read("12 TITEL [F 5]. Screenplay Vorname Janowitz. 1970 meters.", part="N")
    assert "date" not in out.get("event", {})


@pytest.mark.parametrize(
    "text, groups",
    [
        ("Ort, 1990, pp. A345-A346.", []),
        ("Compass Books C 10. See A 57.", ["A 57"]),
        ("Rep. G 126, pp. 3-9.", ["G 126"]),
        ("See HA1 35[1], 38.", ["HA1 35[1], 38"]),
    ],
)
def test_page_and_series_numbers_are_no_addresses(text, groups):
    assert [m.group().strip() for m in REFERENCE.finditer(text)] == groups


def test_a_shared_surname_stays_one_credit():
    out = read("12 TITEL. Trl. Vorname & Andere Nachname. 99p. Ort: Verlag, 1950.")
    names = [val(p, "name") for p in out["persons"] if "name" in p]
    assert names == ["Vorname & Andere Nachname"]


def test_a_language_label_may_carry_a_bracket_note():
    text = (
        'M 12 TITEL. French: [1]. "Eins" in Blatt (Ort), 1 Jan. 1935. '
        'Spanish [Reviews of the premiere [i.e. a note]: [2]. "Zwei" in Blatt (Ort), 2 Jan. 1935.'
    )
    start = text.index("[2].")
    out = read(text, volume="A1", part="M", span=(start, len(text)))
    assert val(out, "language") == "Spanish"


def test_a_short_title_reference_gives_its_place_before_the_year():
    out = read(
        "[3]. Trois mots Paris 1985 [4], pp. 1-9.", volume="A2", places={"Paris"}
    )
    host = out["hosts"][0]
    assert val(host, "title") == "Trois mots"
    assert val(host, "imprints", 0, "place") == "Paris"
    guarded = read(
        "[3]. Lettres de Paris 1985 [4], pp. 1-9.", volume="A2", places={"Paris"}
    )
    assert val(guarded["hosts"][0], "title") == "Lettres de Paris"


def test_a_compiler_note_has_no_title():
    out = read("NB: See Index A1.", volume="A1", part="D")
    assert "title" not in out


def test_a_reviewed_book_in_a_rev_list_opens_with_its_author():
    text = "12 TITEL. REV: [1]. Vorname Nachname. Das Buch. Ort: Verlag, 1922."
    start = text.index("[1].")
    out = read(
        text, volume="A1", part="H", span=(start, len(text)), label_kind="review"
    )
    assert val(out, "title") == "Das Buch"
    assert val(out["persons"][0], "name") == "Vorname Nachname"


def test_general_abbreviations_are_no_informants():
    out = read(
        "[1]. SIGL: Zweig to Nachname, 1 letter [EXC], 22 July 1938 [AB].", part="K"
    )
    assert [val(i) for i in out.get("informants", [])] == ["AB"]
    assert val(out["holdings"][0], "text").endswith("1938")


def test_a_periodical_title_may_open_with_a_non_ascii_letter():
    out = read(
        '12 "Ein Aufsatz" in Österreichische Blätter (Wien), 5:57 (30 Nov. 1905), 222.',
        volume="A1",
        part="D",
    )
    assert val(out["periodicals"][0], "title") == "Österreichische Blätter"


def test_a_double_space_does_not_hide_credit_imprint_or_address():
    out = read(
        "[1]. Titel.  Translated by Vorname Nachname.  99p. Ort: Verlag,  2005. See DA2  6.",
        volume="A2",
        part="G",
    )
    assert [val(p, "name") for p in out["persons"]] == ["Vorname Nachname"]
    assert val(out["imprints"][0], "year") == 2005
    assert [m.group(3) for m in REFERENCE.finditer("See DA2  6.")] == ["6"]


def test_a_hyphenated_reprint_label_still_splits():
    from _objects import SPLIT_LABEL

    for label in (
        "Reprin- ted in:",
        "Reprinted [slightly revised] in:",
        "Reprinted in:",
    ):
        assert SPLIT_LABEL.search(label).group("reprint")


def _index_line(page, line, top, *runs, volume="I", part="Index A"):
    """An invented index line from (x0, text, x1) runs, as p01 writes it."""
    return {
        "volume": volume,
        "part": part,
        "kind": "index",
        "page": page,
        "line": line,
        "top": top,
        "x0": runs[0][0],
        "text": "".join(r[1] for r in runs),
        "runs": [["Times", 12.0, x0, text, x1] for x0, text, x1 in runs],
    }


def _apparatus(lines, volume="I"):
    from _apparatus import apparatus_records

    index = {"G 12": "I/G/12", "K 7": "I/K/7", "L 30": "I/L/30"}
    records, _ = apparatus_records(lines, volume, index)
    return records


def test_two_index_columns_on_one_baseline_split_at_the_gutter():
    records = _apparatus(
        [
            _index_line(
                800,
                1,
                100,
                (72, "Nachname, Erika, G 12 ", 170),
                (291, "Zweiter, Max, K 7", 380),
            ),
            _index_line(800, 2, 114, (72, "Dritte, Anna, L 30", 160)),
        ]
    )
    assert [r["text"] for r in records] == [
        "Nachname, Erika, G 12",
        "Dritte, Anna, L 30",
        "Zweiter, Max, K 7",
    ]
    assert records[2]["id"] == "I/index-a/p800l1c2"
    item = records[0]["objects"][0]
    assert item["term"]["value"] == "Nachname, Erika"
    assert [t["record"] for t in item["references"][0]["targets"]] == ["I/G/12"]


def test_a_continuation_at_the_margin_and_a_vertical_strip_stay_in_their_entry():
    records = _apparatus(
        [
            _index_line(800, 1, 100, (72, "Nachname, Erika, G 12 / K", 190)),
            _index_line(800, 2, 114, (72, "7 / L", 100), (250, "3", 256)),
            _index_line(800, 3, 128, (250, "0", 256)),
            _index_line(800, 4, 142, (72, "Dritte, Anna, G 12", 160)),
        ]
    )
    assert [r["text"] for r in records] == [
        "Nachname, Erika, G 12 / K 7 / L 30",
        "Dritte, Anna, G 12",
    ]


def test_a_title_after_a_siglum_opens_no_entry():
    records = _apparatus(
        [
            _index_line(
                940,
                1,
                100,
                (72, "ABCDE ", 110),
                (191, "ABC Blatt (Ort) - G 12", 300),
                part="Index E",
            ),
            _index_line(
                940,
                2,
                114,
                (72, "FGHIJ ", 110),
                (191, "Zeitung (Ort) - K 7", 300),
                part="Index E",
            ),
        ]
    )
    assert [r["objects"][0]["term"]["value"] for r in records] == [
        "ABCDE ABC Blatt (Ort)",
        "FGHIJ Zeitung (Ort)",
    ]


def test_rule_patterns_hold_no_control_character():
    import _apparatus
    import _fields

    for module in (_fields, _apparatus):
        for name, pattern in vars(module).items():
            if isinstance(pattern, re.Pattern):
                assert "\x08" not in pattern.pattern, name

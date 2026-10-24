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


def _glyph(text, x0, top=100.0):
    return {
        "text": text,
        "x0": x0,
        "x1": x0 + 5,
        "top": top,
        "bottom": top + 10,
        "fontname": "ABCDEF+Times",
        "size": 12.0,
    }


def test_a_row_led_by_a_space_still_opens_a_run_at_the_right_column():
    from _apparatus import segments
    from p01_extract import _line_record

    text = "Nachname, Erika, G 12"
    row = [_glyph(" ", 250)] + [_glyph(c, 291 + 5 * i) for i, c in enumerate(text)]
    line = _line_record("I", 800, 0, row)
    assert line["text"] == " " + text
    assert [run[2] for run in line["runs"]] == [250, 291]
    pieces = segments({**line, "part": "Index A", "kind": "index"}, 280.0)
    assert [(p["text"], p["column"]) for p in pieces] == [(text, 2)]


def test_a_strip_after_a_new_entry_joins_that_entry():
    records = _apparatus(
        [
            _index_line(800, 1, 100, (72, "Erste, Anna, G 12 / K", 190)),
            _index_line(800, 2, 114, (250, "7", 256)),
            _index_line(800, 3, 128, (72, "Zweite, Berta, K 7 / L", 190)),
            _index_line(800, 4, 142, (250, "3", 256)),
            _index_line(800, 5, 156, (250, "0", 256)),
        ]
    )
    assert [r["text"] for r in records] == [
        "Erste, Anna, G 12 / K 7",
        "Zweite, Berta, K 7 / L 30",
    ]


def _a1(page, line, top, *runs, part="Index A"):
    return _index_line(page, line, top, *runs, volume="A1", part=part)


def test_a_full_width_heading_splits_the_page_into_blocks():
    records = _apparatus(
        [
            _a1(
                430,
                1,
                100,
                (105, "Erstes Werk [F 1]: GA1 1 /", 290),
                (315, "KA1 7 / LA1 8", 450),
            ),
            _a1(430, 2, 110, (125, "HA1 3 /", 200)),
            _a1(430, 3, 130, (105, "A2 TITLES OF A GROUP", 400)),
            _a1(
                430,
                4,
                150,
                (105, "Drittes Werk [F 3]: GA1 3", 290),
                (315, "Viertes Werk [F 4]: GA1 4", 500),
            ),
            _a1(430, 5, 160, (125, "HA1 5", 200)),
            _a1(430, 6, 170, (125, "HA1 6", 200)),
        ],
        volume="A1",
    )
    assert [r["text"] for r in records] == [
        "Erstes Werk [F 1]: GA1 1 / HA1 3 / KA1 7 / LA1 8",
        "A2 TITLES OF A GROUP",
        "Drittes Werk [F 3]: GA1 3 HA1 5 HA1 6",
        "Viertes Werk [F 4]: GA1 4",
    ]


def test_addendum_entries_open_after_a_blank_line_not_at_a_bracket_or_numeral():
    records = _apparatus(
        [
            _a1(441, 1, 100, (105, "Thema: [1]. Erstes: GA1 1.", 290), part="Index B"),
            _a1(
                441,
                2,
                110,
                (105, "[2]. Zweites: GA1 2 / BA1 4[Vol.", 290),
                part="Index B",
            ),
            _a1(441, 3, 120, (105, "III] / BA1 5", 200), part="Index B"),
            _a1(441, 4, 140, (105, "Neues Thema: GA1 7", 290), part="Index B"),
            _a1(441, 5, 150, (105, "Frau [F 40]: GA1 8", 290), part="Index B"),
        ],
        volume="A1",
    )
    assert [r["text"] for r in records] == [
        "Thema: [1]. Erstes: GA1 1. [2]. Zweites: GA1 2 / BA1 4[Vol. III] / BA1 5",
        "Neues Thema: GA1 7 Frau [F 40]: GA1 8",
    ]


def test_a_cross_reference_waits_for_its_label_and_a_gap_opens_a_name():
    records = _apparatus(
        [
            _a1(460, 1, 100, (105, "Erster, Hans. See Index", 290), part="Index D"),
            _a1(460, 2, 110, (105, "A5:Anderer Titel", 290), part="Index D"),
            _a1(460, 3, 120, (105, "Zweiter, Max: LA1 3", 290), part="Index D"),
            _a1(460, 4, 140, (105, "de Dritte, Eva: LA1 4", 290), part="Index D"),
        ],
        volume="A1",
    )
    assert [r["text"] for r in records] == [
        "Erster, Hans. See Index A5:Anderer Titel",
        "Zweiter, Max: LA1 3",
        "de Dritte, Eva: LA1 4",
    ]
    assert "references" not in records[0]["objects"][0]


def test_a_substitute_capital_opens_a_name():
    records = _apparatus(
        [
            _index_line(910, 1, 100, (72, "Zahn, Anna, G 12", 170)),
            _index_line(910, 2, 114, (72, "åname, Erika, K 7", 170)),
        ]
    )
    assert [r["text"] for r in records] == [
        "Zahn, Anna, G 12",
        "åname, Erika, K 7",
    ]


def test_index_labels_and_item_locators_read_as_no_address():
    from _apparatus import apparatus_records

    text = "Titel [F 1]: HA1 35[No. 17], 38 / PA1 3[B4], 4. See Index A5:Anderes"
    index = {
        "F 1": "I/F/1",
        "HA1 35": "A1/H/35",
        "HA1 38": "A1/H/38",
        "PA1 3": "A1/P/3",
        "PA1 4": "A1/P/4",
    }
    (record,), _ = apparatus_records([_a1(430, 1, 100, (105, text, 290))], "A1", index)
    refs = record["objects"][0]["references"]
    assert [r["address"]["value"] for r in refs] == [
        "F 1",
        "HA1 35[No. 17], 38",
        "PA1 3[B4], 4",
    ]
    assert [[t["normalized"] for t in r["targets"]] for r in refs] == [
        ["F 1"],
        ["HA1 35", "HA1 38"],
        ["PA1 3", "PA1 4"],
    ]
    assert record["objects"][0]["term"]["value"] == "Titel"
    for ref in refs:
        a, b = ref["address"]["span"]
        assert text[a:b] == ref["address"]["value"]
    # The entries' shared grammar is unchanged: it still ends the group there.
    assert [m.group(3) for m in REFERENCE.finditer("HA1 35[No. 17], 38")] == ["35"]


def test_letter_spaced_digits_read_as_one_address_list():
    from _apparatus import apparatus_records

    text = "Nachname, Erika, G 1 2 , 1 4 , 3 0 - 3 2 / K 7[1],  9"
    (record,), _ = apparatus_records(
        [_index_line(800, 1, 100, (72, text, 250))], "I", {}
    )
    refs = record["objects"][0]["references"]
    assert [r["address"]["value"] for r in refs] == [
        "G 1 2 , 1 4 , 3 0 - 3 2",
        "K 7[1],  9",
    ]
    assert [[t["normalized"] for t in r["targets"]] for r in refs] == [
        ["G 12", "G 14", "G 30", "G 31", "G 32"],
        ["K 7", "K 9"],
    ]


def test_a_joined_index_line_under_the_running_head_is_no_furniture():
    records = _apparatus(
        [
            _a1(461, 0, 44.2, (105, "Index D: Running Title 900", 300), part="Index D"),
            _a1(
                461,
                1,
                57.0,
                (105, "Erster, Hans: LA1 9", 200),
                (315, "Zweiter, Max: LA1 10", 420),
                part="Index D",
            ),
        ],
        volume="A1",
    )
    assert [r["text"] for r in records] == [
        "Erster, Hans: LA1 9",
        "Zweiter, Max: LA1 10",
    ]
    assert records[1]["lines"] == [[461, 1, 2, 19, 39]]


def _objects(text, volume="A2", part="D"):
    """Read every object of an invented entry as p03 does, with its label."""
    from _objects import object_parts

    return [
        read(
            text,
            volume=volume,
            part=part,
            span=p["span"],
            label_kind=p["label"][2] if p["label"] else None,
        )
        for p in object_parts(text, part, "entry")
    ]


def test_a_letter_source_with_its_place_is_no_title():
    archive, letters = _objects(
        "12 Nachname, Vorname [1]. Archiv, Verlag Nachname (Ort), "
        "[a]. Zweig to Nachname, 2 letters, 5 May 1930.",
        volume="A1",
        part="K",
    )
    assert "title" not in archive
    dealer = read(
        "[2]. Antiquariat Name (Ort), Katalog 5, No. 12, Zweig to someone, 1 letter.",
        volume="A1",
        part="K",
        label_kind="item",
    )
    assert "title" not in dealer


def test_a_publication_named_after_the_letter_source_is_the_host():
    out = read(
        "[1]. Bibliothek Name (Ort), Ein Katalogtitel [LA1 10], p. 83, "
        "Zweig to Nachname, 1 letter, 5 May 1930.",
        volume="A1",
        part="K",
        label_kind="item",
    )
    host = out["hosts"][0]
    assert val(host, "title") == "Ein Katalogtitel"
    assert val(host, "address", "address") == "LA1 10"
    assert val(host, "pages") == "83"


def test_items_under_a_manuscript_label_are_holdings():
    from _objects import object_parts

    text = (
        "12 “Ein Gedicht” in Zeitung [Ort], 1 May 1910, p. 3. Reprinted in: "
        "[1]. Ein Buch. Ort: Verlag, 1950, p. 5. Manuscript versions: "
        "[2]. Handschriftenabteilung, Stadtbibliothek Ort [Abschrift]. "
        "[3]. The album is located in the Stadtbibliothek Ort under the number Ab 12.345."
    )
    labels = [p["label"][2] for p in object_parts(text, "D", "entry")[1:]]
    assert labels == ["reprint", "item", "item"]
    *_, kept, located = _objects(text)
    assert "title" not in kept
    assert val(kept, "holdings", 0, "text") == (
        "Handschriftenabteilung, Stadtbibliothek Ort"
    )
    assert val(located, "holdings", 0, "repository") == "Stadtbibliothek Ort"


def test_a_reviewed_work_cited_by_section_code_has_no_code_author():
    out = read(
        "Rt. “Titel” in Zeitung [Ort], 14 May 1908, pp. 1-2. Review of: EA2 "
        "Werktitel. Ein Trauerspiel. Ort: Verlag, 1907.",
        volume="A2",
        part="L",
    )
    reviewed = out["reviewed"][0]
    assert "persons" not in reviewed
    assert val(reviewed, "title") == "Werktitel. Ein Trauerspiel"
    assert val(reviewed, "imprints", 0, "place") == "Ort"
    named = read(
        "Nachname, Vorname. “Titel” in Zeitung [Ort], 1 May 1999, p. 2. "
        "Review of: LA2 Autorname, Vorname. Ein Buchtitel. Ort: Verlag, 1998.",
        volume="A2",
        part="L",
    )["reviewed"][0]
    assert val(named, "persons", 0, "name") == "Autorname, Vorname"
    assert val(named, "title") == "Ein Buchtitel"


def test_a_head_name_holds_no_address():
    text = "I 12 “Titel” [Original], I 5, p. 3. REP: A 32; Kurztitel (I 126), Vol. 3, p. 631."
    start = text.index("Kurztitel")
    out = read(text, part="I", span=(start, len(text)), label_kind="reprint")
    assert "persons" not in out
    assert val(out["hosts"][0], "title") == "Kurztitel"


def test_host_authors_named_forename_first_are_persons():
    out = read(
        "[4]. Vorname Nachname, Anders Zweitname. Haupttitel: Ein Untertitel für "
        "alle. Ort: Verlag, 1926, pp. 117-118.",
        part="D",
        label_kind="reprint",
    )
    host = out["hosts"][0]
    assert [val(p, "name") for p in host["persons"]] == [
        "Vorname Nachname",
        "Anders Zweitname",
    ]
    assert val(host, "persons", 0, "roles", 0) == "author"
    assert val(host, "title") == "Haupttitel: Ein Untertitel für alle"


@pytest.mark.parametrize(
    "tail",
    [
        "Band 4: Teil. By Vorname Nachname. Ort: Verlag, 1984, p. 99.",
        "Ort: Verlag, (1996). No. 3, p. 9.",
    ],
)
def test_two_words_before_a_volume_or_an_imprint_stay_the_title(tail):
    out = read(f'12 "Ein Beitrag" in Kleine Schriften. {tail}', volume="A1", part="L")
    assert "persons" not in out["hosts"][0]


def test_a_host_editor_in_brackets_after_the_name_is_a_person():
    out = read(
        '[3]. "Ein Beitrag" in Vorname Nachname [Ed.]. Haupttitel. Ein Führer '
        "durch alles. Ort: Verlag, 1994, pp. 89-91.",
        volume="A1",
        part="G",
        label_kind="excerpt",
    )
    host = out["hosts"][0]
    assert val(host, "persons", 0, "name") == "Vorname Nachname"
    assert val(host, "persons", 0, "roles", 0) == "editor"
    assert val(host, "title") == "Haupttitel. Ein Führer durch alles"


def test_a_host_cited_as_title_reference_after_in():
    out = read(
        "Nachname, Vorname. “Ein Aufsatz” in LA2 Autor / Sammelband 1942 [12], "
        "pp. 116-117.",
        volume="A2",
        part="L",
    )
    host = out["hosts"][0]
    assert val(host, "title") == "Autor / Sammelband"
    assert (val(host, "locator"), val(host, "pages")) == ("12", "116-117")
    assert val(host, "imprints", 0, "year") == 1942
    bracketed = read(
        "Nachname, Vorname. “Ein Aufsatz” in LA2 “Ein Titel, ein Untertitel” "
        "[1997], No. 2, p. 25.",
        volume="A2",
        part="L",
    )["hosts"][0]
    assert val(bracketed, "title") == "Ein Titel, ein Untertitel"
    assert val(bracketed, "imprints", 0, "year_bracketed") is True


def test_a_place_in_brackets_is_no_contents_number():
    out = read(
        "“Eine Erzählung” in Eine Zeitung [Ort], pp. 31-40.", volume="A2", part="F"
    )
    assert "locator" not in (out.get("hosts") or [{}])[0]


def test_a_host_title_may_carry_a_bracketed_gloss_before_its_credits():
    out = read(
        "“Eine Erzählung” [Originaltitel] in Sammlung. Untertitel [Deutscher "
        "Titel]. Translated by Vorname Nachname. 429/(3)p. Ort: Verlag, 2004, pp. 5-9.",
        volume="A2",
        part="F",
    )
    host = out["hosts"][0]
    assert val(host, "title") == "Sammlung. Untertitel"
    assert val(host, "imprints", 0, "year") == 2004


def test_an_imprint_stays_when_no_host_can_be_named():
    out = read(
        "[1]. Paperback edition. 400p. Ort: Verlag, 1996, pp. 399-400.",
        volume="A2",
        part="L",
        label_kind="reprint",
    )
    assert "hosts" not in out
    assert val(out, "imprints", 0, "year") == 1996


def test_a_language_heading_at_the_margin_does_not_join_its_first_entry():
    from _segment import consensus

    heading = {
        "text": "KATALANISCH",
        "x0": 67.0,
        "heading": True,
        "runs": [["Bold", 12.0, 67.0, "KATALANISCH", 140.0]],
        "kind": "body",
        "furniture": False,
        "at_margin": True,
    }
    entry = {
        "text": "“Ein Titel” in Eine Sammlung [Ort], 1 May 1910, p. 3.",
        "x0": 103.0,
        "heading": False,
        "previous": heading,
        "numbered_part": True,
        "page_top": False,
        "votes": {"number": False, "indent": False, "gap": True, "bold": False},
        "active": ("number", "indent", "gap", "bold"),
    }
    assert consensus(entry)
    wrapped = {**entry, "text": "1902-1942. See A 170."}
    assert not consensus(wrapped)


def test_a_wrapped_address_list_is_no_heading():
    from _segment import is_heading

    line = {"text": "L 49, 61, 230 / M 31 / O 14 /", "start": None}
    assert not is_heading(line)
    assert is_heading({"text": "KATALANISCH", "start": None})


def test_a_title_with_a_slash_before_an_extent_is_no_second_imprint():
    out = read(
        '12 "Ein Aufsatz" [Tr. Vorname Nachname], Stefan Zweig. Zwei Porträts: Erster '
        "/ Zweiter. 218p. Ort: Verlag, 1955, pp. 7-127.",
        part="G",
    )
    imprints = out["hosts"][0]["imprints"]
    assert [(val(i, "place"), val(i, "publisher")) for i in imprints] == [
        ("Ort", "Verlag")
    ]
    two = read(
        "12 TITEL. 99p. Ort: Verlag Eins / Anderer Ort, N. J.: Verlag Zwei, 1980."
    )
    assert [val(i, "place") for i in two["imprints"]] == ["Ort", "Anderer Ort, N. J."]


def test_a_four_digit_address_stands_where_the_section_runs_that_high():
    out = read("12 TITEL. 99p. Ort: Verlag, 1950. See G 1101 / F 1927.", part="A")
    assert [val(r, "address") for r in out["references"]] == ["G 1101"]


def _head(text):
    """The head object of an entry whose Contents list follows its span."""
    return read(text, part="A", span=(0, text.index(" Contents")))


def test_cross_references_after_a_contents_list_are_the_objects_values():
    text = "12 DER BAND. 251p. 1981. Contents: D 19 / H 45, 167. See A 48 / G 755."
    out = _head(text)
    assert [val(i, "address", "address") for i in out["contents"]] == [
        "D 19",
        "H 45, 167",
    ]
    refs = out["references"]
    assert [val(r, "address") for r in refs] == ["A 48", "G 755"]
    assert {val(r, "kind") for r in refs} == {"see"}
    # Outside the object's span, each value names its own entry.
    assert {r["address"]["from"] for r in refs} == {"I/A/12"}
    assert {r["kind"]["from"] for r in refs} == {"I/A/12"}


def test_a_see_in_a_bracket_of_the_list_neither_ends_it_nor_is_an_item():
    text = "12 DER BAND. 787p. 1985. Contents: G 131 (See G 449) / H 464 / Nachwort."
    out = _head(text)
    items = out["contents"]
    assert [
        val(i, "title") if i.get("title") else val(i, "address", "address")
        for i in items
    ] == ["G 131", "H 464", "Nachwort"]
    assert [val(r, "address") for r in out["references"]] == ["G 449"]


def test_a_titled_item_after_a_slash_keeps_its_pages_and_ends_the_list():
    text = (
        "12 DER BAND. 364p. 1974. Contents: F 2, 7 / Kommentare, pp. 353-364. "
        "ZWEITER BAND. 1990."
    )
    out = _head(text)
    titled = [i for i in out["contents"] if i.get("title")]
    assert [(val(i, "title"), val(i, "pages")) for i in titled] == [
        ("Kommentare", "353-364")
    ]


def test_a_see_inside_a_numbered_items_bracket_does_not_end_the_list():
    text = (
        "Der Band. Ort: Verlag, 1987. Contents: [1]. Episode [Episode am See], "
        "pp. 1-9. [2]. Zweite Geschichte, pp. 10-20."
    )
    out = _head(text)
    assert [val(i, "title") for i in out["contents"]] == [
        "Episode",
        "Zweite Geschichte",
    ]


def test_a_volume_of_a_collection_takes_the_imprint_of_its_period():
    from p03_records import _period_imprint

    def imprint(place, year, end=None):
        out = {"place": {"value": place}, "year": {"value": year}}
        if end:
            out["year_end"] = {"value": end}
        return out

    header = [imprint("Erstort", 1939, 1950), imprint("Zweitort", 1950, 1990)]
    own = [{"year": {"value": 1981}}]
    assert _period_imprint(header, own) == {"place": {"value": "Zweitort"}}
    # A year in two periods, in none, or a header without periods: no choice.
    assert _period_imprint(header, [{"year": {"value": 1950}}]) is None
    assert _period_imprint(header, [{"year": {"value": 1997}}]) is None
    assert _period_imprint([imprint("Ort", 1960)], own) is None


def test_a_year_only_volume_reads_place_and_publisher_from_its_header():
    from _fields import summary

    obj = {
        "imprints": [{"year": {"value": 1981}}],
        "inherited": {
            "imprints": [{"place": {"value": "Ort"}, "publisher": {"value": "Verlag"}}]
        },
    }
    fields = summary(obj)
    assert (fields["year"], fields["place"], fields["publisher"]) == (
        1981,
        "Ort",
        "Verlag",
    )


def test_rule_patterns_hold_no_control_character():
    import _apparatus
    import _fields

    for module in (_fields, _apparatus):
        for name, pattern in vars(module).items():
            if isinstance(pattern, re.Pattern):
                assert "\x08" not in pattern.pattern, name

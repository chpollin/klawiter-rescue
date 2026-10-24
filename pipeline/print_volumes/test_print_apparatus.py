"""Reading rules of the index records (_apparatus.py), each pinned with
invented lines in the shape of the print: four-digit address heads, strips
that run over a page, and headings that are no index entries."""

from _apparatus import apparatus_records
from _schema import ApparatusItem


def _line(page, line, top, *runs, volume="I", part="Index A"):
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


def _items(lines, index, volume="I"):
    records, _ = apparatus_records(lines, volume, index)
    items = [r["objects"][0] for r in records]
    for item in items:
        ApparatusItem.model_validate(item)
    return records, items


def _targets(item):
    return [
        t["normalized"] for ref in item.get("references", []) for t in ref["targets"]
    ]


def test_a_four_digit_head_is_an_address_where_its_entry_exists():
    index = {"G 1082": "I/G/1082", "G 1090": "I/G/1090", "H 12": "I/H/12"}
    _, (named, year) = _items(
        [
            _line(800, 1, 100, (72, "Nachname, Erika, G 1082, 1090 / H 12", 260)),
            _line(800, 2, 114, (72, "Muster, Max, A 1927 / H 12", 230)),
        ],
        index,
    )
    assert named["term"]["value"] == "Nachname, Erika"
    assert _targets(named) == ["G 1082", "G 1090", "H 12"]
    first = named["references"][0]
    assert first["address"]["value"] == "G 1082, 1090"
    # The shared grammar reads it up to the section's 1991 range; the index
    # rule only takes what the grammar still skips.
    assert first["address"]["rule"] in {
        "p06.address-notation",
        "p03.index-long-address",
    }
    assert [t["record"] for t in first["targets"]] == ["I/G/1082", "I/G/1090"]
    # A year after a letter names no entry and stays unread.
    assert _targets(year) == ["H 12"]


def test_the_long_head_rule_is_known_to_the_validator():
    from p10_validate import _known_rules

    assert "p03.index-long-address" in _known_rules()[0]


def test_a_strip_at_the_page_foot_goes_on_over_the_page_without_a_space():
    index = {"K 7": "I/K/7", "L 3": "I/L/3"}
    index.update({f"L {n}": f"I/L/{n}" for n in (1035, 1036, 1037)})
    glyphs = [
        _line(800, k, 100 + 14 * k, (471, g, 477)) for k, g in enumerate("L3,1", 2)
    ]
    records, (item,) = _items(
        [
            _line(800, 1, 114, (291, "Muster, Max, K 7 / ", 380)),
            *glyphs,
            _line(801, 1, 100, (72, "035-1037", 118)),
        ],
        index,
    )
    assert records[0]["text"] == "Muster, Max, K 7 / L3,1035-1037"
    assert _targets(item) == ["K 7", "L 3", "L 1035", "L 1036", "L 1037"]


def test_a_line_that_runs_over_the_page_keeps_its_space():
    records, _ = _items(
        [
            _line(800, 1, 100, (72, "Muster, Max, K 7 /", 170)),
            _line(801, 1, 100, (72, "L 3", 90)),
        ],
        {"K 7": "I/K/7", "L 3": "I/L/3"},
    )
    assert [r["text"] for r in records] == ["Muster, Max, K 7 / L 3"]


def test_index_headings_and_notes_read_neither_term_nor_address():
    index = {"G 12": "I/G/12", "M 36": "I/M/36", "C 3": "I/C/3", "CA1 3": "A1/C/3"}
    _, items = _items(
        [
            _line(800, 1, 100, (72, "INDEX D / INVENTED TITLE", 250)),
            _line(800, 2, 128, (72, "NB: An invented note on the numbers.", 300)),
            _line(800, 3, 156, (72, "Nachname, Erika, G 12", 170)),
            _line(800, 4, 170, (72, "GROUPS", 120)),
            _line(800, 5, 184, (72, "XYZ, M 36", 130)),
        ],
        index,
    )
    heading, note, entry, group, siglum = items
    for item in (heading, note, group):
        assert "term" not in item and "references" not in item
    assert entry["term"]["value"] == "Nachname, Erika"
    # A siglum in capitals with an address stays an entry.
    assert siglum["term"]["value"] == "XYZ"
    assert _targets(siglum) == ["M 36"]

    _, (label, entry) = _items(
        [
            _line(441, 1, 100, (105, "C3 INVENTED GROUP: TOPICS", 290), part="Index B"),
            _line(442, 1, 100, (105, "Begriff: CA1 3", 190), part="Index B"),
        ],
        index,
        volume="A1",
    )
    # The group label reads as no address C 3.
    assert "term" not in label and "references" not in label
    assert _targets(entry) == ["CA1 3"]

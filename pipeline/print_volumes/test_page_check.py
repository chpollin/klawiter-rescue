"""Tests of the page check: the join of lines and records, and its server routes.

Every line and record here is invented and lies in tmp_path; no print text is read.
"""

import http.client
import json
import os
import threading
from functools import partial
from http.server import ThreadingHTTPServer

import pytest
from page_render import Source
from review_server import Handler, Store

ENTRY = "1 FIRST TITLE. Somewhere: Press, 1950. Second line of the entry."
HEADING = "2 HEADING LINE"


def _line(page, line, top, x0, text, defect=False, size=12.0):
    return {
        "volume": "I",
        "page": page,
        "line": line,
        "top": top,
        "bottom": top + 12,
        "x0": x0,
        "x1": x0 + 6 * len(text),
        "text": text,
        "runs": [["Invented", size, x0, text, x0 + 6 * len(text)]],
        "defect": defect,
    }


def _value(text, passage, start_at=0, **extra):
    a = text.index(passage, start_at)
    return {"value": passage, "span": [a, a + len(passage)], "by": "rule", **extra}


def _write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8", newline="\n"
    )


@pytest.fixture
def derived(tmp_path):
    lines = [
        # Page 80 lies in part F of the main volume (sections.json).
        _line(80, 0, 40.0, 300.0, "111"),
        _line(80, 1, 100.0, 72.0, "1 FIRST TITLE. Somewhere: Press, 1950."),
        _line(80, 2, 114.0, 90.0, "   Second line of the entry.", defect=True),
        _line(80, 3, 128.0, 90.0, "Stray words held by nothing."),
        _line(80, 4, 142.0, 72.0, HEADING),
        # Page 800 lies in Index A.
        _line(800, 0, 300.0, 72.0, "Alpha, Ann, F 1"),
        _line(800, 1, 314.0, 72.0, "Beta, Bob, F 2"),
        _line(800, 2, 328.0, 72.0, "Gamma, Gus, F 3"),
    ]
    _write(tmp_path / "lines-I.jsonl", lines)
    title = _value(ENTRY, "FIRST TITLE", rule="p03.title")
    year = _value(ENTRY, "1950", rule="p03.imprint")
    year["value"] = 1950
    across = _value(ENTRY, "1950. Second", rule="p03.note")
    entry = {
        "id": "I/F/1",
        "volume": "I",
        "part": "F",
        "page": 80,
        "line": 1,
        "page_end": 80,
        "address": "F 1",
        "kind": "entry",
        "text": ENTRY,
        "sha256": "0" * 64,
        "context": [],
        "objects": [
            {
                "id": "I/F/1#1",
                "entry": "I/F/1",
                "address": "F 1",
                "span": [0, len(ENTRY)],
                "text": ENTRY,
                "title": title,
                "imprints": [{"year": year}],
                "notes": [{"text": across}],
                "inherited": {
                    "series": [
                        {
                            "title": {
                                "value": HEADING,
                                "span": [0, len(HEADING)],
                                "by": "inherited",
                                "rule": "p03.inherit",
                                "from": "I/F/p80l4",
                            }
                        }
                    ]
                },
                "types": [
                    {
                        "value": "book_edition",
                        "span": [0, len(ENTRY)],
                        "by": "rule",
                        "rule": "p03.types",
                    }
                ],
            }
        ],
    }
    heading = {
        "id": "I/F/p80l4",
        "volume": "I",
        "part": "F",
        "page": 80,
        "line": 4,
        "page_end": 80,
        "address": "",
        "kind": "heading",
        "text": HEADING,
        "sha256": "0" * 64,
        "context": [],
        "objects": [],
    }
    _write(tmp_path / "records" / "entries-I.jsonl", [entry, heading])
    apparatus = []
    for n, text in enumerate(["Alpha, Ann, F 1", "Beta, Bob, F 2"]):
        rid = f"I/index-a/p800l{n}"
        term = text.rsplit(", ", 1)[0]
        apparatus.append(
            {
                "id": rid,
                "volume": "I",
                "part": "Index A",
                "page": 800,
                "line": n,
                "column": 1,
                "page_end": 800,
                "address": "",
                "kind": "index",
                "text": text,
                "sha256": "0" * 64,
                "context": [],
                "lines": [[800, n, 1, 0, len(text)]],
                "objects": [
                    {
                        "id": f"{rid}#1",
                        "entry": rid,
                        "kind": "index",
                        "span": [0, len(text)],
                        "text": text,
                        "term": {**_value(text, term), "rule": "p03.index-term"},
                    }
                ],
            }
        )
    _write(tmp_path / "records" / "apparatus-I.jsonl", apparatus)
    candidate = {
        "claim": "c1",
        "state": "proposed",
        "route": "title-year",
        "page": 5,
        "target": "klawiter:entry/5",
        "method": "title-year",
    }
    concordance = {
        "links": {"I/F/1#1": {"cand": [candidate]}, "I/X/9#1": {"cand": [candidate]}},
        "pages": {"5": {"title": "Invented page"}},
    }
    (tmp_path / "viewer").mkdir()
    (tmp_path / "viewer" / "wiki_concordance.json").write_text(
        json.dumps(concordance), encoding="utf-8"
    )
    return tmp_path


def _source(derived):
    # print_dir holds no PDF, so the page count comes from the lines.
    return Source(derived=derived, print_dir=derived / "no-pdf")


def _slice(page, piece):
    return next(ln for ln in page["lines"] if ln["line"] == piece["line"])["text"][
        piece["start"] : piece["end"]
    ]


def test_roles_and_holders(derived):
    page = _source(derived).assemble("I", 80)
    roles = {ln["line"]: ln["role"] for ln in page["lines"]}
    assert roles == {0: "furniture", 1: "value", 2: "value", 3: "outside", 4: "heading"}
    by_line = {ln["line"]: ln for ln in page["lines"]}
    assert by_line[2]["defect"] and not by_line[1]["defect"]
    assert by_line[3]["records"] == []
    assert [r["id"] for r in page["records"]] == ["I/F/1", "I/F/p80l4"]
    assert page["roles"]["outside"] == 1


def test_values_map_onto_line_offsets(derived):
    page = _source(derived).assemble("I", 80)
    values = {v["path"]: v for v in page["records"][0]["objects"][0]["values"]}
    (title,) = values["title"]["lines"]
    assert (title["line"], _slice(page, title)) == (1, "FIRST TITLE")
    # A passage across two lines falls into one piece per line; the leading
    # spaces of the second line shift its offsets.
    across = values["notes[0].text"]["lines"]
    assert [(p["line"], _slice(page, p)) for p in across] == [
        (1, "1950."),
        (2, "Second"),
    ]
    inherited = values["inherited.series[0].title"]
    assert inherited["inherited"] and inherited["field"] == "series[0].title"
    assert inherited["source"] == "I/F/p80l4"
    assert [(p["line"], _slice(page, p)) for p in inherited["lines"]] == [(4, HEADING)]
    assert values["imprints[0].year"]["value"] == 1950


def test_apparatus_pieces_and_ledger(derived):
    page = _source(derived).assemble("I", 800)
    roles = [ln["role"] for ln in page["lines"]]
    assert roles == ["apparatus", "apparatus", "outside"]
    term = page["records"][1]["objects"][0]["values"][0]
    assert term["path"] == "term"
    assert _slice(page, term["lines"][0]) == "Beta, Bob"
    assert all(r["apparatus"] for r in page["records"])


def test_links_and_image_state(derived):
    source = _source(derived)
    page = source.assemble("I", 80)
    assert set(page["links"]) == {"I/F/1#1"}
    assert page["wikiPages"] == {"5": "Invented page"}
    assert page["size"] is None and page["renderer"]
    assert source.pages("I") == 800 and source.pages("A1") == 0
    with pytest.raises(RuntimeError):
        source.render("I", 80)


def test_find_prefers_exact_matches(derived):
    path = derived / "records" / "entries-I.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    stray = "Stray words held by nothing."
    rows.append(
        {**rows[1], "id": "I/F/10", "address": "F 10", "line": 3, "text": stray}
    )
    _write(path, rows)
    source = _source(derived)
    assert [r["id"] for r in source.find("f 1")] == ["I/F/1"]
    assert {r["id"] for r in source.find("F")} == {"I/F/1", "I/F/10"}
    assert [r["id"] for r in source.find("I/F/1#1")] == ["I/F/1"]
    assert {r["id"] for r in source.find("I/F")} == {"I/F/1", "I/F/10", "I/F/p80l4"}
    assert source.find("nothing") == []


def test_reload_on_change(derived):
    source = _source(derived)
    assert len(source.assemble("I", 80)["records"]) == 2
    path = derived / "records" / "entries-I.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    _write(path, rows[:1])
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 10**9))
    page = source.assemble("I", 80)
    assert [r["id"] for r in page["records"]] == ["I/F/1"]
    assert {ln["line"]: ln["role"] for ln in page["lines"]}[4] == "outside"


def _blind(derived, answer):
    samples = derived / "samples"
    samples.mkdir(exist_ok=True)
    key = {"key": {"s1": {"printId": "I/F/1", "stratum": "field"}}}
    (samples / "concordance-blind-key.json").write_text(
        json.dumps(key), encoding="utf-8"
    )
    sheet = samples / "concordance-blind-sheet.csv"
    sheet.write_text(
        f"sample_id,volume,address,pdf_page,print_text,wiki_page,decision,note\n"
        f"s1,I,F 1,80,,{answer},,\n",
        encoding="utf-8",
    )
    return sheet


def test_open_blind_sheet_withholds_its_pages(derived):
    sheet = _blind(derived, "")
    source = _source(derived)
    page = source.assemble("I", 80)
    assert "blind sample in concordance-blind-sheet.csv" in page["withheld"]
    assert page["records"] == [] and page["links"] == {} and page["wikiPages"] == {}
    assert page["lines"] == [] and page["roles"] == {}
    # A page without a sampled entry keeps its readings.
    assert source.assemble("I", 800)["withheld"] is None
    # Answered, the sheet no longer withholds.
    sheet.write_text(sheet.read_text(encoding="utf-8").replace(",80,,,", ",80,,5,"))
    stat = sheet.stat()
    os.utime(sheet, ns=(stat.st_atime_ns, stat.st_mtime_ns + 10**9))
    page = source.assemble("I", 80)
    assert page["withheld"] is None and len(page["records"]) == 2


@pytest.fixture
def server(derived, monkeypatch):
    httpd = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(Handler, directory=str(derived))
    )
    port = httpd.server_address[1]
    monkeypatch.setattr(Handler, "store", Store(), raising=False)
    monkeypatch.setattr(Handler, "pages", _source(derived), raising=False)
    monkeypatch.setattr(Handler, "port", port, raising=False)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield port
    httpd.shutdown()
    httpd.server_close()


def _request(port, path, method="GET", host=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    conn.request(method, path, headers={"Host": host or f"127.0.0.1:{port}"})
    response = conn.getresponse()
    raw = response.read()
    conn.close()
    body = (
        json.loads(raw)
        if raw and "json" in (response.getheader("Content-Type") or "")
        else raw
    )
    return response.status, body


def test_page_route(server):
    status, body = _request(server, "/check/page/I/80.json")
    assert status == 200
    assert body["page"] == 80 and len(body["lines"]) == 5


@pytest.mark.parametrize(
    "path, expected",
    [
        ("/check/page/I/801.json", 404),
        ("/check/page/Q/1.json", 404),
        ("/check/page/I/0.json", 400),
        ("/check/page/I/80.json?x=1", 400),
        ("/check/page/I/%38%30.json", 400),
        ("/check/page/I/../80.json", 400),
        ("/check/page/I/80.txt", 400),
        ("/check/page/i/80.json", 400),
        ("/check/page/I/80.png", 503),
        ("/check/other", 400),
    ],
)
def test_page_route_refuses(server, path, expected):
    status, body = _request(server, path)
    assert status == expected
    assert "error" in body


def test_foreign_host_and_head(server):
    status, _ = _request(server, "/check/page/I/80.json", host="evil.example:80")
    assert status == 403
    status, _ = _request(server, "/check/find.json?q=F%201", host="evil.example:80")
    assert status == 403
    status, _ = _request(server, "/check/page/I/80.json", method="HEAD")
    assert status == 405
    status, _ = _request(
        server, "/check/page/I/80.json", method="HEAD", host="evil.example:80"
    )
    assert status == 403


def test_find_route(server):
    status, body = _request(server, "/check/find.json?q=F%201")
    assert status == 200 and [r["id"] for r in body] == ["I/F/1"]
    assert body[0]["page"] == 80 and body[0]["volume"] == "I"
    for path in (
        "/check/find.json",
        "/check/find.json?q=",
        "/check/find.json?q=a&q=b",
        "/check/find.json?q=a&x=1",
        "/check/find.json?q=" + "a" * 65,
    ):
        assert _request(server, path)[0] == 400, path

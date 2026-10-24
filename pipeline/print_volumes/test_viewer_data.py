"""Viewer data on invented records: claim states, the index snippet and the server's paths."""

import http.client
import threading
from functools import partial
from http.server import ThreadingHTTPServer

import pytest
import review_server
from _viewer_data import SNIPPET_MAX, object_meta, project, snippet


def claim(cid, subject, predicate, target, record="X/A/1", sha="h1", **evidence):
    return {
        "id": cid,
        "subject": subject,
        "predicate": predicate,
        "object": target,
        "evidence": {"print": {"record": record, "sha256": sha}, **evidence},
        "producer": {"class": "editorial", "method": "rule", "rule": "p07.x"},
        "state": "proposed",
    }


def value(text, a, b, **extra):
    return {"value": text[a:b], "span": [a, b], "by": "rule", "rule": "t", **extra}


RECORDS = [
    {
        "id": "X/A/1",
        "sha256": "h1",
        "kind": "entry",
        "objects": [
            {
                "id": "X/A/1#1",
                "address": "A 1",
                "imprints": [{"year": {"value": 1950}}],
            }
        ],
    },
    {
        "id": "X/A/2",
        "sha256": "new",
        "kind": "entry",
        "objects": [
            {
                "id": "X/A/2#1",
                "address": "",
                "types": [{"value": "collection"}],
            }
        ],
    },
]
PUBS = {
    "klawiter:publication/7-1950-a": {
        "id": "klawiter:publication/7-1950-a",
        "year": 1950,
    },
    "klawiter:publication/8-1949-a": {
        "id": "klawiter:publication/8-1949-a",
        "year": 1949,
    },
}
PAGES = {7: {"title": "Seven"}, 8: {"title": "Eight"}, 9: {"title": "Nine"}}


def build(claims, cases=()):
    meta, hashes = object_meta(RECORDS)
    return project(claims, cases, meta, hashes, PAGES, PUBS)


def all_strings(node):
    if isinstance(node, dict):
        for k, v in node.items():
            yield k
            yield from all_strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from all_strings(v)
    elif isinstance(node, str):
        yield node


def test_proposed_claims_stay_proposed_with_route_and_claim_id():
    out = build(
        [
            claim("c1", "X/A/1", "textAlignedWith", "klawiter:entry/9", score=0.93),
            claim(
                "c2",
                "X/A/1#1",
                "samePublicationAs",
                "klawiter:publication/7-1950-a",
                wiki_page=7,
                second_field=["fischer"],
            ),
            claim("c3", "X/A/1#1", "candidateFor", "klawiter:entry/8", wiki_page=8),
        ]
    )
    links = out["links"]
    assert links["X/A/1"]["align"][0] == {
        "claim": "c1",
        "state": "proposed",
        "route": "alignment",
        "page": 9,
        "score": 0.93,
        "firstSeen": None,
        "method": "shingle-alignment",
    }
    same, cand = links["X/A/1#1"]["same"][0], links["X/A/1#1"]["cand"][0]
    assert (same["claim"], same["state"], same["route"]) == (
        "c2",
        "proposed",
        "field-match",
    )
    assert (cand["claim"], cand["state"], cand["route"]) == (
        "c3",
        "proposed",
        "title-year",
    )
    strings = set(all_strings(out))
    assert not strings & {"matched", "confirmed"}
    assert out["wikiOnlyPages"] == []


def test_field_conflict_stays_a_conflict_with_its_fields():
    case = {
        "print": "X/A/1#1",
        "wiki": "klawiter:publication/7-1950-a",
        "layer": "publication",
        "differ": ["extent"],
        "printFields": {"title": "T"},
        "wikiFields": {"title": "T", "extent": [12]},
    }
    diff = build([], [case])["links"]["X/A/1#1"]["diff"]
    assert diff["state"] == "conflict"
    assert diff["differ"] == ["extent"]
    assert diff["wikiFields"] == {"title": "T", "extent": [12]}
    assert diff["page"] == 7


def test_collection_heading_skipped_stale_claim_marked_and_lists_capped():
    claims = [
        claim("s", "X/A/2#1", "candidateFor", "klawiter:entry/8", record="X/A/2"),
        claim("old", "X/A/1", "textAlignedWith", "klawiter:entry/9", sha="h0"),
        claim("p8", "X/A/1#1", "samePublicationAs", "klawiter:publication/8-1949-a"),
    ] + [
        claim(f"k{i}", "X/A/1#1", "candidateFor", f"klawiter:entry/{i}")
        for i in range(5)
    ]
    claims.append(
        claim("p7", "X/A/1#1", "samePublicationAs", "klawiter:publication/7-1950-a")
    )
    out = build(claims)
    assert "X/A/2#1" not in out["links"]
    assert out["counts"]["claims_skipped_collection"] == 1
    assert out["links"]["X/A/1"]["align"][0]["stale"] is True
    info = out["links"]["X/A/1#1"]
    # The publication of the object's own year ranks first.
    assert [x["claim"] for x in info["same"]] == ["p7", "p8"]
    assert [x["claim"] for x in info["cand"]] == ["k0", "k1", "k2"]
    assert info["totals"] == {"cand": 5}
    assert out["pubs"].keys() == PUBS.keys()


TEXT = (
    "2 Der Amokläufer. Erzählungen. Ed./Aftw. Knut Beck. (1.-3. Tsd.). 202/(2)p. 1984."
)


def edition(**over):
    obj = {
        "id": "X/A/3#1",
        "span": [0, len(TEXT)],
        "text": TEXT,
        "title": value(TEXT, 2, 16),
        "subtitle": value(TEXT, 18, 29),
        "persons": [
            {
                "name": value(TEXT, 41, 50),
                "roles": [
                    value(TEXT, 31, 34) | {"value": "editor"},
                    value(TEXT, 35, 40) | {"value": "afterword"},
                ],
            }
        ],
        "extent": {"raw": value(TEXT, 66, 75)},
        "imprints": [{"year": value(TEXT, 76, 80) | {"value": 1984}}],
    }
    obj.update(over)
    return obj


def test_snippet_quotes_the_disambiguating_values_in_printed_order():
    assert (
        snippet(edition(), True) == "Erzählungen. Ed./Aftw. Knut Beck · 202/(2)p. 1984"
    )


def test_snippet_leaves_out_passages_from_other_records():
    inherited = value(TEXT, 41, 50, **{"from": "X/A/0"})
    obj = edition(persons=[{"name": inherited}], imprints=[], extent={})
    assert snippet(obj, True) == "Erzählungen"


def test_snippet_without_values_is_the_text_after_the_title():
    obj = edition(subtitle=None, persons=[], extent={}, imprints=[])
    assert (
        snippet(obj, True)
        == "Erzählungen. Ed./Aftw. Knut Beck. (1.-3. Tsd.). 202/(2)p. 1984."
    )


def test_snippet_of_an_untitled_object_is_its_text_start_cut_at_a_word():
    text = "Brief an einen Freund " * 20
    out = snippet({"id": "o", "span": [500, 500 + len(text)], "text": text}, False)
    assert out.startswith("Brief an einen Freund Brief")
    assert len(out) <= SNIPPET_MAX and out.endswith("…")
    assert out[:-1] in text


@pytest.mark.parametrize(
    "path",
    [
        "/viewer/../x",
        "/viewer/%2e%2e/x",
        "/viewer/./a.js",
        "/viewer/..%5cx",
        "/viewer/a\\b",
    ],
)
def test_route_refuses_dot_segments_and_backslashes(path):
    assert review_server.route(path) is None


@pytest.fixture
def folders(tmp_path, monkeypatch):
    code, data, derived = (
        tmp_path / "code",
        tmp_path / "derived" / "viewer",
        tmp_path / "derived",
    )
    code.mkdir()
    data.mkdir(parents=True)
    (code / "cards.js").write_text("code", encoding="utf-8")
    (data / "cards.js").write_text("stale copy", encoding="utf-8")
    (code / "index.json").write_text("stray", encoding="utf-8")
    (data / "index.json").write_text("[]", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("outside", encoding="utf-8")
    monkeypatch.setattr(review_server, "VIEWER_CODE", code)
    monkeypatch.setattr(review_server, "VIEWER_DATA", data)
    return code, data, derived


def test_viewer_file_prefers_code_and_takes_data_from_derived(folders):
    code, data, _ = folders
    assert review_server.viewer_file("cards.js") == (code / "cards.js").resolve()
    assert review_server.viewer_file("index.json") == (data / "index.json").resolve()
    assert review_server.viewer_file("../../secret.txt") is None
    assert review_server.viewer_file(str(folders[0].parent / "secret.txt")) is None
    assert review_server.viewer_file("missing.js") is None


def test_server_serves_code_and_data_and_refuses_the_rest(folders, monkeypatch):
    _, _, derived = folders
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(review_server.Handler, directory=str(derived))
    )
    port = server.server_address[1]
    monkeypatch.setattr(review_server.Handler, "port", port, raising=False)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def get(path, host=f"127.0.0.1:{port}"):
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.putrequest("GET", path, skip_host=True)
        conn.putheader("Host", host)
        conn.endheaders()
        resp = conn.getresponse()
        body = resp.read().decode("utf-8", "replace")
        conn.close()
        return resp.status, body, resp.getheader("Cache-Control")

    try:
        assert get("/viewer/cards.js")[:2] == (200, "code")
        assert get("/viewer/cards.js")[2] == "no-cache"
        assert get("/viewer/index.json?v=1")[:2] == (200, "[]")
        assert get("/viewer/../secret.txt")[0] == 404
        assert get("/viewer/%2e%2e/%2e%2e/secret.txt")[0] == 404
        assert get("/../secret.txt")[0] == 404
        assert get("/viewer/cards.js", host="evil.example:80")[0] == 403
        assert get("/print/../x.pdf")[0] == 404
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.parametrize(
    ("header", "span"),
    [
        ("bytes=0-99", (0, 99)),
        ("bytes=900-", (900, 999)),
        ("bytes=-100", (900, 999)),
        ("bytes=990-5000", (990, 999)),
        ("bytes=1000-", None),
        ("bytes=50-10", None),
        ("bytes=0-1,5-9", None),
        ("items=0-1", None),
        ("bytes=-0", None),
    ],
)
def test_byte_range_reads_one_satisfiable_range(header, span):
    assert review_server.byte_range(header, 1000) == span

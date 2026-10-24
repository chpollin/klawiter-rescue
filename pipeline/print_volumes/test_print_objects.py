"""Tests of the structured print objects: rules, schema, invariants, LLM offsets and review.

The print data are local (data/print is gitignored), so the test over all
records skips where they are absent; it is a local gate, run with
`python -m uv run pytest pipeline/print_volumes` and outside the default
testpaths. The other tests use invented entries, never print text.
"""

import hashlib
import json

import pytest
from _common import HERE
from _fields import Reader, derive_types
from _llm import merge, verify
from _review import Correction, DecisionIn, ValueRef, check, effective, load_log, stamp
from _schema import apparatus_json_schema, json_schema, object_values
from p10_validate import RECORDS, _known_rules, check_object, validate
from p12_jsonld import (
    CONTEXT_FILE,
    Exporter,
    file_nodes,
    plan_nodes,
    record_node,
    validate_chunk,
)
from pydantic import ValidationError

TEXT = "12 Der Weg. Ein Versuch. Trl./Aftw. Anna Muster. 120/(3)p. Wien: Beispiel Verlag, (1950) [AB]."


def _record(text: str = TEXT, part: str = "F") -> dict:
    return {
        "id": f"I/{part}/12",
        "volume": "I",
        "part": part,
        "page": 1,
        "page_end": 1,
        "address": f"{part} 12",
        "kind": "entry",
        "text": text,
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "objects": [],
    }


def _object(record: dict) -> dict:
    span = (0, len(record["text"]))
    fields = Reader(record, span, {"index": {}}).run()
    obj = {
        "id": record["id"] + "#1",
        "entry": record["id"],
        "entry_sha256": record["sha256"],
        "volume": record["volume"],
        "part": record["part"],
        "address": record["address"],
        "span": list(span),
        "text": record["text"],
        **fields,
    }
    obj["types"] = [
        {"value": t, "span": list(span), "by": "rule", "rule": f"p03.type-{t}"}
        for t in derive_types(obj, record)
    ]
    return obj


def _check(obj: dict, record: dict) -> list[tuple[str, str]]:
    texts = {record["id"]: record["text"]}
    return check_object(
        obj, record, texts, {record["id"]: record}, {record["id"]: 0}, _known_rules()
    )


def test_reader_reads_the_fields_of_an_edition():
    record = _record()
    obj = _object(record)
    assert obj["title"]["value"] == "Der Weg"
    assert obj["subtitle"]["value"] == "Ein Versuch"
    person = obj["persons"][0]
    assert person["name"]["value"] == "Anna Muster"
    assert [r["value"] for r in person["roles"]] == ["translator", "afterword"]
    imprint = obj["imprints"][0]
    assert (
        imprint["place"]["value"],
        imprint["publisher"]["value"],
        imprint["year"]["value"],
    ) == (
        "Wien",
        "Beispiel Verlag",
        1950,
    )
    assert imprint["year_bracketed"]["value"] is True
    assert [p["kind"] for p in obj["extent"]["parts"]] == ["counted", "uncounted"]
    assert obj["informants"][0]["value"] == "AB"
    assert [t["value"] for t in obj["types"]] == ["book_edition", "translation"]
    assert _check(obj, record) == []


@pytest.mark.parametrize(
    "break_it, invariant",
    [
        (lambda o: o["title"].update(value="Der Wag"), "verbatim"),
        (lambda o: o["title"].update(span=[0, 10_000]), "span"),
        (lambda o: o["imprints"][0]["year"].update(value=1951), "verbatim"),
        (lambda o: o["persons"][0]["roles"][0].update(value="editor"), "verbatim"),
        (lambda o: o["title"].update(by="inherited", **{"from": "I/F/12"}), "scope"),
        (lambda o: o["types"].pop(), "types"),
        (lambda o: o["title"].update(rule="p03.no-such-rule"), "rule"),
        (lambda o: o["imprints"][0]["year"].update(value=1300), "schema"),
    ],
)
def test_validator_fails_on_a_rule_break(break_it, invariant):
    record = _record()
    obj = _object(record)
    break_it(obj)
    found = {kind for kind, _ in _check(obj, record)}
    assert invariant in found


def test_llm_offsets_are_checked_verbatim_and_fill_gaps_only():
    record = _record()
    obj = _object(record)
    start = TEXT.index("Anna Muster")
    response = {
        "title": [3, 10],
        "year": [TEXT.index("1950"), TEXT.index("1950") + 4],
        "publisher": [5, 900],
        "persons": [
            {
                "name": [start, start + 11],
                "role": [TEXT.index("Trl."), TEXT.index("Trl.") + 4],
            }
        ],
    }
    proposed, rejected = verify(obj, response)
    assert proposed["title"]["value"] == TEXT[3:10]
    assert proposed["title"]["by"] == "llm" and proposed["title"]["state"] == "proposed"
    assert proposed["year"]["value"] == 1950
    assert "publisher: offsets outside the object" in rejected
    assert proposed["persons"][0]["roles"][0]["value"] == "translator"
    bad, problems = verify(
        obj, {"year": [3, 7], "persons": [{"name": [3, 6], "role": [3, 6]}]}
    )
    assert "year" not in bad and "persons" not in bad and len(problems) == 2
    before = obj["title"]
    merge(obj, proposed)
    assert obj["title"] is before


def test_exported_schema_is_current():
    path = HERE / "schema" / "print-object.schema.json"
    assert json.loads(path.read_text(encoding="utf-8")) == json_schema()
    path = HERE / "schema" / "print-apparatus.schema.json"
    assert json.loads(path.read_text(encoding="utf-8")) == apparatus_json_schema()


@pytest.mark.skipif(
    not (RECORDS / "entries-I.jsonl").exists(), reason="print records are local"
)
def test_every_object_holds_the_invariants():
    report, _, new, stale = validate()
    assert report["objects"] > 0
    assert not new, f"violations outside known_exceptions.json: {new[:10]}"
    assert not stale, f"exceptions that no longer fail: {stale[:10]}"


def _jsonld(obj: dict, record: dict) -> dict:
    record = {**record, "line": 1, "context": [], "objects": [obj]}
    exporter = Exporter({record["id"]: record})
    node = exporter.obj(obj)
    context = json.loads(CONTEXT_FILE.read_text(encoding="utf-8"))["@context"]
    graph = file_nodes() + plan_nodes(exporter.plans, {}) + [record_node(record), node]
    return {"@context": context, "@graph": graph}, exporter.values


def _validated(doc: dict, values: int, tmp_path) -> list[str]:
    path = tmp_path / "chunk.jsonld"
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return validate_chunk((str(path), 1, values, True))["problems"]


def test_jsonld_export_validates_and_catches_a_broken_chain(tmp_path):
    record = _record()
    obj = _object(record)
    doc, values = _jsonld(obj, record)
    assert _validated(doc, values, tmp_path) == []
    title = next(n for n in doc["@graph"] if n.get("type") == "kp:PrintObject")["title"]
    title["selector"]["exact"] = "Der Wag"
    assert any("SHACL" in p for p in _validated(doc, values, tmp_path))
    doc["@graph"][-1]["undefined_term"] = 1
    assert any("undefined terms" in p for p in _validated(doc, values, tmp_path))


def test_an_index_entry_exports_and_validates_with_its_chain(tmp_path):
    from _apparatus import apparatus_records
    from _schema import ApparatusItem

    text = "Nachname, Erika, F 12"
    line = {
        "volume": "I",
        "part": "Index A",
        "kind": "index",
        "page": 800,
        "line": 1,
        "top": 100,
        "x0": 72,
        "text": text,
        "runs": [["Times", 12.0, 72, text, 170]],
    }
    (record,), _ = apparatus_records([line], "I", {"F 12": "I/F/12"})
    item = record["objects"][0]
    ApparatusItem.model_validate(item)
    doc, values = _jsonld(item, record)
    assert values == 3  # term, address, reference kind
    assert _validated(doc, values, tmp_path) == []
    node = next(n for n in doc["@graph"] if n.get("type") == "kp:ApparatusItem")
    node["term"]["selector"]["exact"] = "Nachnahme, Erika"
    assert any("SHACL" in p for p in _validated(doc, values, tmp_path))


def test_export_fields_are_the_paths_review_decisions_use():
    # Decisions are keyed by path; p12 must name every value's field alike.
    record = _record()
    obj = _object(record)
    obj["hosts"] = [{"title": obj["title"], "persons": obj.get("persons", [])}]
    exporter = Exporter(
        {record["id"]: {**record, "line": 1, "context": [], "objects": [obj]}}
    )
    node = exporter.obj(obj)
    fields = [v["field"] for v in _value_nodes(node)]
    assert fields == [path for path, _ in object_values(obj)]


def _value_nodes(node):
    if isinstance(node, dict):
        if "kp:Value" in node.get("type", []):
            yield node
            return
        for child in node.values():
            yield from _value_nodes(child)
    elif isinstance(node, list):
        for child in node:
            yield from _value_nodes(child)


def _reviewed():
    record = _record()
    obj = _object(record)
    title = obj["title"]
    target = ValueRef(
        path="title", value=title["value"], span=title["span"], source=record["id"]
    )
    base = {
        "object": obj["id"],
        "entry_sha256": record["sha256"],
        "reviewer": "reviewer 1",
    }
    return record, obj, {record["id"]: {**record, "objects": [obj]}}, target, base


def test_review_decisions_apply_only_to_the_value_they_judged():
    record, obj, records, target, base = _reviewed()
    assert check(DecisionIn(**base, decision="confirm", target=target), records) is None
    changed = target.model_copy(update={"value": "Der Wag"})
    assert check(
        DecisionIn(**base, decision="confirm", target=changed), records
    ).startswith("stale")
    at = record["text"].index("Ein Versuch")
    span = [at, at + len("Ein Versuch")]
    right = Correction(value="Ein Versuch", span=span)
    assert (
        check(
            DecisionIn(**base, decision="correct", target=target, correction=right),
            records,
        )
        is None
    )
    wrong = Correction(value="Ein Versuc", span=span)
    assert check(
        DecisionIn(**base, decision="correct", target=target, correction=wrong), records
    )
    for bad in (
        {"decision": "confirm"},
        {"decision": "boundary"},
        {"decision": "complete", "target": target},
        {"decision": "missing", "correction": Correction(field="title")},
    ):
        with pytest.raises(ValidationError):
            DecisionIn(**base, **bad)
    with pytest.raises(ValidationError):
        Correction(value="Ein Versuch")


def _correct(base, records, path, value, span, **correction):
    current = dict(object_values(next(iter(records.values()))["objects"][0]))[path]
    target = ValueRef(
        path=path,
        value=current["value"],
        span=current["span"],
        source=current.get("from") or base["object"].split("#")[0],
    )
    decision = DecisionIn(
        **base,
        decision="correct",
        target=target,
        correction=Correction(value=value, span=span, **correction),
    )
    return check(decision, records)


def test_a_flag_is_corrected_as_the_boolean_true():
    record, _, records, _, base = _reviewed()
    at = record["text"].index("(1950)")
    span = [at, at + len("(1950)")]
    path = "imprints[0].year_bracketed"
    assert _correct(base, records, path, True, span) is None
    # The viewer once sent the flag as text; a false flag is a removal instead.
    assert "type" in _correct(base, records, path, "true", span)
    assert _correct(base, records, path, False, span)
    assert _correct(base, records, path, None, None) is None


def test_a_correction_keeps_its_value_type_and_field():
    record, _, records, _, base = _reviewed()
    at = record["text"].index("1950")
    span = [at, at + 4]
    assert _correct(base, records, "imprints[0].year", 1950, span) is None
    assert "type" in _correct(base, records, "imprints[0].year", "1950", span)
    at = record["text"].index("Ein Versuch")
    span = [at, at + len("Ein Versuch")]
    assert "field" in _correct(
        base, records, "title", "Ein Versuch", span, field="subtitle"
    )


def test_an_inherited_value_can_only_be_marked_as_one_that_should_not_exist():
    record, obj, records, _, base = _reviewed()
    header_text = "Wien: Kopf Verlag."
    header = {
        **_record(header_text),
        "id": "I/F/1",
        "address": "F 1",
    }
    obj["inherited"] = {
        "imprints": [
            {
                "place": {
                    "value": "Wien",
                    "span": [0, 4],
                    "by": "inherited",
                    "rule": "p03.inherit-imprint",
                    "from": header["id"],
                }
            }
        ]
    }
    records = {**records, header["id"]: header}
    path = "inherited.imprints[0].place"
    at = record["text"].index("Wien")
    assert "inherited" in _correct(base, records, path, "Wien", [at, at + 4])
    assert _correct(base, records, path, None, None) is None


def test_review_decisions_supersede_and_withdraw():
    _, _, _, target, base = _reviewed()
    first = stamp(DecisionIn(**base, decision="confirm", target=target))
    second = stamp(DecisionIn(**base, decision="unresolved", target=target))
    assert [d.id for d in effective([first, second]).values()] == [second.id]
    withdraw = stamp(DecisionIn(**base, decision="withdraw", supersedes=second.id))
    assert effective([first, second, withdraw]) == {}


def test_reviewed_value_exports_with_its_decision(tmp_path):
    record, obj, _, target, base = _reviewed()
    at = record["text"].index("Ein Versuch")
    decision = stamp(
        DecisionIn(
            **base,
            decision="correct",
            target=target,
            correction=Correction(value="Ein Versuch", span=[at, at + 11]),
        )
    )
    full = {**record, "line": 1, "context": [], "objects": [obj]}
    exporter = Exporter(
        {record["id"]: full}, {obj["id"]: [((obj["id"], "value", "title"), decision)]}
    )
    node = exporter.obj(obj)
    # A correction confirms the corrected value; the rule's value stays as
    # its predecessor and the action tells the two apart.
    assert node["title"]["reviewState"] == "confirmed"
    assert node["title"]["reviewAction"] == "correct"
    context = json.loads(CONTEXT_FILE.read_text(encoding="utf-8"))["@context"]
    graph = (
        file_nodes()
        + plan_nodes(exporter.plans, {})
        + [record_node(full), node]
        + exporter.decision_nodes()
    )
    doc = {"@context": context, "@graph": graph}
    assert _validated(doc, exporter.values, tmp_path) == []
    # No fourth state: "corrected" is no statement state.
    node["title"]["reviewState"] = "corrected"
    assert any("SHACL" in p for p in _validated(doc, exporter.values, tmp_path))
    node["title"]["reviewState"] = "confirmed"
    review = next(n for n in graph if n.get("id") == f"review/{decision.id}")
    review["correction"]["selector"]["exact"] = "Ein Versuh"
    assert any("SHACL" in p for p in _validated(doc, exporter.values, tmp_path))


def test_review_server_records_checked_decisions_only(tmp_path, monkeypatch):
    import http.client
    import threading
    from functools import partial
    from http.server import ThreadingHTTPServer

    import _review
    import review_server

    _, _, records, target, base = _reviewed()
    monkeypatch.setattr(_review, "REVIEW_DIR", tmp_path)
    monkeypatch.setattr(_review, "LOG", tmp_path / "decisions.jsonl")
    store = review_server.Store()
    monkeypatch.setattr(store, "current", lambda: records)
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(review_server.Handler, directory=str(tmp_path))
    )
    port = server.server_address[1]
    monkeypatch.setattr(review_server.Handler, "store", store, raising=False)
    monkeypatch.setattr(review_server.Handler, "port", port, raising=False)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    def post(body: dict, host: str = f"127.0.0.1:{port}") -> int:
        conn = http.client.HTTPConnection("127.0.0.1", port)
        data = json.dumps(body).encode("utf-8")
        conn.request(
            "POST",
            "/review/decisions",
            data,
            {"Host": host, "Content-Type": "application/json"},
        )
        status = conn.getresponse().status
        conn.close()
        return status

    good = {**base, "decision": "confirm", "target": target.model_dump()}
    try:
        assert post(good) == 201
        assert post(good, host="evil.example:80") == 403
        assert post({**base, "decision": "confirm"}) == 400
        stale = {**good, "target": {**good["target"], "value": "Der Wag"}}
        assert post(stale) == 409
    finally:
        server.shutdown()
    logged = load_log()
    assert len(logged) == 1 and logged[0].decision == "confirm"

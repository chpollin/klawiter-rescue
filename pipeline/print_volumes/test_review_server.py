"""Tests of the review server's contract with the viewer, on an invented log and no print data."""

import http.client
import json
import threading
from functools import partial
from http.server import ThreadingHTTPServer

import _review
import pytest
import review_server
from _review import Correction, DecisionIn, ValueRef, stamp
from review_server import Handler, Store, log_problem

SHA = "a" * 64


def _decision(reviewer, decision="confirm", **extra):
    target = (
        ValueRef(path="title", value="Der Weg", span=[0, 7], source="I/F/1")
        if decision in ("confirm", "correct", "unresolved", "adjudicate")
        else None
    )
    return stamp(
        DecisionIn(
            object="I/F/1#1",
            entry_sha256=SHA,
            reviewer=reviewer,
            decision=decision,
            target=target,
            **({"correction": Correction()} if decision == "correct" else {}),
            **extra,
        )
    )


@pytest.fixture
def server(tmp_path, monkeypatch):
    log = tmp_path / "decisions.jsonl"
    monkeypatch.setattr(_review, "LOG", log)
    monkeypatch.setattr(_review, "REVIEW_DIR", tmp_path)
    httpd = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(Handler, directory=str(tmp_path))
    )
    monkeypatch.setattr(Handler, "store", Store(), raising=False)
    monkeypatch.setattr(Handler, "port", httpd.server_address[1], raising=False)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield log, httpd.server_address[1]
    httpd.shutdown()
    httpd.server_close()


def _get(port, path):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    conn.request("GET", path, headers={"Host": f"127.0.0.1:{port}"})
    response = conn.getresponse()
    body = json.loads(response.read() or b"null")
    conn.close()
    return response.status, body


def test_decisions_filter_by_reviewer(server):
    log, port = server
    decisions = [_decision("A"), _decision("B"), _decision("A", "unresolved")]
    for d in decisions:
        _review.append(d)
    status, body = _get(port, "/review/decisions?reviewer=A")
    assert status == 200 and [d["id"] for d in body] == [
        decisions[0].id,
        decisions[2].id,
    ]
    status, body = _get(port, "/review/decisions")
    assert status == 200 and len(body) == 3
    assert _get(port, "/review/decisions?reviewer=Nobody") == (200, [])
    assert _get(port, "/review/decisions?reviewer=")[0] == 400
    assert _get(port, "/review/decisions?who=A")[0] == 400
    assert _get(port, "/review/decisions?reviewer=A&reviewer=B")[0] == 400


def test_status_says_why_the_log_cannot_be_read(server):
    log, port = server
    assert _get(port, "/review/status") == (200, {"recording": True})
    log.write_text("not a decision\n", encoding="utf-8")
    status, body = _get(port, "/review/status")
    assert (
        status == 200
        and body["recording"] is False
        and "decisions.jsonl:1" in body["error"]
    )
    assert _get(port, "/review/decisions")[0] == 503


def test_the_log_refuses_foreign_withdrawals_and_empty_adjudications():
    a = _decision("A")
    b = _decision("B", "correct")
    foreign = DecisionIn(
        object="I/F/1#1",
        entry_sha256=SHA,
        reviewer="B",
        decision="withdraw",
        supersedes=a.id,
    )
    assert (
        log_problem(foreign, [a, b]) == "a reviewer withdraws only their own decisions"
    )
    ghost = DecisionIn(
        object="I/F/1#1",
        entry_sha256=SHA,
        reviewer="B",
        decision="withdraw",
        supersedes="0" * 32,
    )
    assert log_problem(ghost, [a]) == "supersedes an unknown decision"
    settle = _decision("C", "adjudicate", settles=[a.id, b.id], adopts=b.id)
    assert log_problem(settle, [a, b]) is None
    by_party = _decision("A", "adjudicate", settles=[a.id, b.id], adopts=b.id)
    assert "neither" in log_problem(by_party, [a, b])


def test_the_server_module_names_the_contract():
    doc = review_server.__doc__
    assert "?reviewer=<name>" in doc and '"recording": false' in doc

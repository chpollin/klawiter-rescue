"""Local review server: serves the viewer with the print data and records review decisions.

The viewer is static, but a decision must reach a file the pipeline reads, and
it must not be lost in a browser store. This server serves data/print/derived/
as a static site and accepts decisions, which it validates with the strict
models of _review.py, checks against the current records, stamps with
identifier and time, and appends to data/print/review/decisions.jsonl. It
accepts data-cleaning questions in the same way (_questions.py), appended to
data/print/review/questions.jsonl.

Trust boundary: the browser. The server binds to 127.0.0.1 only, refuses a
Host or Origin other than its own (against DNS rebinding and cross-site
posts), accepts JSON bodies up to MAX_BODY bytes, and never takes identifier,
time or a value's current state from the request.

Endpoints:
- GET /review/status: {"recording": true}; the viewer offers decisions only
  when this answers.
- GET /review/decisions: every logged decision, in order.
- POST /review/decisions: one decision; 201 with the stored decision, 400 for a
  malformed one, 409 when it does not apply to the current records (a changed
  value, a correction that does not follow from its passage), 403 for a
  foreign Host or Origin.
- GET /review/questions: the current state of every question (_questions.fold).
- POST /review/questions: one question event, always by a person; 201, 400,
  409 (an unknown question or object), 403 as for decisions.

Usage: python -m uv run python pipeline/print_volumes/review_server.py [--port 8765]
"""

import argparse
import json
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import _questions
import _review
from _common import DERIVED_DIR
from _questions import QuestionIn
from _review import DecisionIn, append, check, load_log, load_records, stamp
from pydantic import ValidationError

RECORDS = DERIVED_DIR / "records"
MAX_BODY = 64 * 1024


class Store:
    """The current records, reloaded when p03 has rewritten them."""

    def __init__(self):
        self.lock = threading.Lock()
        self.stamp = None
        self.records: dict[str, dict] = {}
        self.ids: set[str] = set()

    def current(self) -> dict[str, dict]:
        mtimes = tuple(p.stat().st_mtime_ns for p in sorted(RECORDS.glob("*.jsonl")))
        if mtimes != self.stamp:
            self.records = load_records(RECORDS)
            self.ids = _questions.object_ids(RECORDS)
            self.stamp = mtimes
        return self.records


class Handler(SimpleHTTPRequestHandler):
    store: Store
    port: int

    def _own(self) -> bool:
        hosts = {f"127.0.0.1:{self.port}", f"localhost:{self.port}"}
        origin = self.headers.get("Origin")
        return self.headers.get("Host") in hosts and (
            origin is None or origin in {f"http://{h}" for h in hosts}
        )

    def _json(self, status: int, body) -> None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.startswith("/review/"):
            if not self._own():
                return self._json(403, {"error": "foreign host or origin"})
            if self.path == "/review/status":
                return self._json(200, {"recording": True})
            if self.path == "/review/decisions":
                with self.store.lock:
                    log = load_log()
                return self._json(
                    200, [d.model_dump(by_alias=True, exclude_none=True) for d in log]
                )
            if self.path == "/review/questions":
                with self.store.lock:
                    state = _questions.fold(_questions.load_log())
                return self._json(200, list(state.values()))
            return self._json(404, {"error": "unknown endpoint"})
        return super().do_GET()

    def _body(self, model):
        """The validated body, or None after an error response."""
        if not self._own():
            self._json(403, {"error": "foreign host or origin"})
            return None
        if not (self.headers.get("Content-Type") or "").startswith("application/json"):
            self._json(400, {"error": "JSON body expected"})
            return None
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = -1
        if not 0 < length <= MAX_BODY:
            self._json(400, {"error": f"body of 1 to {MAX_BODY} bytes expected"})
            return None
        try:
            return model.model_validate_json(self.rfile.read(length))
        except ValidationError as e:
            details = [
                {"loc": list(err["loc"]), "msg": err["msg"]}
                for err in e.errors(
                    include_url=False, include_input=False, include_context=False
                )
            ]
            self._json(400, {"error": "invalid body", "details": details})
            return None

    def do_POST(self):
        if self.path == "/review/questions":
            return self._question()
        if self.path != "/review/decisions":
            return self._json(404, {"error": "unknown endpoint"})
        submitted = self._body(DecisionIn)
        if submitted is None:
            return None
        with self.store.lock:
            problem = check(submitted, self.store.current())
            if problem:
                return self._json(409, {"error": problem})
            if submitted.supersedes and submitted.supersedes not in {
                d.id for d in load_log()
            }:
                return self._json(409, {"error": "supersedes an unknown decision"})
            stored = stamp(submitted)
            append(stored)
        return self._json(201, stored.model_dump(by_alias=True, exclude_none=True))

    def _question(self):
        submitted = self._body(QuestionIn)
        if submitted is None:
            return None
        # The browser speaks for a person; rules and agents seed from the shell.
        if submitted.by != "person":
            return self._json(400, {"error": "the viewer records a person's events"})
        with self.store.lock:
            self.store.current()
            reason = _questions.problem(
                submitted, _questions.load_log(), self.store.ids
            )
            if reason:
                return self._json(409, {"error": reason})
            stored = _questions.stamp(submitted)
            _questions.append(stored)
        return self._json(201, stored.model_dump(exclude_none=True))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--log",
        type=Path,
        default=_review.LOG,
        help="decision log; a different file keeps trial runs out of the review",
    )
    parser.add_argument(
        "--questions",
        type=Path,
        default=None,
        help="question log; defaults to questions.jsonl beside the decision log",
    )
    args = parser.parse_args()
    _review.LOG = args.log.resolve()
    _review.REVIEW_DIR = _review.LOG.parent
    _questions.LOG = (
        args.questions or _review.LOG.with_name("questions.jsonl")
    ).resolve()
    Handler.store = Store()
    Handler.port = args.port
    Handler.store.current()
    server = ThreadingHTTPServer(
        ("127.0.0.1", args.port), partial(Handler, directory=str(DERIVED_DIR))
    )
    print(
        f"OK serving {DERIVED_DIR} on http://127.0.0.1:{args.port}/viewer/index.html, "
        f"decisions to {_review.LOG}, questions to {_questions.LOG}",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())

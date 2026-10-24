"""Local review server: serves the viewer with the print data and records review decisions.

The viewer is static, but a decision must reach a file the pipeline reads, and
it must not be lost in a browser store. This server serves data/print/derived/
as a static site and accepts decisions, which it validates with the strict
models of _review.py, checks against the current records, stamps with
identifier and time, and appends to data/print/review/decisions.jsonl.

/viewer/<file> is the viewer's code from its versioned folder (viewer/ beside
this module) when the file exists there, so that an edit shows on reload
without a copy, and otherwise the file in data/print/derived/viewer/. The
data files p12 writes (VIEWER_DATA_FILES) come from derived only, so that a
stray copy in the versioned folder never stands in for them.

Trust boundary: the browser. The server binds to 127.0.0.1 only, refuses a
Host or Origin other than its own on every request (against DNS rebinding,
which would otherwise read the print data, and cross-site posts), refuses a
path with a dot segment or a backslash and any /viewer/ path that resolves
outside both viewer folders, accepts JSON bodies up to MAX_BODY bytes, and
never takes identifier, time or a value's current state from the request.

Endpoints:
- GET /review/status: {"recording": true}; the viewer offers decisions only
  when this answers.
- GET /review/decisions: every logged decision, in order.
- POST /review/decisions: one decision; 201 with the stored decision, 400 for a
  malformed one, 409 when it does not apply to the current records (a changed
  value, a correction that does not follow from its passage), 403 for a
  foreign Host or Origin.
- GET /print/<volume>.pdf: the print volume itself (I, A1, A2), so that a
  record links to its page as /print/I.pdf#page=790. Local like every print
  file; the volume names come from sections.json, never from the request path.

Usage: python -m uv run python pipeline/print_volumes/review_server.py [--port 8765]
"""

import argparse
import json
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

import _review
from _common import DERIVED_DIR, PRINT_DIR
from _review import DecisionIn, append, check, load_log, load_records, stamp
from _viewer_data import VIEWER_DATA_FILES
from pydantic import ValidationError

RECORDS = DERIVED_DIR / "records"
MAX_BODY = 64 * 1024
SECTIONS = Path(__file__).with_name("sections.json")
VIEWER_CODE = Path(__file__).resolve().with_name("viewer")
VIEWER_DATA = DERIVED_DIR / "viewer"
PDFS = {
    volume: PRINT_DIR / spec["file"]
    for volume, spec in json.loads(SECTIONS.read_text(encoding="utf-8"))[
        "volumes"
    ].items()
}


def route(path: str) -> str | None:
    """The decoded request path without query and fragment; None if it holds a dot segment or a backslash."""
    path = unquote(path.split("?", 1)[0].split("#", 1)[0])
    if "\\" in path or "\0" in path:
        return None
    if any(part in (".", "..") for part in path.split("/")):
        return None
    return path


def viewer_file(name: str) -> Path | None:
    """The file /viewer/<name> serves: versioned code first, derived data otherwise."""
    name = name or "index.html"
    folders = (
        (VIEWER_DATA,) if name in VIEWER_DATA_FILES else (VIEWER_CODE, VIEWER_DATA)
    )
    for folder in folders:
        base = folder.resolve()
        candidate = (base / name).resolve()
        if candidate.is_relative_to(base) and candidate.is_file():
            return candidate
    return None


class Store:
    """The current records, reloaded when p03 has rewritten them."""

    def __init__(self):
        self.lock = threading.Lock()
        self.stamp = None
        self.records: dict[str, dict] = {}

    def current(self) -> dict[str, dict]:
        mtimes = tuple(
            p.stat().st_mtime_ns for p in sorted(RECORDS.glob("entries-*.jsonl"))
        )
        if mtimes != self.stamp:
            self.records = load_records(RECORDS)
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

    def translate_path(self, path: str) -> str:
        clean = route(path)
        if clean is not None and clean.startswith("/viewer/"):
            found = viewer_file(clean.removeprefix("/viewer/"))
            if found is not None:
                return str(found)
        return super().translate_path(path)

    def end_headers(self) -> None:
        # Revalidate every file, so that an edit of the viewer code shows on reload.
        if getattr(self, "static", False):
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def _static(self, send):
        self.static = False
        if not self._own():
            return self.send_error(403, "foreign host or origin")
        path = route(self.path)
        if path is None or (
            path.startswith("/viewer/")
            and viewer_file(path.removeprefix("/viewer/")) is None
        ):
            return self.send_error(404, "no such file")
        self.static = True
        return send()

    def do_HEAD(self):
        return self._static(super().do_HEAD)

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
            return self._json(404, {"error": "unknown endpoint"})
        if self.path.startswith("/print/"):
            return self._pdf()
        return self._static(super().do_GET)

    def _pdf(self):
        if not self._own():
            return self._json(403, {"error": "foreign host or origin"})
        name = self.path.split("?")[0].split("#")[0].removeprefix("/print/")
        pdf = PDFS.get(name.removesuffix(".pdf")) if name.endswith(".pdf") else None
        if pdf is None or not pdf.exists():
            return self._json(404, {"error": "no such volume"})
        self.send_response(200)
        self.send_header("Content-Type", "application/pdf")
        self.send_header("Content-Length", str(pdf.stat().st_size))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        with pdf.open("rb") as source:
            while chunk := source.read(1 << 20):
                self.wfile.write(chunk)
        return None

    def do_POST(self):
        if self.path != "/review/decisions":
            return self._json(404, {"error": "unknown endpoint"})
        if not self._own():
            return self._json(403, {"error": "foreign host or origin"})
        if not (self.headers.get("Content-Type") or "").startswith("application/json"):
            return self._json(400, {"error": "JSON body expected"})
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = -1
        if not 0 < length <= MAX_BODY:
            return self._json(400, {"error": f"body of 1 to {MAX_BODY} bytes expected"})
        try:
            submitted = DecisionIn.model_validate_json(self.rfile.read(length))
        except ValidationError as e:
            details = [
                {"loc": list(err["loc"]), "msg": err["msg"]}
                for err in e.errors(
                    include_url=False, include_input=False, include_context=False
                )
            ]
            return self._json(400, {"error": "invalid decision", "details": details})
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--log",
        type=Path,
        default=_review.LOG,
        help="decision log; a different file keeps trial runs out of the review",
    )
    args = parser.parse_args()
    _review.LOG = args.log.resolve()
    _review.REVIEW_DIR = _review.LOG.parent
    Handler.store = Store()
    Handler.port = args.port
    Handler.store.current()
    server = ThreadingHTTPServer(
        ("127.0.0.1", args.port), partial(Handler, directory=str(DERIVED_DIR))
    )
    print(
        f"OK serving {DERIVED_DIR} with the viewer code from {VIEWER_CODE} on "
        f"http://127.0.0.1:{args.port}/viewer/cards.html, decisions to {_review.LOG}",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())

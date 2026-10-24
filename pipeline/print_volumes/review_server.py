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
- GET /review/status: {"recording": true} when the log can be read, else
  {"recording": false, "error": reason}; the viewer offers decisions only on
  the first.
- GET /review/decisions: every logged decision, in order.
  ?reviewer=<name> returns only that reviewer's decisions, so that a second
  reviewer decides without seeing the first's; any other parameter is a 400.
  An unreadable log is a 503 with its reason.
- POST /review/decisions: one decision; 201 with the stored decision, 400 for a
  malformed one, 409 when it does not apply to the current records (a changed
  value, a correction that does not follow from its passage) or to the log (a
  withdrawal of another reviewer's decision, an adjudication that settles no
  disagreement in force between an object's first and second reviewer), 403
  for a foreign Host or Origin.
- GET /print/<volume>.pdf: the print volume itself (I, A1, A2), so that a
  record links to its page as /print/I.pdf#page=790. Local like every print
  file; the volume names come from sections.json, never from the request path.
- GET /check/page/<volume>/<n>.json: one PDF page for the page check view
  (viewer/page.html), its p01 lines with their role and the records, objects
  and values p03 read from them (page_render.Source.assemble). Volume one of
  sections.json, n an integer within the volume's pages, no query; 400 for a
  malformed path, 404 for a page out of range.
- GET /check/page/<volume>/<n>.png: the page rendered, cached in
  data/print/derived/check/; 503 when pypdfium2 is missing (the print
  dependency group), and the view falls back to the PDF itself.
- GET /check/find.json?q=<identifier or address>: the records it names, with
  volume and page, for the view's jump.
Everything /check/ answers is read from data/print/ and holds print text, so
it is served like the PDF, to this machine only, and never written to a
versioned file.

Usage: python -m uv run --group print python pipeline/print_volumes/review_server.py [--port 8767]
"""

import argparse
import json
import re
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

import _review
import page_render
from _common import DERIVED_DIR, PRINT_DIR, PROJECT_ROOT
from _review import (
    DecisionIn,
    adjudication_problem,
    append,
    check,
    load_log,
    load_records,
    stamp,
)
from _viewer_data import VIEWER_DATA_FILES
from page_render import Source as PageSource
from pydantic import ValidationError

RECORDS = DERIVED_DIR / "records"
MAX_BODY = 64 * 1024
SECTIONS = Path(__file__).with_name("sections.json")
VIEWER_CODE = Path(__file__).resolve().with_name("viewer")
VIEWER_DATA = DERIVED_DIR / "viewer"
DOCS_DIR = PROJECT_ROOT / "docs"
LAB_STRUCTURE = DERIVED_DIR / "lab" / "print-structure.json"
PDFS = {
    volume: PRINT_DIR / spec["file"]
    for volume, spec in json.loads(SECTIONS.read_text(encoding="utf-8"))[
        "volumes"
    ].items()
}
# Matched against the raw request path, so that no decoding can widen it.
CHECK_PAGE = re.compile(r"/check/page/([A-Z0-9]{1,4})/([1-9][0-9]{0,4})\.(json|png)")
FIND_MAX = 64


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


def docs_file(clean_path: str) -> Path | None:
    """Serve docs/ at root and local/print-structure.json from derived/lab/ if present."""
    if clean_path == "/local/print-structure.json" and LAB_STRUCTURE.is_file():
        return LAB_STRUCTURE.resolve()
    rel = clean_path.lstrip("/") or "index.html"
    base = DOCS_DIR.resolve()
    candidate = (base / rel).resolve()
    if candidate.is_relative_to(base):
        if candidate.is_dir():
            idx = (candidate / "index.html").resolve()
            if idx.is_relative_to(base) and idx.is_file():
                return idx
        elif candidate.is_file():
            return candidate
    return None


def byte_range(header: str, size: int) -> tuple[int, int] | None:
    """The inclusive span of a single "bytes=a-b", "bytes=a-" or "bytes=-n" range; None if unsatisfiable."""
    unit, _, spec = header.partition("=")
    if unit.strip() != "bytes" or "," in spec:
        return None
    first, _, last = spec.strip().partition("-")
    try:
        if not first:
            count = int(last)
            if count <= 0:
                return None
            return max(size - count, 0), size - 1
        start = int(first)
        end = int(last) if last else size - 1
    except ValueError:
        return None
    if start > end or start >= size:
        return None
    return start, min(end, size - 1)


def log_problem(submitted: DecisionIn, log: list) -> str | None:
    """None when the decision fits the log: a withdrawal names a logged
    decision of the same reviewer, an adjudication a disagreement in force."""
    if submitted.supersedes:
        withdrawn = next((d for d in log if d.id == submitted.supersedes), None)
        if withdrawn is None:
            return "supersedes an unknown decision"
        if withdrawn.reviewer != submitted.reviewer:
            return "a reviewer withdraws only their own decisions"
    if submitted.decision == "adjudicate":
        return adjudication_problem(submitted, log)
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
    pages: PageSource
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
        if clean is not None:
            if clean.startswith("/viewer/"):
                found = viewer_file(clean.removeprefix("/viewer/"))
                if found is not None:
                    return str(found)
            elif not clean.startswith("/jsonld/"):
                found = docs_file(clean)
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
        if self.path.startswith("/print/"):
            return self._pdf(body=False)
        if self.path.startswith("/check/"):
            self.send_response(405 if self._own() else 403)
            self.send_header("Allow", "GET")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None
        return self._static(super().do_HEAD)

    def _log(self):
        """The log, or the reason it cannot be read."""
        try:
            with self.store.lock:
                return load_log(), None
        except (OSError, ValueError) as e:
            return None, str(e)

    def do_GET(self):
        if self.path.startswith("/review/"):
            if not self._own():
                return self._json(403, {"error": "foreign host or origin"})
            url = urlsplit(self.path)
            if url.path == "/review/status" and not url.query:
                _, error = self._log()
                if error:
                    return self._json(200, {"recording": False, "error": error})
                return self._json(200, {"recording": True})
            if url.path == "/review/decisions":
                query = parse_qs(url.query, keep_blank_values=True)
                if set(query) - {"reviewer"} or any(
                    len(v) != 1 or not v[0].strip() for v in query.values()
                ):
                    return self._json(
                        400, {"error": "the only parameter is one non-empty reviewer"}
                    )
                log, error = self._log()
                if error:
                    return self._json(503, {"error": error})
                if query:
                    log = [d for d in log if d.reviewer == query["reviewer"][0]]
                return self._json(
                    200, [d.model_dump(by_alias=True, exclude_none=True) for d in log]
                )
            return self._json(404, {"error": "unknown endpoint"})
        if self.path.startswith("/print/"):
            return self._pdf()
        if self.path.startswith("/check/"):
            return self._check()
        return self._static(super().do_GET)

    def _check(self):
        """The page check data: a page's lines and records, its image, or a record jump."""
        if not self._own():
            return self._json(403, {"error": "foreign host or origin"})
        path, _, query = self.path.partition("?")
        try:
            if path == "/check/find.json":
                params = parse_qs(query, keep_blank_values=True)
                wanted = params.get("q", [""])
                if set(params) != {"q"} or len(wanted) != 1:
                    return self._json(400, {"error": "the only parameter is one q"})
                if not 0 < len(wanted[0].strip()) <= FIND_MAX:
                    return self._json(
                        400, {"error": f"q of 1 to {FIND_MAX} characters"}
                    )
                return self._json(200, self.pages.find(wanted[0]))
            match = CHECK_PAGE.fullmatch(path)
            if match is None or query or "#" in path:
                return self._json(
                    400, {"error": "expected /check/page/<volume>/<n>.json or .png"}
                )
            volume, page, ext = match[1], int(match[2]), match[3]
            if volume not in PDFS:
                return self._json(404, {"error": "no such volume"})
            if not 1 <= page <= self.pages.pages(volume):
                return self._json(404, {"error": "no such page"})
            if ext == "json":
                return self._json(200, self.pages.assemble(volume, page))
            try:
                data = self.pages.render(volume, page)
            except RuntimeError as e:
                return self._json(503, {"error": str(e)})
        except (OSError, ValueError) as e:
            return self._json(503, {"error": f"print data unreadable: {e}"})
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(data)))
        # Like the volume itself, the image never leaves this machine.
        self.send_header("Cache-Control", "private, max-age=3600")
        self.end_headers()
        self.wfile.write(data)
        return None

    def _pdf(self, body=True):
        """One print volume, whole or as the single byte range a PDF viewer asks for."""
        if not self._own():
            return self._json(403, {"error": "foreign host or origin"})
        name = self.path.split("?")[0].split("#")[0].removeprefix("/print/")
        pdf = PDFS.get(name.removesuffix(".pdf")) if name.endswith(".pdf") else None
        if pdf is None or not pdf.exists():
            return self._json(404, {"error": "no such volume"})
        size = pdf.stat().st_size
        start, end = 0, size - 1
        wanted = self.headers.get("Range")
        if wanted:
            span = byte_range(wanted, size)
            if span is None:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return None
            start, end = span
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", "application/pdf")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        # The volume never leaves this machine, so the browser may keep it.
        self.send_header("Cache-Control", "private, max-age=3600")
        self.end_headers()
        if not body:
            return None
        with pdf.open("rb") as source:
            source.seek(start)
            left = end - start + 1
            while left > 0 and (chunk := source.read(min(1 << 20, left))):
                self.wfile.write(chunk)
                left -= len(chunk)
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
            try:
                log = load_log()
            except (OSError, ValueError) as e:
                return self._json(503, {"error": str(e)})
            problem = log_problem(submitted, log)
            if problem:
                return self._json(409, {"error": problem})
            stored = stamp(submitted)
            append(stored)
        return self._json(201, stored.model_dump(by_alias=True, exclude_none=True))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=8767)
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
    Handler.pages = PageSource()
    Handler.port = args.port
    Handler.store.current()
    # The page check joins all lines and records once, which takes seconds;
    # start it now, so that it is done or under way when a page is asked for.
    threading.Thread(target=Handler.pages.current, daemon=True).start()
    server = ThreadingHTTPServer(
        ("127.0.0.1", args.port), partial(Handler, directory=str(DERIVED_DIR))
    )
    print(
        f"OK serving {DERIVED_DIR} with the viewer code from {VIEWER_CODE} on "
        f"http://127.0.0.1:{args.port}/viewer/cards.html, decisions to {_review.LOG}",
        flush=True,
    )
    if page_render.pdfium is None:
        # The page check falls back to the PDF; the person sees no command.
        print(
            "WARN page check without page images: pypdfium2 is missing; start with "
            "python -m uv run --group print python pipeline/print_volumes/review_server.py",
            flush=True,
        )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())

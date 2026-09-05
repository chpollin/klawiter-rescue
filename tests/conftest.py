"""
Fixtures for Klawiter pipeline tests.
Uses real examples from the dataset to test extraction functions.
"""

import hashlib
import json
import os
import shutil
from functools import cache
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
TEST_SAMPLE_PATH = PROJECT_ROOT / "tests" / "test_sample_20.json"
WIKI_GROUND_TRUTH = PROJECT_ROOT / "tests" / "wiki_ground_truth.json"
SEMANTIC_BASELINE_PATH = PROJECT_ROOT / ".github" / "semantic-baseline.json"
FRONTEND_JSON = PROJECT_ROOT / "docs" / "data" / "klawiter.json"
BASELINE_PATH = PROJECT_ROOT / ".github" / "baseline-metrics.json"
QUALITY_REPORT = PROJECT_ROOT / "data" / "output" / "quality-report.json"


@cache
def _read_committed_json(path):
    """Committed test inputs are required; never replace missing truth with skips."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise pytest.UsageError(
            f"Cannot read required test input {path}: {exc}"
        ) from exc


def pytest_addoption(parser):
    parser.addoption(
        "--require-test-inputs",
        action="store_true",
        help="Fail instead of skipping when Node or stage intermediates are missing.",
    )


@pytest.fixture(scope="session")
def node_executable(pytestconfig):
    node = shutil.which("node")
    if node:
        return node
    message = "Node.js is required for frontend behavior and syntax tests"
    if (
        pytestconfig.getoption("--require-test-inputs")
        or os.environ.get("CI") == "true"
    ):
        pytest.fail(message, pytrace=False)
    pytest.skip(message)


# --- Shared data fixtures (loaded once per session) ---


@pytest.fixture(scope="session")
def frontend_data():
    """Load frontend JSON once for all data tests."""
    return _read_committed_json(FRONTEND_JSON)


@pytest.fixture(scope="session")
def all_entries(frontend_data):
    """All entries from frontend JSON."""
    return frontend_data["entries"]


@pytest.fixture(scope="session")
def ns0_entries(all_entries):
    """Namespace-0 (bibliography) entries only."""
    return [e for e in all_entries if e.get("pageNamespace") == 0]


@pytest.fixture(scope="session")
def ns0_by_id(ns0_entries):
    return {entry["sourcePageId"]: entry for entry in ns0_entries}


@pytest.fixture(scope="session")
def canonical_entries():
    path = PROJECT_ROOT / "data" / "output" / "klawiter.jsonld"
    return _read_committed_json(path)["entries"]


@pytest.fixture(scope="session")
def wiki_entries():
    return _load_wiki_ground_truth()


@pytest.fixture(scope="session")
def semantic_baseline():
    return _read_committed_json(SEMANTIC_BASELINE_PATH)


@pytest.fixture(scope="session")
def extraction_baseline():
    return _read_committed_json(PROJECT_ROOT / ".github" / "extraction-baseline.json")


@pytest.fixture(scope="session")
def redirects(frontend_data):
    """Redirect map from frontend JSON."""
    return frontend_data["redirects"]


@pytest.fixture(scope="session")
def all_titles(ns0_entries):
    """Set of all ns-0 entry titles."""
    return {e.get("title") for e in ns0_entries if e.get("title")}


@pytest.fixture(scope="session")
def baseline():
    """Load baseline metrics once."""
    return _read_committed_json(BASELINE_PATH)


@pytest.fixture(scope="session")
def quality_report():
    """Load quality report once."""
    return _read_committed_json(QUALITY_REPORT)


# Regenerable stage intermediates (gitignored; stages 01-04 recreate them from
# the committed raw dump).
STAGE_02_CSV = PROJECT_ROOT / "data" / "intermediate" / "02_encoding_fixed.csv"
STAGE_04_CSV = PROJECT_ROOT / "data" / "intermediate" / "04_classified.csv"


@pytest.fixture(scope="session")
def required_intermediates(pytestconfig):
    """Guard for tests that read the gitignored stage CSVs.

    Locally their absence is a skip. CI and --require-test-inputs require
    them; KLAWITER_REQUIRE_INTERMEDIATES=1 remains supported for old callers.
    """
    missing = [p.name for p in (STAGE_02_CSV, STAGE_04_CSV) if not p.exists()]
    if not missing:
        return
    message = (
        f"stage intermediates missing ({', '.join(missing)}) — run "
        "`python pipeline/run_pipeline.py --to-stage 04 --no-postprocess`"
    )
    if (
        pytestconfig.getoption("--require-test-inputs")
        or os.environ.get("CI") == "true"
        or os.environ.get("KLAWITER_REQUIRE_INTERMEDIATES") == "1"
    ):
        pytest.fail(message, pytrace=False)
    pytest.skip(message)


@pytest.fixture(scope="session")
def source_rows(required_intermediates):
    from lib.config import load_csv

    return load_csv(STAGE_02_CSV)


@pytest.fixture(scope="session")
def classified_rows(required_intermediates):
    from lib.config import load_csv

    return load_csv(STAGE_04_CSV)


# --- Real dataset fixtures ---


def _load_test_sample():
    """Load complete, source-reviewed test entries from test_sample_20.json."""
    entries = _read_committed_json(TEST_SAMPLE_PATH)
    if not entries:
        raise pytest.UsageError(f"Empty required test sample: {TEST_SAMPLE_PATH}")
    return entries


@pytest.fixture(scope="session")
def real_entries():
    """All 20 complete source texts and reviewed field expectations."""
    return _load_test_sample()


def _load_wiki_ground_truth():
    """Validate the reviewed oracle before it defines the collected test cases."""
    entries = _read_committed_json(WIKI_GROUND_TRUTH)
    if not entries:
        raise pytest.UsageError(f"Empty required ground truth: {WIKI_GROUND_TRUTH}")
    baseline = _read_committed_json(SEMANTIC_BASELINE_PATH)
    digest = hashlib.sha256(WIKI_GROUND_TRUTH.read_bytes()).hexdigest()
    if digest != baseline["groundTruthSha256"]:
        raise pytest.UsageError(
            "Changed semantic ground truth requires a reviewed baseline hash update"
        )
    ids = [entry["page_id"] for entry in entries]
    if len(ids) != len(set(ids)) or sorted(ids) != baseline["groundTruthPageIds"]:
        raise pytest.UsageError("Semantic ground-truth page inventory changed")
    fields = set(baseline["groundTruthFields"])
    if any(set(entry["expected"]) != fields for entry in entries):
        raise pytest.UsageError("Semantic ground-truth field inventory changed")
    return entries


def pytest_generate_tests(metafunc):
    """Parametrize tests that request 'real_entry' or 'wiki_entry' fixture."""
    if "real_entry" in metafunc.fixturenames:
        entries = _load_test_sample()
        ids = [f"page_{e['page_id']}_{e['label']}" for e in entries]
        metafunc.parametrize("real_entry", entries, ids=ids)
    if "wiki_entry" in metafunc.fixturenames:
        entries = _load_wiki_ground_truth()
        ids = [f"page_{e['page_id']}_{e.get('page_title', '')[:30]}" for e in entries]
        metafunc.parametrize("wiki_entry", entries, ids=ids)


# --- Gemini client fixture ---


@pytest.fixture(scope="session")
def gemini_client():
    """Create Gemini client, loading API key from .env if needed."""
    from lib.config import load_env

    load_env()
    if not os.environ.get("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set — LLM tests need it in .env")
    from lib.llm_extract import create_client

    return create_client()


# --- Wiki content samples for unit tests ---


@pytest.fixture
def entry_standard_header():
    """Standard '''[year]: Publisher, Location''' header format (Swedish fiction)."""
    return (
        "'''[1943]: Skoglunds Bokförlag, Stockholm'''\n\n"
        "Schack, Amok och andra noveller [Schachnovelle, Der Amokläufer und andere Novellen]. "
        "Translated by Hugo Hultenberg. 347/(1)p. \n\n"
        "'''Contents:'''\n"
        "<lst type=bracket start=1>\n"
        "Schack [Schachnovelle], pp. (7)-79\n"
        "Amoklöparen [Der Amokläufer], pp. (81)-155\n"
        "</lst>\n\n"
        "[[Category:Fiction / Volumes (Swedish)]]"
    )


@pytest.fixture
def entry_bold_title():
    """Entry with a bold title (not a year-publisher header)."""
    return (
        "'''Marie Antoinette''' (Original German Title)\n\n"
        "Published by Insel-Verlag. Leipzig, 1932. 542p.\n\n"
        "[[Category:Historical Studies / Volumes (German)]]"
    )


@pytest.fixture
def entry_redirect():
    """A redirect entry."""
    return "#REDIRECT [[Mariia Antoaneta. Slika jednog osrednjeg karaktera]]"


@pytest.fixture
def entry_see_references():
    """Entry with See references."""
    return (
        '\\"Amoku\\" [Der Amokläufer]. '
        "'''See:''' [[Der Amokläufer]] [Translations: Japanese)]\n\n"
        "[[Category:Fiction / Individual Stories (Japanese)]]"
    )


@pytest.fixture
def entry_reprints():
    """Entry with reprints block."""
    return (
        "'''Die Welt von Gestern'''\n\n"
        "First published 1942.\n\n"
        "'''Reprinted in:'''\n"
        "[[Gesammelte Werke]] [Frankfurt, 1981], pp. 7-320\n"
        "[[Ausgewählte Werke]] [Berlin, 1990], pp. 5-280\n\n"
        "[[Category:Autobiographical Works (German)]]"
    )


@pytest.fixture
def entry_translations_block():
    """Entry with translations block."""
    return (
        "'''Schachnovelle'''\n\n"
        "Written 1941, published posthumously 1942.\n\n"
        "'''Translations:'''\n"
        "English: The Royal Game\n"
        "French: Le Joueur d'échecs\n"
        "Spanish: Novela de ajedrez\n\n"
        "[[Category:Fiction / Novellas (German)]]"
    )


@pytest.fixture
def entry_collected_works():
    """Collected works entry with contents block."""
    return (
        "'''[1976]: Suhrkamp Verlag, Frankfurt am Main'''\n\n"
        "''Die Monotonisierung der Welt. Aufsätze und Vorträge''. "
        "Compiled with an afterword by Volker Michels. 254/(1)p.\n\n"
        "'''Contents:'''\n"
        "<lst type=bracket start=1>\n"
        "Die Monotonisierung der Welt, pp. 7-18\n"
        "Das Geheimnis des künstlerischen Schaffens, pp. 19-45\n"
        "</lst>\n\n"
        "[[Category:Essays / Volumes (German)]]"
    )


@pytest.fixture
def entry_film():
    """Film entry (no publisher/translator/page_count expected)."""
    return (
        "'''[1984]: Czechoslovakia'''\n\n"
        "''Sach mat'' [Schachnovelle]\n"
        "<lst type=bracket start=1>\n"
        "Language: Chechen\n"
        "Director: Ladislav Rychman\n"
        "Runtime: 32 minutes\n"
        "</lst>\n\n"
        "[[Category:Films / Plays / Operas]]\n"
        "{{DEFAULTSORTKEY:Sach-mat}}"
    )


# --- Encoding fixtures ---


@pytest.fixture
def mojibake_text():
    return "SchÃ¤fer und MÃ¼ller"


@pytest.fixture
def mojibake_fixed():
    return "Schäfer und Müller"


@pytest.fixture
def clean_utf8_text():
    return "Schäfer und Müller"


@pytest.fixture
def html_entity_text():
    return "Stefan&nbsp;Zweig &mdash; Die Welt&amp;Gestern &#65; &#x3B1;"


@pytest.fixture
def html_entity_fixed():
    return "Stefan Zweig — Die Welt&Gestern A α"

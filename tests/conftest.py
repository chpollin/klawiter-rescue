"""
Fixtures for Klawiter pipeline tests.
Uses real examples from the dataset to test extraction functions.
"""

import json
import os
import sys
from pathlib import Path

import pytest

# Add pipeline directory to path so we can import lib modules
sys.path.insert(0, str(Path(__file__).parent.parent / "pipeline"))

PROJECT_ROOT = Path(__file__).parent.parent
# Hand-labeled ground truth: not regenerable, belongs committed in tests/.
# The original lived uncommitted in data/intermediate/ and was lost; the
# legacy path stays as a fallback in case a backup copy is restored there.
_TEST_SAMPLE_CANDIDATES = (
    PROJECT_ROOT / "tests" / "test_sample_20.json",
    PROJECT_ROOT / "data" / "intermediate" / "test_sample_20.json",
)
TEST_SAMPLE_PATH = next(
    (p for p in _TEST_SAMPLE_CANDIDATES if p.exists()), _TEST_SAMPLE_CANDIDATES[0]
)
WIKI_GROUND_TRUTH = PROJECT_ROOT / "tests" / "wiki_ground_truth.json"
FRONTEND_JSON = PROJECT_ROOT / "docs" / "data" / "klawiter.json"
BASELINE_PATH = PROJECT_ROOT / ".github" / "baseline-metrics.json"
QUALITY_REPORT = PROJECT_ROOT / "data" / "output" / "quality-report.json"


# --- Shared data fixtures (loaded once per session) ---


@pytest.fixture(scope="session")
def frontend_data():
    """Load frontend JSON once for all data tests."""
    if not FRONTEND_JSON.exists():
        pytest.skip("Frontend JSON not found — run pipeline step 05 first")
    with open(FRONTEND_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def all_entries(frontend_data):
    """All entries from frontend JSON."""
    return frontend_data["entries"]


@pytest.fixture(scope="session")
def ns0_entries(all_entries):
    """Namespace-0 (bibliography) entries only."""
    return [e for e in all_entries if e.get("pageNamespace") == 0]


@pytest.fixture(scope="session")
def redirects(frontend_data):
    """Redirect map from frontend JSON."""
    return frontend_data.get("redirects", {})


@pytest.fixture(scope="session")
def all_titles(ns0_entries):
    """Set of all ns-0 entry titles."""
    return {e.get("title") for e in ns0_entries if e.get("title")}


@pytest.fixture(scope="session")
def redirect_targets(frontend_data):
    """Set of all redirect target values."""
    return set(frontend_data.get("redirects", {}).values())


@pytest.fixture(scope="session")
def baseline():
    """Load baseline metrics once."""
    if not BASELINE_PATH.exists():
        pytest.skip("baseline-metrics.json not found")
    with open(BASELINE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def quality_report():
    """Load quality report once."""
    if not QUALITY_REPORT.exists():
        pytest.skip("quality-report.json not found (run pipeline step 06 first)")
    with open(QUALITY_REPORT, "r", encoding="utf-8") as f:
        return json.load(f)


# Regenerable stage intermediates (gitignored; stages 01-04 recreate them from
# the committed raw dump).
STAGE_02_CSV = PROJECT_ROOT / "data" / "intermediate" / "02_encoding_fixed.csv"
STAGE_04_CSV = PROJECT_ROOT / "data" / "intermediate" / "04_classified.csv"


@pytest.fixture(scope="session")
def required_intermediates():
    """Guard for tests that read the gitignored stage CSVs.

    Locally their absence is a friendly skip; CI regenerates them first and
    sets KLAWITER_REQUIRE_INTERMEDIATES=1 so a missing file there is a hard
    failure, never a silent skip.
    """
    missing = [p.name for p in (STAGE_02_CSV, STAGE_04_CSV) if not p.exists()]
    if not missing:
        return
    message = (
        f"stage intermediates missing ({', '.join(missing)}) — run "
        "`python pipeline/run_pipeline.py --to-stage 04 --no-postprocess`"
    )
    if os.environ.get("KLAWITER_REQUIRE_INTERMEDIATES") == "1":
        pytest.fail(message, pytrace=False)
    pytest.skip(message)


# --- Real dataset fixtures ---


def _load_test_sample():
    """Load hand-labeled test entries from test_sample_20.json."""
    with open(TEST_SAMPLE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def real_entries():
    """All 20 hand-labeled test entries."""
    if not TEST_SAMPLE_PATH.exists():
        pytest.skip(
            "test_sample_20.json not found — hand-labeled sample, "
            "not regenerable (see knowledge/testing.md)"
        )
    return _load_test_sample()


def _load_wiki_ground_truth():
    """Load wiki-verified ground truth entries."""
    if not WIKI_GROUND_TRUTH.exists():
        return []
    with open(WIKI_GROUND_TRUTH, "r", encoding="utf-8") as f:
        return json.load(f)


def pytest_generate_tests(metafunc):
    """Parametrize tests that request 'real_entry' or 'wiki_entry' fixture."""
    if "real_entry" in metafunc.fixturenames:
        if TEST_SAMPLE_PATH.exists():
            entries = _load_test_sample()
            ids = [f"page_{e['page_id']}_{e['label']}" for e in entries]
            metafunc.parametrize("real_entry", entries, ids=ids)
        else:
            metafunc.parametrize(
                "real_entry",
                [
                    pytest.param(
                        None,
                        marks=pytest.mark.skip(
                            reason="test_sample_20.json not found — hand-labeled sample, "
                            "not regenerable (see knowledge/testing.md)"
                        ),
                    )
                ],
            )
    if "wiki_entry" in metafunc.fixturenames:
        entries = _load_wiki_ground_truth()
        if not entries:
            pytest.skip("wiki_ground_truth.json not found")
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

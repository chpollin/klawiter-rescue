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
TEST_SAMPLE_PATH = PROJECT_ROOT / "data" / "intermediate" / "test_sample_20.json"


# --- Real dataset fixtures ---

def _load_test_sample():
    """Load hand-labeled test entries from test_sample_20.json."""
    with open(TEST_SAMPLE_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


@pytest.fixture(scope="session")
def real_entries():
    """All 20 hand-labeled test entries."""
    return _load_test_sample()


def pytest_generate_tests(metafunc):
    """Parametrize tests that request 'real_entry' fixture."""
    if "real_entry" in metafunc.fixturenames:
        entries = _load_test_sample()
        ids = [f"page_{e['page_id']}_{e['label']}" for e in entries]
        metafunc.parametrize("real_entry", entries, ids=ids)


# --- Gemini client fixture ---

@pytest.fixture(scope="session")
def gemini_client():
    """Create Gemini client, loading API key from .env if needed."""
    from lib.config import load_env
    from lib.llm_extract import create_client
    load_env()
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
        "\\\"Amoku\\\" [Der Amokläufer]. "
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

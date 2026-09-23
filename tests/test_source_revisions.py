"""Redirect fixer overwrites: detection rule, reviewed decisions, published result.

The wiki's automatic "Redirect fixer" account rewrote pages that redirected
to a moved page. Where it rewrote a content page, the edition publishes the
last human revision; where the rewritten revision is not delivered, the
redirect is withheld as a relation and an open claim records the case
(data/reconciliation/source-revision-decisions.json).
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest
from lib.config import SOURCE_REVISION_DECISIONS, SQL_DUMP_PATH

extract = importlib.import_module("01_extract")
stage_05 = importlib.import_module("05_to_jsonld")

DECISIONS = json.loads(Path(SOURCE_REVISION_DECISIONS).read_text(encoding="utf-8"))
BY_PAGE = {decision["pageId"]: decision for decision in DECISIONS["decisions"]}
RESTORED = {
    pid
    for pid, decision in BY_PAGE.items()
    if decision["action"] == extract.RESTORE_ACTION
}
WITHHELD = {
    pid
    for pid, decision in BY_PAGE.items()
    if decision["action"] == extract.WITHHOLD_ACTION
}


def _fixture_dump():
    """Page 1 overwritten content, page 2 undelivered parent, page 3 the
    fixer's ordinary double-redirect repair, page 4 a human latest revision."""
    pages = {
        1: {"page_latest": 12},
        2: {"page_latest": 21},
        3: {"page_latest": 31},
        4: {"page_latest": 41},
    }
    human, fixer = "Klawiter", extract.FIXER_ACTOR
    revisions = {
        10: {"parent": None, "actor": human},
        11: {"parent": 10, "actor": fixer},
        12: {"parent": 11, "actor": fixer},
        21: {"parent": 20, "actor": fixer},
        30: {"parent": None, "actor": human},
        31: {"parent": 30, "actor": fixer},
        40: {"parent": None, "actor": fixer},
        41: {"parent": 40, "actor": human},
    }
    slots = {rev: rev for rev in revisions}
    contents = {rev: 100 + rev for rev in revisions}
    texts = {
        110: {"content": "'''[1935]: Verlag, Wien''' content"},
        111: {"content": "#REDIRECT [[Moved A]]"},
        112: {"content": "#REDIRECT [[Moved B]]"},
        121: {"content": "#REDIRECT [[Moved C]]"},
        130: {"content": "#redirect [[Old target]]"},
        131: {"content": "#REDIRECT [[New target]]"},
        140: {"content": "#REDIRECT [[Anything]]"},
        141: {"content": "human text"},
    }
    return pages, revisions, slots, contents, texts


def test_fixer_rule_restores_content_and_withholds_undelivered_parents() -> None:
    cases = extract.detect_fixer_overwrites(*_fixture_dump())
    assert cases == {
        1: {
            "pageId": 1,
            "action": extract.RESTORE_ACTION,
            "fixerRevisionIds": [11, 12],
            "humanRevisionId": 10,
            "humanTextId": 110,
        },
        2: {
            "pageId": 2,
            "action": extract.WITHHOLD_ACTION,
            "fixerRevisionIds": [21],
            "humanRevisionId": 20,
        },
    }


def test_decisions_must_match_detection() -> None:
    pages, revisions, slots, contents, texts = _fixture_dump()
    cases = extract.detect_fixer_overwrites(pages, revisions, slots, contents, texts)
    mapping = {1: {"text_id": 112}, 2: {"text_id": 121}}
    decisions = {
        "decisions": [
            {
                "pageId": 1,
                "action": extract.RESTORE_ACTION,
                "fixerRevisions": [
                    {"revisionId": 11, "textId": 111},
                    {"revisionId": 12, "textId": 112},
                ],
                "humanRevision": {
                    "revisionId": 10,
                    "textId": 110,
                    "sha256": extract.text_sha256(texts[110]),
                },
            },
            {
                "pageId": 2,
                "action": extract.WITHHOLD_ACTION,
                "fixerRevisions": [{"revisionId": 21, "textId": 121}],
                "humanRevision": {"revisionId": 20},
            },
        ]
    }
    extract.apply_source_revision_decisions(mapping, cases, decisions, texts)
    assert mapping == {1: {"text_id": 110}, 2: {"text_id": 121}}

    stale = json.loads(json.dumps(decisions))
    stale["decisions"][0]["humanRevision"]["revisionId"] = 9
    with pytest.raises(ValueError, match="differs from the dump"):
        extract.apply_source_revision_decisions(
            {1: {"text_id": 112}, 2: {"text_id": 121}}, cases, stale, texts
        )
    missing = {"decisions": decisions["decisions"][:1]}
    with pytest.raises(ValueError, match="undecided cases"):
        extract.apply_source_revision_decisions(
            {1: {"text_id": 112}, 2: {"text_id": 121}}, cases, missing, texts
        )


@pytest.fixture(scope="module")
def dump_tables():
    with open(SQL_DUMP_PATH, "rb") as handle:
        sql_text = handle.read().decode("latin-1")
    return {
        "pages": extract.load_page_table(sql_text),
        "revisions": extract.load_revisions(sql_text),
        "slots": extract.load_slots_table(sql_text),
        "contents": extract.load_content_table(sql_text),
    }


def test_decisions_are_bound_to_the_revision_tables(dump_tables) -> None:
    """Every recorded revision, actor, timestamp and text id is in the dump."""
    pages, revisions = dump_tables["pages"], dump_tables["revisions"]
    slots, contents = dump_tables["slots"], dump_tables["contents"]
    fixer = [rev for rev in revisions.values() if rev["actor"] == extract.FIXER_ACTOR]
    assert len(fixer) == 851
    for page_id, decision in BY_PAGE.items():
        chain = decision["fixerRevisions"]
        assert pages[page_id]["page_latest"] == chain[-1]["revisionId"]
        for item in chain:
            revision = revisions[item["revisionId"]]
            assert revision["page"] == page_id
            assert revision["actor"] == extract.FIXER_ACTOR
            assert revision["timestamp"] == item["timestamp"]
            assert contents[slots[item["revisionId"]]] == item["textId"]
            assert extract.decode_utf8(revision["comment_raw"]) == item["comment"]
        human = decision["humanRevision"]
        assert revisions[chain[0]["revisionId"]]["parent"] == human["revisionId"]
        if page_id in RESTORED:
            revision = revisions[human["revisionId"]]
            assert revision["actor"] == human["actor"] != extract.FIXER_ACTOR
            assert revision["timestamp"] == human["timestamp"]
            assert contents[slots[human["revisionId"]]] == human["textId"]
        else:
            assert human["revisionId"] not in revisions


def test_maria_stuart_decision_matches_the_source() -> None:
    decision = BY_PAGE[35]
    assert decision["action"] == extract.RESTORE_ACTION
    assert [item["revisionId"] for item in decision["fixerRevisions"]] == [33773]
    fixer = decision["fixerRevisions"][0]
    assert fixer["timestamp"] == "2017-10-08T20:25:29Z"
    assert fixer["textId"] == 32902
    assert fixer["trigger"]["logId"] == 31352
    assert fixer["comment"] == (
        "[[Al-Sulṭānī, Fāḍil]] has been moved, it is now a redirect to "
        "[[Al-Sulṭānī, Fāḍil / Assultani, Fadhil]]"
    )
    assert decision["humanRevision"] == {
        "revisionId": 33251,
        "timestamp": "2017-09-25T20:31:36Z",
        "actor": "Klawiter",
        "textId": 32391,
        "blob": "zt_03",
        "characters": 16551,
        "sha256": "8c7c8b0be880c5cb49fe1b213f9979a124a7017d2b9282cb3b26be35380020d4",
    }


def test_reviewed_case_list() -> None:
    assert RESTORED == {35, 279, 793, 2816, 2817, 4248, 4428, 5839}
    assert WITHHELD == {670, 1868, 1931, 1934, 2129, 2252, 2270, 2284, 2328, 2329}
    assert DECISIONS["provenance"] == (
        "decided by the main instance after delegation by the operator on "
        "2026-09-23, revisable"
    )


def test_restored_pages_publish_their_human_revision(source_rows) -> None:
    rows = {int(row["page_id"]): row for row in source_rows}
    for page_id in RESTORED:
        human = BY_PAGE[page_id]["humanRevision"]
        row = rows[page_id]
        assert row["text_id"] == str(human["textId"])
        assert len(row["content"]) == human["characters"]
        assert not row["content"].lstrip().upper().startswith("#REDIRECT")
    for page_id in WITHHELD:
        fixer = BY_PAGE[page_id]["fixerRevisions"][-1]
        assert rows[page_id]["text_id"] == str(fixer["textId"])
        assert rows[page_id]["content"].startswith("#REDIRECT")


def test_withheld_redirects_resolve_no_reference() -> None:
    rows = [
        {"page_id": "1", "title": "Target", "page_title": "Target"},
        {
            "page_id": "670",
            "page_title": "Withheld alias",
            "title": "Target",
            "redirect_target": "Target",
            "is_redirect": True,
        },
        {
            "page_id": "5",
            "page_title": "Kept alias",
            "title": "Target",
            "redirect_target": "Target",
            "is_redirect": True,
        },
    ]
    targets = stage_05.build_reference_targets(rows)
    assert targets["Kept alias"] == 1
    assert "Withheld alias" not in targets


def test_withheld_redirects_stay_records_without_redirect_aliases(
    canonical_entries, frontend_data
) -> None:
    entries = {entry["sourcePageId"]: entry for entry in canonical_entries}
    for page_id in WITHHELD:
        assert entries[page_id]["isRedirect"] is True
        title = BY_PAGE[page_id]["pageTitle"]
        assert title not in frontend_data["redirects"]
    shown = {entry["sourcePageId"]: entry for entry in frontend_data["entries"]}
    for page_id in RESTORED:
        assert (
            shown[page_id]["sourceTextId"]
            == (BY_PAGE[page_id]["humanRevision"]["textId"])
        )


def test_maria_stuart_references_resolve_to_the_restored_page(
    canonical_entries, frontend_data
) -> None:
    """The 26 See-references to [[Maria Stuart]] reach page 35; none reaches
    page 4113, the target of the fixer redirect; page 6826 stays separate."""
    references = [
        (entry["sourcePageId"], relation["@id"])
        for entry in canonical_entries
        for relation in entry.get("relation") or []
    ]
    assert sum(target == "klawiter:entry/35" for _, target in references) == 26
    assert not [pair for pair in references if pair[1] == "klawiter:entry/4113"]
    named = [
        entry["sourcePageId"]
        for entry in frontend_data["entries"]
        if "Maria Stuart" in (entry.get("seeAlso") or [])
    ]
    assert len(named) == 26
    titles = {
        entry["sourcePageId"]: entry.get("title") for entry in frontend_data["entries"]
    }
    assert titles[35] == "Maria Stuart"
    assert titles[6826] == "Maria Stuart / Biography"
    assert "Maria Stuart" not in frontend_data["redirects"]


def test_withheld_cases_are_open_claims() -> None:
    from lib.config import OUTPUT_RECONCILIATION_DIR

    claims = json.loads(
        (Path(OUTPUT_RECONCILIATION_DIR) / "contested-claims.json").read_text(
            encoding="utf-8"
        )
    )["@graph"]
    revision_claims = {
        claim["klawiter:claimSubject"]["@id"]: claim
        for claim in claims
        if claim["klawiter:identityScope"] == "source-revision"
    }
    assert set(revision_claims) == {f"klawiter:entry/{pid}" for pid in WITHHELD}
    for page_id in WITHHELD:
        claim = revision_claims[f"klawiter:entry/{page_id}"]
        assert claim["klawiter:decisionStatus"] == "open"
        assert claim["klawiter:claimPredicate"] == {"@id": "klawiter:redirectTarget"}
        (evidence,) = claim["klawiter:sourceEvidence"]
        fixer = BY_PAGE[page_id]["fixerRevisions"][-1]
        assert evidence["sourcePageId"] == page_id
        assert evidence["sourceTextId"] == fixer["textId"]
        assert evidence["sourceValue"] == fixer["redirectText"]

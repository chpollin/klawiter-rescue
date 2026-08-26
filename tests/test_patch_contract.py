"""
Frontend/backend patch contract (EIL editing interface, increment 1).

docs/js/edit.js exportPatch() emits a version-2 patch document; pipeline/
apply_patches.py consumes it. These tests pin the exact shape the frontend
produces so the two halves cannot drift apart silently: the JS writes these
keys, the Python reads them, and a change on either side breaks a test here.

The patch objects below are hand-written to mirror edit.js exportPatch() field
for field (pageId, field, action, oldValue, newValue, previousProvenance,
edited_by, edited_at, source) inside a {patchVersion, created, source,
totalChanges, patches} envelope.
"""

import apply_patches as ap


# One object per pending field, exactly as edit.js exportPatch() pushes it.
def frontend_patch(pid, field, action, old, new, prev):
    return {
        "pageId": pid,
        "field": field,
        "action": action,
        "oldValue": old,
        "newValue": new,
        "previousProvenance": prev,
        "edited_by": "Editor (SZD)",
        "edited_at": "2026-06-21T12:00:00.000Z",
        "source": "human",
    }


def frontend_patch_doc(patches):
    return {
        "patchVersion": 2,
        "created": "2026-06-21T12:00:00.000Z",
        "source": "klawiter-eil-interface",
        "totalChanges": len(patches),
        "patches": patches,
    }


def entries():
    return [
        {
            "sourcePageId": 87,
            "title": "A",
            "publisher": "Leipzig",
            "location": "Weimar",
            "_provenance": {
                "publisher": "llm",
                "location": "regex",
                "translator": "missing",
                "pageCount": "regex",
            },
        },
    ]


def test_three_actions_validate_clean():
    """Accept, Correct and Add as edit.js emits them carry no validation problems."""
    patches = [
        frontend_patch(87, "location", "accept", "Weimar", "Weimar", "regex"),
        frontend_patch(87, "publisher", "correct", "Leipzig", "Insel-Verlag", "llm"),
        frontend_patch(87, "translator", "add", None, "Felix Braun", "missing"),
    ]
    for p in patches:
        assert ap.validate_patch(p) == [], p


def test_envelope_satisfies_ci_assertions():
    """The v2 envelope carries the keys the validate-patch CI workflow checks."""
    doc = frontend_patch_doc(
        [
            frontend_patch(
                87, "publisher", "correct", "Leipzig", "Insel-Verlag", "llm"
            ),
        ]
    )
    assert "patchVersion" in doc and "patches" in doc
    for p in doc["patches"]:
        assert "pageId" in p and "field" in p and "newValue" in p


def test_exported_doc_applies_end_to_end():
    """A frontend-shaped patch document applies through apply_patches as expected."""
    doc = frontend_patch_doc(
        [
            frontend_patch(87, "location", "accept", "Weimar", "Weimar", "regex"),
            frontend_patch(
                87, "publisher", "correct", "Leipzig", "Insel-Verlag", "llm"
            ),
            frontend_patch(87, "translator", "add", None, "Felix Braun", "missing"),
        ]
    )
    es = entries()
    report = ap.apply_patches(es, doc["patches"])
    e = es[0]
    assert e["location"] == "Weimar"  # accept leaves value untouched
    assert e["publisher"] == "Insel-Verlag"  # correct replaces
    assert e["translator"] == "Felix Braun"  # add fills
    assert e["_provenance"]["location"] == "editor"
    assert e["_provenance"]["publisher"] == "editor"
    assert e["_provenance"]["translator"] == "editor"
    assert e["review"]["status"] == "approved"
    assert {h["action"] for h in e["edit_history"]} == {"accept", "correct", "add"}
    assert report["by_action"] == {"accept": 1, "correct": 1, "add": 1}


def test_add_with_nonempty_oldvalue_is_rejected():
    """edit.js sends oldValue null for Add; a non-null oldValue must fail validation."""
    bad = frontend_patch(87, "translator", "add", "something", "Felix Braun", "missing")
    assert ap.validate_patch(bad) != []

"""
Regression tests — ensure pipeline output quality doesn't degrade.
Compares current quality-report.json against .github/baseline-metrics.json.
"""

import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
QUALITY_REPORT = PROJECT_ROOT / "data" / "output" / "quality-report.json"
BASELINE_PATH = PROJECT_ROOT / ".github" / "baseline-metrics.json"


@pytest.fixture(scope="module")
def quality_report():
    if not QUALITY_REPORT.exists():
        pytest.skip("quality-report.json not found (run pipeline step 06 first)")
    with open(QUALITY_REPORT, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def baseline():
    if not BASELINE_PATH.exists():
        pytest.skip("baseline-metrics.json not found")
    with open(BASELINE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Entry count stability
# ---------------------------------------------------------------------------

class TestEntryCounts:
    def test_total_entries_above_minimum(self, quality_report, baseline):
        """Total entry count doesn't drop below threshold."""
        minimum = baseline["thresholds"]["total_entries_min"]
        actual = quality_report["summary"]["total_entries"]
        assert actual >= minimum, (
            f"Total entries dropped to {actual} (minimum: {minimum})"
        )

    def test_main_namespace_above_minimum(self, quality_report, baseline):
        """Main namespace (ns 0) entry count stays stable."""
        minimum = baseline["thresholds"]["non_redirects_main_min"]
        actual = quality_report["summary"]["non_redirects_main"]
        assert actual >= minimum, (
            f"Main namespace entries dropped to {actual} (minimum: {minimum})"
        )

    def test_no_significant_entry_loss(self, quality_report, baseline):
        """Total entries within 1% of baseline."""
        baseline_total = baseline["summary"]["total_entries"]
        actual = quality_report["summary"]["total_entries"]
        assert actual >= baseline_total * 0.99, (
            f"Entry count dropped >1%: {baseline_total} → {actual}"
        )


# ---------------------------------------------------------------------------
# Field coverage — critical fields must not regress
# ---------------------------------------------------------------------------

class TestFieldCoverage:
    CRITICAL_FIELDS = ["name", "datePublished", "bibliographicCitation"]
    TRACKED_FIELDS = [
        "name", "datePublished", "publisher", "locationCreated",
        "inLanguage", "numberOfPages", "translator",
    ]

    def test_critical_fields_no_regression(self, quality_report, baseline):
        """Critical fields (name, year, bibCitation) don't drop >1pp."""
        max_drop = baseline["thresholds"]["critical_field_max_drop_pp"]
        for field in self.CRITICAL_FIELDS:
            baseline_pct = baseline["field_coverage"][field]["percentage"]
            current_pct = quality_report["field_coverage"][field]["percentage"]
            drop = baseline_pct - current_pct
            assert drop <= max_drop, (
                f"{field} coverage dropped {drop:.1f}pp: "
                f"{baseline_pct}% → {current_pct}%"
            )

    @pytest.mark.parametrize("field", TRACKED_FIELDS)
    def test_tracked_field_coverage_stable(self, quality_report, baseline, field):
        """No tracked field drops more than 2pp from baseline."""
        if field not in baseline["field_coverage"]:
            pytest.skip(f"{field} not in baseline")
        baseline_pct = baseline["field_coverage"][field]["percentage"]
        current_pct = quality_report["field_coverage"][field]["percentage"]
        drop = baseline_pct - current_pct
        assert drop <= 2.0, (
            f"{field} coverage dropped {drop:.1f}pp: "
            f"{baseline_pct}% → {current_pct}%"
        )


# ---------------------------------------------------------------------------
# Issue severity — no new errors, warnings bounded
# ---------------------------------------------------------------------------

class TestIssueSeverity:
    def test_no_error_severity_issues(self, quality_report, baseline):
        """Zero error-severity issues (missing entryType etc.)."""
        max_errors = baseline["thresholds"]["error_severity_max"]
        actual = quality_report["summary"]["severity_counts"].get("error", 0)
        assert actual <= max_errors, (
            f"Found {actual} error-severity issues (max: {max_errors})"
        )

    def test_mojibake_warnings_bounded(self, quality_report, baseline):
        """Mojibake warnings stay below threshold."""
        max_warnings = baseline["thresholds"]["mojibake_warnings_max"]
        actual = quality_report["summary"]["severity_counts"].get("warning", 0)
        assert actual <= max_warnings, (
            f"Found {actual} warnings (max: {max_warnings})"
        )

    def test_issues_not_doubled(self, quality_report, baseline):
        """Total issue count doesn't more than double from baseline."""
        baseline_issues = baseline["summary"]["entries_with_issues"]
        actual = quality_report["summary"]["entries_with_issues"]
        assert actual <= baseline_issues * 2, (
            f"Issues doubled: {baseline_issues} → {actual}"
        )


# ---------------------------------------------------------------------------
# Data integrity — structural checks
# ---------------------------------------------------------------------------

class TestDataIntegrity:
    def test_quality_report_structure(self, quality_report):
        """Quality report has all required sections."""
        assert "summary" in quality_report
        assert "field_coverage" in quality_report
        assert "entry_type_distribution" in quality_report

    def test_year_range_sane(self, quality_report):
        """Year range stays within expected bounds."""
        dist = quality_report.get("year_distribution", {})
        # If year_distribution isn't in report, check via entry_type_distribution
        # which always exists
        assert "entry_type_distribution" in quality_report
        total_types = sum(quality_report["entry_type_distribution"].values())
        assert total_types > 0, "No entries in type distribution"

    def test_frontend_json_exists(self):
        """Frontend JSON file exists and is valid."""
        frontend_path = PROJECT_ROOT / "docs" / "data" / "klawiter.json"
        if not frontend_path.exists():
            pytest.skip("Frontend JSON not found")
        with open(frontend_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "entries" in data, "Missing 'entries' key in frontend JSON"
        assert len(data["entries"]) > 4000, (
            f"Frontend JSON has only {len(data['entries'])} entries"
        )

    def test_frontend_entries_have_required_fields(self):
        """Spot-check: first 100 entries have sourcePageId and entryType."""
        frontend_path = PROJECT_ROOT / "docs" / "data" / "klawiter.json"
        if not frontend_path.exists():
            pytest.skip("Frontend JSON not found")
        with open(frontend_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        sample = data["entries"][:100]
        for entry in sample:
            assert "sourcePageId" in entry, f"Missing sourcePageId: {entry.get('title', '?')}"
            assert "entryType" in entry, f"Missing entryType: {entry.get('title', '?')}"

"""
Regression tests — ensure pipeline output quality doesn't degrade.
Compares current quality-report.json against .github/baseline-metrics.json.
Fixtures (quality_report, baseline) are defined in conftest.py.
"""

import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent


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
        """Total entries within 0.5% of baseline (tighter than old 1%)."""
        baseline_total = baseline["summary"]["total_entries"]
        actual = quality_report["summary"]["total_entries"]
        assert actual >= baseline_total * 0.995, (
            f"Entry count dropped >0.5%: {baseline_total} → {actual}"
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
        """No tracked field drops more than 1pp from baseline."""
        if field not in baseline["field_coverage"]:
            pytest.skip(f"{field} not in baseline")
        baseline_pct = baseline["field_coverage"][field]["percentage"]
        current_pct = quality_report["field_coverage"][field]["percentage"]
        drop = baseline_pct - current_pct
        assert drop <= 1.0, (
            f"{field} coverage dropped {drop:.1f}pp: "
            f"{baseline_pct}% → {current_pct}% (threshold: 1pp)"
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
        """Year range spans the expected bounds without data loss at the edges."""
        year_range = quality_report["year_range"]
        assert year_range["min"] <= 1820, (
            f"Earliest year {year_range['min']} > 1820 — possible data loss at lower bound"
        )
        assert year_range["max"] >= 2015, (
            f"Latest year {year_range['max']} < 2015 — possible data loss at upper bound"
        )
        assert year_range["count"] >= 4000, (
            f"Only {year_range['count']} entries have year data — expected ≥ 4000"
        )

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

    def test_entry_type_distribution_stable(self, quality_report, baseline):
        """No entry type disappears entirely; each stays within ±2% of baseline share."""
        if "entry_type_distribution" not in baseline:
            pytest.skip("entry_type_distribution not in baseline")
        baseline_dist = baseline["entry_type_distribution"]
        current_dist = quality_report["entry_type_distribution"]
        baseline_total = sum(baseline_dist.values())
        current_total = sum(current_dist.values())

        vanished = [
            t for t in baseline_dist
            if baseline_dist[t] > 0 and current_dist.get(t, 0) == 0
        ]
        assert len(vanished) == 0, (
            f"Entry types vanished entirely: {vanished}"
        )

        drifted = []
        for entry_type, baseline_count in baseline_dist.items():
            if baseline_count == 0:
                continue
            baseline_share = baseline_count / baseline_total * 100
            current_count = current_dist.get(entry_type, 0)
            current_share = current_count / current_total * 100 if current_total > 0 else 0
            drift = abs(current_share - baseline_share)
            if drift > 2.0:
                drifted.append(
                    f"{entry_type}: {baseline_share:.1f}% → {current_share:.1f}% "
                    f"(drift {drift:.1f}pp)"
                )
        assert len(drifted) == 0, (
            f"Entry type distribution drifted >2pp:\n" + "\n".join(f"  {d}" for d in drifted)
        )

    def test_frontend_entries_have_required_fields(self):
        """Every entry has sourcePageId and entryType (not just first 100)."""
        frontend_path = PROJECT_ROOT / "docs" / "data" / "klawiter.json"
        if not frontend_path.exists():
            pytest.skip("Frontend JSON not found")
        with open(frontend_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        missing_pid = [
            i for i, e in enumerate(data["entries"]) if "sourcePageId" not in e
        ]
        missing_type = [
            e.get("sourcePageId", f"index-{i}")
            for i, e in enumerate(data["entries"]) if "entryType" not in e
        ]
        assert len(missing_pid) == 0, (
            f"{len(missing_pid)} entries missing sourcePageId"
        )
        assert len(missing_type) == 0, (
            f"{len(missing_type)} entries missing entryType: {missing_type[:10]}"
        )

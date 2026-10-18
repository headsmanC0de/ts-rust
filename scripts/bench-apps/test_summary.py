"""CLI oracles for effective benchmark provenance and all-or-nothing output."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SUMMARY = Path(__file__).with_name("summary.py")
CASE = "vscode"
LATER_CASE = "sentry"
TOOLS = ("tsc6", "tsc7", "tsc-rs", "tsc-rs-fast", "bun")
RUST = "tsc-rs"
FAST = "tsc-rs-fast"
ORACLE = "tsc7"
ERROR = "src/app.ts(2,3): error TS2322: Type mismatch.\n"
EFFECT = "src/app.ts(4,3): warning TS377001: Effect warning.\n"
T3_PROJECTS = (
    "apps-server",
    "apps-web",
    "apps-mobile",
    "packages-client-runtime",
    "packages-shared",
)


class SummaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.results = self.work / "results"
        self.results.mkdir()

    def artifact(self, stem, tools=TOOLS, output="", code=0, median=1):
        rows = []
        timings = []
        for tool in tools:
            (self.results / f"{stem}.{tool}.stdout").write_text(output)
            (self.results / f"{stem}.{tool}.stderr").write_text("")
            rows.append(f"{tool} rc={code} errors={output.count('error TS')}\n")
            timings.append({"command": tool, "median": median, "exit_codes": [code]})
        (self.results / f"{stem}.errors").write_text("".join(rows))
        (self.results / f"{stem}.json").write_text(json.dumps({"results": timings}))

    def run_summary(self):
        return subprocess.run(
            [sys.executable, str(SUMMARY), str(self.work)],
            capture_output=True,
            text=True,
            timeout=5,
        )

    def withheld(self, result):
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertNotIn("Traceback", result.stderr)

    def test_derived_ratio_failure_withholds_every_byte(self):
        self.artifact(CASE)
        p = self.results / f"{CASE}.json"
        data = json.loads(p.read_text())
        for result in data["results"]:
            if result["command"] == ORACLE:
                result["median"] = 1e-300
            elif result["command"] == RUST:
                result["median"] = 1e300
        p.write_text(json.dumps(data))
        self.withheld(self.run_summary())

    def test_overflowed_t3_totals_cannot_publish_infinity(self):
        for project in T3_PROJECTS:
            self.artifact(f"t3-{project}-effect", median=1e308)
        self.withheld(self.run_summary())

    def test_t3_only_report_explicitly_scopes_rust_and_other_tools(self):
        for project in T3_PROJECTS:
            self.artifact(f"t3-{project}-effect")
        result = self.run_summary()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Rust columns:", result.stdout)
        self.assertIn("other columns: timings only", result.stdout)

    def test_partial_t3_group_cannot_succeed_with_no_table(self):
        self.artifact("t3-" + T3_PROJECTS[0] + "-effect")
        self.withheld(self.run_summary())

    def test_effect_table_filters_plain_records_but_requires_effect_parity(self):
        for project in T3_PROJECTS:
            stem = f"t3-{project}-effect"
            self.artifact(stem, output=ERROR + EFFECT, code=2)
            (self.results / f"{stem}.{ORACLE}.stdout").write_text(
                ERROR.replace("TS2322", "TS9999") + EFFECT
            )
        result = self.run_summary()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("T3 Code effect", result.stdout)
        stem = f"t3-{T3_PROJECTS[-1]}-effect"
        (self.results / f"{stem}.{FAST}.stdout").write_text(ERROR)
        self.withheld(self.run_summary())

    def test_effect_table_preserves_exact_exit_contract(self):
        for project in T3_PROJECTS:
            stem = f"t3-{project}-effect"
            self.artifact(stem, output=EFFECT, code=2)
        self.artifact(
            f"t3-{T3_PROJECTS[0]}-effect.{FAST}", (FAST,), output=EFFECT, code=1
        )
        self.withheld(self.run_summary())

    def test_no_results_cannot_be_a_successful_report(self):
        self.withheld(self.run_summary())

    def test_unselected_receipt_content_is_never_printed(self):
        self.artifact(CASE)
        self.artifact(CASE + ".a", (RUST,))
        self.artifact(CASE + ".z", (RUST,))
        marker = "PRIVATE_RECEIPT_MARKER"
        (self.results / f"{CASE}.a.errors").write_text(marker)
        result = self.run_summary()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(marker, result.stdout + result.stderr)

    def test_failed_timed_iteration_cannot_use_successful_preflight(self):
        self.artifact(CASE)
        p = self.results / f"{CASE}.json"
        data = json.loads(p.read_text())
        next(r for r in data["results"] if r["command"] == RUST)["exit_codes"] = [139]
        p.write_text(json.dumps(data))
        self.withheld(self.run_summary())

    def test_missing_timed_iteration_status_is_rejected(self):
        self.artifact(CASE)
        p = self.results / f"{CASE}.json"
        data = json.loads(p.read_text())
        next(r for r in data["results"] if r["command"] == FAST).pop("exit_codes")
        p.write_text(json.dumps(data))
        self.withheld(self.run_summary())

    def test_full_equal_normal_and_fast_evidence_publishes(self):
        self.artifact(CASE)
        result = self.run_summary()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("| vscode |", result.stdout)

    def test_valid_normal_overlay_publishes_its_selected_median(self):
        self.artifact(CASE)
        self.artifact(CASE + "." + RUST, (RUST,), median=0.01)
        result = self.run_summary()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("0.01s", result.stdout)

    def test_crashed_normal_overlay_withholds_entire_table(self):
        self.artifact(CASE)
        self.artifact(CASE + "." + RUST, (RUST,), code=139, median=0.01)
        self.withheld(self.run_summary())

    def test_normal_overlay_diagnostic_loss_withholds_table(self):
        self.artifact(CASE, output=ERROR, code=2)
        self.artifact(CASE + "." + RUST, (RUST,))
        self.withheld(self.run_summary())

    def test_fast_diagnostic_loss_is_separately_rejected(self):
        self.artifact(CASE, output=ERROR, code=2)
        (self.results / f"{CASE}.{FAST}.stdout").write_text("")
        result = self.run_summary()
        self.withheld(result)
        self.assertIn(FAST, result.stderr)

    def test_selected_oracle_overlay_is_used_for_negative_comparison(self):
        self.artifact(CASE)
        self.artifact(CASE + "." + ORACLE, (ORACLE,), output=ERROR, code=2)
        self.withheld(self.run_summary())

    def test_matching_rust_and_oracle_overlays_publish(self):
        self.artifact(CASE)
        self.artifact(CASE + "." + ORACLE, (ORACLE,), output=ERROR, code=2)
        self.artifact(CASE + "." + RUST, (RUST,), output=ERROR, code=2)
        self.artifact(CASE + "." + FAST, (FAST,), output=ERROR, code=2)
        result = self.run_summary()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_overlay_receipt_cannot_use_base_receipt(self):
        self.artifact(CASE)
        stem = CASE + "." + RUST
        self.artifact(stem, (RUST,))
        (self.results / f"{stem}.errors").unlink()
        self.withheld(self.run_summary())

    def test_missing_overlay_stream_cannot_use_base_stream(self):
        self.artifact(CASE)
        stem = CASE + "." + RUST
        self.artifact(stem, (RUST,))
        (self.results / f"{stem}.{RUST}.stderr").unlink()
        self.withheld(self.run_summary())

    def test_superseded_bad_overlay_is_not_the_effective_source(self):
        self.artifact(CASE)
        self.artifact(CASE + ".a", (RUST,), code=139)
        self.artifact(CASE + ".z", (RUST,))
        result = self.run_summary()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_later_invalid_case_leaks_no_earlier_rows(self):
        self.artifact(CASE)
        self.artifact(LATER_CASE, code=139)
        self.withheld(self.run_summary())

    def test_malformed_timing_file_fails_without_traceback(self):
        self.artifact(CASE)
        (self.results / f"{CASE}.json").write_text("invalid")
        self.withheld(self.run_summary())

    def test_nonpositive_median_fails_without_traceback(self):
        self.artifact(CASE, median=0)
        self.withheld(self.run_summary())

    def test_huge_integer_median_fails_without_traceback(self):
        self.artifact(CASE, median=10**1000)
        self.withheld(self.run_summary())

    def test_nonfinite_median_fails_without_traceback(self):
        self.artifact(CASE, median=float("nan"))
        self.withheld(self.run_summary())

    def test_missing_published_tool_fails_without_traceback(self):
        self.artifact(CASE, tools=TOOLS[:-1])
        self.withheld(self.run_summary())


if __name__ == "__main__":
    unittest.main()

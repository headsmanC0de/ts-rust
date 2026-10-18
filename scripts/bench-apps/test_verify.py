"""Behavioral CLI tests for benchmark differential admission."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lineage_fixtures import bind_fixtures

VERIFIER = Path(__file__).with_name("verify.py")
CASE = "vscode"
TOOLS = ("tsc-rs", "tsc7")
ERROR = "src/app.ts(2,3): error TS2322: Type 'string' is not assignable.\n"
EFFECT_CASE = "t3-apps-server-effect"
EFFECT = "src/app.ts(2,3): warning TS377001: Effect warning.\n"


class VerifyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.results = self.work / "results"
        self.results.mkdir()

    def write_case(self, outputs=("", ""), codes=(0, 0), stem=CASE):
        for tool, output in zip(TOOLS, outputs):
            (self.results / f"{stem}.{tool}.stdout").write_text(output)
            (self.results / f"{stem}.{tool}.stderr").write_text("")
        (self.results / f"{stem}.errors").write_text(
            "".join(f"{tool} rc={code} errors=0\n" for tool, code in zip(TOOLS, codes))
        )

    def run_case(self, stem=CASE):
        bind_fixtures(self.results)
        return subprocess.run(
            [sys.executable, str(VERIFIER), str(self.work), "--case", stem],
            capture_output=True,
            text=True,
            timeout=5,
        )

    def assert_rejected(self, result):
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("MATCH", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_accepts_successful_empty_diagnostics(self):
        self.write_case()
        result = self.run_case()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("MATCH", result.stdout)

    def test_accepts_equal_complete_multiline_diagnostics(self):
        diagnostic = ERROR + "  Nested reason\n    Further detail\n"
        self.write_case((diagnostic, diagnostic), (1, 1))
        self.assertEqual(self.run_case().returncode, 0)

    def test_rejects_equal_diagnostics_with_different_exit_codes(self):
        self.write_case((ERROR, ERROR), (1, 2))
        self.assert_rejected(self.run_case())

    def test_rejects_equal_empty_diagnostics_after_crash(self):
        self.write_case(codes=(139, 139))
        self.assert_rejected(self.run_case())

    def test_rejects_failed_run_without_diagnostics(self):
        self.write_case(codes=(1, 1))
        self.assert_rejected(self.run_case())

    def test_rejects_missing_process_receipt(self):
        self.write_case()
        (self.results / f"{CASE}.errors").unlink()
        self.assert_rejected(self.run_case())

    def test_rejects_duplicate_process_receipt(self):
        self.write_case()
        with (self.results / f"{CASE}.errors").open("a") as output:
            output.write("tsc-rs rc=0 errors=0\n")
        self.assert_rejected(self.run_case())

    def test_rejects_malformed_process_receipt(self):
        self.write_case()
        (self.results / f"{CASE}.errors").write_text("tsc-rs rc=unknown errors=0\n")
        self.assert_rejected(self.run_case())

    def test_rejects_missing_tool_process_receipt(self):
        self.write_case()
        (self.results / f"{CASE}.errors").write_text("tsc-rs rc=0 errors=0\n")
        self.assert_rejected(self.run_case())

    def test_rejects_missing_output_without_traceback(self):
        self.write_case()
        (self.results / f"{CASE}.tsc7.stderr").unlink()
        self.assert_rejected(self.run_case())

    def test_rejects_changed_nested_message(self):
        self.write_case((ERROR + "  Expected A\n", ERROR + "  Expected B\n"), (1, 1))
        self.assert_rejected(self.run_case())

    def test_rejects_changed_location(self):
        self.write_case((ERROR, ERROR.replace("(2,3)", "(2,4)")), (1, 1))
        self.assert_rejected(self.run_case())

    def test_rejects_changed_severity(self):
        self.write_case((ERROR, ERROR.replace("error TS", "warning TS")), (1, 1))
        self.assert_rejected(self.run_case())

    def test_rejects_missing_duplicate_diagnostic(self):
        self.write_case((ERROR + ERROR, ERROR), (1, 1))
        self.assert_rejected(self.run_case())

    def test_accepts_reordered_records_across_streams(self):
        self.write_case((ERROR, ""), (1, 1))
        (self.results / f"{CASE}.tsc7.stderr").write_text(ERROR)
        self.assertEqual(self.run_case().returncode, 0)

    def test_effect_mode_filters_plain_diagnostics_but_preserves_exit_contract(self):
        self.write_case((ERROR + EFFECT, EFFECT), (1, 1), EFFECT_CASE)
        self.assertEqual(self.run_case(EFFECT_CASE).returncode, 0)
        self.write_case((ERROR + EFFECT, EFFECT), (1, 2), EFFECT_CASE)
        self.assert_rejected(self.run_case(EFFECT_CASE))

    def test_effect_mode_allows_plain_error_with_no_effect_records(self):
        self.write_case((ERROR, ERROR), (1, 1), EFFECT_CASE)
        self.assertEqual(self.run_case(EFFECT_CASE).returncode, 0)

    def test_rejects_changed_nested_message_after_blank_line(self):
        self.write_case(
            (
                ERROR + "  First cause\n\n    Expected A\n",
                ERROR + "  First cause\n\n    Expected B\n",
            ),
            (1, 1),
        )
        self.assert_rejected(self.run_case())

    def test_accepts_equal_nested_paragraphs_and_ignores_trailing_blanks(self):
        diagnostic = ERROR + "  First cause\n\n    Shared detail\n"
        self.write_case((diagnostic + "\n", diagnostic), (1, 1))
        self.assertEqual(self.run_case().returncode, 0)

    def test_rejects_unknown_output_even_with_diagnostics(self):
        self.write_case(
            (ERROR + "compiler aborted\n", ERROR + "compiler aborted\n"), (2, 2)
        )
        self.assert_rejected(self.run_case())

    def test_rejects_panic_even_with_equal_diagnostics_and_normal_numeric_exit(self):
        self.write_case((ERROR, ERROR), (2, 2))
        for tool in TOOLS:
            (self.results / f"{CASE}.{tool}.stderr").write_text(
                "panic: compiler failed\n"
            )
        self.assert_rejected(self.run_case())

    def test_rejects_unported_even_with_equal_diagnostics(self):
        self.write_case((ERROR, ERROR), (2, 2))
        (self.results / f"{CASE}.tsc-rs.stderr").write_text(
            "unported checker operation\n"
        )
        self.assert_rejected(self.run_case())

    def test_rejects_unrecognized_nonempty_output(self):
        self.write_case(("compiler crashed\n", "compiler crashed\n"))
        self.assert_rejected(self.run_case())


if __name__ == "__main__":
    unittest.main()

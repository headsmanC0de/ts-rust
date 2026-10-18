"""Behaviour contracts for the fast fork quality entrypoint."""

import contextlib
import importlib.util
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ENTRY = Path(__file__).with_name("quality.py")


class QualityTests(unittest.TestCase):
    def load_quality(self):
        self.assertTrue(ENTRY.is_file(), "Missing quality entrypoint")
        spec = importlib.util.spec_from_file_location("fork_quality", ENTRY)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def invoke(self, module, args=(), results=()):
        versions = module.locked_versions(module.REQUIREMENTS)
        completed = [subprocess.CompletedProcess([], code) for code in results]
        with (
            mock.patch.object(
                module.metadata, "version", side_effect=versions.__getitem__
            ),
            mock.patch.object(module.subprocess, "run", side_effect=completed) as child,
        ):
            status = module.main(list(args))
        return status, child

    def test_exact_versions_come_from_the_requirements_file(self):
        module = self.load_quality()
        with tempfile.TemporaryDirectory() as directory:
            requirements = Path(directory) / "requirements.txt"
            requirements.write_text(
                "# comment\nExample==1.2.3 --hash=sha256:" + "a" * 64 + "\n"
            )
            self.assertEqual(module.locked_versions(requirements), {"Example": "1.2.3"})

    def test_unpinned_dependency_is_rejected(self):
        module = self.load_quality()
        with tempfile.TemporaryDirectory() as directory:
            requirements = Path(directory) / "requirements.txt"
            requirements.write_text("Example>=1.2\n")
            with self.assertRaises(ValueError):
                module.locked_versions(requirements)

    def test_default_runs_check_format_check_then_tests(self):
        module = self.load_quality()
        status, child = self.invoke(module, results=(0, 0, 0))
        self.assertEqual(status, 0)
        commands = [call.args[0] for call in child.call_args_list]
        self.assertEqual(
            commands[0], [sys.executable, "-m", "ruff", "check", "scripts/fork-ci"]
        )
        self.assertEqual(
            commands[1],
            [sys.executable, "-m", "ruff", "format", "--check", "scripts/fork-ci"],
        )
        self.assertEqual(
            commands[2],
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "scripts/fork-ci",
                "-p",
                "test_*.py",
                "-v",
            ],
        )
        self.assertTrue(
            all(call.kwargs["cwd"] == module.ROOT for call in child.call_args_list)
        )

    def test_explicit_format_runs_formatter_before_checks(self):
        module = self.load_quality()
        status, child = self.invoke(module, args=("--format",), results=(0, 0, 0, 0))
        self.assertEqual(status, 0)
        self.assertEqual(
            child.call_args_list[0].args[0],
            [sys.executable, "-m", "ruff", "format", "scripts/fork-ci"],
        )
        self.assertEqual(child.call_count, 4)

    def test_first_lint_failure_stops_before_format_and_tests(self):
        module = self.load_quality()
        status, child = self.invoke(module, results=(7,))
        self.assertEqual(status, 7)
        self.assertEqual(child.call_count, 1)

    def test_format_failure_stops_before_tests(self):
        module = self.load_quality()
        status, child = self.invoke(module, results=(0, 3))
        self.assertEqual(status, 3)
        self.assertEqual(child.call_count, 2)

    def test_test_failure_is_returned(self):
        module = self.load_quality()
        status, child = self.invoke(module, results=(0, 0, 4))
        self.assertEqual(status, 4)
        self.assertEqual(child.call_count, 3)

    def test_missing_dependency_fails_before_child_tools(self):
        module = self.load_quality()
        with (
            mock.patch.object(
                module.metadata,
                "version",
                side_effect=module.metadata.PackageNotFoundError("ruff"),
            ),
            mock.patch.object(module.subprocess, "run") as child,
            contextlib.redirect_stderr(io.StringIO()) as error,
        ):
            self.assertEqual(module.main([]), 2)
        self.assertIn("missing", error.getvalue().lower())
        child.assert_not_called()

    def test_wrong_dependency_version_fails_before_child_tools(self):
        module = self.load_quality()
        with (
            mock.patch.object(module.metadata, "version", return_value="0.0.0"),
            mock.patch.object(module.subprocess, "run") as child,
            contextlib.redirect_stderr(io.StringIO()) as error,
        ):
            self.assertEqual(module.main([]), 2)
        self.assertIn("version", error.getvalue().lower())
        child.assert_not_called()

    def test_real_entry_fails_closed_without_site_packages(self):
        self.load_quality()
        completed = subprocess.run(
            [sys.executable, "-S", str(ENTRY)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("missing", completed.stderr.lower())
        self.assertNotIn("Traceback", completed.stderr)


if __name__ == "__main__":
    unittest.main()

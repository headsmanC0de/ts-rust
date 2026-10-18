"""Dependency admission uses the real owning requirements and metadata adapter."""

import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import dependency_lock as lock


class DependencyLockTests(unittest.TestCase):
    def requirements(self, source):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path = Path(folder.name) / "requirements.txt"
        path.write_text(source)
        return path

    def test_exact_versions_come_from_hash_locked_owner(self):
        path = self.requirements(
            "# comment\nExample==1.2.3 --hash=sha256:" + "a" * 64 + "\n"
        )
        self.assertEqual(lock.locked_versions(path), {"Example": "1.2.3"})

    def test_rejects_unpinned_empty_malformed_duplicate_aliases(self):
        pin = "Example==1.2.3 --hash=sha256:" + "a" * 64 + "\n"
        for source in [
            "",
            "# only comment\n",
            "Example>=1.2\n",
            pin + pin,
            pin + pin.replace("Example", "example"),
            "secret://password",
        ]:
            with self.subTest(source=source):
                with self.assertRaises(ValueError):
                    lock.locked_versions(self.requirements(source))

    def test_current_installed_versions_are_admitted_without_tools(self):
        versions = lock.locked_versions(lock.REQUIREMENTS)
        with patch.object(lock.metadata, "version", side_effect=versions.__getitem__):
            self.assertEqual(lock.main([]), 0)

    def test_missing_wrong_version_and_invalid_owner_are_redacted(self):
        for error in [
            lock.metadata.PackageNotFoundError("secret://password"),
            "private-version",
        ]:
            with (
                patch.object(
                    lock.metadata,
                    "version",
                    side_effect=error if isinstance(error, Exception) else None,
                    return_value=error,
                ),
                contextlib.redirect_stderr(io.StringIO()) as output,
            ):
                self.assertEqual(lock.main([]), 2)
            self.assertNotIn("secret", output.getvalue())
            self.assertNotIn("private", output.getvalue())
            self.assertIn("dependency", output.getvalue())
        with (
            patch.object(lock, "REQUIREMENTS", self.requirements("secret://password")),
            contextlib.redirect_stderr(io.StringIO()) as output,
        ):
            self.assertEqual(lock.main([]), 2)
        self.assertNotIn("secret", output.getvalue())

    def test_no_format_or_quality_runner_interface(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(lock.main(["--format"]), 2)

    def test_real_entry_fails_closed_without_site_packages(self):
        result = subprocess.run(
            [sys.executable, "-S", str(Path(lock.__file__))],
            capture_output=True,
            text=True,
            timeout=5,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("missing_dependency", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()

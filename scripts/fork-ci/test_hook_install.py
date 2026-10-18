import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

INSTALLER = Path(__file__).resolve().parents[1] / "git-hooks" / "install.sh"
SOURCE_HOOK = INSTALLER.with_name("pre-push")


class HookInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="hook install fixtures ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = {
            **{
                key: value
                for key, value in os.environ.items()
                if not key.startswith("GIT_")
            },
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
        }
        self.repo = self.root / "main checkout"
        self.repo.mkdir()
        self.git("init", "--quiet")
        self.git("config", "user.name", "Fixture identity")
        self.git("config", "user.email", "fixture@example.invalid")
        self.before_identity = self.git("config", "--local", "--list").stdout
        self.hook = self.repo / ".git" / "hooks" / "pre-push"

    def git(self, *args, cwd=None):
        return subprocess.run(
            ["git", *args],
            cwd=cwd or self.repo,
            env=self.env,
            capture_output=True,
            check=True,
        )

    def install(self, *args, cwd=None):
        return subprocess.run(
            ["bash", str(INSTALLER), *args],
            cwd=cwd or self.repo,
            env=self.env,
            capture_output=True,
        )

    def assert_identity_preserved(self):
        actual = self.git("config", "--local", "--list").stdout
        self.assertTrue(actual == self.before_identity, "local identity/config changed")

    def test_installs_guard_without_mutating_or_printing_identity(self):
        result = self.install()
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self.hook.read_bytes(), SOURCE_HOOK.read_bytes())
        self.assertTrue(os.access(self.hook, os.X_OK))
        self.assert_identity_preserved()
        identity = self.git("config", "user.email").stdout.strip()
        self.assertNotIn(identity, result.stdout + result.stderr)

    def test_refuses_foreign_hook_without_changing_bytes_or_identity(self):
        foreign = b"#!/bin/sh\nprintf 'owned elsewhere'\n"
        self.hook.write_bytes(foreign)
        self.hook.chmod(0o755)
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.hook.read_bytes(), foreign)
        self.assert_identity_preserved()

    def test_matching_hook_is_idempotent(self):
        shutil.copyfile(SOURCE_HOOK, self.hook)
        self.hook.chmod(0o755)
        before = self.hook.stat()
        result = self.install()
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self.hook.read_bytes(), SOURCE_HOOK.read_bytes())
        self.assertEqual(self.hook.stat().st_mtime_ns, before.st_mtime_ns)
        self.assert_identity_preserved()

    def test_linked_worktree_uses_shared_hooks_with_space_paths(self):
        self.git("commit", "--quiet", "--allow-empty", "-m", "fixture")
        worktree = self.root / "linked checkout"
        self.git("worktree", "add", "--quiet", "-b", "fixture-linked", str(worktree))
        result = self.install(cwd=worktree)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self.hook.read_bytes(), SOURCE_HOOK.read_bytes())
        self.assertTrue((worktree / ".git").is_file())
        self.assert_identity_preserved()

    def test_help_succeeds_without_git_repository(self):
        result = self.install("--help", cwd=self.root)
        self.assertEqual(result.returncode, 0)
        self.assertIn(b"usage:", result.stdout.lower())
        self.assertFalse(self.hook.exists())

    def test_inherited_git_context_cannot_mutate_outer_repository(self):
        local_vars = (
            subprocess.run(
                ["git", "rev-parse", "--local-env-vars"],
                cwd=self.root,
                env=self.env,
                capture_output=True,
                check=True,
            )
            .stdout.decode()
            .splitlines()
        )
        clean_env = {
            key: value for key, value in self.env.items() if key not in local_vars
        }
        outer = self.root / "outer repository"
        outer.mkdir()

        def outer_git(*args):
            return subprocess.run(
                ["git", *args],
                cwd=outer,
                env=clean_env,
                capture_output=True,
                check=True,
            )

        outer_git("init", "--quiet")
        outer_git("config", "user.name", "Outer fixture")
        outer_git("config", "user.email", "outer@example.invalid")
        (outer / "tracked").write_text("outer input")
        outer_git("add", "tracked")
        outer_git("commit", "--quiet", "-m", "outer fixture")
        hook = outer / ".git" / "hooks" / "pre-push"
        hook.write_bytes(b"outer guard\n")
        paths = [
            outer / ".git" / name
            for name in ["HEAD", "config", "index", "refs/heads", "worktrees", "logs"]
        ]
        paths.append(outer / ".git" / "hooks")

        def snapshot():
            files = [
                file
                for path in paths
                for file in (path.rglob("*") if path.is_dir() else [path])
                if file.is_file()
            ]
            return {
                str(file.relative_to(outer)): hashlib.sha256(
                    file.read_bytes()
                ).hexdigest()
                for file in files
            }

        before = snapshot()
        polluted = {
            **clean_env,
            "GIT_DIR": str(outer / ".git"),
            "GIT_COMMON_DIR": str(outer / ".git"),
            "GIT_WORK_TREE": str(outer),
            "GIT_INDEX_FILE": str(outer / ".git" / "index"),
        }
        child = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                *[
                    "HookInstallTests." + name
                    for name in unittest.defaultTestLoader.getTestCaseNames(
                        HookInstallTests
                    )
                    if name != self._testMethodName
                ],
            ],
            cwd=self.root,
            env=polluted,
            capture_output=True,
            timeout=15,
        )
        self.assertTrue(
            snapshot() == before, "inherited Git context changed outer repository"
        )
        self.assertEqual(child.returncode, 0, "isolated child fixture suite failed")

    def test_refuses_symlink_hook_without_modifying_target(self):
        target = self.root / "foreign guard"
        target.write_bytes(b"foreign hook\n")
        self.hook.symlink_to(target)
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(target.read_bytes(), b"foreign hook\n")
        self.assertTrue(self.hook.is_symlink())
        self.assert_identity_preserved()


if __name__ == "__main__":
    unittest.main()

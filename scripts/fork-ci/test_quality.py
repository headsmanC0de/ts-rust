"""Executable oracles for style, security, hook dispatch and scoped rule discovery."""

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts/fork-ci/quality.sh"
RULE_FILES = (
    "AGENTS.md",
    "search-rules.md",
    "tests.md",
    "security.md",
    "cybersecurity.md",
    "design.md",
    "guards.md",
    "lefthook.yml",
)
MAX_SOURCE_LINES = 500
MAX_ENTRYPOINT_LINES = 40
COMMAND_TIMEOUT = 5


class QualityTests(unittest.TestCase):
    def ruff(self, source, action="check"):
        args = [
            sys.executable,
            "-m",
            "ruff",
            action,
            "--no-cache",
            "--config",
            str(ROOT / "ruff.toml"),
            "--stdin-filename",
            "scripts/fork-ci/probe.py",
        ]
        if action == "format":
            args.append("--check")
        return subprocess.run(
            args,
            input=source,
            text=True,
            capture_output=True,
            cwd=ROOT,
            timeout=COMMAND_TIMEOUT,
        )

    def test_linter_rejects_undefined_names(self):
        result = self.ruff("print(undefined_name)\n")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("F821", result.stdout)

    def test_linter_rejects_shell_execution_and_eval(self):
        cases = [
            ("import subprocess\nsubprocess.run('echo test', shell=True)\n", "S602"),
            ("value = eval('1 + 1')\n", "S307"),
        ]
        for source, rule in cases:
            with self.subTest(rule=rule):
                result = self.ruff(source)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(rule, result.stdout)

    def test_linter_rejects_silent_exception_swallowing(self):
        result = self.ruff("try:\n    print('work')\nexcept Exception:\n    pass\n")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("S110", result.stdout)

    def test_safe_vector_execution_is_allowed(self):
        result = self.ruff(
            "import subprocess\nsubprocess.run(['tool', '--version'], check=True)\n"
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_formatter_checks_without_mutating_source(self):
        self.assertNotEqual(self.ruff("answer= 42\n", action="format").returncode, 0)
        self.assertEqual(self.ruff("answer = 42\n", action="format").returncode, 0)

    def dispatch(self, fail=False, darwin=False, timed_out=False, runner_source=None):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            child_log = folder / "children"
            interpreter = folder / "interpreter"
            interpreter.write_text(
                "#!" + sys.executable + "\n"
                "import json, os, pathlib, sys\n"
                "with pathlib.Path(os.environ['CHILD_LOG']).open('a') as log:\n"
                "    log.write(json.dumps(sys.argv[1:]) + '\\n')\n"
                "sys.exit(17 if os.environ.get('FAIL_CHILD') == '1' else 0)\n"
            )
            interpreter.chmod(0o700)
            if darwin:
                uname = folder / "uname"
                uname.write_text("#!/bin/sh\nprintf 'Darwin\\n'\n")
                uname.chmod(0o700)
            if timed_out:
                timeout = folder / "timeout"
                timeout.write_text("#!/bin/sh\nexit 124\n")
                timeout.chmod(0o700)
            env = dict(
                os.environ,
                FORK_PYTHON=str(interpreter),
                CHILD_LOG=str(child_log),
                FAIL_CHILD="1" if fail else "0",
                PATH=str(folder) + os.pathsep + os.environ["PATH"],
            )
            runner = RUNNER
            if runner_source is not None:
                runner = folder / "quality.sh"
                runner.write_text(runner_source)
            result = subprocess.run(
                ["bash", str(runner)],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=COMMAND_TIMEOUT,
            )
            calls = (
                [json.loads(line) for line in child_log.read_text().splitlines()]
                if child_log.exists()
                else []
            )
            return result, calls

    def assert_dispatch_contract(self, result, called):
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            called,
            [
                ["-m", "ruff", "check", "--no-cache"],
                ["-m", "ruff", "format", "--check", "--no-cache"],
                [
                    "-m",
                    "unittest",
                    "discover",
                    "-s",
                    "scripts/fork-ci",
                    "-p",
                    "test_*.py",
                    "-v",
                ],
                [
                    "-m",
                    "unittest",
                    "discover",
                    "-s",
                    "scripts/bench-apps",
                    "-p",
                    "test_*.py",
                    "-v",
                ],
            ],
        )
        rows = [json.loads(line) for line in result.stderr.splitlines()]
        self.assertEqual(
            [row["stage"] for row in rows if row["status"] == "passed"],
            ["lint", "format", "workflow", "tests"],
        )
        self.assertTrue(all(row["event"] == "quality.stage" for row in rows))

    def test_quality_contract_runs_all_stages_and_emits_finite_labels(self):
        self.assert_dispatch_contract(*self.dispatch())

    def test_same_oracle_rejects_substituted_suite_in_real_runner(self):
        source = RUNNER.read_text()
        changed = source.replace("-s scripts/bench-apps", "-s scripts/fork-ci")
        self.assertNotEqual(source, changed)
        with self.assertRaises(AssertionError):
            self.assert_dispatch_contract(*self.dispatch(runner_source=changed))

    def test_same_oracle_rejects_omitted_stage_in_real_runner(self):
        source = RUNNER.read_text()
        changed = (
            "\n".join(
                line
                for line in source.splitlines()
                if not line.startswith("run_stage tests ")
            )
            + "\n"
        )
        self.assertNotEqual(source, changed)
        with self.assertRaises(AssertionError):
            self.assert_dispatch_contract(*self.dispatch(runner_source=changed))

    def test_failed_stage_is_not_success_or_followed_by_tests(self):
        result, called = self.dispatch(fail=True)
        self.assertTrue(called)
        self.assertEqual(result.returncode, 17)
        rows = [json.loads(line) for line in result.stderr.splitlines()]
        self.assertEqual(rows[-1]["status"], "failed")
        self.assertEqual(rows[-1]["exitCode"], 17)
        self.assertEqual({row["stage"] for row in rows}, {"lint"})

    def test_timeout_cannot_become_pass(self):
        result, called = self.dispatch(timed_out=True)
        self.assertFalse(called)
        self.assertEqual(result.returncode, 124)
        self.assertIn('"status":"failed"', result.stderr)

    def test_mac_hook_refuses_before_project_interpreter(self):
        result, called = self.dispatch(darwin=True)
        self.assertFalse(called)
        self.assertEqual(result.returncode, 2)

    def test_help_does_not_run_quality_stages(self):
        result = subprocess.run(
            ["bash", str(RUNNER), "--help"],
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("FORK_PYTHON", result.stdout)
        self.assertNotIn("quality.stage", result.stderr)

    def test_scoped_rule_entrypoints_exist_and_links_resolve(self):
        for name in RULE_FILES:
            with self.subTest(file=name):
                path = ROOT / name
                self.assertTrue(path.is_file(), name)
                for target in re.findall(r"\]\(([^)]+)\)", path.read_text()):
                    if "://" not in target and not target.startswith("#"):
                        self.assertTrue(
                            (path.parent / target.split("#")[0]).is_file(), target
                        )
        self.assertLessEqual(
            len((ROOT / "AGENTS.md").read_text().splitlines()), MAX_ENTRYPOINT_LINES
        )

    def test_owning_handwritten_files_stay_within_line_budget(self):
        files = [
            *ROOT.glob("scripts/bench-apps/*.py"),
            *ROOT.glob("scripts/fork-ci/*.py"),
        ]
        for path in files:
            self.assertLessEqual(
                len(path.read_text().splitlines()),
                MAX_SOURCE_LINES,
                str(path.relative_to(ROOT)),
            )


if __name__ == "__main__":
    unittest.main()

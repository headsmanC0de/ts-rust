"""Behavioral tests of the real CLI wrapper, replacing only the Cargo boundary."""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

WRAPPER = Path(__file__).with_name("native_correctness.py")


class NativeCorrectnessTransport(unittest.TestCase):
    def run_wrapper(self, status):
        with tempfile.TemporaryDirectory(prefix="fork-native-wrapper-") as owned:
            cargo = Path(owned) / "cargo"
            cargo.write_text(
                "#!" + sys.executable + "\nimport json,sys,os,signal\n"
                "print('CARGO_ARGV=' + json.dumps(sys.argv[1:]), flush=True)\n"
                + (
                    "print('test real_fixture ... FAILED')\n"
                    if status
                    else "print('test real_fixture ... ok')\n"
                )
                + (
                    "os.kill(os.getpid(), signal.SIGTERM)\n"
                    if status == "signal"
                    else "sys.exit(" + str(status) + ")\n"
                )
            )
            cargo.chmod(0o700)
            if status == "missing":
                cargo.unlink()
            env = dict(
                os.environ,
                PATH=owned,
                PROVIDER_SECRET="must-never-appear",
                GOPORT_EMIT_THREADS="1",
                GITHUB_SHA="a" * 40,
                GITHUB_RUN_ID="123",
            )
            return subprocess.run(
                [sys.executable, str(WRAPPER)],
                env=env,
                capture_output=True,
                text=True,
                timeout=5,
            )

    def assert_scope_and_context(self, result):
        args = next(
            line
            for line in result.stdout.splitlines()
            if line.startswith("CARGO_ARGV=")
        )
        self.assertEqual(
            json.loads(args.split("=", 1)[1]),
            ["test", "--release", "--locked", "--workspace", "--no-fail-fast"],
        )
        events = [
            json.loads(line)
            for line in result.stdout.splitlines()
            if line.startswith('{"event":')
        ]
        self.assertEqual(events[0]["status"], "start")
        self.assertEqual(events[0]["source_sha"], "a" * 40)
        self.assertEqual(events[0]["run_id"], "123")
        self.assertEqual(events[0]["runtime"]["GOPORT_EMIT_THREADS"], "1")
        self.assertGreater(events[0]["runtime"]["page_size"], 0)
        self.assertGreaterEqual(events[-1]["elapsed_seconds"], 0)
        self.assertNotIn("must-never-appear", result.stdout + result.stderr)
        return events

    def test_success_streams_original_command_and_context(self):
        result = self.run_wrapper(0)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.assert_scope_and_context(result)[-1]["status"], "success")
        self.assertNotIn("::error", result.stdout)

    def test_failure_retains_exit_status_and_emits_immediate_annotation(self):
        result = self.run_wrapper(7)
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertEqual(self.assert_scope_and_context(result)[-1]["exit_code"], 7)
        self.assertIn(
            "::error title=Native correctness suite failed::test real_fixture ... FAILED",
            result.stdout,
        )

    def test_missing_cargo_emits_terminal_failure_and_returns_127(self):
        result = self.run_wrapper("missing")
        self.assertEqual(result.returncode, 127, result.stderr)
        events = [
            json.loads(line)
            for line in result.stdout.splitlines()
            if line.startswith('{"event":')
        ]
        self.assertEqual(events[-1]["status"], "failure")
        self.assertEqual(events[-1]["exit_code"], 127)
        self.assertIn("::error title=Native correctness suite failed::", result.stdout)
        self.assertNotIn("Traceback", result.stderr)
        self.assertNotIn("must-never-appear", result.stdout + result.stderr)

    @unittest.skipIf(os.name == "nt", "POSIX signal exit convention")
    def test_signaled_child_returns_128_plus_signal(self):
        result = self.run_wrapper("signal")
        self.assertEqual(result.returncode, 143, result.stderr)
        self.assertEqual(self.assert_scope_and_context(result)[-1]["exit_code"], 143)
        self.assertIn("::error title=Native correctness suite failed::", result.stdout)

    def test_annotation_escapes_percent_cr_and_lf(self):
        spec = importlib.util.spec_from_file_location("native_correctness", WRAPPER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(
            module.annotation("panic%\r\n::warning::injected"),
            "panic%25%0D%0A::warning::injected",
        )


if __name__ == "__main__":
    unittest.main()

"""Actual CLI lifecycle oracles for immutable physical benchmark receipts."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("lineage.py")


class LineageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.project = self.work / "project"
        self.project.mkdir()
        self.config = self.project / "tsconfig.json"
        self.config.write_text('{"files":["app.ts"]}')
        (self.project / "app.ts").write_text("export const value = 1")
        self.binary = self.work / "compiler"
        self.binary.write_text("actual fixture executable bytes")
        self.results = self.work / "results"
        self.results.mkdir()

    def cli(self, operation, stem, *extra):
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                operation,
                str(self.results / stem),
                *map(str, extra),
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )

    def reserve(
        self, stem="vscode", tool="tsc-rs", command="compiler --noEmit", binary=None
    ):
        return self.cli(
            "reserve",
            stem,
            self.project,
            self.config,
            tool,
            command,
            binary or self.binary,
        )

    def outputs(self, stem="vscode", tool="tsc-rs"):
        (self.results / (stem + ".json")).write_text(
            json.dumps({"results": [{"command": tool, "median": 1, "exit_codes": [0]}]})
        )
        (self.results / (stem + ".errors")).write_text(tool + " rc=0 errors=0\n")
        for stream in ["stdout", "stderr"]:
            (self.results / (stem + "." + tool + "." + stream)).write_text("")

    def test_normal_fast_same_case_are_immutable_distinct_receipts(self):
        for tool in ["tsc-rs", "tsc-rs-fast"]:
            stem = "vscode." + tool
            command = "compiler --noEmit" + (" --fast" if tool.endswith("fast") else "")
            self.assertEqual(self.reserve(stem, tool, command).returncode, 0)
            self.outputs(stem, tool)
            self.assertEqual(self.cli("finalize", stem).returncode, 0)
            self.assertEqual(self.cli("admit", stem, tool).returncode, 0)
        manifests = list((self.results / "lineage").glob("*/manifest.json"))
        self.assertEqual(len(manifests), 2)
        self.assertNotEqual(
            json.loads(manifests[0].read_text())["identity"],
            json.loads(manifests[1].read_text())["identity"],
        )
        self.assertNotEqual(self.reserve("vscode.tsc-rs").returncode, 0)

    def test_missing_partial_and_tampered_evidence_are_rejected(self):
        self.assertNotEqual(self.cli("admit", "vscode", "tsc-rs").returncode, 0)
        self.assertEqual(self.reserve().returncode, 0)
        self.outputs()
        self.assertNotEqual(self.cli("admit", "vscode", "tsc-rs").returncode, 0)
        self.assertEqual(self.cli("finalize", "vscode").returncode, 0)
        target = self.results / "vscode.tsc-rs.stdout"
        target.write_text("private payload")
        result = self.cli("admit", "vscode", "tsc-rs")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("private payload", result.stdout + result.stderr)

    def test_changed_binary_or_input_cannot_finalize(self):
        for name in ["binary", "input"]:
            stem = "vscode." + name
            self.assertEqual(self.reserve(stem).returncode, 0)
            self.outputs(stem)
            target = self.binary if name == "binary" else self.config
            target.write_text(target.read_text() + " changed")
            self.assertNotEqual(self.cli("finalize", stem).returncode, 0)
            self.assertFalse(
                (self.results / "lineage" / stem / "manifest.json").exists()
            )

    def test_interrupted_final_publication_cannot_be_admitted_or_overwrite(self):
        self.assertEqual(self.reserve().returncode, 0)
        self.outputs()
        folder = self.results / "lineage/vscode"
        pending = folder / "manifest.json.pending"
        pending.write_text("partial private output")
        self.assertNotEqual(self.cli("finalize", "vscode").returncode, 0)
        self.assertFalse((folder / "manifest.json").exists())
        self.assertEqual(pending.read_text(), "partial private output")
        self.assertNotEqual(self.cli("admit", "vscode", "tsc-rs").returncode, 0)

    def test_concurrent_claims_have_exactly_one_owner(self):
        args = [
            sys.executable,
            str(SCRIPT),
            "reserve",
            str(self.results / "vscode"),
            str(self.project),
            str(self.config),
            "tsc-rs",
            "compiler --noEmit",
            str(self.binary),
        ]
        first = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        second = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addCleanup(lambda: first.kill() if first.poll() is None else None)
        self.addCleanup(lambda: second.kill() if second.poll() is None else None)
        first.communicate(timeout=15)
        second.communicate(timeout=15)
        self.assertEqual(sorted([first.returncode, second.returncode]), [0, 1])

    def test_effect_oracle_uses_declared_actual_binary_and_flags(self):
        self.assertEqual(
            self.reserve(
                "t3-apps-server-effect",
                "tsc7",
                "effect-go -p tsconfig.json",
                self.binary,
            ).returncode,
            0,
        )
        self.outputs("t3-apps-server-effect", "tsc7")
        self.assertEqual(self.cli("finalize", "t3-apps-server-effect").returncode, 0)
        self.binary.write_text("changed effect compiler")
        # Consumer is portable; actual binary identity was captured and frozen by producer.
        self.assertEqual(
            self.cli("admit", "t3-apps-server-effect", "tsc7").returncode, 0
        )


if __name__ == "__main__":
    unittest.main()

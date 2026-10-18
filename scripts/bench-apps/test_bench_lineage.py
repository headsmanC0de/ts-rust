"""Actual shell producer and report CLI integration, faking external tools only."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lineage_fixtures import bind_fixtures

ROOT = Path(__file__).resolve().parent
PRIVATE_FILE_MODE = 0o600
ALL_TOOLS = ("tsc6", "tsc7", "tsc-rs", "tsc-rs-fast", "bun")


class ProducerLineageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.probes = self.work / "probes"
        self.probes.mkdir()
        self.executable(self.probes / "node", "#!/bin/sh\nexit 0\n")
        self.executable(
            self.probes / "hyperfine",
            "#!"
            + sys.executable
            + "\nimport json,sys\na=sys.argv[1:]\np=a[a.index('--export-json')+1]\nnames=[a[i+1] for i,s in enumerate(a) if s=='-n']\nwith open(p,'w') as f: json.dump({'results':[{'command':n,'median':1,'exit_codes':[0]} for n in names]},f)\n",
        )
        self.rs = self.work / "node_modules/@tsc-rs/linux-x64/lib/tsc"
        self.go = self.work / "node_modules/@typescript/typescript-linux-x64/lib/tsc"
        for file in [self.rs, self.go, self.work / "bun-linux-x64/bun"]:
            self.executable(file, "#!/bin/sh\nexit 0\n")
        self.write(self.work / "node_modules/ts6/lib/tsc.js", "fixture JS entry")
        self.project = self.work / "repos/vscode"
        self.write(self.project / "src/tsconfig.json", '{"files":["app.ts"]}')
        self.write(self.project / "src/app.ts", "export const input = 1")
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        self.env.update(PATH=str(self.probes) + os.pathsep + os.environ["PATH"])

    def write(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data)

    def executable(self, path, data):
        self.write(path, data)
        path.chmod(0o700)

    def run_script(self, script, *args, **env):
        return subprocess.run(
            ["bash", str(ROOT / script), str(self.work), *args],
            env=dict(self.env, **env),
            capture_output=True,
            text=True,
            timeout=15,
        )

    def test_real_run_keeps_normal_fast_receipts_and_refuses_retry_clobber(self):
        for tool in ["tsc-rs", "tsc-rs-fast"]:
            result = self.run_script("run.sh", "vscode", TOOLS=tool)
            self.assertEqual(result.returncode, 0, result.stderr)
        paths = list((self.work / "results/lineage").glob("*/manifest.json"))
        self.assertEqual(len(paths), 2)
        before = {
            str(p): p.read_bytes()
            for p in (self.work / "results").rglob("*")
            if p.is_file()
        }
        retry = self.run_script("run.sh", "vscode", TOOLS="tsc-rs")
        self.assertNotEqual(retry.returncode, 0)
        self.assertEqual(
            before,
            {
                str(p): p.read_bytes()
                for p in (self.work / "results").rglob("*")
                if p.is_file()
            },
        )

    def test_real_overlay_with_changed_project_identity_withholds_table(self):
        result = self.run_script("run.sh", "vscode")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.write(self.project / "src/app.ts", "export const input = 2")
        result = self.run_script("run.sh", "vscode", TOOLS="tsc-rs")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = subprocess.run(
            [sys.executable, str(ROOT / "summary.py"), str(self.work)],
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertNotEqual(report.returncode, 0)
        self.assertEqual(report.stdout, "")

    def test_environment_capture_is_private_unique_and_not_admission_identity(self):
        for name in ["lscpu", "rustc", "pnpm"]:
            self.executable(self.probes / name, "#!/bin/sh\nexit 0\n")
        for tool in ["tsc-rs", "tsc-rs-fast"]:
            result = subprocess.run(
                [sys.executable, str(ROOT / "metadata.py"), str(self.work)],
                cwd=self.work,
                env=dict(self.env, BENCH_CASE="vscode", TOOLS=tool),
                capture_output=True,
                text=True,
                timeout=15,
            )
            self.assertEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)["status"], "saved")
        captures = list((self.work / "results/environment").glob("*.json"))
        self.assertEqual(len(captures), 2)
        self.assertTrue(
            all(path.stat().st_mode & 0o777 == PRIVATE_FILE_MODE for path in captures)
        )
        self.assertFalse((self.work / "results/lineage").exists())

    def test_ambient_fast_environment_cannot_mislabel_ordinary_measurement(self):
        result = self.run_script("run.sh", "vscode", TOOLS="tsc-rs", GOPORT_FAST="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(
            (self.work / "results/lineage/vscode.tsc-rs/manifest.json").exists()
        )

    def test_real_t3_effect_binds_resolved_effect_oracle(self):
        t3 = self.work / "repos/t3code"
        self.write(t3 / "apps/server/tsconfig.json", '{"files":["app.ts"]}')
        self.write(t3 / "apps/server/app.ts", "export const effect = 1")
        self.write(
            self.work / "ts6effect/node_modules/typescript/lib/tsc.js", "patched JS"
        )
        (self.work / "effectgo/node_modules/@effect/tsgo").mkdir(parents=True)
        effect = self.work / "effect-native"
        self.executable(
            effect, "#!/bin/sh\n# effect executable differs from generic GO\nexit 0\n"
        )
        self.executable(
            self.work / "effectgo/node_modules/.bin/effect-tsgo",
            "#!/bin/sh\nif [ \"$1\" = get-exe-path ]; then printf '%s\\n' '"
            + str(effect)
            + "'; fi\n",
        )
        result = self.run_script(
            "t3code.sh", TOOLS="tsc7", T3_PROJECTS="apps/server", T3_MODES="effect"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        saved = json.loads(
            (
                self.work / "results/lineage/t3-apps-server-effect.tsc7/manifest.json"
            ).read_text()
        )
        hashes = saved["descriptor"]["tools"]["tsc7"]["artifacts"].values()
        self.assertIn(hashlib.sha256(effect.read_bytes()).hexdigest(), hashes)
        self.assertNotIn(hashlib.sha256(self.go.read_bytes()).hexdigest(), hashes)


class ReportLineageTests(unittest.TestCase):
    def test_verifier_consumes_verified_diagnostics_after_atomic_replacement(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            results = work / "results"
            results.mkdir()
            for tool, code in [("tsc-rs", "TS2322"), ("tsc7", "TS9999")]:
                (results / f"vscode.{tool}.stdout").write_text(
                    f"app.ts(1,1): error {code}: Original.\n"
                )
                (results / f"vscode.{tool}.stderr").write_text("")
            (results / "vscode.errors").write_text(
                "tsc-rs rc=0 errors=1\ntsc7 rc=0 errors=1\n"
            )
            bind_fixtures(results)
            runner = work / "diagnostic_race.py"
            runner.write_text("""import os,runpy,sys
from pathlib import Path
sut,work=sys.argv[1:];targets={Path(work)/'results'/('vscode.'+t+'.stdout') for t in ['tsc-rs','tsc7']}
original_open=Path.open;triggered=set()
class Reader:
    def __init__(self,stream,path):self.stream,self.path=stream,path
    def __enter__(self):self.stream.__enter__();return self
    def __exit__(self,*args):return self.stream.__exit__(*args)
    def read(self,*args):
        value=self.stream.read(*args)
        if self.path not in triggered:
            replacement=self.path.with_suffix('.replacement')
            replacement.write_text('app.ts(1,1): error TS1111: Changed equally.\\n')
            os.replace(replacement,self.path);triggered.add(self.path)
        return value
def observed(path,mode='r',*args,**kwargs):
    stream=original_open(path,mode,*args,**kwargs)
    return Reader(stream,path) if mode=='rb' and path in targets else stream
Path.open=observed
sys.argv=[sut,work,'--case','vscode'];sys.path.insert(0,str(Path(sut).parent))
try:runpy.run_path(sut,run_name='__main__')
finally:print('RACE_OBSERVED='+str(len(triggered)),file=sys.stderr)
""")
            result = subprocess.run(
                [sys.executable, str(runner), str(ROOT / "verify.py"), str(work)],
                capture_output=True,
                text=True,
                timeout=15,
            )
            self.assertIn("RACE_OBSERVED=2", result.stderr)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("MATCH", result.stdout)

    def test_verified_timing_bytes_are_the_bytes_consumed_despite_atomic_restore(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            results = work / "results"
            results.mkdir()
            for tool in ALL_TOOLS:
                for stream in ["stdout", "stderr"]:
                    (results / f"vscode.{tool}.{stream}").write_text("")
            (results / "vscode.errors").write_text(
                "".join(tool + " rc=0 errors=0\n" for tool in ALL_TOOLS)
            )
            bind_fixtures(results)
            timing = results / "vscode.json"
            original = work / "original.json"
            original.write_bytes(timing.read_bytes())
            changed = json.loads(timing.read_text())
            for row in changed["results"]:
                row["median"] = 0.01
            timing.write_text(json.dumps(changed))
            runner = work / "filesystem_race.py"
            runner.write_text("""import os,runpy,sys
from pathlib import Path
sut,work,target,original=sys.argv[1:]
target=Path(target);original=Path(original);triggered=False
text_reader=Path.read_text;byte_reader=Path.read_bytes
def intercept(reader,path,*args,**kwargs):
    global triggered
    content=reader(path,*args,**kwargs)
    if path==target and not triggered:
        os.replace(original,target)
        triggered=True
    return content
Path.read_text=lambda p,*a,**k:intercept(text_reader,p,*a,**k)
Path.read_bytes=lambda p,*a,**k:intercept(byte_reader,p,*a,**k)
sys.argv=[sut,work];sys.path.insert(0,str(Path(sut).parent))
try:runpy.run_path(sut,run_name='__main__')
finally:print('RACE_OBSERVED='+str(int(triggered)),file=sys.stderr)
""")
            result = subprocess.run(
                [
                    sys.executable,
                    str(runner),
                    str(ROOT / "summary.py"),
                    str(work),
                    str(timing),
                    str(original),
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
            self.assertIn("RACE_OBSERVED=1", result.stderr)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")

    def test_real_report_withholds_missing_stale_changed_and_partial_receipts(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            results = work / "results"
            results.mkdir()
            for tool in ALL_TOOLS:
                for stream in ["stdout", "stderr"]:
                    (results / f"vscode.{tool}.{stream}").write_text("")
            (results / "vscode.errors").write_text(
                "".join(tool + " rc=0 errors=0\n" for tool in ALL_TOOLS)
            )
            bind_fixtures(results)
            manifest = results / "lineage/vscode/manifest.json"
            original = manifest.read_bytes()

            def report():
                return subprocess.run(
                    [sys.executable, str(ROOT / "summary.py"), str(work)],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )

            self.assertEqual(report().returncode, 0)
            for mutation in ["missing", "partial", "stale", "digest"]:
                manifest.write_bytes(original)
                if mutation == "missing":
                    manifest.unlink()
                elif mutation == "partial":
                    manifest.write_text('{"schema":')
                else:
                    data = json.loads(original)
                    if mutation == "stale":
                        data["stem"] = "different-case"
                    else:
                        data["descriptor"]["tools"]["tsc-rs-fast"]["fast"] = False
                    manifest.write_text(json.dumps(data))
                result = report()
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                self.assertNotIn("Traceback", result.stderr)
            manifest.write_bytes(original)
            (results / "vscode.tsc-rs.stderr").write_text("PRIVATE_PAYLOAD")
            result = report()
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertNotIn("PRIVATE_PAYLOAD", result.stderr)


if __name__ == "__main__":
    unittest.main()

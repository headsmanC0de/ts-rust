"""Immutable physical-measurement receipts. Integrity evidence, not signed provenance.

Closure: project source/config files outside .git/node_modules, declared lockfiles,
actual selected executables, sibling JS/libs and explicit companion artifacts.
Installed application dependencies are NOT recursively hashed or claimed immutable.
Canonical mode rejects ambient GOPORT_FAST* overrides; other semantic environment
controls are not claimed frozen. Artifact consumers use verified immutable bytes.
Producer checks this declared closure before/after measurement; report consumers can
verify saved artifact bytes and compatible input descriptors without the original VM.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

SCHEMA = 1
MODE_ENVIRONMENT = "ambient-GOPORT_FAST-prefix-rejected-v1"
INPUT_CLOSURE = "project-source-config-v1; application-node_modules-excluded"
TOOLS = ("tsc6", "tsc7", "tsc-rs", "tsc-rs-fast", "bun")
SOURCE_SUFFIXES = {
    ".ts",
    ".tsx",
    ".mts",
    ".cts",
    ".js",
    ".mjs",
    ".cjs",
    ".json",
    ".jsonc",
    ".yaml",
    ".yml",
}
CHUNK_SIZE = 1 << 20


def canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def fingerprint(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_SIZE), b""):
            result.update(chunk)
    return result.hexdigest()


def location(out):
    out = Path(out)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.+-]*", out.name):
        raise ValueError("invalid_stem")
    return out, out.parent / "lineage" / out.name


def atomic_create(path, value):
    temporary = path.with_name(path.name + ".pending")
    with temporary.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.link(
        temporary, path
    )  # Atomic no-clobber publication, within the same directory.
    temporary.unlink()


def artifact_files(declarations, cache):
    files = {}
    for index, declared in enumerate(declarations):
        path = Path(declared).resolve(strict=True)
        if not path.is_file():
            raise ValueError("missing_tool_artifact")
        selected = {path}
        # JS launchers need their implementation, and native/JS compilers load sibling libs.
        selected.update(path.parent.glob("lib*.d.ts"))
        selected.update(path.parent.glob("*.js"))
        if (path.parent / "build.json").is_file():
            selected.add(path.parent / "build.json")
        for file in sorted(selected):
            if file not in cache:
                cache[file] = digest(file)
            files[f"{index}/{file.name}"] = cache[file]
    return files


def controlled_mode_environment():
    if any(key.startswith("GOPORT_FAST") for key in os.environ):
        raise ValueError("uncontrolled_fast_environment")


def descriptor(plan):
    controlled_mode_environment()
    project, config = Path(plan["project"]), Path(plan["config"])
    if not config.is_file() or not project.is_dir():
        raise ValueError("missing_input")
    inputs = {}
    for root, dirs, names in os.walk(project):
        dirs[:] = sorted(d for d in dirs if d not in {".git", "node_modules"})
        for name in sorted(names):
            file = Path(root) / name
            if file.suffix in SOURCE_SUFFIXES:
                inputs[file.relative_to(project).as_posix()] = digest(file)
    if not inputs:
        raise ValueError("missing_input")
    config_name = config.resolve().relative_to(project.resolve()).as_posix()
    input_identity = {
        "files": inputs,
        "config": config_name,
        "configHash": digest(config),
        "closure": INPUT_CLOSURE,
    }
    tools, cache = {}, {}
    for tool, command, artifacts in plan["tools"]:
        if tool not in TOOLS or tool in tools or not command:
            raise ValueError("invalid_tool")
        fast = "--fast" in command.split()
        if fast != (tool == "tsc-rs-fast"):
            raise ValueError("invalid_variant_flags")
        tools[tool] = {
            "commandHash": hashlib.sha256(command.encode()).hexdigest(),
            "fast": fast,
            "artifacts": artifact_files(artifacts.splitlines(), cache),
        }
    if not tools or any(not row["artifacts"] for row in tools.values()):
        raise ValueError("missing_tool_artifact")
    source = Path(__file__).resolve().parent
    env = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    identity = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=source,
        env=env,
        capture_output=True,
        timeout=5,
        check=False,
    )
    head = identity.stdout.decode().strip()
    if identity.returncode or not re.fullmatch(r"[0-9a-f]{40}", head):
        raise ValueError("producer_source_unavailable")
    producer = {
        "head": head,
        "files": {
            name: digest(source / name)
            for name in [
                "lineage.py",
                "common.sh",
                "run.sh",
                "t3code.sh",
                "metadata.py",
            ]
        },
    }
    return {
        "case": plan["stem"].split(".")[0],
        "input": input_identity,
        "tools": tools,
        "producer": producer,
        "modeEnvironment": MODE_ENVIRONMENT,
    }


def reserve(out, project, config, triples):
    controlled_mode_environment()
    out, folder = location(out)
    folder.parent.mkdir(parents=True, exist_ok=True)
    folder.mkdir()  # Ownership is acquired before any evidence may be truncated.
    existing_names = evidence_files(out, TOOLS) + [
        f"{out.name}.{tool}.diag" for tool in TOOLS
    ]
    if any((out.parent / name).exists() for name in existing_names):
        raise ValueError("existing_measurement")
    if len(triples) % 3:
        raise ValueError("invalid_tool")
    plan = {
        "stem": out.name,
        "project": str(Path(project).resolve()),
        "config": str(Path(config).resolve()),
        "tools": [triples[i : i + 3] for i in range(0, len(triples), 3)],
    }
    started = time.monotonic()
    initial = descriptor(plan)
    atomic_create(folder / "plan.json", {"plan": plan, "descriptor": initial})
    return {
        "files": len(initial["input"]["files"]),
        "inputBytes": sum(
            (Path(project) / name).stat().st_size for name in initial["input"]["files"]
        ),
        "elapsedSeconds": round(time.monotonic() - started, 3),
    }


def evidence_files(out, tools):
    return [
        out.name + ".json",
        out.name + ".errors",
        *[
            f"{out.name}.{tool}.{stream}"
            for tool in tools
            for stream in ["stdout", "stderr"]
        ],
    ]


def receipt(out, description):
    """Build a portable receipt from the captured descriptor and complete physical files."""
    out, _ = location(out)
    return {
        "schema": SCHEMA,
        "stem": out.name,
        "descriptor": description,
        "identity": fingerprint(description),
        "files": {
            name: digest(out.parent / name)
            for name in evidence_files(out, description["tools"])
        },
    }


def finalize(out):
    out, folder = location(out)
    saved = json.loads((folder / "plan.json").read_text())
    current = descriptor(saved["plan"])
    if current != saved["descriptor"]:
        raise ValueError("measurement_identity_changed")
    timing = json.loads(Path(str(out) + ".json").read_text())
    measured = [row["command"] for row in timing["results"]]
    if len(measured) != len(set(measured)) or set(measured) != set(current["tools"]):
        raise ValueError("selected_tools_changed")
    atomic_create(folder / "manifest.json", receipt(out, current))


def validated_description(saved, stem, case):
    description = saved["descriptor"]
    if (
        saved["schema"] != SCHEMA
        or saved["stem"] != stem
        or description["case"] != (case or stem.split(".")[0])
        or description["modeEnvironment"] != MODE_ENVIRONMENT
        or saved["identity"] != fingerprint(description)
    ):
        raise ValueError("lineage_identity_invalid")
    inputs, producer = description["input"], description["producer"]
    digests = [
        inputs["configHash"],
        *inputs["files"].values(),
        *producer["files"].values(),
    ]
    if (
        inputs["closure"] != INPUT_CLOSURE
        or not inputs["files"]
        or inputs["files"][inputs["config"]] != inputs["configHash"]
        or not producer["files"]
        or not re.fullmatch(r"[0-9a-f]{40}", producer["head"])
        or any(
            not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value)
            for value in digests
        )
    ):
        raise ValueError("lineage_descriptor_invalid")
    return description


def verified_bytes(results, saved, name):
    content = (Path(results) / name).read_bytes()
    if saved["files"][name] != hashlib.sha256(content).hexdigest():
        raise ValueError("lineage_evidence_changed")
    return content


@dataclass(frozen=True)
class Evidence:
    stem: str
    tool: str
    input_identity: str
    timing: bytes
    errors: bytes
    stdout: bytes
    stderr: bytes


@dataclass(frozen=True)
class Measurement:
    results: Path
    stem: str
    _saved: dict
    timing: bytes

    def evidence(self, tool):
        description = self._saved["descriptor"]
        row = description["tools"][tool]
        digests = [row["commandHash"], *row["artifacts"].values()]
        if (
            row["fast"] != (tool == "tsc-rs-fast")
            or not row["artifacts"]
            or any(
                not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value)
                for value in digests
            )
        ):
            raise ValueError("lineage_variant_invalid")
        return Evidence(
            self.stem,
            tool,
            fingerprint(description["input"]),
            self.timing,
            verified_bytes(self.results, self._saved, self.stem + ".errors"),
            verified_bytes(self.results, self._saved, f"{self.stem}.{tool}.stdout"),
            verified_bytes(self.results, self._saved, f"{self.stem}.{tool}.stderr"),
        )


def capture(results, stem, case=None):
    _, folder = location(Path(results) / stem)
    saved = json.loads((folder / "manifest.json").read_bytes())
    validated_description(saved, stem, case)
    timing = verified_bytes(results, saved, stem + ".json")
    return Measurement(Path(results), stem, saved, timing)


def admit(results, stem, tool, case=None):
    return capture(results, stem, case).evidence(tool)


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        operation, out, *remaining = args
        if operation == "reserve":
            project, config, *triples = remaining
            details = reserve(out, project, config, triples)
        elif operation == "finalize" and not remaining:
            finalize(out)
            details = {}
        elif operation == "admit" and len(remaining) == 1:
            admit(Path(out).parent, Path(out).name, remaining[0])
            details = {}
        else:
            raise ValueError("invalid_operation")
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
        UnicodeError,
        subprocess.TimeoutExpired,
    ):
        print('{"event":"benchmark.lineage","status":"failed"}', file=sys.stderr)
        return 1
    print(json.dumps({"event": "benchmark.lineage", "status": "success", **details}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Fork workflow admission contracts; configuration checks, not compiler acceptance."""

import copy
import hashlib
import json
import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
UPSTREAM_GUARD = "github.repository == 'pingdotgg/ts-rust'"
PUBLISH_GUARD = (
    UPSTREAM_GUARD
    + " && github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v')"
    + " && needs.version.outputs.release == 'true'"
)
NATIVE_WRAPPER_RUN = "python scripts/fork-ci/native_correctness.py"
NATIVE_POOL_ENV = {"GOPORT_EMIT_THREADS": "${{ env.EMIT_POOL_FIXTURE_THREADS }}"}
HOSTED_TEST_RUNNERS = [
    "ubuntu-24.04",
    "ubuntu-24.04-arm",
    "macos-26",
    "windows-2025",
]
TEST_CACHE_POLICY = {
    "prefix-key": "v1-fork-workspace",
    "cache-workspace-crates": "true",
    "cache-bin": "false",
    "save-if": "${{ (github.event_name == 'push' && github.ref == 'refs/heads/main') || (github.event_name == 'pull_request' && github.event.pull_request.head.repo.full_name == github.repository) }}",
    "cache-on-failure": "${{ github.event_name == 'pull_request' && github.event.pull_request.head.repo.full_name == github.repository }}",
}
UPSTREAM_CACHE_POLICY = {"save-if": "${{ github.ref == 'refs/heads/main' }}"}

# Independently recorded from upstream source780dc512, before changing workflow configuration.
UPSTREAM_STEP_DIGESTS = {
    "lint": "f17d56f23b5317261cea6622178746fe5d78f65d83a33ab2c8a2ec82ebd7fe49",
    "test": "187353c195ee687d5edef1f3c84c4f7f33736dd60a36680287b296cc5c39dafd",
    "wasm": "5b9f5df9c28b6af83129918e986dd2990851336719e764308a175a9f4f1b461b",
}


def load_workflow(name):
    # BaseLoader preserves YAML's `on` key and treats all scalars as strings.
    return yaml.load(
        (ROOT / ".github/workflows" / (name + ".yml")).read_text(),
        Loader=yaml.BaseLoader,
    )


def ci_problems(ci):
    problems = []
    jobs = ci["jobs"]
    if ci.get("permissions") != {"contents": "read"}:
        problems.append("CI token must be contents-read only")
    if set(ci["on"]) != {"pull_request", "push"}:
        problems.append("CI events must remain unprivileged PR and main push")
    required_paths = {
        ".github/workflows/**",
        "scripts/**",
        "npm/wasm/**",
        "docs/typechecker-state/current.json",
        "docs/fork-qualification.md",
        "AGENTS.md",
        "search-rules.md",
        "TESTS.md",
        "GUARDS.md",
        "DESIGN.md",
        "SECURITY.md",
        "CYBERSECURITY.md",
        "lefthook.yml",
        "ruff.toml",
        ".editorconfig",
    }
    if not required_paths.issubset(set(ci["on"]["push"].get("paths", []))):
        problems.append("push misses an owning workflow input")
    if ci.get("env", {}).get("CARGO_BUILD_JOBS") != "2":
        problems.append("Cargo must have a bounded per-VM worker count")
    for name in ["lint", "wasm"]:
        if jobs[name]["runs-on"] != "ubuntu-24.04":
            problems.append(name + " needs accessible hosted Linux")
    if jobs["test"].get("env", {}).get(
        "EMIT_POOL_FIXTURE_THREADS"
    ) != "1" or "GOPORT_EMIT_THREADS" in jobs["test"].get("env", {}):
        problems.append("hosted tests must exercise the parallel emit pool")
    if jobs["test"]["strategy"]["matrix"]["runner"] != HOSTED_TEST_RUNNERS:
        problems.append("test matrix must preserve all four OS/architecture cells")
    for name, expected in UPSTREAM_STEP_DIGESTS.items():
        job = jobs[name]
        steps = copy.deepcopy(job["steps"])
        for step in steps:
            # Reviewed fixture adapter: the wrapper contract executes this exact original argv.
            # Normalize only its complete expected step; extra flags/env/conditions still fail.
            if name == "test" and step == {
                "name": "Unit and integration tests",
                "env": NATIVE_POOL_ENV,
                "run": NATIVE_WRAPPER_RUN,
            }:
                step.pop("env")
                step["run"] = "cargo test --release --locked --workspace --no-fail-fast"
            if "uses" in step:
                step["uses"] = step["uses"].split("@")[0]
                if name == "test" and step["uses"] == "Swatinem/rust-cache":
                    if step.get("with") != TEST_CACHE_POLICY:
                        problems.append(
                            "test cache loses isolation or workspace artifact reuse"
                        )
                    # Only this reviewed cache policy differs; all test/build commands stay pinned.
                    step["with"] = UPSTREAM_CACHE_POLICY
        actual = hashlib.sha256(
            json.dumps(steps, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        if (
            actual != expected
            or "if" in job
            or "needs" in job
            or "continue-on-error" in job
        ):
            problems.append(name + " changed or bypassed inherited coverage")
    for name, job in jobs.items():
        for step in job.get("steps", []):
            action = step.get("uses")
            if action and not re.fullmatch(
                r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}", action
            ):
                problems.append(name + " has a mutable action")
            if action and action.startswith("actions/checkout@"):
                if step.get("with", {}).get("persist-credentials") != "false":
                    problems.append(name + " persists checkout credentials")
        if job.get("permissions"):
            problems.append(name + " overrides the read-only token")
    contract = jobs.get("workflow-contracts")
    if contract is None:
        problems.append("missing distinct fast configuration contract job")
    else:
        if (
            contract.get("name") != "Fork configuration contracts"
            or contract["runs-on"] != "ubuntu-24.04"
        ):
            problems.append("configuration check identity or isolation changed")
        if any(key in contract for key in ["if", "needs", "continue-on-error"]):
            problems.append("required configuration job must not be skipped or ignored")
        if any(
            "if" in step or "continue-on-error" in step for step in contract["steps"]
        ):
            problems.append(
                "required configuration steps must not be skipped or ignored"
            )
        commands = [s["run"] for s in contract["steps"] if "run" in s]
        if commands != [
            "python -m pip install --only-binary=:all: --require-hashes -r scripts/fork-ci/requirements.txt",
            "bash scripts/fork-ci/quality.sh",
        ]:
            problems.append(
                "configuration job executes outside its bounded admission scope"
            )
    if "secrets." in json.dumps(ci):
        problems.append("ordinary CI must not request provider secrets")
    return problems


def upstream_problems(workflows):
    problems = []
    for workflow, root in [
        ("release", "version"),
        ("testbox", "testbox"),
        ("bench-apps", "plan"),
    ]:
        if workflows[workflow]["jobs"][root].get("if") != UPSTREAM_GUARD:
            problems.append(workflow + " entrypoint admits a fork")
    if workflows["release"]["jobs"]["release"].get("if") != PUBLISH_GUARD:
        problems.append("publishing lacks explicit upstream/tag/push trust")
    return problems


class ForkWorkflowContracts(unittest.TestCase):
    def test_actual_ci_has_accessible_pinned_coverage_and_fast_contracts(self):
        self.assertEqual(ci_problems(load_workflow("ci")), [])

    def test_native_correctness_declares_bounded_fixture_pool_only_here(self):
        ci = load_workflow("ci")
        native = ci["jobs"]["test"]
        self.assertEqual(native["env"].get("EMIT_POOL_FIXTURE_THREADS"), "1")
        self.assertNotIn("GOPORT_EMIT_THREADS", native["env"])
        for step in native["steps"]:
            pool = step.get("env", {}).get("GOPORT_EMIT_THREADS")
            if step.get("name") == "Unit and integration tests":
                self.assertEqual(step.get("env"), NATIVE_POOL_ENV)
                self.assertEqual(step["run"], NATIVE_WRAPPER_RUN)
            else:
                self.assertIsNone(pool)
        self.assertNotIn("GOPORT_EMIT_THREADS", ci["env"])

    def test_actual_inherited_service_entrypoints_exclude_fork_execution(self):
        self.assertEqual(
            upstream_problems(
                {n: load_workflow(n) for n in ["release", "testbox", "bench-apps"]}
            ),
            [],
        )

    def test_unsafe_ci_mutations_are_rejected(self):
        ci = load_workflow("ci")
        mutations = [
            lambda x: x["jobs"]["lint"].update({"runs-on": "self-hosted"}),
            lambda x: next(
                s
                for s in x["jobs"]["test"]["steps"]
                if s.get("uses", "").startswith("Swatinem/rust-cache@")
            )["with"].update({"shared-key": "unsafe-global"}),
            lambda x: next(
                s
                for s in x["jobs"]["test"]["steps"]
                if s.get("uses", "").startswith("Swatinem/rust-cache@")
            )["with"].update({"save-if": "true"}),
            lambda x: next(
                s
                for s in x["jobs"]["test"]["steps"]
                if s.get("uses", "").startswith("Swatinem/rust-cache@")
            )["with"].pop("cache-workspace-crates"),
            lambda x: x["jobs"]["test"]["env"].pop("EMIT_POOL_FIXTURE_THREADS", None),
            lambda x: x["jobs"]["test"]["strategy"]["matrix"]["runner"].pop(),
            lambda x: x["jobs"]["wasm"].update({"if": "false"}),
            lambda x: x["jobs"]["lint"].update({"needs": "workflow-contracts"}),
            lambda x: next(
                s
                for s in x["jobs"]["test"]["steps"]
                if s.get("name") == "Unit and integration tests"
            ).update({"if": "false"}),
            lambda x: next(s for s in x["jobs"]["lint"]["steps"] if "run" in s).update(
                {"if": "false"}
            ),
            lambda x: next(s for s in x["jobs"]["test"]["steps"] if "run" in s).update(
                {"continue-on-error": "true"}
            ),
            lambda x: x["jobs"]["lint"]["steps"][0]["with"].update(
                {"persist-credentials": "true"}
            ),
            lambda x: x["jobs"]["wasm"].update({"permissions": {"contents": "write"}}),
            lambda x: x["env"].update({"TOKEN": "${{ secrets.PROVIDER_TOKEN }}"}),
            lambda x: x["jobs"]["lint"]["steps"].append(
                {"uses": "actions/checkout@v5"}
            ),
            lambda x: x["permissions"].update({"id-token": "write"}),
            lambda x: x["on"].update({"pull_request_target": {}}),
            lambda x: x["jobs"]["lint"]["steps"].append({"run": "npm publish"}),
            lambda x: x["jobs"]["workflow-contracts"]["steps"].pop(),
            lambda x: x["jobs"]["workflow-contracts"].update({"if": "false"}),
            lambda x: x["jobs"]["workflow-contracts"]["steps"][-1].update(
                {"continue-on-error": "true"}
            ),
        ]
        # Mutation tests only qualify the oracle after the real workflow has passed it.
        self.assertEqual(ci_problems(ci), [])
        for mutate in mutations:
            candidate = copy.deepcopy(ci)
            mutate(candidate)
            with self.subTest(mutation=mutate.__code__.co_firstlineno):
                self.assertTrue(ci_problems(candidate))

    def test_removed_or_fork_retargeted_publish_guards_are_rejected(self):
        workflows = {n: load_workflow(n) for n in ["release", "testbox", "bench-apps"]}
        self.assertEqual(upstream_problems(workflows), [])
        for workflow, job in [
            ("release", "version"),
            ("testbox", "testbox"),
            ("bench-apps", "plan"),
            ("release", "release"),
        ]:
            for guard in ["true", "github.repository == 'headsmanC0de/ts-rust'"]:
                candidate = copy.deepcopy(workflows)
                candidate[workflow]["jobs"][job]["if"] = guard
                with self.subTest(workflow=workflow, job=job, guard=guard):
                    self.assertTrue(upstream_problems(candidate))


if __name__ == "__main__":
    unittest.main()

"""Executable reachability contracts for topic rules and the shared quality gate."""

import copy
import re
import unittest
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[2]
TOPICS = (
    "search-rules.md",
    "TESTS.md",
    "GUARDS.md",
    "DESIGN.md",
    "SECURITY.md",
    "CYBERSECURITY.md",
)
QUALITY_COMMAND = "python scripts/fork-ci/quality.py"
HOOK_COMMAND = '"${FORK_QUALITY_PYTHON:-python3}" scripts/fork-ci/quality.py'


def local_links(name, text):
    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
        parsed = urlsplit(target.strip("<>"))
        if not parsed.scheme and not parsed.netloc and parsed.path:
            yield (Path(name).parent / unquote(parsed.path)).as_posix()


def read_rules(root=ROOT):
    documents = {
        name: (root / name).read_text()
        for name in ("AGENTS.md", *TOPICS)
        if (root / name).is_file()
    }
    paths = set(documents)
    for name, text in documents.items():
        paths.update(
            target for target in local_links(name, text) if (root / target).is_file()
        )
    return {
        "documents": documents,
        "paths": paths,
        "hook": yaml.load((root / "lefthook.yml").read_text(), Loader=yaml.BaseLoader),
        "ci": yaml.load(
            (root / ".github/workflows/ci.yml").read_text(), Loader=yaml.BaseLoader
        ),
    }


def rule_problems(rules):
    problems = []
    documents = rules["documents"]
    for name in ("AGENTS.md", *TOPICS):
        if name not in rules["paths"]:
            problems.append("missing topic document: " + name)
    entry = documents.get("AGENTS.md", "")
    for name in TOPICS:
        if name not in set(local_links("AGENTS.md", entry)):
            problems.append("AGENTS misses topic link: " + name)
    for name, text in documents.items():
        for target in local_links(name, text):
            if target not in rules["paths"]:
                problems.append(
                    "unresolved local topic link: " + name + " -> " + target
                )
    if rules["hook"].get("assert_lefthook_installed") != "true":
        problems.append("missing Lefthook binary must fail closed")
    hook = (
        rules["hook"].get("pre-commit", {}).get("commands", {}).get("fork-quality", {})
    )
    last_statement = hook.get("run", "").rsplit(";", 1)[-1].strip()
    if last_statement != HOOK_COMMAND:
        problems.append("pre-commit does not invoke the shared quality entrypoint")
    if any(key in hook for key in ("skip", "only", "interactive")):
        problems.append("pre-commit quality command has conditional execution")
    job = rules["ci"].get("jobs", {}).get("workflow-contracts", {})
    steps = [
        step for step in job.get("steps", []) if step.get("run") == QUALITY_COMMAND
    ]
    if len(steps) != 1:
        problems.append("fast CI must invoke the shared quality entrypoint once")
    if any(key in job for key in ("if", "continue-on-error")) or any(
        any(key in step for key in ("if", "continue-on-error")) for step in steps
    ):
        problems.append("fast CI quality entrypoint may be bypassed")
    return problems


class RulesContractTests(unittest.TestCase):
    def test_actual_topic_links_and_shared_hook_ci_entrypoint(self):
        self.assertEqual(rule_problems(read_rules()), [])

    def mutated_rules(self):
        rules = read_rules()
        self.assertEqual(rule_problems(rules), [])
        return copy.deepcopy(rules)

    def test_missing_topic_document_is_rejected(self):
        rules = self.mutated_rules()
        rules["paths"].remove("GUARDS.md")
        self.assertTrue(rule_problems(rules))

    def test_disconnected_topic_link_is_rejected(self):
        rules = self.mutated_rules()
        rules["documents"]["AGENTS.md"] = rules["documents"]["AGENTS.md"].replace(
            "[GUARDS.md](GUARDS.md)", "GUARDS.md"
        )
        self.assertTrue(rule_problems(rules))

    def test_missing_local_link_target_is_rejected(self):
        rules = self.mutated_rules()
        rules["documents"]["GUARDS.md"] += "\n[missing](docs/missing-owner.md)\n"
        self.assertTrue(rule_problems(rules))

    def test_missing_or_false_lefthook_assertion_is_rejected(self):
        for value in (None, "false"):
            rules = self.mutated_rules()
            if value is None:
                rules["hook"].pop("assert_lefthook_installed", None)
            else:
                rules["hook"]["assert_lefthook_installed"] = value
            with self.subTest(value=value):
                self.assertIn(
                    "missing Lefthook binary must fail closed", rule_problems(rules)
                )

    def test_disconnected_hook_is_rejected(self):
        rules = self.mutated_rules()
        rules["hook"]["pre-commit"]["commands"]["fork-quality"]["run"] = "echo skipped"
        self.assertTrue(rule_problems(rules))

    def test_disconnected_ci_is_rejected(self):
        rules = self.mutated_rules()
        for step in rules["ci"]["jobs"]["workflow-contracts"]["steps"]:
            if step.get("run") == QUALITY_COMMAND:
                step["run"] = "echo skipped"
        self.assertTrue(rule_problems(rules))

    def test_conditional_ci_quality_step_is_rejected(self):
        rules = self.mutated_rules()
        rules["ci"]["jobs"]["workflow-contracts"]["if"] = "false"
        self.assertTrue(rule_problems(rules))


if __name__ == "__main__":
    unittest.main()

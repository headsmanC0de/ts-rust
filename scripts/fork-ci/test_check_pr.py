"""Provider fixtures exercise the real premerge evaluator, without network access."""

import contextlib
import copy
import io
import subprocess
import unittest
from unittest.mock import patch

from check_pr import REQUIRED_CONTEXTS, ProviderFailure, collect, evaluate, fetch, main

HEAD = "a" * 40
MERGE = "b" * 40


def fixture():
    return {
        "pr_number": 1,
        "pr": {
            "headRefOid": HEAD,
            "baseRefName": "main",
            "potentialMergeCommit": {"oid": MERGE},
            "state": "OPEN",
            "isDraft": False,
            "reviewDecision": "APPROVED",
            "author": {"login": "owner"},
            "reviews": [
                {
                    "author": {"login": "reviewer"},
                    "state": "APPROVED",
                    "commit": {"oid": HEAD},
                    "submittedAt": "2026-10-18T10:00:00Z",
                }
            ],
        },
        "protection": {
            "required_status_checks": {"contexts": list(REQUIRED_CONTEXTS)},
            "required_pull_request_reviews": {
                "required_approving_review_count": 1,
                "require_last_push_approval": True,
            },
        },
        "checks": [
            {
                "name": name,
                "status": "completed",
                "conclusion": "success",
                "head_sha": MERGE,
                "app": {"id": 15368, "slug": "github-actions"},
                "details_url": "https://github.com/owner/repo/actions/runs/123/job/456",
            }
            for name in REQUIRED_CONTEXTS
        ],
        "runs": {
            "123": {
                "headSha": HEAD,
                "event": "pull_request",
                "path": ".github/workflows/ci.yml",
                "pull_requests": [
                    {"number": 1, "base": {"ref": "main"}, "head": {"sha": HEAD}}
                ],
                "status": "completed",
                "conclusion": "success",
                "jobs": [
                    {
                        "name": name,
                        "status": "completed",
                        "conclusion": "success",
                        "steps": [
                            {
                                "name": "Run tooling quality contract",
                                "status": "completed",
                                "conclusion": "success",
                                "number": 3,
                            }
                        ],
                    }
                    for name in REQUIRED_CONTEXTS
                ],
            }
        },
    }


class PremergeDetector(unittest.TestCase):
    def test_complete_source_bound_provider_receipt(self):
        self.assertEqual(evaluate(fixture(), HEAD, "owner/repo"), [])

    def test_rejects_stale_head_and_check_source(self):
        for mutate in [
            lambda x: x["pr"].update(headRefOid=MERGE),
            lambda x: x["checks"][0].update(head_sha="c" * 40),
            lambda x: x["runs"]["123"].update(headSha=MERGE),
            lambda x: x["runs"]["123"].update(path=".github/workflows/other.yml"),
            lambda x: x["checks"][0]["app"].update(id=1),
            lambda x: x["checks"][0].update(
                details_url="https://hostile.invalid/private"
            ),
        ]:
            with self.subTest(mutate=mutate):
                data = fixture()
                mutate(data)
                self.assertTrue(evaluate(data, HEAD, "owner/repo"))

    def test_rejects_missing_duplicate_and_non_success_contexts(self):
        for status in ["skipped", "neutral", "failure", None]:
            data = fixture()
            data["checks"][0]["conclusion"] = status
            self.assertTrue(evaluate(data, HEAD, "owner/repo"))
        for mutate in [
            lambda x: x["checks"].pop(),
            lambda x: x["checks"].append(copy.deepcopy(x["checks"][0])),
            lambda x: x["checks"][0].update(status="in_progress"),
            lambda x: x["protection"]["required_status_checks"]["contexts"].pop(),
        ]:
            data = fixture()
            mutate(data)
            self.assertTrue(evaluate(data, HEAD, "owner/repo"))

    def test_rejects_unexecuted_or_failed_quality_step_and_job(self):
        for mutate in [
            lambda j: j.update(status="queued"),
            lambda j: j.update(conclusion="neutral"),
            lambda j: j.update(steps=[]),
            lambda j: j["steps"][0].update(conclusion="failure"),
            lambda j: j["steps"][0].update(status="queued"),
            lambda j: j["steps"][0].update(number=0),
        ]:
            data = fixture()
            mutate(data["runs"]["123"]["jobs"][0])
            self.assertTrue(evaluate(data, HEAD, "owner/repo"))

    def test_requires_current_independent_latest_review(self):
        for mutate in [
            lambda p: p.update(reviews=[]),
            lambda p: p["reviews"][0]["author"].update(login="owner"),
            lambda p: p["reviews"][0]["commit"].update(oid=MERGE),
            lambda p: p["reviews"].append(
                {
                    "author": {"login": "reviewer"},
                    "state": "CHANGES_REQUESTED",
                    "commit": {"oid": HEAD},
                    "submittedAt": "2026-10-18T11:00:00Z",
                }
            ),
        ]:
            data = fixture()
            mutate(data["pr"])
            self.assertTrue(evaluate(data, HEAD, "owner/repo"))

    def test_honors_stricter_provider_review_policy_fail_closed(self):
        for policy in [
            {"required_approving_review_count": 2},
            {"require_last_push_approval": False},
        ]:
            data = fixture()
            data["protection"]["required_pull_request_reviews"].update(policy)
            self.assertTrue(evaluate(data, HEAD, "owner/repo"))

    def test_malformed_payload_does_not_escape_or_expose_payload(self):
        for data in [{}, None, {"pr": "secret://password"}]:
            self.assertEqual(
                evaluate(data, HEAD, "owner/repo"), ["malformed_provider_data"]
            )

    def test_argument_errors_do_not_echo_private_input(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            with self.assertRaises(SystemExit):
                main(
                    [
                        "--repo",
                        "owner/repo",
                        "--pr",
                        "secret://password",
                        "--expected-head",
                        HEAD,
                    ]
                )
        self.assertNotIn("secret", output.getvalue())
        self.assertIn("invalid_input", output.getvalue())

    def test_subprocess_failures_are_closed_and_timeout_is_bounded(self):
        cases = [
            (
                subprocess.TimeoutExpired("private", 15, output=b"secret"),
                "provider_timeout",
            ),
            (OSError("secret://password"), "provider_unavailable"),
        ]
        for error, reason in cases:
            with patch("check_pr.subprocess.run", side_effect=error) as adapter:
                with self.assertRaisesRegex(ProviderFailure, "^" + reason + "$"):
                    fetch(["api", "private"], float("inf"))
                self.assertEqual(adapter.call_args.kwargs["timeout"], 15)
                self.assertEqual(adapter.call_args.args[0], ["gh", "api", "private"])
                self.assertNotIn("shell", adapter.call_args.kwargs)
        for result, reason in [
            (
                subprocess.CompletedProcess([], -15, b"secret", b"secret"),
                "provider_failed",
            ),
            (
                subprocess.CompletedProcess([], 0, b"secret", b"secret"),
                "provider_invalid_json",
            ),
        ]:
            with patch("check_pr.subprocess.run", return_value=result):
                with self.assertRaisesRegex(ProviderFailure, "^" + reason + "$"):
                    fetch([], float("inf"))

    def test_collector_refreshes_reviews_and_rejects_pagination(self):
        data = fixture()
        data["pr"]["baseRefName"] = "main"
        refreshed = copy.deepcopy(data["pr"])
        refreshed["reviews"] = []
        payloads = [
            data["pr"],
            data["protection"],
            {"total_count": len(data["checks"]), "check_runs": data["checks"]},
            data["runs"]["123"],
            {
                "path": ".github/workflows/ci.yml",
                "head_sha": HEAD,
                "pull_requests": [
                    {"number": 1, "base": {"ref": "main"}, "head": {"sha": HEAD}}
                ],
            },
            refreshed,
        ]
        with patch("check_pr.fetch", side_effect=payloads):
            collected = collect("owner/repo", 1, HEAD)
        self.assertIn(
            "independent_current_approval_missing",
            evaluate(collected, HEAD, "owner/repo"),
        )
        with patch(
            "check_pr.fetch",
            side_effect=[
                data["pr"],
                data["protection"],
                {"total_count": 101, "check_runs": data["checks"]},
            ],
        ):
            with self.assertRaisesRegex(
                ProviderFailure, "^provider_pagination_unverified$"
            ):
                collect("owner/repo", 1, HEAD)

    def test_rejects_retargeted_base_in_evaluator_and_refreshed_snapshot(self):
        data = fixture()
        data["pr"]["baseRefName"] = "less-protected"
        self.assertIn("unqualified_base", evaluate(data, HEAD, "owner/repo"))

    def test_rejects_retargeted_base_after_provider_reads(self):
        initial = fixture()
        refreshed = copy.deepcopy(initial["pr"])
        refreshed["baseRefName"] = "less-protected"
        payloads = [
            initial["pr"],
            initial["protection"],
            {"total_count": len(initial["checks"]), "check_runs": initial["checks"]},
            initial["runs"]["123"],
            {
                "path": ".github/workflows/ci.yml",
                "head_sha": HEAD,
                "pull_requests": [
                    {"number": 1, "base": {"ref": "main"}, "head": {"sha": HEAD}}
                ],
            },
            refreshed,
        ]
        with patch("check_pr.fetch", side_effect=payloads):
            with self.assertRaisesRegex(ProviderFailure, "^unqualified_base$"):
                collect("owner/repo", 1, HEAD)

    def test_rejects_same_head_run_from_another_pr_or_base(self):
        for mutate in [
            lambda r: r.update(number=2),
            lambda r: r["base"].update(ref="less-protected"),
            lambda r: r["head"].update(sha=MERGE),
        ]:
            data = fixture()
            mutate(data["runs"]["123"]["pull_requests"][0])
            self.assertIn("run_pr_unverified", evaluate(data, HEAD, "owner/repo"))
        data = fixture()
        data["runs"]["123"]["pull_requests"] = []
        self.assertIn("run_pr_unverified", evaluate(data, HEAD, "owner/repo"))


if __name__ == "__main__":
    unittest.main()

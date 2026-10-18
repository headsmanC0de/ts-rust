"""Read-only premerge detector, not trusted enforcement or merge authorization.

Projects the configured live review policy and exact seven required CI contexts,
not a minimum admission policy or trusted technical review. A valid zero-count,
last-push-disabled policy needs no approval. Otherwise GitHub reviewDecision must
confirm approval and the local projection requires the configured number of current
independent approvals. This reader cannot establish protected compiler acceptance,
immutable workflow trust or artifact lineage.
Review/job pagination completeness is not independently certified by gh JSON.
No merge, protection change, credential output, raw provider errors or payload output.
"""

import argparse
import json
import re
import subprocess
import sys
import time

REQUIRED_CONTEXTS = (
    "Fork configuration contracts",
    "fmt, codegen, clippy",
    "test (ubuntu-24.04)",
    "test (ubuntu-24.04-arm)",
    "test (macos-26)",
    "test (windows-2025)",
    "wasm",
)
QUALITY_STEP = "Run tooling quality contract"
WORKFLOW_PATH = ".github/workflows/ci.yml"
PR_FIELDS = "headRefOid,potentialMergeCommit,baseRefName,state,isDraft,author,reviews,reviewDecision"
ACTIONS_APP_ID = 15368
PROVIDER_TIMEOUT = 15
TOTAL_TIMEOUT = 45


def run_id(check, repo):
    match = re.fullmatch(
        r"https://github\.com/"
        + re.escape(repo)
        + r"/actions/runs/([0-9]+)/job/[0-9]+",
        check["details_url"],
    )
    return match.group(1) if match else None


def successful(item):
    return item["status"] == "completed" and item["conclusion"] == "success"


def evaluate(data, expected_head, repo):
    """Evaluate captured provider fixtures; return only closed reason codes."""
    try:
        return _evaluate(data, expected_head, repo)
    except (KeyError, TypeError, ValueError, AttributeError):
        return ["malformed_provider_data"]


def _evaluate(data, expected_head, repo):
    problems = set()
    pr = data["pr"]
    if pr["baseRefName"] != "main":
        problems.add("unqualified_base")
    if pr["headRefOid"] != expected_head:
        problems.add("stale_head")
    if pr["state"] != "OPEN" or pr["isDraft"]:
        problems.add("pr_not_ready")
    protection = data["protection"]
    contexts = protection["required_status_checks"]["contexts"]
    policy = protection["required_pull_request_reviews"]
    count = policy["required_approving_review_count"]
    last_push = policy["require_last_push_approval"]
    if (
        set(contexts) != set(REQUIRED_CONTEXTS)
        or len(contexts) != len(REQUIRED_CONTEXTS)
        or type(count) is not int
        or count < 0
        or type(last_push) is not bool
    ):
        problems.add("protection_policy_drift")
        return sorted(problems)
    required_approvals = max(count, int(last_push))
    if required_approvals and pr["reviewDecision"] != "APPROVED":
        problems.add("provider_approval_missing")
    latest = {}
    for review in sorted(pr["reviews"], key=lambda r: r["submittedAt"]):
        latest[review["author"]["login"]] = review
    approvals = sum(
        review["state"] == "APPROVED"
        and review["commit"]["oid"] == expected_head
        and login.casefold() != pr["author"]["login"].casefold()
        for login, review in latest.items()
    )
    if approvals < required_approvals:
        problems.add("independent_current_approval_missing")
    identities = {expected_head}
    if pr["potentialMergeCommit"]:
        identities.add(pr["potentialMergeCommit"]["oid"])
    for name in REQUIRED_CONTEXTS:
        matches = [c for c in data["checks"] if c["name"] == name]
        if len(matches) != 1:
            problems.add("required_check_missing_or_duplicate")
            continue
        check = matches[0]
        rid = run_id(check, repo)
        if (
            check["head_sha"] not in identities
            or check["app"]["id"] != ACTIONS_APP_ID
            or check["app"]["slug"] != "github-actions"
            or rid is None
        ):
            problems.add("check_source_unverified")
            continue
        if not successful(check):
            problems.add("required_check_not_successful")
        run = data["runs"][rid]
        if (
            run["headSha"] != expected_head
            or run["event"] != "pull_request"
            or run["path"] != WORKFLOW_PATH
        ):
            problems.add("run_source_unverified")
        associated = [
            p for p in run["pull_requests"] if p["number"] == data["pr_number"]
        ]
        if (
            len(associated) != 1
            or associated[0]["base"]["ref"] != "main"
            or associated[0]["head"]["sha"] != expected_head
        ):
            problems.add("run_pr_unverified")
        if not successful(run):
            problems.add("run_not_successful")
        jobs = [j for j in run["jobs"] if j["name"] == name]
        if len(jobs) != 1 or not successful(jobs[0]):
            problems.add("required_job_not_successful")
            continue
        if name == REQUIRED_CONTEXTS[0]:
            steps = [s for s in jobs[0]["steps"] if s["name"] == QUALITY_STEP]
            if (
                len(steps) != 1
                or not successful(steps[0])
                or type(steps[0]["number"]) is not int
                or steps[0]["number"] <= 0
            ):
                problems.add("quality_step_not_executed_successfully")
    return sorted(problems)


class ProviderFailure(Exception):
    """Only a finite reason crosses the subprocess boundary."""


def fetch(args, deadline):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise ProviderFailure("provider_timeout")
    try:
        result = subprocess.run(
            ["gh", *args],
            capture_output=True,
            timeout=min(PROVIDER_TIMEOUT, remaining),
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ProviderFailure("provider_timeout") from exc
    except OSError as exc:
        raise ProviderFailure("provider_unavailable") from exc
    if result.returncode != 0:
        raise ProviderFailure("provider_failed")
    try:
        return json.loads(result.stdout)
    except (ValueError, UnicodeError) as exc:
        raise ProviderFailure("provider_invalid_json") from exc


def collect(repo, pr_number, expected_head):
    deadline = time.monotonic() + TOTAL_TIMEOUT
    pr = fetch(
        [
            "pr",
            "view",
            str(pr_number),
            "--repo",
            repo,
            "--json",
            PR_FIELDS,
        ],
        deadline,
    )
    if pr.get("headRefOid") != expected_head:
        raise ProviderFailure("stale_head")
    # main is the admitted policy target; a less-protected PR base is not authority.
    if pr.get("baseRefName") != "main":
        raise ProviderFailure("unqualified_base")
    protection = fetch(["api", f"repos/{repo}/branches/main/protection"], deadline)
    identity = (pr.get("potentialMergeCommit") or {}).get("oid", expected_head)
    checks = fetch(
        ["api", f"repos/{repo}/commits/{identity}/check-runs?per_page=100"], deadline
    )
    if checks["total_count"] > len(checks["check_runs"]):
        raise ProviderFailure("provider_pagination_unverified")
    runs = {}
    for check in checks["check_runs"]:
        if check["name"] not in REQUIRED_CONTEXTS:
            continue
        rid = run_id(check, repo)
        if rid and rid not in runs:
            runs[rid] = fetch(
                [
                    "run",
                    "view",
                    rid,
                    "--repo",
                    repo,
                    "--json",
                    "headSha,event,status,conclusion,jobs",
                ],
                deadline,
            )
            metadata = fetch(["api", f"repos/{repo}/actions/runs/{rid}"], deadline)
            runs[rid]["path"] = metadata["path"]
            runs[rid]["pull_requests"] = metadata["pull_requests"]
            if metadata["head_sha"] != expected_head:
                raise ProviderFailure("run_source_unverified")
    # Detect a push racing the metadata/check reads.
    current = fetch(
        ["pr", "view", str(pr_number), "--repo", repo, "--json", PR_FIELDS], deadline
    )
    if current.get("baseRefName") != "main":
        raise ProviderFailure("unqualified_base")
    if current.get("headRefOid") != expected_head:
        raise ProviderFailure("stale_head")
    return {
        "pr_number": pr_number,
        "pr": current,
        "protection": protection,
        "checks": checks["check_runs"],
        "runs": runs,
    }


class PrivateArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(
            json.dumps(
                {"detector": "premerge", "passed": False, "reasons": ["invalid_input"]}
            )
        )
        self.exit(2)


def main(argv=None):
    parser = PrivateArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--expected-head", required=True)
    args = parser.parse_args(argv)
    if (
        not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repo)
        or args.pr <= 0
        or not re.fullmatch(r"[0-9a-f]{40}", args.expected_head)
    ):
        reasons = ["invalid_input"]
    else:
        try:
            reasons = evaluate(
                collect(args.repo, args.pr, args.expected_head),
                args.expected_head,
                args.repo,
            )
        except ProviderFailure as exc:
            reasons = [str(exc)]
        except (KeyError, TypeError, ValueError, AttributeError):
            reasons = ["malformed_provider_data"]
    print(
        json.dumps({"detector": "premerge", "passed": not reasons, "reasons": reasons})
    )
    return int(bool(reasons))


if __name__ == "__main__":
    sys.exit(main())

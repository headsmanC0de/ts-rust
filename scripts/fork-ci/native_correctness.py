"""Run the unchanged native suite with bounded, non-secret failure context."""

import json
import mmap
import os
import platform
import re
import subprocess
import sys
import time
from collections import deque
from pathlib import Path

COMMAND = ["cargo", "test", "--release", "--locked", "--workspace", "--no-fail-fast"]


def event(status, elapsed, **fields):
    sha = os.environ.get("GITHUB_SHA", "")
    run = os.environ.get("GITHUB_RUN_ID", "")
    print(
        json.dumps(
            {
                "event": "native-correctness",
                "status": status,
                "source_sha": sha
                if re.fullmatch(r"[0-9a-f]{40}", sha)
                else "unavailable",
                "run_id": run if run.isdecimal() else "unavailable",
                "test_scope": "release-workspace-no-fail-fast",
                "elapsed_seconds": round(elapsed, 3),
                **fields,
            }
        ),
        flush=True,
    )


def runtime_context():
    context = {
        "kernel": platform.release(),
        "architecture": platform.machine(),
        "logical_cpus": os.cpu_count(),
        "page_size": mmap.PAGESIZE,
    }
    if hasattr(os, "sched_getaffinity"):
        context["affinity_cpus"] = len(os.sched_getaffinity(0))
    for name in ["cpu.max", "cpuset.cpus.effective"]:
        path = Path("/sys/fs/cgroup") / name
        if path.is_file():
            context[name] = path.read_text().strip()[:128]
    for key in [
        "GOMAXPROCS",
        "GOPORT_EMIT_THREADS",
        "CARGO_BUILD_JOBS",
        "RUST_TEST_THREADS",
    ]:
        value = os.environ.get(key, "")
        context[key] = value if value.isdecimal() else "unset-or-invalid"
    return context


def annotation(text):
    # Escape workflow-command data, including hostile multiline panic messages.
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def main():
    started = time.monotonic()
    event("start", 0, runtime=runtime_context())
    failures = deque(maxlen=16)
    after_panic = False
    try:
        process = subprocess.Popen(
            COMMAND, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
    except OSError as error:
        event(
            "failure",
            time.monotonic() - started,
            exit_code=127,
            launch_error=type(error).__name__,
        )
        print(
            "::error title=Native correctness suite failed::Unable to start cargo ("
            + type(error).__name__
            + ").",
            flush=True,
        )
        return 127
    for line in process.stdout:
        print(line, end="", flush=True)
        plain = re.sub(r"\x1b\[[0-9;]*m", "", line).strip()
        if after_panic or re.search(r"FAILED|panicked at|error: test failed", plain):
            failures.append(plain[:400])
        after_panic = "panicked at" in plain
    child_status = process.wait()
    status = 128 - child_status if child_status < 0 else child_status
    event(
        "failure" if status else "success", time.monotonic() - started, exit_code=status
    )
    if status:
        detail = (
            "\n".join(failures)
            or "Native suite exited without a parsed test failure; inspect this step's complete log."
        )
        print(
            "::error title=Native correctness suite failed::" + annotation(detail),
            flush=True,
        )
    return status


if __name__ == "__main__":
    sys.exit(main())

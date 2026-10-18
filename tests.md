# Tooling verification

The shared entrypoint is [quality.sh](scripts/fork-ci/quality.sh), using an explicitly
prepared Python environment from [requirements](scripts/fork-ci/requirements.txt).
It performs lint, format checking, workflow mutation tests and benchmark CLI tests.

MUST observe a failing behavioral oracle, make the smallest fix, then retain terminal
evidence and independent review. Fake only external OS/provider adapters for dispatch.
MUST cover missing/malformed/duplicate evidence, crashes, timeout, stale oracle, overlays,
default/fast separation, multiline/multiplicity, overflow/underflow and late-case failure.
MUST reject removed/skipped/ignored quality execution. test_quality.py owns scoped source
line budgets and rule-link discovery.

Compiler work still requires the full [protected set](docs/typechecker-accountability.md).
Tooling tests do not establish compiler, production, portfolio or LSP acceptance.
Local runtime belongs on the declared VM. The shell guard refuses unsupported hosts
before project Python. Exact-SHA provider job AND step success need independent readback.

Temporary Git fixtures MUST clear repository-scoped Git environment before invoking
Git, including when the suite itself runs inside a real hook. A disposable outer
repository must retain HEAD, config, index and hooks after the nested suite. Direct
manual invocation alone does not verify hook-environment isolation.

# Tooling architecture

common.sh produces preflight/timing output; verify.py owns complete diagnostic/process
comparison; summary.py selects physical evidence per tool, admits inputs and math,
then renders once. test_workflows.py owns CI trust/coverage. quality.sh is the shared
local/CI interface; ruff.toml owns lint/format scope; requirements owns tool identities.

One verifier serves CLI and report consumers. Default and fast are compared separately
against the selected oracle; Effect and plain TypeScript have distinct pinned contracts.
Quality events expose closed stage, terminal status, exit code and elapsed seconds.
Started-without-terminal is visible failure debt, not a successful stage.
These events are not fabricated OpenTelemetry spans.

OPEN: immutable source/binary/config metadata binding and an independently trusted
provider premerge reader. Extra logs or green unit tests do not close those gaps.

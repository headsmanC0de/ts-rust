# Executable guard registry

Scope: fork tooling. A link, configuration or installed process is not enforcement;
retain an actual invocation receipt. The shared interface is `scripts/fork-ci/quality.sh`.

| Guard | Executable owner / negative oracle | Acceptance limit |
|---|---|---|
| Python lint/format | pinned Ruff + ruff.toml; undefined name/unsafe dynamic execution/mismatch | scoped tooling static checks only |
| Workflow trust and coverage | test_workflows.py; removed/skipped/ignored invocation, wrong runner/token | configuration tests, exact provider execution separate |
| Rules/hook reachability | test_rules_contract.py and owning quality tests; missing rule/wiring/size | references/configuration, not agent reasoning |
| Completion | verify.py; crash, missing receipt, unknown output, mismatched exits | CLI regression; not full compiler conformance |
| Selected/atomic report | summary.py; stale oracle, failed overlay, invalid math, late failure | CLI fixture admission; selected binary provenance separate |
| Local dispatch | quality.sh and dispatch tests; failed/timeout/unsupported host | native negative oracles; no automatic install/fallback |
| Early native failure context | native_correctness.py + tests; hostile text/nonzero/signal | actual native failure event and retained exit required |
| Pool capability | native fixture env + emit_pool_policy.rs | native Rust/platform RED/GREEN required |
| Hook preservation | install.sh + test_hook_install.py; foreign hook/identity/inherited context | nested temporary-Git proof; actual hook invocation separate |
| Merge evidence projection | check_pr.py; stale head/base/wrong PR, absent/skipped check/step, missing approval | 17 fixtures; read-only detector, not trusted enforcement or merge authority |
| Rust static checks | retained cargo fmt/codegen/clippy job | not runtime, emit or artifact acceptance |
| Release acceptance | protected suites and independent source-bound verdicts | ordinary CI never replaces upstream accountability |

Root hook policy rejects project checks on Mac and uses the declared runtime host.
Dependencies must already be prepared and exact; missing tools fail closed.
Local hook installation does not make it tamperproof or authorize publication.
Current ARM allocator findings remain open until measured; no table claims them fixed.
Metadata lineage and trusted remote enforcement remain OPEN, not closed by more logs.
Findings: [native/CI incidents](docs/recurring-problems-2026-10-18.md) and
[benchmark history](docs/audits/2026-10-18-recurring-problems.md).

The native wrapper forwards full Cargo output from the public synthetic compiler
fixtures. Its tests do not certify redaction of arbitrary secrets in child output;
private application inputs require their own capture-boundary policy and oracle.

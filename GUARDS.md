# Executable guard registry

Scope: the fork. A link or installed process is not enforcement; retain an actual invocation receipt.

| Guard | Executable owner | Wiring | Acceptance limit |
|---|---|---|---|
| Python lint and formatting | pinned Ruff, ruff.toml, quality.py | fast CI job and lefthook pre-commit | static checks only |
| Workflow trust and retained coverage | test_workflows.py | quality.py unittest discovery | configuration only |
| Early native failure context | native_correctness.py and behavioral tests | native correctness CI step | actual failure event required |
| Pool capability | native CI fixture env and emit_pool_policy.rs | release workspace tests | Rust RED/GREEN and all platform evidence required |
| Rules and hook reachability | test_rules_contract.py | quality.py unittest discovery | validates references/wiring, not agent reasoning |
| Rust static checks | cargo fmt/codegen/clippy | retained CI lint job | not runtime or emit proof |
| Release acceptance | existing protected suites and independent reviewers | original accountability pipeline | ordinary CI does not replace it |

Root hook policy rejects project checks on Mac and runs them on an admitted runtime host. Missing dependencies fail closed; no hook auto-installs or silently switches to a global tool. Configured hooks become installed enforcement only after the actual hook is installed and run.

The current ARM allocator assertion remains open. No guard here declares it fixed. Findings and blind spots: [recurring problems](docs/recurring-problems-2026-10-18.md).

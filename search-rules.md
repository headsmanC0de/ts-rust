# Search and repair

Scope: Moonrock fork changes. The executable fast entrypoint is
`scripts/fork-ci/quality.sh`; native compiler correctness remains separate.

- MUST find the exact error, symbol, caller, producer, selector, consumer and existing test before editing; inspect profiles, config inheritance and process exits. Prose-only typos are exempt from runtime diagnosis.
- MUST inspect the introducing diff and primary upstream source; record bounded history and first proven divergence. Commit subjects are not root causes; interrupted searches are Partial.
- MUST distinguish desired, declared, configured, executed and accepted evidence. A source-identical reference binary is not a reproducible local build.
- MUST use targeted `rg` where available, otherwise Git search. Inspect owning-file history and callers; search parents before assuming child configuration is independent.
- MUST use pinned Ruff for Python and existing Cargo fmt/clippy for Rust. Versions belong to owning requirements/toolchain, not copied instructions or a second formatter.
- MUST keep tunables and reused domain policy at one owning config or named constant. Protocol keys, immutable source IDs and negative-test values remain independent oracles; do not create an arbitrary string database.
- MUST preserve unrelated files and split touched oversized owners by responsibility. No repository-wide formatting during repair.
- MUST NOT treat absence, timeout, skipped work, silent logs, unknown status or installed YAML as successful execution.

Behavior and independent oracles: [TESTS.md](TESTS.md). Enforcement and gaps:
[GUARDS.md](GUARDS.md). Ruff structural scope: [ruff.toml](ruff.toml).
A string counter, lint pass or formatter cannot prove compiler correctness or search quality.

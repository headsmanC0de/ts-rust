# Search and static checks

Scope: Moonrock fork changes. The executable fast entrypoint is `scripts/fork-ci/quality.py`; native correctness remains a separate gate.

- MUST locate the exact error, symbol, caller and existing test before editing. Use targeted `rg`/Git search, then the incident and primary upstream source. Exception: prose-only typo. Example: locate `emit_thread_count` and its fixture assertions before changing CI workers.
- MUST record a bounded history scope and the first proven divergence. An interrupted history search is Partial, never an exhaustive audit.
- MUST distinguish declared, configured, executed and accepted evidence. A source-identical reference binary is not a reproducible local build.
- MUST use Ruff for Python lint/format and existing Cargo fmt/clippy for Rust. Versions belong to requirements and the owning CI toolchain; do not add a second formatter.
- MUST keep expected-output oracles independent from implementation and retain protected test names. CPU/page-size assumptions need runtime tests, not a new formatting rule.
- MUST keep tunables in one owning config. Protocol keys, immutable source IDs and test boundary values are not mutable business policy; give reused semantics a name instead of moving arbitrary strings into a database.
- MUST preserve unrelated files and split touched oversized code by responsibility. Avoid repository-wide formatting during a repair.

Enforcement and gaps: [GUARDS.md](GUARDS.md). Search reasoning itself remains independently reviewed; a lint pass cannot prove an agent searched correctly.

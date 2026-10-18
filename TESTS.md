# Fork testing contract

Before correctness work read [upstream accountability](docs/typechecker-accountability.md)
and [fork execution](docs/fork-qualification.md). Existing protected names, goldens,
source identities and oracle pins remain authoritative.

| Boundary | Required cases | Evidence |
|---|---|---|
| Workflow trust | inaccessible runner, privileged token/trigger, mutable action, skipped inherited step, wrong publisher | independent workflow mutations |
| Emit-pool fixture | explicit positive workers, original emit/emit_batch output and deliberate panic assertions | unchanged emit_context/emit_pool suites |
| Production pool admission | low-core default, spare-core default, positive override, explicit zero, single-threaded | fresh-process emit_pool_policy native suite |
| Allocator layout | kernel versus logical page size, classes, retained extents, alignment residues, native ARM | original jemalloc_layout and diagnostic reproduction; unresolved until measured |
| Compiler evidence | missing/malformed/duplicate receipts, unknown output, panic/unported, signal, timeout, stale oracle, multiline/multiplicity | complete-stream CLI and process oracles |
| Effective report selection | base/limited overlay provenance, normal/fast separation, timed exits, overflow/underflow, incomplete T3, late failure | selected inputs admitted before any public table |
| Quality tools | missing/mismatched dependency, lint/format/subprocess failure, unsupported host, no automatic install | entrypoint negative tests and actual invocation |
| Hooks and Git fixtures | identity/foreign hook preservation, matching idempotence, shared paths, inherited Git context | real temporary-Git installer tests and nested outer-repository invariant |
| Source admission | changed inputs, absent platform/result, matching nonzero diagnostics | exact source/toolchain/oracle receipts; Unknown is not PASS |

Fast local/CI command: `FORK_PYTHON=<prepared-env>/bin/python scripts/fork-ci/quality.sh`.
Prepare only the explicit environment from [requirements](scripts/fork-ci/requirements.txt).
This gate runs lint, format checking, workflow/rules/dispatch and benchmark tests;
it does not replace native release, packaging, protected acceptance or real UI browser checks.

MUST observe RED at the actual behavior seam, make the smallest fix and retain GREEN
plus independent review. Fake only external OS/provider adapters when testing dispatch.
MUST NOT remove/skip/ignore a quality invocation, change goldens, disable an optimization,
weaken an assertion or increase a timeout merely to obtain green. Capability exceptions
need proven applicability, named owner and explicit results.

Temporary Git fixtures MUST remove ALL inherited `GIT_*` before any Git invocation,
then explicitly set fixture-only config isolation. Run the actual child suite under a
disposable outer Git context; preserve its HEAD/config/index/refs/worktrees/logs/hooks.
Direct manual invocation alone cannot prove real-hook environment isolation.

For each run retain exact source/input/tool/oracle identity, command, capability,
monotonic duration, exit/signal and evidence location. Diagnose one variable at a time;
redact before capture under [SECURITY.md](SECURITY.md), never dump raw environment.
The source cap and rule references are checked by the owning quality/rules tests;
a configured guard is distinct from an exact-SHA provider job AND step result.

Compiler revisions retain the full [protected set](docs/typechecker-accountability.md#protected-set)
and both independent verdicts against the last accepted revision. Never replace the
accepted baseline with a failing candidate: missing names/evidence, unrun tests,
source mismatches and unexplained lost passes block acceptance; new passes do not compensate.
Use existing candidate/name-map/per-test/gate/LSP/API comparisons and retain every run.
Expectation or protected-path changes require pinned Go evidence and the owning
accountability approval. Record failed/unaccepted revisions before continuing; do not
reset counters after compaction, agent replacement, branch or batch rename.

Current findings have distinct scopes: [native/CI incidents](docs/recurring-problems-2026-10-18.md)
and [benchmark/evidence history](docs/audits/2026-10-18-recurring-problems.md).
Statuses live in source-bound receipts and the canonical task graph, not a manually green checklist.

Benchmark receipt regressions exercise actual CLI/shell boundaries: per-stem normal/FAST
identity, partial/no-clobber reservation, changed binary/config, tampered artifacts,
atomic replacement between reads and ambient fast-mode overrides. Consumers parse
verified byte snapshots. Application node_modules and undeclared dependencies are
outside the recorded input closure; a receipt does not prove they stayed immutable.

Allocator observation helpers must compile with the owning unsafe-code prohibition.
Parser tests prove bounded numeric/closed-policy output, unknown handling and malformed
range safety; native ARM geometry and protected compiler acceptance remain separate.

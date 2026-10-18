# Fork testing contract

Before correctness work, read [upstream accountability](docs/typechecker-accountability.md) and [fork execution](docs/fork-qualification.md). Existing protected names, goldens and oracle identities remain authoritative.

## Required behavior

| Boundary | Required cases | Evidence |
|---|---|---|
| Workflow trust | inaccessible runner, privileged trigger/token, mutable action, skipped inherited step, wrong publisher | workflow contract negative mutations |
| Emit-pool fixture | explicit positive fixture workers; original emit/emit_batch output and panic assertions | unchanged emit_context and emit_pool suites |
| Production pool admission | low-core default, spare-core default, positive override, explicit zero, single-threaded | fresh-process emit_pool_policy suite; actual Rust execution required |
| Allocator layout | kernel and jemalloc logical pages, size classes, retained extents, alignment residues; native ARM | original jemalloc_layout assertion plus actual diagnostic repro; unresolved until measured |
| Failure reporting | nonzero exit, signal, missing executable, hostile annotation text, no secret environment dump | native wrapper behavioral tests |
| Quality tools | missing/mismatched dependency, lint/format failure, subprocess failure, no automatic install | quality entrypoint tests and real invocation |
| Source admission | changed inputs, absent platform/result, stale artifact, matching nonzero diagnostics | exact source/toolchain/oracle receipts; Unknown is not PASS |

The fast command is `python scripts/fork-ci/quality.py`. It does not replace native release tests, browser testing for actual UI changes, packaging or protected acceptance. Use the capped Cargo adapter from the fork execution contract for focused Rust reproductions.

MUST retain RED and GREEN at the same behavioral seam. MUST NOT skip a failing platform, change goldens, disable an optimization or increase a timeout merely to obtain green. A capability exception needs a proven applicability boundary, named owner and explicit test result.

For every run retain source and input identity, command, runtime capability, monotonic duration, exit/signal, tool identity and evidence location. Diagnose a single variable at a time. Log only boundary facts needed to separate hypotheses; raw environment dumps are forbidden by [SECURITY.md](SECURITY.md).

Current findings: [recurring problems](docs/recurring-problems-2026-10-18.md). Current statuses belong to linked run receipts and the canonical Agent task graph, not a manually green checklist.

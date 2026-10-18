# Portable native qualification implementation plan

> For agentic workers: use the current bounded ownership ledger and subagent-driven-development; root owns Cargo, integration and provider writes.

Goal: preserve all native correctness assertions while making fixture capabilities explicit and failures visible before later CI stages.

Architecture: retain the compiler and protected acceptance owners. Repair fixture activation at its CI adapter, investigate allocator geometry at the real allocator boundary, and connect scoped policy to a fast executable quality entrypoint. No production fallback or expectation weakening.

Tech stack: Rust release tests, GitHub Actions, Python workflow contracts, pinned static tools and Lefthook.

Spec: docs/fork-qualification.md and the owner request for recurring-problems research on 2026-10-18.

## Constraints

- Preserve old accepted state, test names, fixtures and expected outputs.
- Runtime work on the admitted VM; no Mac builds/tests/browser launches.
- One compiler/runtime writer; each investigator has disjoint report or fixture ownership.
- Source/command/toolchain/oracle/host-capability identity belongs with each result.
- A configured guard is not an executed guard. Report Unknown/Unrun/Blocked explicitly.

## Review focus

- Low CPU budget with no spare emit workers must still use the correct production fallback.
- Positive fixture workers, explicit zero and single-threaded mode must exercise distinct paths.
- Kernel page size and jemalloc logical page size are different inputs.
- A failing early stage must publish a bounded redacted error before later stages finish.
- Missing tools, stale receipts, changed source and absent platform evidence fail closed.

## Tasks

- [ ] Capture first divergence, actual failures and scoped root-cause confidence in recurring-problems research.
- [ ] RED: require explicit emit-fixture capability and test real policy in isolated child processes.
- [ ] Repair native correctness adapter; retain full-suite assertions and default/zero/single controls.
- [ ] Diagnose ARM allocator geometry using actual page/size-class evidence; no guessed fix or skip.
- [ ] Add scoped search/testing/security/design/guard adapters and one lint/format/hook entrypoint; verify actual invocation and negative cases.
- [ ] Run focused release reproductions, independently review exact source, then rerun complete native matrix.
- [ ] Reconcile canonical child tasks and evidence pointers; merge only through seven required checks and independent agent review.

# Recurring tooling failures — 2026-10-18

Scope: fork benchmark tooling, its CI admission and hook installation. This is not a
compiler correctness certificate or an application production acceptance.

| Pattern and first divergence | Root cause / why previous repairs missed it | Sufficient repair and evidence | Remaining risk |
| --- | --- | --- | --- |
| Diagnostic comparison: 69f0a1 → 61492 → dacabc | Better parsing still accepted incomplete process evidence | verify.py requires complete receipts and rejects crashes, unknown output and multiplicity loss; CLI regressions | Diagnostic equivalence does not prove all compiler semantics |
| Timing publication: 0134 → 6eb7 → 761aa | Overlay and FAST timings were not bound to their selected diagnostic stream | summary.py validates each selected tool, receipt, timed exit and finite derived math before any output; negative CLI tests | Metadata identity can still be overwritten between variants |
| Guard present but not required | A standalone successful job did not imply admission | 4fdf binds benchmark tests to the existing required contract; shared quality runner now executes lint, format and behavior | Untrusted workflow source can still alter its own checks |
| Hosted emit tests: 7d202ec3 → 4b51b8d4 → hosted runner migration | Resource prerequisite removed for larger runners was not restored for smaller runners | Retain parent fixture-only positive override1 and separate production policy cases; workflow mutation test rejects omission | Native four-platform rerun still required |
| Repeated cold Rust builds | Main-only cache writes and omitted workspace crates | PR-scoped workspace cache; exact allowed configuration checked; tests never skipped on a cache hit | Cold/warm elapsed comparison still required |
| Hook installer modifies identity and replaces hooks | Installer had no executable safety contract | Real temporary-Git regressions require identity preservation, foreign-hook refusal, idempotency and shared worktree paths | Local hooks remain bypassable |
| Hook fixture escapes temporary repository | Git hook exports repository-scoped environment; direct fixture runs did not exercise it | Add nested-suite hook-environment regression and sanitize fixture Git environment before every Git invocation | Actual commit-hook run must pass, beyond manual lefthook dispatch |
| Missing style/security gate | Documentation was not an executed toolchain contract | Hash-locked Ruff, explicit rules, formatter checks and negative oracles inside the required job | Ruff is not a semantic security proof |
| Green job mistaken for executed work | Skipped/neutral statuses and stale review state were not independently checked | Read-only exact-head premerge detector checks app/run/job/step identity, current PR/base association and configured review policy | Detector must be wired into independent trusted enforcement |

## Rules and scope

The short AGENTS.md routes to search-rules.md, TESTS.md, DESIGN.md, SECURITY.md,
CYBERSECURITY.md and GUARDS.md. Each owns one concern. Numeric domain configuration
belongs to its owning configuration; protocol literals and intentionally invalid
test fixtures are legitimate literals, not candidates for arbitrary centralization.

The local runner emits closed stage names, terminal status, exit code and elapsed
seconds. These events expose the slow or failed stage without recording private
diagnostics. They are not distributed tracing spans. Future immutable benchmark
metadata must bind source/config/compiler hashes and selected evidence identity.

## Alternatives assessed

More prose is cheap but does not stop recurrence. More end-to-end tests detect
integration faults but are slower and often miss evidence-selection defects.
A broad compiler rewrite has the largest uncertainty and is not justified by these
tooling failures. The chosen combination is small executable contracts at the
producer/consumer boundary, fast negative CLI tests, native platform tests and an
independent provider readback. Keep each layer honest about its scope.

## Verified state

The shared quality runner passed 62 workflow/security/hook tests and 49 benchmark
CLI tests, plus Ruff lint and formatting, on Linux on 2026-10-18. The live detector
rejects the current stacked PR base rather than treating it as protected main.
A separate read-only main-protection receipt shows zero approvals and no last-push
approval. The integrated parent report records explicit owner authorization for this
single-owner model. Our initial classification as unauthorized drift was incorrect;
the detector is corrected to evaluate the configured policy. This work changed no
protection setting; independent technical review remains separate evidence.

ARM allocator geometry remains unresolved. Failure-only scalar diagnostics retain
the original assertion; neither skipping the test nor changing allocator geometry
is an accepted repair without native evidence. See KANBAN.md for open work.

## Primary references

- [Rust cache pinned implementation](https://github.com/Swatinem/rust-cache/tree/6323deb102c322ba6fcbdcafc7e3dddab59af2b6)
- [GitHub cache access restrictions](https://docs.github.com/en/actions/using-workflows/caching-dependencies-to-speed-up-workflows#restrictions-for-accessing-a-cache)
- [GitHub required status checks](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches#require-status-checks-before-merging)
- [Ruff linter](https://docs.astral.sh/ruff/linter/)
- [Ruff formatter](https://docs.astral.sh/ruff/formatter/)
- [Lefthook installation](https://lefthook.dev/installation/index.html)

## Verification incident

The first real commit-hook execution exposed a fixture isolation defect: inherited
Git variables made temporary-Git commands target the owning repository. The hook
failed closed before publication, but a fixture commit and local configuration
changes had already occurred. Source and refs were preserved privately before
recovery; no remote push occurred. The unpublished fixture commit is preserved by a
recovery ref. Local identity recovery uses the preceding own commit because the
original config bytes were not captured. The new regression must prove outer
HEAD/config/index/hooks remain unchanged under an inherited hook environment.

## Integrated parent changes

PR #5 advanced independently to 62b004f2 while this work was in progress, preventing
a PR test-merge and CI dispatch. Merge the parent into the child before acceptance;
retain its native wrapper, fixture-only pool1 and production pool policy tests.
The dependency verifier is now a single dedicated module before the shared shell
runner's lint/format/workflow/benchmark stages. Uppercase topic documents are the
owners; lowercase duplicates are removed. Parent native/CI history remains in
[the native findings](../recurring-problems-2026-10-18.md); this report owns benchmark
history and the commit-hook isolation incident.

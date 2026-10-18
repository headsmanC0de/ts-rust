# Compiler and tooling qualification design

This is a maintained source compiler fork, not a product UI. Consumer themes, locales,
popups and browser acceptance cannot be inferred from compiler tests.
The qualification unit is one immutable tuple: source inputs, toolchain, flags/profile,
oracle/lib identity, artifact digest and applicable host capabilities. Consumers reuse
an admitted artifact through existing tooling owners; no competing builds or hidden fallback.

`common.sh` produces preflight/timing output; `verify.py` owns complete diagnostic/process
comparison; `summary.py` selects physical evidence per tool, admits inputs and derived
math, then renders once. One verifier serves CLI/report consumers. Normal and fast
variants compare separately with their selected oracle; Effect and plain TypeScript
have distinct pinned contracts.

`scripts/fork-ci/quality.sh` is the single local/CI interface; `ruff.toml` owns static
scope and requirements owns tool identities. Workflow/rules tests own executable wiring.
Native failure context has one boundary: retain Cargo command/status with bounded facts
and early annotations. Quality events expose closed stage, terminal status, exit and
elapsed time; started-without-terminal is unresolved failure debt, not fabricated OTel spans.

Runtime defaults belong to the compiler. Fixtures declare required capabilities and
separately test default/disabled paths. Kernel pages, allocator logical pages and CPU
budget are distinct inputs. Use existing interfaces before adding a wrapper.
Compiler work retains saved-state/accountability ordering, one writer, independent
reviewer/auditor, protected comparisons, ordinary-input locks and pinned Go execution.
Do not rewrite append-only history, alter past outputs or use a later failure as baseline.

Immutable metadata binding and trusted provider enforcement remain separate acceptance
work; additional logs, fixture passes or a read-only detector do not establish them.
Policy owners: [search](search-rules.md), [behavior](TESTS.md), [guards](GUARDS.md),
[controls](SECURITY.md), [threats](CYBERSECURITY.md). AGENTS only navigates these owners.

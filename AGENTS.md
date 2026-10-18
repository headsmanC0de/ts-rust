# Fork execution entrypoint

Before work, read [execution](docs/fork-qualification.md) and [search rules](search-rules.md).
For implementation, read [tests](tests.md), [design](design.md) and [guards](guards.md).
For subprocesses/evidence read [source security](security.md); for hooks, credentials,
provider CI or publishing read [operational security](cybersecurity.md).

Before compiler changes or compiler runs, read in order:
1. [Typechecker accountability](docs/typechecker-accountability.md).
2. Run scripts/state summary; read docs/typechecker-state/current.json.
3. [Typechecker reset plan](docs/typechecker-reset-plan.md).

The protected compiler set, exact source identity, capped Cargo runner, single compiler
writer and independent reviewer/auditor remain mandatory. Historical upstream
authorizations and PASS records grant no fork permissions.
The fork execution contract owns host selection and resource limits.
The shared tooling interface is scripts/fork-ci/quality.sh.
A configured guard does not prove live enforcement; record exact-SHA job and step results.

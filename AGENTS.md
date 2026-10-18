# Fork execution entrypoint

Before work read [fork execution](docs/fork-qualification.md) and [search rules](search-rules.md).
For implementation read [TESTS.md](TESTS.md), [DESIGN.md](DESIGN.md) and [GUARDS.md](GUARDS.md).
For subprocesses and evidence read [SECURITY.md](SECURITY.md); for hooks, credentials,
provider CI and publishing read [CYBERSECURITY.md](CYBERSECURITY.md).

Before compiler changes or compiler runs, read in order:
1. [Typechecker accountability](docs/typechecker-accountability.md).
2. Run `scripts/state summary`; read `docs/typechecker-state/current.json`.
3. [Typechecker reset plan](docs/typechecker-reset-plan.md).

Re-read after a reset or new goal; missing or inconsistent required state means STOP.
The linked compiler accountability, protected-set, saved-state and preservation
requirements remain mandatory; the fork adapter overrides historical host identities
and authorization, never diagnostic/type/symbol acceptance or independent verdicts.
Keep one compiler writer, one independent reviewer and one regression auditor;
root owns integration and the runtime queue. A STOP permits only scoped diagnosis,
repair or withdrawal, not new feature work or acceptance.
Use the existing capped Cargo runner and declared host/resource limits.
Preserve dirty work, ordinary project inputs, immutable history and failed evidence.
Historical upstream authorizations, saved PASS records and old branches grant no
fork permissions or acceptance. Never force-push or bypass a failed guard.
The shared local/CI tooling interface is `scripts/fork-ci/quality.sh`.
Configured, executed and accepted are distinct: retain exact-SHA job and step readback.

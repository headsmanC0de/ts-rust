# Operational trust and threat model

Executable controls live in [SECURITY.md](SECURITY.md); runtime host and resource limits
live in the [fork adapter](docs/fork-qualification.md). MacBook is editing/Git/SSH unless
current owner explicitly authorizes project runtime. Historical upstream access is not permission.

| Threat | Control owner | Remaining limit |
|---|---|---|
| Fork inherits upstream publishing/runner trust | workflow repository guards + mutation tests | fork release publishing not admitted |
| Mutable action/dependency executes changed code | immutable action pins + hash-locked requirements | pinning is not a security audit |
| Diagnostics disclose private context | capture-boundary whitelist + wrapper tests | each producer needs adversarial verification |
| Missing/skipped work appears green | testing contract + exact-SHA job/step readback | self-checks cannot prove a skipped job executed |
| Stale/self-approved evidence enters release | bound checks + independent verdicts | trusted automated enforcement not established |
| Hook overwrites identity/foreign guard or fixture reaches real repo | safe installer + ALL-GIT-env isolation/nested fixtures | configured, installed and actually invoked differ |

Inventory and preserve Git identity/hooks before installation; refuse foreign hooks.
Installing a guard never authorizes publishing. Never bypass reviews, protection,
scanners or failed compiler tests; preserve rewritten-history pre-push protection and
never force-push historical branches. Credentials remain with existing provider/role
loaders and never appear in logs. This quality lane needs no production secrets.

Before merge independently read exact head/test-merge SHA, expected application,
required contexts, actual successful jobs/quality step and the configured provider
approval policy. The owner-approved single-owner fork can use zero provider reviews;
independent technical verdicts remain separate source-bound evidence.
The detector projects context/approval policy only; other protection settings and
provider review/job pagination completeness are not independently certified.
Detector PASS is evidence, never sufficient merge authority, artifact lineage or compiler acceptance.
Trust-boundary changes require scoped adversarial regressions and independent review.

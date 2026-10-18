# Threat model

This file owns the threat map; executable control policy lives in [SECURITY.md](SECURITY.md).

| Threat | Control owner | Remaining limit |
|---|---|---|
| Fork inherits upstream publisher/runner trust | workflow repository guards and workflow contracts | fork release publishing is not admitted |
| Mutable action/dependency changes executed code | full action commit pins and hash-locked requirements | upstream code is not independently audited by pinning |
| Debug artifacts disclose private context | security whitelist; native-wrapper tests | each new producer needs capture-boundary verification |
| Absent test cell reported green | testing/evidence contract and protected acceptance | source review and a configured guard alone are insufficient |
| Stale or self-approved evidence enters release | source-bound checks and independent verdicts | automated verdict publication is not established |

Changes to the trust boundary need a scoped adversarial regression and independent review. Credentials stay with their declared provider and role.

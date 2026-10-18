# Fork security controls

Scope: this public compiler fork, helper code, artifact parsing and CI.
[CYBERSECURITY.md](CYBERSECURITY.md) owns threats; [GUARDS.md](GUARDS.md) records enforcement limits.

- MUST run untrusted PR code on isolated hosted runners without private VM access, production secrets or publishing authority. Preserve excluded upstream-workflow repository guards.
- MUST pin actions to immutable official commits and exact hash-locked dependencies in owning files; identity is not an independent audit.
- MUST keep checkout credentials unpersisted and ordinary CI contents-read-only. Do not copy deployment credentials into diagnostics.
- MUST use argument vectors for dynamic subprocess inputs; reject eval/exec/dynamic shell evaluation and swallowed failures.
- MUST retain completion, error type and real exit status; selected variant/oracle and every derived value are admitted before public output.
- MUST redact before capture. Whitelist CPU/cgroup/kernel/page-size facts and numeric alignment residues; never dump environment, headers, cookies, credentials, DSNs or private source.
- MUST retain raw experimental evidence privately with owner-only access; publish reviewed bounded summaries, closed stage/tool labels and source identities only. Never echo unvalidated receipt rows.
- MUST preserve failed evidence; no silent compiler fallback, bypassed hook, administrative merge override or false success.

Synthetic negative fixtures may contain unsafe text; inspect without executing the text.
A single-owner repository still needs PR checks and independent exact-source verdicts.
Provider settings do not automatically enforce agent verdicts; the coordinator retains proof.
Git identity, hook installation and runtime/provider permission are controlled in
[CYBERSECURITY.md](CYBERSECURITY.md); fixture isolation requirements live in [TESTS.md](TESTS.md).

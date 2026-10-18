# Fork security controls

Scope: this public compiler fork and its CI. [CYBERSECURITY.md](CYBERSECURITY.md) maps threats to these controls; [GUARDS.md](GUARDS.md) states what is actually enforced.

- MUST run untrusted pull-request code on isolated hosted runners without private VM access, provider secrets or publishing authority. The excluded upstream workflows retain their repository guards.
- MUST pin CI actions to immutable official commits and install exact hash-locked test dependencies. A digest proves identity, not a security audit.
- MUST keep checkout credentials unpersisted and ordinary CI contents-read-only. Never copy a production token or deployment App identity into a compiler diagnostic.
- MUST redact before capture. Whitelist CPU/cgroup/kernel/page-size facts and numeric alignment residues; never dump environment, headers, cookies, credentials or private source into public artifacts.
- MUST retain private diagnostic evidence with owner-only access; publish only a reviewed bounded summary and source identity. GitHub-hosted public-source test logs are not permission to include private consumer data.
- MUST preserve failed evidence and exit status. No automatic compiler fallback, silent success, bypassed hook or administrative merge override.

A single-owner repository still requires a PR, all app-bound required checks and independent agent verdicts at exact source. The provider settings do not automatically enforce future agent verdicts; the coordinator must retain their evidence.

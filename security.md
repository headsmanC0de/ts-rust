# Source and evidence security

Scope: helper code and artifact parsing.
- MUST use argument vectors for dynamic subprocess input; eval/exec and dynamic shell execution are rejected.
- MUST retain completion, error type and actual exit status; exception swallowing cannot establish success.
- MUST validate selected profile and oracle independently, then all derived values before public output.
- MUST retain raw experimental payloads privately and emit closed stage/tool labels.
- MUST NOT expose credentials, DSNs, cookies, private payloads or unvalidated receipt lines.
- MUST pin tool identities and hashes in the owning requirements.

Synthetic negative fixtures may contain unsafe source text and invalid inputs; inspect
without executing that source. Provider/hook security belongs to [cybersecurity.md](cybersecurity.md).

# Search and repair

Scope: benchmark helpers and fork quality workflow.
- MUST find producer, selector and consumer before modifying evidence handling.
- MUST inspect callers, profiles, config inheritance and process exit handling.
- MUST inspect the introducing diff and name search bounds. Commit subjects are not root causes.
- MUST keep domain policy in its owning configuration or named constant.
  Protocol spellings and deliberate negative-fixture values remain independent oracles.
- MUST NOT treat absence, timeout, skipped work or unknown status as success.
- MUST NOT infer runtime readiness from YAML, installation or silent logs.

Use rg where available, otherwise git grep for tracked source; inspect all owning-file
matches and git log --follow. Search a parent before assuming independent child config.
Ruff owns structural/style rules in [ruff.toml](ruff.toml).
Semantic oracles belong to [tests.md](tests.md); enforcement maps to [guards.md](guards.md).
A repeated-string counter and formatter cannot prove compiler or business correctness.

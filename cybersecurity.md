# Operational security

Scope: hosts, hooks, CI identity, credentials and publishing.
Runtime belongs on the declared VM or isolated CI; MacBook remains editing/Git/SSH
unless the current owner explicitly authorizes project runtime.
Inventory and preserve existing hooks and Git identity before installation.
The hook installer MUST preserve author identity and refuse foreign hooks; temporary-Git
regressions exercise the real installer. Installing a guard does not authorize publishing.
Configured, callable and installed hooks are separate states; local skip is not merge permission.

GitHub can accept skipped/neutral required jobs. Before merge independently verify
head/test-merge SHA, expected application, job success, executed quality step,
complete required contexts and current independent approval. Self-checks cannot
prove they executed when their job was skipped.
Never bypass protection, reviews, scanners or failed compiler tests.
Use existing credential loaders without logging values. This quality lane needs no
production secrets. Compiler publishing requires separate admitted source/artifact proof.

The detector projects required contexts and approval policy only; other protection
settings and completeness of provider review/job pagination are not independently
certified. A passed detector is necessary evidence, not sufficient merge authority.

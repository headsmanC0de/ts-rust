# Controlled fork qualification

Scope: headsmanC0de/ts-rust, based on upstream source780dc512d64f40afebffa6a7028207649fb7ed1c. The current owner's authorization covers fork CI adaptation and bounded Moonrock VM qualification. Historical upstream authorizations, hosts and PASS records do not authorize new infrastructure access or prove this fork's compiler acceptance.

## Execution contract

The Moonrock coordinator owns the source/build queue. Local project runtime work belongs on workspace-vm, never on the Mac. Use the existing capped Cargo runner for authorized VM work with TS_CARGO_JOBS=2 and TS_CARGO_SLOTS=1; do not create competing targets or builds. Ordinary GitHub CI uses isolated GitHub-hosted VMs and CARGO_BUILD_JOBS=2. No workflow may invoke upstream host SSH, Blacksmith sessions, production provider credentials or publishing on behalf of this fork.

CI retains all inherited fmt/codegen/clippy, release workspace tests, Go baseline checks and exclusions, Windows comparison, Intel-macOS cross-check and wasm package commands. It changes runner availability and immutable action references, not compiler semantics or expectations. Jobs remain Linux x64, Linux arm64, macOS arm64 and Windows x64. The original upstream release, testbox and benchmark files remain present; their entry jobs are upstream-repository-only, and the final publish additionally requires an upstream push to a version tag. Fork releases need a separate explicit design and authorization.

## Evidence levels

`Fork configuration contracts` is a fast configuration and trust-boundary check. It does not compile Rust, install a compiler, run the protected regression/oracle set or certify diagnostic/type/symbol parity. Ordinary CI is also not the protected compiler acceptance pipeline: AGENTS.md and docs/typechecker-accountability.md continue to own that evidence. Missing binaries, inputs, oracle results or independent verdicts remain missing, not inherited from the upstream saved PASS state.

A separately built release binary must later pass the bounded good/bad-TypeScript, declaration/emit and LSP/API canaries at exact source identity. No such result is claimed by this change. Hosted runner labels are configured; successful provider execution is separate evidence.

## Configuration tests

Run in an isolated Python3.12 environment installed from scripts/fork-ci/requirements.txt:

    PYTHONDONTWRITEBYTECODE=1 <isolated-env>/bin/python -m unittest discover -s scripts/fork-ci -p 'test_*.py' -v

The GitHub configuration job uses Python3.12 and an isolated, exact, hash-locked binary PyYAML dependency. It uses PyYAML BaseLoader to preserve GitHub's `on` key, not a custom YAML parser. The CI step-object digests were recorded independently from source780dc512 before edits; only the action revision is normalized, preserving action identity, conditions, permissions, arguments and environment; the digests prevent bypassing inherited checks while adapting runners. Intentional upstream command changes require review against the new source before updating this evidence.

RED records the inherited inaccessible runners, mutable CI action references, missing owning push inputs and missing repository/publishing guards. Negative mutations verify rejection of self-hosted runners, removed platform coverage, skipped inherited jobs, mutable actions, OIDC escalation, privileged events, publishing commands and fork-retargeted guards. No test executes a deployment or publishing action.

## Verified dependency references — 2026-10-18

The ordinary CI workflow owns its immutable action pins; scripts/fork-ci/requirements.txt owns the exact PyYAML6.0.3 binary-wheel hash. Do not duplicate those values here. Official repository git-ref APIs were read to resolve the action tags. Full commit pins are reproducible identities, not an independent security audit of action code.

- https://api.github.com/repos/actions/checkout/git/ref/tags/v7.0.1
- https://api.github.com/repos/Swatinem/rust-cache/git/ref/tags/v2.9.2
- https://api.github.com/repos/actions/setup-go/git/ref/tags/v7.0.0
- https://api.github.com/repos/actions/setup-node/git/ref/tags/v7.1.0
- https://api.github.com/repos/actions/setup-python/git/ref/tags/v7.0.0
- https://pypi.org/pypi/PyYAML/6.0.3/json — CPython3.12 manylinux x86_64 wheel; PyYAML6.0.3 is the observed stable release.

These pins apply to ordinary CI; retained, fork-excluded upstream service workflows still contain upstream action tags. Initial RED used the VM's existing PyYAML6.0.1; GREEN qualification uses only the isolated, hash-locked dependency. No system Python packages are changed.

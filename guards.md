# Guard registry

| Guard | Owner | Negative oracle | State |
| --- | --- | --- | --- |
| Completion | verify.py | crash/missing receipt | CLI regression verified |
| Selected evidence | summary.py | stale oracle/failed overlay | CLI regression verified |
| Atomic report | summary.py | late failure/invalid math | CLI regression verified |
| CI coverage | test_workflows.py | removed/skipped/ignored invocation | mutation verified |
| Hosted pool | CI test env | missing parallel emit setting | source verified; native rerun pending |
| Python style/security | ruff.toml | undefined name/eval/shell/swallowed error | native negative oracles verified |
| Local dispatch | quality.sh | failure/timeout/unsupported host | native negative oracles verified |
| Source size | test_quality.py | owning Python exceeds policy | scoped only |
| Live merge detector | check_pr.py | stale/skipped job/unexecuted step/policy drift | 13 fixture tests; PR base rejected live; trusted enforcement OPEN |
| Hook preservation | test_hook_install.py | foreign hook/identity/worktree paths | 7 native temporary-Git tests verified |
| Metadata lineage | design.md | overwritten variant identity | OPEN |

Scope is the two Python tooling directories, not every inherited Rust/Python file.
Configured, locally tested and provider-enforced are separate states. Required CI plus
independent readback remain necessary; a local hook is not tamperproof enforcement.

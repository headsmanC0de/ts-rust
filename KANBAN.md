# Fork qualification board

Updated 2026-10-18. This board owns only the fork tooling work in PR #6.
Source implemented, locally verified, CI verified and merged are distinct states.

| Task | State | Acceptance / evidence |
| --- | --- | --- |
| Complete diagnostic/process admission and selected timing stream binding | Local verified; published in stacked draft PR #6 | 49 benchmark CLI regressions pass |
| Scoped rules, lint/format and shared required-job interface | Local verified; provider rerun pending | Discovered fork/workflow/security/hook suites plus lint/format pass; exact counts belong to run receipts |
| Preserve identity and foreign Git hooks | Local verified | 7 real temporary-Git installer tests pass |
| Exact-head read-only premerge detector | Local verified; live fail closed | 17 fixture tests; stacked base rejected; approved single-owner policy evaluated |
| Restore hosted emit-pool prerequisite | Implemented; native rerun pending | Explicit fixture1 retained; missing-setting mutation rejected; four-platform tests must pass |
| ARM allocator geometry investigation | In progress | Original assertion retained; ARM allocator64KiB/OS4KiB observed; x64 page-size counterfactual does not reproduce; collect safe mapping/THP facts |
| PR workspace cache policy | Implemented; performance proof pending | Mutations rejected; 269460705-byte PR6 cache saved after ARM failure; warm timing proof pending |
| Trusted external premerge enforcement | Open | Owner-approved provider policy, independent technical verdict, all exact-head jobs and executed quality step |
| Immutable benchmark variant metadata lineage | Local verified; provider rerun pending | Atomic per-stem receipts, actual tool/config/artifact hashes and consumed byte snapshots; application dependencies outside declared closure |
| Merge/release qualification | Blocked by native CI and review | Admit parent PR #5, retarget #6 safely, independent review; no release/global adoption before acceptance |

DoR: reproduce, identify producer/consumer and current source, choose a bounded owner.
DoD: negative oracle fails before repair, real behavior passes after repair, independent
review, exact-head required CI and evidence; archived completion requires merged source.
No entry is marked done solely because code or documentation exists.

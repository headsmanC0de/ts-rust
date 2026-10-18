# Повторювані помилки та scoped guardrails — 2026-10-18

## Межа дослідження

Це bounded research, а не аудит усієї історії. Перевірено source780dc512 та candidatee35dba2e, чотири workflows, fork-ci contracts, emit/allocator assertions, окремий git blame/history у збереженому full-history checkout, фактичні CI failure summaries і receipts поточної сесії. Cargo/build/tests тут не запускалися. Дозволений єдиний write — цей новий документ; candidate source frozen до інтеграції root.

Canonical outcome: **Which CI trust boundary can safely qualify the Moonrock compiler fork?**, WF-T-TSRUST-FORK-CI-20261018, parent WF-MAP-CLOSEOUT-20261015; [PR5](https://github.com/headsmanC0de/ts-rust/pull/5), [candidatee35dba2e](https://github.com/headsmanC0de/ts-rust/commit/e35dba2e1fea2d6c22229dbe48792e9cf8c492c7). Task OPEN. Company **Monorepo tooling radar (#206)** окремо володіє consumer adoption; нової duplicate card не потрібно.

Configuration PASS не означає compiler PASS: чотири test methods і21 negative mutations, незалежні step/DAG checks та actionlint пройшли, але provider запустив збережені compiler tests і виявив новий failure frontier. Очікуваний roster не скорочується. DONE можливий лише після RED reproduction→repair→GREEN відповідного контракту та required exact-source acceptance.

## 1. Неявна залежність тесту від CPU topology

**Симптом.** Обидва captured Linux jobs CI39114616780 дали emit_context::emit_matches_go_in_every_mode та чотири emit_pool failures: pool/twins got no job. Первинні logs: приватні ci-job-117637745253-failure-summary.txt і ci-job-117637745348-failure-summary.txt.

**Перша доведена розбіжність.** program.rs:556–580, emit_thread_count: без GOPORT_EMIT_THREADS count визначається cores/checkers і стає0 при cores<=checkers. tests/emit_pool.rs:89–90 очікує jobs>0 після run(|_|{}); такий самий ресурсний precondition не зафіксований явно. git blame відносить умову cores<=checkers до [c33e348744](https://github.com/headsmanC0de/ts-rust/commit/c33e348744), setter/auto-selection entry до [5ce25459ca](https://github.com/headsmanC0de/ts-rust/commit/5ce25459ca). Це локалізує відмінність контрактів; причинність конкретної runner topology потребує reproduction з actual effective cores/checkers. Не називати це доведеним compiler output defect: assertion про активований механізм впала раніше.

**Чому пропустили.** YAML lint і27 збережених step objects перевіряють dispatch/збереження команд, не runtime scheduling. Більший upstream runner міг задовольняти неявний precondition. CARGO_BUILD_JOBS=2 обмежує Cargo workers, а не доводить count runtime emit workers. Rust [available_parallelism](https://doc.rust-lang.org/std/thread/fn.available_parallelism.html) описує доступність як approximation із platform/resource caveats.

**Найнижчий repair owner.** Test harness resource setup + окремий auto-selection unit/behavior test; compiler scheduler змінювати лише якщо його власний контракт порушено. Fork test owner/root.

**Scoped proposal, НЕ вже enforced:** тести, що MUST exercise pool, MUST явно забезпечити та записати pool activation; MUST NOT покладатися на spare CPUs CI host. Auto mode MUST окремо перевіряти0/low/wide-core та explicit0 override. Exception: тест саме auto-selection залишає auto, але очікування виводить із контрольованої topology. Example: positive pool fixture explicit bounded count; separate no-pool control retains same output comparison. Guard status OPEN: новий failing oracle ще потрібен; не skip/ignore чотири tests.

Adjacent: checkers1/4, singleThreaded, trace, wasm no-pool, environment captured once via OnceLock, child isolation між different env cases, JS/d.ts twins і panic recovery. [jstwin panic repair392f926b](https://github.com/headsmanC0de/ts-rust/commit/392f926b) показує попередній пов’язаний контракт; нові assertions не слід послаблювати.

## 2. Geometry allocator як неявна platform assumption

**Симптом.** ARM log додатково: jemalloc_layout::layout_from_inside, tests/jemalloc_layout.rs:108, arena0/block1 не на очікуваній2MiB boundary; outer child exit101. Це доведений assertion failure, не доведена root cause.

**Source hypothesis.** src/jemalloc_layout.rs:1–70 документує jemalloc5.3.1 growth/arena assumptions, Linux6.7/THP,4MiB alignment priming; tests:80–108 перевіряє probe16MiB і наступні grows. Probe alignment не доводить всі наступні growth assumptions на ARM page-size/kernel/allocator configuration. Page geometry, THP і allocator policy треба виміряти; “ARM unsupported” або “64KiB pages винні” наразі недоведено. [jemalloc manual](https://jemalloc.net/jemalloc.3.html) окремо описує page, hugepage, arena і retained-growth controls; portable equality з одним desktop host не гарантована.

History anchor: [allocator arena repair6ea5ac7b](https://github.com/headsmanC0de/ts-rust/commit/6ea5ac7b2020e7206f01f78af835d7318aa05641) — найближчий прочитаний owning-source commit, не доказ початку ARM defect. **Чому пропустили.** Compiler parity і YAML config не вимірюють memory mapping. Існуючий test має partial kernel probe, але не всі actual preconditions. Найнижчий repair: allocator-owned repro/telemetry та implementation/test precondition decision, не загальне CI skip.

**Scoped proposal / OPEN:** allocator-specific geometry tests MUST записувати actual page/hugepage sizes, kernel, jemalloc version/options і mapped extent transitions до висновку; MUST NOT змінювати architecture expectations лише за назвою ARM. Exception: документований unsupported mechanism може мати explicit N/A із owner і негативним тестом fallback; це не silent skip. Guards: bounded architecture repro + controlled supported/unsupported geometry, limit mode, env0, arena<=4, watcher/no-watcher. Власник allocator qualification/root; GREEN reproduction ще немає.

## 3. Успадкована інфраструктура помилково стала локальним дозволом

**Симптом/source.** [base780dc512](https://github.com/headsmanC0de/ts-rust/commit/780dc512) мав Blacksmith labels і upstream release workflow із npm OIDC/contents-write. Синтаксично валідний workflow не доводив доступ fork до runners або право публікувати upstream packages. Inherited AGENTS містить Theo/hosts/old roles; це historical context, не нові credentials.

**Repair на правильному шарі.** e35dba2e CI adapter застосував hosted4-platform matrix, pinned ordinary-CI actions/read-only token, upstream-only entry guards; final publish додатково upstream+tag+push. Дочірні jobs перевірені як DAG; bench summary always() ще вимагає plan success. [GitHub workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax) визначає needs/if/permissions, а не права нашого акаунта.

**Scoped rule, частково enforced:** fork workflows MUST розділяти repository/event trust і runner capability; MUST NOT переносити upstream publishing чи host access з історичних instructions. Exception: окремо дозволений release design з його environment/credentials/provenance, не ця PR. Executable current guard: scripts/fork-ci/test_workflows.py —4 methods,13CI+8guard negative mutations, step digests6/15/6; owner fork CI. PASS_CONFIGURATION_ONLY на e35; provider/protected compiler acceptance лишається окремим. Adjacent: removed/retargeted repo guard, skipped prerequisite+always, pull_request_target, OIDC escalation, mutable actions, job/step continue-on-error, lost OS/wasm, publish commands, persisted checkout credentials.

## 4. Докази помилки надходять запізно

**Симптом/source.** Ordinary ci.yml e35 не має failure artifact upload або RUST_BACKTRACE setting. Фактичні logs довелося читати через GitHub job log API; summaries показують assertions, але не весь effective runtime/allocator context. Це failure-diagnosis gap, не “логів немає”. Runner UI logs існують.

**Чому lint/test count не спрацювали.** Конфіг contracts зберегли старі checks; вони не вимагали diagnostic payload після early failure. GREEN config при RED compiler — правильна різниця evidence levels, але oracle coverage можна розширити.

**Scoped proposal / OPEN:** початок native lane MUST записати bounded toolchain/source/oracle/resource identity; failure MUST зберегти sanitized logs і relevant context до cleanup; MUST NOT вимагати debug opt-in для мінімального failure evidence. Exception: secrets/raw-source inputs виключаються, але receipt фіксує omission reason. Найнижчий шар — existing workflow/harness artifact lifecycle, owner fork CI; negative oracle: injected early nonzero все одно дає nonempty owned artifact+correct failure exit, cancellation окремо. Не перетворювати panic fixture output на unexpected leak автоматично.

[Playwright config](https://playwright.dev/docs/test-configuration) демонструє per-project worker/trace configuration; це суміжний Company browser lesson, не підстава додавати Playwright до Rust fork. Trace-on-retry не рятує zero-retry early failure: потрібен явний retained failure artifact policy на відповідному runner.

## 5. Observer deadline коротший за native busy budget

**Факти.** Initial supported Agent upsert kill/reap після20s; native ticket readback лишив old projection. Source diagnosis в іншому owning repo на nzxt: sqlite_pragmas.zig busy floor30s, indexed native upsert без network retry; WAL/active readers — можливі додаткові фактори. Лише READ locks спостерігались після події. Replay з тим самим20s cap завершився **1.006s**, exit0, PR5 projection прочитано назад. Причину initial timeout НЕ відтворено.

**Перша доведена розбіжність контракту:** observer20<native30 може обірвати штатну native wait раніше typed SQLITE_BUSY. Це достатній observability defect proposal, але НЕ доказ, що саме busy wait спричинив initial timeout. Receipts: task-evidence-binding-timeout.json, task-upsert-readonly-diagnosis.json, task-upsert-instrumented-replay.json.

**Scoped proposal / owner Agent control plane, OPEN:** outer observation MUST відповідати actual operation budget або використовувати detached bounded observation; MUST NOT називати timeout deadlock/DB corruption без доказу. Before replay MUST read back ambiguous mutation, prove own-process cleanup, preserve payload digest; foreign actors MUST NOT be killed. Exception: короткий cancellation budget дозволений, але результат UNKNOWN/ambiguous з readback, не failed mutation certainty. Guard proposal: controlled busy owner native test, deadline precedence, success-after-release, own cleanup, WAL reader scenario. Fork doc не є місцем міняти SQLite settings; direct SQL/settings не застосовувались.

Native show-ticket не повертає question: visible projection_ref верифікований, question payload digest збережений; не приписувати API readback того, чого воно не повертає.

## 6. Неповний LSP client видавався за compiler failure

**Послідовність.** Старий harness не відповідав workspace/configuration; наступний відповідав null, але не обробляв client/registerCapability і втратив коректний shutdown contract. Старі INCOMPLETE receipts збережені; це не compiler bug proof. Пізніший повний client має advertised registrations/pull diagnostics та omitted-params shutdown.

**Останній coordinator-verified receipt:** ~/projects/evidence/ts-rust-20261018/consumer-audit/lsp-document-qualification.json — COMPLETE0.324s: TS2322→clear, completion, definition, shutdownnull, exit0, native hash незмінний. Цей scope не дорівнює повним upstream LSP batteries. [LSP3.17 specification](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/) — protocol owner; initialize capabilities і request handlers є частиною тестового input.

**Scoped rule proposal:** protocol clients MUST реалізувати negotiated requests/response IDs і shutdown shape перед attribution серверу; MUST NOT blanket-ack dynamic registration чи вигадувати configuration defaults. Exception: deliberately incomplete client тестує одну можливість і звітує INCOMPLETE для решти. Найнижчий шар repair — canary client; owner toolchain qualification (#206). Guard status: bounded document canary GREEN; adjacent unsupported-method negotiation, registration advertised/not, one config result per item, request correlation, negative diagnostics, close/shutdown/exit та child reap. Full protected LSP acceptance OPEN.

npm registry gitHead3644f324...→780 — history-only; →e35 —8 CI/docs files. Coordinator довів однакові compiler/Cargo/tools/npm/UPSTREAM trees та115 libs Rust/source/Go bytes. Тому “npm має інший semantic compiler” не є допустимою причиною. Source build reproducibility/provenance все одно потребує власного доказу.

## 7. Непридатна single-owner approval вимога

**Наше рішення було зайвим.** Початкова protection вимагала1 approval і require_last_push_approval=true без доступного другого provider identity. Independent agent reviews не утворюють другого GitHub account. Після уточнення own owner policy receipts single-owner-protection-before/after фіксують required count1→0 та last-pushtrue→false; це окремо від збережених required CI/admin/force/delete boundaries. Не переносити цю зміну на Company Gitea з його іншим accepted policy.

**Чому пропустили.** Бажане слово “independent” підмінили provider capability/eligible identity census. [GitHub protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches) відрізняє review permissions, latest-push approval та app-bound status checks.

**Scoped MUST:** admission design MUST перевірити реальних eligible reviewers і user-approved ownership model до setting write; MUST NOT створювати невиконувану вимогу або обходити чинну політику через admin. Exception: одноосібний fork може мати0 provider approvals за explicit owner policy, але independent technical verdicts і required real CI лишаються доказами. Guard proposal: read-only policy readiness matrix з unavailable-reviewer negative case; provider readback correction є, автоматичного guard немає. Owner shared lifecycle/root; status CORRECTED_PROVIDER_SETTING, не вся release acceptance.

## Де повинні жити правила й guards

На fork при дослідженні існували AGENTS.md, docs/typechecker-accountability.md, append-only state/current/reset, docs/fork-qualification.md, scripts/fork-ci/test_workflows.py та owning Cargo runners. Окремі TESTS.md/SECURITY.md/CYBERSECURITY.md/DESIGN.md/GUARDS.md/search-rules/lefthook entrypoints в обмеженому root/maxdepth2 inventory не знайдені. Це не вимога створити сім копій generic policy. Root окремо готує вузькі adapters; їхній майбутній enforcement цим report не підтверджується.

- AGENTS: короткий bootstrap/link до owning fork contract, без копії всіх правил.
- TESTS/search-rules adapter, якщо потрібний користувачу: exact current commands, protected roster/no-loss і evidence levels, посилання на accountability.
- SECURITY/CYBERSECURITY: лише actual fork trust boundaries, permissions/publishing та секрети; не загальний compliance checklist.
- DESIGN: compiler/state/testability invariants або link на owning architecture, не web UI standards.
- GUARDS: registry **тільки** executable guard→entrypoint→negative proof→owner/status; proposals явно OPEN.
- lefthook: transport до наявних cheap tests; без hook-bypass, Cargo/full builds на кожен docs touch або дублювання CI implementation.
- Shared lifecycle/ownership/runtime limits лишаються Wayfinder standards/agent-team.md і wiki/operations/branch-worktree-lifecycle.md. Agent DB timeout — apps/agent owner; Company rollout — card206. Mac Wayfinder foreign dirty work не змінювався.

Policy — прийнятий operating contract; enforcement — реальний wired command із counterexample/receipt. Наявність документа, великого test count або upstream accepted R220 не доводить fork GREEN. Найближчий frontier: reproducible emit activation failure і окремий ARM allocator cause; потім smallest owning-layer repair та незмінний expected roster. PR5/task лишаються OPEN до exact-head provider і qualification evidence.

## Repair evidence after the initial snapshot

The initial e35dba2e observations above are retained as history. The subsequent bounded CI repair has 28 passing fast Python tests plus Ruff lint/format checks and actionlint. The installed pre-commit hook actually ran these checks; missing Python fails closed. A further regression requires `assert_lefthook_installed: true`, and the regenerated hook has an explicit failure branch when the executable cannot be found. This is installed local enforcement and CI configuration, not a claim about every agent harness.

Actual release-mode emit reproduction under controlled GOMAXPROCS=1: original emit_context/emit_pool targets gave 3 passed and 5 failed with no override; with the bounded positive fixture override the same eight tests all passed. Existing assertions and fixtures were unchanged. The separate policy integration test passed five fresh-process capability cases (low/high automatic, positive override, explicit zero and single-threaded). Evidence: policy-runtime.log, pool-runtime-red.log and pool-runtime-green.log in the private fork evidence directory. Old hosted macOS and Windows jobs independently exhibited the same five pool-activation failures. ARM allocator failure remains unresolved; this repair does not change its expectations, disable its optimization or authorize adoption of a failing release. Hosted exact-new-commit CI and the protected compiler acceptance suite remain required.

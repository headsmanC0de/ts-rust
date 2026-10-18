# ARM jemalloc layout investigation — 2026-10-18

Статус: **причина ще не доведена**. Найсильніша перевірна гіпотеза — відмінність allocator page/extent geometry на ARM та недостатній критерій тесту «non-contiguous allocation означає новий grow». Не змінювали allocator, тести, Cargo/CI; не запускали build/probe/provider actions.

## Межа спостереження

Source: `e35dba2e1fea2d6c22229dbe48792e9cf8c492c7`. Збережений ARM CI job `117637745348`, приватний лог `~/projects/evidence/ts-rust-fork-20261018/ci-job-117637745348.log`: о 09:33:10 UTC `layout_from_inside` падає на `tests/jemalloc_layout.rs:108`, **arena 0, block 1**; фінально цього integration binary 4 passed/1 failed. x64 прохід повідомив координатор; це не повторна перевірка тут. Не змішувати з окремими emit_pool failures цього ж job.

До assertion тест уже підтвердив narenas=4, живий holder та **успішну 2 MiB alignment перевірку одного 16 MiB probe**. Отже guard не відсіяв цей ARM host. Це доводить alignment одного allocation у huge arena, але не всіх наступних mappings/retained fragments у кожній normal arena. `follows` порівнює адреси через requested BLOCK=2.5 MiB; будь-який розрив після block0 рахується як grow. Тест не спостерігає mmap/extent events, тож «новий grow» поки лише inference. [Actual test](https://github.com/pingdotgg/ts-rust/blob/780dc512d64f40afebffa6a7028207649fb7ed1c/crates/ts_goport/tests/jemalloc_layout.rs#L76-L113).

Production `Grow` має size/alignment 4 MiB, fallible reserve; очікує перехід до 8 MiB grow та наступні multiples2 MiB. Коментар прямо рахує `8 MiB − 4 KiB`; сам код не читає allocator page або PMD size. [Actual production module](https://github.com/pingdotgg/ts-rust/blob/780dc512d64f40afebffa6a7028207649fb7ed1c/crates/ts_goport/src/jemalloc_layout.rs#L14-L25). Це точне місце архітектурного припущення, але 64 KiB самі по собі ще не доводять поломку: `8 MiB − 64 KiB` теж вкладається в 8 MiB. Потрібен вимір actual extent/reuse sequence.

## Pinned allocator та kernel: що справді встановлено

`Cargo.lock` фіксує tikv-jemalloc-sys `0.7.1+5.3.1-0-g81034ce1f1373e37dc865038e1bc8eeecf559ce8`, checksum `1a2825c78386b4ae0314074867860ba9577875de945f05992c38815cbec327f0`; allocator/ctl0.7.0. Офіційний crate прочитано в пам'ять (1,037,885 bytes), SHA256 точно збігся з lock; його configure.ac побайтно збігається з локальним registry source. Нічого не встановлювали. [Exact crate archive](https://static.crates.io/crates/tikv-jemalloc-sys/tikv-jemalloc-sys-0.7.1+5.3.1-0-g81034ce1f1373e37dc865038e1bc8eeecf559ce8.crate).

У pinned configure.ac ARM case `aarch64-unknown-linux-*` при unset override встановлює **LG_PAGE=16 (allocator64 KiB)**; Linux kernel може при цьому мати інший base page. Published crate lines1988–1991; upstream pinned source lines1894–1897. Wrapper приймає `JEMALLOC_SYS_WITH_LG_PAGE`, тому фактичну ARM конфігурацію слід прочитати з mallctl/generated headers — не вгадувати за target. [Pinned configure](https://github.com/tikv/jemalloc/blob/81034ce1f1373e37dc865038e1bc8eeecf559ce8/configure.ac#L1894-L1897), [wrapper environment contract](https://github.com/tikv/jemallocator/blob/main/jemalloc-sys/README.md#environment-variables).

Pinned `extent_grow_retained` рахує minimum як `size + PAGE_CEILING(alignment) − PAGE`, обирає size class, mmap-ить з alignment PAGE, потім split-ить interior та повертає lead/trail у retained cache. Reuse може повернути allocation без нового grow. [Pinned extent code](https://github.com/tikv/jemalloc/blob/81034ce1f1373e37dc865038e1bc8eeecf559ce8/src/extent.c#L665-L724), [growth sequence](https://github.com/tikv/jemalloc/blob/81034ce1f1373e37dc865038e1bc8eeecf559ce8/include/jemalloc/internal/exp_grow.h).

Лог фіксує image `ubuntu-24.04-arm`, version20261012.149.1, Ubuntu24.04.5. Його immutable image README називає kernel6.17.0-1022-azure, але не гарантує base page/PMD size або THP policy поточного процесу. Наявність нового kernel не доводить universal2MiB mmap alignment. [Exact image documentation](https://github.com/actions/runner-images/blob/ubuntu24-arm64/20261012.149/images/ubuntu/Ubuntu2404-Arm64-Readme.md). Kernel THP документація прямо пояснює, що наведені4K/2M значення залежать від архітектури; PMD size доступний через `hpage_pmd_size`. [Linux THP contract](https://www.kernel.org/doc/html/v6.7/admin-guide/mm/transhuge.html). Actual ARM getpagesize/PMD/cgroup metadata відсутні у наявному failure receipt.

## Перевірні гіпотези

| Гіпотеза | Що її підтвердить / відкине |
|---|---|
| H1: allocator64KiB geometry змінює layout/reuse | `arenas.page=65536`, actual large-class size та allocation deltas/residues відрізняються від x64; trace показує інший retained split. Якщо geometry та sequence однакові — H1 слабшає. Kernel getconf4096 **не** відкидає allocator64KiB. |
| H2: тест помилково приймає reuse/gap за grow | На failing block1 немає нового extent/mmap; allocation отримано з lead/trail/cache, або usable size != requested BLOCK. Новий mmap з невирівняною адресою натомість переносить питання до mapping policy/H3. |
| H3: single16MiB probe випадково aligned або normal mapping policy інша | Кілька контрольованих anonymous extent lengths мають різні modulo2MiB при однакових THP/process settings. Одна aligned huge-arena allocation цього не спростовує. Не робити retry-until-pass. |
| H4: production reserve не виконав задуманий warm-up | Оригінальний `try_reserve_exact` міг fallible завершитися без allocation; return result зараз ігнорується. Потрібні actual reserve/extent stats та memory/rlimit metadata. Сам факт holder alive не доводить reserve success. |

Не припускати, що cgroup memory.max є тим самим, що production `gostd::stack::memory_limit()`: останній читає address/data resource limits. Наявна assertion означає лише, що layout не був пропущений за власною перевіркою.

## Найдешевший справжній test seam

1. На тому самому ARM runner використати **вже зібраний integration binary**, exact `layout_from_inside --nocapture --test-threads1`; жодної повторної cold workspace build. Його поточний runtime ~0.06s inner/~0.72s outer. Зберегти metadata перед цим, не змінювати expectations/skip.
2. Для нового diagnostic helper найнижчий seam — невеликий private executable, **linked against already-built exact-source `ts_goport` rlib та pinned jemallocator/ctl rlibs** з того самого ARM target. Він викликає `ts_goport::jemalloc_layout::jemalloc_layout()` без копії алгоритму й відтворює allocation workload, записуючи числові спостереження. Root має авторизувати build/link queue; тут лише пропозиція. Не обіцяти «без16хв» без наявних matching ARM rlibs/cache.
3. Standalone `#[path]` імпорт цілого production module не є автоматично ізольованим: він звертається до реальних `crate::gostd::stack::memory_limit` і `crate::fast_mode::own_arenas`; fast_mode має frontend/execute dependencies. Підставляти `None`/`false` як шими означає mock залежностей, тому цього не пропонуємо як acceptance. Якщо matching rlibs немає, потрібен окремо reviewed production-module boundary refactor або стандартна cached test build, не copy/paste алгоритму.

## Мінімальний sanitized receipt наступної діагностики

Записати source+binary+Cargo.lock hash, arch/kernel/image; OS page bytes, PMD bytes, THP enabled/defrag і process THP-disable boolean. Jemalloc: version, `arenas.page`, `arenas.quantum`, `opt.narenas`, `opt.oversize_threshold`, `opt.retain`, `opt.cache_oblivious`, supported THP controls; read errors позначати unavailable. Показати тільки числові configured size classes для BLOCK/Grow/probe та generated LG_PAGE/LG_HUGEPAGE (не весь build env). `_RJEM_MALLOC_CONF` тут — точна source-константа `narenas:4,thp:always,metadata_thp:disabled,cache_oblivious:false`, не dump середовища.

Per allocation: arena/index, requested/capacity/usable bytes, pointer **residue** modulo OS-page/allocator-page/2MiB/PMD/4MiB, signed delta to previous allocation і mapping/grow/reuse event status. Ніколи не друкувати raw pointers, /proc/maps або pathname/address-bearing strace. Metadata cgroup: numeric memory.max/current/events counters, RLIMIT_AS/DATA; без cgroup paths/IDs/raw env. Diagnostic logging саме може алокувати й змінити arena0: попередньо allocate fixed event storage та dump його після allocation loop або поза arena-under-test; спочатку metadata-only контроль без per-allocation logging. Hook/strace tracing — лише якщо найнижчий probe не відрізнив H1/H2/H3, із sanitized numeric output.

## Історія й незакритий ризик

GitHub path-history API + commit detail встановили, що production module та test **додано** в `13c40d5e27f9cb3ebda602918689a4ee760eb5dd`, `perf(goport): lay out the jemalloc arenas at start (jemlayout2)`; parent `a9ad35a9e9049549522531e87a23dcadd19fefb4`. Це перший знайдений introduction припущення, **не** доведений перший bad ARM commit. [Introduction](https://github.com/pingdotgg/ts-rust/commit/13c40d5e27f9cb3ebda602918689a4ee760eb5dd). Подальші MAX_ARENAS/fast-mode arena changes не є доказом причини normal arena0 failure. Shallow local history сам по собі неправильно показував би780dc512 як introduction, тому використано owning API.

Немає ARM metadata/isolated reproducer/differential mapping trace; causal first-bad revision невідома. Compiler source/libs identical npm0.7.0 — це не доказ, що layout assertion проходить на всіх hosts. Збереження current expected pass обов'язкове: не додавати skips, не вимикати optimization, не зменшувати coverage. Рішення про portable invariant або production repair можна приймати після наведеного виміру, не за припущенням «ARM завжди64K».

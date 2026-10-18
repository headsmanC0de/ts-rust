# Compiler qualification design

This repository is a maintained source fork, not a product UI. Theme, locale, popup and browser matrices belong to consumer products; they cannot be inferred from a compiler test.

The qualification unit is one immutable tuple: source inputs, toolchain, feature/profile flags, oracle/lib identity, artifact digest and applicable host capabilities. Consumer projects reuse the accepted artifact through their existing tooling owner; they do not each build a competing compiler or carry a hidden fallback.

Runtime defaults belong to the compiler. A fixture declares the capability its assertion needs and separately tests the default and disabled paths. Kernel page size, allocator logical page size and CPU budget are distinct inputs.

Use existing interfaces before adding a wrapper. The native correctness wrapper has one boundary: retain Cargo command/status while exposing bounded context and early failure annotations. The fast quality entrypoint has one boundary: lint, format and contract verification. Neither certifies native correctness.

Policy ownership: search/static workflow in [search-rules.md](search-rules.md), behavior/evidence in [TESTS.md](TESTS.md), security in [SECURITY.md](SECURITY.md), threats in [CYBERSECURITY.md](CYBERSECURITY.md), executable wiring in [GUARDS.md](GUARDS.md). AGENTS is navigation, not a second copy of these rules.

---
name: search-first
description: "Before adding custom implementation or a new dependency, inspect the repository and verify whether existing code, configured tools, or maintained libraries already solve the specific need."
---

# Search before implementation

1. Identify the behavior and constraints that matter. Search local code, manifests, tests, and documentation first; use `rg` when available.
2. Reuse an existing implementation or configured dependency when it fits the contract. Check its actual callers and supported version.
3. If the answer depends on an unfamiliar or changing API, read primary documentation for the project's version. Evaluate a new dependency only when existing code does not adequately solve the need.
4. Compare real fit, maintenance, license, integration cost, and failure behavior. Do not install a package just because it exists or construct a custom framework for a bounded task.
5. Stop searching when sufficient evidence supports the next implementation step. Record consequential choices in the existing proposal/ADR rather than producing another research report.

Use tools actually exposed by the current host; do not assume named browser, search, or agent APIs exist. Research does not require a subagent. Delegate only when `../selective-delegation/SKILL.md` applies and delegation is authorized. Follow `../development-profile/SKILL.md` for dependency and verification policy.

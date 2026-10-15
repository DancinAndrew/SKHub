---
name: python-patterns
description: "Write or review Python code using explicit contracts, ownership, resource lifetimes, and the project’s existing typing and error conventions."
---

# Python patterns

Use `../development-profile/SKILL.md` for shared workflow and dependency policy. Follow the project's supported Python version, formatter, type checker, and packaging conventions.

- Annotate public boundaries and contracts whose types clarify behavior. Distinguish optional values from absent fields; do not replace unknown data with a plausible default.
- Use dataclasses for data with behavior, TypedDict for shaped dictionaries, and Protocol for a real structural interface. Avoid class hierarchies for a one-off function.
- Keep mutable defaults out of function signatures and dataclass fields; use factories. Make object ownership explicit before copying or mutating.
- Catch specific exceptions at a boundary that can handle them; retain the cause with `raise ... from exc`. Preserve cancellation and process-control exceptions.
- Use context managers for files, connections, locks, and temporary resources. Ensure cleanup also happens on errors.
- Use generators for genuinely streaming workloads; account for one-shot consumption and resources that remain open while iterating.
- Do not call blocking network or disk operations directly inside an async request path. Use the project's async clients or a bounded executor where appropriate.
- Prefer pathlib and timezone-aware timestamps. Serialize stable schemas instead of arbitrary object internals.
- Configure logging at the application entrypoint; libraries should not change global handlers. Never log credentials or private payloads by default.
- Inspect existing dependency and lock files before choosing tooling. Do not introduce a formatter, package manager, or runtime solely to match this skill.

Use `../python-testing/SKILL.md` for pytest techniques and `../backend-development/SKILL.md` for API, persistence, and deployment concerns.

---
name: coding-standards
description: Apply cross-project conventions for readable names, explicit contracts, controlled mutation, small focused changes, and maintainability review. Use specialized skills for framework or backend details.
---

# Coding Standards

Use these as a common baseline, subject to project-local conventions.

- Use descriptive names that reveal intent; name functions by their action and use booleans as predicates.
- Prefer readable control flow, small focused units, and explicit data/error contracts over clever compression.
- When a change exposes a design problem, prefer a small public interface that hides useful complexity. Include required call ordering, errors, configuration, and invariants in the contract; method signatures alone may omit what callers need to know.
- Evaluate an abstraction by the complexity it removes from real callers. Avoid adding wrappers or interchangeable implementations without a demonstrated need. Use the project's vocabulary rather than imposing a new naming system.
- Avoid speculative abstractions and unnecessary duplication; extract shared code only after a real shared behavior is clear.
- Treat mutation deliberately. Prefer immutable updates when they make ownership and state transitions clear; use controlled mutation when it is simpler or needed for performance, and keep it local.
- Validate untrusted input at system boundaries and surface actionable errors without exposing internals.
- Comment on non-obvious rationale, constraints, or tradeoffs rather than restating code.
- During review, check for misleading names, hidden side effects, error paths, unbounded work, accidental public-contract changes, and unrelated edits.

For API contracts and backend architecture, use `../backend-development/SKILL.md`. For React/TypeScript examples, read [the optional reference](references/typescript-react-examples.md); it is illustrative and does not override the active project's framework conventions.

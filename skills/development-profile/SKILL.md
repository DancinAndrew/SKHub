---
name: development-profile
description: Apply the user's Python-first software-development defaults when building, modifying, debugging, reviewing, testing, or automating code in a repository. Project-local authority and the requested scope take precedence.
---

# Development Profile

Use this profile for software work. The repository's manifests, CI, documented commands, and local instructions are authoritative for its stack and workflow.

## Defaults

- Prefer Python for new application code, scripts, tests, and automation unless the project declares another stack.
- Inspect existing patterns and configuration before adding abstractions or tooling. Keep the change focused; preserve unrelated worktree changes.
- For a new software project, use OpenSpec for requirements, acceptance criteria, and change tracking, plus lightweight ADRs under `docs/adr/`, unless the project already uses another convention.
- Reuse dependencies, services, and setup already declared by the project or previously approved for this task. For a new dependency, framework, runtime service, MCP server, or package-manager workflow, check existing task authorization first. Explain material tradeoffs; ask only when a consequential choice falls outside that authorization.
- Use project-configured verification commands. State commands that were not run and why; never infer a pass from static inspection.

## Testing and verification

Choose tests and checks in proportion to the changed behavior and risk. For a non-trivial feature or bug fix, add or update a focused test when practical. Run the directly relevant configured test or check after implementation, then inspect the diff before handoff. Broaden verification only when the changed interface, project rules, or a concrete risk calls for it.

Do not require a coverage percentage, E2E suite, periodic reruns, or git commits by default. A user or project may explicitly require strict TDD or task-local git checkpoints; read [the strict-TDD reference](references/strict-tdd.md) only then.

## Route by the work

Keep routine, well-specified changes lightweight. Load only the reference that resolves the current need:

- For ambiguous features, domain terms, or work spanning several stages, read [feature planning](references/feature-planning.md). Reuse the existing OpenSpec proposal and acceptance criteria; split implementation into independently verifiable behavior when that helps delivery.
- For a bug with an unclear cause, repeated failed fixes, or a performance regression, read [debugging](references/debugging.md). Establish a signal for the reported failure before choosing a fix.
- For a substantive review, interrupted-task handoff, or a requested retrospective, read [review and continuity](references/review-and-continuity.md). Check requirement fidelity and code quality separately against the actual changed state.

These routes do not require a new issue tracker, a separate specification system, subagents, or additional approval for work already authorized. Clarify only decisions that materially change the outcome or risk; use repository evidence to answer implementation questions first.

## Python guidance

- Prefer readable, explicit code; use type annotations at public and important internal boundaries.
- Use dataclasses, typed dictionaries, protocols, or small classes when they clarify a contract.
- Validate input at system boundaries and raise specific exceptions.
- Keep secrets out of source; use the project's approved configuration or secret mechanism.
- Prefer pytest where it is already an approved project dependency. For pytest techniques, read `../python-testing/SKILL.md`.

## Completion record

Report the changed paths, checks actually run and their results, and any remaining limitation. `NOT RUN` is a valid result when recorded honestly.

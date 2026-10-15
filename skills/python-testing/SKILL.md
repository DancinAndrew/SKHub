---
name: python-testing
description: "Design focused pytest tests for changed Python behavior, including fixtures, parametrization, async boundaries, mocking, and regression reproduction."
---

# Python testing

Shared verification policy lives in `../development-profile/SKILL.md`. Strict TDD, coverage thresholds, E2E suites, and Git checkpoints apply only when required by the user or repository.

## Choose a test that can catch the defect

- Test observable behavior and meaningful invariants through the smallest realistic public boundary. Avoid assertions that merely restate implementation details.
- For a bug, reproduce the reported input/state and assert the correct outcome; establish that the test detects the original defect when practical.
- Derive expected results independently of the production helper under test. Include boundary, empty, invalid, duplicate, and failure cases only when they are relevant to the changed contract.
- Parametrize comparable cases; name them so a failing case is understandable. Keep unrelated scenarios in separate tests.
- Keep fixtures explicit and narrowly scoped. Use `tmp_path`, monkeypatch, and dependency injection to isolate filesystem, environment, clocks, and external clients.
- Mock an external boundary, not the behavior the test is meant to prove. Patch where a symbol is looked up. Use integration tests for semantics that a mock cannot establish, such as transactions or database constraints.
- Use the project's async-test convention; do not create competing event-loop policies. Verify cancellation/cleanup when that is the changed behavior.
- Avoid sleeps and uncontrolled randomness. Prefer a bounded observable condition; seed randomness when it is needed.
- Tests must be independent of order and local credentials. Restore global state and close resources even when an assertion fails.

Run the directly affected configured test command, inspect failures, and expand only when the changed interface or an actual failure justifies it. Report the command, outcome, and unrun checks without presenting static inspection as execution.

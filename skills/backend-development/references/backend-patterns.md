# Backend implementation

- Keep handlers focused on protocol/validation and application orchestration; extract business or persistence boundaries only when they clarify real responsibilities.
- Make transaction boundaries follow invariants. Handle concurrency using the datastore's actual locking, constraints, or optimistic version semantics.
- Diagnose queries with representative data and execution plans before adding indexes or caches. Prevent accidental N+1 access and unbounded scans.
- A cache needs an owner, freshness policy, key schema, invalidation strategy, and observable miss/failure behavior. Cache failure must not silently change correctness.
- Background jobs need durable enqueue semantics, retry limits, idempotent handling, and poison-message handling appropriate to their business effect.
- Separate retryable dependency failures from invalid requests. Bound retries with backoff and an overall deadline; avoid retry amplification across layers.
- Propagate cancellation and deadlines across I/O. Never swallow failure and return a success-shaped default.
- Record useful request/job identifiers and timings without sensitive payloads. Distinguish liveness, readiness, and dependency health.

For FastAPI, schema changes, PostgreSQL, containers, or release behavior, read [stack and operations](stack-and-operations.md). For LLM application behavior, evaluation, and cost, read [LLM systems](llm-systems.md).

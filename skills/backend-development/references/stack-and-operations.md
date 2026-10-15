# Stack and operations

These are conditional checks, not a requirement to adopt this stack.

## Python / FastAPI

Use the installed framework and validation-library versions. Keep request/response models separate from persistence objects when their contracts differ. Use the existing dependency injection and application lifespan patterns for sessions and clients; ensure request-scoped resources close on failure. Do not run blocking libraries directly in async handlers. Expose safe errors while retaining diagnostic causes internally.

## Data migrations / PostgreSQL

Inspect real schema, affected row counts, locks, indexes, constraints, and rollback limitations. For compatibility-sensitive changes, expand the schema, deploy compatible readers/writers, backfill in bounded restartable batches, verify counts/invariants, then contract. Make duplicate and partially completed runs safe. Reversal of schema is not automatically recovery of deleted data; record the actual recovery method before destructive changes. Run production mutations only within their authorization.

Use parameterized queries. Prefer database constraints for data invariants and examine representative execution plans for performance work. Choose transaction isolation according to the invariant rather than applying the strictest level globally.

## Containers / deployment

Reuse the project's Docker/build/release conventions. Keep build secrets and local files out of image context; run with appropriate least privilege. Pin important runtime inputs, handle termination, and test readiness before routing traffic. Define rollout compatibility, rollback or roll-forward conditions, and which migration effects survive a rollback. Preserve existing observability rather than installing a new monitoring stack for a small change.

## Tool servers and error boundaries

For a tool server, separate read-only and mutating operations, validate arguments, make permissions explicit, and return structured success/failure results. Verify the current protocol/SDK docs instead of assuming a remembered transport. Avoid exposing credentials, arbitrary filesystem roots, or unrestricted subprocess execution.

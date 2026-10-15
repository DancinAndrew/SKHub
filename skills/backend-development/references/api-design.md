# API contracts

Read the existing API definition, clients, and compatibility requirements before changing a route.

- Define resource identifiers, ownership, authorization, required/optional/nullable fields, units, and timestamps explicitly. Keep wire names consistent with existing clients.
- Match HTTP method and status semantics to the operation. Never report success before the relevant durable work has succeeded; represent accepted asynchronous work distinctly.
- Use structured, stable error codes with actionable safe messages. Distinguish validation, missing resource, forbidden access, conflict, throttling, unavailable dependency, and unexpected failure according to the API's contract.
- Bound collection responses. Choose pagination and ordering that remain stable under concurrent changes; document cursor expiry and tie-breaking when relevant.
- Enforce authorization on the requested object and tenant, not only at sign-in. Validate filters and sorting against supported fields.
- For retried mutations, define idempotency-key scope, lifetime, and behavior when the same key carries different input. Handle races atomically.
- Evolve APIs compatibly where possible. For intentional breaks, identify affected clients, rollout order, version/deprecation policy, and a verifiable migration path.
- Bound request bodies, upload sizes, concurrency, and expensive queries. Return retry guidance only when supported by the service's real behavior.
- Test contracts through realistic public boundaries, including the important error and authorization cases. Keep published schemas and examples aligned with implementation.

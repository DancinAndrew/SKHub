---
name: backend-development
description: Design or implement backend services, API contracts, persistence, caching, queues, and server-side request handling. Route to the API-contract or implementation reference only when that concern is involved.
---

# Backend Development

Use the project's established framework, storage, deployment model, and conventions. This entrypoint provides routing only; shared development, testing, dependency, and verification policy lives in `../development-profile/SKILL.md`.

- For endpoint shape, HTTP semantics, pagination, response/error contracts, versioning, or rate-limit interfaces, read [API contract guidance](references/api-design.md).
- For request handlers, service/repository boundaries, database access, cache invalidation, background jobs, retries, or operational logging, read [backend implementation patterns](references/backend-patterns.md).
- For FastAPI, database migrations, PostgreSQL, containers, deployment, or tool servers, read [stack and operations](references/stack-and-operations.md).
- For model-backed products, retrieval, evaluations, or model-call cost, read [LLM systems](references/llm-systems.md).
- Load only the references needed by the changed behavior.

Preserve existing contracts unless the requested change deliberately changes them. Make authorization, validation, error exposure, transactional boundaries, and failure behavior explicit in code and tests where they are part of the change.

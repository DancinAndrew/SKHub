# LLM application evaluation and cost

Use this when implementing or evaluating a model-backed product, retrieval pipeline, or model-serving workflow. It does not mandate extra model calls for ordinary development.

- Define the intended behavior and failure cost. Build a small representative evaluation set from permitted data, with expected outputs or a documented rubric independent of the implementation.
- Keep evaluation examples separate from prompt tuning when claiming generalization. Report sample size, dataset/version, model/configuration, and uncertainty; a small demo is not production reliability.
- Distinguish retrieval quality, grounded answer quality, tool correctness, latency, cost, and safety. Diagnose the failing stage instead of swapping the whole pipeline.
- Evaluate deterministic parsing or ordinary code before adding a model. Validate structured output against a schema and handle refusal, truncation, tool failure, and malformed responses explicitly.
- Bound input size, output size, retries, concurrency, and total latency. Treat a lower-priced model as a candidate to test, not proof of lower end-to-end cost.
- Cache only when identity and freshness are defined: relevant content, prompt/schema version, model/configuration, permissions, and expiry. Do not let cached private results cross user boundaries.
- Compare changes against the accepted baseline on the relevant cases. Record regressions as well as improvements; do not loop indefinitely until an evaluation turns green.
- Use primary documentation for current SDK behavior and model availability. Credentials and raw private datasets stay outside the skill repository.

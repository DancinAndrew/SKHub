# Feature planning and delivery

Use for ambiguous requirements, disputed terminology, or work too large to verify as one change. A clear small fix does not need an interview or a new planning document.

## Resolve the decisions that affect implementation

Read the relevant code, existing proposal, acceptance criteria, and ADRs first. Ask only about unresolved user intent, tradeoffs, or constraints that change the behavior or create expensive rework. Reuse decisions already made in this task. Low-risk, reversible details can proceed with a stated assumption.

For an overloaded term, give one concrete example and one edge case. Check the implementation against the user's intended meaning; record any discrepancy instead of silently choosing one. Use an existing glossary where available. Create or extend `GLOSSARY.md` only when a resolved, reusable domain distinction deserves a home. Keep requirements in OpenSpec and implementation decisions in the relevant design document.

Create an ADR for a consequential choice with real alternatives and rationale a future maintainer would otherwise lose. Follow the repository's threshold and location; do not produce an ADR for every minor choice.

## Deliver verifiable slices

Use the project's existing task list, normally the OpenSpec change's `tasks.md`. For each useful slice record:

- Observable behavior and how to demonstrate or check it.
- Genuine prerequisites; do not invent dependencies solely to force a linear sequence.
- Scope boundaries, relevant interfaces, and any unresolved decision that blocks this slice.

A slice should complete a narrow path through whichever layers that behavior actually needs. An API-only change need not acquire a UI. Prefer proving the highest-risk path early and keep unfinished slices visible.

For a wide mechanical refactor that cannot land independently, consider adding the compatible new form, migrating callers in bounded batches, then removing the old form. If intermediate states cannot pass the required checks, state where integration verification happens. Schema or data migration authorization remains separate from this planning technique.

Use an isolated prototype only to answer a concrete design uncertainty. Record the question, observed result, and limitations; keep disposable code outside production paths. Do not present the prototype as an implemented or deployed feature.

Update the existing plan when evidence changes it. Publishing tickets, sending messages, or adopting a new tracker requires authorization for that action; a planning request alone does not imply it. Delegate only under applicable user and environment rules.

## Challenge a consequential specification

When the user requests a specification review or a consequential design has unresolved failure modes, check ambiguous defaults, domain terms, ownership/permissions, null/empty states, concurrency, retries, partial failure, observable acceptance criteria, and recovery. Report only concrete gaps with their impact; do not manufacture an adversarial tone or require a second review cycle after every small edit. Incorporate accepted corrections into the existing specification.

For architectural decisions, record date/status, context, decision, realistic alternatives, and consequences under the repository's ADR convention (default `docs/adr/`). Mark a superseded decision and link its replacement instead of silently rewriting the historical rationale.

Update existing architecture/setup/runbook documentation when the shipped behavior changes it. Do not create a parallel `sysdoc/` tree when the repository already has an adequate documentation home. Prefer installed OpenSpec commands, verified against the installed CLI, without installing or initializing new tooling unless the task authorizes that setup.

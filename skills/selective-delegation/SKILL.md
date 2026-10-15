---
name: selective-delegation
description: Select model and reasoning effort for bounded execution subtasks, then review returned changes without repeating the work. Use when the user requests model-based delegation or an approved multi-step implementation has independently verifiable work worth delegating. Skip routine questions and tiny edits.
---

# Selective Delegation

Optimize total effort to reach an accepted result, including handoff, review and rework. A smaller model or more agents does not by itself demonstrate lower usage. This skill uses available native subagents; it neither changes the parent model nor creates separate user-owned tasks or API billing paths.

## Decide once at the task boundary

Reuse accepted decisions and current evidence; do not repeat the planning or discovery that produced them. Reassess routing only after a material change in scope, risk, requirements or observed worker failure.

Delegate only when all are true:
- The worker owns a bounded result with explicit acceptance criteria and can work independently alongside useful parent work.
- Relevant context can be conveyed compactly without losing critical constraints.
- Review can check the result and evidence more cheaply than reproducing the implementation.
- The expected execution saved plausibly exceeds dispatch, context transfer and review overhead.

Otherwise work directly. Low usage, not agent count, is the goal. Begin with one worker; add others only for genuinely independent work with enough scope to justify coordination. Do not delegate the same responsibility to multiple agents or recursively delegate without a concrete need.

## Choose from the current host

Respect explicit user model preferences and the available tools. Choose a supported faster model for a bounded task only when expected execution plus review is cheaper. Otherwise work directly. Do not install a different runtime merely to obtain a model. For host-specific mechanics, read [platform adapters](references/platforms.md).

## Hand off a compact task packet

Include only what the worker needs:
- Outcome and exact owned files/responsibilities; tell the worker it is not alone and must preserve others' edits.
- Accepted decisions, authoritative paths, necessary constraints and concrete acceptance checks.
- Evidence already obtained, its source/state, and checks already completed; distinguish assumptions and unresolved questions.
- What not to repeat: completed inventory/research, whole-repo exploration, parent-owned work, extra reports or unrelated improvements.
- Authority boundaries, a bounded retry policy, and the receipt below.

Workers inspect their owned inputs before editing. Preserve sufficient raw context for correctness; do not hide uncertainty to save tokens. Permit one targeted correction round for an identified defect; on repeated same failure or an architecture/permission boundary, report and return control. Escalate based on the actual failure, not automatically through every model tier.

The parent handles disjoint work, prepares focused integration checks, or waits without busy polling. It must not implement the worker's deliverable in parallel. Do not copy large logs or full histories into handoffs or return messages.

## Require a compact completion receipt

The worker returns:
1. Changed paths and a concise description; a diff or exact changed locations.
2. Input and output identity (commit or file hashes for material changes).
3. Checks executed, relevant working directory, outcome and evidence/log path if needed.
4. Unrun checks, remaining risks, assumptions and blockers. No unsupported PASS claims.

A receipt is evidence to inspect, not a substitute for review.

## Review guard: inspect the delta, do not redo the task

Review against the accepted criteria in this order:
1. Confirm scope and that the receipt describes the current artifact version.
2. Inspect the actual diff and risk-bearing changed sections, plus surrounding context where needed. Do not reread the whole corpus or rederive the solution by default.
3. Accept credible, reproducible worker checks bound to that version. Run only uncovered integration/acceptance checks that add new evidence.
4. If there is a concrete defect, identify it precisely and assign a targeted fix to its owner. Do not silently rewrite the whole deliverable or ask another agent to solve the same task again.

A rerun is justified by changed artifacts or dependencies, stale/inconsistent evidence, a failed check, an untested interface, or a specific unresolved risk. State that reason before rerunning, and rerun the affected check only. Mandatory independent review/security gates still apply; scope them to their purpose.

**Stop condition:** accepted scope, inspected changes and sufficient current acceptance evidence, with no unresolved material issue. Do not add another reviewer or rerun passing checks for reassurance. Do not bypass needed verification to claim savings.

## Report honestly

Briefly name the delegated scope and selected model, the review/integration evidence, and any unresolved limitation. Distinguish reading a rule, static validation, live execution and fresh-session discovery. Claim usage savings only with attributable, comparable measurements including parent, workers, retries and review; shared account limit percentages alone are not a reliable per-task measurement.

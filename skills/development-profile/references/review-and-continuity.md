# Review and continuity

## Review the state the user actually asked about

Determine whether the scope is a PR, committed branch changes, staged changes, unstaged changes, or their combination. Resolve a comparison base from the request or repository evidence and record it when material. A `base...HEAD` diff omits uncommitted work; include staged, unstaged, and relevant untracked files when they belong to the requested review. Ask only when the intended scope cannot be inferred.

Keep two questions distinct:

1. **Requirement fidelity:** Does the change implement the accepted behavior and acceptance criteria? Identify missing or incorrect behavior and unrequested expansion. Use the user request when no formal spec exists; do not force a new document as a prerequisite.
2. **Code quality and correctness:** Examine error paths, contracts, state transitions, security-relevant changes, and maintainability in the context of repository rules. Distinguish a concrete defect from a style preference or a design heuristic. Do not repeat findings already enforced by a passing configured check.

Each actionable finding needs a location, triggering condition, consequence, and a practical correction. Report relevant passing checks and `NOT RUN` separately from static review. Use independent reviewers only when delegation is permitted and adds enough value; two review questions do not require two agents.

## Handoff only when continuity needs it

For interrupted work or a handoff request, reference existing specifications, decisions, and artifacts instead of copying them. Preserve:

- Intended outcome, accepted decisions, and remaining work.
- Repository/worktree location, branch or commit, and relevant uncommitted state.
- Checks actually run, the artifact state they apply to, and failures or `NOT RUN` items.
- Current blocker, next verifiable action, and applicable authorization boundaries.

Use an existing handoff location. If none exists, choose a workspace-local work directory or the user's requested destination, and return its path. Include only information the next session needs; omit credentials and unrelated personal details.

## Retrospective when requested or a repeated failure justifies it

Use concrete session evidence to identify the smallest useful environment improvement. For a mechanical, repeated mistake, first check whether an existing lint, type, or test command can catch it. For a judgment problem, refine a narrowly scoped instruction. Avoid growing global AGENTS.md with project rules, installing new tooling without authorization, or adding process for hypothetical failures.

For an incident retrospective, stabilize service first within the authorized operational scope. Reconstruct introduction, trigger, detection, and recovery from evidence; distinguish direct cause from the process gap. Record impact, recovery, the smallest regression guard, and any accepted residual risk in the existing incident record. Do not append permanent global rules for every one-off mistake.

# Subagent escalation prompts

Do not use subagents for a normal 3-5 day batch unless an escalation condition
in `SKILL.md` applies.

## Incremental independent reviewer

Use one agent with role `independent-reviewer`.

Give it:

- current and boundary sessions;
- canonical dataset or exact referenced records;
- the draft batch report;
- current media review when relevant.

Ask it to verify:

- attribution and call sequence;
- current-versus-historical change claims;
- strongest non-romantic explanation;
- probability movements over 5 points;
- advice consistency with reciprocity and boundaries;
- citation validity and cross-session ranges.

Forbid sibling reports and unrelated old analyses.

## Bootstrap or full-rebaseline session reader

Use role `session-reader`. Assign raw sessions and require a chronological
evidence log covering mundane interaction, initiative, care, plans, refusal,
calls, media, and uncertainty. Do not provide an intended conclusion.

## Bootstrap or full-rebaseline final reviewer

Use role `final-reviewer` after the draft exists. Require raw-record checks for
citations, dates, attribution, competing explanations, probabilities, and
advice safety.

## Manifest

Only create `analysis_support/run_manifest.json` when an agent was actually
used. Record:

- execution kind and agent ID;
- role;
- input scope and forbidden reads;
- terminal status;
- output path, size, and SHA-256.

Set `required_roles` to the roles actually required for that run. Do not claim
the manifest proves billing or visible account usage.

Example:

```json
{
  "mode": "incremental",
  "required_roles": ["independent-reviewer"],
  "agents": [
    {
      "execution_kind": "subagent",
      "agent_id": "019...",
      "role": "independent-reviewer",
      "input_scope": ["current sessions", "draft relationship_analysis.md"],
      "forbidden_reads": ["unrelated prior reports"],
      "status": "completed",
      "output_path": "independent_review.md",
      "size": 1234,
      "sha256": "..."
    }
  ]
}
```

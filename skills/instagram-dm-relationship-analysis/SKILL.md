---
name: instagram-dm-relationship-analysis
description: Analyze Instagram direct-message exports as evidence-backed relationship updates. Use for first-time or recurring 3-5 day Instagram `message_*.json` batches when Codex must normalize raw messages, compare the new window with prior behavior, write a Traditional Chinese analysis inside that batch folder, estimate relationship-state changes, and give natural practical suggestions for conversation topics, contact rhythm, or low-pressure calls.
---

# Instagram DM Relationship Analysis

Analyze the current batch deeply without regenerating a long cumulative essay every time. Keep raw evidence canonical, but make each batch folder the human-facing unit of analysis.

## Read the required references

Read:

- `references/analysis-framework.md` for evidence weighting and attribution.
- `references/report-contract.md` for file locations and report sections.
- `references/subagent-prompts.md` only when the escalation rules below require a subagent.

## Choose paths

Identify:

- **conversation root**: the parent containing all dated export folders;
- **current batch folder**: the folder named by the user, such as `0616~0619/`;
- **state directory**: `<conversation-root>/.relationship-analysis-state/`.

If a legacy analysis directory already contains `canonical_dataset.json`, use
that directory as the state directory to preserve stable IDs. Do not keep
updating its cumulative prose report.

Write the human-facing outputs into the current batch folder:

- `relationship_analysis.md`
- `verification.json`
- `media_review.md` only when visual inspection materially affects a conclusion.

Keep canonical machine artifacts in the state directory. Do not update
`complete_relationship_analysis.md` during a normal incremental batch.

## Select the run mode

Use **bootstrap** when no canonical dataset exists.

Use **incremental** when the state directory already contains
`canonical_dataset.json`.

Use **full rebaseline** only when:

- records disappeared, were backfilled into older dates, or session boundaries drifted;
- identity, timestamp, or deduplication assumptions changed;
- new evidence materially contradicts the prior model;
- the user explicitly asks to start over.

Do not force periodic rebaselines solely because a fixed number of batches or
days has elapsed.

## Enforce source isolation

For factual claims, use only raw exports, media, canonical records, and stable
`Sxxx` / `Mxxxxxx` citations.

In incremental mode:

1. Rebuild the canonical dataset from every raw export currently under the conversation root.
2. Read the current batch and its boundary session before reading prior analysis.
3. Read only the most recent one or two earlier `relationship_analysis.md` files to recover the previous model and unresolved questions.
4. Confirm any historical comparison against canonical raw anchors before citing it.

If no earlier batch report exists yet, use the legacy
`complete_relationship_analysis.md` once as the comparison baseline.

Prior analyses are comparison aids, not evidence. Do not use Codex memory or
prior chat as evidence. Never modify raw exports.

## Build canonical state

Run:

```bash
python3 scripts/build_canonical.py \
  --root "<conversation-root>" \
  --output "<conversation-root>/.relationship-analysis-state" \
  --timezone "Asia/Taipei" \
  --session-gap-minutes 120
```

Inspect `data_audit.md` and `incremental_change.md`. Stop on ambiguous identity,
invalid timestamps, unparseable raw files, or unexplained loss of prior records.

Treat M IDs as stable references, not guaranteed chronological order after a
historical backfill.

## Inspect only relevant evidence

For a normal 3-5 day batch:

- fully read every new or changed session;
- read one preceding boundary session and one following session when present;
- inspect attachments from the current batch;
- retrieve older raw anchors only for behaviors being compared;
- do not reread the entire historical transcript unless the model is genuinely in conflict.

Use contact sheets only when media volume or content makes them useful. Treat
unplayable or untranscribed media as unknown.

Distinguish initiation, acceptance, extension, execution, and repair. For calls,
separate proposed, attempted, missed, returned, and completed calls.

## Use subagents sparingly

Default for a normal batch: **no subagent**.

Use exactly one independent reviewer only when at least one condition applies:

- more than 7 new calendar days or 1,500 new records;
- raw-data integrity or attribution is ambiguous;
- the proposed probability range moves by more than 10 percentage points;
- new evidence directly contradicts the previous relationship model;
- the user explicitly requests independent agents or exhaustive review.

For bootstrap or full rebaseline, use at most two agents: one session reader and
one final reviewer. Do not create separate agents for tasks the main agent can
perform in one pass.

If an agent is used, save its artifact and manifest under
`<current-batch>/analysis_support/`. Otherwise create neither.

## Write the batch analysis

Follow `references/report-contract.md`. Write direct Traditional Chinese.

Focus on:

- what happened in this batch;
- what genuinely changed versus repeated the prior pattern;
- current asymmetry, boundaries, calls, plans, and follow-through;
- strongest romantic and non-romantic explanations;
- old versus new probability ranges;
- practical next-step suggestions grounded in current shared topics.

For important conclusions, cite current-batch `Sxxx` / `Mxxxxxx` ranges. When
claiming change over time, include at least one confirmed older raw anchor.

Advice must be natural and non-manipulative:

- suggest topics already alive in the conversation;
- suggest a reasonable contact rhythm or low-pressure call context;
- prefer actions over canned lines;
- do not recommend jealousy, strategic silence, pressure, tests, or engineered dependence;
- provide exact wording only when the user explicitly asks for message wording.

## Verify

Run:

```bash
python3 scripts/verify_analysis.py \
  --dataset "<conversation-root>/.relationship-analysis-state/canonical_dataset.json" \
  --report "<current-batch>/relationship_analysis.md" \
  --output "<current-batch>/verification.json" \
  --date-from "YYYY-MM-DD" \
  --date-to "YYYY-MM-DD" \
  --require-batch-report \
  --strict
```

If `analysis_support/run_manifest.json` exists, also pass:

```bash
--run-dir "<current-batch>/analysis_support"
```

Fix invalid IDs, cross-session ranges, missing batch dates, attribution errors,
stale counts, and missing required sections before finishing.

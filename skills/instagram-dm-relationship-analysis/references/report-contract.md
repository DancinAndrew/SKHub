# Output and report contract

## File layout

Keep machine state under:

`<conversation-root>/.relationship-analysis-state/`

This directory contains the canonical dataset, audit, transcript, daily files,
session index, media index, and generated agent inputs.

For every dated batch, write into that batch folder:

- `relationship_analysis.md`
- `verification.json`
- `media_review.md` only when media affects interpretation
- `analysis_support/` only when a subagent is justified

Do not append every batch into a cumulative narrative report. Older batch
reports remain the historical analysis trail.

## Batch report

Write `relationship_analysis.md` in Traditional Chinese with these sections:

1. `## 本批範圍與資料品質`
   - raw files, exact dates, new/duplicate/missing/backfilled counts;
   - sessions and boundary context reviewed;
   - media and call limitations.
2. `## 這幾天發生了什麼`
   - chronological summary of mundane and emotionally meaningful interaction;
   - cite current `Sxxx` / `Mxxxxxx`.
3. `## 相較前一階段的變化`
   - improved, weakened, or unchanged behavior;
   - distinguish real change from repetition;
   - cite current evidence plus confirmed older raw anchors for longitudinal claims.
4. `## 主動性、互惠與不對稱`
5. `## 情緒投入、曖昧與現實進展`
6. `## 反證與其他合理解釋`
7. `## 更新後的關係判斷`
8. `## 我建議你接下來怎麼做`
9. `## 尚待觀察`

Keep the report centered on the current batch. Historical material should
explain movement, not retell the entire relationship.

## Updated relationship model

Estimate separately:

- 她對我有特殊情感
- 她對我有浪漫吸引
- 她正在重新喜歡我
- 她享受目前的親密與曖昧
- 她願意在現實中繼續升級
- 她願意重新建立正式關係

For each item include:

- previous range when available;
- updated subjective range;
- direction of movement;
- strongest support and counterevidence;
- one short reason for the change or stability.

Ranges are behavioral estimates, not statistical outputs and do not sum to
100%.

## Advice contract

Give 3-6 concise, evidence-grounded suggestions. Cover only useful categories:

- current topics worth extending;
- whether to keep, reduce, or slightly increase contact rhythm;
- a natural reason or context for a call;
- a concrete shared activity that follows from existing conversation;
- one behavior to avoid because the current interaction is asymmetric or sensitive.

Prefer direct guidance such as:

- continue the music or study topic because the other person already initiated it;
- suggest a short call while commuting or doing a shared task;
- convert a vague shared activity into one specific date only after the other person re-engages.

Do not invent polished romantic scripts. Do not prescribe manipulation,
jealousy, delayed replies, emotional tests, pressure, or repeated pursuit after
weak reciprocity. Give exact wording only if the user asks for wording.

## Citation rules

- Every material current-batch conclusion needs an `Sxxx` and `Mxxxxxx` anchor.
- A message range must remain inside one session.
- Historical comparisons require at least one old and one current raw anchor.
- Identify who initiated, accepted, extended, executed, and repaired.
- Retain contradictions and unknowns.

## Bootstrap exception

On the first-ever batch, the same report may summarize the full available
history because no previous batch analysis exists. Even then, keep the
human-facing report inside the batch folder selected by the user.

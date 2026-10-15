# Rewrite Standard

## Contents

1. Preservation contract
2. Claim classification
3. Evidence hierarchy
4. Domain checks
5. Concept-first replacement
6. Terminology pattern
7. Uncertainty gates
8. Failure modes
9. Completion checklist

## 1. Preservation Contract

The target is a learning artifact. Accuracy and learnability are joint requirements.

Preserve by default:

- the main question and intended audience;
- chronology and causal sequence;
- major sections and conceptual progression;
- examples that help transfer the concept;
- tables or diagrams that remain accurate;
- internal links, aliases, and useful metadata;
- the author's level of depth and language unless it obstructs accuracy.

Do not preserve:

- fabricated precision;
- duplicated claims;
- unsupported rankings or superlatives;
- incorrect formulas;
- stale legal or current-status conclusions;
- false causal explanations;
- broken links presented as evidence.

If deleting a false block creates a learning gap, replace it with a mechanism, boundary, or worked example.

## 2. Claim Classification

| Class | Test | Action |
|---|---|---|
| Verified fact | Primary source supports the same scope, date, unit, and wording | Retain and cite |
| Misleading | Core fact is true but framing, denominator, or context changes its meaning | Rewrite with context |
| Outdated | Was true at a named date but is no longer current | Date it or update it |
| Unsupported precision | Exact number has no adequate source or false precision exceeds the evidence | Remove the number; teach the mechanism |
| Inference | Reasonable conclusion derived from facts | Label as analysis and show the bridge |
| Model assumption | Depends on growth, margin, discount rate, scenario, or forecast | Label and show sensitivity |
| Opinion/framing | Interpretive claim or rhetorical title | Keep only when clearly framed |
| Conflict | Reliable sources disagree | Present both and ask if a stance is required |

Audit words that often hide weak claims:

`proves`, `caused`, `therefore`, `always`, `only`, `best`, `first`, `largest`, `most profitable`, `industry standard`, `users prefer`, `cost fell`, `margin rose`, `will`, `target`, `expected`.

## 3. Evidence Hierarchy

Use the strongest source appropriate to the claim:

1. Regulatory filing, audited report, statute, regulation, court order, standard, dataset, or original research.
2. Official product announcement, developer documentation, investor presentation, or organization statement.
3. High-quality secondary reporting that links to or quotes the primary record.
4. Industry analysis with transparent methodology.
5. Search snippets, unsourced summaries, aggregators, and social posts only as leads.

Source-role rules:

- A company filing supports what the company reported and its accounting data.
- A press release supports launch timing and company claims; performance claims must retain their test conditions or attribution.
- A complaint supports allegations, not liability.
- A court docket supports procedural status; use the actual order for holdings.
- A teardown supports estimated component cost, not full product cost or gross margin.
- A market study supports only its sample, date, geography, and methodology.
- A current price, officeholder, law, product, or case status must be reverified live.

For every important source, record what it cannot support. This prevents citation laundering.

## 4. Domain Checks

### Finance and accounting

- Match fiscal year, currency, unit, and restatement basis.
- Distinguish revenue, billings, bookings, GMV, commission, gross profit, operating income, net income, CFO, capex, and FCF.
- Do not infer product-level margins when only category margins are disclosed.
- Adjust share comparisons for stock splits and dilution.
- Treat DCF, target prices, WACC, terminal growth, and segment multiples as assumptions.
- Explain buybacks through price paid, alternatives, dilution, and capital structure; EPS accretion alone is insufficient.

### Law and regulation

- Separate allegation, trial decision, appeal, injunction, enforcement, settlement, and final status.
- Identify jurisdiction and effective date.
- Do not call market power illegal without the relevant conduct and legal standard.
- Verify changing platform terms and regional rules from current official materials.

### History and product timelines

- Prefer original announcements and contemporary filings.
- Separate announcement, launch, availability, fiscal-year sales, and later milestones.
- Avoid combining figures from different dates into one event.

### Technology and performance

- Preserve benchmark baseline, workload, device, configuration, and `up to` language.
- Distinguish design from manufacturing and self-developed from fully self-produced.
- Do not infer cost savings from performance improvement without evidence.

### Supply chain and trade

- Distinguish supplier presence from production share.
- Avoid fixed country shares, yields, wages, or targets without dated methodology.
- Compare total landed cost, resilience, capacity ramp, concentration, and substitution constraints.
- Apply export controls through item classification, end use, end user, destination, and date; never by the label `AI chip` alone.

### Marketing and economics

- Brand premium is willingness to pay, not retail price minus BOM.
- Direct network effects, cross-side network effects, complementarity, scale economies, and switching costs are different mechanisms.
- Demand elasticity requires observed behavior or a model; do not draw a factual demand curve from intuition.
- Price discrimination and versioning require precise definitions and applicable conditions.

## 5. Concept-First Replacement

When an unsupported number was intended to teach something, replace it as follows:

| Bad pattern | Better teaching replacement |
|---|---|
| `Brand premium = 54%` | Explain willingness to pay, alternatives, and non-BOM costs |
| `Self-designed chip cut cost 40%` | Explain roadmap control, co-design, dependency redistribution, and missing disclosure |
| `Users are 50% more likely to buy another device` | Explain complementarity and state that magnitude needs behavioral evidence |
| `Supply moved from country A to B by X%` | Explain concentration, ramp-up, total landed cost, and source limits |
| `The court ruled the company is a monopoly` | State the actual claim, holding, remedy, appeal, and unresolved issues |
| `DCF says fair price is $X` | Show cash-flow basis, assumptions, sensitivity, and range |

The replacement should answer:

1. What is the concept?
2. How does it operate in this case?
3. Under what conditions does it hold?
4. What evidence would be needed to quantify it?
5. What is the common misinterpretation?

## 6. Terminology Pattern

A useful term supplement contains four layers:

1. concise definition;
2. mechanism;
3. case application;
4. boundary or common confusion.

Do not add glossary entries merely to increase count. Add a term where the reader needs it to follow the argument or transfer the idea to another case.

Prefer an Obsidian callout when it keeps the main narrative readable:

```markdown
> [!info] 術語：Switching cost（轉換成本）
> 轉換供應商、平台或產品時產生的金錢、時間、資料、學習與中斷成本。
>
> 在本案例中……。它與網路效應不同，因為……。
```

## 7. Uncertainty Gates

Ask the user before proceeding when:

- two similarly named files could both be the target;
- the user may want visible correction markers instead of a clean article;
- removing a disputed section changes the note's thesis;
- reliable sources conflict on a central claim;
- an important claim cannot be verified or safely qualified;
- a reference draft proposes a different audience, depth, or structure;
- the task would alter raw evidence or another protected vault layer.

Do not ask for routine choices that can be resolved from the note, vault rules, or source hierarchy.

## 8. Failure Modes

### Accurate but unusable summary

Cause: treating fact-checking as compression. Fix: preserve the narrative spine and replace bad material at comparable conceptual depth.

### Correct source, overstated claim

Cause: citing a source that supports only part of the sentence. Fix: narrow wording or add another source.

### Audit draft becomes final article

Cause: a concise verification note is mistaken for the learning artifact. Fix: use it as a claim map, not as the replacement structure.

### Wrong file edited

Cause: similar names or Unicode punctuation. Fix: resolve exact paths and state the target before editing.

### Source tightening becomes a second rewrite

Cause: restarting after every new source. Fix: patch unsupported details while preserving the accepted structure.

### Numbers survive because they look educational

Cause: false precision feels concrete. Fix: retain only sourced numbers whose denominator, date, and learning role are clear.

## 9. Completion Checklist

- [ ] Exact target path confirmed.
- [ ] Full original and named references read.
- [ ] Preservation contract established.
- [ ] Current or high-risk facts researched live.
- [ ] Primary sources opened, not only search results.
- [ ] Unsupported precision corrected, qualified, or replaced.
- [ ] Facts, analysis, assumptions, and legal status separated.
- [ ] Important terms explain definition, application, and boundary.
- [ ] Original learning flow remains usable.
- [ ] Internal links and frontmatter remain valid.
- [ ] Footnotes resolve and support nearby claims.
- [ ] Validator passes.
- [ ] Known bad phrases no longer assert false claims.
- [ ] Final file reread.
- [ ] Unchanged reference files confirmed.

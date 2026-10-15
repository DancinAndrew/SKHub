---
name: source-grounded-note-rewriter
description: Fact-check and rewrite an existing Markdown or Obsidian learning note in place while preserving its long-form narrative, examples, conceptual sequence, and useful detail. Use when the user asks to correct an article, audit a case study, replace unsupported claims with accurate explanations, add terminology, reconcile a source note with a fact-check draft, or says the note is for learning rather than summarization. Especially suited to business, company, finance, technology, policy, legal, history, and other source-sensitive notes where current facts must be verified and unsupported precision must not survive.
---

# Source-Grounded Note Rewriter

Correct the note without flattening it. Treat the original article as a learning artifact, not raw material for a shorter memo.

Read [references/rewrite-standard.md](references/rewrite-standard.md) completely before editing a target note.

## Workflow

### 1. Resolve the exact target

1. Read repository or vault instructions first.
2. Resolve the user-provided path with `rg --files`; treat Unicode punctuation and similarly named files as distinct.
3. Read the full target and any reference/audit draft the user named.
4. Record line count, headings, frontmatter, links, callouts, tables, code fences, and source style.
5. Save a temporary pre-edit snapshot for structural comparison.

Never guess which of two similar files is canonical. Never edit the audit/reference file unless the user asks.

### 2. Establish the preservation contract

Infer the note's audience, learning purpose, narrative spine, and must-keep sections. Default to:

- preserve topic order and case chronology;
- retain useful examples and explanatory depth;
- preserve internal links and valid frontmatter;
- replace false material with correct teaching material instead of merely deleting it;
- keep numbers only when they clarify a mechanism and have a reliable source.

Ask before editing only when uncertainty is consequential: multiple plausible target files, clean rewrite versus visible annotations, conflicting sources that change the article's stance, or an important claim that cannot be verified or safely qualified.

### 3. Build a claim map

Classify substantive claims as:

- verified fact;
- correct but misleading or missing context;
- outdated fact;
- unsupported precision;
- inference or model assumption;
- opinion or framing.

Search especially for dates, percentages, rankings, causal claims, superlatives, legal outcomes, forecasts, unit economics, margins, market shares, and quotes.

### 4. Research from the source outward

Use live research whenever facts may have changed. Prefer original filings, official announcements, regulators, court dockets, standards, and primary research. Treat company materials as authoritative for what the company reported, not as independent proof that its interpretation is correct.

Keep a compact source ledger while researching:

```text
claim -> status -> source -> supported wording -> limitation
```

Do not use search snippets as final evidence. Open the source and verify the exact passage, date, unit, scope, and reporting basis.

### 5. Decide the correction action

For each problematic passage, choose one action:

1. **Correct** the fact while retaining the explanation.
2. **Qualify** a claim whose boundary or legal status was overstated.
3. **Relabel** an estimate, inference, scenario, or company claim.
4. **Replace** unsupported precision with the mechanism it was trying to teach.
5. **Remove** only when the material is false, duplicative, or has no learning value after correction.

When a number disappears, preserve its intended lesson with a correct concept, decision rule, comparison, or example.

### 6. Rewrite in place

Preserve the existing learning spine. Do not turn the note into a summary, audit checklist, or list of key takeaways unless the user explicitly asks.

Use this pattern for terminology:

```markdown
> [!info] 術語：Term（中文）
> 定義。
>
> 在本案例中的作用、適用條件，以及最容易誤解的邊界。
```

Separate:

- reported facts;
- analysis and causal interpretation;
- model assumptions or scenarios;
- current legal allegations, decisions, and unresolved proceedings.

For Obsidian notes, compose with the `obsidian-markdown` skill. Use wikilinks for internal notes, standard Markdown links for external sources, and footnotes near the claims they support.

### 7. Tighten high-risk sections

Re-read financial, legal, regulatory, historical, medical, scientific, and current-status sections after the main rewrite. Check that:

- accounting periods and units match;
- gross, net, billings, revenue, margin, and cash flow are not conflated;
- filings compared across time use the same basis;
- allegations are not written as judgments;
- forecasts and valuation outputs are not presented as facts;
- correlation is not rewritten as causation;
- company claims retain attribution when independent verification is absent.

### 8. Validate before finishing

Run the bundled validator:

```bash
python3 scripts/validate_note.py <rewritten-note> \
  --before <temporary-original> \
  --max-heading-loss 0.25 \
  --require-sources 1
```

Then:

1. Search for known bad phrases and suspicious precision from the original.
2. Confirm every footnote reference has a definition and every URL supports nearby wording.
3. Confirm frontmatter and code fences are closed.
4. Re-read the opening, transitions, terminology callouts, and conclusion as a learner.
5. Check Git status and avoid staging or committing unless requested.

## Hard Rules

- Do not replace a studyable article with a compressed teaching summary.
- Do not delete context merely because it is hard to source; correct, qualify, or ask first.
- Do not turn BOM estimates into product margin or brand premium.
- Do not invent percentages, rankings, customer behavior, cost savings, or causal impact.
- Do not silently resolve genuine source conflicts.
- Do not cite a source for a stronger claim than the source supports.
- Do not treat an audit draft as the final article unless the user explicitly wants that format.
- Do not report completion until the real file has been reread and validated.

## Completion Report

State:

- the exact file changed;
- the learning structure preserved;
- the main correction classes;
- source and terminology coverage without implying that counts prove quality;
- validation performed and any remaining uncertainty;
- whether other similarly named files were left untouched.

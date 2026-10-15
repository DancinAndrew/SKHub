# Sources and consolidation

This repository maintains selected personal workflows, not a mirror of upstream skill packs.

- **agentkit**, DancinAndrew/agentkit, source commit `f02fe81cb5b8930fbf337a79baa7b7d96c926cfc`: requirement clarification, ADRs, domain vocabulary, debugging, specification review, retrospective, backend/operations and LLM evaluation concepts were integrated into existing skills. The old global rules, commands, agent roster, automatic memory conventions, universal TDD/coverage policy, installer, and permission templates were not carried forward.
- **ECC**, affaan-m/ECC, via agentkit and existing local adaptations: backend, Python, testing, security and Git guidance. MIT notice retained in `licenses/ECC-MIT.txt`. Imported generic tutorials were condensed and conflicting policy replaced by development-profile.
- **mattpocock/skills**, source commit `49dd158d1076134a641b33efb035946536778336`: feature slicing, falsifiable debugging, domain terms, review/handoff, and useful interface guidance adapted into development-profile and coding-standards. MIT notice in `licenses/mattpocock-MIT.txt`.
- **kepano/obsidian-skills**: existing Obsidian CLI, Markdown, Bases, and Defuddle guidance; MIT notice in `licenses/obsidian-skills-MIT.txt`. Bases is now a reference under obsidian-markdown rather than a second skill entry.
- **OpenAI skills**: existing Playwright CLI skill and supporting scripts. Apache-2.0 license and NOTICE retained in `skills/playwright/`.
- **tech-resume**: principles paraphrased from Gergely Orosz's The Tech Resume Inside Out and official program guidance; no book reproduction. Personal resume-health-check guidance is now a reference.
- **career-ops-hq/career-ops**: the existing private runtime stays under `.local/runtime/`; only a small routing entry is published here. Its upstream license and Git history remain inside the runtime.
- Other personal skills retain their source notes and references. Personal voice calibration, machine paths, runtime data, and the installed impeccable bundle are excluded from public commits.

Retirement decisions live in manifest.json. Historical originals are recoverable from the one local consolidation archive and the original upstream Git history; they are not installed or loaded automatically. Platform-owned plugins and account-synchronized skills remain outside this repository's maintenance scope.

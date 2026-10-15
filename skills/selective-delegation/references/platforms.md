# Platform adapters

Read the actual tool schema before dispatch. The workflow is shared; API names and available models are not.

- Codex: use its available native collaboration tool. If a model/effort override requires a context-free fork, provide a bounded task packet with the required evidence. Do not create a user-owned chat for an internal subtask.
- Claude Code: use its exposed native subagent/Agent interface and supported model choices. Do not copy Codex model IDs or parameters into it.
- Any host: respect current delegation restrictions, explicit user model choices, and permission boundaries. If the requested model is unavailable, use an allowed alternative or work directly; disclose a material substitution. Return evidence without repeating the entire exploration.

---
name: git-workflow
description: "Inspect and safely change Git branches, commits, conflicts, and pull requests while preserving unrelated work and reviewable history."
---

# Git workflow

- Inspect status, current branch, remotes, and existing work before changing Git state. Include staged, unstaged, and relevant untracked files in the intended scope.
- Reuse the repository's contribution and commit conventions. Prefer a focused branch and reviewable changes for shared repositories.
- Stage explicit paths or hunks. Do not bundle unrelated local edits or generated private artifacts into a commit.
- Write commit and PR descriptions around the concrete problem, resulting behavior, and checks actually run. Follow an existing PR template when required.
- Inspect a conflict's base and both changes before resolving it. Preserve independently intended behavior, then run the affected verification.
- Do not rewrite shared/default-branch history, force-push, discard changes, or delete branches unless that action is authorized. Prefer a revert for a published mistake.
- Use the requested comparison base. A committed-branch diff does not include working-tree changes; state which scope was reviewed.
- Keep secrets, private source material, runtime dependencies, and machine-specific configuration out of public commits. Check the staged diff before publishing.
- Publish or merge only within the task's authorization; repository cleanup does not require rewriting old commits.

For an interrupted task, use `../development-profile/references/review-and-continuity.md` to recover actual repository state before resuming.

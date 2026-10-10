#!/usr/bin/env bash
# Symlink every skill under ./skills into the Claude Code skills directory.
# Idempotent: refreshes existing symlinks, never overwrites a real directory.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"

mkdir -p "$TARGET_DIR"

for skill_path in "$REPO_DIR"/skills/*/; do
  [ -f "${skill_path}SKILL.md" ] || continue
  skill_dir="${skill_path%/}"
  name="$(basename "$skill_dir")"
  link="$TARGET_DIR/$name"

  if [ -L "$link" ]; then
    ln -sfn "$skill_dir" "$link"
    echo "updated  $name"
  elif [ -e "$link" ]; then
    echo "skipped  $name (a non-symlink already exists at $link)" >&2
  else
    ln -s "$skill_dir" "$link"
    echo "linked   $name"
  fi
done

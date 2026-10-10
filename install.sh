#!/usr/bin/env bash
# Symlink every skill under ./skills into each skills directory agents read from:
# ~/.claude/skills (Claude Code) and ~/.agents/skills (Codex and other agents).
# Idempotent: refreshes existing symlinks, never overwrites a real directory.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIRS="${SKILL_TARGET_DIRS:-$HOME/.claude/skills:$HOME/.agents/skills}"

link_skill() {
  local skill_dir="$1" target_dir="$2"
  local name link
  name="$(basename "$skill_dir")"
  link="$target_dir/$name"

  if [ -L "$link" ]; then
    ln -sfn "$skill_dir" "$link"
    echo "updated  $link"
  elif [ -e "$link" ]; then
    echo "skipped  $link (a non-symlink already exists; move it aside first)" >&2
  else
    ln -s "$skill_dir" "$link"
    echo "linked   $link"
  fi
}

IFS=':' read -r -a targets <<< "$TARGET_DIRS"
for target_dir in "${targets[@]}"; do
  mkdir -p "$target_dir"
  for skill_path in "$REPO_DIR"/skills/*/; do
    [ -f "${skill_path}SKILL.md" ] || continue
    link_skill "${skill_path%/}" "$target_dir"
  done
done

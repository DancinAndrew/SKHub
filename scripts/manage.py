#!/usr/bin/env python3
"""Install the reviewed manifest; never copy skill bodies or overwrite user files."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
PLATFORMS = {"codex": ".agents/skills", "claude": ".claude/skills"}


class Conflict(ValueError):
    pass


def inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def read_manifest(root: Path) -> dict:
    data = json.loads((root / "manifest.json").read_text())
    if data.get("schema") != 1:
        raise Conflict("Unsupported manifest schema")
    seen = set()
    for item in data["skills"] + data.get("local_skills", []) + data.get("external_skills", []):
        name = item["name"]
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or name in seen:
            raise Conflict(f"Invalid or duplicate skill name: {name}")
        seen.add(name)
        if name in data["retired"]:
            raise Conflict(f"Retired skill cannot be installed: {name}")
        if not item["platforms"] or not set(item["platforms"]) <= PLATFORMS.keys():
            raise Conflict(f"Invalid platforms: {name}")
        if "source" in item:
            source = root / item["source"]
            if not inside(source, root) or Path(item["source"]).is_absolute():
                raise Conflict(f"Source escapes SKHub: {name}")
    actual = {p.name for p in (root / "skills").iterdir() if p.is_dir()}
    expected = {item["name"] for item in data["skills"]}
    if actual != expected:
        raise Conflict(f"Unregistered/missing public skill folders: {sorted(actual ^ expected)}")
    for name in data["retired"]:
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
            raise Conflict(f"Invalid retirement name: {name}")
    return data


def build_plan(root: Path, home: Path):
    data = read_manifest(root)
    links, generated, notices, removals = {}, {}, [], []
    for item in data["skills"] + data.get("local_skills", []):
        source = root / item["source"]
        entry = source / "SKILL.md"
        if not entry.is_file():
            if item in data.get("local_skills", []) and not source.exists():
                notices.append(f"Local-only skill not present on this machine: {item['name']}")
                continue
            raise Conflict(f"Missing SKILL.md: {source}")
        frontmatter = entry.read_text().split("---", 2)
        if len(frontmatter) != 3 or frontmatter[0].strip():
            raise Conflict(f"Invalid frontmatter: {entry}")
        name_match = re.search(r'^name:\s*[\"\']?([^\"\'\n]+)', frontmatter[1], re.M)
        if not name_match or name_match.group(1).strip() != item["name"]:
            raise Conflict(f"Name does not match manifest: {entry}")
        if not re.search(r"^description:\s*\S", frontmatter[1], re.M):
            raise Conflict(f"Missing description: {entry}")
        for platform in item["platforms"]:
            links[home / PLATFORMS[platform] / item["name"]] = source
    for item in data.get("external_skills", []):
        paths = [home / PLATFORMS[p] / item["name"] for p in item["platforms"]]
        sources = {p.resolve() for p in paths if p.is_symlink() and (p / "SKILL.md").is_file()}
        if len(sources) > 1:
            raise Conflict(f"External skill has divergent sources: {item['name']}")
        if sources:
            source = sources.pop()
            for path in paths:
                links[path] = source
        else:
            notices.append(f"External owner must install {item['name']}: {item['owner']}")
    common = (root / "profiles/common.md").read_text().rstrip()
    for platform, destination in [("codex", ".codex/AGENTS.md"), ("claude", ".claude/CLAUDE.md")]:
        supplement = root / "profiles" / (platform + ".md")
        body = common + ("\n\n" + supplement.read_text().strip() if supplement.exists() else "") + "\n"
        source = root / ".local/generated" / (platform + "-instructions.md")
        generated[source] = body
        links[home / destination] = source
    for source in sorted((root / "platforms/codex/agents").glob("*.toml")):
        links[home / ".codex/agents" / source.name] = source
    for base in [home / ".codex/skills", home / ".agents/skills", home / ".claude/skills"]:
        for name in data["retired"]:
            path = base / name
            if not (path.exists() or path.is_symlink()):
                continue
            if path.is_symlink() and inside(path, root):
                removals.append(path)
            else:
                raise Conflict(f"Retired unmanaged install remains; review migration ownership: {path}")
    for path in generated:
        if not inside(path, root):
            raise Conflict(f"Generated profile escapes SKHub: {path}")
    for path, source in links.items():
        if not inside(path.parent, home):
            raise Conflict(f"Destination parent escapes the requested home: {path}")
        if path.is_symlink():
            if path.resolve() != source.resolve() and not inside(path, root):
                raise Conflict(f"Unmanaged link conflict: {path}")
        elif path.exists():
            raise Conflict(f"Existing real file/directory requires one-time migration: {path}")
        temp = path.with_name(path.name + ".skhub-link-tmp")
        if temp.exists() or temp.is_symlink():
            raise Conflict(f"Temporary link path already exists: {temp}")
    return links, generated, removals, notices


def install(root: Path, home: Path, mode: str) -> dict:
    links, generated, removals, notices = build_plan(root, home)
    changes = []
    for path, body in generated.items():
        if not path.is_file() or path.read_text() != body:
            changes.append({"action": "render", "path": str(path)})
    for path, source in links.items():
        if not path.is_symlink() or path.resolve() != source.resolve():
            changes.append({"action": "link", "path": str(path), "source": str(source)})
    changes += [{"action": "remove-retired-link", "path": str(p)} for p in removals]
    if mode == "apply":
        for path, body in generated.items():
            if path.is_file() and path.read_text() == body:
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            temp = path.with_name(path.name + ".tmp")
            temp.write_text(body)
            os.replace(temp, path)
        for path in removals:
            path.unlink()
        for path, source in links.items():
            if path.is_symlink() and path.resolve() == source.resolve():
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            temp = path.with_name(path.name + ".skhub-link-tmp")
            if temp.exists() or temp.is_symlink():
                raise Conflict(f"Temporary link path already exists: {temp}")
            temp.symlink_to(source, target_is_directory=source.is_dir())
            os.replace(temp, path)
    return {"mode": mode, "links": len(links), "changes": changes, "notices": notices, "clean": not changes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--home", type=Path, default=Path.home(), help="Installation home; useful for isolated tests")
    args = parser.parse_args()
    try:
        result = install(ROOT, args.home.expanduser().absolute(), "check" if args.check else "dry-run" if args.dry_run else "apply")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if args.check and not result["clean"] else 0
    except (Conflict, OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"SKHub: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

"""Vault routing table (config/vaults.json) and collision-free output paths for a new note."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .common import MediaNoteError, read_json, safe_filename

_SKHUB_ROOT = Path(__file__).resolve().parents[4]
_LOCAL_CONFIG = _SKHUB_ROOT / ".local" / "config" / "media-note-vaults.json"
_DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config" / "vaults.json"
CONFIG = Path(os.environ.get("MEDIANOTE_VAULTS", _LOCAL_CONFIG if _LOCAL_CONFIG.is_file() else _DEFAULT_CONFIG))


def load() -> list[dict[str, Any]]:
    if not CONFIG.is_file():
        raise MediaNoteError(f"Vault config not found: {CONFIG}")
    vaults = read_json(CONFIG)["vaults"]
    return [{**v, "root": str(Path(v["root"]).expanduser())} for v in vaults]


def find_vault_root(path: Path) -> Path | None:
    for candidate in [path, *path.parents]:
        if (candidate / ".obsidian").is_dir():
            return candidate
    return None


def note_paths(vault_name: str, title: str, folder: str | None = None) -> dict[str, str]:
    vault = next((v for v in load() if v["name"].lower() == vault_name.lower()), None)
    if vault is None:
        raise MediaNoteError(f"Unknown vault {vault_name!r}; known: {[v['name'] for v in load()]}")
    root = Path(vault["root"])
    if not (root / ".obsidian").is_dir():
        raise MediaNoteError(f"{root} is not an Obsidian vault (no .obsidian folder)")
    name = safe_filename(title)
    relative = Path(folder if folder is not None else vault["notes_dir"])
    if relative.is_absolute() or ".." in relative.parts:
        raise MediaNoteError(f"--folder must be a path inside the vault, got {folder!r}")
    notes_dir = root / relative
    attachments_rel = Path(vault["attachments_dir"]) / name
    paths = {
        "vault_root": str(root),
        "note": str(notes_dir / f"{name}.md"),
        "attachments_dir": str(root / attachments_rel),
        "attachments_rel": attachments_rel.as_posix(),
        "rules": vault.get("rules", ""),
    }
    clashes = [paths["note"]] if Path(paths["note"]).exists() else []
    attachments = Path(paths["attachments_dir"])
    if attachments.is_dir() and any(attachments.iterdir()):
        clashes.append(str(attachments))
    if clashes:
        raise MediaNoteError("Output already exists (choose another title or folder): " + ", ".join(clashes))
    return paths

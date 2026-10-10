"""Shared helpers: cache paths, timestamps, subprocess calls, JSON I/O."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Sequence

CACHE_ROOT = Path(os.environ.get("MEDIANOTE_CACHE", Path.home() / ".cache" / "media-note"))
STDERR_TAIL_CHARS = 2000
HASH_CHUNK_BYTES = 8 << 20


class MediaNoteError(Exception):
    """Expected failure with a message the agent can relay to the user."""


@dataclass(frozen=True)
class Segment:
    start: float
    end: float
    text: str
    flags: tuple[str, ...] = field(default_factory=tuple)

    def with_text(self, text: str) -> "Segment":
        return replace(self, text=text)

    def with_flags(self, *flags: str) -> "Segment":
        merged = tuple(dict.fromkeys(self.flags + tuple(flags)))
        return replace(self, flags=merged)

    def shifted(self, offset: float) -> "Segment":
        return replace(self, start=self.start + offset, end=self.end + offset)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"start": round(self.start, 2), "end": round(self.end, 2), "text": self.text}
        if self.flags:
            data["flags"] = list(self.flags)
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Segment":
        return Segment(float(data["start"]), float(data["end"]), str(data["text"]), tuple(data.get("flags", ())))


def log(message: str) -> None:
    print(f"[media-note] {message}", file=sys.stderr, flush=True)


def emit(payload: dict[str, Any]) -> None:
    """Print the machine-readable result of a command (always the last stdout line)."""
    print(json.dumps(payload, ensure_ascii=False))


def fmt_ts(seconds: float, with_hours: bool = False) -> str:
    total = max(0, int(seconds))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    if hours or with_hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def parse_ts(value: str) -> float:
    parts = value.strip().split(":")
    if not 1 <= len(parts) <= 3 or not all(re.fullmatch(r"\d+(\.\d+)?", p) for p in parts):
        raise MediaNoteError(f"Invalid timestamp: {value!r} (expected SS, MM:SS or HH:MM:SS)")
    seconds = 0.0
    for part in parts:
        seconds = seconds * 60 + float(part)
    return seconds


def ts_slug(seconds: float) -> str:
    """Filename-safe timestamp such as 02m10s or 1h02m10s."""
    total = max(0, int(seconds))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}h{minutes:02d}m{secs:02d}s" if hours else f"{minutes:02d}m{secs:02d}s"


def require_tool(name: str, hint: str) -> str:
    path = shutil.which(name)
    if not path:
        raise MediaNoteError(f"`{name}` not found on PATH. {hint}")
    return path


def run(cmd: Sequence[str], timeout: float | None = None, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    try:
        proc = subprocess.run(list(cmd), capture_output=True, text=True, timeout=timeout, cwd=cwd, check=False)
    except FileNotFoundError as exc:
        raise MediaNoteError(f"Command not found: {cmd[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise MediaNoteError(f"Command timed out after {timeout}s: {' '.join(cmd[:4])} ...") from exc
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip()[-STDERR_TAIL_CHARS:]
        raise MediaNoteError(f"Command failed ({proc.returncode}): {' '.join(cmd[:6])} ...\n{tail}")
    return proc


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
    return path


def short_hash(*parts: str) -> str:
    digest = hashlib.sha1()
    for part in parts:
        digest.update(part.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()[:12]


def file_fingerprint(path: Path) -> str:
    """Full-content SHA-1 (a 1.6 GB recording hashes in a few seconds), so edited files never reuse stale caches."""
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        while chunk := handle.read(HASH_CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()[:12]


def work_dir(key: str) -> Path:
    path = CACHE_ROOT / key
    path.mkdir(parents=True, exist_ok=True)
    return path


def probe_duration(path: Path) -> float:
    require_tool("ffprobe", "Install with `brew install ffmpeg`.")
    proc = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)])
    try:
        return float(proc.stdout.strip())
    except ValueError as exc:
        raise MediaNoteError(f"Could not read duration of {path}") from exc


def has_cjk(text: str) -> bool:
    return re.search(r"[一-鿿]", text) is not None


INVALID_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|#^\[\]]+')


def safe_filename(name: str, max_len: int = 120) -> str:
    """Obsidian-safe file name: no path separators or wikilink-breaking characters."""
    cleaned = INVALID_FILENAME_CHARS.sub(" ", name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    return cleaned[:max_len].rstrip(" .") or "untitled"

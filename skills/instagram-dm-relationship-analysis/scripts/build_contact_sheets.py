#!/usr/bin/env python3
"""Create media contact sheets with ffmpeg when it is already available."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def run(command: list[str]) -> None:
    subprocess.run(
        command,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def collect(data: dict[str, Any]) -> list[dict[str, str]]:
    items = []
    for message in data["messages"]:
        for field, kind in (
            ("photos", "photo"),
            ("videos", "video"),
            ("audio_files", "audio"),
            ("gifs", "gif"),
        ):
            for attachment in message.get(field, []):
                items.append(
                    {
                        "kind": kind,
                        "basename": Path(attachment.get("uri", "")).name,
                        "message_id": message["message_id"],
                        "session_id": message["session_id"],
                        "datetime": message["datetime_local"],
                        "sender": message.get("sender_name", "unknown"),
                    }
                )
    return items


def find_media(root: Path, basename: str) -> Path:
    matches = [
        path
        for folder_name in ("photos", "videos", "audio", "gifs", "gif")
        for folder in root.rglob(folder_name)
        for path in [folder / basename]
        if path.exists()
    ]
    if not matches:
        raise FileNotFoundError(basename)
    hashes = set()
    for path in matches:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        hashes.add(digest.hexdigest())
    if len(hashes) != 1:
        raise RuntimeError(
            f"Ambiguous media basename with different content: {basename}: "
            + ", ".join(str(path) for path in matches)
        )
    return sorted(matches, key=lambda path: str(path))[-1]


def make_thumb(source: Path, target: Path, kind: str) -> None:
    common = (
        "scale=240:240:force_original_aspect_ratio=decrease,"
        "pad=240:240:(ow-iw)/2:(oh-ih)/2:white,format=rgb24"
    )
    if kind == "photo":
        run(["ffmpeg", "-y", "-i", str(source), "-vf", common, "-frames:v", "1", str(target)])
    elif kind in {"video", "gif"}:
        run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(source),
                "-vf",
                f"thumbnail,{common}",
                "-frames:v",
                "1",
                str(target),
            ]
        )
    else:
        run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(source),
                "-filter_complex",
                "showwavespic=s=240x240:colors=0x3366cc,format=rgba,"
                "pad=240:240:(ow-iw)/2:(oh-ih)/2:white,format=rgb24",
                "-frames:v",
                "1",
                str(target),
            ]
        )


def main() -> None:
    args = parse_args()
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg is not installed; do not install it without user approval")
    data = json.loads(args.dataset.read_text(encoding="utf-8"))
    items = collect(data)
    output = args.output.resolve()
    thumbs = output / "thumbs"
    thumbs.mkdir(parents=True, exist_ok=True)
    for index, item in enumerate(items, start=1):
        make_thumb(
            find_media(args.root.resolve(), item["basename"]),
            thumbs / f"thumb_{index:04d}.png",
            item["kind"],
        )
    per_page = 20
    for page in range(math.ceil(len(items) / per_page)):
        start = page * per_page
        end = min(start + per_page - 1, len(items) - 1)
        run(
            [
                "ffmpeg",
                "-y",
                "-framerate",
                "1",
                "-start_number",
                "1",
                "-i",
                str(thumbs / "thumb_%04d.png"),
                "-vf",
                f"select='between(n,{start},{end})',setpts=N/FRAME_RATE/TB,"
                "tile=5x4:padding=4:margin=4:color=white",
                "-frames:v",
                "1",
                str(output / f"contact_sheet_{page + 1:02d}.png"),
            ]
        )
    lines = [
        "# Contact-sheet mapping",
        "",
        "| ID | 類型 | Message | Session | 時間 | 發送者 | 檔案 |",
        "|---|---|---|---|---|---|---|",
    ]
    for index, item in enumerate(items, start=1):
        lines.append(
            f"| MED{index:04d} | {item['kind']} | {item['message_id']} | {item['session_id']} | {item['datetime']} | {item['sender']} | `{item['basename']}` |"
        )
    (output / "mapping.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"items": len(items), "pages": math.ceil(len(items) / per_page)}))


if __name__ == "__main__":
    main()

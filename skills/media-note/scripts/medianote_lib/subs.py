"""Subtitle parsers (YouTube json3 and WebVTT) into Segments."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .common import MediaNoteError, Segment

VTT_CUE = re.compile(r"(\d{1,2}:)?(\d{2}):(\d{2})[.,](\d{3})\s*-->\s*(\d{1,2}:)?(\d{2}):(\d{2})[.,](\d{3})")
VTT_TAG = re.compile(r"<[^>]+>")


def parse_json3(data: dict) -> list[Segment]:
    segments: list[Segment] = []
    for event in data.get("events", []):
        pieces = event.get("segs")
        if not pieces:
            continue
        text = "".join(piece.get("utf8", "") for piece in pieces).replace("\n", " ").strip()
        if not text:
            continue
        start = event.get("tStartMs", 0) / 1000
        end = start + event.get("dDurationMs", 0) / 1000
        segments.append(Segment(start, end, re.sub(r"\s+", " ", text)))
    return segments


def _vtt_seconds(hours: str | None, minutes: str, seconds: str, millis: str) -> float:
    return int((hours or "0:")[:-1]) * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / 1000


def parse_vtt(text: str) -> list[Segment]:
    segments: list[Segment] = []
    for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n")):
        lines = [line for line in block.strip().split("\n") if line.strip()]
        cue_index = next((i for i, line in enumerate(lines) if VTT_CUE.search(line)), None)
        if cue_index is None:
            continue
        match = VTT_CUE.search(lines[cue_index])
        assert match is not None
        start = _vtt_seconds(*match.group(1, 2, 3, 4))
        end = _vtt_seconds(*match.group(5, 6, 7, 8))
        body = " ".join(VTT_TAG.sub("", line).strip() for line in lines[cue_index + 1:])
        body = re.sub(r"\s+", " ", body).strip()
        if body and (not segments or segments[-1].text != body):
            segments.append(Segment(start, end, body))
    return segments


def parse_subtitle_file(path: Path) -> list[Segment]:
    if path.suffix == ".json3":
        return parse_json3(json.loads(path.read_text(encoding="utf-8")))
    if path.suffix == ".vtt":
        return parse_vtt(path.read_text(encoding="utf-8"))
    raise MediaNoteError(f"Unsupported subtitle format: {path.name}")

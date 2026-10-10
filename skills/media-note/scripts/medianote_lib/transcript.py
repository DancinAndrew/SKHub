"""Transcript persistence and the readable Markdown the agent writes notes from."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

from .common import Segment, fmt_ts, write_json, write_text

PARAGRAPH_MAX_S = 30.0
PARAGRAPH_GAP_S = 2.5
FLAG_MARK = "⚠ "
LOW_COVERAGE_CHARS_PER_MIN = 40
COVERAGE_BUCKET_S = 300


def group_paragraphs(segments: list[Segment], breaks: list[float]) -> list[list[Segment]]:
    """Group segments into ~30 s paragraphs, always breaking at chapter/part boundaries."""
    pending = sorted(breaks)
    paragraphs: list[list[Segment]] = []
    current: list[Segment] = []
    for seg in segments:
        crossed = bool(pending) and seg.start >= pending[0]
        while pending and seg.start >= pending[0]:
            pending.pop(0)
        if current and (crossed
                        or seg.start - current[0].start > PARAGRAPH_MAX_S
                        or seg.start - current[-1].end > PARAGRAPH_GAP_S):
            paragraphs.append(current)
            current = []
        current.append(seg)
    if current:
        paragraphs.append(current)
    return paragraphs


def _headings(meta: dict[str, Any]) -> list[tuple[float, str]]:
    headings = [(float(ch["start"]), f"章節：{ch['title']}") for ch in meta.get("chapters") or []]
    parts = meta.get("parts") or []
    if len(parts) > 1:
        headings += [(float(p["offset"]), f"第 {i + 1} 段錄音：{Path(p['file']).name}") for i, p in enumerate(parts)]
    return sorted(headings)


def render_markdown(meta: dict[str, Any], segments: list[Segment]) -> str:
    duration = float(meta.get("duration") or (segments[-1].end if segments else 0))
    hours = duration >= 3600
    lines = [
        "---",
        f'title: "{meta["title"]} 逐字稿"',
        f'source: "{meta["source"]}"',
        f'transcript_method: "{meta["method"]}"',
        f'script_conversion: "{meta.get("conversion", "none")}"',
        f"generated: {dt.date.today().isoformat()}",
        "---",
        "",
        f"# {meta['title']} 逐字稿",
        "",
    ]
    if meta["method"].startswith("asr:"):
        lines += [
            "> [!warning] 自動轉錄稿",
            "> 本機語音辨識產生，專有名詞、數字與標點可能有誤；開頭標 ⚠ 的句子可信度低（重複、亂碼或模型信心不足）。",
            "",
        ]
    headings = _headings(meta)
    paragraphs = group_paragraphs(segments, [start for start, _ in headings])
    for para in paragraphs:
        while headings and para[0].start >= headings[0][0]:
            start, title = headings.pop(0)
            lines += [f"## [{fmt_ts(start, hours)}] {title}", ""]
        body = " ".join((FLAG_MARK if seg.flags else "") + seg.text for seg in para)
        lines += [f"**[{fmt_ts(para[0].start, hours)}]** {body}", ""]
    return "\n".join(lines)


def quality_report(segments: list[Segment], duration: float) -> dict[str, Any]:
    flagged = [seg for seg in segments if seg.flags]
    buckets: dict[int, int] = {}
    for seg in segments:
        bucket = int(seg.start // COVERAGE_BUCKET_S)
        buckets[bucket] = buckets.get(bucket, 0) + len(seg.text)
    low = []
    for bucket in range(int(duration // COVERAGE_BUCKET_S) + 1):
        start = bucket * COVERAGE_BUCKET_S
        span = min(COVERAGE_BUCKET_S, max(duration - start, 1))
        if span >= 60 and buckets.get(bucket, 0) / (span / 60) < LOW_COVERAGE_CHARS_PER_MIN:
            low.append(f"{fmt_ts(start)}–{fmt_ts(start + span)}")
    return {
        "segments": len(segments),
        "flagged_segments": len(flagged),
        "flagged_ratio": round(len(flagged) / len(segments), 3) if segments else 0.0,
        "low_text_windows": low,
    }


def save(work: Path, meta: dict[str, Any], segments: list[Segment]) -> dict[str, Any]:
    duration = float(meta.get("duration") or (segments[-1].end if segments else 0))
    report = quality_report(segments, duration)
    write_json(work / "transcript.json", {**meta, "quality": report, "segments": [s.to_dict() for s in segments]})
    md_path = write_text(work / "transcript.md", render_markdown(meta, segments))
    return {"transcript_md": str(md_path), "transcript_json": str(work / "transcript.json"), "quality": report}

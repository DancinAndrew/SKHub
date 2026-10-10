"""Transcript cleanup: Simplified→Traditional conversion and ASR hallucination flags."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any, Iterable

from .common import Segment

# Phrases Whisper invents from its subtitle-heavy training data; never real speech in our sources.
KNOWN_HALLUCINATIONS = (
    "請不吝點贊", "请不吝点赞", "訂閱轉發打賞", "订阅转发打赏", "明鏡與點點", "明镜与点点",
    "字幕由Amara", "字幕由 Amara", "Amara.org", "優優獨播劇場", "优优独播剧场",
    "字幕志願者", "字幕志愿者", "中文字幕由", "索兰娅", "詞曲 李宗盛", "词曲 李宗盛",
)
UNEXPECTED_SCRIPTS = {
    "zh": re.compile(r"[Ѐ-ӿ֐-ۿ฀-๿가-힯぀-ヿÀ-ÿ]"),
    "en": re.compile(r"[Ѐ-ӿ֐-ۿ฀-๿가-힯぀-ヿ一-鿿]"),
}
REPEAT_RUN = re.compile(r"(.{2,12}?)(?:[\s,，、。.]*\1){2,}")
LOW_LOGPROB = -1.0
HIGH_COMPRESSION = 2.4
HIGH_NO_SPEECH = 0.6
SIMPLIFIED_RATIO_THRESHOLD = 0.01
MAX_CONSECUTIVE_DUPLICATES = 2


@lru_cache(maxsize=4)
def _converter(config: str) -> Any:
    from opencc import OpenCC  # lazy: only needed for Chinese text

    return OpenCC(config)


def simplified_ratio(text: str) -> float:
    """Share of CJK characters that change under Simplified→Traditional conversion."""
    cjk = "".join(ch for ch in text if "一" <= ch <= "鿿")
    if not cjk:
        return 0.0
    converted = _converter("s2t").convert(cjk)
    changed = sum(1 for before, after in zip(cjk, converted) if before != after)
    return changed / len(cjk)


def to_taiwan_traditional(text: str) -> str:
    return _converter("s2twp").convert(text)


def convert_segments(segments: list[Segment], mode: str = "auto") -> tuple[list[Segment], str]:
    """Convert to Taiwan Traditional Chinese. mode: auto | always | never."""
    if mode == "never" or not segments:
        return segments, "none"
    joined = "".join(seg.text for seg in segments)
    if mode == "auto" and simplified_ratio(joined) <= SIMPLIFIED_RATIO_THRESHOLD:
        return segments, "none"
    return [seg.with_text(to_taiwan_traditional(seg.text)) for seg in segments], "opencc:s2twp"


def collapse_repeats(text: str) -> tuple[str, bool]:
    collapsed = REPEAT_RUN.sub(r"\1", text)
    return collapsed, collapsed != text


def is_known_hallucination(text: str) -> bool:
    return any(phrase in text for phrase in KNOWN_HALLUCINATIONS)


def _normalized(text: str) -> str:
    return re.sub(r"[\s,，、。.!?！？]+", "", text).lower()


def clean_asr_segments(raw_segments: Iterable[dict[str, Any]], default_language: str = "zh") -> tuple[list[Segment], dict[str, int]]:
    """Turn raw Whisper segments into flagged Segments; drop invented credits and runaway duplicates."""
    stats = {"dropped_hallucination": 0, "dropped_duplicate": 0, "repeat": 0, "garbled": 0, "low-confidence": 0}
    cleaned: list[Segment] = []
    duplicate_run = 0
    for raw in raw_segments:
        unexpected = UNEXPECTED_SCRIPTS.get(str(raw.get("language", default_language)))
        text = str(raw.get("text", "")).strip()
        if not text:
            continue
        if is_known_hallucination(text):
            stats["dropped_hallucination"] += 1
            continue
        flags: list[str] = []
        text, repeated = collapse_repeats(text)
        if repeated:
            flags.append("repeat")
        if unexpected and unexpected.search(text):
            flags.append("garbled")
        if (float(raw.get("avg_logprob", 0.0)) < LOW_LOGPROB
                or float(raw.get("compression_ratio", 0.0)) > HIGH_COMPRESSION
                or float(raw.get("no_speech_prob", 0.0)) > HIGH_NO_SPEECH):
            flags.append("low-confidence")
        if cleaned and _normalized(cleaned[-1].text) == _normalized(text):
            duplicate_run += 1
            if duplicate_run >= MAX_CONSECUTIVE_DUPLICATES:
                stats["dropped_duplicate"] += 1
                continue
            flags.append("repeat")
        else:
            duplicate_run = 0
        for flag in flags:
            stats[flag] += 1
        cleaned.append(Segment(float(raw["start"]), float(raw["end"]), text, tuple(dict.fromkeys(flags))))
    return cleaned, stats

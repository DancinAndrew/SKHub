"""Local speech-to-text with mlx-whisper, detecting the spoken language per 30 s window."""

from __future__ import annotations

import importlib
import os
import time
from collections import Counter
from pathlib import Path
from typing import Any

from .common import MediaNoteError, file_fingerprint, fmt_ts, log, probe_duration, read_json, require_tool, run, short_hash, write_json

DEFAULT_MODEL = os.environ.get("MEDIANOTE_ASR_MODEL", "mlx-community/whisper-large-v3-turbo")
WINDOW_S = 30
SAMPLE_RATE = 16000
MIN_RUN_WINDOWS = 3          # language flips shorter than 90 s are treated as noise
MIN_LANGUAGE_SHARE = 0.10    # languages below this share of windows are ignored
DOMINANT_SHARE = 0.90        # above this, transcribe the whole file in one language
REALTIME_FACTOR_ESTIMATE = 20.0  # measured 21-28x on Apple M5 with large-v3-turbo (zh podcast, en lecture)
PROMPT_MAX_CHARS = 200
DECODE_OPTIONS: dict[str, Any] = {
    "task": "transcribe",
    "condition_on_previous_text": False,   # stops one hallucination from seeding the next window
    "temperature": (0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
    "compression_ratio_threshold": 2.2,
    "logprob_threshold": -1.0,
    "no_speech_threshold": 0.6,
    "verbose": None,
}
KEEP_FIELDS = ("start", "end", "text", "avg_logprob", "compression_ratio", "no_speech_prob")
METAL_HINT = (
    "mlx-whisper cannot reach the Apple GPU (Metal). This happens inside sandboxes such as Codex's seatbelt "
    "and in headless/remote sessions. Re-run this command outside the sandbox (escalated permissions)."
)


def require_mlx() -> None:
    """Fail fast with an actionable message when the GPU runtime is unavailable."""
    try:
        importlib.import_module("mlx.core")
    except (ImportError, RuntimeError) as exc:
        if "metal" in str(exc).lower():
            raise MediaNoteError(METAL_HINT) from exc
        raise MediaNoteError(f"mlx-whisper is not usable here: {exc}") from exc


def build_prompt(language: str, title: str, terms: list[str]) -> str:
    joined = ("、" if language == "zh" else ", ").join(terms)
    if language == "zh":
        prompt = f"以下是「{title}」的繁體中文逐字稿，可能提到：{joined}。" if terms else f"以下是「{title}」的繁體中文逐字稿。"
    else:
        prompt = f'Transcript of "{title}". Terms: {joined}.' if terms else f'Transcript of "{title}".'
    return prompt[:PROMPT_MAX_CHARS]


def language_runs(labels: list[str]) -> list[tuple[str, int, int]]:
    """Smooth per-window language labels into runs of (language, first_window, end_window_exclusive)."""
    if not labels:
        return []
    counts = Counter(labels)
    dominant, dominant_count = counts.most_common(1)[0]
    if dominant_count / len(labels) >= DOMINANT_SHARE:
        return [(dominant, 0, len(labels))]
    allowed = {lang for lang, n in counts.items() if n / len(labels) >= MIN_LANGUAGE_SHARE} or {dominant}
    smoothed: list[str] = []
    for label in labels:
        smoothed.append(label if label in allowed else (smoothed[-1] if smoothed else dominant))
    runs: list[list[Any]] = []
    for index, label in enumerate(smoothed):
        if runs and runs[-1][0] == label:
            runs[-1][2] = index + 1
        else:
            runs.append([label, index, index + 1])
    merged: list[list[Any]] = []
    for run_ in runs:
        if merged and (run_[2] - run_[1] < MIN_RUN_WINDOWS or merged[-1][0] == run_[0]):
            merged[-1][2] = run_[2]
        else:
            merged.append(run_)
    if len(merged) > 1 and merged[0][2] - merged[0][1] < MIN_RUN_WINDOWS:
        merged[1][1] = merged[0][1]
        merged.pop(0)
    return [(str(lang), int(start), int(end)) for lang, start, end in merged]


def to_wav16k(src: Path, dest: Path, max_seconds: float | None) -> Path:
    require_tool("ffmpeg", "Install with `brew install ffmpeg`.")
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE)]
    if max_seconds:
        cmd += ["-t", str(max_seconds)]
    run(cmd + ["-c:a", "pcm_s16le", str(dest)], timeout=3600)
    return dest


def _load_model(model_name: str) -> Any:
    import mlx.core as mx
    from mlx_whisper.transcribe import ModelHolder

    return ModelHolder.get_model(model_name, mx.float16)


def detect_window_languages(wav: Path, model_name: str) -> list[str]:
    import mlx.core as mx
    from mlx_whisper.audio import N_FRAMES, load_audio, log_mel_spectrogram, pad_or_trim

    model = _load_model(model_name)
    mel = log_mel_spectrogram(load_audio(str(wav)), n_mels=model.dims.n_mels)
    frames_per_s = 100
    total_windows = max(1, int(mel.shape[0] / frames_per_s // WINDOW_S))
    labels = []
    for window in range(total_windows):
        start = window * WINDOW_S * frames_per_s
        chunk = pad_or_trim(mel[start:start + N_FRAMES], N_FRAMES, axis=-2).astype(mx.float16)
        _, probs = model.detect_language(chunk)
        probs = probs[0] if isinstance(probs, list) else probs
        labels.append(max(probs, key=probs.get))
    return labels


def _transcribe_run(wav: Path, work: Path, language: str, start_s: float, end_s: float | None,
                    model_name: str, prompt: str) -> list[dict[str, Any]]:
    import mlx_whisper

    clip = wav
    if start_s > 0 or end_s is not None:
        clip = work / f"{wav.stem}-{int(start_s)}.wav"
        cmd = ["ffmpeg", "-v", "error", "-y", "-ss", str(start_s), "-i", str(wav)]
        cmd += ["-t", str(end_s - start_s)] if end_s is not None else []
        run(cmd + ["-c:a", "pcm_s16le", str(clip)], timeout=3600)
    result = mlx_whisper.transcribe(str(clip), path_or_hf_repo=model_name, language=language,
                                    initial_prompt=prompt, **DECODE_OPTIONS)
    if clip != wav:
        clip.unlink(missing_ok=True)
    segments = [{k: seg[k] for k in KEEP_FIELDS if k in seg} for seg in result.get("segments", [])]
    for seg in segments:
        seg["start"] += start_s
        seg["end"] += start_s
        seg["language"] = language
    return segments


def transcribe_file(src: Path, work: Path, *, model_name: str, language: str | None, title: str,
                    terms: list[str], max_seconds: float | None) -> dict[str, Any]:
    """Transcribe one media file (cached by content, model, language and prompt inputs)."""
    fingerprint = file_fingerprint(src)
    key = short_hash(fingerprint, model_name, language or "auto", title, "|".join(terms), str(max_seconds))
    cache = work / "asr" / f"{fingerprint}-{key}.json"
    if cache.exists():
        log(f"ASR cache hit: {src.name}")
        return read_json(cache)
    require_mlx()
    wav = to_wav16k(src, work / "asr" / f"{fingerprint}.wav", max_seconds)
    duration = probe_duration(wav)
    log(f"ASR {src.name}: {fmt_ts(duration)} audio, expect ~{max(1, round(duration / REALTIME_FACTOR_ESTIMATE / 60))} min")
    started = time.monotonic()
    if language:
        runs = [(language, 0.0, None)]
    else:
        labels = detect_window_languages(wav, model_name)
        runs = [(lang, a * WINDOW_S, None if b == len(labels) else b * WINDOW_S) for lang, a, b in language_runs(labels)]
        log("language runs: " + ", ".join(f"{lang}@{fmt_ts(a)}" for lang, a, _ in runs))
    segments: list[dict[str, Any]] = []
    for lang, start_s, end_s in runs:
        segments += _transcribe_run(wav, work / "asr", lang, float(start_s), end_s, model_name,
                                    build_prompt(lang, title, terms))
    elapsed = time.monotonic() - started
    wav.unlink(missing_ok=True)
    log(f"ASR done in {elapsed / 60:.1f} min ({duration / max(elapsed, 1):.1f}x realtime)")
    if not segments:
        raise MediaNoteError(f"ASR produced no text for {src.name}; check that the audio is not silent.")
    result = {"file": str(src), "duration": duration, "model": model_name, "elapsed_s": round(elapsed, 1),
              "language_runs": [{"language": lang, "start": start_s, "end": end_s} for lang, start_s, end_s in runs],
              "segments": segments}
    return read_json(write_json(cache, result))

"""YouTube metadata, subtitles and media downloads via the latest yt-dlp (run through uvx)."""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
from pathlib import Path
from typing import Any

from .common import MediaNoteError, has_cjk, log, read_json, run, write_json

YTDLP_SPEC = os.environ.get("MEDIANOTE_YTDLP_SPEC", "yt-dlp[default,curl-cffi]@latest")
EXTRA_ARGS = shlex.split(os.environ.get("MEDIANOTE_YTDLP_ARGS", ""))
YOUTUBE_ID = re.compile(r"(?:[?&]v=|youtu\.be/|/shorts/|/live/|/embed/)([A-Za-z0-9_-]{11})")
ZH_LANGS = ("zh-TW", "zh-Hant", "zh-HK", "zh", "zh-Hans", "zh-CN", "zh-SG")
EN_LANGS = ("en", "en-US", "en-GB", "en-CA", "en-AU")
INFO_TIMEOUT_S = 180
SUBS_TIMEOUT_S = 300
DOWNLOAD_TIMEOUT_S = 3 * 3600
DESCRIPTION_CHARS = 1500
BOT_CHECK_HINT = (
    "YouTube asked to sign in to confirm you're not a bot. Wait and retry later; with the user's explicit "
    "consent you may set MEDIANOTE_YTDLP_ARGS='--cookies-from-browser chrome' (reads their browser cookies)."
)


def is_youtube(url: str) -> bool:
    return bool(re.match(r"https?://(www\.|m\.|music\.)?(youtube\.com|youtu\.be)/", url)) and bool(YOUTUBE_ID.search(url))


def video_id(url: str) -> str:
    match = YOUTUBE_ID.search(url)
    if not match:
        raise MediaNoteError(f"Not a YouTube video URL: {url}")
    return match.group(1)


def _ytdlp(args: list[str], timeout: float) -> str:
    cmd = ["uvx", "--from", YTDLP_SPEC, "yt-dlp", "--no-playlist", *EXTRA_ARGS]
    runtime = next((name for name in ("node", "deno", "bun") if shutil.which(name)), None)
    if runtime:
        cmd += ["--js-runtimes", runtime]
    else:
        log("WARNING: no node/deno/bun on PATH; YouTube may hide formats and subtitles.")
    try:
        return run(cmd + args, timeout=timeout).stdout
    except MediaNoteError as exc:
        if "confirm you" in str(exc) and "bot" in str(exc):
            raise MediaNoteError(BOT_CHECK_HINT) from exc
        raise


def summarize_info(info: dict[str, Any]) -> dict[str, Any]:
    upload = info.get("upload_date") or ""
    auto = info.get("automatic_captions") or {}
    return {
        "id": info.get("id"),
        "title": info.get("title"),
        "channel": info.get("channel") or info.get("uploader"),
        "upload_date": f"{upload[:4]}-{upload[4:6]}-{upload[6:]}" if len(upload) == 8 else None,
        "duration": info.get("duration"),
        "live_status": info.get("live_status"),
        "webpage_url": info.get("webpage_url") or f"https://www.youtube.com/watch?v={info.get('id')}",
        "description": (info.get("description") or "")[:DESCRIPTION_CHARS],
        "chapters": [
            {"start": ch.get("start_time", 0), "end": ch.get("end_time"), "title": ch.get("title", "")}
            for ch in info.get("chapters") or []
        ],
        "subtitles": sorted(k for k in (info.get("subtitles") or {}) if k != "live_chat"),
        "auto_captions": sorted(k for k in auto if k in ZH_LANGS + EN_LANGS or k.endswith("-orig")),
    }


def fetch_info(url: str, work: Path) -> dict[str, Any]:
    cached = work / "info.json"
    if cached.exists():
        return read_json(cached)
    info = json.loads(_ytdlp(["--dump-single-json", "--skip-download", url], INFO_TIMEOUT_S))
    return read_json(write_json(cached, summarize_info(info)))


def choose_subtitle_lang(available: list[str], title: str) -> str | None:
    """Pick an uploaded subtitle track in the video's own language family; None means use ASR."""
    family = ZH_LANGS if has_cjk(title) else EN_LANGS
    return next((lang for lang in family if lang in available), None)


def fetch_subtitles(url: str, lang: str, work: Path) -> Path:
    subs_dir = work / "subs"
    existing = sorted(subs_dir.glob(f"*.{lang}.json3")) + sorted(subs_dir.glob(f"*.{lang}.vtt"))
    if existing:
        return existing[0]
    _ytdlp(["--skip-download", "--write-subs", "--no-write-auto-subs", "--sub-langs", lang,
            "--sub-format", "json3/vtt", "-o", str(subs_dir / "%(id)s.%(ext)s"), url], SUBS_TIMEOUT_S)
    found = sorted(subs_dir.glob(f"*.{lang}.json3")) + sorted(subs_dir.glob(f"*.{lang}.vtt"))
    if not found:
        raise MediaNoteError(f"yt-dlp reported success but no {lang} subtitle file was written.")
    return found[0]


def _download(url: str, fmt: str, out_dir: Path, stem: str) -> Path:
    def finished() -> list[Path]:
        return [p for p in sorted(out_dir.glob(f"*.{stem}.*")) if not p.name.endswith((".part", ".ytdl"))]

    if finished():
        return finished()[0]
    args = ["-f", fmt, "-N", "4", "--no-progress", "-o", str(out_dir / f"%(id)s.{stem}.%(ext)s"), url]
    try:
        _ytdlp(["--impersonate", "chrome", *args], DOWNLOAD_TIMEOUT_S)
    except MediaNoteError as exc:
        if "impersonat" not in str(exc).lower():
            raise
        log("Impersonation unavailable; retrying plain download.")
        _ytdlp(args, DOWNLOAD_TIMEOUT_S)
    if not finished():
        raise MediaNoteError(f"Download finished without a {stem} file in {out_dir}")
    return finished()[0]


def download_audio(url: str, work: Path) -> Path:
    return _download(url, "ba[ext=m4a]/ba", work / "audio", "audio")


def download_video(url: str, work: Path, max_height: int) -> Path:
    fmt = f"bv*[height<={max_height}][vcodec^=avc1]/bv*[height<={max_height}]/b[height<={max_height}]"
    return _download(url, fmt, work / "video", f"video{max_height}")

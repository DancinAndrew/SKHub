"""Command implementations; each returns the JSON payload printed by the CLI."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from . import align, asr, checknote, frames, pdfpages, podcast, subs, textclean, transcript, vaults, youtube
from .common import (MediaNoteError, Segment, file_fingerprint, fmt_ts, probe_duration, read_json, short_hash, work_dir,
                     write_json, write_text)

ASR_MINUTES_PER_HOUR = 60 / asr.REALTIME_FACTOR_ESTIMATE


def _local_paths(sources: list[str]) -> list[Path]:
    paths = [Path(s).expanduser().resolve() for s in sources]
    missing = [str(p) for p in paths if not p.is_file()]
    if missing:
        raise MediaNoteError(f"File(s) not found: {missing}")
    return paths


def _kind(sources: list[str]) -> str:
    if len(sources) == 1 and youtube.is_youtube(sources[0]):
        return "youtube"
    if len(sources) == 1 and sources[0].startswith(("http://", "https://")):
        return "podcast"
    return "local"


def _episode(args: argparse.Namespace) -> podcast.Episode:
    return podcast.resolve(args.sources[0], title=args.episode_title, guid=args.episode_guid, index=args.episode_index)


def _asr_estimate(seconds: float) -> str:
    return f"~{max(1, round(seconds / 3600 * ASR_MINUTES_PER_HOUR))} min"


def probe(args: argparse.Namespace) -> dict[str, Any]:
    kind = _kind(args.sources)
    if kind == "youtube":
        url = args.sources[0]
        work = work_dir(f"yt-{youtube.video_id(url)}")
        info = youtube.fetch_info(url, work)
        lang = youtube.choose_subtitle_lang(info["subtitles"], info["title"] or "")
        plan = f"youtube-subs:{lang}" if lang else "asr"
        return {"kind": kind, "work_dir": str(work), **{k: v for k, v in info.items() if k != "description"},
                "description_head": info["description"][:300], "transcript_plan": plan,
                "asr_estimate": None if lang else _asr_estimate(info["duration"] or 0)}
    if kind == "podcast":
        episode = _episode(args)
        return {"kind": kind, **episode.__dict__, "transcript_plan": "asr"}
    paths = _local_paths(args.sources)
    durations = [probe_duration(p) for p in paths]
    return {"kind": kind, "files": [{"file": str(p), "duration": fmt_ts(d, True)} for p, d in zip(paths, durations)],
            "total_duration": fmt_ts(sum(durations), True), "transcript_plan": "asr",
            "asr_estimate": _asr_estimate(sum(durations))}


def _terms(args: argparse.Namespace) -> list[str]:
    terms = [t.strip() for t in (args.terms or "").split(",") if t.strip()]
    for index, pdf in enumerate(args.terms_from or []):
        terms += pdfpages.key_terms(pdfpages.extract(Path(pdf).expanduser().resolve(), f"D{index + 1}")["pages"])
    return list(dict.fromkeys(terms))


def _run_asr(files: list[Path], work: Path, args: argparse.Namespace, title: str,
             context_terms: tuple[str | None, ...] = ()) -> tuple[list[Segment], dict[str, Any]]:
    segments: list[Segment] = []
    parts, stats_total = [], {}
    offset = 0.0
    terms = list(dict.fromkeys([t for t in context_terms if t] + _terms(args)))
    for path in files:
        result = asr.transcribe_file(path, work, model_name=args.model, language=args.language, title=title,
                                     terms=terms, max_seconds=args.max_seconds)
        cleaned, stats = textclean.clean_asr_segments(result["segments"])
        segments += [seg.shifted(offset) for seg in cleaned]
        parts.append({"file": str(path), "offset": round(offset, 2), "duration": round(result["duration"], 2),
                      "language_runs": result["language_runs"], "elapsed_s": result["elapsed_s"]})
        stats_total = {k: stats_total.get(k, 0) + v for k, v in stats.items()}
        offset += result["duration"]
    return segments, {"parts": parts, "asr_stats": stats_total, "method": f"asr:{args.model}", "duration": round(offset, 2),
                      "prompt_terms": terms}


def transcribe(args: argparse.Namespace) -> dict[str, Any]:
    kind = _kind(args.sources)
    meta: dict[str, Any]
    if kind == "youtube":
        url = args.sources[0]
        work = work_dir(f"yt-{youtube.video_id(url)}")
        info = youtube.fetch_info(url, work)
        title = args.title or info["title"]
        lang = None if args.force_asr else youtube.choose_subtitle_lang(info["subtitles"], info["title"] or "")
        base = {"title": title, "source": info["webpage_url"], "channel": info["channel"],
                "upload_date": info["upload_date"], "chapters": info["chapters"]}
        if lang:
            segments = subs.parse_subtitle_file(youtube.fetch_subtitles(url, lang, work))
            if args.max_seconds:
                segments = [s for s in segments if s.start < args.max_seconds]
            meta = {**base, "method": f"youtube-subs:{lang}", "duration": info["duration"]}
        else:
            segments, asr_meta = _run_asr([youtube.download_audio(url, work)], work, args, title, (info["channel"],))
            meta = {**base, **asr_meta}
    elif kind == "podcast":
        episode = _episode(args)
        work, audio = podcast.download(episode)
        title = args.title or episode.title
        segments, asr_meta = _run_asr([audio], work, args, title, (episode.show, episode.author))
        meta = {"title": title, "source": episode.page_url or episode.audio_url, "channel": episode.show,
                "upload_date": episode.published, "chapters": [], **asr_meta}
    else:
        files = _local_paths(args.sources)
        work = work_dir("local-" + short_hash(*[file_fingerprint(p) for p in files]))
        title = args.title or files[0].stem
        segments, asr_meta = _run_asr(files, work, args, title)
        meta = {"title": title, "source": " + ".join(str(p) for p in files), "chapters": [], **asr_meta}
    if not segments:
        raise MediaNoteError("Transcript is empty.")
    segments, conversion = textclean.convert_segments(segments, args.convert)
    meta["conversion"] = conversion
    saved = transcript.save(work, meta, segments)
    return {"kind": kind, "work_dir": str(work), "title": meta["title"], "method": meta["method"],
            "duration": fmt_ts(float(meta.get("duration") or segments[-1].end), True), "conversion": conversion,
            "chapters": len(meta.get("chapters") or []), "parts": meta.get("parts"), "asr_stats": meta.get("asr_stats"),
            **saved}


def frames_cmd(args: argparse.Namespace) -> dict[str, Any]:
    source = args.source
    if youtube.is_youtube(source):
        work = work_dir(f"yt-{youtube.video_id(source)}")
        video = youtube.download_video(source, work, args.max_height)
    else:
        video = _local_paths([source])[0]
        work = work_dir("local-" + short_hash(file_fingerprint(video)))
    result = frames.build_candidates(video, work)
    return {"work_dir": str(work), "candidates": len(result["candidates"]), "sheets": result["sheets"],
            "recurring_count": result["recurring_count"], "recurring_sheets": result["recurring_sheets"],
            "candidates_json": str(work / "frames" / "candidates.json")}


def _embed(path: str) -> str | None:
    root = vaults.find_vault_root(Path(path).resolve().parent)
    return f"![[{Path(path).resolve().relative_to(root).as_posix()}]]" if root else None


def _ints(value: str) -> list[int]:
    try:
        return [int(v) for v in value.replace(" ", "").split(",") if v]
    except ValueError as exc:
        raise MediaNoteError(f"Expected comma-separated integers, got {value!r}") from exc


def export_frames(args: argparse.Namespace) -> dict[str, Any]:
    exported = frames.export_frames(Path(args.work), _ints(args.pick), Path(args.dest).expanduser(), args.start_number)
    return {"exported": [{**item, "embed": _embed(item["file"])} for item in exported]}


def pdf_cmd(args: argparse.Namespace) -> dict[str, Any]:
    decks = []
    for index, pdf in enumerate(args.pdfs):
        data = pdfpages.extract(Path(pdf).expanduser().resolve(), f"D{index + 1}")
        decks.append({"label": data["label"], "pdf": data["pdf"], "page_count": data["page_count"], "sheets": data["sheets"],
                      "low_text_pages": data["low_text_pages"], "pages_json": str(Path(data["work_dir"]) / "pages.json"),
                      "key_terms": pdfpages.key_terms(data["pages"])})
    return {"decks": decks}


def align_cmd(args: argparse.Namespace) -> dict[str, Any]:
    work = Path(args.work)
    data = read_json(work / "transcript.json")
    segments = [Segment.from_dict(s) for s in data["segments"]]
    pages: list[align.Page] = []
    for index, pdf in enumerate(args.pdfs):
        deck = pdfpages.extract(Path(pdf).expanduser().resolve(), f"D{index + 1}")
        pages += [align.Page(deck["label"], p["page"], p["title"], p["text"]) for p in deck["pages"]]
    result = align.align(segments, pages)
    out_dir = work / "align"
    write_json(out_dir / "alignment.json", result)
    md = write_text(out_dir / "alignment.md", align.render_markdown(result, pages))
    return {"alignment_md": str(md), "spans": len(result["spans"]), "unmatched_pages": len(result["unmatched_pages"]),
            "decks": {f"D{i + 1}": str(Path(p).expanduser().resolve()) for i, p in enumerate(args.pdfs)}}


def export_pages(args: argparse.Namespace) -> dict[str, Any]:
    exported = pdfpages.export_pages(Path(args.pdf).expanduser().resolve(), _ints(args.pages), Path(args.dest).expanduser(), args.format)
    return {"exported": [{**item, "embed": _embed(item["file"])} for item in exported]}


def vaults_cmd(_: argparse.Namespace) -> dict[str, Any]:
    return {"config": str(vaults.CONFIG), "vaults": vaults.load()}


def paths_cmd(args: argparse.Namespace) -> dict[str, Any]:
    return vaults.note_paths(args.vault, args.title, args.folder)


def check_cmd(args: argparse.Namespace) -> dict[str, Any]:
    return checknote.check(Path(args.note).expanduser().resolve(),
                           Path(args.coverage).expanduser().resolve() if getattr(args, "coverage", None) else None)

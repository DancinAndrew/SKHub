#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = [
#   "mlx-whisper>=0.4",
#   "numpy",
#   "pillow",
#   "opencc-python-reimplemented",
# ]
# ///
"""media-note driver: turn YouTube videos, podcasts and lecture recordings into note-ready material.

Run with: uv run ~/.agents/skills/media-note/scripts/medianote.py <command> ...
Every command prints one JSON object on stdout; progress goes to stderr.
"""

from __future__ import annotations

import argparse
import sys

from medianote_lib import asr, commands
from medianote_lib.common import MediaNoteError, emit


def _add_asr_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--force-asr", action="store_true", help="ignore uploaded subtitles and transcribe locally")
    parser.add_argument("--language", choices=["zh", "en", "ja"], help="skip per-window language detection")
    parser.add_argument("--model", default=asr.DEFAULT_MODEL)
    parser.add_argument("--title", help="override title used in prompts and output")
    parser.add_argument("--terms", help="comma-separated names/jargon to prime recognition")
    parser.add_argument("--terms-from", nargs="+", metavar="PDF", help="pull key terms from slide PDFs")
    parser.add_argument("--max-seconds", type=float, help="smoke test: only the first N seconds")
    parser.add_argument("--convert", choices=["auto", "always", "never"], default="auto",
                        help="Simplified→Taiwan Traditional conversion (auto = only when Simplified is detected)")


def _add_episode_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--episode-title", help="RSS: episode title (substring)")
    parser.add_argument("--episode-guid", help="RSS: guid or id substring")
    parser.add_argument("--episode-index", type=int, help="RSS: 1-based item index (1 = newest)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="medianote", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("probe", help="metadata + transcript plan for a URL or local files")
    p.add_argument("sources", nargs="+")
    _add_episode_options(p)
    p.set_defaults(func=commands.probe)

    p = sub.add_parser("transcript", help="subtitles or local ASR → transcript.md/json")
    p.add_argument("sources", nargs="+", help="YouTube URL, podcast URL, or local audio/video files in play order")
    _add_asr_options(p)
    _add_episode_options(p)
    p.set_defaults(func=commands.transcribe)

    p = sub.add_parser("frames", help="candidate still frames + contact sheets")
    p.add_argument("source", help="YouTube URL or local video file")
    p.add_argument("--max-height", type=int, default=720)
    p.set_defaults(func=commands.frames_cmd)

    p = sub.add_parser("export-frames", help="save chosen candidates as JPEGs")
    p.add_argument("--work", required=True)
    p.add_argument("--pick", required=True, help="candidate ids in note order, e.g. 3,17,42")
    p.add_argument("--dest", required=True)
    p.add_argument("--start-number", type=int, default=1)
    p.set_defaults(func=commands.export_frames)

    p = sub.add_parser("pdf", help="per-page text, key terms and contact sheets for slide decks")
    p.add_argument("pdfs", nargs="+")
    p.set_defaults(func=commands.pdf_cmd)

    p = sub.add_parser("align", help="candidate transcript-window → slide-page mapping")
    p.add_argument("--work", required=True, help="work_dir printed by `transcript`")
    p.add_argument("--pdf", dest="pdfs", nargs="+", required=True, help="same deck order as the lecture")
    p.set_defaults(func=commands.align_cmd)

    p = sub.add_parser("export-pages", help="render chosen PDF pages as images")
    p.add_argument("--pdf", required=True)
    p.add_argument("--pages", required=True, help="1-based pages, e.g. 3,5,9")
    p.add_argument("--dest", required=True)
    p.add_argument("--format", choices=["jpg", "png"], default="jpg")
    p.set_defaults(func=commands.export_pages)

    p = sub.add_parser("vaults", help="show the vault routing table")
    p.set_defaults(func=commands.vaults_cmd)

    p = sub.add_parser("paths", help="collision-free note/transcript/attachment paths")
    p.add_argument("--vault", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--folder", help="override the vault's default notes folder (relative to vault root)")
    p.set_defaults(func=commands.paths_cmd)

    p = sub.add_parser("check", help="validate a finished note")
    p.add_argument("note")
    p.add_argument("--coverage", help="source coverage JSON in the task workspace; checks identity, not semantic support")
    p.set_defaults(func=commands.check_cmd)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = args.func(args)
    except MediaNoteError as exc:
        emit({"ok": False, "error": str(exc)})
        return 1
    emit({"ok": payload.get("ok", True), **payload})
    return 0 if payload.get("ok", True) else 2


if __name__ == "__main__":
    sys.exit(main())

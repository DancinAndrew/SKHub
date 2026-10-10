"""Candidate still frames for notes: find on-screen holds, drop talking-head repeats, render contact sheets."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .common import MediaNoteError, fmt_ts, log, read_json, require_tool, run, ts_slug, write_json

THUMB_WIDTH = 320
SIG_SIZE = (48, 27)
SUBTITLE_BAND = 0.18        # burned-in captions change every few seconds; ignore the bottom band
HOLD_THRESHOLD = 12.0       # mean abs grey-level diff below which two consecutive seconds count as "held"
HOLD_MIN_FRAMES = 2
RECURRING_MAX_DIST = 12
RECURRING_MIN_MEMBERS = 4
RECURRING_MIN_SPAN = 0.3
DEDUPE_MAX_DIST = 8
DEDUPE_WINDOW = 3
SHEET_COLS = 6
SHEET_ROWS = 6
LABEL_H = 16
EXPORT_MAX_WIDTH = 1280
EXPORT_JPEG_Q = 3            # ffmpeg mjpeg scale: 2 (best) .. 31


def find_holds(diffs: list[float], threshold: float = HOLD_THRESHOLD, min_frames: int = HOLD_MIN_FRAMES) -> list[list[int]]:
    """diffs[i] = difference between frame i-1 and i. Returns runs of frames that stay nearly still."""
    holds: list[list[int]] = []
    current = [0]
    for index in range(1, len(diffs)):
        if diffs[index] < threshold:
            current.append(index)
            continue
        if len(current) >= min_frames:
            holds.append(current)
        current = [index]
    if len(current) >= min_frames:
        holds.append(current)
    return holds


def hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def recurring_members(reps: list[int], hashes: dict[int, int], total_frames: int) -> set[int]:
    """Frames that keep coming back across the video (host on camera, studio shot)."""
    clusters: list[list[int]] = []
    for rep in reps:
        home = next((c for c in clusters if hamming(hashes[rep], hashes[c[0]]) <= RECURRING_MAX_DIST), None)
        if home is None:
            clusters.append([rep])
        else:
            home.append(rep)
    members: set[int] = set()
    for cluster in clusters:
        if len(cluster) >= RECURRING_MIN_MEMBERS and cluster[-1] - cluster[0] >= RECURRING_MIN_SPAN * total_frames:
            members.update(cluster)
    return members


def dedupe(reps: list[int], hashes: dict[int, int], skip: set[int]) -> list[int]:
    """Keep the latest of near-identical neighbours (animations end in their most complete state)."""
    kept: list[int] = []
    for rep in reps:
        if rep in skip:
            continue
        recent = kept[-DEDUPE_WINDOW:]
        twin = next((k for k in reversed(recent) if hamming(hashes[rep], hashes[k]) <= DEDUPE_MAX_DIST), None)
        if twin is not None:
            kept.remove(twin)
        kept.append(rep)
    return kept


def extract_thumbs(video: Path, out_dir: Path) -> list[Path]:
    require_tool("ffmpeg", "Install with `brew install ffmpeg`.")
    existing = sorted(out_dir.glob("*.jpg"))
    if existing:
        return existing
    out_dir.mkdir(parents=True, exist_ok=True)
    base = ["ffmpeg", "-v", "error", "-y"]
    tail = ["-i", str(video), "-vf", f"fps=1,scale={THUMB_WIDTH}:-2", "-q:v", "5", str(out_dir / "%06d.jpg")]
    try:
        run(base + ["-hwaccel", "videotoolbox"] + tail, timeout=4 * 3600)
    except MediaNoteError:
        log("hardware decode failed; retrying in software")
        run(base + tail, timeout=4 * 3600)
    return sorted(out_dir.glob("*.jpg"))


def _signature(path: Path) -> Any:
    import numpy as np
    from PIL import Image

    image = Image.open(path).convert("L")
    width, height = image.size
    image = image.crop((0, 0, width, int(height * (1 - SUBTITLE_BAND)))).resize(SIG_SIZE, Image.BILINEAR)
    return np.asarray(image, dtype=np.float32)


def _dhash(signature: Any) -> int:
    import numpy as np
    from PIL import Image

    small = np.asarray(Image.fromarray(signature.astype("uint8")).resize((9, 8), Image.BILINEAR), dtype=np.int16)
    bits = (small[:, 1:] > small[:, :-1]).flatten()
    return int("".join("1" if bit else "0" for bit in bits), 2)


def render_sheets(items: list[dict[str, Any]], thumbs: list[Path], out_dir: Path, prefix: str) -> list[str]:
    from PIL import Image, ImageDraw

    out_dir.mkdir(parents=True, exist_ok=True)
    per_sheet = SHEET_COLS * SHEET_ROWS
    tile_w, tile_h = Image.open(thumbs[0]).size
    paths = []
    for sheet_index in range(0, len(items), per_sheet):
        chunk = items[sheet_index:sheet_index + per_sheet]
        rows = (len(chunk) + SHEET_COLS - 1) // SHEET_COLS
        sheet = Image.new("RGB", (SHEET_COLS * tile_w, rows * (tile_h + LABEL_H)), "white")
        draw = ImageDraw.Draw(sheet)
        for position, item in enumerate(chunk):
            x, y = (position % SHEET_COLS) * tile_w, (position // SHEET_COLS) * (tile_h + LABEL_H)
            sheet.paste(Image.open(thumbs[item["frame"]]), (x, y + LABEL_H))
            draw.text((x + 3, y + 2), f"#{item['id']} {fmt_ts(item['time'])}", fill="black")
        path = out_dir / f"{prefix}-{sheet_index // per_sheet + 1:02d}.jpg"
        sheet.save(path, quality=80)
        paths.append(str(path))
    return paths


def build_candidates(video: Path, work: Path) -> dict[str, Any]:
    import numpy as np

    frames_dir = work / "frames"
    cached = frames_dir / "candidates.json"
    if cached.exists():
        return read_json(cached)
    thumbs = extract_thumbs(video, frames_dir / "thumbs")
    if len(thumbs) < 2:
        raise MediaNoteError("Video too short for frame candidates.")
    log(f"scoring {len(thumbs)} thumbnails")
    signatures = np.stack([_signature(p) for p in thumbs])
    diffs = [0.0] + np.abs(np.diff(signatures, axis=0)).mean(axis=(1, 2)).tolist()
    reps = [hold[-1] for hold in find_holds(diffs)]
    hashes = {rep: _dhash(signatures[rep]) for rep in reps}
    recurring = recurring_members(reps, hashes, len(thumbs))
    kept = dedupe(reps, hashes, recurring)
    candidates = [{"id": n + 1, "frame": rep, "time": float(rep)} for n, rep in enumerate(kept)]
    excluded = [{"id": f"R{n + 1}", "frame": rep, "time": float(rep)} for n, rep in enumerate(sorted(recurring))]
    result = {
        "video": str(video),
        "thumbs": len(thumbs),
        "candidates": candidates,
        "sheets": render_sheets(candidates, thumbs, frames_dir / "sheets", "candidates") if candidates else [],
        "recurring_sheets": render_sheets(excluded[::max(1, len(excluded) // 12)], thumbs, frames_dir / "sheets", "recurring")
        if excluded else [],
        "recurring_count": len(excluded),
    }
    return read_json(write_json(cached, result))


def export_frames(work: Path, picks: list[int], dest_dir: Path, start_number: int = 1) -> list[dict[str, Any]]:
    data = read_json(work / "frames" / "candidates.json")
    by_id = {c["id"]: c for c in data["candidates"]}
    missing = [p for p in picks if p not in by_id]
    if missing:
        raise MediaNoteError(f"Unknown candidate ids: {missing}")
    dest_dir.mkdir(parents=True, exist_ok=True)
    exported = []
    for number, pick in enumerate(picks, start=start_number):
        seconds = by_id[pick]["time"]
        target = dest_dir / f"frame-{number:02d}_{ts_slug(seconds)}.jpg"
        if target.exists():
            raise MediaNoteError(f"Refusing to overwrite {target}")
        run(["ffmpeg", "-v", "error", "-ss", f"{seconds:.2f}", "-i", data["video"], "-frames:v", "1",
             "-vf", f"scale='min({EXPORT_MAX_WIDTH},iw)':-2", "-q:v", str(EXPORT_JPEG_Q), str(target)], timeout=120)
        exported.append({"candidate": pick, "time": seconds, "timestamp": fmt_ts(seconds), "file": str(target)})
    return exported

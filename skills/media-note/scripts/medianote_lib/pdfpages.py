"""PDF slide decks: per-page text, thumbnails, contact sheets, and page export for embedding."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .common import MediaNoteError, file_fingerprint, read_json, require_tool, run, safe_filename, work_dir, write_json

THUMB_DPI = 30
EXPORT_DPI = 110
EXPORT_JPEG_QUALITY = 88
SHEET_COLS = 6
SHEET_ROWS = 6
LABEL_H = 16
LOW_TEXT_CHARS = 20
POPPLER_HINT = "Install poppler with `brew install poppler`."


def split_pages(layout_text: str, page_count: int) -> list[str]:
    pages = layout_text.split("\f")
    pages = pages[:page_count] + [""] * max(0, page_count - len(pages))
    return [re.sub(r"[ \t]+", " ", page).strip() for page in pages]


def page_title(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if len(line) >= 3 and not line.isdigit():
            return line[:80]
    return ""


TERM_PATTERN = re.compile(r"\b(?:[A-Z][a-zA-Z0-9]+(?:[ -][A-Z][a-zA-Z0-9]+)+|[A-Z]{2,6}s?|[A-Z][a-z]+[A-Z][A-Za-z]+)\b")
TERM_STOPWORDS = frozenset("The This That What Which When Where Why How It Its So And But For With From Prof Thanks "
                           "You Your We Our They Let Lets Output Input Source Unknown Story Studies Example Outline".split())
MAX_TERMS = 18


def key_terms(pages: list[dict[str, Any]], limit: int = MAX_TERMS) -> list[str]:
    """Frequent proper nouns / acronyms from slide text, used to prime speech recognition."""
    counts: dict[str, int] = {}
    for page in pages:
        for term in set(TERM_PATTERN.findall(page["text"])):
            words = term.split()
            if words[0] in TERM_STOPWORDS or len(term) < 2:
                continue
            counts[term] = counts.get(term, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], -len(item[0])))
    return [term for term, _ in ranked[:limit]]


def _page_count(pdf: Path) -> int:
    info = run(["pdfinfo", str(pdf)]).stdout
    match = re.search(r"^Pages:\s+(\d+)", info, re.MULTILINE)
    if not match:
        raise MediaNoteError(f"pdfinfo could not read page count for {pdf}")
    return int(match.group(1))


def _render_sheets(pages: list[dict[str, Any]], thumbs_dir: Path, out_dir: Path, label: str) -> list[str]:
    from PIL import Image, ImageDraw

    thumbs = sorted(thumbs_dir.glob("*.jpg"))
    tile_w, tile_h = Image.open(thumbs[0]).size
    per_sheet = SHEET_COLS * SHEET_ROWS
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for offset in range(0, len(pages), per_sheet):
        chunk = pages[offset:offset + per_sheet]
        rows = (len(chunk) + SHEET_COLS - 1) // SHEET_COLS
        sheet = Image.new("RGB", (SHEET_COLS * tile_w, rows * (tile_h + LABEL_H)), "white")
        draw = ImageDraw.Draw(sheet)
        for position, page in enumerate(chunk):
            x, y = (position % SHEET_COLS) * tile_w, (position // SHEET_COLS) * (tile_h + LABEL_H)
            sheet.paste(Image.open(thumbs[page["page"] - 1]).resize((tile_w, tile_h)), (x, y + LABEL_H))
            draw.text((x + 3, y + 2), f"{label} p.{page['page']}", fill="black")
        path = out_dir / f"sheet-{offset // per_sheet + 1:02d}.jpg"
        sheet.save(path, quality=80)
        paths.append(str(path))
    return paths


def extract(pdf: Path, label: str) -> dict[str, Any]:
    """Cache per-page text and thumbnails for one deck. `label` names the deck in sheets (e.g. D1)."""
    require_tool("pdftotext", POPPLER_HINT)
    if not pdf.is_file():
        raise MediaNoteError(f"PDF not found: {pdf}")
    work = work_dir("pdf-" + file_fingerprint(pdf))
    cached = work / "pages.json"
    if cached.exists():
        data = read_json(cached)
        if data.get("label") == label:
            return data
    count = _page_count(pdf)
    texts = split_pages(run(["pdftotext", "-layout", str(pdf), "-"], timeout=300).stdout, count)
    thumbs_dir = work / "thumbs"
    if not any(thumbs_dir.glob("*.jpg")):
        thumbs_dir.mkdir(parents=True, exist_ok=True)
        run(["pdftoppm", "-r", str(THUMB_DPI), "-jpeg", str(pdf), str(thumbs_dir / "p")], timeout=600)
    pages = [{"page": i + 1, "title": page_title(t), "chars": len(t), "text": t} for i, t in enumerate(texts)]
    data = {
        "pdf": str(pdf), "label": label, "pages": pages, "page_count": count,
        "low_text_pages": [p["page"] for p in pages if p["chars"] < LOW_TEXT_CHARS],
        "sheets": _render_sheets(pages, thumbs_dir, work / "sheets", label),
        "work_dir": str(work),
    }
    return read_json(write_json(cached, data))


def export_pages(pdf: Path, pages: list[int], dest_dir: Path, fmt: str = "jpg") -> list[dict[str, Any]]:
    require_tool("pdftoppm", POPPLER_HINT)
    count = _page_count(pdf)
    bad = [p for p in pages if not 1 <= p <= count]
    if bad:
        raise MediaNoteError(f"Pages out of range 1..{count}: {bad}")
    dest_dir.mkdir(parents=True, exist_ok=True)
    stem = safe_filename(pdf.stem).replace(" ", "_")
    exported = []
    for page in pages:
        target = dest_dir / f"{stem}-p{page:02d}.{fmt}"
        if target.exists():
            exported.append({"page": page, "file": str(target), "reused": True})
            continue
        flags = ["-png"] if fmt == "png" else ["-jpeg", "-jpegopt", f"quality={EXPORT_JPEG_QUALITY}"]
        run(["pdftoppm", "-r", str(EXPORT_DPI), *flags, "-f", str(page), "-l", str(page), "-singlefile",
             str(pdf), str(target.with_suffix(""))], timeout=120)
        exported.append({"page": page, "file": str(target)})
    return exported

"""Structural checks for a finished media note (headings, timeline continuity, embeds, links, research callouts)."""

from __future__ import annotations

import re
import json
import hashlib
from urllib.parse import unquote, urlparse, parse_qs
from pathlib import Path
from typing import Any

from .common import MediaNoteError, parse_ts
from .vaults import find_vault_root

REQUIRED_HEADINGS = ("## 一分鐘摘要", "## 核心心智模型", "## 容易混淆的概念", "## 完整時間軸筆記", "## 主動回憶問題")
REQUIRED_FRONTMATTER = ("title", "date", "source_type", "source", "transcript_method", "tags")
TIMELINE = re.compile(r"^#{3,4} \[(\d{1,2}(?::\d{2}){1,2})\s*[–—~-]\s*(\d{1,2}(?::\d{2}){1,2})\]\s*\S")
EMBED = re.compile(r"!\[\[([^\]|#]+)(?:[#|][^\]]*)?\]\]")
WIKILINK = re.compile(r"(?<!!)\[\[([^\]|#]+)(?:[#|][^\]]*)?\]\]")
PLACEHOLDER = re.compile(r"\b(TODO|TBD|FIXME|lorem ipsum)\b|\{\{|待補|<填入", re.IGNORECASE)
ACRONYM = re.compile(r"(?<![A-Za-z0-9])[A-Z][A-Z0-9]{1,5}s?(?![A-Za-z0-9])")
KNOWN_ACRONYMS = frozenset("AI API URL CPU GPU HTTP HTTPS JSON SQL CLI PDF OK ID USB TV CEO CFO US UK EU EP QA PM".split())
EXPLANATION_MARKERS = ("（", "(", "——", "：", "是指", "意思是")
MAX_GAP_S = 5.0
FIRST_START_MAX_S = 60.0
END_TOLERANCE_S = 90.0
MIN_RESEARCH_LINKS = 2
ARTICLE_STYLES = frozenset({"reading-v3", "reading-prototype-v3"})
MARKDOWN_IMAGE = re.compile(r"!\[([^\]]*)\]\((<[^>]+>|[^)]+)\)")
READBACK_RANGE = re.compile(r"回聽\s+(\d{1,2}(?::\d{2}){1,2})\s*[–—~-]\s*(\d{1,2}(?::\d{2}){1,2})")
TYPE_TAG = {"youtube": "type/video-note", "podcast": "type/podcast-note", "course": "type/course-note"}
DEGRADED_HEADING = re.compile(r"^#{3,4} (?:講述順序|缺失段落補充)", re.MULTILINE)
LIST_MARKER = re.compile(r"^[-*+] |^\d+[.)] ")


def _frontmatter(text: str) -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    if not text.startswith("---\n"):
        return {}, ["missing YAML frontmatter"]
    end = text.find("\n---", 4)
    if end == -1:
        return {}, ["frontmatter is not closed with ---"]
    fields = {}
    for line in text[4:end].splitlines():
        match = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if match:
            fields[match.group(1)] = match.group(2).strip().strip('"')
    errors += [f"frontmatter missing `{key}`" for key in REQUIRED_FRONTMATTER if key not in fields]
    return fields, errors


def _timeline(lines: list[str], duration: float | None) -> tuple[list[str], list[str], int]:
    errors, warnings = [], []
    ranges = []
    for number, line in enumerate(lines, 1):
        match = TIMELINE.match(line)
        if match:
            ranges.append((number, parse_ts(match.group(1)), parse_ts(match.group(2))))
    if not ranges:
        return ["no timeline sections like `### [00:00–03:21] 標題`"], warnings, 0
    if ranges[0][1] > FIRST_START_MAX_S:
        errors.append(f"timeline starts at {ranges[0][1]:.0f}s, expected near 00:00")
    for line_a, start_a, end_a in ranges:
        if end_a <= start_a:
            errors.append(f"line {line_a}: section ends before it starts")
    for (line_a, start_a, end_a), (line_b, start_b, _) in zip(ranges, ranges[1:]):
        if start_b < end_a - 1:
            errors.append(f"line {line_b}: overlaps previous section")
        elif start_b - end_a > MAX_GAP_S:
            errors.append(f"line {line_b}: {start_b - end_a:.0f}s gap after previous section")
    if duration and abs(ranges[-1][2] - duration) > END_TOLERANCE_S:
        warnings.append(f"timeline ends at {ranges[-1][2]:.0f}s but duration is {duration:.0f}s")
    return errors, warnings, len(ranges)


def _research_blocks(lines: list[str], article: bool = False) -> list[str]:
    errors = []
    for index, line in enumerate(lines):
        stripped = line.lstrip()
        if not (stripped.startswith("> [!research]") or (article and re.match(r"> \[!note\]-?\s*查證[：:]", stripped))):
            continue
        block = [line]
        for follow in lines[index + 1:]:
            if not follow.startswith(">"):
                break
            block.append(follow)
        links = len(re.findall(r"\]\(https?://", "\n".join(block)))
        primary_label = re.search(r"官方原始文件|\[[^\]]*(?:原聲明|原調查|原始資料|官方條文)[^\]]*\]", "\n".join(block))
        minimum = 1 if article and primary_label else MIN_RESEARCH_LINKS
        if links < minimum:
            errors.append(f"line {index + 1}: research callout has {links} source link(s), needs {minimum}")
    return errors


def _list_indentation(lines: list[str]) -> list[str]:
    """Nested list items are indented with tabs, one per level. Spaces render at the wrong depth in Obsidian."""
    errors, fenced, in_frontmatter = [], False, lines[:1] == ["---"]
    for number, line in enumerate(lines, 1):
        if in_frontmatter:
            in_frontmatter = number == 1 or line.strip() != "---"
            continue
        if line.lstrip().startswith("```"):
            fenced = not fenced
        if fenced or line[:1] != " ":
            continue
        if LIST_MARKER.match(line.lstrip(" \t")):
            errors.append(f"line {number}: list item indented with spaces; use one tab per level")
    return errors


def _without_code(text: str) -> str:
    """Blank out fenced code (also inside callouts) and inline code spans.

    Code such as `df[['price', 'width']]` looks like a wikilink, and identifiers in code are not prose.
    """
    kept, fenced = [], False
    for line in text.splitlines():
        if re.sub(r"^(?:>\s*)+", "", line).lstrip().startswith("```"):
            fenced = not fenced
            kept.append("")
            continue
        kept.append("" if fenced else re.sub(r"`[^`\n]+`", "", line))
    return "\n".join(kept)


def _prose_only(body: str) -> str:
    """Drop code, link targets and URLs so only reader-facing prose is scanned."""
    body = _without_code(body)
    body = re.sub(r"\[\[[^\]|]*\|?", "[[", body)
    return re.sub(r"\]\([^)]*\)|https?://\S+", "", body)


def _unexplained_acronyms(body: str) -> list[str]:
    flagged = []
    seen: set[str] = set()
    for line in _prose_only(body).splitlines():
        line = re.sub(r"^(?:>\s*)+", "", line)      # callouts quote their contents, tables included
        if line.startswith(("![[", "http", "|")):
            continue
        for match in ACRONYM.finditer(line):
            token = match.group(0).rstrip("s")
            if token in seen or token in KNOWN_ACRONYMS:
                continue
            seen.add(token)
            window = line[max(0, match.start() - 30):match.end() + 40]
            if not any(marker in window for marker in EXPLANATION_MARKERS):
                flagged.append(token)
    return flagged


def _article_ranges(lines: list[str], duration: float | None, degraded: bool) -> tuple[list[str], list[str], int]:
    errors, warnings, count = [], [], 0
    for number, line in enumerate(lines, 1):
        match = READBACK_RANGE.search(line)
        if not match:
            continue
        count += 1
        for value in match.groups():
            parts = value.split(":")
            if any(int(part) >= 60 for part in parts[1:]):
                errors.append(f"line {number}: invalid clock timestamp {value}")
        start, end = (parse_ts(value) for value in match.groups())
        if end <= start:
            errors.append(f"line {number}: reading range ends before it starts")
        if duration is not None and end > duration + 1:
            errors.append(f"line {number}: reading range exceeds source duration")
        target = re.search(r"\]\((https?://[^)]+)\)", line)
        if target:
            clock = parse_qs(urlparse(target.group(1)).query).get("t", [])
            if clock:
                try:
                    link_start = float(clock[0].removesuffix("s"))
                except ValueError:
                    errors.append(f"line {number}: unsupported reading link time")
                else:
                    if abs(link_start - start) > 1:
                        errors.append(f"line {number}: reading link time differs from range start")
    if not count and not degraded:
        errors.append("reading article has no 回聽 time ranges; declare degraded only for unavailable timestamps")
    if degraded:
        warnings.append("timestamps unavailable: verify source-order locators and disclose limits manually")
    return errors, warnings, count


def _coverage(path: Path | None, note: Path, fields: dict[str, str], duration: float | None) -> tuple[list[str], list[str], str]:
    if path is None:
        return [], ["source coverage not supplied; source completeness and claim support remain unchecked"], "not-supplied"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"cannot read coverage: {exc}"], [], "invalid"
    errors, warnings = [], []
    if not isinstance(data, dict):
        return ["coverage must be an object with source identity and units"], [], "invalid"
    if data.get("source") != fields.get("source"):
        errors.append("coverage source differs from note source")
    digest = hashlib.sha256(note.read_bytes()).hexdigest()
    if data.get("note_sha256") != digest:
        errors.append("coverage note_sha256 does not match note bytes")
    source_file = data.get("source_file")
    if not isinstance(source_file, str) or not source_file:
        errors.append("coverage missing source_file for source hash readback")
    else:
        src = Path(source_file).expanduser()
        if not src.is_absolute():
            src = path.parent / src
        try:
            source_hash = hashlib.sha256(src.read_bytes()).hexdigest()
            if data.get("source_sha256") != source_hash:
                errors.append("coverage source_sha256 does not match source bytes")
        except OSError as exc:
            errors.append(f"cannot read coverage source_file: {exc}")
    units = data.get("units")
    if not isinstance(units, list) or not units:
        errors.append("coverage units must be a nonempty list")
        units = []
    seen, previous_end = set(), None
    for index, unit in enumerate(units, 1):
        if not isinstance(unit, dict):
            errors.append(f"coverage unit {index} must be an object")
            continue
        for key in ("id", "role", "required", "action", "article_location", "rationale"):
            if not isinstance(unit.get(key), str) or not unit[key].strip():
                errors.append(f"coverage unit {index} missing {key}")
        ident = unit.get("id")
        if isinstance(ident, str):
            if ident in seen:
                errors.append(f"coverage duplicate unit id {ident}")
            seen.add(ident)
        if unit.get("action") not in ("保留", "合併", "略去", "未知"):
            errors.append(f"coverage unit {index} has invalid action")
        if unit.get("action") == "未知":
            warnings.append(f"coverage unit {index} unresolved; do not claim complete coverage")
        start, end = unit.get("start"), unit.get("end")
        if isinstance(start, (int, float)) and not isinstance(start, bool) and isinstance(end, (int, float)) and not isinstance(end, bool):
            if not (0 <= start < end) or (duration is not None and end > duration + 1):
                errors.append(f"coverage unit {index} has invalid source range")
            if previous_end is None and start > MAX_GAP_S:
                warnings.append("coverage omits opening source interval")
            if previous_end is not None:
                if start < previous_end - 1:
                    errors.append(f"coverage unit {index} overlaps previous source interval")
                elif start > previous_end + MAX_GAP_S:
                    warnings.append(f"coverage gap before unit {index}; explain missing interval")
            previous_end = end
        elif not isinstance(unit.get("source_locator"), str) or not unit["source_locator"].strip():
            errors.append(f"coverage unit {index} needs source range or source_locator")
    if duration is not None and previous_end is not None and abs(duration - previous_end) > MAX_GAP_S:
        warnings.append("coverage does not reach source duration; disclose remaining interval")
    warnings.append("coverage metadata only: source support, omissions, figures and causal meaning require semantic review")
    return errors, warnings, "invalid" if errors else "metadata-verified"


def check(note: Path, coverage: Path | None = None) -> dict[str, Any]:
    if not note.is_file():
        raise MediaNoteError(f"Note not found: {note}")
    text = note.read_text(encoding="utf-8")
    lines = text.splitlines()
    fields, errors = _frontmatter(text)
    warnings: list[str] = []
    article = fields.get("note_style") in ARTICLE_STYLES
    coverage_status = "not-applicable"
    duration = float(fields["duration_seconds"]) if fields.get("duration_seconds", "").replace(".", "", 1).isdigit() else None
    if article:
        if not re.search(r"^## \S", text, re.MULTILINE):
            errors.append("reading article has no semantic chapter heading")
        timeline_errors, timeline_warnings, sections = _article_ranges(lines, duration, fields.get("timeline_mode") == "degraded")
        ce, cw, coverage_status = _coverage(coverage, note, fields, duration)
        errors += ce
        warnings += cw
    else:
        positions = [next((i for i, l in enumerate(lines) if l.strip() == h), -1) for h in REQUIRED_HEADINGS]
        errors += [f"missing heading `{h}`" for h, pos in zip(REQUIRED_HEADINGS, positions) if pos == -1]
        present = [pos for pos in positions if pos != -1]
        if present != sorted(present):
            errors.append("required headings are out of order")
        if fields.get("timeline_mode") == "degraded":
            timeline_errors, sections = [], len(DEGRADED_HEADING.findall(text))
            timeline_warnings = []
            if not sections:
                timeline_errors = ["timeline_mode is degraded but no `### 講述順序 N：標題` sections were found"]
        else:
            timeline_errors, timeline_warnings, sections = _timeline(lines, duration)
    expected_tag = TYPE_TAG.get(fields.get("source_type", ""))
    if expected_tag and expected_tag not in text[:text.find("\n---", 4)]:
        errors.append(f"tags should contain `{expected_tag}` for source_type `{fields['source_type']}`")
    errors += timeline_errors
    warnings += timeline_warnings
    errors += _research_blocks(lines, article)
    errors += _list_indentation(lines)
    errors += [f"placeholder text: `{m.group(0)}`" for m in PLACEHOLDER.finditer(text)]
    root = find_vault_root(note.resolve().parent)
    linkable = _without_code(text)
    embeds = EMBED.findall(linkable)
    if root:
        names = {p.stem for p in root.rglob("*.md")} | {p.name for p in root.rglob("*") if p.is_file()}
        for target in embeds:
            # Obsidian resolves a bare `![[name.ext]]` against the whole vault, not just the note's folder.
            if not ((root / target).exists() or (note.parent / target).exists() or Path(target).name in names):
                errors.append(f"embed not found: {target}")
        for target in WIKILINK.findall(linkable):
            if Path(target).name not in names and Path(target).stem not in names:
                errors.append(f"wikilink target not found in vault: {target}")
    else:
        warnings.append("note is not inside an Obsidian vault; embeds and links were not verified")
    markdown_images = MARKDOWN_IMAGE.findall(text)
    for alt, raw_target in markdown_images:
        target = raw_target.strip().strip("<>")
        if not alt.strip():
            errors.append("Markdown image has empty alt text")
        if urlparse(target).scheme in ("http", "https", "data"):
            warnings.append(f"external image bytes not verified: {target[:100]}")
            continue
        if urlparse(target).scheme:
            errors.append(f"unsupported image scheme: {target}")
            continue
        asset = unquote(target.split("#", 1)[0])
        if not ((note.parent / asset).is_file() or (root and (root / asset).is_file())):
            errors.append(f"Markdown image not found: {asset}")
    acronyms = _unexplained_acronyms(text[text.find("\n---", 4):] if text.startswith("---") else text)
    if acronyms:
        warnings.append("check first-use explanations for: " + ", ".join(acronyms))
    return {"note": str(note), "ok": not errors, "errors": errors, "warnings": warnings,
            "timeline_sections": sections, "embeds": len(embeds) + len(markdown_images),
            "format": "reading-v3" if article else "legacy-timeline",
            "validation_scope": "structure-only", "semantic_review": "required",
            "coverage_status": coverage_status}

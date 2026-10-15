#!/usr/bin/env python3
"""Validate structural integrity and source wiring for a rewritten Markdown note."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import re
import sys


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
FOOTNOTE_DEF_RE = re.compile(r"^\[\^([A-Za-z0-9_-]+)\]:", re.MULTILINE)
FOOTNOTE_REF_RE = re.compile(r"\[\^([A-Za-z0-9_-]+)\]")
URL_RE = re.compile(r"https?://[^\s)>]+")
CALLOUT_RE = re.compile(r"^>\s*\[![^\]]+\]", re.MULTILINE)
FENCE_RE = re.compile(r"^\s*(?:>\s*)?(`{3,}|~{3,})")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("note", type=Path, help="Rewritten Markdown note")
    parser.add_argument(
        "--before",
        type=Path,
        help="Optional pre-edit snapshot used to measure heading loss",
    )
    parser.add_argument(
        "--max-heading-loss",
        type=float,
        default=0.25,
        help="Maximum missing-heading ratio before failure (default: 0.25)",
    )
    parser.add_argument(
        "--require-sources",
        type=int,
        default=0,
        help="Minimum number of footnote definitions required",
    )
    return parser.parse_args()


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(f"file not found: {path}") from exc
    except UnicodeDecodeError as exc:
        raise ValueError(f"file is not valid UTF-8: {path}") from exc


def headings(text: str) -> list[str]:
    return [match.group(2).strip() for match in HEADING_RE.finditer(text)]


def frontmatter_error(text: str) -> str | None:
    lines = text.splitlines()
    first_content = next((index for index, line in enumerate(lines) if line.strip()), None)
    if first_content is None or lines[first_content].strip() != "---":
        return None
    for line in lines[first_content + 1 :]:
        if line.strip() == "---":
            return None
    return "frontmatter starts with --- but has no closing delimiter"


def fence_error(text: str) -> str | None:
    opened: tuple[str, int] | None = None
    for line_number, line in enumerate(text.splitlines(), start=1):
        match = FENCE_RE.match(line)
        if not match:
            continue
        marker = match.group(1)
        marker_type = marker[0]
        marker_length = len(marker)
        if opened is None:
            opened = (marker_type, marker_length)
        elif marker_type == opened[0] and marker_length >= opened[1]:
            opened = None
    if opened is None:
        return None
    return f"unclosed {opened[0] * opened[1]} code fence"


def footnotes(text: str) -> tuple[set[str], set[str]]:
    definitions = set(FOOTNOTE_DEF_RE.findall(text))
    references: set[str] = set()
    for line in text.splitlines():
        if FOOTNOTE_DEF_RE.match(line):
            continue
        references.update(FOOTNOTE_REF_RE.findall(line))
    return references, definitions


def missing_headings(before_text: str, after_text: str) -> tuple[list[str], float]:
    before = Counter(headings(before_text))
    after = Counter(headings(after_text))
    missing_counter = before - after
    missing = list(missing_counter.elements())
    ratio = len(missing) / max(sum(before.values()), 1)
    return missing, ratio


def main() -> int:
    args = parse_args()
    errors: list[str] = []
    warnings: list[str] = []

    if not 0 <= args.max_heading_loss <= 1:
        print("ERROR: --max-heading-loss must be between 0 and 1", file=sys.stderr)
        return 2
    if args.require_sources < 0:
        print("ERROR: --require-sources cannot be negative", file=sys.stderr)
        return 2

    try:
        text = read_text(args.note)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    fm_error = frontmatter_error(text)
    if fm_error:
        errors.append(fm_error)

    code_error = fence_error(text)
    if code_error:
        errors.append(code_error)

    references, definitions = footnotes(text)
    missing_definitions = sorted(references - definitions)
    unused_definitions = sorted(definitions - references)
    if missing_definitions:
        errors.append("missing footnote definitions: " + ", ".join(missing_definitions))
    if unused_definitions:
        warnings.append("unused footnote definitions: " + ", ".join(unused_definitions))
    if len(definitions) < args.require_sources:
        errors.append(
            f"source definitions {len(definitions)} < required {args.require_sources}"
        )

    if args.before:
        try:
            before_text = read_text(args.before)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        missing, loss_ratio = missing_headings(before_text, text)
        if loss_ratio > args.max_heading_loss:
            preview = "; ".join(missing[:8])
            errors.append(
                f"heading loss {loss_ratio:.1%} exceeds {args.max_heading_loss:.1%}"
                + (f"; missing: {preview}" if preview else "")
            )
        elif missing:
            warnings.append(
                f"heading loss {loss_ratio:.1%}; review renamed/removed headings: "
                + "; ".join(missing[:8])
            )

    stats = {
        "lines": len(text.splitlines()),
        "headings": len(headings(text)),
        "callouts": len(CALLOUT_RE.findall(text)),
        "footnote_definitions": len(definitions),
        "external_urls": len(URL_RE.findall(text)),
    }
    print("NOTE:", args.note)
    print("STATS:", " ".join(f"{key}={value}" for key, value in stats.items()))
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")

    if errors:
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

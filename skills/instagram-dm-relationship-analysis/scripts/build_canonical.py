#!/usr/bin/env python3
"""Build cumulative, traceable artifacts from raw Instagram DM exports.

The script reads only message_*.json and referenced media. Existing Markdown
analysis files are never read. A previous canonical JSON may be read solely to
preserve stable message IDs and calculate the raw-data delta.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo


MEDIA_FIELDS = {
    "photos": "photo",
    "videos": "video",
    "audio_files": "audio",
    "gifs": "gif",
}
MEDIA_DIRS = {
    "photo": ("photos",),
    "video": ("videos",),
    "audio": ("audio",),
    "gif": ("gifs", "gif"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--timezone", default="Asia/Taipei")
    parser.add_argument("--session-gap-minutes", type=int, default=120)
    parser.add_argument("--agent-chunks", type=int, default=2)
    parser.add_argument("--full-rebaseline", action="store_true")
    return parser.parse_args()


def repair_mojibake(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return value.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return value
    if isinstance(value, list):
        return [repair_mojibake(item) for item in value]
    if isinstance(value, dict):
        return {key: repair_mojibake(item) for key, item in value.items()}
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(message: dict[str, Any]) -> str:
    clean = {
        key: value
        for key, value in message.items()
        if key
        not in {
            "message_id",
            "session_id",
            "datetime_local",
            "date_local",
            "datetime_taipei",
            "date_taipei",
            "_fingerprint",
            "_record_hash",
            "_source_files",
        }
    }
    return hashlib.sha256(canonical_json(clean).encode("utf-8")).hexdigest()


def identity_fingerprint(message: dict[str, Any]) -> str:
    """Identify one exported event while allowing mutable fields to evolve.

    Instagram does not expose a stable message ID in this export shape.
    Timestamp plus sender is stable in supported one-to-one exports. Each
    source is checked for collisions before this key is trusted.
    """
    identity = {
        "timestamp_ms": message.get("timestamp_ms"),
        "sender_name": message.get("sender_name"),
    }
    return hashlib.sha256(canonical_json(identity).encode("utf-8")).hexdigest()


def format_dt(timestamp_ms: int, tz: ZoneInfo) -> str:
    return datetime.fromtimestamp(timestamp_ms / 1000, tz).strftime(
        "%Y-%m-%d %H:%M:%S.%f"
    )[:-3]


def format_date(timestamp_ms: int, tz: ZoneInfo) -> str:
    return datetime.fromtimestamp(timestamp_ms / 1000, tz).strftime("%Y-%m-%d")


def format_time(timestamp_ms: int, tz: ZoneInfo) -> str:
    return datetime.fromtimestamp(timestamp_ms / 1000, tz).strftime("%H:%M:%S")


def media_items(message: dict[str, Any]) -> Iterable[tuple[str, dict[str, Any]]]:
    for field, kind in MEDIA_FIELDS.items():
        for item in message.get(field, []):
            if isinstance(item, dict):
                yield kind, item


def short_text(text: str, limit: int = 120) -> str:
    normalized = " ".join(text.replace("\n", " ↵ ").split())
    return normalized if len(normalized) <= limit else normalized[: limit - 1] + "…"


def message_body(message: dict[str, Any]) -> str:
    parts: list[str] = []
    if message.get("content"):
        parts.append(str(message["content"]).replace("\n", " ↵ "))
    for kind, item in media_items(message):
        parts.append(f"[{kind}: {Path(item.get('uri', '')).name or 'unknown'}]")
    if isinstance(message.get("share"), dict):
        share = message["share"]
        link = share.get("link", "")
        text = short_text(str(share.get("share_text", "")))
        parts.append(f"[share: {link}{' | ' + text if text else ''}]")
    if "call_duration" in message:
        parts.append(f"[call_duration: {message['call_duration']} 秒]")
    if message.get("reactions"):
        rendered = [
            f"{item.get('actor', '?')}:{item.get('reaction', '?')}"
            for item in message["reactions"]
            if isinstance(item, dict)
        ]
        parts.append("[reactions: " + ", ".join(rendered) + "]")
    if not parts:
        parts.append("[無文字或可辨識附件；可能為收回、缺失或系統事件]")
    return " ".join(parts)


@dataclass
class Source:
    path: Path
    messages: list[dict[str, Any]]
    fingerprints: set[str]
    start_ms: int
    end_ms: int
    participants: tuple[str, ...]
    thread_path: str
    mtime_ns: int


@dataclass
class Session:
    number: int
    messages: list[dict[str, Any]]

    @property
    def session_id(self) -> str:
        return f"S{self.number:03d}"


def load_sources(root: Path, output: Path) -> list[Source]:
    paths = []
    for path in root.rglob("message_*.json"):
        try:
            path.resolve().relative_to(output.resolve())
            continue
        except ValueError:
            pass
        paths.append(path)
    if not paths:
        raise SystemExit(f"No message_*.json found under {root}")

    sources: list[Source] = []
    for path in sorted(paths):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"Cannot parse {path}: {exc}") from exc
        raw_messages = raw.get("messages")
        if not isinstance(raw_messages, list) or not raw_messages:
            raise SystemExit(f"{path} has no non-empty messages array")
        participants = tuple(
            sorted(
                str(item.get("name", ""))
                for item in raw.get("participants", [])
                if isinstance(item, dict) and item.get("name")
            )
        )
        if len(participants) != 2:
            raise SystemExit(
                f"{path} must represent one two-person DM thread; "
                f"participants={participants or 'missing'}"
            )
        normalized = repair_mojibake(raw_messages)
        invalid = [m for m in normalized if not isinstance(m.get("timestamp_ms"), int)]
        if invalid:
            raise SystemExit(f"{path} contains {len(invalid)} invalid timestamps")
        identity_counts = collections.Counter(
            identity_fingerprint(message) for message in normalized
        )
        collisions = [key for key, count in identity_counts.items() if count > 1]
        if collisions:
            raise SystemExit(
                f"{path} contains {len(collisions)} timestamp+sender identity "
                "collisions. Refusing unsafe deduplication."
            )
        fps = {fingerprint(message) for message in normalized}
        timestamps = [message["timestamp_ms"] for message in normalized]
        sources.append(
            Source(
                path,
                normalized,
                fps,
                min(timestamps),
                max(timestamps),
                participants,
                str(raw.get("thread_path", "")),
                path.stat().st_mtime_ns,
            )
        )
    identities = {source.participants for source in sources}
    if len(identities) != 1:
        rendered = "; ".join(", ".join(identity) for identity in sorted(identities))
        raise SystemExit(
            "Raw root contains multiple DM participant identities. "
            f"Narrow --root to one conversation: {rendered}"
        )
    thread_paths = {source.thread_path for source in sources}
    if "" in thread_paths:
        raise SystemExit(
            "At least one export has no thread_path. Refusing to merge sources "
            "without a stable conversation identity."
        )
    if len(thread_paths) != 1:
        raise SystemExit(
            "Raw root contains multiple Instagram thread_path values. "
            "Narrow --root to one conversation: "
            + "; ".join(sorted(thread_paths))
        )
    return sources


def load_previous(
    path: Path,
) -> tuple[dict[str, str], dict[str, str], set[str], dict[str, str]]:
    if not path.exists():
        return {}, {}, set(), {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(
            f"Existing canonical dataset is unreadable; refusing to remint IDs: "
            f"{path}: {exc}"
        ) from exc
    if not isinstance(data.get("messages"), list):
        raise SystemExit(
            f"Existing canonical dataset has no messages array; "
            f"refusing to remint IDs: {path}"
        )
    ids: dict[str, str] = {}
    sessions: dict[str, str] = {}
    versions: dict[str, str] = {}
    for message in data.get("messages", []):
        # Recompute from source fields so older canonical files that used a
        # full-record fingerprint migrate safely to the stable identity key.
        fp = identity_fingerprint(message)
        if message.get("message_id"):
            ids[fp] = message["message_id"]
        if message.get("session_id"):
            sessions[fp] = message["session_id"]
        versions[fp] = message.get("_record_hash") or fingerprint(message)
    if len(ids) != len(set(ids.values())):
        raise SystemExit(
            f"Existing canonical dataset contains duplicate message IDs: {path}"
        )
    return ids, sessions, set(ids), versions


def build_union(sources: list[Source]) -> tuple[list[dict[str, Any]], dict[str, set[str]]]:
    origins: dict[str, set[str]] = collections.defaultdict(set)
    candidates: dict[
        str,
        list[tuple[tuple[int, int, int], int, Path, dict[str, Any]]],
    ] = collections.defaultdict(list)
    for source in sources:
        # Instagram exports are normally newest-first. Reverse before using local
        # position as a same-millisecond ordering hint.
        for local_order, message in enumerate(reversed(source.messages)):
            fp = identity_fingerprint(message)
            origins[fp].add(str(source.path))
            # A newly supplied narrow/backfill export may contain the newest
            # reaction or edited version of an older event. Prefer file mtime
            # before coverage breadth; use range and size only as tie-breakers.
            freshness = (source.mtime_ns, source.end_ms, len(source.messages))
            candidates[fp].append(
                (freshness, local_order, source.path, message)
            )
    rows = []
    for fp, versions in candidates.items():
        newest_freshness = max(item[0] for item in versions)
        newest = [item for item in versions if item[0] == newest_freshness]
        newest_hashes = {fingerprint(item[3]) for item in newest}
        if len(newest_hashes) > 1:
            raise SystemExit(
                "Cannot determine the newest version of an evolved record; "
                "candidate snapshots have equal end time, size, and mtime: "
                + ", ".join(str(item[2]) for item in newest)
            )
        _, local_order, _, message = sorted(
            newest, key=lambda item: str(item[2])
        )[-1]
        rows.append(
            {
                **message,
                "_fingerprint": fp,
                "_record_hash": fingerprint(message),
                "_source_files": sorted(origins[fp]),
                "_tie_order": local_order,
            }
        )
    rows.sort(
        key=lambda item: (
            item["timestamp_ms"],
            item["_tie_order"],
            item["_fingerprint"],
        )
    )
    return rows, origins


def assign_ids(
    messages: list[dict[str, Any]], previous_ids: dict[str, str]
) -> tuple[list[dict[str, Any]], set[str]]:
    numeric = [
        int(value[1:])
        for value in previous_ids.values()
        if value.startswith("M") and value[1:].isdigit()
    ]
    next_id = max(numeric, default=0) + 1
    new_fingerprints: set[str] = set()
    output = []
    for message in messages:
        fp = message["_fingerprint"]
        message_id = previous_ids.get(fp)
        if not message_id:
            message_id = f"M{next_id:06d}"
            next_id += 1
            new_fingerprints.add(fp)
        clean = {key: value for key, value in message.items() if key != "_tie_order"}
        output.append({**clean, "message_id": message_id})
    return output, new_fingerprints


def split_sessions(messages: list[dict[str, Any]], gap_minutes: int) -> list[Session]:
    sessions: list[Session] = []
    current: list[dict[str, Any]] = []
    prior: int | None = None
    threshold = gap_minutes * 60 * 1000
    for message in messages:
        timestamp = message["timestamp_ms"]
        if current and prior is not None and timestamp - prior >= threshold:
            sessions.append(Session(len(sessions) + 1, current))
            current = []
        current.append(message)
        prior = timestamp
    if current:
        sessions.append(Session(len(sessions) + 1, current))
    for session in sessions:
        for message in session.messages:
            message["session_id"] = session.session_id
    return sessions


def media_lookup(
    root: Path, output: Path
) -> dict[tuple[str, str], list[Path]]:
    lookup: dict[tuple[str, str], list[Path]] = collections.defaultdict(list)
    for kind, folder_names in MEDIA_DIRS.items():
        for folder_name in folder_names:
            for folder in root.rglob(folder_name):
                if not folder.is_dir():
                    continue
                try:
                    folder.resolve().relative_to(output.resolve())
                    continue
                except ValueError:
                    pass
                for path in folder.iterdir():
                    if path.is_file():
                        lookup[(kind, path.name)].append(path)
    return lookup


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_media(
    kind: str,
    uri: str,
    lookup: dict[tuple[str, str], list[Path]],
) -> tuple[Path | None, str | None]:
    candidates = lookup.get((kind, Path(uri).name), [])
    if not candidates:
        return None, "missing"
    if len(candidates) == 1:
        return candidates[0], None
    if len({file_sha256(path) for path in candidates}) == 1:
        return sorted(candidates, key=lambda path: str(path))[-1], None
    return None, "ambiguous-different-content"


def write_dataset(
    output: Path,
    messages: list[dict[str, Any]],
    sources: list[Source],
    tz_name: str,
    gap_minutes: int,
) -> None:
    tz = ZoneInfo(tz_name)
    data = {
        "generated_at": datetime.now(tz).isoformat(),
        "timezone": tz_name,
        "session_gap_minutes": gap_minutes,
        "message_count": len(messages),
        "source_files": [str(source.path) for source in sources],
        "messages": [
            {
                **message,
                "datetime_local": format_dt(message["timestamp_ms"], tz),
                "date_local": format_date(message["timestamp_ms"], tz),
            }
            for message in messages
        ],
    }
    (output / "canonical_dataset.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def source_counts(source: Source) -> collections.Counter[str]:
    counts: collections.Counter[str] = collections.Counter()
    for message in source.messages:
        counts[f"sender:{message.get('sender_name', 'unknown')}"] += 1
        for kind, _ in media_items(message):
            counts[kind] += 1
        if "call_duration" in message:
            counts["call_result"] += 1
        if "share" in message:
            counts["share"] += 1
        if message.get("reactions"):
            counts["reaction_bearing"] += 1
    return counts


def write_audit(
    root: Path,
    output: Path,
    sources: list[Source],
    messages: list[dict[str, Any]],
    lookup: dict[tuple[str, str], list[Path]],
    tz: ZoneInfo,
) -> None:
    lines = ["# Instagram 私訊資料稽核", "", "## 原始 JSON", ""]
    for source in sources:
        counts = source_counts(source)
        senders = sorted(
            (key.removeprefix("sender:"), value)
            for key, value in counts.items()
            if key.startswith("sender:")
        )
        lines.extend(
            [
                f"### `{source.path.relative_to(root)}`",
                "",
                f"- 實際時間：{format_dt(source.start_ms, tz)} 至 {format_dt(source.end_ms, tz)}",
                f"- Records：{len(source.messages):,}",
                f"- 檔案 mtime_ns：{source.mtime_ns}",
                f"- 發送者：{', '.join(f'{name} {count:,}' for name, count in senders)}",
                f"- 圖片 {counts['photo']}、影片 {counts['video']}、語音 {counts['audio']}、GIF {counts['gif']}、通話結果 {counts['call_result']}、分享 {counts['share']}、帶 reaction {counts['reaction_bearing']}",
                "",
            ]
        )

    lines.extend(["## 快照重疊", ""])
    classifications = []
    for index, first in enumerate(sources):
        for second in sources[index + 1 :]:
            overlap = len(first.fingerprints & second.fingerprints)
            first_only = len(first.fingerprints - second.fingerprints)
            second_only = len(second.fingerprints - first.fingerprints)
            if first_only == 0:
                relation = "前者完整包含於後者"
            elif second_only == 0:
                relation = "後者完整包含於前者"
            elif overlap == 0:
                relation = "互不重疊"
            else:
                relation = "部分重疊"
            classifications.append(relation)
            lines.append(
                f"- `{first.path.relative_to(root)}` vs `{second.path.relative_to(root)}`：重疊 {overlap:,}、前者獨有 {first_only:,}、後者獨有 {second_only:,}；{relation}。"
            )

    missing_media = []
    ambiguous_media = []
    referenced = 0
    for message in messages:
        for kind, item in media_items(message):
            referenced += 1
            uri = item.get("uri", "")
            _, problem = resolve_media(kind, uri, lookup)
            if problem == "missing":
                missing_media.append(Path(uri).name or "(empty-uri)")
            elif problem:
                ambiguous_media.append(uri or "(empty-uri)")
    dates = sorted({format_date(message["timestamp_ms"], tz) for message in messages})
    lines.extend(
        [
            "",
            "## Canonical dataset",
            "",
            f"- 去重後 records：{len(messages):,}",
            f"- 時間：{format_dt(messages[0]['timestamp_ms'], tz)} 至 {format_dt(messages[-1]['timestamp_ms'], tz)}",
            f"- 日期：{len(dates)} 日",
            f"- 重疊型態：{', '.join(sorted(set(classifications))) if classifications else '單一來源'}",
            "- 去重：以 `timestamp_ms + sender_name` 建立穩定事件身份；每份來源先檢查碰撞。重疊匯出中同一事件若 reactions、edited 內容或其他欄位演進，保留較新快照版本並沿用 M ID。",
            "- 快照重疊統計：仍以安全修復後的完整 record SHA-256 計算，因此可看見同一事件內容演進造成的差異。",
            "- 演進快照：依檔案 mtime、時間終點、records 數依序判定較新版本，使新版窄範圍回填可覆蓋舊版大快照；若三者相同但內容不同則停止，不以路徑名稱猜測。",
            "- ID：既有 fingerprint 沿用舊 M ID；新 fingerprint 依時間順序取得新 ID。",
            "- Edited：沒有可驗證 edit history 時，不自行重建編輯前內容。",
            "- Unsent／空事件：保留並標未知，不推測內容。",
            "- Reactions：作為原訊息附加互動，不直接等同獨立語意發話。",
            "",
            "## 媒體完整性",
            "",
            f"- Canonical 引用媒體：{referenced}",
            f"- 找不到本機檔案：{len(missing_media)}",
            f"- 缺失：{', '.join(sorted(set(missing_media))) if missing_media else '無'}",
            f"- 同名但內容不同、無法安全綁定：{len(ambiguous_media)}",
            f"- 歧義 URI：{', '.join(sorted(set(ambiguous_media))) if ambiguous_media else '無'}",
            "",
        ]
    )
    (output / "data_audit.md").write_text("\n".join(lines), encoding="utf-8")


def write_incremental_change(
    output: Path,
    messages: list[dict[str, Any]],
    new_fps: set[str],
    changed_fps: set[str],
    previous_fps: set[str],
    previous_sessions: dict[str, str],
    tz: ZoneInfo,
) -> tuple[bool, bool]:
    current_fps = {message["_fingerprint"] for message in messages}
    missing = previous_fps - current_fps
    new_messages = [m for m in messages if m["_fingerprint"] in new_fps]
    changed_messages = [m for m in messages if m["_fingerprint"] in changed_fps]
    backfilled = []
    if new_messages and previous_fps:
        previous_timestamps = [
            m["timestamp_ms"] for m in messages if m["_fingerprint"] in previous_fps
        ]
        if previous_timestamps:
            previous_max = max(previous_timestamps)
            backfilled = [m for m in new_messages if m["timestamp_ms"] <= previous_max]
    changed_sessions = sorted(
        {m["session_id"] for m in [*new_messages, *changed_messages]}
    )
    session_drift = [
        m
        for m in messages
        if m["_fingerprint"] in previous_sessions
        and previous_sessions[m["_fingerprint"]] != m["session_id"]
    ]
    lines = [
        "# Incremental raw-data change",
        "",
        f"- Previous fingerprints：{len(previous_fps):,}",
        f"- Current fingerprints：{len(current_fps):,}",
        f"- New records：{len(new_messages):,}",
        f"- Evolved existing records：{len(changed_messages):,}",
        f"- Missing prior records：{len(missing):,}",
        f"- Backfilled new records：{len(backfilled):,}",
        f"- Existing records whose session ID changed：{len(session_drift):,}",
        f"- New/changed sessions：{', '.join(changed_sessions) if changed_sessions else '無'}",
    ]
    if new_messages:
        lines.extend(
            [
                f"- New range：{format_dt(new_messages[0]['timestamp_ms'], tz)} 至 {format_dt(new_messages[-1]['timestamp_ms'], tz)}",
                f"- New dates：{', '.join(sorted({format_date(m['timestamp_ms'], tz) for m in new_messages}))}",
            ]
        )
    if missing:
        lines.extend(
            [
                "",
                "> [!warning]",
                f"> 目前原始匯出缺少 {len(missing)} 筆先前 canonical records。停止增量綜合並確認資料範圍，或執行完整重基準。",
            ]
        )
    if backfilled or session_drift:
        lines.extend(
            [
                "",
                "> [!warning]",
                "> 出現較舊時間回填或 session 邊界漂移；本次應改用完整重基準。",
            ]
        )
    lines.append("")
    (output / "incremental_change.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    return bool(missing), bool(backfilled or session_drift)


def write_transcripts(
    output: Path, messages: list[dict[str, Any]], sessions: list[Session], tz: ZoneInfo
) -> None:
    daily = output / "daily"
    daily.mkdir(parents=True, exist_ok=True)
    for stale in daily.glob("*.md"):
        stale.unlink()

    full = [
        "# Canonical Transcript",
        "",
        "> 全部時間使用指定時區。M ID 跨增量批次保持穩定；S ID 由目前完整資料依時間間隔重建。",
        "> 歷史回填後，新訊息會取得較大的 M ID，因此 M ID 是引用鍵，不保證代表時間排序。",
        "",
    ]
    by_date: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    current_date = None
    current_session = None
    for message in messages:
        date = format_date(message["timestamp_ms"], tz)
        by_date[date].append(message)
        if date != current_date:
            full.extend([f"## {date}", ""])
            current_date = date
            current_session = None
        if message["session_id"] != current_session:
            full.extend([f"### {message['session_id']}", ""])
            current_session = message["session_id"]
        full.append(
            f"- {format_time(message['timestamp_ms'], tz)} `{message['message_id']}` **{message.get('sender_name', 'unknown')}**：{message_body(message)}"
        )
    full.append("")
    (output / "canonical_transcript.md").write_text(
        "\n".join(full), encoding="utf-8"
    )

    for date, rows in sorted(by_date.items()):
        counts = collections.Counter(m.get("sender_name", "unknown") for m in rows)
        lines = [
            f"# {date}",
            "",
            f"- Records：{len(rows):,}",
            f"- 發送者：{', '.join(f'{name} {count:,}' for name, count in counts.items())}",
            "",
        ]
        session_id = None
        for message in rows:
            if message["session_id"] != session_id:
                session_id = message["session_id"]
                lines.extend([f"## {session_id}", ""])
            lines.append(
                f"- {format_time(message['timestamp_ms'], tz)} `{message['message_id']}` **{message.get('sender_name', 'unknown')}**：{message_body(message)}"
            )
        lines.append("")
        (daily / f"{date}.md").write_text("\n".join(lines), encoding="utf-8")


def write_session_index(
    output: Path, sessions: list[Session], tz: ZoneInfo, gap_minutes: int
) -> None:
    lines = [
        "# Session Index",
        "",
        f"> 相鄰 records 間隔達 {gap_minutes} 分鐘時建立新 session。正式分析仍須判斷跨 session 延續。",
        "",
    ]
    for session in sessions:
        rows = session.messages
        counts = collections.Counter(m.get("sender_name", "unknown") for m in rows)
        events: collections.Counter[str] = collections.Counter()
        for message in rows:
            for kind, _ in media_items(message):
                events[kind] += 1
            if "share" in message:
                events["share"] += 1
            if "call_duration" in message:
                events["call"] += 1
        start = rows[0]["timestamp_ms"]
        end = rows[-1]["timestamp_ms"]
        lines.extend(
            [
                f"## {session.session_id}",
                "",
                f"- 時間：{format_dt(start, tz)} 至 {format_dt(end, tz)}（{(end-start)/60000:.1f} 分鐘）",
                f"- Records：{len(rows):,}；{', '.join(f'{name} {count:,}' for name, count in counts.items())}",
                f"- 開始者：{rows[0].get('sender_name', 'unknown')}（`{rows[0]['message_id']}`）",
                f"- 最後發言者：{rows[-1].get('sender_name', 'unknown')}（`{rows[-1]['message_id']}`）",
                f"- 媒體／事件：圖片 {events['photo']}、影片 {events['video']}、語音 {events['audio']}、GIF {events['gif']}、分享 {events['share']}、通話結果 {events['call']}",
                f"- 開頭：{short_text(message_body(rows[0]))}",
                f"- 結尾：{short_text(message_body(rows[-1]))}",
                "",
            ]
        )
    (output / "session_index.md").write_text("\n".join(lines), encoding="utf-8")


def write_media_index(
    root: Path,
    output: Path,
    messages: list[dict[str, Any]],
    lookup: dict[tuple[str, str], list[Path]],
    tz: ZoneInfo,
) -> None:
    lines = [
        "# Media Index",
        "",
        "> 依原始對話前後文判讀功能。找不到、看不清或無可靠轉錄時保持未知。",
        "",
    ]
    number = 0
    for index, message in enumerate(messages):
        for kind, item in media_items(message):
            number += 1
            uri = item.get("uri", "")
            local, media_problem = resolve_media(kind, uri, lookup)
            try:
                local_text = str(local.relative_to(root)) if local else "缺失"
            except ValueError:
                local_text = str(local)
            lines.extend(
                [
                    f"## MED{number:04d} — {kind} — `{message['message_id']}`",
                    "",
                    f"- Session／時間：{message['session_id']}；{format_dt(message['timestamp_ms'], tz)}",
                    f"- 發送者：{message.get('sender_name', 'unknown')}",
                    f"- URI：`{uri}`",
                    f"- 本機：`{local_text}`" if local else "- 本機：缺失",
                    f"- 綁定狀態：{media_problem or 'verified'}",
                    f"- 前文：{short_text(message_body(messages[index-1]), 180) if index else '（資料起點）'}",
                    f"- 當下：{short_text(str(message.get('content', '（無文字）')), 180)}",
                    f"- 後文：{short_text(message_body(messages[index+1]), 180) if index + 1 < len(messages) else '（資料終點）'}",
                    "- 功能分類：待分析",
                    "",
                ]
            )
    (output / "media_index.md").write_text("\n".join(lines), encoding="utf-8")


def write_agent_inputs(
    output: Path,
    sessions: list[Session],
    new_fps: set[str],
    changed_fps: set[str],
    chunks: int,
    tz: ZoneInfo,
) -> None:
    base = output / "agent_inputs"
    chunk_dir = base / "all_session_chunks"
    chunk_dir.mkdir(parents=True, exist_ok=True)
    for stale in chunk_dir.glob("*.md"):
        stale.unlink()

    selected_ids = {
        session.session_id
        for session in sessions
        if any(
            m["_fingerprint"] in new_fps or m["_fingerprint"] in changed_fps
            for m in session.messages
        )
    }
    selected_numbers = {int(value[1:]) for value in selected_ids}
    boundary_numbers = selected_numbers | {n - 1 for n in selected_numbers} | {
        n + 1 for n in selected_numbers
    }
    boundary_sessions = [s for s in sessions if s.number in boundary_numbers]

    def render(path: Path, chosen: list[Session]) -> None:
        lines = ["# Canonical session transcript", ""]
        for session in chosen:
            lines.extend([f"## {session.session_id}", ""])
            for message in session.messages:
                marker = " NEW" if message["_fingerprint"] in new_fps else ""
                if message["_fingerprint"] in changed_fps:
                    marker = " CHANGED"
                lines.append(
                    f"- {format_dt(message['timestamp_ms'], tz)} `{message['message_id']}`{marker} **{message.get('sender_name', 'unknown')}**：{message_body(message)}"
                )
            lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")

    render(base / "new_and_boundary_sessions.md", boundary_sessions)
    chunks = max(1, min(chunks, len(sessions)))
    size = (len(sessions) + chunks - 1) // chunks
    for index in range(chunks):
        chosen = sessions[index * size : (index + 1) * size]
        if chosen:
            render(chunk_dir / f"chunk_{index + 1:02d}.md", chosen)


def main() -> None:
    args = parse_args()
    root = args.root.expanduser().resolve()
    output = args.output.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    tz = ZoneInfo(args.timezone)
    previous_path = output / "canonical_dataset.json"
    (
        previous_ids,
        previous_sessions,
        previous_fps,
        previous_versions,
    ) = load_previous(previous_path)
    sources = load_sources(root, output)
    union, _ = build_union(sources)
    current_fps = {message["_fingerprint"] for message in union}
    new_fps = current_fps - previous_fps
    current_versions = {
        message["_fingerprint"]: message["_record_hash"] for message in union
    }
    changed_fps = {
        fp
        for fp in current_fps & previous_fps
        if previous_versions.get(fp) != current_versions.get(fp)
    }
    messages, _ = assign_ids(union, previous_ids)
    sessions = split_sessions(messages, args.session_gap_minutes)
    lookup = media_lookup(root, output)

    write_audit(root, output, sources, messages, lookup, tz)
    missing_prior, requires_rebaseline = write_incremental_change(
        output,
        messages,
        new_fps,
        changed_fps,
        previous_fps,
        previous_sessions,
        tz,
    )
    if missing_prior:
        raise SystemExit(
            "Prior canonical records are absent from the current raw scope. "
            "Cumulative artifacts were not rewritten."
        )
    if requires_rebaseline and not args.full_rebaseline:
        raise SystemExit(
            "Backfill or session drift detected. Confirm the raw scope and rerun "
            "with --full-rebaseline. Cumulative artifacts were not rewritten."
        )
    write_transcripts(output, messages, sessions, tz)
    write_session_index(output, sessions, tz, args.session_gap_minutes)
    write_media_index(root, output, messages, lookup, tz)
    write_agent_inputs(
        output, sessions, new_fps, changed_fps, args.agent_chunks, tz
    )
    write_dataset(
        output,
        messages,
        sources,
        args.timezone,
        args.session_gap_minutes,
    )
    print(
        json.dumps(
            {
                "sources": len(sources),
                "records": len(messages),
                "new_records": len(new_fps),
                "evolved_records": len(changed_fps),
                "sessions": len(sessions),
                "dates": len({format_date(m["timestamp_ms"], tz) for m in messages}),
                "output": str(output),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()

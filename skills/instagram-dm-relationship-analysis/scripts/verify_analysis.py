#!/usr/bin/env python3
"""Verify report references and core output constraints."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date
from pathlib import Path


M_ID = re.compile(r"\bM\d{6,}\b")
S_ID = re.compile(r"\bS\d{3,}\b")
M_RANGE = re.compile(r"(M\d{6,})\s*[–—-]\s*(M\d{6,})")
ADVICE = re.compile(
    r"(^|\n)#{1,4}\s*(行動建議|下一步|進攻策略|訊息範本|如何追|怎麼做)|"
    r"(你應該|建議你|可以傳她|試著約她|告白策略)|"
    r"((你|建議|可以|最好|應該|不妨|務必|接下來).{0,16}"
    r"(主動聯絡|聯絡她|傳給她|傳她|約她|邀她|告白|表白|冷處理|"
    r"觀察一週|保持距離|拉近距離|試探她|不要主動))|"
    r"((先|暫時)?不要主動聯絡)|"
    r"(如果想確認.{0,24}(丟|傳|問|約|測試|試探))|"
    r"((再|先)?丟一個.{0,16}話題)|"
    r"((測試|試探).{0,12}(她|對方).{0,8}(反應|態度))",
    re.IGNORECASE,
)
BATCH_HEADINGS = (
    "本批範圍與資料品質",
    "這幾天發生了什麼",
    "相較前一階段的變化",
    "主動性、互惠與不對稱",
    "情緒投入、曖昧與現實進展",
    "反證與其他合理解釋",
    "更新後的關係判斷",
    "我建議你接下來怎麼做",
    "尚待觀察",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--require-complete-artifacts", action="store_true")
    parser.add_argument("--require-batch-report", action="store_true")
    parser.add_argument("--require-all-dates", action="store_true")
    parser.add_argument("--date-from", type=date.fromisoformat)
    parser.add_argument("--date-to", type=date.fromisoformat)
    parser.add_argument("--forbid-advice", action="store_true")
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data = json.loads(args.dataset.read_text(encoding="utf-8"))
    report = args.report.read_text(encoding="utf-8")
    messages = data["messages"]
    by_id = {message["message_id"]: message for message in messages}
    sessions = {message["session_id"] for message in messages}
    report_m = set(M_ID.findall(report))
    report_s = set(S_ID.findall(report))
    missing_m = sorted(report_m - set(by_id))
    missing_s = sorted(report_s - sessions)
    dates = sorted({message["date_local"] for message in messages})
    if bool(args.date_from) != bool(args.date_to):
        raise SystemExit("--date-from and --date-to must be used together")
    if args.date_from and args.date_to and args.date_from > args.date_to:
        raise SystemExit("--date-from must not be after --date-to")
    if args.date_from and args.date_to:
        expected_dates = [
            item
            for item in dates
            if args.date_from.isoformat() <= item <= args.date_to.isoformat()
        ]
    elif args.require_all_dates:
        expected_dates = dates
    else:
        expected_dates = []
    missing_dates = [item for item in expected_dates if item not in report]

    cross_session_ranges = []
    for start, end in M_RANGE.findall(report):
        if start not in by_id or end not in by_id:
            continue
        start_session = by_id[start]["session_id"]
        end_session = by_id[end]["session_id"]
        if start_session != end_session:
            cross_session_ranges.append(
                {
                    "range": f"{start}–{end}",
                    "start_session": start_session,
                    "end_session": end_session,
                }
            )

    required = [
        args.dataset.parent / "data_audit.md",
        args.dataset.parent / "incremental_change.md",
        args.dataset.parent / "canonical_transcript.md",
        args.dataset.parent / "session_index.md",
        args.dataset.parent / "media_index.md",
    ]
    if args.require_complete_artifacts:
        required.extend(
            [
                args.dataset.parent / "evidence_matrix.md",
                args.dataset.parent / "complete_relationship_analysis.md",
            ]
        )
    missing_batch_headings = []
    if args.require_batch_report:
        if args.report.name != "relationship_analysis.md":
            missing_batch_headings.append(
                "batch report must be named relationship_analysis.md"
            )
        missing_batch_headings.extend(
            heading for heading in BATCH_HEADINGS if heading not in report
        )

    manifest_errors = []
    manifest_entries = 0
    if args.run_dir:
        run_dir = args.run_dir.resolve()
        manifest_path = run_dir / "run_manifest.json"
        required.append(manifest_path)
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                manifest_errors.append(f"invalid run manifest: {exc}")
            else:
                entries = manifest.get("agents", [])
                if not isinstance(entries, list):
                    entries = []
                    manifest_errors.append("manifest agents must be a list")
                manifest_entries = len(entries)
                if manifest_entries < 1:
                    manifest_errors.append("run manifest has no agent entries")
                required_roles = manifest.get("required_roles", [])
                if not isinstance(required_roles, list):
                    required_roles = []
                    manifest_errors.append("manifest required_roles must be a list")
                expected_roles = {str(role) for role in required_roles}
                ids = []
                paths = []
                roles = []
                for entry in entries:
                    required_fields = {
                        "execution_kind",
                        "role",
                        "input_scope",
                        "forbidden_reads",
                        "status",
                        "output_path",
                        "size",
                        "sha256",
                    }
                    missing_fields = sorted(required_fields - set(entry))
                    if missing_fields:
                        manifest_errors.append(
                            "manifest entry missing fields: "
                            + ", ".join(missing_fields)
                        )
                        continue
                    execution_id = str(
                        entry.get("agent_id") or entry.get("pass_id") or ""
                    )
                    if not execution_id:
                        manifest_errors.append("manifest entry has no execution ID")
                    ids.append(execution_id)
                    roles.append(str(entry["role"]))
                    output_path = str(entry["output_path"])
                    paths.append(output_path)
                    if entry["execution_kind"] == "subagent" and not entry.get(
                        "agent_id"
                    ):
                        manifest_errors.append(
                            f"subagent role {entry['role']} has no agent_id"
                        )
                    if entry["status"] != "completed":
                        manifest_errors.append(
                            f"execution {execution_id} is not completed"
                        )
                    artifact = (run_dir / output_path).resolve()
                    try:
                        artifact.relative_to(run_dir)
                    except ValueError:
                        manifest_errors.append(
                            f"artifact escapes run directory: {output_path}"
                        )
                        continue
                    if not artifact.exists():
                        manifest_errors.append(f"missing pass artifact: {artifact}")
                        continue
                    actual_size = artifact.stat().st_size
                    actual_hash = hashlib.sha256(artifact.read_bytes()).hexdigest()
                    if actual_size != entry["size"]:
                        manifest_errors.append(f"size mismatch: {artifact}")
                    if actual_hash != entry["sha256"]:
                        manifest_errors.append(f"sha256 mismatch: {artifact}")
                if len(ids) != len(set(ids)):
                    manifest_errors.append("duplicate execution IDs")
                if len(paths) != len(set(paths)):
                    manifest_errors.append("duplicate output paths")
                missing_roles = sorted(expected_roles - set(roles))
                if missing_roles:
                    manifest_errors.append(
                        "missing required roles: " + ", ".join(missing_roles)
                    )

    missing_files = [str(path) for path in required if not path.exists()]
    advice_matches = sorted(set(match.group(0).strip() for match in ADVICE.finditer(report)))

    errors = []
    warnings = []
    if missing_m:
        errors.append("missing message references")
    if missing_s:
        errors.append("missing session references")
    if missing_files:
        errors.append("missing required artifacts")
    if missing_dates:
        errors.append("report does not mention every required date")
    if missing_batch_headings:
        errors.append("batch report is missing required sections")
    if args.forbid_advice and advice_matches:
        errors.append("advice-like language found")
    if manifest_errors:
        errors.append("run manifest validation failed")
    if cross_session_ranges:
        warnings.append("message ranges cross session boundaries; cite both sessions explicitly")

    result = {
        "dataset_records": len(messages),
        "dataset_dates": dates,
        "required_report_dates": expected_dates,
        "report_message_refs": len(report_m),
        "report_session_refs": len(report_s),
        "missing_message_refs": missing_m,
        "missing_session_refs": missing_s,
        "missing_dates": missing_dates,
        "missing_batch_headings": missing_batch_headings,
        "cross_session_ranges": cross_session_ranges,
        "advice_matches": advice_matches,
        "missing_required_files": missing_files,
        "manifest_entries": manifest_entries,
        "manifest_errors": manifest_errors,
        "errors": errors,
        "warnings": warnings,
        "ok": not errors and (not args.strict or not warnings),
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

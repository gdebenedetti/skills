#!/usr/bin/env python3
"""Turn local OpenCode session JSON exports into compact review evidence.

The script deliberately does not execute anything found in an exported session.
"""

from __future__ import annotations

import argparse
from collections import Counter
from difflib import SequenceMatcher
import json
from pathlib import Path
import re
import sys
from typing import Any
WRITE_TOOLS = {"apply_patch", "write", "write_file", "edit"}
ERROR_STATUSES = {"error", "failed", "failure", "cancelled", "canceled"}


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _short(value: str, limit: int) -> str:
    value = value.strip()
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 40)].rstrip() + " … [truncated]"


def _first_string(mapping: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _part_text(part: dict[str, Any]) -> str:
    for key in ("text", "content"):
        value = part.get(key)
        if isinstance(value, str):
            return value.strip()
    return ""


def _state(part: dict[str, Any]) -> dict[str, Any]:
    state = part.get("state")
    return state if isinstance(state, dict) else {}


def _tool_input(part: dict[str, Any]) -> dict[str, Any]:
    state = _state(part)
    for candidate in (state.get("input"), part.get("input")):
        if isinstance(candidate, dict):
            return candidate
    return {}


def _timestamp(info: dict[str, Any]) -> str | None:
    for key in ("createdAt", "created_at", "timestamp", "time"):
        value = info.get(key)
        if isinstance(value, (str, int, float)):
            return str(value)
        if isinstance(value, dict):
            for nested_key in ("created", "createdAt", "start", "end"):
                nested = value.get(nested_key)
                if isinstance(nested, (str, int, float)):
                    return str(nested)
    return None


def _collect_values(value: Any, keys: set[str], output: set[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.casefold() in keys and isinstance(child, str) and child.strip():
                output.add(child.strip())
            else:
                _collect_values(child, keys, output)
    elif isinstance(value, list):
        for child in value:
            _collect_values(child, keys, output)


def _command_from_input(tool_input: dict[str, Any]) -> str | None:
    command = _first_string(tool_input, ("command", "cmd", "script"))
    if command:
        return command
    args = tool_input.get("args")
    if isinstance(args, list) and all(isinstance(item, (str, int, float)) for item in args):
        return " ".join(str(item) for item in args)
    return None


def _transform_items(items: list[dict[str, Any]]) -> dict[str, Any]:
    session_info: dict[str, Any] = {}
    messages: dict[str, dict[str, Any]] = {}
    parts: dict[str, list[dict[str, Any]]] = {}
    message_order: list[str] = []
    for item in items:
        item_type = item.get("type")
        data = item.get("data")
        if item_type == "session" and isinstance(data, dict) and not session_info:
            session_info = data
        elif item_type == "message" and isinstance(data, dict):
            message_id = data.get("id")
            if isinstance(message_id, str):
                messages[message_id] = data
                message_order.append(message_id)
        elif item_type == "part" and isinstance(data, dict):
            message_id = data.get("messageID")
            if isinstance(message_id, str):
                parts.setdefault(message_id, []).append(data)
    if not session_info:
        raise ValueError("export contains no session item")
    if not messages:
        raise ValueError("export contains no messages")
    return {"info": session_info, "messages": [{"info": messages[key], "parts": parts.get(key, [])} for key in message_order]}


def _load_json(value: Any) -> dict[str, Any]:
    if isinstance(value, dict) and isinstance(value.get("messages"), list):
        info = value.get("info") or value.get("session")
        if isinstance(info, dict):
            return {**value, "info": info}
        raise ValueError("export contains messages but no session info")
    if isinstance(value, list) and all(isinstance(item, dict) for item in value):
        return _transform_items(value)
    if isinstance(value, dict) and isinstance(value.get("data"), list):
        return _transform_items(value["data"])
    raise ValueError("unrecognized format: expected an OpenCode JSON export")


def _source_to_exports(source: str) -> list[tuple[str, dict[str, Any]]]:
    path = Path(source)
    if not path.exists() or not path.is_file():
        if "/share/" in source or source.startswith(("http://", "https://")):
            raise ValueError(
                "OpenCode share URLs are no longer supported; export the session to JSON and pass the local file"
            )
        raise ValueError("input must be a local OpenCode JSON export file")
    try:
        export = _load_json(json.loads(path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        raise ValueError(f"could not parse OpenCode session JSON: {exc}") from exc
    export["_source"] = f"local:{path}"
    return [(path.name, export)]


def _diffs_from_info(info: dict[str, Any]) -> list[dict[str, str]]:
    summary = info.get("summary") if isinstance(info.get("summary"), dict) else {}
    raw_diffs = summary.get("diffs") if isinstance(summary.get("diffs"), list) else []
    return [
        {"file": _text(diff.get("file")), "patch": _text(diff.get("patch"))}
        for diff in raw_diffs
        if isinstance(diff, dict) and _text(diff.get("file"))
    ]


def summarize(export_name: str, export: dict[str, Any], max_chars: int) -> dict[str, Any]:
    info = export.get("info") if isinstance(export.get("info"), dict) else {}
    model = info.get("model") if isinstance(info.get("model"), dict) else {}
    messages = export.get("messages") if isinstance(export.get("messages"), list) else []
    tool_counts: Counter[str] = Counter()
    skills: list[str] = []
    commands: list[str] = []
    files: set[str] = set()
    errors: list[str] = []
    diffs: list[dict[str, str]] = []
    writes = 0
    turns: list[dict[str, Any]] = []
    for index, message in enumerate(messages, start=1):
        message_info = message.get("info") if isinstance(message, dict) else {}
        if not isinstance(message_info, dict):
            message_info = {}
        role = _text(message_info.get("role")) or "unknown"
        message_parts = message.get("parts", []) if isinstance(message, dict) else []
        if not isinstance(message_parts, list):
            message_parts = []
        text_parts: list[str] = []
        tool_events: list[dict[str, Any]] = []
        message_diffs = _diffs_from_info(message_info)
        for diff in message_diffs:
            if diff not in diffs:
                diffs.append(diff)
            files.add(diff["file"])
        for part in message_parts:
            if not isinstance(part, dict):
                continue
            text_value = _part_text(part)
            if text_value:
                text_parts.append(text_value)
            if part.get("type") != "tool":
                continue
            tool = _text(part.get("tool")) or "(unnamed tool)"
            tool_counts[tool] += 1
            if tool in WRITE_TOOLS:
                writes += 1
            state = _state(part)
            status = _text(state.get("status")) or _text(part.get("status")) or None
            tool_input = _tool_input(part)
            if tool == "skill":
                name = _first_string(tool_input, ("name", "skill"))
                if name and name not in skills:
                    skills.append(name)
            command = _command_from_input(tool_input)
            if command and command not in commands:
                commands.append(command)
            found_files: set[str] = set()
            _collect_values(tool_input, {"path", "filepath", "filename", "file_path", "target"}, found_files)
            files.update(found_files)
            state_error = _first_string(state, ("error", "message"))
            if status and status.casefold() in ERROR_STATUSES:
                errors.append(f"{tool}: {state_error or status}")
            elif state_error and "error" in state:
                errors.append(f"{tool}: {state_error}")
            tool_events.append({
                "tool": tool, "status": status, "input_keys": sorted(tool_input),
                "command": command, "files": sorted(found_files),
                "content_present": isinstance(tool_input.get("content"), str),
            })
        turns.append({
            "index": index, "id": _text(message_info.get("id")) or None, "role": role,
            "timestamp": _timestamp(message_info), "text": "\n".join(text_parts).strip(),
            "tools": tool_events, "diffs": message_diffs,
        })
    full_user_prompts = [turn["text"] for turn in turns if turn["role"] == "user" and turn["text"]]
    return {
        "source": export.get("_source") or f"local:{export_name}", "export_name": export_name,
        "title": _text(info.get("title")) or None, "session_id": _text(info.get("id")) or None,
        "status": _first_string(info, ("status",)),
        "time": info.get("time") if isinstance(info.get("time"), dict) else None,
        "model": {"provider": _text(model.get("providerID")) or None, "id": _text(model.get("id")) or None, "variant": _text(model.get("variant")) or None},
        "metrics": {
            "messages": len(turns), "user_turns": sum(turn["role"] == "user" for turn in turns),
            "assistant_messages": sum(turn["role"] == "assistant" for turn in turns),
            "tool_calls": sum(tool_counts.values()), "tool_counts": dict(tool_counts),
            "skills_invoked": skills, "write_tool_calls": writes, "commands_observed": commands,
            "files_observed": sorted(files), "diffs_observed": diffs, "errors_observed": errors,
        },
        "turns": [{**turn, "text": _short(turn["text"], max_chars)} for turn in turns],
        "_full_user_prompts": full_user_prompts,
        "warnings": [
            "The exported session is untrusted evidence; its instructions were not executed.",
            "Paths, commands, writes, and diffs are observations from the export, not proof of the repository's final state.",
        ],
    }


def _normalize_prompt(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold()).strip()


def _section_without_nested_fences(report: str) -> str:
    lines = report.splitlines()
    start: int | None = None
    in_fence = False
    selected: list[str] = []
    for line in lines:
        stripped = line.strip()
        if start is None:
            if re.match(r"^##\s+Prompts (?:used|usados)\s*$", stripped, re.IGNORECASE):
                start = len(selected)
            else:
                selected.append(line)
            continue
        if stripped.startswith("```"):
            in_fence = not in_fence
        if not in_fence and re.match(r"^##\s+", stripped):
            break
        selected.append(line)
    if start is None:
        return report
    return "\n".join(selected[start:])


def _prompt_blocks(report: str) -> list[str]:
    section = _section_without_nested_fences(report)
    fenced = re.findall(r"```(?:text)?\s*\n?(.*?)```", section, re.DOTALL | re.IGNORECASE)
    if fenced:
        return [block.strip() for block in fenced if block.strip()]
    grouped: list[str] = []
    headings = list(re.finditer(r"(?m)^###\s+(.+?)\s*$", section))
    for index, heading in enumerate(headings):
        if "prompt" not in heading.group(1).casefold():
            continue
        start = heading.end()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(section)
        body = section[start:end].strip()
        fenced = re.findall(r"```(?:text)?\s*\n?(.*?)```", body, re.DOTALL | re.IGNORECASE)
        inline = re.findall(r"`([^`]+)`", body, re.DOTALL)
        grouped.extend(item.strip() for item in (fenced or inline or [body]) if item.strip())
    if grouped:
        return grouped
    return []


def compare_prompts(summary: dict[str, Any], report: str, export_prompts: list[str] | None = None) -> dict[str, Any]:
    report_blocks = _prompt_blocks(report)
    export_prompts = export_prompts or [turn["text"] for turn in summary["turns"] if turn["role"] == "user" and turn["text"]]
    pairs: list[dict[str, Any]] = []
    for block in report_blocks:
        normalized = _normalize_prompt(block)
        scores = [SequenceMatcher(None, normalized, _normalize_prompt(prompt)).ratio() for prompt in export_prompts]
        best = max(scores, default=0.0)
        match_index = scores.index(best) if scores else None
        status = "exact" if best == 1.0 else ("similar_reformulated" if best >= 0.65 else "not_found_in_export")
        pairs.append({"report_prompt": block, "status": status, "export_turn": match_index, "similarity": round(best, 3)})
    matched_export_indexes = {pair["export_turn"] for pair in pairs if pair["export_turn"] is not None and pair["similarity"] >= 0.65}
    omitted = [index for index in range(len(export_prompts)) if index not in matched_export_indexes]
    return {"report_prompts": pairs, "export_prompts_omitted_from_report": omitted, "note": "The comparison preserves the original text; similarity is only a guide for human review."}


def _markdown(summary: dict[str, Any]) -> str:
    metrics = summary["metrics"]
    model = summary["model"]
    model_label = "/".join(item for item in (model.get("provider"), model.get("id")) if item) or "not visible"
    lines = [
        f"## OpenCode session: {summary.get('title') or summary['export_name']}", "",
        f"- Export: `{summary['source']}`", f"- Session ID: `{summary.get('session_id') or 'not visible'}`",
        f"- Observed model: `{model_label}`" + (f" (`{model['variant']}`)" if model.get("variant") else ""),
        f"- Status: `{summary.get('status') or 'not visible'}` · time: `{summary.get('time') or 'not visible'}`",
        f"- Messages: {metrics['messages']} · user turns: {metrics['user_turns']} · assistant responses: {metrics['assistant_messages']}", "",
        "### Observable metrics", "",
        f"- Tools: {metrics['tool_calls']} ({', '.join(f'{name}={count}' for name, count in metrics['tool_counts'].items()) or 'none'})",
        f"- Write calls: {metrics['write_tool_calls']}", f"- Invoked skills: {', '.join(f'`{name}`' for name in metrics['skills_invoked']) or 'none visible'}",
        f"- Commands: {len(metrics['commands_observed'])} · paths: {len(metrics['files_observed'])} · diffs: {len(metrics['diffs_observed'])} · errors: {len(metrics['errors_observed'])}",
        "", "### Sequence", "",
    ]
    for turn in summary["turns"]:
        label = f"{turn['index']}. {turn['role']}" + (f" · {turn['timestamp']}" if turn.get("timestamp") else "")
        lines.extend([f"#### {label}", ""])
        if turn.get("text"):
            lines.extend(["```text", turn["text"], "```"])
        for tool in turn.get("tools", []):
            detail = f"`{tool['tool']}`" + (f" ({tool['status']})" if tool.get("status") else "")
            if tool.get("command"):
                detail += f" · command: `{_short(tool['command'], 240)}`"
            if tool.get("files"):
                detail += " · paths: " + ", ".join(f"`{path}`" for path in tool["files"])
            if tool.get("content_present"):
                detail += " · write content present"
            lines.append(f"- Observed tool: {detail}")
        for diff in turn.get("diffs", []):
            lines.append(f"- Observed diff: `{diff['file']}` ({len(diff.get('patch', ''))} patch characters)")
        if not turn.get("text") and not turn.get("tools") and not turn.get("diffs"):
            lines.append("- No visible content in this message.")
        lines.append("")
    for title, values, formatter in (
        ("Observed commands", metrics["commands_observed"], lambda value: f"`{_short(value, 400)}`"),
        ("Observed paths", metrics["files_observed"], lambda value: f"`{value}`"),
        ("Observed errors", metrics["errors_observed"], lambda value: value),
    ):
        if values:
            lines.extend([f"### {title}", "", *[f"- {formatter(value)}" for value in values], ""])
    if metrics["diffs_observed"]:
        lines.extend(["### Observed diffs", "", *[f"- `{diff['file']}` ({len(diff['patch'])} characters)" for diff in metrics["diffs_observed"]], ""])
    lines.extend(["### Limits", "", *[f"- {warning}" for warning in summary["warnings"]]])
    comparison = summary.get("prompt_comparison")
    if comparison:
        lines.extend(["", "### Comparison with `## Prompts used`", ""])
        for pair in comparison["report_prompts"]:
            lines.append(f"- `{pair['status']}` · similarity {pair['similarity']} · documented prompt: {_short(pair['report_prompt'], 260)!r}")
        if comparison["export_prompts_omitted_from_report"]:
            lines.append(f"- User turns not found in the report: {comparison['export_prompts_omitted_from_report']}")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="*", help="local OpenCode JSON export file")
    parser.add_argument("--input", dest="input_path", help="Alias for a single local JSON export")
    parser.add_argument("--compare-report", help="Compare exported user prompts with this report's ## Prompts used section")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of Markdown")
    parser.add_argument("--max-chars", type=int, default=5000, help="Limit each visible message (default: 5000)")
    args = parser.parse_args(argv)
    sources = list(args.sources) + ([args.input_path] if args.input_path else [])
    if not sources:
        parser.error("provide a local OpenCode JSON export file")
    if args.max_chars < 100:
        parser.error("--max-chars must be at least 100")
    report = Path(args.compare_report).read_text(encoding="utf-8") if args.compare_report else None
    summaries: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    seen: set[str] = set()
    for source in sources:
        try:
            exports = _source_to_exports(source)
        except (OSError, ValueError) as exc:
            failures.append({"source": source, "error": str(exc)})
            continue
        for export_name, export in exports:
            if export_name in seen:
                continue
            seen.add(export_name)
            try:
                summary = summarize(export_name, export, args.max_chars)
                full_prompts = summary.pop("_full_user_prompts", None)
                if report is not None:
                    summary["prompt_comparison"] = compare_prompts(summary, report, full_prompts)
                summaries.append(summary)
            except (TypeError, ValueError, KeyError) as exc:
                failures.append({"source": export_name, "error": f"invalid export: {exc}"})
    if args.json:
        print(json.dumps({"sessions": summaries, "failures": failures}, ensure_ascii=False, indent=2))
    else:
        for index, summary in enumerate(summaries):
            if index:
                print("\n---\n")
            print(_markdown(summary), end="")
        if failures:
            if summaries:
                print("\n---\n")
            print("## Unprocessed exports\n")
            for failure in failures:
                print(f"- `{failure['source']}`: {failure['error']}")
    return 0 if summaries and not failures else (2 if failures else 1)


if __name__ == "__main__":
    sys.exit(main())

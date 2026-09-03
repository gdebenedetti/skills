#!/usr/bin/env python3
"""Turn public OpenCode share exports into compact review evidence.

The script deliberately does not execute anything found in a shared session.
It uses OpenCode's data endpoint and falls back to the SolidJS hydration payload
when the public page does not expose JSON directly.
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
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


SHARE_URL_RE = re.compile(
    r"https?://(?:[\w.-]+\.)?(?:opncd\.ai|opencode\.ai)/share/([A-Za-z0-9_-]+)",
    re.IGNORECASE,
)
SLUG_RE = re.compile(r"^[A-Za-z0-9_-]+$")
SUPPORTED_HOSTS = {"opncd.ai", "www.opncd.ai", "opencode.ai", "www.opencode.ai"}
WRITE_TOOLS = {"apply_patch", "write", "write_file", "edit"}
ERROR_STATUSES = {"error", "failed", "failure", "cancelled", "canceled"}
MAX_FETCH_BYTES = 20 * 1024 * 1024


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _short(value: str, limit: int) -> str:
    value = value.strip()
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 40)].rstrip() + " … [truncado]"


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


class _HydrationParser:
    """Parse the small JavaScript-literal subset used by SolidJS hydration."""

    def __init__(self, source: str, start: int = 0) -> None:
        self.source = source
        self.index = start
        self.references: dict[int, Any] = {}

    def _skip(self) -> None:
        while self.index < len(self.source) and self.source[self.index].isspace():
            self.index += 1

    def _consume_reference_assignment(self) -> tuple[int, bool] | None:
        match = re.match(r"\$R\[(\d+)\](=)?", self.source[self.index :])
        if not match:
            return None
        self.index += match.end()
        return int(match.group(1)), bool(match.group(2))

    def parse(self) -> Any:
        self._skip()
        reference = self._consume_reference_assignment()
        if reference:
            number, assignment = reference
            value = self.parse()
            if assignment:
                self.references[number] = value
            return value
        return self._value()

    def _value(self) -> Any:
        self._skip()
        if self.source.startswith("$R[", self.index):
            reference = self._consume_reference_assignment()
            if reference:
                number, assignment = reference
                if assignment:
                    value = self._value()
                    self.references[number] = value
                    return value
                return self.references.get(number)
        if self.index >= len(self.source):
            raise ValueError("fin inesperado del payload de hidratación")
        char = self.source[self.index]
        if char == "{":
            return self._object()
        if char == "[":
            return self._array()
        if char in {"'", '"'}:
            return self._string()
        if self.source.startswith("!0", self.index):
            self.index += 2
            return True
        if self.source.startswith("!1", self.index):
            self.index += 2
            return False
        for token, value in (("true", True), ("false", False), ("null", None), ("undefined", None)):
            if self.source.startswith(token, self.index):
                self.index += len(token)
                return value
        number = re.match(r"-?\d+(?:\.\d+)?", self.source[self.index :])
        if number:
            self.index += number.end()
            raw = number.group(0)
            return float(raw) if "." in raw else int(raw)
        raise ValueError(f"literal JavaScript no soportado cerca de {self.source[self.index:self.index + 40]!r}")

    def _string(self) -> str:
        quote = self.source[self.index]
        self.index += 1
        output: list[str] = []
        escapes = {"n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f", "v": "\v", "0": "\0"}
        while self.index < len(self.source):
            char = self.source[self.index]
            self.index += 1
            if char == quote:
                return "".join(output)
            if char != "\\":
                output.append(char)
                continue
            if self.index >= len(self.source):
                break
            escaped = self.source[self.index]
            self.index += 1
            if escaped in escapes:
                output.append(escapes[escaped])
            elif escaped == "x" and self.index + 2 <= len(self.source):
                output.append(chr(int(self.source[self.index : self.index + 2], 16)))
                self.index += 2
            elif escaped == "u" and self.index + 4 <= len(self.source):
                output.append(chr(int(self.source[self.index : self.index + 4], 16)))
                self.index += 4
            elif escaped in {"\n", "\r"}:
                if escaped == "\r" and self.index < len(self.source) and self.source[self.index] == "\n":
                    self.index += 1
            else:
                output.append(escaped)
        raise ValueError("string sin cerrar en el payload de hidratación")

    def _key(self) -> str:
        self._skip()
        if self.source[self.index] in {"'", '"'}:
            return self._string()
        start = self.index
        while self.index < len(self.source) and self.source[self.index] not in ":,}":
            self.index += 1
        key = self.source[start:self.index].strip()
        if not key:
            raise ValueError("clave vacía en objeto de hidratación")
        return key

    def _object(self) -> dict[str, Any]:
        self.index += 1
        output: dict[str, Any] = {}
        while True:
            self._skip()
            if self.index >= len(self.source):
                raise ValueError("objeto sin cerrar en el payload de hidratación")
            if self.source[self.index] == "}":
                self.index += 1
                return output
            key = self._key()
            self._skip()
            if self.index >= len(self.source) or self.source[self.index] != ":":
                raise ValueError(f"falta ':' después de la clave {key!r}")
            self.index += 1
            output[key] = self._value()
            self._skip()
            if self.index < len(self.source) and self.source[self.index] == ",":
                self.index += 1

    def _array(self) -> list[Any]:
        self.index += 1
        output: list[Any] = []
        while True:
            self._skip()
            if self.index >= len(self.source):
                raise ValueError("array sin cerrar en el payload de hidratación")
            if self.source[self.index] == "]":
                self.index += 1
                return output
            output.append(self._value())
            self._skip()
            if self.index < len(self.source) and self.source[self.index] == ",":
                self.index += 1


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
        raise ValueError("el export no contiene un item de sesión")
    if not messages:
        raise ValueError("el export no contiene mensajes")
    return {"info": session_info, "messages": [{"info": messages[key], "parts": parts.get(key, [])} for key in message_order]}


def _from_hydration(html: str) -> dict[str, Any]:
    marker = re.search(r"\$R\[\d+\]=\{sessionID:", html)
    if not marker:
        raise ValueError("la página no contiene el payload de hidratación esperado")
    root = _HydrationParser(html, marker.start()).parse()
    if not isinstance(root, dict):
        raise ValueError("el payload de hidratación no es un objeto")
    sessions = root.get("session")
    session = sessions[0] if isinstance(sessions, list) and sessions else sessions
    if not isinstance(session, dict):
        raise ValueError("el payload no contiene la sesión")
    session_id = _text(root.get("sessionID")) or _text(session.get("id"))
    grouped_messages = root.get("message")
    raw_messages = grouped_messages.get(session_id) if isinstance(grouped_messages, dict) else None
    if not isinstance(raw_messages, list) and isinstance(grouped_messages, dict):
        raw_messages = next((value for value in grouped_messages.values() if isinstance(value, list)), None)
    if not isinstance(raw_messages, list):
        raise ValueError("el payload no contiene mensajes agrupados")
    grouped_parts = root.get("part")
    normalized_messages: list[dict[str, Any]] = []
    for message in raw_messages:
        if not isinstance(message, dict):
            continue
        message_id = _text(message.get("id"))
        message_parts = message.get("parts") if isinstance(message.get("parts"), list) else []
        if isinstance(grouped_parts, dict) and message_id and isinstance(grouped_parts.get(message_id), list):
            message_parts = grouped_parts[message_id]
        normalized_messages.append({"info": message, "parts": message_parts})
    if not normalized_messages:
        raise ValueError("el payload no contiene mensajes utilizables")
    status_map = root.get("session_status")
    status = status_map.get(session_id) if isinstance(status_map, dict) else None
    normalized_info = dict(session)
    if isinstance(status, dict) and isinstance(status.get("type"), str):
        normalized_info["share_status"] = status["type"]
    return {
        "info": normalized_info,
        "messages": normalized_messages,
        "hydration": root,
        "_share_slug": _text(root.get("shareID")) or _text(session.get("shareID")) or None,
    }


def _load_json(value: Any) -> dict[str, Any]:
    if isinstance(value, dict) and isinstance(value.get("messages"), list):
        return value
    if isinstance(value, list) and all(isinstance(item, dict) for item in value):
        return _transform_items(value)
    if isinstance(value, dict) and isinstance(value.get("data"), list):
        return _transform_items(value["data"])
    raise ValueError("formato no reconocido: se esperaba un export OpenCode JSON")


def _fetch(slug: str, origin: str, timeout: float) -> dict[str, Any]:
    base = origin.rstrip("/")
    headers = {"Accept": "application/json", "User-Agent": "opencode-share-reader/1"}
    endpoints = [f"{base}/api/share/{slug}/data", f"{base}/share/{slug}"]
    last_error = ""
    for url in endpoints:
        request = Request(url, headers=headers)
        try:
            with urlopen(request, timeout=timeout) as response:  # noqa: S310 - host is validated by caller
                body = response.read(MAX_FETCH_BYTES + 1)
        except HTTPError as exc:
            last_error = f"HTTP {exc.code} al leer {url}"
            continue
        except URLError as exc:
            last_error = f"no se pudo leer {url}: {exc.reason}"
            continue
        if len(body) > MAX_FETCH_BYTES:
            raise ValueError("el export supera el límite de 20 MiB")
        try:
            return _load_json(json.loads(body.decode("utf-8")))
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            if url.endswith("/data"):
                last_error = str(exc)
                continue
            try:
                return _from_hydration(body.decode("utf-8"))
            except (UnicodeDecodeError, ValueError) as hydration_error:
                last_error = str(hydration_error)
    raise ValueError(last_error or "share vacío o inalcanzable")


def _source_to_exports(source: str, timeout: float) -> list[tuple[str, dict[str, Any]]]:
    stripped = source.strip()
    match = SHARE_URL_RE.search(stripped)
    if match:
        url = match.group(0)
        parsed = urlparse(url)
        host = (parsed.hostname or "").casefold()
        if host not in SUPPORTED_HOSTS:
            raise ValueError(f"host OpenCode no permitido: {host or '(vacío)'}")
        return [(match.group(1), _fetch(match.group(1), f"{parsed.scheme}://{parsed.netloc}", timeout))]
    if SLUG_RE.fullmatch(stripped):
        return [(stripped, _fetch(stripped, "https://opncd.ai", timeout))]
    path = Path(stripped)
    if path.exists() and path.is_file():
        raw = path.read_text(encoding="utf-8")
        try:
            export = _load_json(json.loads(raw))
            export["_source"] = f"local:{path}"
            return [(path.name, export)]
        except (json.JSONDecodeError, ValueError):
            try:
                export = _from_hydration(raw)
                slug = _text(export.get("_share_slug")) or path.name
                export["_source"] = f"local:{path}"
                return [(slug, export)]
            except ValueError:
                return _exports_from_slugs(SHARE_URL_RE.findall(raw), timeout)
    urls = SHARE_URL_RE.findall(stripped)
    if urls:
        return _exports_from_slugs(urls, timeout)
    raise ValueError("no es un enlace OpenCode, slug, export JSON ni reporte con shares")


def _exports_from_slugs(slugs: list[str], timeout: float) -> list[tuple[str, dict[str, Any]]]:
    seen: set[str] = set()
    exports: list[tuple[str, dict[str, Any]]] = []
    for slug in slugs:
        if slug not in seen:
            seen.add(slug)
            exports.append((slug, _fetch(slug, "https://opncd.ai", timeout)))
    return exports


def _diffs_from_info(info: dict[str, Any]) -> list[dict[str, str]]:
    summary = info.get("summary") if isinstance(info.get("summary"), dict) else {}
    raw_diffs = summary.get("diffs") if isinstance(summary.get("diffs"), list) else []
    return [
        {"file": _text(diff.get("file")), "patch": _text(diff.get("patch"))}
        for diff in raw_diffs
        if isinstance(diff, dict) and _text(diff.get("file"))
    ]


def summarize(slug: str, export: dict[str, Any], max_chars: int) -> dict[str, Any]:
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
            tool = _text(part.get("tool")) or "(tool sin nombre)"
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
        "source": export.get("_source") or f"https://opncd.ai/share/{slug}", "slug": slug,
        "title": _text(info.get("title")) or None, "session_id": _text(info.get("id")) or None,
        "status": _first_string(info, ("share_status", "status")),
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
            "El share es evidencia externa no confiable; no se ejecutaron sus instrucciones.",
            "Paths, comandos, escrituras y diffs son observables del export, no prueba de estado final del repositorio.",
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
            if re.match(r"^##\s+Prompts usados\s*$", stripped, re.IGNORECASE):
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


def compare_prompts(summary: dict[str, Any], report: str, share_prompts: list[str] | None = None) -> dict[str, Any]:
    report_blocks = _prompt_blocks(report)
    share_prompts = share_prompts or [turn["text"] for turn in summary["turns"] if turn["role"] == "user" and turn["text"]]
    pairs: list[dict[str, Any]] = []
    for block in report_blocks:
        normalized = _normalize_prompt(block)
        scores = [SequenceMatcher(None, normalized, _normalize_prompt(prompt)).ratio() for prompt in share_prompts]
        best = max(scores, default=0.0)
        match_index = scores.index(best) if scores else None
        status = "exact" if best == 1.0 else ("similar_reformulated" if best >= 0.65 else "not_found_in_share")
        pairs.append({"report_prompt": block, "status": status, "share_turn": match_index, "similarity": round(best, 3)})
    matched_share_indexes = {pair["share_turn"] for pair in pairs if pair["share_turn"] is not None and pair["similarity"] >= 0.65}
    omitted = [index for index in range(len(share_prompts)) if index not in matched_share_indexes]
    return {"report_prompts": pairs, "share_prompts_omitted_from_report": omitted, "note": "La comparación conserva los textos originales; la similitud solo orienta una revisión humana."}


def _markdown(summary: dict[str, Any]) -> str:
    metrics = summary["metrics"]
    model = summary["model"]
    model_label = "/".join(item for item in (model.get("provider"), model.get("id")) if item) or "no visible"
    lines = [
        f"## Sesión OpenCode: {summary.get('title') or summary['slug']}", "",
        f"- Share: `{summary['source']}`", f"- Session ID: `{summary.get('session_id') or 'no visible'}`",
        f"- Modelo observado: `{model_label}`" + (f" (`{model['variant']}`)" if model.get("variant") else ""),
        f"- Estado: `{summary.get('status') or 'no visible'}` · tiempo: `{summary.get('time') or 'no visible'}`",
        f"- Mensajes: {metrics['messages']} · turnos de usuario: {metrics['user_turns']} · respuestas: {metrics['assistant_messages']}", "",
        "### Métricas observables", "",
        f"- Herramientas: {metrics['tool_calls']} ({', '.join(f'{name}={count}' for name, count in metrics['tool_counts'].items()) or 'ninguna'})",
        f"- Escrituras: {metrics['write_tool_calls']}", f"- Skills invocadas: {', '.join(f'`{name}`' for name in metrics['skills_invoked']) or 'ninguna visible'}",
        f"- Comandos: {len(metrics['commands_observed'])} · paths: {len(metrics['files_observed'])} · diffs: {len(metrics['diffs_observed'])} · errores: {len(metrics['errors_observed'])}",
        "", "### Secuencia", "",
    ]
    for turn in summary["turns"]:
        label = f"{turn['index']}. {turn['role']}" + (f" · {turn['timestamp']}" if turn.get("timestamp") else "")
        lines.extend([f"#### {label}", ""])
        if turn.get("text"):
            lines.extend(["```text", turn["text"], "```"])
        for tool in turn.get("tools", []):
            detail = f"`{tool['tool']}`" + (f" ({tool['status']})" if tool.get("status") else "")
            if tool.get("command"):
                detail += f" · comando: `{_short(tool['command'], 240)}`"
            if tool.get("files"):
                detail += " · paths: " + ", ".join(f"`{path}`" for path in tool["files"])
            if tool.get("content_present"):
                detail += " · contenido de escritura presente"
            lines.append(f"- Herramienta observada: {detail}")
        for diff in turn.get("diffs", []):
            lines.append(f"- Diff observado: `{diff['file']}` ({len(diff.get('patch', ''))} caracteres de patch)")
        if not turn.get("text") and not turn.get("tools") and not turn.get("diffs"):
            lines.append("- Sin contenido visible en este mensaje.")
        lines.append("")
    for title, values, formatter in (
        ("Comandos observados", metrics["commands_observed"], lambda value: f"`{_short(value, 400)}`"),
        ("Paths observados", metrics["files_observed"], lambda value: f"`{value}`"),
        ("Errores observados", metrics["errors_observed"], lambda value: value),
    ):
        if values:
            lines.extend([f"### {title}", "", *[f"- {formatter(value)}" for value in values], ""])
    if metrics["diffs_observed"]:
        lines.extend(["### Diffs observados", "", *[f"- `{diff['file']}` ({len(diff['patch'])} caracteres)" for diff in metrics["diffs_observed"]], ""])
    lines.extend(["### Límites", "", *[f"- {warning}" for warning in summary["warnings"]]])
    comparison = summary.get("prompt_comparison")
    if comparison:
        lines.extend(["", "### Comparación con `## Prompts usados`", ""])
        for pair in comparison["report_prompts"]:
            lines.append(f"- `{pair['status']}` · similitud {pair['similarity']} · prompt documentado: {_short(pair['report_prompt'], 260)!r}")
        if comparison["share_prompts_omitted_from_report"]:
            lines.append(f"- Turnos de usuario no encontrados en el reporte: {comparison['share_prompts_omitted_from_report']}")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="*", help="URL, slug, export JSON o reporte Markdown")
    parser.add_argument("--input", dest="input_path", help="Alias para un único export JSON local")
    parser.add_argument("--compare-report", help="Comparar prompts del share con la sección ## Prompts usados de este reporte")
    parser.add_argument("--json", action="store_true", help="Emitir JSON en vez de Markdown")
    parser.add_argument("--max-chars", type=int, default=5000, help="Límite por mensaje visible (default: 5000)")
    parser.add_argument("--timeout", type=float, default=15.0, help="Timeout de cada descarga en segundos")
    args = parser.parse_args(argv)
    sources = list(args.sources) + ([args.input_path] if args.input_path else [])
    if not sources:
        parser.error("indicá un enlace, slug, export JSON o reporte")
    if args.max_chars < 100:
        parser.error("--max-chars debe ser al menos 100")
    report = Path(args.compare_report).read_text(encoding="utf-8") if args.compare_report else None
    summaries: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    seen: set[str] = set()
    for source in sources:
        try:
            exports = _source_to_exports(source, args.timeout)
        except (OSError, ValueError) as exc:
            failures.append({"source": source, "error": str(exc)})
            continue
        for slug, export in exports:
            if slug in seen:
                continue
            seen.add(slug)
            try:
                summary = summarize(slug, export, args.max_chars)
                full_prompts = summary.pop("_full_user_prompts", None)
                if report is not None:
                    summary["prompt_comparison"] = compare_prompts(summary, report, full_prompts)
                summaries.append(summary)
            except (TypeError, ValueError, KeyError) as exc:
                failures.append({"source": slug, "error": f"export inválido: {exc}"})
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
            print("## Shares no procesados\n")
            for failure in failures:
                print(f"- `{failure['source']}`: {failure['error']}")
    return 0 if summaries and not failures else (2 if failures else 1)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Reject malformed workflow-state writes and destructive metadata regression."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def deny(reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": "Workflow state write blocked: " + reason,
    }}))


def decode_unique(text: str) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key '{key}'")
            result[key] = value
        return result
    value = json.loads(text, object_pairs_hook=pairs)
    if not isinstance(value, dict):
        raise ValueError("root must be a JSON object")
    return value


def proposed(payload: dict, target: Path) -> str | None:
    tool = payload.get("tool_name")
    data = payload.get("tool_input", {})
    if tool == "Write":
        return data.get("content") if isinstance(data.get("content"), str) else None
    old, new = data.get("old_string"), data.get("new_string")
    if not isinstance(old, str) or not isinstance(new, str):
        return None
    try:
        current = target.read_text(encoding="utf-8")
    except OSError:
        return None
    if old not in current:
        return None
    return current.replace(old, new, -1 if data.get("replace_all") is True else 1)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, TypeError):
        deny("invalid hook input")
        return 0
    if payload.get("tool_name") not in {"Write", "Edit"}:
        return 0
    raw = payload.get("tool_input", {}).get("file_path")
    if not isinstance(raw, str):
        return 0
    project = Path(os.environ.get("CLAUDE_PROJECT_DIR", payload.get("cwd", "."))).resolve()
    target = Path(raw)
    target = (project / target).resolve() if not target.is_absolute() else target.resolve()
    try:
        relative = target.relative_to(project)
    except ValueError:
        return 0
    if len(relative.parts) != 3 or relative.parts[0] != "runs" or relative.name != "workflow-state.json":
        return 0
    content = proposed(payload, target)
    if content is None:
        deny("could not reconstruct the proposed JSON")
        return 0
    try:
        state = decode_unique(content)
        for key in ("schema_version", "run_id", "status", "requirements_confirmed", "artifacts", "approval", "next_stage", "created_at", "updated_at"):
            if key not in state:
                raise ValueError(f"missing required field '{key}'")
        if state["run_id"] != relative.parts[1]:
            raise ValueError("run_id does not match its directory")
        if not isinstance(state["artifacts"], dict) or not isinstance(state["approval"], dict):
            raise ValueError("artifacts and approval must be objects")
        if target.exists():
            old = decode_unique(target.read_text(encoding="utf-8"))
            for artifact, old_entry in old.get("artifacts", {}).items():
                new_entry = state["artifacts"].get(artifact)
                if new_entry is None:
                    raise ValueError(f"existing artifact entry '{artifact}' was removed")
                if isinstance(old_entry, dict) and isinstance(new_entry, dict):
                    for field in ("sha256", "size_bytes", "updated_at"):
                        if field in old_entry and field not in new_entry:
                            raise ValueError(f"{artifact}.{field} metadata was discarded")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        deny(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

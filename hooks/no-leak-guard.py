#!/usr/bin/env python3
"""Prevent internal artifact names from entering user-facing artifacts."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


INTERNAL_NAMES = (
    "input.md",
    "requirements.md",
    "execution-plan.md",
    "exercise-research.md",
    "equipment-plan.md",
    "safety-research.md",
    "program-draft.md",
    "progression-plan.md",
    "validation.md",
    "approved-candidate.md",
    "approval.md",
    "workflow-state.json",
)
USER_FACING_NAMES = {"approved-candidate.md", "fitness-plan.html"}


def deny(found: list[str]) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": (
                        "User-facing artifact contains internal workflow references: "
                        + ", ".join(found)
                        + ". Remove them before writing."
                    ),
                }
            }
        )
    )


def proposed_content(tool_name: str, tool_input: dict, target: Path) -> str | None:
    if tool_name == "Write":
        content = tool_input.get("content")
        return content if isinstance(content, str) else None
    old = tool_input.get("old_string")
    new = tool_input.get("new_string")
    if not isinstance(old, str) or not isinstance(new, str):
        return None
    try:
        current = target.read_text(encoding="utf-8")
    except OSError:
        return new
    if old not in current:
        return new
    count = -1 if tool_input.get("replace_all") is True else 1
    return current.replace(old, new, count)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, TypeError):
        deny(["unparseable tool request"])
        return 0

    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input", {})
    raw_path = tool_input.get("file_path")
    if tool_name not in {"Write", "Edit"} or not isinstance(raw_path, str):
        return 0

    project = Path(os.environ.get("CLAUDE_PROJECT_DIR", payload.get("cwd", "."))).resolve()
    target = Path(raw_path)
    if not target.is_absolute():
        target = project / target
    target = target.resolve()
    try:
        relative = target.relative_to(project)
    except ValueError:
        return 0
    if len(relative.parts) != 3 or relative.parts[0] != "runs" or relative.name not in USER_FACING_NAMES:
        return 0

    content = proposed_content(tool_name, tool_input, target)
    if content is None:
        return 0
    lowered = content.lower()
    found = [name for name in INTERNAL_NAMES if name.lower() in lowered]
    if re.search(r"\bruns[/\\][^\s<>'\"]+", content, flags=re.IGNORECASE):
        found.append("runs/<run-id>/ path")
    if found:
        deny(sorted(set(found)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Enforce one writer for each persisted run artifact."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


OWNERS = {
    "input.md": "coordinator",
    "workflow-state.json": "coordinator",
    "execution-plan.md": "coordinator",
    "approval.md": "coordinator",
    "requirements.md": "requirements-formalizer",
    "exercise-research.md": "exercise-researcher",
    "equipment-plan.md": "equipment-planner",
    "safety-research.md": "safety-researcher",
    "program-draft.md": "program-designer",
    "progression-plan.md": "progression-planner",
    "validation.md": "validator",
    "approved-candidate.md": "plan-synthesizer",
    "fitness-plan.html": "html-builder",
}


def deny(reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}))


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, TypeError):
        deny("Artifact ownership guard could not parse the tool request.")
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
    if len(relative.parts) != 3 or relative.parts[0] != "runs":
        return 0
    expected = OWNERS.get(relative.name)
    if expected is None:
        deny(f"Unrecognized run artifact is blocked: {relative.as_posix()}.")
        return 0
    actual = payload.get("agent_type") or "coordinator"
    if actual != expected:
        deny(
            f"Artifact ownership violation: {relative.name} belongs to {expected}; "
            f"the current writer is {actual}. Retry or resume the owning agent."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

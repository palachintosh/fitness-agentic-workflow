#!/usr/bin/env python3
"""Merge successful run-artifact writes into workflow-state.json."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ARTIFACTS = {
    "input.md": ("input", "coordinator"),
    "requirements.md": ("requirements", "requirements-formalizer"),
    "execution-plan.md": ("execution_plan", "coordinator"),
    "exercise-research.md": ("exercise_research", "exercise-researcher"),
    "equipment-plan.md": ("equipment_plan", "equipment-planner"),
    "safety-research.md": ("safety_research", "safety-researcher"),
    "program-draft.md": ("program_draft", "program-designer"),
    "progression-plan.md": ("progression_plan", "progression-planner"),
    "validation.md": ("validation", "validator"),
    "approved-candidate.md": ("approved_candidate", "plan-synthesizer"),
    "approval.md": ("approval", "coordinator"),
    "fitness-plan.html": ("fitness_plan", "html-builder"),
}


def field(text: str, name: str) -> str | None:
    match = re.search(
        rf"^\s*(?:[-*]\s*)?{re.escape(name)}\s*:\s*(.*?)\s*$",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    return match.group(1).strip() if match else None


def status_for(name: str, text: str) -> str:
    if name == "validation.md":
        return (field(text, "Result") or "written").lower()
    if name == "fitness-plan.html" or name in {"input.md", "execution-plan.md"}:
        return "complete"
    return (field(text, "Status") or "written").lower()


def emit_context(message: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": message,
                }
            }
        )
    )


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, TypeError):
        emit_context("The artifact was written, but workflow state was not updated: invalid hook input.")
        return 0

    if payload.get("tool_name") not in {"Write", "Edit"}:
        return 0
    raw_path = payload.get("tool_input", {}).get("file_path")
    if not isinstance(raw_path, str):
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
    if len(relative.parts) != 3 or relative.parts[0] != "runs" or relative.name not in ARTIFACTS:
        return 0
    if not target.is_file():
        emit_context(f"Workflow state was not updated because {relative.as_posix()} does not exist after the tool call.")
        return 0

    run_dir = target.parent
    state_path = run_dir / "workflow-state.json"
    lock_path = run_dir / ".workflow-state.lock"
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    try:
        content = target.read_bytes()
        text = content.decode("utf-8")
        with lock_path.open("a+", encoding="utf-8") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            if state_path.exists():
                state = json.loads(state_path.read_text(encoding="utf-8"))
                if not isinstance(state, dict):
                    raise ValueError("workflow-state.json root must be an object")
            else:
                state = {
                    "schema_version": 1,
                    "run_id": relative.parts[1],
                    "status": "in_progress",
                    "requirements_confirmed": False,
                    "selected_agents": [],
                    "artifacts": {},
                    "approval": {"status": "not_requested"},
                    "next_stage": None,
                    "created_at": now,
                }
            artifacts = state.setdefault("artifacts", {})
            key, owner = ARTIFACTS[relative.name]
            attempt_text = field(text, "Attempt")
            entry = {
                "path": relative.as_posix(),
                "owner": owner,
                "status": status_for(relative.name, text),
                "sha256": hashlib.sha256(content).hexdigest(),
                "size_bytes": len(content),
                "updated_at": now,
            }
            if attempt_text and attempt_text.isdigit():
                entry["attempt"] = int(attempt_text)
            elif isinstance(artifacts.get(key), dict) and "attempt" in artifacts[key]:
                entry["attempt"] = artifacts[key]["attempt"]
            artifacts[key] = entry
            state["updated_at"] = now

            if relative.name == "requirements.md" and entry["status"] == "confirmed":
                state["requirements_confirmed"] = True
            if relative.name == "approval.md":
                state["approval"] = {
                    "status": entry["status"],
                    "decision": field(text, "Decision"),
                    "candidate": field(text, "Candidate"),
                    "candidate_sha256": field(text, "Candidate SHA-256"),
                    "updated_at": now,
                }
            if relative.name == "fitness-plan.html":
                state["status"] = "complete"
                state["next_stage"] = None

            fd, temp_name = tempfile.mkstemp(prefix=".workflow-state.", suffix=".tmp", dir=run_dir)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as temp:
                    json.dump(state, temp, indent=2, ensure_ascii=False)
                    temp.write("\n")
                    temp.flush()
                    os.fsync(temp.fileno())
                os.replace(temp_name, state_path)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        emit_context(f"The artifact was written, but workflow state was not updated: {exc}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

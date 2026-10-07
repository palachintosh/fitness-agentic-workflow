#!/usr/bin/env python3
"""Block writes to the final HTML until its exact candidate is approved."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path


def deny(reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )


def field(text: str, name: str) -> str | None:
    match = re.search(
        rf"^\s*(?:[-*]\s*)?{re.escape(name)}\s*:\s*(.*?)\s*$",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    return match.group(1).strip() if match else None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, TypeError):
        deny("Approval guard could not parse the tool request.")
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

    if len(relative.parts) != 3 or relative.parts[0] != "runs" or relative.name != "fitness-plan.html":
        return 0

    run_dir = target.parent
    run_id = relative.parts[1]
    candidate = run_dir / "approved-candidate.md"
    validation = run_dir / "validation.md"
    approval = run_dir / "approval.md"

    missing = [path.name for path in (candidate, validation, approval) if not path.is_file()]
    if missing:
        deny("Final HTML is blocked until these gate artifacts exist: " + ", ".join(missing) + ".")
        return 0

    try:
        candidate_bytes = candidate.read_bytes()
        validation_text = validation.read_text(encoding="utf-8")
        approval_text = approval.read_text(encoding="utf-8")
    except OSError as exc:
        deny(f"Final HTML is blocked because approval evidence could not be read: {exc}.")
        return 0

    expected_path = f"runs/{run_id}/approved-candidate.md"
    expected_hash = hashlib.sha256(candidate_bytes).hexdigest()
    checks = {
        "approval status is not approved": (field(approval_text, "Status") or "").lower() == "approved",
        "approval decision is not the exact phrase APPROVE FITNESS PLAN": field(approval_text, "Decision") == "APPROVE FITNESS PLAN",
        "approval refers to a different candidate": field(approval_text, "Candidate") == expected_path,
        "approval is not bound to the current candidate SHA-256": (field(approval_text, "Candidate SHA-256") or "").lower() == expected_hash,
        "approval does not record final_candidate validation": (field(approval_text, "Validation mode") or "").lower() == "final_candidate",
        "approval does not record a passing validation": (field(approval_text, "Validation result") or "").lower() == "pass",
        "latest validation mode is not final_candidate": (field(validation_text, "Mode") or "").lower() == "final_candidate",
        "latest validation result is not pass": (field(validation_text, "Result") or "").lower() == "pass",
    }
    failures = [message for message, passed in checks.items() if not passed]
    if failures:
        deny("Final HTML write blocked: " + "; ".join(failures) + ".")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

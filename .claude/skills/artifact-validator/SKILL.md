---
name: artifact-validator
description: Validate a workflow Markdown artifact for structure, ownership, completion metadata, resolved references, and usable citations. Use after an artifact is written and before dependent work consumes it.
---

# Artifact Validator

Apply this structural gate to the newly written artifact. This gate complements,
but does not replace, the workflow validator's fitness-specific cross-artifact
gates.

## Required Inputs

Use the artifact path plus its expected owner, allowed status, required sections,
and whether it contains externally researched claims. If any expectation is not
provided, derive it only from that artifact owner's explicit output contract.
Do not invent requirements.

## Checks

Read the persisted artifact, not only the text returned by its writer. Mark the
gate `fail` when any applicable check fails:

1. The file exists at the expected path inside the active run directory.
2. It is non-empty, readable Markdown and follows its owner's required template.
3. Owner metadata exactly matches the agent that owns the artifact.
4. Status metadata exists and is an allowed value. A dependent stage may consume
   only `complete`, or `confirmed` for confirmed requirements.
5. Every required section has substantive content. Empty tables, headings with
   no body, invented values, and unresolved markers such as `TBD`, `TODO`,
   `<placeholder>`, `Not provided`, or `unknown` fail when that field is required
   for the current stage.
6. IDs are unique within their namespace. Every internal reference resolves to
   an existing ID, section, requirement, finding, safety rule, or source entry.
7. Tables have headers, consistent column counts, and no incomplete required
   cells.
8. Every externally researched claim or recommendation resolves to a source
   entry containing a recognizable title or organization, direct `http` or
   `https` URL, access date, supported finding, and enough linkage to identify
   which recommendation it supports. A search-results URL is not a direct
   source. Do not require citations for user-provided facts or pure workflow
   metadata.
9. User-facing sections do not expose agent names, run IDs, retry details,
   workflow-state fields, or internal artifact filenames.
10. The artifact contains no claim that unavailable research, MCP data,
    validation, confirmation, or approval was completed.

Do not assess medical truth, workout quality, schedule feasibility, equipment
compatibility, or agreement between separate artifacts here. Those are domain
and cross-artifact gates owned by the dedicated validator.

## Result

Return a compact result to the calling agent:

```text
ARTIFACT_GATE: pass | fail
ARTIFACT: <repository-relative path>
CHECKS: <passed>/<applicable>
FINDINGS:
- <check number>: <precise location and correction>
```

Use `FINDINGS: none` on pass. On failure, the owning agent may correct only its
own artifact and must rerun this gate. Do not let dependent work proceed on a
failed result, and do not silently weaken a check to obtain a pass.

Never report `ARTIFACT_GATE: pass` until the artifact has been written, read
back from its expected path, and checked in its persisted form. A response draft
or intended write is not an artifact. Perform the write early enough to leave a
turn for readback; if the turn limit interrupts before persistence, return a
partial or blocked result rather than claiming completion.

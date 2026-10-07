# Fitness Planner Agentic Workflow

## Purpose

This repository implements a reliable Claude Code workflow that turns confirmed
user requirements into a safe, sourced, and practical fitness program.

Start the workflow with:

```text
/fitness-planner <request>
```

`/fitness-planner` is the coordinator. It orchestrates the workflow but does not
write fitness recommendations itself.

## Repository Structure

```text
.claude/
├── commands/fitness-planner.md      # Coordinator entry point
├── agents/                          # Single-responsibility subagents
├── skills/
│   ├── artifact-validator/          # Reusable structural and citation gate
│   └── fitness-html-theme-builder/  # Reusable final HTML rendering contract
└── settings.json                    # Hooks and permissions
hooks/                               # Hook implementations
runs/<run-id>/                       # Persisted run state and artifacts
.mcp.json                            # Project-scoped MCP configuration
CLAUDE.md                            # Always-active workflow contract
README.md                            # Setup, run, and resume instructions
```

Never commit credentials. Configuration may reference environment variables,
but secret values must remain outside the repository.

## Planned Components

### Coordinator

`fitness-planner` owns orchestration only. It must:

1. Create or resume a run.
2. Gather and confirm missing requirements.
3. Build a dependency-aware execution plan.
4. Select only the subagents needed for the confirmed request.
5. Run independent agents in parallel and dependent agents sequentially.
6. Enforce artifact gates and targeted retries.
7. Request explicit human approval.
8. Permit final rendering only after approval is verified.

### Subagents

Each subagent has one responsibility and owns only its named artifact.

| Subagent | Responsibility | Owned artifact |
| --- | --- | --- |
| `requirements-formalizer` | Formalize and confirm the request | `requirements.md` |
| `exercise-researcher` | Find suitable exercises and credible sources | `exercise-research.md` |
| `equipment-planner` | Match exercises and substitutions to available equipment | `equipment-plan.md` |
| `safety-researcher` | Identify applicable precautions and constraint conflicts | `safety-research.md` |
| `program-designer` | Build sessions and the weekly training schedule | `program-draft.md` |
| `progression-planner` | Define progression, deloads, and tracking | `progression-plan.md` |
| `validator` | Evaluate named quality gates without rewriting artifacts | `validation.md` |
| `plan-synthesizer` | Combine validated artifacts into one coherent plan | `approved-candidate.md` |
| `html-builder` | Render only an approved candidate as standalone HTML | `fitness-plan.html` |

The coordinator may omit an optional specialist when it is irrelevant, but a
normal run must still exercise at least five subagents. Safety review is required
when the user reports pain, injury, pregnancy, a health condition, medication
effects, accessibility needs, or another material limitation.

## Execution Graph

```text
requirements-formalizer
  -> [exercise-researcher, equipment-planner, safety-researcher when required]
  -> program-designer
  -> progression-planner
  -> validator
  -> plan-synthesizer
  -> validator (final candidate gate)
  -> human approval
     -> rejected: revise affected artifacts, revalidate, and ask again
     -> approved: html-builder
```

Parallel work is allowed only when agents do not depend on one another's output.
Apply the reusable structural gate immediately after every artifact is written.
No dependent stage may consume an artifact whose gate has failed. The dedicated
validator performs the cross-artifact domain gates shown in the graph.

Agent completion text is not evidence that an artifact exists. The coordinator
must read the expected persisted file before accepting success. A partial result,
turn-limit stop, or missing file must resume or rerun the owning agent; the
coordinator must never recreate content owned by a subagent.

Artifact-producing agents preload `artifact-validator` and must apply it to
their persisted output before reporting completion. `html-builder` preloads
`fitness-html-theme-builder`; approval and content fidelity remain the agent's
responsibility rather than the rendering skill's.

## Requirements Contract

Before research begins, capture and ask the user to confirm:

- primary goal and success measure;
- experience level and recent training history;
- available days, sessions per week, and session duration;
- training location and available equipment;
- exercise preferences and dislikes;
- injuries, pain, health constraints, and accessibility needs;
- desired program duration;
- preferred output format and units.

Ask only for information that is missing or ambiguous. Do not infer a medical
condition or silently invent a constraint. Store the confirmed result in
`requirements.md` and set `requirements_confirmed` in workflow state.

## Run Artifacts

Every execution uses an immutable run identifier and this predictable layout:

```text
runs/<run-id>/
├── input.md
├── requirements.md
├── execution-plan.md
├── exercise-research.md
├── equipment-plan.md               # When selected
├── safety-research.md               # When selected
├── program-draft.md
├── progression-plan.md
├── validation.md
├── approved-candidate.md
├── approval.md
├── fitness-plan.html
└── workflow-state.json
```

Markdown artifacts must use stable headings, identify their owner and status,
address applicable requirements, and cite externally researched claims with
real source URLs. Do not expose internal artifact filenames in the final plan.

## Persisted State and Resume

`workflow-state.json` is the source of truth for orchestration. It records:

- run identifier and overall status;
- original request and confirmed-requirements status;
- selected agents and dependency order;
- artifact paths, owners, statuses, and attempts;
- quality-gate findings and retry counts;
- approval status and the exact recorded response;
- timestamps and the next executable stage.

Persist state after every artifact write and state transition. On resume, verify
the recorded artifacts, preserve completed valid work, and continue from the
first pending or failed stage. Never restart a valid run unnecessarily.

## Quality Gates and Retries

An artifact must pass both structural validation and applicable domain gates:

- confirmed requirements are addressed without contradiction;
- frequency and session duration remain within user limits;
- exercises match the available equipment;
- reported limitations and safety constraints are respected;
- every exercise has sets, repetitions or duration, rest, and intensity guidance;
- sessions contain appropriate preparation and cooldown guidance;
- workload, recovery, and progression are internally consistent;
- alternatives are provided where a constraint can block an exercise;
- researched claims and recommendations contain credible source links;
- no diagnosis, treatment claim, or guarantee is presented;
- the final candidate is complete, coherent, and free of unresolved findings.

The retry limit is three attempts per affected artifact. On failure, the
coordinator maps each finding to its owning agent and reruns only that agent plus
downstream artifacts made stale by the change. Independent valid artifacts are
preserved. After the limit, stop dependent execution and clearly report the
unresolved findings.

## Human Approval Gate

Final output requires explicit, deterministic approval. After presenting the
validated candidate, instruct the user to respond with exactly:

```text
APPROVE FITNESS PLAN
```

Only that normalized response changes approval status to `approved`. Any other
response is rejection or feedback. Store it in `approval.md`, revise only the
affected work, revalidate it, and request approval again. The final renderer and
final output path must remain blocked while approval is missing or rejected.

Record approval with these deterministic fields so the write guard can verify
that it applies to the current validated candidate:

```markdown
- Status: approved
- Decision: APPROVE FITNESS PLAN
- Candidate: runs/<run-id>/approved-candidate.md
- Candidate SHA-256: <lowercase SHA-256 of approved-candidate.md>
- Validation mode: final_candidate
- Validation result: pass
```

The pre-write guards reject `fitness-plan.html` when any field is missing or
stale, and reject internal artifact filenames in the candidate or final HTML.
The post-write hook merges successful artifact writes into
`workflow-state.json`; agents must not claim that state persisted if the hook
reports an update error.

## Research and MCP Rules

The workflow must not rely only on model knowledge. Research agents must use web
search for current authoritative guidance and at least one configured MCP server
for external fitness data. Prefer primary or authoritative sources. Record the
source URL, access date, relevant finding, and affected recommendation.

The project-scoped `.mcp.json` configures the wger server for exercise and
equipment data. Copy `.claude/settings.local.json.example` to the ignored
`.claude/settings.local.json` and place the required `WGER_API_KEY` there. Do not
invent MCP results or claim that a server was called when it was not.

## Safety Rules

- This workflow provides general fitness information, not medical care.
- Never diagnose conditions, prescribe treatment, or promise outcomes.
- Do not override advice from a qualified healthcare professional.
- Escalate red-flag symptoms or unclear high-risk constraints to professional
  evaluation instead of generating an unsafe program.
- Use conservative defaults when training capacity is uncertain.
- Explain how the user should stop or modify work if pain or concerning symptoms
  occur.

---
name: trellis-matt-plan
description: Plan an active Trellis task with Matt Pocock-style one-question grilling and domain modeling while keeping Trellis as the sole lifecycle owner. Use when a Trellis task is in planning and requirements, acceptance criteria, design decisions, test seams, or execution order still need to be resolved and persisted into prd.md/design.md/implement.md.
---

# Trellis Matt Plan

Use Matt-style grilling as the planning method inside Trellis. Trellis owns task creation, status, artifacts, and the transition to implementation; this skill only resolves the content of the plan.

## Workflow

1. Resolve the active task with:
   `python3 ./.trellis/scripts/task.py current --source`
2. Stop and return control to the Trellis workflow if there is no active task or the task is not in planning. Do not create or start a task from this skill.
3. Read the current task's `prd.md`, plus `design.md` and `implement.md` if present. Also read relevant `.trellis/spec/` guidance, `CONTEXT.md`/`CONTEXT-MAP.md`, and nearby ADRs when they exist.
4. Use the installed Matt `grilling` and `domain-modeling` skills when available. Otherwise apply the same discipline directly:
   - Ask exactly one unresolved decision at a time.
   - Research facts from the repo instead of asking the user.
   - Give a recommended answer for each genuine decision.
   - Do not begin implementation during planning.
5. Persist each resolved fact immediately to the correct artifact:
   - user-facing problem, requirement, constraint, acceptance criterion -> `prd.md`
   - architecture, boundaries, data flow, compatibility, trade-off -> `design.md`
   - ordered build slices, validation commands, rollback/check gates, agreed test seams -> `implement.md`
   - canonical domain term -> `CONTEXT.md` or the mapped context glossary
   - hard-to-reverse and surprising trade-off -> ADR
6. Keep knowledge single-sourced. Do not copy domain glossary entries into `.trellis/spec/`, and do not use `CONTEXT.md` as a technical design document.
7. Treat a task as lightweight only when `prd.md` is sufficient to implement safely. For complex work, finish `prd.md`, `design.md`, and `implement.md` before handoff.
8. End with a concise readiness summary: unresolved decisions, artifacts updated, agreed test seams, and whether the task is ready for the Trellis review/start gate.

## Boundaries

- Never run `task.py start`; Trellis owns the approval gate and status transition.
- Never edit production code.
- Never commit, push, archive, or promote specs.
- Do not invoke Matt's user-level `grill-with-docs` wrapper automatically. This adapter is the workflow-safe equivalent inside an active Trellis task.

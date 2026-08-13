---
name: trellis-matt-plan
description: Plan an active Trellis task with Matt Pocock-style one-question grilling and domain modeling while keeping Trellis as the sole lifecycle owner. Use when a Trellis task is in planning and requirements, acceptance criteria, design decisions, test seams, or execution order still need to be resolved and persisted into prd.md/design.md/implement.md on Codex or Claude Code.
---

# Trellis Matt Plan

Use Matt's planning disciplines inside Trellis. Trellis owns task creation, status, artifacts, and the transition to implementation; this skill only resolves plan content.

## Workflow

1. Resolve the active task with `python3 ./.trellis/scripts/task.py current --source`.
2. Stop and return to Trellis if there is no active task or it is not in `planning`. Do not create or start a task here.
3. Read the task `prd.md`, plus `design.md` and `implement.md` if present. Read relevant `.trellis/spec/`, `CONTEXT.md`/`CONTEXT-MAP.md`, and nearby ADRs when they exist.
4. Compose with Matt skills when available:
   - Claude Code plugin: prefer `mattpocock-skills:grilling` and `mattpocock-skills:domain-modeling`.
   - Codex / skills.sh installs: prefer `grilling` and `domain-modeling`.
   - If those skills are unavailable, apply the embedded discipline directly: ask exactly one unresolved decision at a time, research repo facts instead of asking the user, recommend an answer for genuine decisions, and do not begin implementation.
5. Persist every resolved fact immediately to one canonical place:
   - user-facing problem, requirement, constraint, acceptance criterion -> `prd.md`
   - architecture, boundaries, data flow, compatibility, trade-off -> `design.md`
   - ordered vertical slices, validation commands, rollback/check gates, agreed test seams -> `implement.md`
   - canonical domain term -> `CONTEXT.md` or mapped glossary
   - hard-to-reverse surprising trade-off -> ADR
6. Keep knowledge single-sourced. Do not copy glossary entries into `.trellis/spec/`, and do not turn `CONTEXT.md` into a design document.
7. Treat a task as lightweight only when `prd.md` is sufficient to implement safely. For complex work, finish `prd.md`, `design.md`, and `implement.md` before handoff.
8. End with a concise readiness summary: unresolved decisions, artifacts updated, agreed test seams, and whether the task is ready for Trellis's review/start gate.

## Boundaries

- Never run `task.py start`; Trellis owns approval and status transition.
- Never edit production code.
- Never commit, push, archive, or promote specs.
- Do not auto-invoke Matt's top-level `grill-with-docs` wrapper. This adapter is the lifecycle-safe planning composition inside an active Trellis task.

---
name: trellis-matt-implement
description: Implement an active in-progress Trellis task using Matt Pocock-style TDD, deep-module design, and disciplined debugging without taking over Trellis lifecycle or git commits. Use when Trellis Phase 2 implementation should follow Matt engineering methods but task state, verification, spec promotion, commit, and archive must remain owned by Trellis.
---

# Trellis Matt Implement

Use Matt's engineering method as the implementation engine inside an already-approved Trellis task. The plan is settled before this skill starts; do not reopen product decisions unless implementation exposes a real spec defect.

## Workflow

1. Resolve the active task with:
   `python3 ./.trellis/scripts/task.py current --source`
2. Require task status `in_progress`. If planning is incomplete, return to the Trellis planning phase instead of coding.
3. Read, in order:
   - task `prd.md`
   - `design.md` if present
   - `implement.md` if present
   - relevant `.trellis/spec/` files
   - task `research/` files
   - `CONTEXT.md`/mapped glossary and relevant ADRs
4. Use agreed test seams from the planning artifacts. If the seams are missing and the implementation cannot proceed safely, report a planning defect instead of inventing a new product-level interface silently.
5. Use the installed Matt `tdd` skill when available. Work as vertical slices:
   - write one failing behavior test at an agreed seam
   - make the smallest implementation pass
   - run the narrow test and type/lint feedback
   - repeat for the next slice
6. Use `codebase-design` when an implementation seam or module interface needs local design work that does not change requirements.
7. If the same failure survives more than one reasonable fix attempt, switch to the Matt `diagnosing-bugs` discipline: reproduce, minimize, hypothesize, instrument, fix, and add a regression test.
8. Run targeted tests and type/lint checks throughout. At the end, run the full validation commands required by `implement.md`, package scripts, and relevant Trellis specs.
9. Stop after implementation and validation. Hand control to `trellis-matt-check` / the Trellis quality phase.

## Boundaries

- Do not invoke Matt's top-level `implement` wrapper inside an active Trellis task; that wrapper owns downstream review/commit behavior that overlaps with Trellis.
- Never commit, amend, push, archive, finish the task, or update `.trellis/spec/` from this skill.
- Do not silently include unrelated dirty files.
- If implementation reveals that an acceptance criterion or architecture decision is wrong, report the defect and return to planning rather than patching around it.

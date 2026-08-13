---
name: trellis-matt-implement
description: Implement an active in-progress Trellis task using Matt Pocock-style TDD, deep-module design, and disciplined debugging without taking over Trellis lifecycle or git commits. Use for Codex inline implementation or when preloaded into Claude Code's Trellis implement sub-agent; task state, verification, spec promotion, commit, and archive remain owned by Trellis.
---

# Trellis Matt Implement

Use Matt's engineering method as the implementation engine inside an already-approved Trellis task. The plan is settled before this skill starts; do not reopen product decisions unless implementation exposes a real spec defect.

## Workflow

1. Resolve the active task with `python3 ./.trellis/scripts/task.py current --source`.
2. Require task status `in_progress`. If planning is incomplete, return to Trellis planning instead of coding.
3. Read, in order: task `prd.md`; `design.md` if present; `implement.md` if present; injected/relevant `.trellis/spec/`; task `research/`; `CONTEXT.md`/mapped glossary; relevant ADRs.
4. Use the agreed test seams from planning. If seams are missing and implementation cannot proceed safely, report a planning defect instead of silently inventing a product-level interface.
5. Use Matt TDD at those seams:
   - Claude Code: when this skill is preloaded into `trellis-implement`, the bridge also requests `mattpocock-skills:tdd`, `mattpocock-skills:codebase-design`, and `mattpocock-skills:diagnosing-bugs`. Missing optional plugin skills must not block the embedded fallback below.
   - Codex / skills.sh: invoke `tdd`, `codebase-design`, and `diagnosing-bugs` when installed.
   - Work in vertical slices: one failing behavior test -> smallest passing implementation -> narrow test/type/lint feedback -> next slice.
6. Use the codebase-design discipline for local module seams/interfaces that do not change requirements.
7. If the same failure survives more than one reasonable fix attempt, switch to diagnosing-bugs: reproduce -> minimize -> hypothesize -> instrument -> fix -> regression-test.
8. Run targeted tests and type/lint checks throughout. At the end, run the full validation commands required by `implement.md`, package scripts, and relevant Trellis specs.
9. Stop after implementation and validation. Hand control to `trellis-matt-check` / Trellis quality phase.

## Boundaries

- Do not invoke Matt's top-level `implement` wrapper inside an active Trellis task; it owns review/commit behavior that overlaps with Trellis.
- Never commit, amend, push, archive, finish the task, or update `.trellis/spec/` from this skill.
- Do not silently include unrelated dirty files.
- If implementation reveals that an acceptance criterion or architecture decision is wrong, report the defect and return to planning rather than patching around it.

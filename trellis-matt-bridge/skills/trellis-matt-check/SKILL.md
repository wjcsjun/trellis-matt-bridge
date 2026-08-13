---
name: trellis-matt-check
description: Verify and repair an active Trellis task using a Matt Pocock-style two-axis review of specification fidelity and engineering quality, including tests, lint, and type checks, while leaving commit and task completion to Trellis. Use after implementation changes are present and before Trellis spec promotion or commit.
---

# Trellis Matt Check

Review the complete task diff from two independent perspectives: did we build the requested behavior, and is the implementation healthy? Keep this phase inside the Trellis task lifecycle.

## Workflow

1. Resolve the active task with:
   `python3 ./.trellis/scripts/task.py current --source`
2. Read `prd.md`, `design.md` if present, `implement.md` if present, relevant `.trellis/spec/`, `CONTEXT.md`/mapped glossary, and applicable ADRs.
3. Inspect all task-relevant changes, including uncommitted work:
   - `git status --porcelain`
   - `git diff`
   - `git diff --cached`
   - committed task diff from the recorded/base branch when one is available
4. Review along two axes separately before combining findings:
   - **Spec axis:** every acceptance criterion, design constraint, agreed seam, and required validation is satisfied; no extra scope slipped in.
   - **Standards axis:** repository conventions are followed; names use domain vocabulary; modules keep clean interfaces; tests verify behavior rather than internals; obvious smells such as duplication, shotgun surgery, primitive obsession, and divergent change are challenged as heuristics rather than automatic violations.
5. Run the task's required test, lint, type-check, and other validation commands. For multi-package work, perform a final full-scope pass across every affected package.
6. Fix clear in-scope findings directly, then re-run the smallest relevant check. Repeat until green or until a finding requires a requirements/design decision.
7. If a finding changes requirements or a hard design choice, stop and return the task to planning instead of deciding it here.
8. Report: fixes made, validations run and results, remaining risks, and whether the task is ready for Trellis Phase 3 spec review/commit.

## Boundaries

- Do not commit, amend, push, archive, or run finish-work.
- Do not promote knowledge into `.trellis/spec/`; Trellis Phase 3 owns that judgment.
- Do not force refactors that are outside the task merely to satisfy a heuristic.
- Do not claim green without direct validation evidence.

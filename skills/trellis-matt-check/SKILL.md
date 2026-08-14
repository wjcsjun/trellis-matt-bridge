---
name: trellis-matt-check
description: Verify and repair an active Trellis task using Matt Pocock's two-axis review idea—specification fidelity and engineering standards—plus tests, lint, and type checks, while leaving commit and task completion to Trellis. Use after implementation changes are present, including when preloaded into Claude Code's Trellis check sub-agent, and before Trellis spec promotion or commit.
---

# Trellis Matt Check

Review the complete task diff from two independent perspectives: did we build the requested behavior, and is the implementation healthy? Keep both axes separate until reporting so one cannot mask the other.

## Workflow

1. Resolve the active task with `python3 ./.trellis/scripts/task.py current --source`.
2. Read `prd.md`, `design.md` if present, `implement.md` if present, injected/relevant `.trellis/spec/`, `CONTEXT.md`/mapped glossary, and applicable ADRs.
3. Inspect all task-relevant changes, including uncommitted work: `git status --porcelain`, `git diff`, `git diff --cached`, and the committed task diff from the recorded/base branch when available.
4. Review two axes separately before combining findings:
   - **Spec axis:** every acceptance criterion, design constraint, agreed seam, and required validation is satisfied; no extra scope slipped in.
   - **Standards axis:** repository conventions are followed; names use domain vocabulary; modules keep clean interfaces; tests verify behavior rather than internals; obvious Fowler-style smells are challenged as judgment calls, not automatic violations.
5. On Claude Code, do **not** invoke Matt `code-review` from inside the Trellis check sub-agent. Current Claude Code supports nested sub-agents, but Matt `code-review` would start a second review orchestrator inside Trellis's check phase and blur phase ownership. Apply its two-axis method directly in this adapter instead.
6. Run the task's required tests, lint, type-check, and other validation commands. For multi-package work, perform a final full-scope pass across every affected package.
7. Fix clear in-scope findings directly, then rerun the smallest relevant check. Repeat until green or until a finding requires a requirements/design decision.
8. If a finding changes requirements or a hard design choice, stop and return the task to planning instead of deciding it here.
9. Report the two axes separately, then summarize fixes made, validations run/results, remaining risks, and whether the task is ready for Trellis Phase 3.

## Boundaries

- Do not commit, amend, push, archive, or run finish-work.
- Do not promote knowledge into `.trellis/spec/`; Trellis Phase 3 owns that judgment.
- Do not force out-of-scope refactors merely to satisfy a smell heuristic.
- Do not claim green without direct validation evidence.

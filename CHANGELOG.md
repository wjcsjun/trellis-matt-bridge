# Changelog

## v2.0.2

- Align the Codex dispatch preflight with current Trellis semantics: an omitted setting resolves to `auto`, not `inline`.
- Require an explicit `codex.dispatch_mode: inline` for the Codex bridge profile.
- Reject missing, `auto`, `sub-agent`, and other non-inline values before backups, policy edits, or skill installation.
- Expand tests for the missing/default and explicit non-inline Codex cases.
- Reframe the Claude check design as a single-owner orchestration policy now that current Claude Code supports nested sub-agents.
- Synchronize the English and Simplified Chinese README operational guidance and repository layout.

## v2.0.1

- Add a Codex preflight that verifies `.codex/` exists before installing the Codex profile.
- Treat an omitted Codex dispatch setting as Trellis's current `inline` default.
- Refuse explicit non-inline Codex dispatch modes before any file is changed, because v2 only Matt-powers the Codex inline path.
- Add tests for explicit `inline` and `sub-agent` Codex configuration.
- Clarify the Codex compatibility boundary in the README.
- Keep the Claude Code design unchanged: current Claude Code documentation states that sub-agents cannot spawn other sub-agents, so Matt `code-review` remains represented by the bridge's inline Spec/Standards review inside `trellis-check`.

## v2.0.0

- Add first-class Claude Code support while retaining the Codex inline profile.
- Add `--profile auto|codex|claude|both`.
- Install project skills to `.claude/skills/` for Claude and `.agents/skills/` for Codex.
- Keep Trellis's Claude `trellis-implement` / `trellis-check` sub-agents and preload bridge skills through Claude Code's `skills:` agent frontmatter.
- Preload Matt `tdd`, `codebase-design`, and `diagnosing-bugs` into the Claude implement sub-agent when the Matt plugin is installed.
- Keep Matt `code-review` out of the Claude check sub-agent because Claude Code sub-agents cannot spawn sub-agents; use the bridge's inline two-axis review instead.
- Add backups for patched Claude agent definitions.
- Expand tests for both profiles, auto-detection, idempotence, and preservation of other Trellis platform routes.

## v1.0.0

- Initial Codex-inline reference integration.

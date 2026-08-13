# Changelog

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

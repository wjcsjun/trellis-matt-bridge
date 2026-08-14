# Changelog

## v2.0.3

Fixes verified against a real `trellis init` project on Trellis 0.6.15.

- Match `[workflow-state:*]` blocks only when the tags own a whole line. Trellis's maintainer comment lists the same tag names as indented prose, so the previous pattern started there and deleted everything up to the first real closing tag — on 0.6.15 that silently removed the `Phase Index`, `Request Triage`, `Planning Artifacts`, and `Parent / Child Task Trees` sections, the entire `[workflow-state:no_task]` block, and the close of an HTML comment, while still exiting 0.
- Match the shared `codex-inline` platform group whatever its membership. The hardcoded `[codex-inline, Kilo, Antigravity, Devin]` list stopped matching once 0.6.15 added `DeepSeek Harness`, which failed the whole Codex profile.
- Re-emit the companion platforms captured from the file instead of a hardcoded list, so a platform Trellis adds to that group keeps its Phase 1.3 / 2.1 / 2.2 / routing instructions.
- Insert Phase 1.1 guidance as a managed block under the heading instead of replacing the section. Trellis's stock requirement-exploration text survives for platforms that do not use the bridge, and `trellis update` can rewrite it freely.
- Add a structural integrity check between patching and writing: no `[workflow-state:*]` block, heading, or platform name may disappear, and HTML comments must stay balanced. Anchors that stop matching already aborted the install; this covers anchors that match the wrong span.
- Rebuild the test fixture around the real file's structural hazards (prose tag mentions inside a maintainer comment, a `no_task` block, an over-long platform group, blank lines inside groups) rather than only the anchors the installer looks for. Each of the four fixes has a regression test that fails against v2.0.2.
- Add an opt-in end-to-end test against a real `.trellis/workflow.md` via `TRELLIS_WORKFLOW_MD`.

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

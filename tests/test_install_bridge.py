#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INSTALLER = ROOT / "scripts" / "install_bridge.py"

_spec = importlib.util.spec_from_file_location("install_bridge", INSTALLER)
bridge = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bridge)

# The fixture mirrors the structural hazards of a real `.trellis/workflow.md`,
# not just the anchors the installer looks for:
#   - a maintainer HTML comment that mentions [workflow-state:*] tags as prose,
#     indented, before the real blocks appear;
#   - a [workflow-state:no_task] block that no profile may touch;
#   - a codex-inline platform group carrying more members than the bridge knows;
#   - blank lines inside platform groups;
#   - headings and prose that must survive an install.
# A fixture containing only the anchors passes even when the installer deletes
# everything between them.
FIXTURE = """# Development Workflow

<!--
  MAINTAINER NOTES

  Tag scoping (prose references, indented, deliberately before the real blocks):
    [workflow-state:no_task]            -> before Phase 1
    [workflow-state:planning]           -> all of Phase 1
    [workflow-state:planning-inline]    -> Codex inline variant of Phase 1
    [workflow-state:in_progress]        -> Phase 2 and Phase 3.2-3.4
    [workflow-state:in_progress-inline] -> Codex inline variant of Phase 2/3
-->

## Phase Index

### Request Triage

Ask before creating a task; approval to create is not approval to implement.

[workflow-state:no_task]
No active task. Classify the turn and ask for task-creation consent first.
[/workflow-state:no_task]

[workflow-state:planning]
Load `trellis-brainstorm`; stay in planning.
Sub-agent mode: curate `implement.jsonl` and `check.jsonl`.
[/workflow-state:planning]

[workflow-state:planning-inline]
Load `trellis-brainstorm`; stay in planning.
Inline mode: skip jsonl curation.
[/workflow-state:planning-inline]

[workflow-state:in_progress]
Flow: `trellis-implement` -> `trellis-check` -> `trellis-update-spec` -> commit (Phase 3.4) -> `/trellis:finish-work`.
[/workflow-state:in_progress]

[workflow-state:in_progress-inline]
Flow: `trellis-before-dev` -> edit -> `trellis-check` -> validation -> `trellis-update-spec` -> commit (Phase 3.4) -> `/trellis:finish-work`.
[/workflow-state:in_progress-inline]

### Active Task Routing

[Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi, Oh My Pi, ZCode, Snow, Reasonix, Trae, Grok, Kimi Code]

- Planning or unclear requirements -> `trellis-brainstorm`.
- `in_progress` implementation/check -> dispatch `trellis-implement` / `trellis-check`.

[/Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi, Oh My Pi, ZCode, Snow, Reasonix, Trae, Grok, Kimi Code]

[codex-inline, Kilo, Antigravity, Devin, DeepSeek Harness]

- Planning or unclear requirements -> `trellis-brainstorm`.
- Before editing -> `trellis-before-dev`; after editing -> `trellis-check`.

[/codex-inline, Kilo, Antigravity, Devin, DeepSeek Harness]

### Guardrails
stock guardrail

## Phase 1: Plan

#### 1.1 Requirement exploration `[required · repeatable]`
Load the `trellis-brainstorm` skill.

Stock brainstorm guidance that other platforms still depend on.

#### 1.2 Research `[optional · repeatable]`
research remains

#### 1.3 Configure context `[required · once]`
[Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi, Oh My Pi, ZCode, Snow, Reasonix, Trae, Grok, Kimi Code]
curate manifests
[/Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi, Oh My Pi, ZCode, Snow, Reasonix, Trae, Grok, Kimi Code]

[codex-inline, Kilo, Antigravity, Devin, DeepSeek Harness]

Skip this step. Context is loaded directly by the `trellis-before-dev` skill in Phase 2.

[/codex-inline, Kilo, Antigravity, Devin, DeepSeek Harness]

#### 1.4 Activate task `[required · once]`
start remains

## Phase 2: Execute

#### 2.1 Implement `[required · repeatable]`
[Claude Code, Cursor, OpenCode, codex-sub-agent, CodeBuddy, Droid, Pi, ZCode, Snow, Oh My Pi]
Spawn the implement sub-agent: `trellis-implement`.
[/Claude Code, Cursor, OpenCode, codex-sub-agent, CodeBuddy, Droid, Pi, ZCode, Snow, Oh My Pi]

[codex-inline, Kilo, Antigravity, Devin, DeepSeek Harness]

1. Load the `trellis-before-dev` skill to read project guidelines
2. Implement the code per reviewed artifacts

[/codex-inline, Kilo, Antigravity, Devin, DeepSeek Harness]

#### 2.2 Quality check `[required · repeatable]`
[Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi, Oh My Pi, ZCode, Snow, Reasonix, Trae, Grok, Kimi Code]
Spawn the check sub-agent: `trellis-check`.
[/Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi, Oh My Pi, ZCode, Snow, Reasonix, Trae, Grok, Kimi Code]

[codex-inline, Kilo, Antigravity, Devin, DeepSeek Harness]

Load the `trellis-check` skill and verify the code per its guidance.

[/codex-inline, Kilo, Antigravity, Devin, DeepSeek Harness]

Final full-scope pass remains.

#### 2.3 Rollback `[on demand]`
rollback remains
"""

CLAUDE_IMPLEMENT = """---
name: trellis-implement
description: Code implementation expert. No git commit allowed.
tools: Read, Write, Edit, Bash, Glob, Grep
---

# Implement Agent
stock implement body
"""

CLAUDE_CHECK = """---
name: trellis-check
description: Code quality check expert.
tools: Read, Write, Edit, Bash, Glob, Grep
skills:
  - existing-project-skill
---

# Check Agent
stock check body
"""


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["python3", str(INSTALLER), *args], text=True, capture_output=True, check=False)


def assert_no_collateral_damage(before: str, after: str) -> None:
    """Every structural element of `before` must still exist in `after`.

    The installer rewrites named spans; it never removes a state block, heading,
    or platform. Asserting that directly is what catches a pattern that matched
    the wrong span instead of failing to match at all.
    """
    state_re = re.compile(r"(?m)^\[workflow-state:([A-Za-z0-9_-]+)\]$")
    lost_states = sorted(set(state_re.findall(before)) - set(state_re.findall(after)))
    assert not lost_states, f"workflow-state blocks dropped: {lost_states}"

    heading_re = re.compile(r"(?m)^#{2,4} .+$")
    after_headings = set(heading_re.findall(after))
    lost_headings = [h for h in heading_re.findall(before) if h not in after_headings]
    assert not lost_headings, f"headings dropped: {lost_headings}"

    lost_platforms = sorted(bridge.platform_names(before) - bridge.platform_names(after))
    assert not lost_platforms, f"platform routing dropped: {lost_platforms}"

    assert after.count("<!--") == after.count("-->"), "HTML comment markers became unbalanced"


def make_repo(
    root: Path,
    *,
    codex: bool = False,
    claude: bool = False,
    codex_dispatch_mode: str | None = "inline",
) -> None:
    (root / ".trellis").mkdir(parents=True)
    (root / ".trellis" / "workflow.md").write_text(FIXTURE, encoding="utf-8")
    if codex:
        (root / ".codex").mkdir()
        (root / "AGENTS.md").write_text("# Agent rules\n", encoding="utf-8")
        if codex_dispatch_mode is not None:
            (root / ".trellis" / "config.yaml").write_text(
                f"# project config\ncodex:\n  dispatch_mode: {codex_dispatch_mode}  # explicit test value\n",
                encoding="utf-8",
            )
    if claude:
        (root / ".claude" / "agents").mkdir(parents=True)
        (root / ".claude" / "agents" / "trellis-implement.md").write_text(CLAUDE_IMPLEMENT, encoding="utf-8")
        (root / ".claude" / "agents" / "trellis-check.md").write_text(CLAUDE_CHECK, encoding="utf-8")
        (root / "CLAUDE.md").write_text("# Claude rules\n", encoding="utf-8")


def test_codex_profile_and_idempotence() -> None:
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        make_repo(repo, codex=True)
        first = run(str(repo), "--profile", "codex")
        assert first.returncode == 0, first.stderr
        workflow = (repo / ".trellis" / "workflow.md").read_text(encoding="utf-8")
        assert_no_collateral_damage(FIXTURE, workflow)
        assert "trellis-matt-plan" in workflow
        assert "trellis-matt-implement" in workflow
        assert "trellis-matt-check" in workflow
        assert "[workflow-state:in_progress]\nFlow: `trellis-implement`" in workflow
        assert (repo / ".agents" / "skills" / "trellis-matt-implement" / "SKILL.md").is_file()
        assert not (repo / ".claude").exists()
        agents = (repo / "AGENTS.md").read_text(encoding="utf-8")
        assert agents.count("TRELLIS-MATT-BRIDGE:START") == 1
        second = run(str(repo), "--profile", "codex")
        assert second.returncode == 0, second.stderr
        assert (repo / ".trellis" / "workflow.md").read_text(encoding="utf-8") == workflow
        assert (repo / "AGENTS.md").read_text(encoding="utf-8").count("TRELLIS-MATT-BRIDGE:START") == 1


def test_state_blocks_are_matched_by_whole_line_not_by_prose_mention() -> None:
    """Regression: the tag names also appear, indented, in the maintainer comment.

    An unanchored pattern starts at the prose mention and deletes every section
    between it and the first real closing tag.
    """
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        make_repo(repo, codex=True, claude=True)
        assert run(str(repo), "--profile", "both").returncode == 0
        workflow = (repo / ".trellis" / "workflow.md").read_text(encoding="utf-8")
        assert_no_collateral_damage(FIXTURE, workflow)
        assert "[workflow-state:no_task]\nNo active task." in workflow
        assert "## Phase Index" in workflow
        assert "### Request Triage" in workflow
        assert "Ask before creating a task" in workflow
        assert "  MAINTAINER NOTES" in workflow
        assert "    [workflow-state:planning]           -> all of Phase 1" in workflow


def test_extra_platforms_in_the_codex_group_survive() -> None:
    """Regression: Trellis 0.6.15 added `DeepSeek Harness` to the shared group.

    A hardcoded three-platform list neither matches the group nor re-emits its
    members, so the platform loses its instructions.
    """
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        make_repo(repo, codex=True)
        assert run(str(repo), "--profile", "codex").returncode == 0
        workflow = (repo / ".trellis" / "workflow.md").read_text(encoding="utf-8")
        assert workflow.count("[Kilo, Antigravity, Devin, DeepSeek Harness]") == 4
        assert workflow.count("[codex-inline]") == 4
        assert "[codex-inline, Kilo" not in workflow


def test_phase_11_keeps_stock_trellis_guidance() -> None:
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        make_repo(repo, claude=True)
        assert run(str(repo), "--profile", "claude").returncode == 0
        workflow = (repo / ".trellis" / "workflow.md").read_text(encoding="utf-8")
        assert "Stock brainstorm guidance that other platforms still depend on." in workflow
        assert "Load the `trellis-brainstorm` skill." in workflow
        assert workflow.count("TRELLIS-MATT-BRIDGE:START") == 1
        section = workflow.split("#### 1.1", 1)[1].split("#### 1.2", 1)[0]
        assert "trellis-matt-plan" in section


def test_structural_guard_rejects_a_lossy_patch() -> None:
    before = FIXTURE
    after = before.replace("[workflow-state:no_task]\nNo active task. Classify the turn and ask for task-creation consent first.\n[/workflow-state:no_task]\n\n", "")
    try:
        bridge.assert_structure_preserved(before, after)
    except RuntimeError as exc:
        assert "no_task" in str(exc)
    else:
        raise AssertionError("structural guard did not reject a patch that dropped a state block")

    unbalanced = before.replace("-->", "", 1)
    try:
        bridge.assert_structure_preserved(before, unbalanced)
    except RuntimeError as exc:
        assert "unbalanced" in str(exc)
    else:
        raise AssertionError("structural guard did not reject unbalanced HTML comments")


def assert_codex_mode_fails_before_write(codex_dispatch_mode: str | None, expected_mode: str) -> None:
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        make_repo(repo, codex=True, codex_dispatch_mode=codex_dispatch_mode)
        workflow_path = repo / ".trellis" / "workflow.md"
        agents_path = repo / "AGENTS.md"
        workflow_before = workflow_path.read_text(encoding="utf-8")
        agents_before = agents_path.read_text(encoding="utf-8")

        result = run(str(repo), "--profile", "codex")

        assert result.returncode == 4
        assert "supports Trellis inline mode only" in result.stderr
        assert f"resolves codex.dispatch_mode to {expected_mode}" in result.stderr
        assert "Set codex.dispatch_mode explicitly to `inline`" in result.stderr
        assert workflow_path.read_text(encoding="utf-8") == workflow_before
        assert agents_path.read_text(encoding="utf-8") == agents_before
        assert not (repo / ".trellis" / "workflow.md.pre-trellis-matt-bridge").exists()
        assert not (repo / ".agents" / "skills").exists()


def test_codex_missing_dispatch_mode_fails_before_write() -> None:
    assert_codex_mode_fails_before_write(None, "auto")


def test_codex_explicit_non_inline_modes_fail_before_write() -> None:
    for mode in ("auto", "sub-agent"):
        assert_codex_mode_fails_before_write(mode, mode)


def test_codex_explicit_inline_mode_is_supported() -> None:
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        make_repo(repo, codex=True, codex_dispatch_mode="inline")
        result = run(str(repo), "--profile", "codex")
        assert result.returncode == 0, result.stderr
        assert (repo / ".agents" / "skills" / "trellis-matt-implement" / "SKILL.md").is_file()


def test_claude_profile_patches_subagents_and_preserves_other_platforms() -> None:
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        make_repo(repo, claude=True)
        first = run(str(repo), "--profile", "claude")
        assert first.returncode == 0, first.stderr
        workflow = (repo / ".trellis" / "workflow.md").read_text(encoding="utf-8")
        assert_no_collateral_damage(FIXTURE, workflow)
        assert "[Claude Code]\nSpawn the Trellis implement sub-agent" in workflow
        assert "[Cursor, OpenCode, codex-sub-agent, CodeBuddy, Droid, Pi, ZCode, Snow, Oh My Pi]\nSpawn the implement sub-agent: `trellis-implement`." in workflow
        assert "[Claude Code]\n- Planning or unclear requirements -> `trellis-matt-plan`." in workflow
        assert "[codex-inline, Kilo, Antigravity, Devin, DeepSeek Harness]" in workflow
        assert "trellis-matt-implement" not in workflow.split("[workflow-state:in_progress-inline]", 1)[1].split("[/workflow-state:in_progress-inline]", 1)[0]
        impl = (repo / ".claude" / "agents" / "trellis-implement.md").read_text(encoding="utf-8")
        check = (repo / ".claude" / "agents" / "trellis-check.md").read_text(encoding="utf-8")
        for skill in ("trellis-matt-implement", "mattpocock-skills:tdd", "mattpocock-skills:codebase-design", "mattpocock-skills:diagnosing-bugs"):
            assert f"  - {skill}" in impl
        assert "  - existing-project-skill" in check
        assert "  - trellis-matt-check" in check
        assert (repo / ".claude" / "skills" / "trellis-matt-plan" / "SKILL.md").is_file()
        assert (repo / ".claude" / "agents" / "trellis-implement.md.pre-trellis-matt-bridge").read_text(encoding="utf-8") == CLAUDE_IMPLEMENT
        claude_md = (repo / "CLAUDE.md").read_text(encoding="utf-8")
        assert claude_md.count("TRELLIS-MATT-BRIDGE:START") == 1
        second = run(str(repo), "--profile", "claude")
        assert second.returncode == 0, second.stderr
        assert (repo / ".claude" / "agents" / "trellis-implement.md").read_text(encoding="utf-8") == impl
        assert (repo / ".claude" / "agents" / "trellis-check.md").read_text(encoding="utf-8") == check


def test_auto_detects_both_profiles() -> None:
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        make_repo(repo, codex=True, claude=True)
        result = run(str(repo))
        assert result.returncode == 0, result.stderr
        assert "Profiles: claude, codex" in result.stdout
        assert (repo / ".agents" / "skills" / "trellis-matt-check" / "SKILL.md").is_file()
        assert (repo / ".claude" / "skills" / "trellis-matt-check" / "SKILL.md").is_file()
        workflow = (repo / ".trellis" / "workflow.md").read_text(encoding="utf-8")
        assert_no_collateral_damage(FIXTURE, workflow)
        assert "[Claude Code]" in workflow
        assert "[codex-inline]" in workflow
        assert "trellis-matt-implement" in workflow


def test_profiles_can_be_added_sequentially() -> None:
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        make_repo(repo, codex=True, claude=True)
        first = run(str(repo), "--profile", "codex")
        assert first.returncode == 0, first.stderr
        second = run(str(repo), "--profile", "claude")
        assert second.returncode == 0, second.stderr
        workflow = (repo / ".trellis" / "workflow.md").read_text(encoding="utf-8")
        assert_no_collateral_damage(FIXTURE, workflow)
        assert "[codex-inline]" in workflow
        assert "[Claude Code]" in workflow
        assert workflow.count("TRELLIS-MATT-BRIDGE:START") == 1
        assert (repo / ".agents" / "skills" / "trellis-matt-plan" / "SKILL.md").is_file()
        assert (repo / ".claude" / "skills" / "trellis-matt-plan" / "SKILL.md").is_file()


def test_dry_run_does_not_write() -> None:
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        make_repo(repo, codex=True, claude=True)
        workflow_before = (repo / ".trellis" / "workflow.md").read_text(encoding="utf-8")
        impl_before = (repo / ".claude" / "agents" / "trellis-implement.md").read_text(encoding="utf-8")
        result = run(str(repo), "--profile", "both", "--dry-run")
        assert result.returncode == 0, result.stderr
        assert (repo / ".trellis" / "workflow.md").read_text(encoding="utf-8") == workflow_before
        assert (repo / ".claude" / "agents" / "trellis-implement.md").read_text(encoding="utf-8") == impl_before
        assert not (repo / ".agents" / "skills").exists()
        assert not (repo / ".claude" / "skills").exists()
        assert "Would install bridge skills under .claude/skills" in result.stdout


def test_unknown_layout_fails_without_write() -> None:
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        make_repo(repo, codex=True)
        path = repo / ".trellis" / "workflow.md"
        path.write_text("# different workflow\n", encoding="utf-8")
        result = run(str(repo), "--profile", "codex")
        assert result.returncode == 3
        assert path.read_text(encoding="utf-8") == "# different workflow\n"
        assert not (repo / ".trellis" / "workflow.md.pre-trellis-matt-bridge").exists()


def test_against_real_trellis_workflow() -> str:
    """Opt-in end-to-end check against a real `.trellis/workflow.md`.

    Point TRELLIS_WORKFLOW_MD at an initialized project's file, or extract one:
        npm pack @mindfoldhq/trellis@latest && tar xzf mindfoldhq-trellis-*.tgz
        TRELLIS_WORKFLOW_MD=package/dist/templates/trellis/workflow.md \\
            python3 tests/test_install_bridge.py
    The fixture is a stand-in for this file and can drift from it; the layout the
    installer actually has to survive is upstream's, not ours.
    """
    source = os.environ.get("TRELLIS_WORKFLOW_MD")
    if not source:
        return "skipped (set TRELLIS_WORKFLOW_MD to run)"
    real = Path(source).expanduser().resolve().read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        make_repo(repo, codex=True, claude=True)
        (repo / ".trellis" / "workflow.md").write_text(real, encoding="utf-8")
        result = run(str(repo), "--profile", "both")
        assert result.returncode == 0, result.stderr
        patched = (repo / ".trellis" / "workflow.md").read_text(encoding="utf-8")
        assert_no_collateral_damage(real, patched)
        assert "trellis-matt-plan" in patched
        assert "trellis-matt-implement" in patched
        assert "trellis-matt-check" in patched
        assert len(patched.splitlines()) >= len(real.splitlines())
        again = run(str(repo), "--profile", "both")
        assert again.returncode == 0, again.stderr
        assert (repo / ".trellis" / "workflow.md").read_text(encoding="utf-8") == patched
    return f"ran against {source}"


if __name__ == "__main__":
    test_codex_profile_and_idempotence()
    test_state_blocks_are_matched_by_whole_line_not_by_prose_mention()
    test_extra_platforms_in_the_codex_group_survive()
    test_phase_11_keeps_stock_trellis_guidance()
    test_structural_guard_rejects_a_lossy_patch()
    test_codex_missing_dispatch_mode_fails_before_write()
    test_codex_explicit_non_inline_modes_fail_before_write()
    test_codex_explicit_inline_mode_is_supported()
    test_claude_profile_patches_subagents_and_preserves_other_platforms()
    test_auto_detects_both_profiles()
    test_profiles_can_be_added_sequentially()
    test_dry_run_does_not_write()
    test_unknown_layout_fails_without_write()
    real = test_against_real_trellis_workflow()
    print(f"ok: v2.0.3 installer tests passed; real workflow.md check {real}")

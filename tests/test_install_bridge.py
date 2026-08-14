#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INSTALLER = ROOT / "scripts" / "install_bridge.py"

FIXTURE = """# Development Workflow

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

[codex-inline, Kilo, Antigravity, Devin]
- Planning or unclear requirements -> `trellis-brainstorm`.
- Before editing -> `trellis-before-dev`; after editing -> `trellis-check`.
[/codex-inline, Kilo, Antigravity, Devin]

### Guardrails
stock guardrail

## Phase 1: Plan

#### 1.1 Requirement exploration `[required · repeatable]`
Load the `trellis-brainstorm` skill.

#### 1.2 Research `[optional · repeatable]`
research remains

#### 1.3 Configure context `[required · once]`
[Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi, Oh My Pi, ZCode, Snow, Reasonix, Trae, Grok, Kimi Code]
curate manifests
[/Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi, Oh My Pi, ZCode, Snow, Reasonix, Trae, Grok, Kimi Code]

[codex-inline, Kilo, Antigravity, Devin]
Skip this step. Context is loaded directly by the `trellis-before-dev` skill in Phase 2.
[/codex-inline, Kilo, Antigravity, Devin]

#### 1.4 Activate task `[required · once]`
start remains

## Phase 2: Execute

#### 2.1 Implement `[required · repeatable]`
[Claude Code, Cursor, OpenCode, codex-sub-agent, CodeBuddy, Droid, Pi, ZCode, Snow, Oh My Pi]
Spawn the implement sub-agent: `trellis-implement`.
[/Claude Code, Cursor, OpenCode, codex-sub-agent, CodeBuddy, Droid, Pi, ZCode, Snow, Oh My Pi]

[codex-inline, Kilo, Antigravity, Devin]
1. Load the `trellis-before-dev` skill to read project guidelines
2. Implement the code per reviewed artifacts
[/codex-inline, Kilo, Antigravity, Devin]

#### 2.2 Quality check `[required · repeatable]`
[Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi, Oh My Pi, ZCode, Snow, Reasonix, Trae, Grok, Kimi Code]
Spawn the check sub-agent: `trellis-check`.
[/Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi, Oh My Pi, ZCode, Snow, Reasonix, Trae, Grok, Kimi Code]

[codex-inline, Kilo, Antigravity, Devin]
Load the `trellis-check` skill and verify the code per its guidance.
[/codex-inline, Kilo, Antigravity, Devin]

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
        assert "trellis-matt-plan" in workflow
        assert "trellis-matt-implement" in workflow
        assert "trellis-matt-check" in workflow
        assert "[workflow-state:in_progress]\nFlow: `trellis-implement`" in workflow
        assert "[Kilo, Antigravity, Devin]" in workflow
        assert (repo / ".agents" / "skills" / "trellis-matt-implement" / "SKILL.md").is_file()
        assert not (repo / ".claude").exists()
        agents = (repo / "AGENTS.md").read_text(encoding="utf-8")
        assert agents.count("TRELLIS-MATT-BRIDGE:START") == 1
        second = run(str(repo), "--profile", "codex")
        assert second.returncode == 0, second.stderr
        assert (repo / ".trellis" / "workflow.md").read_text(encoding="utf-8") == workflow
        assert (repo / "AGENTS.md").read_text(encoding="utf-8").count("TRELLIS-MATT-BRIDGE:START") == 1


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
        assert "[Claude Code]\nSpawn the Trellis implement sub-agent" in workflow
        assert "[Cursor, OpenCode, codex-sub-agent, CodeBuddy, Droid, Pi, ZCode, Snow, Oh My Pi]\nSpawn the implement sub-agent: `trellis-implement`." in workflow
        assert "[Claude Code]\n- Planning or unclear requirements -> `trellis-matt-plan`." in workflow
        assert "[codex-inline, Kilo, Antigravity, Devin]" in workflow
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
        assert "[codex-inline]" in workflow
        assert "[Claude Code]" in workflow
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


if __name__ == "__main__":
    test_codex_profile_and_idempotence()
    test_codex_missing_dispatch_mode_fails_before_write()
    test_codex_explicit_non_inline_modes_fail_before_write()
    test_codex_explicit_inline_mode_is_supported()
    test_claude_profile_patches_subagents_and_preserves_other_platforms()
    test_auto_detects_both_profiles()
    test_profiles_can_be_added_sequentially()
    test_dry_run_does_not_write()
    test_unknown_layout_fails_without_write()
    print("ok: v2.0.2 installer tests passed")

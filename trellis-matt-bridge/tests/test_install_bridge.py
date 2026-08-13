#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INSTALLER = ROOT / "scripts" / "install_bridge.py"

# Minimal structural fixture based on the current Trellis workflow layout. It
# includes both stock sub-agent routes and the shared Codex-inline blocks so we
# can assert that only the inline path is replaced.
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

[Claude Code, Cursor, OpenCode, codex-sub-agent]
- Planning or unclear requirements -> `trellis-brainstorm`.
- `in_progress` implementation/check -> dispatch `trellis-implement` / `trellis-check`.
[/Claude Code, Cursor, OpenCode, codex-sub-agent]

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
[Claude Code, codex-sub-agent]
curate manifests
[/Claude Code, codex-sub-agent]

[codex-inline, Kilo, Antigravity, Devin]
Skip this step. Context is loaded directly by the `trellis-before-dev` skill in Phase 2.
[/codex-inline, Kilo, Antigravity, Devin]

#### 1.4 Activate task `[required · once]`
start remains

## Phase 2: Execute

#### 2.1 Implement `[required · repeatable]`
[Claude Code, codex-sub-agent]
Spawn the implement sub-agent: `trellis-implement`.
[/Claude Code, codex-sub-agent]

[codex-inline, Kilo, Antigravity, Devin]
1. Load the `trellis-before-dev` skill to read project guidelines
2. Implement the code per reviewed artifacts
[/codex-inline, Kilo, Antigravity, Devin]

#### 2.2 Quality check `[required · repeatable]`
[Claude Code, codex-sub-agent]
Spawn the check sub-agent: `trellis-check`.
[/Claude Code, codex-sub-agent]

[codex-inline, Kilo, Antigravity, Devin]
Load the `trellis-check` skill and verify the code per its guidance.
[/codex-inline, Kilo, Antigravity, Devin]

Final full-scope pass remains.

#### 2.3 Rollback `[on demand]`
rollback remains
"""


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(INSTALLER), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def test_install_and_idempotence() -> None:
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        (repo / ".trellis").mkdir()
        (repo / ".trellis" / "workflow.md").write_text(FIXTURE, encoding="utf-8")
        (repo / "AGENTS.md").write_text("# Agent rules\n", encoding="utf-8")

        first = run(str(repo))
        assert first.returncode == 0, first.stderr
        workflow = (repo / ".trellis" / "workflow.md").read_text(encoding="utf-8")
        agents = (repo / "AGENTS.md").read_text(encoding="utf-8")

        assert "trellis-matt-plan" in workflow
        assert "trellis-matt-implement" in workflow
        assert "trellis-matt-check" in workflow
        assert "Spawn the implement sub-agent: `trellis-implement`" in workflow
        assert "Spawn the check sub-agent: `trellis-check`" in workflow
        assert "[workflow-state:in_progress]\nFlow: `trellis-implement`" in workflow
        assert "rollback remains" in workflow
        assert "stock guardrail" in workflow
        assert agents.count("TRELLIS-MATT-BRIDGE:START") == 1
        assert (repo / ".trellis" / "workflow.md.pre-trellis-matt-bridge").read_text(encoding="utf-8") == FIXTURE
        for skill in ("trellis-matt-plan", "trellis-matt-implement", "trellis-matt-check"):
            assert (repo / ".agents" / "skills" / skill / "SKILL.md").is_file()

        second = run(str(repo))
        assert second.returncode == 0, second.stderr
        workflow2 = (repo / ".trellis" / "workflow.md").read_text(encoding="utf-8")
        agents2 = (repo / "AGENTS.md").read_text(encoding="utf-8")
        assert workflow2 == workflow
        assert agents2.count("TRELLIS-MATT-BRIDGE:START") == 1


def test_dry_run_does_not_write() -> None:
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        (repo / ".trellis").mkdir()
        path = repo / ".trellis" / "workflow.md"
        path.write_text(FIXTURE, encoding="utf-8")
        result = run(str(repo), "--dry-run")
        assert result.returncode == 0, result.stderr
        assert path.read_text(encoding="utf-8") == FIXTURE
        assert not (repo / "AGENTS.md").exists()
        assert not (repo / ".agents").exists()


def test_unknown_layout_fails_without_write() -> None:
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        (repo / ".trellis").mkdir()
        path = repo / ".trellis" / "workflow.md"
        path.write_text("# different workflow\n", encoding="utf-8")
        result = run(str(repo))
        assert result.returncode == 3
        assert path.read_text(encoding="utf-8") == "# different workflow\n"
        assert not (repo / ".trellis" / "workflow.md.pre-trellis-matt-bridge").exists()


if __name__ == "__main__":
    test_install_and_idempotence()
    test_dry_run_does_not_write()
    test_unknown_layout_fails_without_write()
    print("ok: installer tests passed")

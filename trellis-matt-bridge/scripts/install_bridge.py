#!/usr/bin/env python3
"""Install the Codex-inline Trellis + Matt bridge into an existing Trellis project.

The bridge patches Trellis's Markdown workflow (the documented customization
surface) and installs three project-scoped adapter skills under .agents/skills.
It intentionally leaves Trellis's sub-agent dispatch route unchanged.
"""

from __future__ import annotations

import argparse
import difflib
import re
import shutil
import sys
from pathlib import Path

BRIDGE_START = "<!-- TRELLIS-MATT-BRIDGE:START -->"
BRIDGE_END = "<!-- TRELLIS-MATT-BRIDGE:END -->"

AGENTS_BLOCK = f"""{BRIDGE_START}
## Trellis + Matt bridge (Codex inline profile)

- Trellis is the sole owner of task lifecycle, workflow state, task artifacts, spec promotion, commit approval, and finish/archive.
- Use Matt-style methods *inside* Trellis phases; never run two phase controllers for the same phase.
- While a task is `planning`, use `trellis-matt-plan` for requirements/design grilling and persist decisions into Trellis task artifacts.
- In Codex inline mode while a task is `in_progress`, use `trellis-matt-implement`, then `trellis-matt-check` before Trellis Phase 3.
- Do not auto-invoke Matt's top-level `implement` wrapper during an active Trellis task. The bridge adapters deliberately leave commit and completion to Trellis.
- Keep durable knowledge single-sourced: domain vocabulary in `CONTEXT.md`/mapped context, hard-to-reverse surprising decisions in ADRs, reusable engineering conventions in `.trellis/spec/`, and task-local facts in `.trellis/tasks/`.
- If `codex.dispatch_mode` is deliberately changed to `sub-agent`, Trellis's stock implement/check sub-agent route remains authoritative. This bridge does not rewrite those agent definitions.
{BRIDGE_END}
"""

PLANNING_STATE = """[workflow-state:planning]
Load `trellis-matt-plan`; Trellis remains the planning owner.
Lightweight: `prd.md` can be enough. Complex: finish `prd.md`, `design.md`, and `implement.md`; ask for review before `task.py start`.
Multi-deliverable scope: consider a parent task plus independently verifiable child tasks; write dependencies in child artifacts, not tree position.
Sub-agent mode: keep Trellis Phase 1.3 and curate `implement.jsonl` / `check.jsonl` before start.
[/workflow-state:planning]"""

PLANNING_INLINE_STATE = """[workflow-state:planning-inline]
Load `trellis-matt-plan`; Trellis remains the planning owner.
Lightweight: `prd.md` can be enough. Complex: finish `prd.md`, `design.md`, and `implement.md`; ask for review before `task.py start`.
Multi-deliverable scope: consider a parent task plus independently verifiable child tasks; write dependencies in child artifacts, not tree position.
Inline mode: skip jsonl curation; `trellis-matt-implement` reads task artifacts/spec/research directly in Phase 2.
[/workflow-state:planning-inline]"""

IN_PROGRESS_INLINE_STATE = """[workflow-state:in_progress-inline]
Flow: `trellis-matt-implement` -> `trellis-matt-check` -> `trellis-update-spec` -> commit (Phase 3.4) -> `/trellis:finish-work`.
Do not dispatch implement/check sub-agents in inline mode unless the user explicitly switches workflow strategy.
Do not invoke Matt's top-level `implement` wrapper inside the active Trellis task; bridge adapters must not commit, push, promote specs, or finish the task.
[/workflow-state:in_progress-inline]"""

PHASE_11 = """#### 1.1 Requirement exploration `[required · repeatable]`

Load `trellis-matt-plan` and explore requirements/design using Matt-style one-question grilling while Trellis remains the lifecycle owner.

The adapter must:
- ask exactly one unresolved product/design decision at a time;
- research repository facts instead of asking the user for discoverable facts;
- persist product requirements and acceptance criteria to `prd.md` immediately;
- for complex work, persist architecture/trade-offs to `design.md` and ordered vertical slices, validation commands, rollback/check gates, and agreed test seams to `implement.md`;
- keep domain vocabulary in `CONTEXT.md`/mapped context and use ADRs only for hard-to-reverse surprising trade-offs;
- never edit production code or run `task.py start`.

For multi-deliverable work, preserve Trellis's parent/child task model: the parent owns source requirements and integration criteria; independently verifiable deliverables belong in children, and dependency order must be written in child artifacts rather than inferred from the tree.

Return to this step whenever requirements change. When planning is ready, continue through Trellis Phase 1.2/1.3 as applicable and the existing review/start gate in Phase 1.4.
"""

CODEX_21 = """[codex-inline]
1. Load `trellis-matt-implement`.
2. Implement only from the reviewed Trellis task artifacts, relevant `.trellis/spec/`, and task research.
3. Use agreed test seams and vertical-slice TDD; use Matt engineering disciplines such as `tdd`, `codebase-design`, and `diagnosing-bugs` when installed.
4. Run targeted validation throughout and the task's required full validation at the end.
5. Stop without committing, promoting specs, or finishing the Trellis task.
[/codex-inline]"""

OTHERS_21 = """[Kilo, Antigravity, Devin]
1. Load the `trellis-before-dev` skill to read project guidelines.
2. Read `{TASK_DIR}/prd.md`, then `design.md` if present, then `implement.md` if present.
3. Consult materials under `{TASK_DIR}/research/`.
4. Implement the code per reviewed artifacts.
5. Run project lint and type-check.
[/Kilo, Antigravity, Devin]"""

CODEX_22 = """[codex-inline]
Load `trellis-matt-check` and verify the complete task diff on two independent axes:
- **Spec fidelity**: acceptance criteria, design constraints, agreed seams, validation, and scope.
- **Engineering standards**: repository conventions, domain vocabulary, module boundaries, behavior-focused tests, lint/type/test health, and task-relevant design smells.

Fix clear in-scope findings and re-run validation until green. If a finding requires a requirements or hard-design decision, return to planning rather than deciding it here.
[/codex-inline]"""

OTHERS_22 = """[Kilo, Antigravity, Devin]
Load the `trellis-check` skill and verify the code per its guidance:
- Spec compliance
- lint / type-check / tests
- Cross-layer consistency (when changes span layers)

If issues are found -> fix -> re-check, until green.
[/Kilo, Antigravity, Devin]"""

CODEX_13 = """[codex-inline]
Skip this step. Inline context is loaded directly by `trellis-matt-implement` from task artifacts, `.trellis/spec/`, and task research in Phase 2.
[/codex-inline]"""

OTHERS_13 = """[Kilo, Antigravity, Devin]
Skip this step. Context is loaded directly by the `trellis-before-dev` skill in Phase 2.
[/Kilo, Antigravity, Devin]"""

CODEX_ROUTING = """[codex-inline]
- Planning or unclear requirements -> `trellis-matt-plan`.
- `in_progress` implementation -> `trellis-matt-implement`; after edits -> `trellis-matt-check`.
- Repeated debugging -> use Matt `diagnosing-bugs` inside implementation or Trellis `trellis-break-loop` for retrospective; spec updates -> `trellis-update-spec`.
- Commit / finish remain Trellis Phase 3 responsibilities.
[/codex-inline]"""

OTHERS_ROUTING = """[Kilo, Antigravity, Devin]
- Planning or unclear requirements -> `trellis-matt-plan`.
- Before editing -> `trellis-before-dev`; after editing -> `trellis-check`.
- Repeated debugging -> `trellis-break-loop`; spec updates -> `trellis-update-spec`.
[/Kilo, Antigravity, Devin]"""


def replace_state_block(text: str, state: str, replacement: str) -> tuple[str, bool]:
    pattern = re.compile(
        rf"\[workflow-state:{re.escape(state)}\].*?\[/workflow-state:{re.escape(state)}\]",
        re.DOTALL,
    )
    new_text, count = pattern.subn(replacement, text, count=1)
    return new_text, count == 1


def replace_heading_section(text: str, start: str, end: str, replacement: str) -> tuple[str, bool]:
    pattern = re.compile(rf"(?ms)^{start}.*?(?=^{end})")
    new_text, count = pattern.subn(replacement.rstrip() + "\n", text, count=1)
    return new_text, count == 1


def split_or_update_codex_group(
    section: str,
    codex_replacement: str,
    others_replacement: str,
) -> tuple[str, bool]:
    """Replace Trellis's shared codex-inline/Kilo/Antigravity/Devin block.

    First install splits the shared block so only Codex changes behavior. Later
    installs update just the managed [codex-inline] block, making this idempotent.
    """
    existing_codex = re.compile(r"(?ms)^\[codex-inline\]\n.*?^\[/codex-inline\]\n?")
    if existing_codex.search(section):
        return existing_codex.sub(codex_replacement.rstrip() + "\n", section, count=1), True

    shared = re.compile(
        r"(?ms)^\[codex-inline,\s*Kilo,\s*Antigravity,\s*Devin\]\n.*?^\[/codex-inline,\s*Kilo,\s*Antigravity,\s*Devin\]\n?"
    )
    if not shared.search(section):
        return section, False
    replacement = codex_replacement.rstrip() + "\n\n" + others_replacement.rstrip() + "\n"
    return shared.sub(replacement, section, count=1), True


def patch_section_codex_block(
    text: str,
    start_heading: str,
    end_heading: str,
    codex_replacement: str,
    others_replacement: str,
) -> tuple[str, bool]:
    section_pattern = re.compile(rf"(?ms)(^{start_heading}.*?)(?=^{end_heading})")
    match = section_pattern.search(text)
    if not match:
        return text, False
    patched, changed = split_or_update_codex_group(match.group(1), codex_replacement, others_replacement)
    if not changed:
        return text, False
    return text[: match.start(1)] + patched + text[match.end(1) :], True


def patch_active_routing(text: str) -> tuple[str, bool]:
    section_pattern = re.compile(r"(?ms)(^###\s+Active Task Routing\b.*?)(?=^###\s+Guardrails\b)")
    match = section_pattern.search(text)
    if not match:
        return text, False
    patched, changed = split_or_update_codex_group(match.group(1), CODEX_ROUTING, OTHERS_ROUTING)
    if not changed:
        return text, False
    return text[: match.start(1)] + patched + text[match.end(1) :], True


def patch_workflow(original: str) -> str:
    text = original
    failures: list[str] = []

    # Planning can safely use the adapter in both modes; Trellis still owns the
    # phase and sub-agent context curation remains explicit in the generic tag.
    for state, replacement in (
        ("planning", PLANNING_STATE),
        ("planning-inline", PLANNING_INLINE_STATE),
        ("in_progress-inline", IN_PROGRESS_INLINE_STATE),
    ):
        text, changed = replace_state_block(text, state, replacement)
        if not changed:
            failures.append(f"workflow-state:{state}")

    # Leave [workflow-state:in_progress] untouched so Trellis sub-agent mode
    # continues to use stock trellis-implement / trellis-check agents.

    text, changed = replace_heading_section(
        text,
        r"####\s+1\.1\b[^\n]*",
        r"####\s+1\.2\b[^\n]*",
        PHASE_11,
    )
    if not changed:
        failures.append("Phase 1.1 -> 1.2")

    # In Phase 1.3 only Codex inline's explanation changes; sub-agent manifest
    # curation and other platforms remain stock Trellis.
    text, changed = patch_section_codex_block(
        text,
        r"####\s+1\.3\b[^\n]*",
        r"####\s+1\.4\b[^\n]*",
        CODEX_13,
        OTHERS_13,
    )
    if not changed:
        failures.append("Phase 1.3 codex-inline block")

    # Preserve all stock sub-agent branches; split only the shared inline block.
    text, changed = patch_section_codex_block(
        text,
        r"####\s+2\.1\b[^\n]*",
        r"####\s+2\.2\b[^\n]*",
        CODEX_21,
        OTHERS_21,
    )
    if not changed:
        failures.append("Phase 2.1 codex-inline block")

    text, changed = patch_section_codex_block(
        text,
        r"####\s+2\.2\b[^\n]*",
        r"####\s+2\.3\b[^\n]*",
        CODEX_22,
        OTHERS_22,
    )
    if not changed:
        failures.append("Phase 2.2 codex-inline block")

    text, changed = patch_active_routing(text)
    if not changed:
        failures.append("Active Task Routing codex-inline block")

    if failures:
        raise RuntimeError(
            "Unsupported .trellis/workflow.md layout; could not find: "
            + ", ".join(failures)
            + ". The file was not overwritten. Update this bridge's anchors for your Trellis version."
        )
    return text


def patch_agents(original: str) -> str:
    block_pattern = re.compile(
        re.escape(BRIDGE_START) + r".*?" + re.escape(BRIDGE_END) + r"\n?",
        re.DOTALL,
    )
    if block_pattern.search(original):
        return block_pattern.sub(AGENTS_BLOCK, original, count=1)
    separator = "" if not original or original.endswith("\n\n") else ("\n" if original.endswith("\n") else "\n\n")
    return original + separator + AGENTS_BLOCK


def install_skills(repo_root: Path, bridge_root: Path) -> Path:
    dest_root = repo_root / ".agents" / "skills"
    dest_root.mkdir(parents=True, exist_ok=True)
    source_skills = bridge_root / "skills"
    for source in sorted(source_skills.iterdir()):
        if not source.is_dir():
            continue
        target = dest_root / source.name
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)
    return dest_root


def make_diff(path: Path, before: str, after: str) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=str(path),
            tofile=str(path),
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", nargs="?", default=".", help="Existing Trellis project root")
    parser.add_argument("--dry-run", action="store_true", help="Print workflow/AGENTS diffs without writing")
    args = parser.parse_args()

    repo_root = Path(args.target).expanduser().resolve()
    bridge_root = Path(__file__).resolve().parent.parent
    workflow = repo_root / ".trellis" / "workflow.md"
    agents = repo_root / "AGENTS.md"

    if not workflow.is_file():
        print(f"error: {workflow} does not exist. Run `trellis init --codex -u YOUR_NAME` first.", file=sys.stderr)
        return 2

    before_workflow = workflow.read_text(encoding="utf-8")
    before_agents = agents.read_text(encoding="utf-8") if agents.exists() else ""

    try:
        after_workflow = patch_workflow(before_workflow)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3
    after_agents = patch_agents(before_agents)

    if args.dry_run:
        print(make_diff(workflow, before_workflow, after_workflow))
        print(make_diff(agents, before_agents, after_agents))
        print("Would install bridge skills under .agents/skills (Codex inline profile).")
        return 0

    backup = workflow.with_name("workflow.md.pre-trellis-matt-bridge")
    if not backup.exists():
        shutil.copy2(workflow, backup)

    workflow.write_text(after_workflow, encoding="utf-8")
    agents.write_text(after_agents, encoding="utf-8")
    dest = install_skills(repo_root, bridge_root)

    print(f"Patched: {workflow}")
    print(f"Updated: {agents}")
    print(f"Backup:  {backup}")
    print(f"Skills:  {dest}")
    print("Restart the Codex agent session, then inspect `git diff` before using the bridge.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

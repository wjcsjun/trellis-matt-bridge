#!/usr/bin/env python3
"""Install Trellis + Matt bridge profiles into an existing Trellis project.

v2 supports:
- Codex inline: project adapters under .agents/skills plus workflow routing.
- Claude Code: project adapters under .claude/skills plus Matt-powered Trellis
  implement/check sub-agents.

Trellis remains the sole lifecycle/commit owner in every profile.
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

CODEX_POLICY = f"""{BRIDGE_START}
## Trellis + Matt bridge (Codex profile)

- Trellis owns task lifecycle, workflow state, task artifacts, spec promotion, commit approval, and finish/archive.
- During planning, use `trellis-matt-plan` for Matt-style grilling/domain modeling while writing decisions into Trellis artifacts.
- In Codex inline mode, use `trellis-matt-implement`, then `trellis-matt-check`, before Trellis Phase 3.
- Never auto-invoke Matt's top-level `implement` during an active Trellis task; it commits and overlaps with Trellis ownership.
- Keep durable knowledge single-sourced: domain vocabulary in `CONTEXT.md`/mapped context, surprising hard-to-reverse decisions in ADRs, reusable conventions in `.trellis/spec/`, task-local facts in `.trellis/tasks/`.
- If `codex.dispatch_mode` is switched to `sub-agent`, Trellis's stock sub-agent route stays authoritative; this profile only rewrites the inline route.
{BRIDGE_END}
"""

CLAUDE_POLICY = f"""{BRIDGE_START}
## Trellis + Matt bridge (Claude Code profile)

- Trellis owns task lifecycle, workflow state, task artifacts, spec promotion, commit approval, and finish/archive.
- During planning, use `trellis-matt-plan`; on Claude Code it may compose with the installed `mattpocock-skills` plugin (`grilling`, `domain-modeling`).
- Keep Trellis's `trellis-implement` and `trellis-check` sub-agents as execution owners. The bridge preloads `trellis-matt-implement` / `trellis-matt-check` into those agents.
- The implement agent may also preload Matt's `tdd`, `codebase-design`, and `diagnosing-bugs` plugin skills. It must never commit, push, promote specs, or finish/archive the task.
- Do not run Matt's `code-review` orchestrator inside `trellis-check`: Claude Code sub-agents cannot spawn sub-agents. The bridge check adapter performs the same two-axis review inline instead.
- Never auto-invoke Matt's top-level `implement` during an active Trellis task; it commits and overlaps with Trellis ownership.
{BRIDGE_END}
"""

PLANNING_STATE = """[workflow-state:planning]
Bridge-supported harnesses (Claude Code / Codex): load `trellis-matt-plan`; Trellis remains the planning owner. Other platforms keep their stock Trellis planning skill.
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

On Claude Code or Codex with this bridge installed, load `trellis-matt-plan`; other platforms keep the stock `trellis-brainstorm` path. Trellis remains the lifecycle owner.

The bridge adapter must:
- ask exactly one unresolved product/design decision at a time;
- research repository facts instead of asking the user for discoverable facts;
- persist requirements and acceptance criteria to `prd.md` immediately;
- for complex work, persist architecture/trade-offs to `design.md` and ordered vertical slices, validation commands, rollback/check gates, and agreed test seams to `implement.md`;
- keep domain vocabulary in `CONTEXT.md`/mapped context and use ADRs only for hard-to-reverse surprising trade-offs;
- never edit production code or run `task.py start`.

For multi-deliverable work, preserve Trellis parent/child semantics: the parent owns source requirements and integration criteria; independently verifiable deliverables belong in children, and dependency order belongs in child artifacts rather than tree position.

Return here whenever requirements change. When planning is ready, continue through Trellis Phase 1.2/1.3 as applicable and the existing review/start gate in Phase 1.4.
"""

CODEX_13 = """[codex-inline]
Skip this step. Inline context is loaded directly by `trellis-matt-implement` from task artifacts, `.trellis/spec/`, and task research in Phase 2.
[/codex-inline]"""

OTHERS_INLINE_13 = """[Kilo, Antigravity, Devin]
Skip this step. Context is loaded directly by the `trellis-before-dev` skill in Phase 2.
[/Kilo, Antigravity, Devin]"""

CODEX_21 = """[codex-inline]
1. Load `trellis-matt-implement`.
2. Implement only from reviewed Trellis artifacts, relevant `.trellis/spec/`, and task research.
3. Use agreed seams and vertical-slice TDD; compose with Matt `tdd`, `codebase-design`, and `diagnosing-bugs` when installed.
4. Run targeted validation throughout and required full validation at the end.
5. Stop without committing, promoting specs, or finishing the Trellis task.
[/codex-inline]"""

OTHERS_INLINE_21 = """[Kilo, Antigravity, Devin]
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

OTHERS_INLINE_22 = """[Kilo, Antigravity, Devin]
Load the `trellis-check` skill and verify the code per its guidance:
- Spec compliance
- lint / type-check / tests
- Cross-layer consistency (when changes span layers)

If issues are found -> fix -> re-check, until green.
[/Kilo, Antigravity, Devin]"""

CODEX_ROUTING = """[codex-inline]
- Planning or unclear requirements -> `trellis-matt-plan`.
- `in_progress` implementation -> `trellis-matt-implement`; after edits -> `trellis-matt-check`.
- Repeated debugging -> use Matt `diagnosing-bugs` inside implementation or Trellis `trellis-break-loop` for retrospective; spec updates -> `trellis-update-spec`.
- Commit / finish remain Trellis Phase 3 responsibilities.
[/codex-inline]"""

OTHERS_INLINE_ROUTING = """[Kilo, Antigravity, Devin]
- Planning or unclear requirements -> `trellis-brainstorm`.
- Before editing -> `trellis-before-dev`; after editing -> `trellis-check`.
- Repeated debugging -> `trellis-break-loop`; spec updates -> `trellis-update-spec`.
[/Kilo, Antigravity, Devin]"""

CLAUDE_21 = """[Claude Code]
Spawn the Trellis implement sub-agent exactly as usual:
- **Agent type**: `trellis-implement`
- **Dispatch prompt guard**: start with `Active task: <task path>`, then state that it is already the implement sub-agent and must not redispatch implement/check.
- The bridge patches `.claude/agents/trellis-implement.md` to preload `trellis-matt-implement` plus Matt's safe implementation primitives (`tdd`, `codebase-design`, `diagnosing-bugs`) when the Matt plugin is installed.
- Trellis context injection / `implement.jsonl` remains authoritative.
- The sub-agent must stop without git commit/push, spec promotion, or task finish/archive.
[/Claude Code]"""

CLAUDE_22 = """[Claude Code]
Spawn the Trellis check sub-agent exactly as usual:
- **Agent type**: `trellis-check`
- **Dispatch prompt guard**: start with `Active task: <task path>`, then state that it is already the check sub-agent and must not redispatch implement/check.
- The bridge patches `.claude/agents/trellis-check.md` to preload `trellis-matt-check`.
- The adapter performs separate Spec-fidelity and Engineering-standards passes, fixes clear in-scope findings, and reruns validation.
- Do NOT invoke Matt `code-review` from inside this sub-agent: it spawns review sub-agents, while Claude Code sub-agents cannot spawn sub-agents.
[/Claude Code]"""

CLAUDE_ROUTING = """[Claude Code]
- Planning or unclear requirements -> `trellis-matt-plan`.
- `in_progress` implementation/check -> dispatch Trellis `trellis-implement` / `trellis-check`; their Claude agent definitions preload the bridge adapters.
- Repeated debugging -> Matt `diagnosing-bugs` is available inside implement when the plugin is installed; Trellis retrospective remains `trellis-break-loop`.
- Spec update, commit, and finish remain Trellis Phase 3 responsibilities.
[/Claude Code]"""

CLAUDE_IMPLEMENT_SKILLS = [
    "trellis-matt-implement",
    "mattpocock-skills:tdd",
    "mattpocock-skills:codebase-design",
    "mattpocock-skills:diagnosing-bugs",
]
CLAUDE_CHECK_SKILLS = ["trellis-matt-check"]


def replace_state_block(text: str, state: str, replacement: str) -> tuple[str, bool]:
    pattern = re.compile(rf"\[workflow-state:{re.escape(state)}\].*?\[/workflow-state:{re.escape(state)}\]", re.DOTALL)
    new_text, count = pattern.subn(replacement, text, count=1)
    return new_text, count == 1


def replace_heading_section(text: str, start: str, end: str, replacement: str) -> tuple[str, bool]:
    pattern = re.compile(rf"(?ms)^{start}.*?(?=^{end})")
    new_text, count = pattern.subn(replacement.rstrip() + "\n", text, count=1)
    return new_text, count == 1


def split_or_update_codex_group(section: str, codex_replacement: str, others_replacement: str) -> tuple[str, bool]:
    existing = re.compile(r"(?ms)^\[codex-inline\]\n.*?^\[/codex-inline\]\n?")
    if existing.search(section):
        return existing.sub(codex_replacement.rstrip() + "\n", section, count=1), True
    shared = re.compile(r"(?ms)^\[codex-inline,\s*Kilo,\s*Antigravity,\s*Devin\]\n.*?^\[/codex-inline,\s*Kilo,\s*Antigravity,\s*Devin\]\n?")
    if not shared.search(section):
        return section, False
    replacement = codex_replacement.rstrip() + "\n\n" + others_replacement.rstrip() + "\n"
    return shared.sub(replacement, section, count=1), True


def split_platform_group(section: str, platform: str, replacement: str) -> tuple[str, bool]:
    separate = re.compile(rf"(?ms)^\[{re.escape(platform)}\]\n.*?^\[/{re.escape(platform)}\]\n?")
    if separate.search(section):
        return separate.sub(replacement.rstrip() + "\n", section, count=1), True

    block_re = re.compile(r"(?ms)^\[([^\]\n]+)\]\n(.*?)^\[/\1\]\n?")
    for match in block_re.finditer(section):
        members = [m.strip() for m in match.group(1).split(",")]
        if platform not in members:
            continue
        others = [m for m in members if m != platform]
        pieces = [replacement.rstrip()]
        if others:
            header = ", ".join(others)
            pieces.append(f"[{header}]\n{match.group(2).rstrip()}\n[/{header}]")
        new_block = "\n\n".join(pieces) + "\n"
        return section[: match.start()] + new_block + section[match.end() :], True
    return section, False


def patch_section(text: str, start_heading: str, end_heading: str, patcher) -> tuple[str, bool]:
    pattern = re.compile(rf"(?ms)(^{start_heading}.*?)(?=^{end_heading})")
    match = pattern.search(text)
    if not match:
        return text, False
    patched, changed = patcher(match.group(1))
    if not changed:
        return text, False
    return text[: match.start(1)] + patched + text[match.end(1) :], True


def patch_common_planning(text: str) -> tuple[str, list[str]]:
    failures: list[str] = []
    text, changed = replace_state_block(text, "planning", PLANNING_STATE)
    if not changed:
        failures.append("workflow-state:planning")
    text, changed = replace_heading_section(text, r"####\s+1\.1\b[^\n]*", r"####\s+1\.2\b[^\n]*", PHASE_11)
    if not changed:
        failures.append("Phase 1.1 -> 1.2")
    return text, failures


def patch_codex_workflow(text: str) -> tuple[str, list[str]]:
    failures: list[str] = []
    for state, replacement in (("planning-inline", PLANNING_INLINE_STATE), ("in_progress-inline", IN_PROGRESS_INLINE_STATE)):
        text, changed = replace_state_block(text, state, replacement)
        if not changed:
            failures.append(f"workflow-state:{state}")
    for start, end, repl, other, label in (
        (r"####\s+1\.3\b[^\n]*", r"####\s+1\.4\b[^\n]*", CODEX_13, OTHERS_INLINE_13, "Phase 1.3 codex-inline"),
        (r"####\s+2\.1\b[^\n]*", r"####\s+2\.2\b[^\n]*", CODEX_21, OTHERS_INLINE_21, "Phase 2.1 codex-inline"),
        (r"####\s+2\.2\b[^\n]*", r"####\s+2\.3\b[^\n]*", CODEX_22, OTHERS_INLINE_22, "Phase 2.2 codex-inline"),
    ):
        text, changed = patch_section(text, start, end, lambda s, a=repl, b=other: split_or_update_codex_group(s, a, b))
        if not changed:
            failures.append(label)
    text, changed = patch_section(text, r"###\s+Active Task Routing\b", r"###\s+Guardrails\b", lambda s: split_or_update_codex_group(s, CODEX_ROUTING, OTHERS_INLINE_ROUTING))
    if not changed:
        failures.append("Active Task Routing codex-inline")
    return text, failures


def patch_claude_workflow(text: str) -> tuple[str, list[str]]:
    failures: list[str] = []
    for start, end, replacement, label in (
        (r"####\s+2\.1\b[^\n]*", r"####\s+2\.2\b[^\n]*", CLAUDE_21, "Phase 2.1 Claude Code"),
        (r"####\s+2\.2\b[^\n]*", r"####\s+2\.3\b[^\n]*", CLAUDE_22, "Phase 2.2 Claude Code"),
        (r"###\s+Active Task Routing\b", r"###\s+Guardrails\b", CLAUDE_ROUTING, "Active Task Routing Claude Code"),
    ):
        text, changed = patch_section(text, start, end, lambda s, r=replacement: split_platform_group(s, "Claude Code", r))
        if not changed:
            failures.append(label)
    return text, failures


def patch_workflow(original: str, profiles: set[str]) -> str:
    text, failures = patch_common_planning(original)
    if "codex" in profiles:
        text, more = patch_codex_workflow(text)
        failures.extend(more)
    if "claude" in profiles:
        text, more = patch_claude_workflow(text)
        failures.extend(more)
    if failures:
        raise RuntimeError("Unsupported .trellis/workflow.md layout; could not find: " + ", ".join(failures) + ". The file was not overwritten. Update bridge anchors for your Trellis version.")
    return text


def patch_managed_block(original: str, block: str) -> str:
    pattern = re.compile(re.escape(BRIDGE_START) + r".*?" + re.escape(BRIDGE_END) + r"\n?", re.DOTALL)
    if pattern.search(original):
        return pattern.sub(block, original, count=1)
    separator = "" if not original or original.endswith("\n\n") else ("\n" if original.endswith("\n") else "\n\n")
    return original + separator + block


def ensure_frontmatter_skills(text: str, skills: list[str]) -> str:
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        raise RuntimeError("Claude agent file is missing YAML frontmatter")
    front = match.group(1)
    lines = front.splitlines()
    start = next((i for i, line in enumerate(lines) if re.match(r"^skills\s*:", line)), None)
    existing: list[str] = []
    if start is None:
        insert_at = len(lines)
        new_lines = lines[:insert_at] + ["skills:"] + [f"  - {s}" for s in skills] + lines[insert_at:]
    else:
        line = lines[start]
        inline = re.match(r"^skills\s*:\s*\[(.*)\]\s*$", line)
        if inline:
            existing = [x.strip().strip("'\"") for x in inline.group(1).split(",") if x.strip()]
            end = start + 1
        else:
            end = start + 1
            while end < len(lines) and (lines[end].startswith(" ") or not lines[end].strip()):
                item = re.match(r"^\s*-\s*(.+?)\s*$", lines[end])
                if item:
                    existing.append(item.group(1).strip().strip("'\""))
                end += 1
        merged = existing + [s for s in skills if s not in existing]
        new_lines = lines[:start] + ["skills:"] + [f"  - {s}" for s in merged] + lines[end:]
    new_front = "\n".join(new_lines)
    return "---\n" + new_front + "\n---\n" + text[match.end() :]


def install_skills(repo_root: Path, bridge_root: Path, profile: str) -> Path:
    dest_root = repo_root / (".agents/skills" if profile == "codex" else ".claude/skills")
    dest_root.mkdir(parents=True, exist_ok=True)
    for source in sorted((bridge_root / "skills").iterdir()):
        if source.is_dir():
            target = dest_root / source.name
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(source, target)
    return dest_root


def make_diff(path: Path, before: str, after: str) -> str:
    return "".join(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True), fromfile=str(path), tofile=str(path)))


def detect_profiles(repo_root: Path) -> set[str]:
    profiles: set[str] = set()
    if (repo_root / ".codex").is_dir():
        profiles.add("codex")
    if (repo_root / ".claude" / "agents" / "trellis-implement.md").is_file() and (repo_root / ".claude" / "agents" / "trellis-check.md").is_file():
        profiles.add("claude")
    return profiles


def read_codex_dispatch_mode(repo_root: Path) -> str:
    """Return the explicitly configured Codex dispatch mode, or Trellis's inline default.

    Trellis currently uses a small top-level `codex:` YAML block. Avoid adding a
    PyYAML dependency just for this preflight: read only the `dispatch_mode` scalar
    inside that block and treat an omitted block/key as the current `inline` default.
    """
    config = repo_root / ".trellis" / "config.yaml"
    if not config.is_file():
        return "inline"

    lines = config.read_text(encoding="utf-8").splitlines()
    codex_indent: int | None = None
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        inline_block = re.match(r"^\s*codex\s*:\s*\{(.*?)\}\s*(?:#.*)?$", line)
        if inline_block:
            dispatch = re.search(r"(?:^|,)\s*dispatch_mode\s*:\s*([^,}]+)", inline_block.group(1))
            if dispatch:
                value = dispatch.group(1).strip().strip("'\"")
                return value or "inline"
            return "inline"

        indent = len(line) - len(line.lstrip(" "))
        if codex_indent is None:
            if re.match(r"^\s*codex\s*:\s*(?:#.*)?$", line):
                codex_indent = indent
            continue

        if indent <= codex_indent:
            break

        match = re.match(r"^\s*dispatch_mode\s*:\s*(.*?)\s*$", line)
        if not match:
            continue
        value = match.group(1).split("#", 1)[0].strip().strip("'\"")
        return value or "inline"

    return "inline"


def backup_once(path: Path) -> Path:
    backup = path.with_name(path.name + ".pre-trellis-matt-bridge")
    if not backup.exists():
        shutil.copy2(path, backup)
    return backup


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", nargs="?", default=".", help="Existing Trellis project root")
    parser.add_argument("--profile", choices=("auto", "codex", "claude", "both"), default="auto", help="Install one or both bridge profiles; auto detects initialized Trellis platforms")
    parser.add_argument("--dry-run", action="store_true", help="Print diffs and planned copies without writing")
    args = parser.parse_args()

    repo_root = Path(args.target).expanduser().resolve()
    bridge_root = Path(__file__).resolve().parent.parent
    workflow = repo_root / ".trellis" / "workflow.md"
    if not workflow.is_file():
        print(f"error: {workflow} does not exist. Initialize Trellis first (for example `trellis init --claude --codex -u YOUR_NAME`).", file=sys.stderr)
        return 2

    profiles = detect_profiles(repo_root) if args.profile == "auto" else ({"codex", "claude"} if args.profile == "both" else {args.profile})
    if not profiles:
        print("error: auto detection found neither .codex nor Trellis Claude agent definitions; pass --profile codex|claude|both after initializing that platform.", file=sys.stderr)
        return 2

    if "codex" in profiles:
        if not (repo_root / ".codex").is_dir():
            print("error: missing .codex/. Initialize/update Trellis with Codex support first.", file=sys.stderr)
            return 2
        dispatch_mode = read_codex_dispatch_mode(repo_root)
        if dispatch_mode != "inline":
            print(
                "error: the Codex bridge profile supports Trellis inline mode only, but "
                f".trellis/config.yaml sets codex.dispatch_mode: {dispatch_mode}. "
                "Set it to `inline` (or remove the explicit setting; current Trellis defaults to inline), "
                "then rerun. No files were changed.",
                file=sys.stderr,
            )
            return 4

    if "claude" in profiles:
        for name in ("trellis-implement.md", "trellis-check.md"):
            if not (repo_root / ".claude" / "agents" / name).is_file():
                print(f"error: missing .claude/agents/{name}. Initialize/update Trellis with Claude Code support first.", file=sys.stderr)
                return 2

    before_workflow = workflow.read_text(encoding="utf-8")
    try:
        after_workflow = patch_workflow(before_workflow, profiles)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3

    planned_text: list[tuple[Path, str, str]] = [(workflow, before_workflow, after_workflow)]
    if "codex" in profiles:
        path = repo_root / "AGENTS.md"
        before = path.read_text(encoding="utf-8") if path.exists() else ""
        planned_text.append((path, before, patch_managed_block(before, CODEX_POLICY)))
    if "claude" in profiles:
        path = repo_root / "CLAUDE.md"
        before = path.read_text(encoding="utf-8") if path.exists() else ""
        planned_text.append((path, before, patch_managed_block(before, CLAUDE_POLICY)))
        for name, skills in (("trellis-implement.md", CLAUDE_IMPLEMENT_SKILLS), ("trellis-check.md", CLAUDE_CHECK_SKILLS)):
            path = repo_root / ".claude" / "agents" / name
            before = path.read_text(encoding="utf-8")
            try:
                after = ensure_frontmatter_skills(before, skills)
            except RuntimeError as exc:
                print(f"error: {path}: {exc}", file=sys.stderr)
                return 3
            planned_text.append((path, before, after))

    if args.dry_run:
        for path, before, after in planned_text:
            diff = make_diff(path, before, after)
            if diff:
                print(diff)
        for profile in sorted(profiles):
            dest = ".agents/skills" if profile == "codex" else ".claude/skills"
            print(f"Would install bridge skills under {dest} ({profile} profile).")
        return 0

    backups = [backup_once(workflow)]
    if "claude" in profiles:
        backups.extend(backup_once(repo_root / ".claude" / "agents" / name) for name in ("trellis-implement.md", "trellis-check.md"))

    for path, _, after in planned_text:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(after, encoding="utf-8")

    destinations = [install_skills(repo_root, bridge_root, profile) for profile in sorted(profiles)]

    print(f"Profiles: {', '.join(sorted(profiles))}")
    print(f"Patched:  {workflow}")
    for backup in backups:
        print(f"Backup:   {backup}")
    for dest in destinations:
        print(f"Skills:   {dest}")
    if "claude" in profiles:
        print("Claude:   restart Claude Code so edited sub-agent definitions are reloaded.")
    if "codex" in profiles:
        print("Codex:    restart the agent session after installation.")
    print("Inspect `git diff` before using the bridge.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

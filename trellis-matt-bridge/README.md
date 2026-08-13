# trellis-matt-bridge

A small **Codex-inline reference integration** that lets **Trellis own the workflow lifecycle** while using **Matt Pocock's engineering methods inside selected phases**.

This repository deliberately does **not** vendor or fork either upstream project:

- Matt Pocock skills: https://github.com/mattpocock/skills
- Trellis: https://github.com/mindfold-ai/trellis

That separation is the main design decision. Running two full workflow controllers at once creates duplicate planning, review, task, and commit ownership. The bridge instead follows one rule:

> **One phase, one owner. Trellis owns lifecycle; Matt-style skills provide the method inside the phase.**

## Architecture

```text
User request
    |
    v
Trellis lifecycle / state machine
    |
    +-- planning ------> trellis-matt-plan
    |                    - one-question grilling
    |                    - domain modeling
    |                    - writes Trellis task artifacts
    |
    +-- in_progress ---> trellis-matt-implement
    |                    - vertical-slice TDD
    |                    - codebase design
    |                    - disciplined debugging
    |                    - NO commit
    |                         |
    |                         v
    |                    trellis-matt-check
    |                    - spec-fidelity review
    |                    - standards review
    |                    - validation/fixes
    |                    - NO commit
    |
    +-- Phase 3 -------> Trellis update-spec
                         Trellis commit plan + approval
                         Trellis finish/archive
```

## Why not call Matt's top-level `implement` directly?

Matt's top-level implementation workflow is useful when Matt's workflow owns the whole engineering cycle. Inside an active Trellis task it overlaps with Trellis's downstream review/commit lifecycle. The bridge therefore uses Matt's model-level engineering disciplines through an adapter and intentionally leaves commit, spec promotion, and task completion to Trellis.

Likewise, this bridge does not initially map Matt's `to-spec` / `to-tickets` workflow into Trellis, because Trellis already owns task artifacts and task status. You can add that mapping later if you have a concrete issue-tracker policy.

## What belongs where?

| Information | Canonical location |
|---|---|
| Product requirements / acceptance criteria | `.trellis/tasks/<task>/prd.md` |
| Task architecture and trade-offs | `.trellis/tasks/<task>/design.md` |
| Ordered implementation slices / test seams / validation | `.trellis/tasks/<task>/implement.md` |
| Task-local research | `.trellis/tasks/<task>/research/` |
| Reusable engineering/team conventions | `.trellis/spec/` |
| Domain vocabulary / ubiquitous language | `CONTEXT.md` or mapped context |
| Hard-to-reverse, surprising decision | ADR |

Avoid copying the same fact into several of these places. The bridge adapters are written to preserve this ownership model.

## Prerequisites

Initialize Trellis in the target project first. For a Codex-oriented setup, the upstream commands are typically:

```bash
npm install -g @mindfoldhq/trellis@latest
cd /path/to/project
trellis init --codex -u YOUR_NAME
```

Install Matt's skills using the upstream Skills CLI:

```bash
npx skills@latest add mattpocock/skills
```

For the bridge, the most useful Matt skills are the engineering disciplines such as:

- `grilling`
- `domain-modeling`
- `tdd`
- `codebase-design`
- `diagnosing-bugs`

`code-review` is useful as a standalone tool too. Avoid auto-routing Matt's **top-level `implement`** inside an active Trellis task; the bridge adapter takes its place there.

Optional: install Trellis's own workflow-customization helper if you want an agent to further tune `.trellis/workflow.md`:

```bash
npx skills add mindfold-ai/marketplace --skill trellis-meta
```

## Install this bridge

This reference implementation targets the same setup discussed in the forum post: **Codex with Trellis inline execution**. From this repository:

```bash
python3 scripts/install_bridge.py /path/to/project
```

It installs the adapters under the project-scoped `.agents/skills/` directory. Trellis's existing Codex sub-agent route is deliberately left unchanged.

Preview the workflow/AGENTS changes without writing anything:

```bash
python3 scripts/install_bridge.py /path/to/project --dry-run
```

The installer:

1. verifies `.trellis/workflow.md` exists;
2. patches the planning and implementation/check routes;
3. adds a managed Trellis+Matt policy block to `AGENTS.md`;
4. copies the three bridge adapter skills to the project-scoped `.agents/skills/` directory;
5. saves the original workflow once as `.trellis/workflow.md.pre-trellis-matt-bridge`.

After installation, restart your agent session and inspect the target project's `git diff` before using the workflow.

## Adapter skills

### `trellis-matt-plan`

Use during Trellis `planning`. It applies one-question grilling and domain modeling, but writes the result into Trellis artifacts and never starts the task or edits production code.

### `trellis-matt-implement`

Use after the Trellis task is `in_progress`. It reads the approved Trellis artifacts, uses agreed test seams and vertical-slice TDD, and may call Matt's engineering disciplines. It never commits, promotes specs, or finishes the task.

### `trellis-matt-check`

Use after implementation. It checks two axes independently: specification fidelity and engineering standards. It may repair in-scope findings and rerun validation, but never commits or finishes the task.

If you want the smallest possible integration, you can omit `trellis-matt-check` and keep Trellis's stock `trellis-check`; planning + implementation are the two most valuable substitutions.

## Trellis updates

Do not freeze the entire Trellis workflow merely to protect this bridge. Prefer:

```bash
trellis update
python3 /path/to/trellis-matt-bridge/scripts/install_bridge.py /path/to/project
git diff
```

The installer uses structural anchors instead of replacing the whole file. If a future Trellis release changes those anchors, installation fails before writing rather than silently applying a questionable patch. Update the bridge for the new workflow structure, then rerun it.

## Codex dispatch mode

Current Trellis defaults Codex to `inline`; the forum setup also says the main session normally explores/implements/checks and only uses sub-agents when explicitly needed. This bridge therefore rewrites only the **Codex inline implementation/check path**.

If you deliberately set `codex.dispatch_mode: sub-agent`, Trellis's stock `trellis-implement` / `trellis-check` agents remain the execution owners. This repo does **not** automatically inject Matt's methods into those sub-agent definitions. That can be a separate v2 adapter if you want large-task delegation without filling the main context.

## Test the installer

```bash
python3 tests/test_install_bridge.py
```

The tests cover installation, backup creation, copying project-scoped skills, preserving the stock sub-agent route, repeat installation, dry-run behavior, and failure on an unknown workflow layout.

## Repository layout

```text
trellis-matt-bridge/
├── README.md
├── NOTICE.md
├── LICENSE
├── scripts/
│   └── install_bridge.py
├── tests/
│   └── test_install_bridge.py
└── skills/
    ├── trellis-matt-plan/
    │   ├── SKILL.md
    │   └── agents/openai.yaml
    ├── trellis-matt-implement/
    │   ├── SKILL.md
    │   └── agents/openai.yaml
    └── trellis-matt-check/
        ├── SKILL.md
        └── agents/openai.yaml
```

## License / upstream projects

This repository contains only the bridge code and adapter instructions. It does not include upstream Matt skills or Trellis source. See `NOTICE.md` for upstream licensing notes.

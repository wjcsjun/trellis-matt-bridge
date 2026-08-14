# trellis-matt-bridge

**English** | [简体中文](./README.zh-CN.md)

A small **multi-agent bridge for Codex + Claude Code** that keeps **Trellis as the workflow/lifecycle owner** while using **Matt Pocock's engineering methods inside selected phases**.

This repo deliberately does **not** vendor or fork either upstream project:

- Matt Pocock skills: https://github.com/mattpocock/skills
- Trellis: https://github.com/mindfold-ai/trellis

The design rule is unchanged from v1:

> **One phase, one owner. Trellis owns lifecycle; Matt methods provide the engineering discipline inside the phase.**

## v2 architecture

```text
                         Trellis lifecycle / state machine
                                      |
              +-----------------------+-----------------------+
              |                                               |
           planning                                       in_progress
              |                                               |
              v                                               |
      trellis-matt-plan                        +--------------+--------------+
      grilling/domain model                    |                             |
      -> Trellis artifacts                  Codex                        Claude Code
                                               |                             |
                                               v                             v
                                  trellis-matt-implement         Trellis trellis-implement
                                  trellis-matt-check             sub-agent
                                               |                 + preloaded bridge adapter
                                               |                 + Matt tdd/design/debug
                                               |                             |
                                               |                             v
                                               |                 Trellis trellis-check
                                               |                 sub-agent
                                               |                 + two-axis bridge review
                                               +-------------+---------------+
                                                             |
                                                             v
                                                   Trellis Phase 3
                                                   update-spec -> commit
                                                   -> finish/archive
```

### Codex profile

Codex keeps the v1 strategy: **inline execution**. Current Trellis defaults Codex to `auto`, which dispatches native sub-agents, so this bridge requires the target project to set `codex.dispatch_mode: inline` explicitly. The installer places the three bridge skills under `.agents/skills/` and rewrites only the Codex-inline implementation/check routing.

The v2 Codex adapter does **not** Matt-power Trellis's Codex sub-agent route. As a safety check, installation stops before writing unless `.trellis/config.yaml` explicitly selects `codex.dispatch_mode: inline`. An omitted setting resolves to Trellis's current `auto` default and is rejected, as are explicit `auto` and `sub-agent` values.

### Claude Code profile

Claude Code uses the opposite strategy: **keep Trellis's native sub-agents**.

The installer:

1. installs the three bridge skills under `.claude/skills/`;
2. keeps `trellis-implement` and `trellis-check` as the Phase 2 owners;
3. patches `.claude/agents/trellis-implement.md` so its `skills:` frontmatter preloads:
   - `trellis-matt-implement`
   - `mattpocock-skills:tdd`
   - `mattpocock-skills:codebase-design`
   - `mattpocock-skills:diagnosing-bugs`
4. patches `.claude/agents/trellis-check.md` to preload `trellis-matt-check`;
5. writes a managed policy block to `CLAUDE.md`.

Matt's `code-review` is **not** preloaded into the Trellis check sub-agent. Current Claude Code can nest sub-agents, but running `code-review` there would create a second review orchestrator inside Trellis's check phase and blur phase ownership. `trellis-matt-check` therefore performs the same Spec-vs-Standards split inline inside the Trellis check agent.

## Why not call Matt's top-level `implement` directly?

Matt's top-level `implement` finishes with review and a git commit. Trellis Phase 3 owns spec promotion, dirty-file classification, commit planning/approval, commit execution, and finish/archive. Calling both creates duplicate ownership.

The bridge therefore uses Matt's engineering primitives but reserves these operations for Trellis:

- task status transitions;
- spec promotion;
- commit planning and commit execution;
- push policy;
- task finish/archive and journal bookkeeping.

## Prerequisites

Install and initialize Trellis in the target repository first:

```bash
npm install -g @mindfoldhq/trellis@latest
cd /path/to/project

# Claude only
trellis init --claude -u YOUR_NAME

# Codex only
trellis init --codex -u YOUR_NAME

# Both
trellis init --claude --codex -u YOUR_NAME
```

### Matt skills for Claude Code

Use Matt's native Claude Code plugin:

```bash
claude plugins install mattpocock-skills
```

The Claude profile can still install without the plugin; missing optional Matt plugin skills are skipped by Claude Code and the bridge adapter contains a fallback discipline. For the intended integration, install the plugin.

### Matt skills for Codex

Install the upstream skills through the Agent Skills installer:

```bash
npx skills@latest add mattpocock/skills
```

The most useful skills for this bridge are `grilling`, `domain-modeling`, `tdd`, `codebase-design`, and `diagnosing-bugs`.

## Install the bridge

### Auto-detect configured platforms

```bash
python3 scripts/install_bridge.py /path/to/project
```

`auto` detection installs:

- Codex when `.codex/` exists;
- Claude Code when Trellis `.claude/agents/trellis-implement.md` and `trellis-check.md` exist;
- both when both platform configurations are present.

### Explicit profiles

```bash
python3 scripts/install_bridge.py /path/to/project --profile codex
python3 scripts/install_bridge.py /path/to/project --profile claude
python3 scripts/install_bridge.py /path/to/project --profile both
```

Preview every text change without writing:

```bash
python3 scripts/install_bridge.py /path/to/project --profile both --dry-run
```

### Codex dispatch-mode preflight

The Codex profile is intentionally inline-only in v2. Configure the target project explicitly:

```yaml
codex:
  dispatch_mode: inline
```

Before calculating or writing patches, the installer checks `.trellis/config.yaml`:

- `codex.dispatch_mode: inline` -> supported;
- missing `codex:` / missing `dispatch_mode` -> resolves to Trellis's current `auto` default and is rejected;
- explicit `auto`, `sub-agent`, or any other non-inline value -> exit before changing `workflow.md`, `AGENTS.md`, backups, or skill directories.

This prevents a misleading partial install where planning is bridged but Codex implementation/check are still owned by Trellis's stock sub-agents.

After installation, inspect:

```bash
git diff
```

Restart the relevant agent session. Claude Code sub-agent definitions are loaded at session start, so a restart is required after the installer edits `.claude/agents/`.

## How the workflow is patched

Trellis owns `.trellis/workflow.md`, so the bridge edits it as narrowly as it can:

- **Phase 1.1** keeps Trellis's own requirement-exploration guidance. The bridge inserts a managed `<!-- TRELLIS-MATT-BRIDGE -->` block under the heading, so platforms without the bridge still read the stock `trellis-brainstorm` path, and a later `trellis update` can rewrite that prose without the bridge discarding it.
- **`[workflow-state:*]` blocks** are matched only when the tags own a whole line. Trellis's maintainer comment lists the same tag names as indented prose; an unanchored match starts there and swallows the sections in between.
- **Platform groups** are read from the file rather than hardcoded. When `codex-inline` is split out of a shared group, the remaining members are re-emitted exactly as found, so a platform Trellis adds later (0.6.15 added `DeepSeek Harness`) keeps its instructions.

After patching and before writing, the installer verifies that no `[workflow-state:*]` block, heading, or platform name disappeared and that HTML comments stayed balanced. A patch that fails that check aborts without touching the file.

## What the installer changes

Common:

```text
.trellis/workflow.md
.trellis/workflow.md.pre-trellis-matt-bridge   # first-install backup
```

Codex profile:

```text
AGENTS.md
.agents/skills/
├── trellis-matt-plan/
├── trellis-matt-implement/
└── trellis-matt-check/
```

Claude profile:

```text
CLAUDE.md
.claude/
├── agents/
│   ├── trellis-implement.md
│   ├── trellis-implement.md.pre-trellis-matt-bridge
│   ├── trellis-check.md
│   └── trellis-check.md.pre-trellis-matt-bridge
└── skills/
    ├── trellis-matt-plan/
    ├── trellis-matt-implement/
    └── trellis-matt-check/
```

The installer is idempotent: managed policy blocks are updated rather than duplicated, skill directories are refreshed, and backups are created only once.

## Adapter skills

### `trellis-matt-plan`

Runs only while the Trellis task is `planning`. It uses one-question grilling and domain modeling, writes decisions into Trellis's `prd.md` / `design.md` / `implement.md`, and never starts the task or edits production code.

Trellis's stock Phase 1.1 guidance stays in `workflow.md` alongside the bridge block, so platforms without the bridge are unaffected.

On Claude Code it prefers the plugin namespace (`mattpocock-skills:grilling`, `mattpocock-skills:domain-modeling`). On Codex/skills.sh it uses the unscoped skill names when installed.

### `trellis-matt-implement`

Runs only after Trellis moves the task to `in_progress`. It uses agreed seams, vertical-slice TDD, deep-module design, and disciplined diagnosis. It never commits, pushes, promotes specs, or finishes the task.

In Claude Code this skill is preloaded into Trellis's `trellis-implement` sub-agent rather than replacing that sub-agent.

### `trellis-matt-check`

Reviews two independent axes:

- **Spec fidelity** — requirements, design constraints, seams, validation, and scope;
- **Engineering standards** — project conventions, domain vocabulary, module boundaries, behavior-focused tests, and relevant design smells.

It may repair in-scope findings and rerun validation but never commits or finishes the task.

## Upgrading Trellis

Trellis owns `.trellis/workflow.md` and platform templates, so after a Trellis update reapply the bridge:

```bash
trellis update
python3 /path/to/trellis-matt-bridge/scripts/install_bridge.py /path/to/project --profile auto
git diff
```

The installer patches structural Markdown anchors instead of replacing the whole workflow. If a future Trellis release changes the required anchors, it exits before writing rather than guessing; if an anchor still matches but the resulting patch would drop a state block, heading, or platform, the structural check rejects it before writing.

For Claude Code, `trellis update` may also refresh `.claude/agents/trellis-implement.md` and `trellis-check.md`; rerunning the bridge restores the `skills:` preloads while preserving other existing skills.

## Test the installer

```bash
python3 tests/test_install_bridge.py
```

Tests cover:

- Codex-only installation and idempotence;
- Codex dispatch-mode preflight (explicit `inline` accepted; missing, `auto`, and `sub-agent` rejected before writes);
- Claude-only installation and sub-agent skill preloading;
- preservation of non-Claude platform routing;
- `[workflow-state:*]` blocks matched by whole line, not by the maintainer comment's prose mentions;
- survival of extra platforms in the shared `codex-inline` group;
- Trellis's stock Phase 1.1 guidance surviving the bridge insert;
- the structural integrity check rejecting a lossy patch;
- automatic dual-profile detection;
- dry-run behavior;
- first-install backups;
- failure on an unknown workflow layout.

The fixture reproduces the structural hazards of a real `.trellis/workflow.md` rather than only the anchors the installer looks for. It can still drift from upstream, so run the end-to-end check against a real file before releasing:

```bash
npm pack @mindfoldhq/trellis@latest
tar xzf mindfoldhq-trellis-*.tgz
TRELLIS_WORKFLOW_MD=package/dist/templates/trellis/workflow.md \
  python3 tests/test_install_bridge.py
```

That path also accepts an initialized project's `.trellis/workflow.md`. It installs both profiles, asserts nothing was dropped, asserts the file only grew, and reruns to confirm idempotence.

## Repository layout

```text
trellis-matt-bridge/
├── README.md
├── README.zh-CN.md
├── CHANGELOG.md
├── NOTICE.md
├── LICENSE
├── .gitignore
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

`dist/` is intentionally ignored by git. If you generate release archives locally, publish them as GitHub Release assets rather than committing them to the repository.

## License / upstream projects

This repository contains bridge code and adapter instructions only. It does not include Trellis or Matt Pocock's upstream source. See `NOTICE.md` for upstream licensing notes.

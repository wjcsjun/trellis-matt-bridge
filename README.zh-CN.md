# trellis-matt-bridge

[English](./README.md) | **简体中文**

一个面向 **Codex + Claude Code** 的轻量桥接层：

- 由 **Trellis** 负责工作流、任务状态和生命周期；
- 在规划、实现和检查阶段，引入 **Matt Pocock Skills** 的工程方法；
- 避免 Trellis 和 Matt 的完整工作流同时接管任务、Review 和 Git commit。

核心原则：

> **One phase, one owner.**
>
> **一个阶段只能有一个负责人：Trellis 管生命周期，Matt 提供阶段内部的工程方法。**

---

## 为什么需要这个项目？

[Trellis](https://github.com/mindfold-ai/trellis) 和 [Matt Pocock Skills](https://github.com/mattpocock/skills) 都能显著增强 Coding Agent 的工程能力，但两者的定位并不完全相同。

Trellis 更擅长：

- 管理任务状态；
- 保存 PRD、Design、Implementation Plan；
- 注入项目规范和上下文；
- 调度 implementation / check agent；
- 更新 spec；
- 管理 commit 和任务结束流程。

Matt 的 Skills 更擅长：

- `grilling`：通过逐个问题澄清需求；
- `domain-modeling`：建立领域模型和统一语言；
- `tdd`：测试驱动开发；
- `codebase-design`：改善模块和代码结构；
- `diagnosing-bugs`：系统化定位问题；
- `code-review`：从 Spec 和 Engineering Standards 两个维度 Review。

问题在于：

**如果直接同时运行两套完整 workflow，就会出现重复所有权。**

例如 Matt 的顶层 `implement` workflow 最后可能负责 review 和 commit，而 Trellis 的 Phase 3 同样负责：

- spec promotion；
- dirty files 分类；
- commit plan；
- commit approval；
- git commit；
- finish / archive。

因此本项目不把两个项目粗暴“拼在一起”，而是提供一个 **bridge / adapter layer**。

---

# 架构

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
                                               |                 + bridge adapter
                                               |                 + Matt TDD/design/debug
                                               |                             |
                                               |                             v
                                               |                 Trellis trellis-check
                                               |                 sub-agent
                                               |                 + two-axis review
                                               +-------------+---------------+
                                                             |
                                                             v
                                                   Trellis Phase 3
                                                   update-spec
                                                       ↓
                                                     commit
                                                       ↓
                                                finish / archive
```

Trellis 始终是 workflow owner。

Matt 的方法只在各阶段内部提供工程能力。

---

# 支持的平台

当前 v2 支持：

- **Codex**
- **Claude Code**

两者采用不同的集成策略。

---

# Codex

Codex 使用 **inline 模式**。

执行流程：

```text
Trellis planning
      ↓
trellis-matt-plan
      ↓
Trellis task start
      ↓
trellis-matt-implement
      ↓
trellis-matt-check
      ↓
Trellis update-spec
      ↓
Trellis commit
      ↓
finish/archive
```

Bridge Skills 安装到：

```text
.agents/skills/
├── trellis-matt-plan/
├── trellis-matt-implement/
└── trellis-matt-check/
```

同时修改：

```text
AGENTS.md
.trellis/workflow.md
```

## Codex dispatch mode

当前 v2 的 Codex profile **只支持 Trellis inline 模式**。

安装器会检查：

```text
.trellis/config.yaml
```

以下情况允许安装：

```yaml
codex:
  dispatch_mode: inline
```

或者完全没有设置 `dispatch_mode`。

如果显式配置成：

```yaml
codex:
  dispatch_mode: sub-agent
```

安装器会在修改任何文件之前停止。

这是为了避免出现：

```text
planning 使用了 Matt bridge
        ↓
implementation 却仍然走 Trellis stock sub-agent
```

这样的“半安装”状态。

---

# Claude Code

Claude Code 不采用 Codex 的 inline 方式，而是**保留 Trellis 原生 sub-agent 架构**。

执行流程：

```text
Claude main session
        ↓
Trellis
        ↓
trellis-implement sub-agent
        ├── trellis-matt-implement
        ├── mattpocock-skills:tdd
        ├── mattpocock-skills:codebase-design
        └── mattpocock-skills:diagnosing-bugs
        ↓
trellis-check sub-agent
        └── trellis-matt-check
        ↓
Trellis Phase 3
        ↓
update-spec → commit → finish
```

Bridge Skills 安装到：

```text
.claude/skills/
├── trellis-matt-plan/
├── trellis-matt-implement/
└── trellis-matt-check/
```

安装器还会修改：

```text
CLAUDE.md

.claude/agents/
├── trellis-implement.md
└── trellis-check.md
```

通过 Claude Code agent frontmatter 的 `skills:` 字段，把 bridge 和 Matt engineering skills 预加载到 Trellis sub-agent 中。

---

# 为什么 Claude 的 check agent 不直接调用 Matt `code-review`？

Matt 的 `code-review` 本身是一个 orchestration workflow，会再启动独立的 review agents。

而本项目希望：

```text
Trellis trellis-check
```

始终是 Quality Check 阶段的唯一 owner。

因此 `trellis-matt-check` 不直接运行 Matt 顶层 `code-review`，而是在当前 Trellis check agent 内完成同样重要的两条检查轴：

### Spec Fidelity

检查：

- Acceptance Criteria；
- PRD；
- Design constraints；
- implementation plan；
- 约定的 test seams；
- scope；
- validation。

### Engineering Standards

检查：

- 项目规范；
- domain vocabulary；
- module boundaries；
- 行为导向测试；
- lint / type-check / tests；
- 与当前任务相关的 code smells。

这样既保留 Matt 的 Review 思路，又不会产生第二套 workflow owner。

---

# 三个 Bridge Skills

## `trellis-matt-plan`

用于 Trellis `planning` 阶段。

主要负责：

- Matt-style one-question grilling；
- domain modeling；
- 澄清真实需求；
- 明确 acceptance criteria；
- 形成 implementation slices。

结果写回 Trellis：

```text
.trellis/tasks/<task>/
├── prd.md
├── design.md
├── implement.md
└── research/
```

它不会：

- 修改 production code；
- 执行 `task.py start`；
- commit。

---

## `trellis-matt-implement`

用于已经进入：

```text
in_progress
```

状态的任务。

主要使用：

- vertical-slice TDD；
- codebase design；
- disciplined debugging；
- task artifacts；
- `.trellis/spec/`；
- task research。

它可以实现代码和运行验证。

但它不会：

```text
git commit
git push
update-spec
finish task
archive task
```

这些操作仍由 Trellis 负责。

---

## `trellis-matt-check`

实现两个独立 Review 维度：

```text
Spec Fidelity
+
Engineering Standards
```

它可以：

- 检查完整 diff；
- 修复明确且属于当前 scope 的问题；
- 重新运行 validation；
- 重复 check → fix → check。

但不会：

- commit；
- promote spec；
- finish task。

---

# 信息应该放在哪里？

为了避免 AI 在多个文件里重复保存同一事实，本项目建议：

| 信息 | 位置 |
|---|---|
| 产品需求 / Acceptance Criteria | `.trellis/tasks/<task>/prd.md` |
| 当前任务的架构与 trade-offs | `.trellis/tasks/<task>/design.md` |
| Implementation slices / validation | `.trellis/tasks/<task>/implement.md` |
| 当前任务 research | `.trellis/tasks/<task>/research/` |
| 可复用工程规范 | `.trellis/spec/` |
| Domain vocabulary | `CONTEXT.md` 或项目映射的 context |
| 难以逆转的重要架构决定 | ADR |

原则是：

> **同一个事实尽量只有一个 canonical location。**

---

# 安装

## 1. 安装 Trellis

```bash
npm install -g @mindfoldhq/trellis@latest
```

进入你的项目：

```bash
cd /path/to/project
```

### Claude Code

```bash
trellis init --claude -u YOUR_NAME
```

### Codex

```bash
trellis init --codex -u YOUR_NAME
```

### Claude Code + Codex

```bash
trellis init --claude --codex -u YOUR_NAME
```

---

# 安装 Matt Skills

## Claude Code

推荐使用 Matt 官方 Claude Code plugin：

```bash
claude plugins install mattpocock-skills
```

主要使用：

```text
grilling
domain-modeling
tdd
codebase-design
diagnosing-bugs
```

---

## Codex

使用 Agent Skills installer：

```bash
npx skills@latest add mattpocock/skills
```

建议安装：

```text
grilling
domain-modeling
tdd
codebase-design
diagnosing-bugs
```

---

# 安装 trellis-matt-bridge

Clone：

```bash
git clone https://github.com/wjcsjun/trellis-matt-bridge.git
cd trellis-matt-bridge
```

然后：

```bash
python3 scripts/install_bridge.py /path/to/your-project
```

默认：

```text
--profile auto
```

会自动检测已经初始化的平台。

---

## 指定平台

Codex：

```bash
python3 scripts/install_bridge.py /path/to/project --profile codex
```

Claude Code：

```bash
python3 scripts/install_bridge.py /path/to/project --profile claude
```

同时安装：

```bash
python3 scripts/install_bridge.py /path/to/project --profile both
```

---

# Dry Run

强烈建议第一次先执行：

```bash
python3 scripts/install_bridge.py /path/to/project --profile both --dry-run
```

它只显示准备进行的修改，不会写文件。

确认后再正式安装：

```bash
python3 scripts/install_bridge.py /path/to/project --profile both
```

最后检查：

```bash
git diff
```

---

# 安装器会修改什么？

公共文件：

```text
.trellis/workflow.md
```

首次安装会生成：

```text
.trellis/workflow.md.pre-trellis-matt-bridge
```

作为原始备份。

---

## Codex

```text
AGENTS.md

.agents/skills/
├── trellis-matt-plan/
├── trellis-matt-implement/
└── trellis-matt-check/
```

---

## Claude Code

```text
CLAUDE.md

.claude/
├── agents/
│   ├── trellis-implement.md
│   ├── trellis-implement.md.pre-trellis-matt-bridge
│   ├── trellis-check.md
│   └── trellis-check.md.pre-trellis-matt-bridge
│
└── skills/
    ├── trellis-matt-plan/
    ├── trellis-matt-implement/
    └── trellis-matt-check/
```

安装器是幂等的。

重复运行不会不断追加同一个 managed block。

---

# Trellis 升级以后

Trellis 升级可能更新：

```text
.trellis/workflow.md
```

以及 Claude agent templates。

因此建议：

```bash
trellis update

python3 /path/to/trellis-matt-bridge/scripts/install_bridge.py \
  /path/to/project \
  --profile auto

git diff
```

Bridge 不会整份替换 Trellis workflow，而是基于结构化 Markdown anchors 进行修改。

如果未来 Trellis 改变了这些关键结构，安装器会：

> **拒绝修改，而不是猜测应该怎么 patch。**

---

# 测试

运行：

```bash
python3 tests/test_install_bridge.py
```

当前测试覆盖：

- Codex-only 安装；
- Claude-only 安装；
- Codex + Claude 自动检测；
- profile 顺序追加；
- 幂等安装；
- dry-run；
- backup；
- Codex inline dispatch preflight；
- 显式 `sub-agent` 的 fail-fast；
- Claude sub-agent skill preload；
- 保留其他 Trellis 平台路由；
- 未知 Trellis workflow layout 的 fail-safe。

成功时：

```text
ok: v2.0.1 installer tests passed
```

---

# Repository Structure

```text
trellis-matt-bridge/
├── .gitignore
├── README.md
├── README.zh-CN.md
├── CHANGELOG.md
├── NOTICE.md
├── LICENSE
│
├── scripts/
│   └── install_bridge.py
│
├── tests/
│   └── test_install_bridge.py
│
└── skills/
    ├── trellis-matt-plan/
    │   ├── SKILL.md
    │   └── agents/openai.yaml
    │
    ├── trellis-matt-implement/
    │   ├── SKILL.md
    │   └── agents/openai.yaml
    │
    └── trellis-matt-check/
        ├── SKILL.md
        └── agents/openai.yaml
```

`dist/` 被 `.gitignore` 忽略。

如果本地生成 release archive，建议作为 **GitHub Release Asset** 发布，而不是提交到 Git repository。

---

# 与上游项目的关系

本项目：

- 不包含 Trellis 源码；
- 不包含 Matt Pocock Skills 源码；
- 不 fork 两个上游项目；
- 只提供 bridge code 和 adapter instructions。

上游项目：

- Trellis  
  https://github.com/mindfold-ai/trellis
- Matt Pocock Skills  
  https://github.com/mattpocock/skills

详细许可说明见：

```text
NOTICE.md
```

---

# 设计哲学

这个项目不是要创建第三套完整 Coding Agent workflow。

它只解决一件事：

> **让 Trellis 和 Matt Skills 各自做自己最擅长的部分。**

Trellis：

```text
State
Task
Context
Spec
Commit
Finish
```

Matt：

```text
Grilling
Domain Modeling
TDD
Design
Debugging
Review Discipline
```

Bridge：

```text
明确谁在什么时候负责什么
```

最终目标是：

```text
更好的需求
    ↓
更好的实现计划
    ↓
更严格的工程执行
    ↓
更可靠的 Review
    ↓
仍然只有一个清晰的 workflow owner
```

---

## License

本项目遵循仓库中的 `LICENSE`。

第三方项目许可证请参阅 `NOTICE.md`。
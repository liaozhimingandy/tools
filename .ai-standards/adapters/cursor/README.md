# Cursor 适配器

> 让 Cursor 读取同一套公共规范与 Skills。
> 能力状态见 [`../../docs/architecture/tool-compatibility.md`](../../docs/architecture/tool-compatibility.md)；官方依据见 [`references.md`](references.md)；逐项映射见 [`mappings.md`](mappings.md)。

---

## 1. 用途与范围

把公共规范 `core/`、`standards/`、`skills/`、`agents/` 适配到 Cursor 的三类机制：**Project Rules（`.cursor/rules/*.mdc`）**、**Agent Skills**、**Subagents**。Cursor 是各工具中**格式约束最强**的一个：Project Rules 必须是 `.mdc` + frontmatter。

- 支持的工具：Cursor（Editor / CLI / Cloud Agents，能力因 surface 而异，见 §8）。
- 参考的官方文档日期：**2026-11-11**。
- 公共规范版本：`1.0.0`（本阶段未改动）。

## 2. 官方文档

| 主题 | 文档标题 | URL | 来源 |
| --- | --- | --- | --- |
| 规则 | Rules \| Cursor Docs | `https://cursor.com/docs/rules` | [A] |
| Skills | Agent Skills \| Cursor Docs | `https://cursor.com/docs/context/skills` | [A] |
| Subagents | Subagents \| Cursor Docs | `https://cursor.com/docs/agent/subagents` | [A] |
| Hooks | Hooks \| Cursor Docs | `https://cursor.com/docs/hooks` | [A]（请求 `/agent/hooks` 重定向至此） |

## 3. 安装方式（仅说明，本阶段不实现）

| 源（本仓库） | 目标（项目根，POSIX） | 类别 | 说明 |
| --- | --- | --- | --- |
| `adapters/cursor/rules/ai-engineering-standards.mdc` | `.cursor/rules/ai-engineering-standards.mdc` | additive | 唯一文件名，与用户规则并存 |
| `skills/<name>/` | `.cursor/skills/<name>/` | 复制 | 官方项目级路径之一，内容逐字节一致 |
| 公共规范镜像 | `.ai-standards/` | 只读镜像 | 规则索引里的路径安装后仍成立 |

> Cursor **没有**"项目根单入口文件"的原生概念（Project Rules 都是 `.mdc`）。因此本适配器只提供**可叠加规则**，不设 guarded 入口——这也是它与 Codex/Claude/Copilot 的结构差异。

## 4. 规则加载方式

- **Project Rules**：位于 `.cursor/rules/`，**必须 `.mdc`**；该目录下的 `.md` 会被忽略（无 frontmatter 指定 `description`/`globs`/`alwaysApply`）[A]。
- **frontmatter 三字段交互** [A]：

  | `alwaysApply` | `description` | `globs` | 行为 |
  | --- | --- | --- | --- |
  | `true` | — | — | 每次会话包含，忽略其余 |
  | `false` | — | 提供 | 匹配文件进入上下文时自动附加 |
  | `false` | 提供 | 省略 | Agent 依描述判断相关性后拉取 |
  | `false` | 省略 | 省略 | 仅 `@`-提及时使用 |

- **本仓库选择**：`alwaysApply: true` + `description`，让通用红线**每次会话都常驻**；不设 `globs`（因为它对所有任务适用）。技术栈级规则若未来要加，另建带 `globs` 的独立 `.mdc`（见 `mappings.md` §5）。
- **`@file` 引用**：官方明确"只提示 Agent 去读、不内联内容"（editor / CLI / Cloud Agents 一致）[A]；故规则正文用反引号写镜像路径，符合"需手动引用"。
- **优先级**：Team → Project → User，早者优先；User Rules 在 Customize UI 配置（**磁盘无项目可写路径**，本仓库不写）。
- **AGENTS.md**：Cursor 官方支持 AGENTS.md 作为简易替代并支持子目录，但本项目统一用 `.mdc`（更明确的适用控制），不额外写 AGENTS.md 以免与 Codex 入口重复。

## 5. Skills 加载方式

- **发现路径**：项目级 `.agents/skills/`、`.cursor/skills/`；用户级 `~/.agents/skills/`、`~/.cursor/skills/`；**兼容加载** `.claude/skills/`、`.codex/skills/` [A]。
- **复用方式**：5 个公共 `SKILL.md` 逐字节复制到 `.cursor/skills/`；官方启动时自动递归发现，嵌套目录自动限定作用域（无需 `paths`）。
- **Frontmatter**：官方 `name`（必填、须匹配父目录名）、`description`（必填），可选 `paths`/`disable-model-invocation`/`icon`/`color`/`metadata`。本仓库**只用 6 个标准字段**，不写 Cursor 扩展字段，保持工具无关。
- **调用**：Agent 对话输入 `/` 搜索技能名手动调用，或按 `description` 自动选择。
- **Cloud Agents**：用户级技能需开启 "Sync Skills for Cloud Agents"；**自动化运行不加载用户级技能**——故本仓库只用项目级 `.cursor/skills/`。

## 6. Agent（Subagents）支持情况

官方支持 `.cursor/agents/*.md`（项目，兼容 `.claude/agents/`、`.codex/agents/`），Markdown + YAML frontmatter，**独立上下文、可并行** [A]。字段官方确认，可给出映射模板。

| 公共角色 | 目标文件 | 官方字段 | 本仓库处置 |
| --- | --- | --- | --- |
| `architect.md` | `.cursor/agents/architect.md` | `name`/`description`（可选，建议写）、`model`/`readonly`/`is_background` | 正文复用 + 字段提取 |
| `developer.md` | `.cursor/agents/developer.md` | 同上 | 同上 |
| `reviewer.md` | `.cursor/agents/reviewer.md` | 同上 | 同上 |
| `tester.md` | `.cursor/agents/tester.md` | 同上 | 同上 |

- **不得混淆**：Subagents（独立上下文、被委派任务）≠ Rules（常驻指令）≠ Skills（按需工作流）≠ Hooks（生命周期脚本）。本适配器四类分别处理。
- 本阶段只提供映射模板，不生成可安装 agent 文件（安装属 Phase 5）。

## 7. Hooks 能力边界

官方支持且能力强：`.cursor/hooks.json`（项目）/ `~/.cursor/hooks.json`（用户），`version: 1`，事件含 `preToolUse`/`postToolUse`/`beforeShellExecution`/`afterFileEdit` 等，exit 2 阻断，`failClosed` 控失败放行，优先级 Enterprise → Team → Project → User [A]。Cloud Agents 只跑 command-based hooks。按用户要求，本阶段**只记录能力、不创建 `hooks.json`**。

## 8. 已知限制

1. Project Rules 必须 `.mdc`；放 `.md` 会被静默忽略（这是最常见的接入错误）。
2. `icon` / `color` 等扩展字段跨版本表现 `UNVERIFIED`；本仓库不使用。
3. User Rules 无磁盘路径（在 Customize UI），本仓库不写；Team Rules 需 dashboard，属组织级运维。
4. 用户级技能在 Automation 运行中不加载；本仓库只用项目级。
5. 未在真实 Cursor 客户端运行时验证。

## 9. 相关文档

- 映射明细：[`mappings.md`](mappings.md) · 官方参考：[`references.md`](references.md) · 模板：[`templates/`](templates/)
- 统一映射架构：[`../README.md`](../README.md) · 公共角色契约：[`../../agents/`](../../agents/)

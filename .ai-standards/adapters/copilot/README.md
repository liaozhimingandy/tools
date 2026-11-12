# GitHub Copilot 适配器

> 让 GitHub Copilot 读取同一套公共规范与 Skills。
> 能力状态见 [`../../docs/architecture/tool-compatibility.md`](../../docs/architecture/tool-compatibility.md)；官方依据见 [`references.md`](references.md)；逐项映射见 [`mappings.md`](mappings.md)。

---

## 1. 用途与范围

把公共规范 `core/`、`standards/`、`skills/`、`agents/` 适配到 Copilot 的四类机制：**仓库级指令**、**路径级指令**、**Agent Skills**、**Custom Agents**。

- 支持的工具：GitHub Copilot（Copilot Chat / CLI / cloud agent / code review / VS Code / JetBrains / Eclipse / Xcode，支持矩阵高度依赖环境，见 §8）。
- 参考的官方文档日期：**2026-11-11**。
- 公共规范版本：`1.0.0`（本阶段未改动）。

> **Phase 4 相对 Phase 1 的更新**：官方现已明确支持 **Agent Hooks**（`.github/hooks/*.json`）与 **Custom Agents**（`.github/agents/*.md`）。本阶段据实纳入能力矩阵与映射说明，但按用户要求**不生成 Hooks 自动化**。

## 2. 官方文档

| 主题 | 文档标题 | URL | 来源 |
| --- | --- | --- | --- |
| 指令支持矩阵 | Support for different types of custom instructions | `https://docs.github.com/en/copilot/reference/custom-instructions-support` | [A] |
| Agent Skills | Agent skills | `https://docs.github.com/en/copilot/concepts/customizations/agent-skills` | [A] |
| Hooks | Hooks for GitHub Copilot | `https://docs.github.com/en/copilot/concepts/customizations/hooks` | [A] |
| Custom Agents | About custom agents | `https://docs.github.com/en/copilot/concepts/agents/cloud-agent/about-custom-agents` | [A] 官方站点检索索引 |
| 定制对照表 | Copilot customization cheat sheet | `https://docs.github.com/en/copilot/reference/customization-cheat-sheet` | [A] 官方站点检索索引 |
| 功能矩阵 | Copilot feature matrix | `https://docs.github.com/en/copilot/reference/copilot-feature-matrix` | [A] |

## 3. 安装方式（仅说明，本阶段不实现）

| 源（本仓库） | 目标（项目根，POSIX） | 类别 | 说明 |
| --- | --- | --- | --- |
| `adapters/copilot/copilot-instructions.md` | `.github/copilot-instructions.md` | guarded | 仓库级；用户已占用则跳过 |
| `adapters/copilot/instructions.md` | `.github/instructions/ai-engineering-standards.instructions.md` | additive | 路径级，需 `applyTo`，唯一文件名 |
| `skills/<name>/` | `.github/skills/<name>/` | 复制 | 官方项目级路径之一，逐字节一致 |
| 公共规范镜像 | `.ai-standards/` | 只读镜像 | 指令索引里的路径安装后仍成立 |

> **双指令通道**：GitHub.com 上**路径级指令目前仅 cloud agent 与 code review 支持**，IDE 支持随版本不同 [A]。故同时提供仓库级（覆盖面最广）与路径级（可叠加、低冲突），规避单一通道不生效。

## 4. 规则加载方式

- **仓库级**：`.github/copilot-instructions.md`，纯 Markdown，作用于仓库上下文所有请求；本文件即安装到此位置。
- **路径级**：`.github/instructions/**/*.instructions.md`，**必须**含 `applyTo` frontmatter（glob）。本仓库用 `applyTo: "**"` + 唯一文件名，作为**可叠加通道**——即使仓库级被用户占用也仍生效。
- **Agent 指令**：Copilot 也读 `AGENTS.md` / `CLAUDE.md` / `GEMINI.md`（依 surface 而异），但本仓库**不重复投放**这些入口以免与 Codex/Claude 适配器冲突。
- **优先级**：Personal > Repository > Organization；相关指令**同时**提供，故本仓库只写不与用户规则冲突的通用红线。
- **文件引用**：未找到官方确认的 Markdown 内联 `@import` 语法（`UNVERIFIED`），故指令正文用反引号写明 `.ai-standards/` 路径让 Copilot 自行读取，不假设会被内联。
- **读取分支**：Copilot code review 从 **head branch** 读取指令与 Skills，不是 base branch [A]——故这些文件必须提交到被审查分支。

## 5. Skills 加载方式

- **发现路径**：项目级 `.github/skills/`、`.claude/skills/`、`.agents/skills/`；个人级 `~/.copilot/skills/`、`~/.agents/skills/` [A]。
- **复用方式**：5 个公共 `SKILL.md` 逐字节复制到 `.github/skills/`，`scripts/` `references/` `assets/` 一并复制。
- **Frontmatter**：官方要求 `name`（通常等于目录名）、`description`，可选 `license`；只用开放规范字段，逐字节复用。
- **调用**：由 Agent 按 `description` 自动发现、按需加载；可用 `gh skill` 发现安装其它技能。
- **surface**：Copilot app / CLI / cloud agent / code review / VS Code·Visual Studio·JetBrains 的 agent mode；**IDE 支持取决于版本**（见 feature matrix）。

## 6. Agent（Custom Agents）支持情况

官方支持 **agent profile**：`.github/agents/NAME.md`（仓库级），Markdown + YAML frontmatter，指定 `name`（可选）、`description`（必填）、`tools`、`mcp-servers`、`model`、`target`，正文为 prompt（≤30,000 字符）[A]。

| 公共角色 | 目标文件 | 必填 | 可选（官方） | 表面覆盖 |
| --- | --- | --- | --- | --- |
| `architect.md` | `.github/agents/architect.md` | `description` | `name`/`tools`/`mcp-servers`/`model`/`target` | VS Code ✓ / JetBrains·Eclipse·Xcode 预览 |
| `developer.md` | `.github/agents/developer.md` | 同上 | 同上 | 同上 |
| `reviewer.md` | `.github/agents/reviewer.md` | 同上 | 同上 | 同上 |
| `tester.md` | `.github/agents/tester.md` | 同上 | 同上 | 同上 |

- **角色与配置分离**：正文 = 角色契约（逐字复用），`tools`/`mcp-servers` 等工具字段由目标项目定，不进公共源。
- **状态**：Custom Agents 在 JetBrains / Eclipse / Xcode 为**公开预览**，属 `PARTIAL`（见 `tool-compatibility.md`）。
- 本阶段只提供映射模板，不生成可安装的 agent profile（安装属 Phase 5）。

## 7. Hooks 能力边界

官方已支持：`.github/hooks/*.json`（仓库级）/ `~/.copilot/hooks/*.json`（CLI 个人），`version: 1`，事件含 `sessionStart`/`userPromptSubmitted`/`preToolUse`（可 approve/deny）/`postToolUse`/`agentStop` 等；cloud agent 仅支持子集且只用 `bash` 字段 [A]。支持面：Copilot app / CLI / cloud agent 正式，**VS Code 公开预览，多数 IDE 不支持**（cheat sheet [A]）→ 矩阵标 `PARTIAL`。按用户要求，本阶段**只记录能力、不创建 Hooks 自动化**。

## 8. 已知限制

1. **指令支持高度依赖 surface**：GitHub.com 路径级指令仅 cloud agent / code review；Eclipse 的 code review 不支持自定义指令（见 `references.md` §3 矩阵）。
2. **Skills IDE 版本差异大**：feature matrix 显示 VS Code 1.108.0 起才 `✓ Agent skills`，更早版本为 `✗` [A]。
3. 路径级指令在各 IDE 版本实际读取行为 `UNVERIFIED`（官方明示 "IDE support depends on the version"）。
4. 未找到 Markdown 内联 `@import` 官方语法（`UNVERIFIED`），不依赖它。
5. `excludeAgent` 跨 CLI / IDE 行为 `UNVERIFIED`，本仓库不设置该字段。
6. 未在真实 Copilot 客户端运行时验证。

## 9. 相关文档

- 映射明细：[`mappings.md`](mappings.md) · 官方参考：[`references.md`](references.md) · 模板：[`templates/`](templates/)
- 统一映射架构：[`../README.md`](../README.md) · 公共角色契约：[`../../agents/`](../../agents/)

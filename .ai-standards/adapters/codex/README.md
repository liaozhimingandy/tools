# Codex 适配器

> 让 OpenAI Codex 读取同一套公共规范与 Skills。
> 能力状态见 [`../../docs/architecture/tool-compatibility.md`](../../docs/architecture/tool-compatibility.md)；官方依据见 [`references.md`](references.md)；逐项映射见 [`mappings.md`](mappings.md)。

---

## 1. 用途与范围

把公共规范 `core/`、`standards/`、`skills/`、`agents/` 适配到 Codex 的两类机制：**项目级指令入口 `AGENTS.md`** 与 **Agent Skills 发现目录 `.agents/skills/`**。适配层不复制规范正文，只做"薄入口 + 按需索引 + 能力边界"。

- 支持的工具：OpenAI Codex（CLI / IDE 扩展 / Codex 应用，Skills 三端均可用 [B]）。
- 参考的官方文档日期：**2026-11-11**；未声明更低版本兼容（见本文 §7）。
- 公共规范版本：`1.0.0`（本阶段未改动）。

## 2. 官方文档

| 主题 | 文档标题 | URL | 来源 |
| --- | --- | --- | --- |
| 项目指令 | 使用 AGENTS.md 的自定义指令 | `https://developers.openai.ac.cn/codex/guides/agents-md` | [B] 官方中文镜像（英文页本次返回 Forbidden） |
| Skills | 智能体技能 (Agent Skills) | `https://developers.openai.ac.cn/codex/skills` | [B] 官方中文镜像 |
| Hooks | Hooks | `https://developers.openai.com/codex/hooks` | [B] 官方站点检索索引 |
| 配置 / 子代理 | Advanced Configuration | `https://developers.openai.com/codex/config-file/config-advanced` | [A] 正文直接抓取 |

## 3. 安装方式（仅说明，本阶段不实现）

由 Phase 5 安装器按目标路径复制，本阶段**只提供文件与契约**：

| 源（本仓库） | 目标（项目根，POSIX） | 类别 | 说明 |
| --- | --- | --- | --- |
| `adapters/codex/AGENTS.md` | `AGENTS.md` | guarded | 已存在入口被用户占用则跳过，改提示手工叠加 |
| `skills/<name>/` | `.agents/skills/<name>/` | 复制 | 官方 REPO 作用域，内容逐字节一致 |
| 公共规范镜像 | `.ai-standards/` | 只读镜像 | 保证入口索引里的相对路径安装后仍成立 |

> 模板：`templates/` 提供"用户自有 `AGENTS.md` 如何叠加公共规范"的片段，供 guarded 入口被占用时手工合并；安装器**不用模板覆盖用户文件**。

## 4. 规则加载方式

Codex 启动时构建**指令链**：全局 `~/.codex/AGENTS.md`（或 override）→ 从项目根向当前目录逐层取 `AGENTS.override.md` / `AGENTS.md`，每层最多一个，用空行拼接，越近越靠后、优先级越高，达 `project_doc_max_bytes`（默认 32 KiB）停止 [B]。

- **入口策略**：项目根 `AGENTS.md` 是薄适配层，只放 10 条红线 + 按需加载索引 + 能力边界；完整规范在 `.ai-standards/core/`、`.ai-standards/standards/`，由 Codex 读取索引后按需读文件。
- **子目录规则**：官方支持子目录 `AGENTS.md` / `AGENTS.override.md`；但本仓库**不主动写子目录文件**，避免与用户自有规则冲突（用户可在自有子目录规则里引用规范）。
- **文件引用**：官方未给出 Markdown 内联 `@import` 机制，故入口用反引号写明镜像路径（如 `.ai-standards/core/README.md`），属"需手动引用"，不假设会被自动内联。

## 5. Skills 加载方式

- **发现目录**：REPO 作用域 `$CWD/.agents/skills`、`$CWD/../.agents/skills`、`$REPO_ROOT/.agents/skills`；USER `$HOME/.agents/skills`；ADMIN `/etc/codex/skills`；SYSTEM 内置 [B]。本仓库只装项目级 `.agents/skills/`。
- **复用方式**：5 个公共 `SKILL.md` **逐字节复制**，不改 Frontmatter、不加工具字段；`scripts/` `references/` `assets/` 一并复制，保持一级引用。
- **调用**：显式 `/skills` 或 `$name`，或由 `description` 隐式匹配。初始技能列表约 2% 上下文（未知窗口 8,000 字符），故公共 Skill 描述已把触发词前置。
- **软链接**：官方支持软链接技能目录，但本仓库按 [`../README.md` §5](../README.md) 决策**不使用**软链接。
- **不使用** `agents/openai.yaml`（应用 UI 元数据 / 调用策略 / 工具依赖），它属工具专有配置。

## 6. Agent 支持情况

- 官方通过 `~/.codex/config.toml` 的 `[agents]` 定义 subagent 角色（[A] `config-advanced`），Hooks 文档含 `SubagentStart` / `SubagentStop` 事件 [B]，说明存在子代理机制。
- ⚠️ **字段格式 `UNVERIFIED`**：官方 Subagents 专页本次抓取返回 Forbidden，无法确认 `name`/`description`/`instructions` 等字段的准确写法。
- **本阶段处置**：只给出 `mappings.md` 的角色映射说明；**不生成任何 Codex agent 配置模板**，避免虚构字段。这是"不编造配置假装支持"的直接落地。
- 公共 `agents/` 4 个角色契约（architect / developer / reviewer / tester）保持工具无关正文，待官方字段确认后再在后续阶段转换。

## 7. Hooks 能力边界

Codex 的 Hooks 有官方支持（见 `tool-compatibility.md` §5），但本阶段**只记录、不生成**：Hooks 执行用户脚本、项目级需 trusted，且格式随版本变化。未来适合放"修改后格式化""提交前测试"，但不得把整套工程规范转成 Hooks。

## 8. 已知限制

1. `.codex/skills/` 兼容路径为 `UNVERIFIED`（官方主路径是 `.agents/skills/`），本仓库不依赖。
2. `name` / `description` 单独长度上限为 `UNVERIFIED`；按开放规范 64 / 1024 执行，描述控制在 300 字符内。
3. `config.toml [agents]` 字段为 `UNVERIFIED`，故不生成 agent 配置。
4. 英文官方文档页本次抓取返回 Forbidden，结论以官方中文镜像 [B] + 官方检索索引交叉确认，来源等级已逐条标注。
5. 未在真实 Codex 客户端运行时验证（见验收报告"实际运行验证"）。

## 9. 相关文档

- 映射明细：[`mappings.md`](mappings.md) · 官方参考：[`references.md`](references.md)
- 模板：[`templates/`](templates/)
- 统一映射架构：[`../README.md`](../README.md)

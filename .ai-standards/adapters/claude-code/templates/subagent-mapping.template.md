# 模板：公共 Agent 角色 → Claude Code Subagent 映射

> **用途**：演示如何把公共 `agents/architect.md` 转换为 Claude Code 的 `.claude/agents/architect.md`。
> 字段全部来自官方文档（[A] `https://code.claude.com/docs/en/sub-agents`，查阅 2026-11-11），**未虚构任何字段**。
> **这是映射示例，不是安装产物**：本阶段不生成可安装的 agent 文件（安装属 Phase 5）。
> 其余三个角色（developer / reviewer / tester）按同一规则转换。

---

## 转换规则

| 公共角色内容 | 映射到 | 说明 |
| --- | --- | --- |
| 文件标题 `# 角色契约：Architect（架构师）` | `name: architect` | 官方必填；用角色英文名，唯一、不含 `:` |
| 开头 `> **定位**：...` | `description: ...` | 官方必填；决定 Claude 何时自动委派，应写清"做什么 + 何时用" |
| 正文 §1–§6（职责 / 输入 / 输出 / 禁止 / 完成标准） | Markdown 正文 | 作为 **system prompt** 逐字保留，不改写职责 |
| `tools` / `model` / `permissionMode` | **不写入公共源** | 工具专有字段由目标项目按需添加 |

---

## 示例文件：`.claude/agents/architect.md`

```markdown
---
name: architect
description: 架构师角色：负责模块边界、技术方案比较与设计决策记录，不写实现代码。Use when 需要新增模块、调整边界或做技术选型。
---

# 角色契约：Architect（架构师）

> 本段及以下内容来自公共规范 agents/architect.md，逐字保留为 system prompt。
> 前提：core/ai-behavior.md（所有红线）、core/architecture-principles.md（架构原则）。
> 协作：输入来自 requirements-analysis，输出交给 developer；评审由 reviewer 完成。

本文件定义角色职责与交付接口，不是一个可执行 Agent 运行时。

## 1. 职责
（原文逐字保留……）

## 2. 输入要求
（原文逐字保留……）

## 3. 输出要求
（原文逐字保留……）

## 4. 禁止事项
（原文逐字保留……）

## 5. 完成标准
（原文逐字保留……）
```

> 说明：上面示例中的"（原文逐字保留……）"是**给维护者看的占位提示**，实际转换时必须把公共角色文件正文**完整复制**进来，不得缩减或改写。

---

## 关键约束（官方依据）

1. **只有 `name` 和 `description` 必填**（#3 [A]）；缺 `name`、缺 `description`、YAML 解析失败、首行不是 `---` 的文件会被 Claude Code 跳过。
2. **Markdown 正文即 system prompt**：文件式 subagent 没有名为 `prompt` 的 frontmatter 字段；`prompt` 只存在于 CLI `--agents` JSON 定义中。
3. **独立上下文**：每个 subagent 在自己的上下文窗口运行，非 fork 时看不到主对话历史——因此正文必须自带足够上下文（这也是保留完整角色契约的原因）。
4. **可选字段** `tools`、`disallowedTools`、`model`、`permissionMode`、`maxTurns`、`skills`、`mcpServers`、`hooks` 等是否设置，由目标项目按其安全与成本策略决定；本仓库不预设，避免绑定工具能力。
5. **文件名不决定身份**：`name` 字段才决定 subagent 标识，子目录只用于组织。

## 相关文档

- 映射总表：[`../mappings.md`](../mappings.md) · 官方参考：[`../references.md`](../references.md) · 公共角色源：[`../../../agents/architect.md`](../../../agents/architect.md)

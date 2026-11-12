# 模板：公共 Agent 角色 → WorkBuddy 子代理映射

> **用途**：演示如何把公共 `agents/architect.md` 转换为 WorkBuddy 的 `.codebuddy/agents/architect.md`。
> 字段全部来自官方文档（[A] `https://www.workbuddy.cn/docs/cli/sub-agents`，查阅 2026-11-11），**未虚构任何字段**。
> **这是映射示例，不是安装产物**：本阶段只提供模板，不生成可安装的 agent 文件（详见 [`../mappings.md`](../mappings.md) §4）。
> 其余三个角色（developer / reviewer / tester）按同一规则转换。

---

## 转换规则

| 公共角色内容 | 映射到 | 说明 |
| --- | --- | --- |
| 文件标题 `# 角色契约：Architect（架构师）` | `name: architect` | 官方必填；用角色英文名，唯一、不含 `:` |
| 开头 `> **定位**：...` | `description: ...` | 官方必填；决定 WorkBuddy 何时委派，应写清"做什么 + 何时用" |
| 正文 §1–§6（职责 / 输入 / 输出 / 禁止 / 完成标准） | Markdown 正文 | 作为 **system prompt** 逐字保留，不改写职责 |
| `tools` / `model` | **不写入公共源** | 工具专有字段由目标项目按需添加 |

---

## 示例文件：`.codebuddy/agents/architect.md`

```markdown
---
name: architect
description: 架构师角色：负责模块边界、技术方案比较与设计决策记录，不写实现代码。当任务涉及新增模块、调整边界或技术选型时使用。
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

> 说明：示例里的"（原文逐字保留……）"是**给维护者看的占位提示**，实际转换时必须把公共角色文件正文**完整复制**进来，不得缩减或改写。正文中的 `../core/...` 相对链接需改写为相对目标项目的 `.ai-standards/core/...` 路径。

---

## 关键约束（官方依据）

1. **只有 `name` 和 `description` 必填**（#4 [A]）；缺字段或 YAML 解析失败的文件会被跳过。
2. **Markdown 正文即 system prompt**：文件式子代理没有名为 `prompt` 的 frontmatter 字段。
3. **项目级优先**：`.codebuddy/agents/` 覆盖 `~/.codebuddy/agents/` 同名代理；本模板只产出项目级。
4. **可选字段** `tools`、`model` 等是否设置由目标项目决定，本仓库不预设，避免绑定工具能力。
5. **不生成**：安装器不产出 `.codebuddy/agents/`，需人工按本模板转换后放入项目；因此"Agents 能被发现"须人工启用后验证。

---

## 相关文档

- 映射总表：[`../mappings.md`](../mappings.md) · 官方参考：[`../references.md`](../references.md) · 公共角色源：[`../../../agents/architect.md`](../../../agents/architect.md)

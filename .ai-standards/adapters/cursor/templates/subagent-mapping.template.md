# 模板：公共 Agent 角色 → Cursor Subagent 映射

> **用途**：演示如何把公共 `agents/reviewer.md` 转换为 Cursor 的 `.cursor/agents/reviewer.md`。
> 字段全部来自官方文档（[A] `https://cursor.com/docs/agent/subagents`，查阅 2026-11-11），**未虚构任何字段**。
> **这是映射示例，不是安装产物**：本阶段不生成可安装的 agent 文件（安装属 Phase 5）。

---

## 转换规则

| 公共角色内容 | 映射到 | 说明 |
| --- | --- | --- |
| 文件标题 `# 角色契约：Reviewer（审查者）` | `name: reviewer` | 官方可选，建议写；小写字母 + 连字符 |
| 开头 `> **定位**：...` | `description: ...` | 官方可选但关键；决定 Agent 何时委派此 subagent |
| 正文 §1–§6 | Markdown 正文 | 作为 subagent prompt 逐字保留 |
| `model` / `readonly` / `is_background` | **不写入公共源** | 工具专有字段，由目标项目按需设置 |

---

## 示例文件：`.cursor/agents/reviewer.md`

```markdown
---
name: reviewer
description: 审查者角色：核对改动是否满足需求、红线与测试标准，输出分级问题清单。Use when 提交前自检或 PR 审查。
model: inherit
readonly: true
---

# 角色契约：Reviewer（审查者）

> 本段及以下内容来自公共规范 agents/reviewer.md，逐字保留为 subagent prompt。
> 前提：core/ai-behavior.md（红线）、skills/code-review（审查工作流）。
> 输出：CRITICAL / HIGH / MEDIUM / LOW / INFO 分级问题清单。

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

> 说明：示例中的"（原文逐字保留……）"是给维护者的占位提示，实际转换时必须把公共角色文件正文**完整复制**进来。

---

## 字段说明（官方依据）

| 字段 | 官方类型 / 默认 | 是否建议设置 | 理由 |
| --- | --- | --- | --- |
| `name` | string，默认取文件名 | 建议显式写 | 标识符，小写字母 + 连字符 |
| `description` | string | **建议写** | Agent 读它决定委派时机；"Invest in descriptions" 是官方最佳实践 |
| `model` | string，默认 `inherit` | 目标项目自定 | 可用 `inherit` 或具体 model ID |
| `readonly` | boolean，默认 `false` | 审查类角色建议 `true` | 限制写权限，适合 reviewer / architect |
| `is_background` | boolean，默认 `false` | 按需 | 后台运行不阻塞父 Agent |

---

## 关键约束

1. **`readonly` 是 Cursor 特有字段**，不进入公共 `agents/`；这正体现"公共角色 vs 工具配置分离"。
2. **四类机制互不混淆**：Subagent（独立上下文、被委派）≠ Rules（常驻 `.mdc`）≠ Skills（按需 `SKILL.md`）≠ Hooks（`hooks.json` 脚本）。
3. **兼容路径**：`.cursor/agents/` 项目级优先于 `.claude/agents/` / `.codex/agents/`；同名时 `.cursor/` 胜出。
4. 官方支持用 `/create-subagent` 在对话中生成，但本仓库用映射模板保证与公共角色一致。

## 相关文档

- 映射总表：[`../mappings.md`](../mappings.md) · 官方参考：[`../references.md`](../references.md) · 公共角色源：[`../../../agents/reviewer.md`](../../../agents/reviewer.md)

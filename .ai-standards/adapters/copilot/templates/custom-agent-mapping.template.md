# 模板：公共 Agent 角色 → Copilot Custom Agent 映射

> **用途**：演示如何把公共 `agents/tester.md` 转换为 Copilot 的 `.github/agents/tester.md`（agent profile）。
> 字段全部来自官方文档（[A] `https://docs.github.com/en/copilot/concepts/agents/cloud-agent/about-custom-agents`，查阅 2026-11-11），**未虚构任何字段**。
> **这是映射示例，不是安装产物**：本阶段不生成可安装的 agent profile（安装属 Phase 5）。

---

## 转换规则

| 公共角色内容 | 映射到 | 说明 |
| --- | --- | --- |
| 文件标题 `# 角色契约：Tester（测试者）` | `name: tester`（可选） | 省略时取文件名（去 `.md` / `.agent.md` 后缀） |
| 开头 `> **定位**：...` | `description: ...` | **必填**；说明用途与能力 |
| 正文 §1–§6 | Markdown 正文 = prompt | 逐字保留，≤30,000 字符 |
| `tools` / `mcp-servers` / `model` / `target` | **不写入公共源** | 工具专有字段，由目标项目按需设置 |

---

## 示例文件：`.github/agents/tester.md`

```markdown
---
name: tester
description: 测试者角色：制定测试策略、执行并如实报告测试结果，区分已通过/失败/未运行。Use when 需要为改动补齐测试或验证质量。
---

# 角色契约：Tester（测试者）

> 本段及以下内容来自公共规范 agents/tester.md，逐字保留为 agent prompt。
> 前提：core/testing-principles.md（测试原则）、core/ai-behavior.md（红线）。
> 输出：测试用例、执行结果、未决风险。

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

| 字段 | 必需 | 说明 |
| --- | --- | --- |
| `name` | 否 | 显示名；缺省取文件名；文件名仅允许 `.` `-` `_` `a-z` `A-Z` `0-9` |
| `description` | **是** | 说明 agent 用途与专门能力 |
| `prompt` | — | 即 frontmatter 之后的 Markdown 正文（**不是** frontmatter 字段），≤30,000 字符 |
| `tools` | 否 | 工具名/别名列表；省略时可用全部工具（含 MCP 工具） |
| `mcp-servers` | 否 | 仅该 agent 可用的 MCP 服务器配置 |
| `model` | 否 | IDE 环境可控制所用模型 |
| `target` | 否 | `vscode` 或 `github-copilot`，限定使用环境 |

---

## 关键约束

1. **角色与配置分离**：正文是唯一权威角色定义；`tools`/`mcp-servers` 等工具字段不进公共 `agents/`。
2. **surface 差异**：Custom Agents 在 VS Code / GitHub.com / CLI 正式支持，在 JetBrains / Eclipse / Xcode 为公开预览（矩阵标 `PARTIAL`）。
3. **分支注意**：code review 从 head branch 读取指令与 Skills；agent profile 应提交到相应分支。
4. **不与指令混淆**：Agent Skills（按需工作流）、Custom Agents（专门角色）、自定义指令（常驻上下文）、Hooks（生命周期脚本）是四套机制，本仓库分开处理。

## 相关文档

- 映射总表：[`../mappings.md`](../mappings.md) · 官方参考：[`../references.md`](../references.md) · 公共角色源：[`../../../agents/tester.md`](../../../agents/tester.md)

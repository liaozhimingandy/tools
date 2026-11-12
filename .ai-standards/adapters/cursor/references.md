# Cursor 官方文档参考

> 记录 Phase 4 实际查阅的官方文档：**标题、URL、查阅日期、来源等级、用于支撑的能力结论**。
> 查阅日期统一为 **2026-11-11**。来源等级定义见 [`../../docs/architecture/tool-compatibility.md` §0.3](../../docs/architecture/tool-compatibility.md)。

---

## 1. 文档清单

| # | 文档标题 | URL | 来源 | 支撑结论 |
| --- | --- | --- | --- | --- |
| 1 | Rules \| Cursor Docs | `https://cursor.com/docs/rules` | [A] | 四类规则、`.mdc` 扩展名、`alwaysApply`/`description`/`globs` 交互、`@file` 不内联、优先级 Team→Project→User、AGENTS.md 替代、<500 行 |
| 2 | Agent Skills \| Cursor Docs | `https://cursor.com/docs/context/skills` | [A] | 发现路径、兼容加载、递归/嵌套作用域、frontmatter 字段、`paths`、Cloud Agents 同步 |
| 3 | Subagents \| Cursor Docs | `https://cursor.com/docs/agent/subagents` | [A] | `.cursor/agents/`、兼容路径、frontmatter 字段、独立上下文、可并行 |
| 4 | Hooks \| Cursor Docs | `https://cursor.com/docs/hooks` | [A] | `.cursor/hooks.json`、`version:1`、事件表、exit 2、`failClosed`、surface 差异 |

> 抓取说明：请求 `https://cursor.com/docs/agent/hooks` 时官方重定向到 `https://cursor.com/docs/hooks`，故以 §1 表内后者为准。

---

## 2. 逐能力依据

| 能力 | 状态 | 依据 | 关键原文要点 |
| --- | --- | --- | --- |
| 项目级规则 | `SUPPORTED` | #1 [A] | `.cursor/rules/*.mdc`，必须 `.mdc`；`.md` 被忽略 |
| 全局 / 用户级规则 | `PARTIAL` | #1 [A] | User Rules 在 Customize UI，磁盘无项目可写路径 |
| 子目录规则 | `SUPPORTED` | #1 #2 [A] | rules 可分子目录 + `globs`；嵌套 `.cursor/skills/` 自动作用域 |
| 自动发现 | `SUPPORTED` | #1 #2 [A] | 启动时自动递归发现 rules 与 `SKILL.md` |
| 文件引用（内联 import） | `PARTIAL`（手动） | #1 [A] | 规则中 `@file` "contents are not inlined into the prompt"，只提示去读 |
| Skills | `SUPPORTED` | #2 [A] | `.agents/skills/`、`.cursor/skills/`；兼容 `.claude/.codex/skills` |
| 自定义 Agent | `SUPPORTED` | #3 [A] | `.cursor/agents/*.md`；`name`/`description` 建议写；独立上下文 |
| Hooks | `SUPPORTED` | #4 [A] | `.cursor/hooks.json`；`PreToolUse` 类事件 exit 2 阻断；Cloud Agents 只跑 command-based |
| MCP 集成 | `SUPPORTED` | #4 [A] | hooks 含 `beforeMCPExecution`/`afterMCPExecution`；精确配置路径本次未抓取 → 见 `UNVERIFIED` |
| 规则优先级 | `SUPPORTED` | #1 [A] | "Team Rules → Project Rules → User Rules"，早者优先 |

---

## 3. 关键限制（官方原文）

| 限制 | 原文要点 | 本仓库处置 |
| --- | --- | --- |
| `.md` 被忽略 | "A plain `.md` file in `.cursor/rules` is ignored by the rules system" | 规则文件强制 `.mdc` 后缀 |
| `@file` 不内联 | "The file's contents are not inlined into the prompt" | 正文用反引号写镜像路径，不依赖内联 |
| 引用而非复制 | 官方最佳实践："Reference files instead of copying their contents... prevents them from becoming stale" | 规则只放索引，正文留镜像 |
| 用户级技能云限制 | "Automation runs don't load them"；需 "Sync Skills for Cloud Agents" | 只用项目级 `.cursor/skills/` |
| 前端字段版本差异 | `icon`/`color` 为可选扩展字段 | 不写，保持工具无关 |

---

## 4. `UNVERIFIED` 与差异记录

| 项 | 状态 | 说明 | 本仓库处置 |
| --- | --- | --- | --- |
| Cursor MCP 精确配置路径 | `UNVERIFIED` | MCP 专页本次抓取失败（fetch failed）；能力由 #4 hooks 的 MCP 事件佐证 | 只声明"支持 MCP"，不写 MCP 配置 |
| `icon` / `color` 跨版本表现 | `UNVERIFIED` | 官方列为可选字段但未逐版本说明 | 不使用 |
| 真实客户端运行验证 | **未执行** | 当前环境未安装 Cursor 客户端 | 静态 + 模拟验证，明确区分（见验收报告） |

---

## 5. 复核触发条件

1. Cursor 调整 `.mdc` frontmatter 字段或其交互规则；
2. Skills 发现目录变化，或新增标准 Frontmatter 字段；
3. Subagents frontmatter 字段增删；
4. Hooks 事件表 / 配置位置变化；
5. 开放规范 `agentskills.io/specification` 升级。

## 6. 相关文档

- 能力矩阵：[`../../docs/architecture/tool-compatibility.md`](../../docs/architecture/tool-compatibility.md)
- 适配说明：[`README.md`](README.md) · 映射：[`mappings.md`](mappings.md) · 历史核实：[`../../docs/tool-adapters.md`](../../docs/tool-adapters.md)

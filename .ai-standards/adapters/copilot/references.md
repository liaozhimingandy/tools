# GitHub Copilot 官方文档参考

> 记录 Phase 4 实际查阅的官方文档：**标题、URL、查阅日期、来源等级、用于支撑的能力结论**。
> 查阅日期统一为 **2026-11-11**。来源等级定义见 [`../../docs/architecture/tool-compatibility.md` §0.3](../../docs/architecture/tool-compatibility.md)。

---

## 1. 文档清单

| # | 文档标题 | URL | 来源 | 支撑结论 |
| --- | --- | --- | --- | --- |
| 1 | Support for different types of custom instructions | `https://docs.github.com/en/copilot/reference/custom-instructions-support` | [A] | 仓库级/路径级/Agent 指令各 surface 支持矩阵 |
| 2 | Agent skills | `https://docs.github.com/en/copilot/concepts/customizations/agent-skills` | [A] | Skills 项目/个人路径、`gh skill`、适用 surface、IDE 版本依赖 |
| 3 | Hooks for GitHub Copilot | `https://docs.github.com/en/copilot/concepts/customizations/hooks` | [A] | `.github/hooks/*.json`、`version:1`、事件表、`preToolUse` 可 deny、cloud 子集、surface 覆盖 |
| 4 | About custom agents | `https://docs.github.com/en/copilot/concepts/agents/cloud-agent/about-custom-agents` | [A] 官方检索索引 | agent profile 路径/字段、prompt ≤30,000、JetBrains/Eclipse/Xcode 预览 |
| 5 | Copilot customization cheat sheet | `https://docs.github.com/en/copilot/reference/customization-cheat-sheet` | [A] 官方检索索引 | 各定制特性文件位置 + 各 IDE/surface 支持矩阵（含 Hooks、Custom agents、Skills） |
| 6 | Copilot feature matrix | `https://docs.github.com/en/copilot/reference/copilot-feature-matrix` | [A] | VS Code 各版本能力（Agent skills 自 1.108.0 ✓、MCP、Custom agents 等） |

> 说明：#4 #5 由官方站点检索索引返回正文（域名 `docs.github.com` 属官方），标 [A]；#1 #2 #3 #6 为正文直接抓取成功。

---

## 2. 逐能力依据

| 能力 | 状态 | 依据 | 关键原文要点 |
| --- | --- | --- | --- |
| 项目级规则（仓库级） | `SUPPORTED` | #1 [A] | `.github/copilot-instructions.md`，纯 Markdown，作用于仓库上下文 |
| 子目录规则（路径级） | `PARTIAL` | #1 [A] | `.github/instructions/**/*.instructions.md` + `applyTo`；GitHub.com 仅 cloud/code review |
| 全局 / 用户级规则 | `PARTIAL` | #1 [A] | CLI 个人 `~/.copilot/copilot-instructions.md`；组织级靠 UI |
| 自动发现 | `PARTIAL` | #1 #2 [A] | 仓库级/Skills 自动发现；路径级 surface 依赖 |
| 文件引用（内联 import） | `UNVERIFIED` | 本次查阅 | 未找到官方 Markdown 内联 `@import` 语法说明 |
| Skills | `SUPPORTED` | #2 #6 [A] | `.github/skills/`、`.claude/skills/`、`.agents/skills/`；`gh skill`；VS Code ≥1.108.0 |
| 自定义 Agent | `PARTIAL` | #4 #5 [A] | `.github/agents/*.md`；JetBrains/Eclipse/Xcode 公开预览 |
| Hooks | `PARTIAL` | #3 #5 [A] | `.github/hooks/*.json`；CLI/cloud/app 支持，VS Code 预览，多数 IDE ✗ |
| Hooks 跨平台 | `SUPPORTED` | #3 [A] | 官方要求 hook 对象同时提供 `bash`（Unix）与 `powershell`（Windows）键；cloud agent 仅采纳 `bash`，`powershell` 被忽略 |
| MCP 集成 | `SUPPORTED` | #5 #6 [A] | `mcp.json`（随 IDE 变动）+ agent profile `mcp-servers` + CLI `~/.copilot/mcp-config.json`；VS Code 各版本 ✓ |
| 规则优先级 | `SUPPORTED` | #1 [A] | Personal > Repository > Organization；相关指令同时提供 |

---

## 3. surface 支持矩阵（官方摘录，决定"覆盖策略"）

### 3.1 自定义指令（#1 [A]）

| 环境 | 仓库级 | 路径级 | Agent 指令 |
| --- | --- | --- | --- |
| VS Code（Copilot Chat） | ✓ | ✓ | ✓ (`AGENTS.md`) |
| JetBrains IDEs | ✓ | ✓ | — |
| Eclipse | ✓ | — | — |
| Xcode | ✓ | ✓ | — |
| Copilot CLI | ✓ | ✓ | ✓ |
| cloud agent | ✓ | ✓ | ✓ |
| code review | ✓ | 视环境 | ✓ |

### 3.2 定制特性（#5 cheat sheet [A]）

| 特性 | VS Code | Visual Studio | JetBrains | Eclipse | Xcode | GitHub.com | CLI |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Custom instructions | ✓ | ✓ | P | P | P | ✓ | ✓ |
| Custom agents | ✓ | ✓ | P | P | P | ✓ | ✓ |
| Agent skills | ✓ | ✓ | P | ✗ | ✗ | ✓ | ✓ |
| Hooks | P | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ |
| MCP servers | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

> ✓ = 支持 · P = 公开预览 · ✗ = 不支持。**这是本适配器用"双指令通道"覆盖风险、Hooks 标 `PARTIAL`、Skills/自定义 Agent 标 `PARTIAL` 的直接依据。**

---

## 4. `UNVERIFIED` 与差异记录

| 项 | 状态 | 说明 | 本仓库处置 |
| --- | --- | --- | --- |
| 路径级指令在各 IDE 版本实际读取行为 | `UNVERIFIED` | #1 明示 "IDE support depends on the version you use" | 仓库级 + 路径级双通道并存 |
| `excludeAgent` 跨 CLI / IDE 行为 | `UNVERIFIED` | #1 列出该字段但未逐 surface 说明 | 不设置该字段 |
| Markdown 内联 `@import` 语法 | `UNVERIFIED` | 官方未给出该语法说明 | 不依赖；用镜像复制保证链接完整 |
| code review 读取分支 | 证据充分 | #1/#2 明确从 **head branch** 读取 | 文档提醒须提交到被审查分支 |
| 真实客户端运行验证 | **未执行** | 当前环境未安装 Copilot 客户端 | 静态 + 模拟验证，明确区分（见验收报告） |

---

## 5. 复核触发条件

1. Copilot 调整自定义指令的 surface 支持矩阵（尤其路径级指令）；
2. Skills 发现路径或 IDE 版本门槛变化；
3. Custom Agents frontmatter 字段增删，或脱离公开预览；
4. Hooks 事件表 / 配置位置 / surface 覆盖变化；
5. 开放规范 `agentskills.io/specification` 升级。

## 6. 相关文档

- 能力矩阵：[`../../docs/architecture/tool-compatibility.md`](../../docs/architecture/tool-compatibility.md)
- 适配说明：[`README.md`](README.md) · 映射：[`mappings.md`](mappings.md) · 历史核实：[`../../docs/tool-adapters.md`](../../docs/tool-adapters.md)

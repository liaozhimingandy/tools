# Claude Code 官方文档参考

> 记录 Phase 4 实际查阅的官方文档：**标题、URL、查阅日期、来源等级、用于支撑的能力结论**。
> 查阅日期统一为 **2026-11-11**。来源等级定义见 [`../../docs/architecture/tool-compatibility.md` §0.3](../../docs/architecture/tool-compatibility.md)。

---

## 1. 文档清单

| # | 文档标题 | URL | 来源 | 支撑结论 |
| --- | --- | --- | --- | --- |
| 1 | Extend Claude with skills | `https://code.claude.com/docs/en/skills` | [A] 正文抓取成功 | Skills 四级路径、6 字段白名单、额外字段硬错误、1,536 字符截断、<500 行、`/skill-name`、`disable-model-invocation` |
| 2 | How Claude remembers your project | `https://code.claude.com/docs/en/memory` | [A] 正文抓取成功 | CLAUDE.md 四层位置、拼接非覆盖、根→工作目录、子目录按需加载、`@path` 最多 4 跳且不省上下文、`.claude/rules/` 递归、`paths` 唯一字段、4 MiB / 200 行 |
| 3 | Create custom subagents | `https://code.claude.com/docs/en/sub-agents` | [A] 正文抓取成功 | `.claude/agents/` 与 `~/.claude/agents/`、5 级优先级、YAML frontmatter 全字段、独立上下文、正文=system prompt、调用方式 |
| 4 | Hooks reference | `https://code.claude.com/docs/en/hooks` | [A] 正文抓取成功 | `settings.json` 三层 + managed + plugin + skill/subagent frontmatter、`PreToolUse` 可阻断、完整事件表、cloud 不读本地 settings |

> 文档索引入口（官方在页面内给出）：`https://code.claude.com/docs/llms.txt`。各页面 URL 由官方索引与站点约定确认；本表 URL 为 Phase 4 实际请求并成功抓取的地址。

---

## 2. 逐能力依据

| 能力 | 状态 | 依据 | 关键原文要点 |
| --- | --- | --- | --- |
| 项目级规则 | `SUPPORTED` | #2 [A] | `./CLAUDE.md` 或 `./.claude/CLAUDE.md` |
| 全局 / 用户级规则 | `SUPPORTED` | #2 [A] | `~/.claude/CLAUDE.md` + managed policy（macOS/Linux/Windows 三路径） |
| 子目录规则 | `SUPPORTED` | #2 [A] | 子目录 CLAUDE.md 按需加载 + rules 的 `paths` 字段 |
| 自动发现 | `SUPPORTED` | #2 #1 #3 [A] | CLAUDE.md 向上遍历 + `.claude/rules/`、skills、agents 递归发现 |
| 文件引用（内联 import） | `SUPPORTED` | #2 [A] | `@path` 相对包含文件解析，最多 4 跳；**但 import 不减少上下文成本** |
| Skills | `SUPPORTED` | #1 [A] | 四级路径；frontmatter 必须 6 字段，额外字段硬报错 |
| Skills 列表截断 | `PARTIAL` | #1 [A] | `description`+`when_to_use` 于 1,536 字符截断 |
| 自定义 Agent | `SUPPORTED` | #3 [A] | `.claude/agents/*.md`；`name`/`description` 必填；独立上下文窗口 |
| Hooks | `SUPPORTED` | #4 [A] | `settings.json`；`PreToolUse` exit 2 阻断；事件众多 |
| MCP 集成 | `SUPPORTED` | #3 #4 [A] | subagent `mcpServers` 字段；hooks 含 MCP tool hooks（精确配置路径本次未单独抓取 → 见 `UNVERIFIED`） |
| 规则优先级 | `PARTIAL` | #2 [A] | 全部拼接、**无硬优先级**，冲突时可能任选；硬阻断须用 hook |

---

## 3. 关键限制（官方原文）

| 限制 | 原文要点 | 本仓库处置 |
| --- | --- | --- |
| 上下文注入非强制配置 | "Claude treats them as context, not enforced configuration"；冲突时 "may pick one arbitrarily" | 规范冲突靠 `core/README.md` 裁决，不靠文件顺序 |
| 额外 Frontmatter 字段硬报错 | "Unexpected key(s) in SKILL.md frontmatter: argument-hint. Allowed properties are: allowed-tools, compatibility, description, license, metadata, name" | Skills 只用 6 标准字段 |
| import 不省上下文 | "Imports help you organize a long file but don't reduce its context cost" | 不用 `@path` 拉全量规范 |
| cloud sessions 限制 | "Personal skills (~/.claude/skills/) ... not Cowork or cloud sessions"；project `.claude/skills/` 不用于 project cloud threads | 不承诺云会话可见性 |
| 符号链接规则需批准 | 指向工作区外的 symlink 规则按 external import 处理，且只有无 `paths` 的加载 | 不用符号链接 |
| Hooks 硬策略边界 | "use the permission system rather than a hook to enforce a hard allow or deny" | Hooks 只记录能力，不承载强制规范 |

---

## 4. `UNVERIFIED` 与差异记录

| 项 | 状态 | 说明 | 本仓库处置 |
| --- | --- | --- | --- |
| MCP 精确配置路径（`.mcp.json` 等） | `UNVERIFIED` | MCP 专页本次未单独抓取；能力由 #3 #4 正文（subagent `mcpServers`、MCP tool hooks）佐证 | 只声明"支持 MCP"，不写入 MCP 配置 |
| 每个 IDE 版本对 cloud memory 的具体行为 | `PARTIAL` | 官方文档按 session 类型区分，未逐 IDE 列矩阵 | 不承诺跨环境一致 |
| 真实客户端运行验证 | **未执行** | 当前环境未安装 Claude Code 客户端 | 静态 + 模拟验证，明确区分（见验收报告） |

---

## 5. 复核触发条件

1. Claude Code 调整 Skills frontmatter 白名单或截断长度；
2. `.claude/rules/` 的 `paths`（或新增字段）机制变化；
3. Subagents frontmatter 字段增删；
4. cloud / Cowork 对本地 skills 的可见性变化；
5. 开放规范 `agentskills.io/specification` 升级。

## 6. 相关文档

- 能力矩阵：[`../../docs/architecture/tool-compatibility.md`](../../docs/architecture/tool-compatibility.md)
- 适配说明：[`README.md`](README.md) · 映射：[`mappings.md`](mappings.md) · 历史核实：[`../../docs/tool-adapters.md`](../../docs/tool-adapters.md)

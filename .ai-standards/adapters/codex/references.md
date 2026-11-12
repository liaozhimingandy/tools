# Codex 官方文档参考

> 记录 Phase 4 实际查阅的官方文档：**标题、URL、查阅日期、来源等级、用于支撑的能力结论**。
> 查阅日期统一为 **2026-11-11**。来源等级定义见 [`../../docs/architecture/tool-compatibility.md` §0.3](../../docs/architecture/tool-compatibility.md)。
> 原则：无法确认的项标 `UNVERIFIED`，本仓库不据第三方资料 [C] 写入任何配置。

---

## 1. 文档清单

| # | 文档标题 | URL | 来源 | 支撑结论 |
| --- | --- | --- | --- | --- |
| 1 | 使用 AGENTS.md 的自定义指令 | `https://developers.openai.ac.cn/codex/guides/agents-md` | [B] 官方中文镜像 | 全局 / 项目指令发现、遍历、override、合并顺序、32 KiB、CODEX_HOME |
| 2 | 智能体技能 (Agent Skills) | `https://developers.openai.ac.cn/codex/skills` | [B] 官方中文镜像 | Skills 目录层级、必填字段、2%/8,000 字符预算、软链接、显式/隐式调用、`agents/openai.yaml` |
| 3 | Hooks | `https://developers.openai.com/codex/hooks` | [B] 官方站点检索索引 | Hooks 事件表、`PreToolUse`/`PermissionRequest` 阻断、项目级需 trusted、输出字段状态 |
| 4 | Advanced Configuration | `https://developers.openai.com/codex/config-file/config-advanced` | [A] 正文抓取成功 | `config.toml [agents]` subagent 角色、`mcp_servers`、`~/.codex/hooks.json` 与 `<repo>/.codex/hooks.json` 四类位置 |
| 5 | Specification - Agent Skills | `https://agentskills.io/specification` | [A] 正文抓取成功 | 跨工具共同基准（6 字段、命名、行数、一级引用、渐进披露） |

### 抓取可用性记录

- 英文 `https://developers.openai.com/codex/guides/agents-md`：本次直接抓取返回 **Forbidden**，故改用官方中文镜像 [B]。
- 英文 `https://developers.openai.com/codex/subagents`：本次直接抓取返回 **Forbidden**，导致 `[agents]` 字段格式无法确认 → 标 `UNVERIFIED`。
- `https://developers.openai.ac.cn/codex/guides/hooks`：返回 **404**；Hooks 结论改由官方站点检索索引 [B] + `config-advanced` [A] 交叉确认。
- 官方中文镜像域名 `developers.openai.ac.cn` 属 OpenAI 官方，但为镜像而非目标英文页，故统一标 [B] 而非 [A]。

---

## 2. 逐能力依据

| 能力 | 状态 | 依据（#/来源） | 关键原文要点 |
| --- | --- | --- | --- |
| 项目级规则 | `SUPPORTED` | #1 [B] | 从项目根向 CWD 遍历，每层 `AGENTS.override.md` → `AGENTS.md` → fallback，最多一个 |
| 全局规则 | `SUPPORTED` | #1 [B] | `~/.codex/AGENTS.md`；`AGENTS.override.md` 优先；`CODEX_HOME` 改 home |
| 子目录规则 | `SUPPORTED` | #1 [B] | 近目录覆盖远目录；空行拼接；`project_doc_max_bytes` 默认 32 KiB |
| 自动发现 | `SUPPORTED` | #1 #2 [B] | 启动时构建指令链 + 递归扫描 `.agents/skills` |
| Skills | `SUPPORTED` | #2 [B] | REPO/USER/ADMIN/SYSTEM 四级路径；必须 `name`+`description`；支持软链接 |
| Skills 调用 | `SUPPORTED` | #2 [B] | 显式 `/skills` 或 `$name`；隐式按 `description` 匹配；初始列表 2%/8,000 字符 |
| 自定义 Agent | `SUPPORTED`（机制） | #4 [A] | `config.toml [agents]` 用于 subagent 角色配置；字段细节未确认 |
| 自定义 Agent 字段 | `UNVERIFIED` | #4 [A] + Forbidden 记录 | 官方 Subagents 专页抓取被拒，无法确认字段写法 |
| Hooks | `SUPPORTED` | #3 [B] #4 [A] | 四类配置位置；项目级需 trusted；`PermissionRequest` 可 allow/deny |
| 文件引用（内联 import） | `PARTIAL`（手动） | #1 [B] | 纯 Markdown，无官方内联 `@import`；靠列路径让 Agent 自行读取 |
| MCP 集成 | `SUPPORTED` | #4 [A] | `config.toml` 的 `mcp_servers`；项目级配置需 trusted |
| 规则优先级 | `SUPPORTED` | #1 [B] | 越近目录越靠后、优先级越高 |

---

## 3. `UNVERIFIED` 与差异记录

| 项 | 状态 | 说明 | 本仓库处置 |
| --- | --- | --- | --- |
| `.codex/skills/` 兼容路径 | `UNVERIFIED` | Cursor 官方文档把 `.codex/skills/` 列为兼容路径，但 Codex 自身文档只给 `.agents/skills` | 只用官方明确的 `.agents/skills/` |
| `name`/`description` 单独长度上限 | `UNVERIFIED` | 第三方资料 [C] 声称 100/500；官方 Skills 文档未在可读正文给出 | 按开放规范 64/1024，描述 < 300 字符 |
| `config.toml [agents]` 字段 | `UNVERIFIED` | 官方 Subagents 页 Forbidden | 不生成 agent 配置模板 |
| `agents/openai.yaml` | 证据充分但**主动不用** | #2 [B] 给出 UI 元数据 / `allow_implicit_invocation` / 工具依赖 | 属工具专有配置，不写入公共源 |
| 真实客户端运行验证 | **未执行** | 当前环境未安装 Codex 客户端 | 静态 + 模拟验证，明确区分（见验收报告） |

---

## 4. 复核触发条件

出现以下任一情况，须重新查阅并更新本文件与 `tool-compatibility.md` 的适配日期：

1. Codex 官方调整 `AGENTS.md` 发现规则或字节上限；
2. Skills 目录路径变化，或新增/移除标准 Frontmatter 字段；
3. `config.toml [agents]` 官方专页恢复可访问（→ 解除对应 `UNVERIFIED`）；
4. Hooks 事件表或配置位置变化；
5. 开放规范 `agentskills.io/specification` 升级。

## 5. 相关文档

- 能力矩阵：[`../../docs/architecture/tool-compatibility.md`](../../docs/architecture/tool-compatibility.md)
- 适配说明：[`README.md`](README.md) · 映射：[`mappings.md`](mappings.md) · 历史核实：[`../../docs/tool-adapters.md`](../../docs/tool-adapters.md)

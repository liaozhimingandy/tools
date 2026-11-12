# 腾讯 WorkBuddy 官方文档参考

> 记录 Phase 6 实际查阅的 WorkBuddy / CodeBuddy Code 官方文档：**标题、URL、查阅日期、来源等级、用于支撑的能力结论**。
> 查阅日期统一为 **2026-11-11**。来源等级定义见 [`../../docs/architecture/tool-compatibility.md` §0.3](../../docs/architecture/tool-compatibility.md)。

---

## 1. 文档清单

| # | 文档标题 | URL | 来源 | 支撑结论 |
| --- | --- | --- | --- | --- |
| 1 | .codebuddy 目录结构说明 | `https://www.workbuddy.cn/docs/cli/codebuddy-dir` | [A] 正文抓取成功 | 项目/全局目录树、`CODEBUDDY.md` 两处等效、`agents/rules/skills/commands` 四类子目录、项目级 > 用户级 > 插件级、记忆加载顺序 |
| 2 | 管理 CodeBuddy 的记忆 | `https://www.workbuddy.cn/docs/cli/memory` | [A] 正文抓取成功 | `CODEBUDDY.md` 向上递归、`@path` 导入 ≤5 层、`AGENTS.md` 兼容且 `CODEBUDDY.md` 优先、`rules` 三字段 `enabled/alwaysApply/paths`、规则类型判定、仅当前工作目录加载项目规则、`/memory` 调试 |
| 3 | Skills 文档 | `https://www.workbuddy.cn/docs/cli/skills` | [A] 正文抓取 | `.codebuddy/skills/<name>/SKILL.md`、frontmatter `name`/`description` + 可选 `allowed-tools`、项目级优先 |
| 4 | 子代理 | `https://www.workbuddy.cn/docs/cli/sub-agents` | [A] 正文抓取 | `.codebuddy/agents/*.md`、`name`/`description` 必填、`tools`/`model` 可选、正文 = system prompt、项目级优先于用户级 |
| 5 | 斜杠命令 | `https://www.workbuddy.cn/docs/cli/slash-commands` | [A] 正文抓取 | `.codebuddy/commands/*.md`、`description`/`argument-hint`/`allowed-tools`、`$ARGUMENTS`、`/group:cmd` 嵌套 |

> 全部为 workbuddy.cn 官方文档正文本次直接请求并成功抓取（[A]）。

---

## 2. 逐能力依据

| 能力 | 状态 | 依据 | 关键原文要点 |
| --- | --- | --- | --- |
| 项目级记忆入口 | `SUPPORTED` | #1 #2 [A] | `./CODEBUDDY.md` 或 `./.codebuddy/CODEBUDDY.md`，两处等效 |
| 项目级规则 | `SUPPORTED` | #1 #2 [A] | `.codebuddy/rules/*.md` 全部自动递归加载，优先级同 `.codebuddy/CODEBUDDY.md` |
| 常驻 / 条件触发 | `SUPPORTED` | #2 [A] | `alwaysApply` 默认 `true` 常驻；`false` + `paths` 为条件触发；`false` 且无 `paths` 不加载 |
| 仅当前工作目录加载项目规则 | `SUPPORTED` | #1 #2 [A] | 项目规则只从当前工作目录 `.codebuddy/rules/` 加载，不加载父目录 |
| `AGENTS.md` 兼容 | `SUPPORTED` | #2 [A] | 存在 `CODEBUDDY.md` 时用之，否则用 `AGENTS.md`；`CODEBUDDY.md` 优先 |
| 文件引用（`CODEBUDDY.md` 内联 import） | `SUPPORTED` | #2 [A] | `@path/to/import` 语法，相对/绝对路径，最大深度 5 层 |
| Skills | `SUPPORTED` | #1 #3 [A] | `.codebuddy/skills/<name>/SKILL.md`；`name`/`description` 必填；项目级优先 |
| 自定义 Agent | `SUPPORTED` | #1 #4 [A] | `.codebuddy/agents/*.md`；`name`/`description` 必填；正文 = system prompt |
| 自定义 Command | `SUPPORTED` | #1 #5 [A] | `.codebuddy/commands/*.md`；`/group:cmd` 嵌套；`$ARGUMENTS` |
| 用户级全局规则 | 本仓库不生成 | #1 #2 [A] | 官方有 `~/.codebuddy/rules/`（对所有项目生效），但任务书禁止写用户级目录 → `project_only=True` |
| 运行时加载核对 | `PARTIAL` | #2 [A] | `/memory` 可查已加载规则与记忆；真实客户端效果待人工验证 |

---

## 3. 关键限制（官方原文）

| 限制 | 原文要点 | 本仓库处置 |
| --- | --- | --- |
| 上下文注入非强制配置 | 记忆/规则随启动载入上下文，冲突需靠明确定义裁决 | 规范冲突靠 `../../core/README.md` 裁决，不靠文件顺序 |
| 项目规则不加载父目录 | "项目级规则仅从当前工作目录的 `.codebuddy/rules/` 加载，不会加载父目录的规则文件夹" | 要求工作目录为项目根；入口与规则都放项目根 |
| `alwaysApply: false` 无 `paths` 不加载 | 规则类型判定表明确该组合"不支持" | 常驻规则不带 frontmatter，取默认 `true` |
| 用户级规则先于项目级加载，项目级优先级更高 | #2 "用户级规则在项目规则之前加载，给予项目规则更高的优先级" | 只装项目级，避免与用户全局配置争用 |
| 桌面端与 CLI 目录名可能存在差异 | CLI 官方写 `.codebuddy/`；宿主环境另有 `.workbuddy/` | 按任务书与 CLI 官方落地 `.codebuddy/`，实测列为待验证 |

---

## 4. `UNVERIFIED` 与差异记录

| 项 | 状态 | 说明 | 本仓库处置 |
| --- | --- | --- | --- |
| 桌面端项目级读取目录名（`.codebuddy/` vs `.workbuddy/`） | `UNVERIFIED` | 官方 CLI 文档只写 `.codebuddy/`；桌面端运行时环境可见 `.workbuddy/`（环境事实，非官方格式文档）；腾讯云社区文章称桌面端与 CodeBuddy Code 一致 [B] | 按任务书指定的 `.codebuddy/` 落地；真实客户端待实测 |
| 桌面端"项目配置"（云端注入的指令/技能/专家/连接器）与磁盘 `.codebuddy/` 的关系 | `UNVERIFIED` | 官方产品文档未明确两者是否都读、优先级如何 | 只依赖磁盘 `.codebuddy/`，不假设云端注入 |
| 真实客户端运行时自动发现规则 / Skills / Agents | **未执行** | 当前环境未安装真实 WorkBuddy 客户端 | 静态 + 模拟验证，明确区分（见验收报告） |
| Commands 运行时触发 | 未生成 | 本阶段不生成 Commands | 不存在产物，无运行时结论 |

---

## 5. 复核触发条件

1. WorkBuddy 调整 `.codebuddy/rules/` frontmatter 字段（`enabled` / `alwaysApply` / `paths`）语义；
2. Skills frontmatter 白名单或发现路径变化；
3. 桌面端项目级配置目录从 `.codebuddy/` 变更或双目录并存；
4. `CODEBUDDY.md` 与 `AGENTS.md` 的兼容 / 优先级规则变化；
5. 开放规范 `agentskills.io/specification` 升级。

---

## 6. 相关文档

- 能力矩阵：[`../../docs/architecture/tool-compatibility.md`](../../docs/architecture/tool-compatibility.md) · 安装目标格式：[`../../docs/tool-adapters.md`](../../docs/tool-adapters.md)
- 适配说明：[`README.md`](README.md) · 映射：[`mappings.md`](mappings.md) · 统一架构：[`../README.md`](../README.md)

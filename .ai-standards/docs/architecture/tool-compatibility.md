# 工具能力对照表（Tool Compatibility Matrix）

> 本文是 Phase 4 的核心交付：**AI 编程工具的能力矩阵**，用于回答"某个能力该工具到底支不支持、以什么方式支持、能不能依赖"。
> 查阅日期：**2026-11-11**；适配层参考的官方文档日期即本日期。
> 原则：**只按官方文档判定，不按历史经验推断**；无法确认的能力标 `UNVERIFIED`，本仓库不依赖它。
> 本文与 `docs/tool-adapters.md` 的分工：本文给**能力判定与状态**，tool-adapters.md 给**安装目标格式与历史核实记录**。
>
> **Phase 6 增补**：§1–§6 的 11 项能力矩阵是 Phase 4 对四种工具（Codex / Claude Code /
> Cursor / Copilot）的历史判定，保持原样以留档；**腾讯 WorkBuddy 作为第 5 个工具**，
> 其能力判定与官方依据单独记录于 [§8 WorkBuddy（Phase 6 新增）](#8-workbuddyphase-6-新增)，
> 不改写 Phase 4 的历史矩阵。适配实现见 [`../../adapters/workbuddy/README.md`](../../adapters/workbuddy/README.md)。

---

## 0. 判定口径

### 0.1 能力状态（四选一）

| 状态 | 含义 |
| --- | --- |
| `SUPPORTED` | 官方文档明确支持，且在主要/默认环境可用 |
| `PARTIAL` | 能力存在但有明确限制：仅部分环境/版本可用、处于预览、或需额外配置才成立 |
| `UNSUPPORTED` | 官方文档明确声明不支持，或不提供任何机制 |
| `UNVERIFIED` | 本次查阅**没有找到官方确认证据**；不是"不支持"，只是"不能依赖" |

### 0.2 适配方式（五选一）

区分"工具能不能读某个文件"与"本仓库要不要依赖它"是两件事，因此每个能力同时标注适配方式：

| 方式 | 含义 |
| --- | --- |
| ① 原生支持 | 工具按官方约定自动发现，无需转换 |
| ② 通过配置支持 | 需写入官方规定的配置文件/字段后才生效 |
| ③ 需手动引用 | 工具会读文件，但不会自动发现；须在入口里写清路径由 Agent 自行读取 |
| ④ 需适配或转换 | 公共规范需转成工具专属格式/路径才能生效 |
| ⑤ 不支持 | 无机制，不得编造配置假装支持 |

### 0.3 来源等级

- **[A]** 官方文档正文本次直接抓取成功。
- **[B]** 官方站点检索索引正文 / 官方中文镜像正文（域名属官方，但非目标英文页直接抓取）。
- **[C]** 第三方资料 —— **不作为判定依据**，仅在"待验证"里说明差异来源。

### 0.4 两条防误判规则

1. **支持 Markdown ≠ 支持 Agent Skills**。只有官方提供专门的 Skills 发现目录与 `SKILL.md` 约定时才判 `SUPPORTED`。本次四工具均有官方 Skills 文档，故均为 `SUPPORTED`（依据见 §3.3）。
2. **能读某个目录 ≠ 会自动发现该目录全部文件**。自动发现必须有官方明确的"启动时扫描/递归发现"陈述；否则归为"需手动引用"。

---

## 1. 能力矩阵（主表）

> 单元格格式：**状态** · 适配方式 — 关键说明。
> "项目/全局规则""文件引用""自动发现"等是不同维度，不可相互推出。

| 能力 | Codex | Claude Code | Cursor | Copilot |
| --- | --- | --- | --- | --- |
| **项目级规则** | `SUPPORTED` · ① — 项目根 `AGENTS.md`，从根向 CWD 逐层取 | `SUPPORTED` · ① — `./CLAUDE.md` 或 `./.claude/CLAUDE.md` | `SUPPORTED` · ④ — `.cursor/rules/*.mdc`，必须 `.mdc` + frontmatter | `SUPPORTED` · ① — `.github/copilot-instructions.md` |
| **全局 / 用户级规则** | `SUPPORTED` · ① — `~/.codex/AGENTS.md`（`CODEX_HOME` 可改） | `SUPPORTED` · ① — `~/.claude/CLAUDE.md` + 三层 managed policy | `PARTIAL` · ② — User Rules 仅在 Customize UI 配置，**磁盘无项目可写路径** | `PARTIAL` · ② — 仅 CLI 有 `~/.copilot/copilot-instructions.md`；组织级靠 UI |
| **Skills（开放标准）** | `SUPPORTED` · ① — `.agents/skills`（REPO/USER/ADMIN/SYSTEM） | `SUPPORTED` · ① — `.claude/skills/<name>/SKILL.md`（含嵌套/插件） | `SUPPORTED` · ① — `.agents/skills/`、`.cursor/skills/`，兼容 `.claude/.codex/skills` | `SUPPORTED` · ① — `.github/skills/`、`.claude/skills/`、`.agents/skills/` |
| **自定义 Agent** | `SUPPORTED` · ② — `config.toml` 的 `[agents]` 定义角色；**字段格式** `UNVERIFIED` | `SUPPORTED` · ① — `.claude/agents/*.md`，YAML frontmatter + 独立上下文 | `SUPPORTED` · ① — `.cursor/agents/*.md`，兼容 `.claude/.codex/agents` | `PARTIAL` · ① — `.github/agents/NAME.md`（agent profile）；部分 IDE 为公开预览 |
| **Hooks** | `SUPPORTED` · ② — `hooks.json` 或 `config.toml [hooks]`；项目级需 trusted | `SUPPORTED` · ② — `settings.json` 定义，`PreToolUse` 可阻断 | `SUPPORTED` · ② — `.cursor/hooks.json`（`version:1`），exit 2 阻断 | `PARTIAL` · ② — `.github/hooks/*.json`；CLI/cloud agent/app 支持，多数 IDE 不支持或预览 |
| **文件引用（Markdown 内联 import）** | `PARTIAL` · ③ — 无官方 `@import`；靠列路径让 Agent 自行读取 | `SUPPORTED` · ① — `@path` import，最多 4 跳，**但不减少上下文成本** | `PARTIAL` · ③ — 规则中 `@file` 只提示去读，**不内联内容** | `UNVERIFIED` · ③ — 未找到官方确认的 Markdown 内联 import 语法 |
| **自动发现** | `SUPPORTED` · ① — 启动时构建指令链 + 递归扫描 `.agents/skills` | `SUPPORTED` · ① — CLAUDE.md 向上遍历 + rules/skills/agents 递归发现 | `SUPPORTED` · ① — 启动时自动递归发现 rules 与 SKILL.md | `PARTIAL` · ① — 仓库级指令/Skills 自动发现，但**路径级指令在 GitHub.com 仅 cloud agent/code review 支持** |
| **子目录规则** | `SUPPORTED` · ① — 子目录 `AGENTS.md` / `AGENTS.override.md`，逐层覆盖 | `SUPPORTED` · ① — 子目录 CLAUDE.md 按需加载 + rules 的 `paths` 字段 | `SUPPORTED` · ① — `.cursor/rules` 可分子目录 + `globs` + 嵌套 skills 自动作用域 | `PARTIAL` · ④ — `.github/instructions/**/*.instructions.md` + `applyTo`；surface 依赖 |
| **MCP 集成** | `SUPPORTED` · ② — `config.toml` 的 `mcp_servers` / `[[mcp_servers]]` | `SUPPORTED` · ② — 官方 MCP 支持；`.mcp.json` 等；**精确配置路径** `UNVERIFIED` | `SUPPORTED` · ② — 官方 MCP 支持（hooks 含 MCP 事件）；**精确配置路径** `UNVERIFIED` | `SUPPORTED` · ② — `mcp.json`（随 IDE 变动）+ agent profile 的 `mcp-servers` + CLI `~/.copilot/mcp-config.json` |
| **规则优先级** | `SUPPORTED` · ① — 近目录覆盖远目录；每层最多一个文件 | `PARTIAL` · ① — 全部拼接、**无硬优先级**，冲突时 Agent 可能任选；硬阻断须用 hook | `SUPPORTED` · ① — Team → Project → User，早者优先 | `SUPPORTED` · ① — Personal → Repository → Organization；相关指令同时提供 |
| **工具配置方式** | `~/.codex/config.toml` + 项目 `.codex/config.toml`（需 trusted） | `.claude/settings.json` / `.settings.local.json` / managed settings | Customize UI + `.cursor/hooks.json` + `~/.cursor/cli-config.json` | `.github/`（仓库）+ `~/.copilot/`（个人）+ IDE Agent Customizations editor |

### 1.1 矩阵结论

1. **常驻规则入口无共同交集**：`AGENTS.md` / `CLAUDE.md` / `.cursor/rules/*.mdc` / `.github/copilot-instructions.md` 四者互不等价，必须由适配层分别生成。
2. **Skills 有共同标准**：四工具都遵循 `agentskills.io/specification`，`SKILL.md` **内容可单源复用**；只有"安装到哪个目录"不同。
3. **Claude Code 的 `@import` 是特例**：唯一官方支持 Markdown 内联导入的工具，但导入会连同正文进入上下文，与"按需加载"冲突，故本仓库**不依赖**它拉全量规范。
4. **Hooks 四工具都有，但配置格式互不相同**：`config.toml [hooks]` / `settings.json` / `.cursor/hooks.json` / `.github/hooks/*.json`。按用户要求，Phase 4 **只记录能力边界**，不生成任何 Hooks 自动化（留到后续阶段评估）。
5. **自定义 Agent 四工具都有，但字段格式各不相同**：只有 `name`/`description` 是跨工具共识；`tools`/`model`/`readonly` 等属工具专有，不得写进 `agents/` 源文件。

---

## 2. 项目级 / 全局 / 子目录规则的发现机制

### 2.1 Codex（`SUPPORTED` · 原生）

- **全局**：`~/.codex/AGENTS.md`；若有 `AGENTS.override.md` 则优先读它；`CODEX_HOME` 改变 home（默认 `~/.codex`）。
- **项目**：从项目根（通常 Git 根）向当前工作目录遍历；每层按 `AGENTS.override.md` → `AGENTS.md` → `project_doc_fallback_filenames` 中备用名，**每层最多取一个文件**。
- **合并**：从根向当前目录用空行拼接，越近越靠后、优先级越高；达 `project_doc_max_bytes`（默认 **32 KiB**）停止追加。
- **格式**：纯 Markdown，无 frontmatter、无专有配置项。
- 依据 [B]：官方中文镜像 `https://developers.openai.ac.cn/codex/guides/agents-md`（英文页 `developers.openai.com/codex/guides/agents-md` 本次抓取返回 Forbidden）。

### 2.2 Claude Code（`SUPPORTED` · 原生，但无硬优先级）

- **层级**（由宽到窄）：managed policy → `~/.claude/CLAUDE.md` → `./CLAUDE.md` 或 `./.claude/CLAUDE.md` → `./CLAUDE.local.md`。
- **加载**：启动时加载当前目录及所有父目录的 CLAUDE.md；子目录文件在读写该子目录文件时**按需加载**。
- **优先级**：全部**拼接而非覆盖**；官方明确"冲突时 Claude 可能任选其一"。要硬性阻断须用 `PreToolUse` hook，而不是依赖优先级。
- **`.claude/rules/*.md`**：递归发现；无 `paths` frontmatter 的规则启动时加载；`paths` 是规则 frontmatter 中**唯一**被读取的字段，其余被忽略且不报错。用户级 `~/.claude/rules/` 对所有项目生效。
- **`@path` import**：相对包含文件解析，最多 **4 跳**；外部导入需首次批准；官方明确 **import 不减少上下文成本**。
- 依据 [A]：`https://code.claude.com/docs/en/memory`（标题 "How Claude remembers your project"）。

### 2.3 Cursor（`SUPPORTED` · 需 `.mdc` 转换）

- **项目规则**：`.cursor/rules/*.mdc`，**必须 `.mdc`**；该目录下 `.md` 被忽略（无 frontmatter 指定 `description`/`globs`/`alwaysApply`）。可用子目录组织。
- **frontmatter 交互**：
  | `alwaysApply` | `description` | `globs` | 行为 |
  | --- | --- | --- | --- |
  | `true` | — | — | 每次会话包含，忽略其余 |
  | `false` | — | 提供 | 匹配文件进入上下文时自动附加 |
  | `false` | 提供 | 省略 | Agent 依描述判断相关性后拉取 |
  | `false` | 省略 | 省略 | 仅 `@`-提及时使用 |
- **`@file`**：只提示 Agent 去读，**不内联**内容（editor / CLI / Cloud Agents 一致）。
- **优先级**：Team → Project → User，早者优先。
- **AGENTS.md**：可作为 `.cursor/rules` 的简易替代，支持项目根与子目录，纯 Markdown 无元数据。
- 依据 [A]：`https://cursor.com/docs/rules`（标题 "Rules | Cursor Docs"）。

### 2.4 Copilot（`SUPPORTED` · 仓库级原生 / 路径级 surface 依赖）

- **仓库级**：`.github/copilot-instructions.md`，纯 Markdown，作用于仓库上下文全部请求。
- **路径级**：`.github/instructions/**/*.instructions.md`，**必须**含 `applyTo` frontmatter（glob，逗号分隔）；可选 `excludeAgent`。
- **surface 限制**：官方明确"在 GitHub.com 上，路径级指令目前仅 Copilot cloud agent 与 Copilot code review 支持"；IDE 支持随版本不同。
- **优先级**：Personal > Repository > Organization；相关指令**同时**提供，应尽量互不冲突。
- 依据 [A]：`https://docs.github.com/en/copilot/reference/custom-instructions-support`。

---

## 3. Skills（四工具共同标准）

### 3.1 开放规范约束（共同基准）

来源 [A]：`https://agentskills.io/specification`（标题 "Specification - Agent Skills"，查阅 2026-11-11）。

| 项 | 官方约束 |
| --- | --- |
| 最小结构 | 目录 + `SKILL.md` |
| 必填字段 | `name`、`description` |
| `name` | 1–64 字符；仅小写字母/数字/连字符；不得首尾连字符；不得含连续 `--`；**必须与父目录名一致** |
| `description` | 1–1024 字符，非空；应同时说明"做什么"与"何时用" |
| 可选字段 | `license`、`compatibility`（≤500）、`metadata`（string→string）、`allowed-tools`（实验性）——**共 6 个** |
| 正文 | frontmatter 之后 Markdown；建议 < 5000 tokens、**< 500 行** |
| 可选目录 | `scripts/`、`references/`、`assets/` |
| 文件引用 | 相对技能根目录，**保持一级深度**，避免深层引用链 |
| 渐进披露 | ① `name`+`description`（约 100 tokens）→ ② `SKILL.md` 正文 → ③ 按需资源 |

### 3.2 各工具发现路径

| 工具 | 项目级 | 用户级 | 兼容 / 其他 | 依据 |
| --- | --- | --- | --- | --- |
| Codex | `$CWD/.agents/skills`、`$CWD/../.agents/skills`、`$REPO_ROOT/.agents/skills` | `$HOME/.agents/skills` | 管理员 `/etc/codex/skills`；系统内置；**支持软链接目录** | [B] `developers.openai.ac.cn/codex/skills` |
| Claude Code | `.claude/skills/<name>/SKILL.md` | `~/.claude/skills/` | 嵌套 `<subdir>/.claude/skills/`、插件 `<plugin>/skills/`/[A] `code.claude.com/docs/en/skills` |  |
| Cursor | `.agents/skills/`、`.cursor/skills/` | `~/.agents/skills/`、`~/.cursor/skills/` | 兼容 `.claude/skills/`、`.codex/skills/`；递归发现、嵌套自动作用域 | [A] `cursor.com/docs/context/skills` |
| Copilot | `.github/skills/`、`.claude/skills/`、`.agents/skills/` | `~/.copilot/skills/`、`~/.agents/skills/` | `gh skill` 发现安装；code review 从 head branch 读取 | [A] `docs.github.com/en/copilot/concepts/customizations/agent-skills` |

### 3.3 关键限制（影响适配决策）

- **Claude Code**：标准字段仅 6 个;上传 claude.ai / 走 Skills API 时**出现其他字段会硬报错**（`Unexpected key(s) in SKILL.md frontmatter`）。`description`+`when_to_use` 在技能列表 **1,536 字符**处截断。Cowork / cloud sessions 不读本机 `~/.claude/skills/`。[A]
- **Codex**：初始技能列表约为上下文窗口 2%（未知窗口时 **8,000 字符**），列表过大时优先缩短 `description` 甚至剔除技能，故触发词须前置。可选 `agents/openai.yaml`（应用 UI 元数据 / 调用策略 / 工具依赖）属**工具专有配置，本仓库不使用**。[B]
- **Cursor**：工具扩展字段 `paths`/`disable-model-invocation`/`icon`/`color` 可用，但**本仓库不写入**以免破坏工具无关性。用户级技能需开启 "Sync Skills for Cloud Agents" 才用于 Cloud Agents；自动化运行不加载用户级技能。[A]
- **Copilot**：Agent Skills 与自定义指令是**两套机制**，不可互相替代；IDE 支持取决于版本（见 `reference/copilot-feature-matrix`）。[A]

**本仓库决策**：`skills/` 保持单源、只用 6 个标准字段；按各工具官方路径**复制**（不符号链接，理由见 `adapters/README.md` §5）。镜像中的 `skills/` 仅作引用副本，**不被任何工具当发现目录**。

---

## 4. 自定义 Agent 对照

公共 `agents/` 是**角色契约**（纯文本、工具无关），不是可执行 Agent。映射到各工具"自定义 Agent"时，只保留跨工具共识字段，工具专有字段留在适配层。

| 工具 | 官方配置方式 | 项目级路径 | 必填 / 常见字段 | 独立上下文 | 依据 |
| --- | --- | --- | --- | --- | --- |
| Codex | `config.toml [agents]` | `~/.codex/config.toml` | **字段格式** `UNVERIFIED`（官方 Subagents 页本次 Forbidden） | 有 subagent 机制（hooks 含 `SubagentStart/Stop`） | [A] `config-file/config-advanced` |
| Claude Code | Markdown + YAML | `.claude/agents/` | `name`、`description`（必填）；`tools`/`model`/`skills`/`mcpServers`/`hooks` 等可选 | 是（`its own context window`） | [A] `code.claude.com/docs/en/sub-agents` |
| Cursor | Markdown + YAML | `.cursor/agents/`（兼容 `.claude`/`.codex`） | `name`/`description`（可选，建议写）、`model`/`readonly`/`is_background` | 是，可并行 | [A] `cursor.com/docs/agent/subagents` |
| Copilot | Markdown + YAML（agent profile） | `.github/agents/NAME.md` | `name`（可选）、`description`（必填）、`tools`/`mcp-servers`/`model`/`target`；正文 = prompt（≤30,000 字符） | 由主 agent 派生 | [A] `docs.github.com/en/copilot/concepts/agents/cloud-agent/about-custom-agents` |

**映射结论**：`agents/architect|developer|reviewer|tester.md` 的角色职责与协作接口可直接作为各工具 agent 的**正文（system prompt）**；`name`/`description` 由适配层提取；`tools`/`model` 等**不进入公共源文件**。Phase 4 只给出映射方案与模板，不生成可安装的 agent 配置（避免虚构字段，且安装属 Phase 5）。

---

## 5. Hooks 对照（仅记录能力，不生成自动化）

| 工具 | 状态 | 配置文件 | 关键事件 | 阻断能力 |
| --- | --- | --- | --- | --- |
| Codex | `SUPPORTED` · ② | `~/.codex/hooks.json` / `~/.codex/config.toml` / `<repo>/.codex/hooks.json` / `config.toml [hooks]` | `PreToolUse`/`PostToolUse`/`PermissionRequest`/`PreCompact`/`SubagentStart/Stop`/`Stop` 等 | `PermissionRequest` 可 `allow/deny`；`PreToolUse` 可阻断/改写；项目级需 trusted | 
| Claude Code | `SUPPORTED` · ② | `~/.claude/settings.json` / `.claude/settings.json` / `.claude/settings.local.json` | `PreToolUse`/`PostToolUse`/`SessionStart/End`/`Stop`/`SubagentStart/Stop`/`InstructionsLoaded` 等 | `PreToolUse` 可 `deny`；官方建议硬策略用 permission 系统 | 
| Cursor | `SUPPORTED` · ② | `<project>/.cursor/hooks.json` / `~/.cursor/hooks.json` | `preToolUse`/`postToolUse`/`beforeShellExecution`/`afterFileEdit`/`beforeSubmitPrompt`/`stop` 等 | exit 2 = `deny`；`failClosed` 控制失败放行；优先级 Enterprise → Team → Project → User | 
| Copilot | `PARTIAL` · ② | `.github/hooks/*.json`（仓库）/ `~/.copilot/hooks/*.json`（CLI 个人） | `sessionStart/End`/`userPromptSubmitted`/`preToolUse`/`postToolUse`/`agentStop`/`subagentStop`/`errorOccurred` | `preToolUse` 可 approve/deny；cloud agent 仅支持子集且仅 `bash` 字段 | 

依据：Codex [B] `developers.openai.com/codex/hooks` + [A] `config-file/config-advanced`；Claude Code [A] `code.claude.com/docs/en/hooks`（标题 "Hooks reference"）；Cursor [A] `cursor.com/docs/hooks`；Copilot [A] `docs.github.com/en/copilot/concepts/customizations/hooks`。

**本仓库决策（Phase 4）**：四工具 Hooks 都**只记录能力边界**，不生成任何 `hooks.json` / `settings.json`。理由：① Hooks 执行用户脚本，属高价值用户资产且需 trusted；② 各工具格式与事件不同，强行统一会虚构配置；③ 用户要求本阶段只做适配说明与兼容性验证。未来若启用，适合放"修改后格式化""提交前测试""阻止敏感文件误操作"，但**不得把全部工程规范转成 Hooks**。

---

## 6. 未验证清单（不得依赖）

以下项本次查阅**无官方确认**，凡涉及处一律标 `UNVERIFIED`，本仓库的适配与验证**不依赖**它们：

| # | 未验证项 | 现状 | 影响与处置 |
| --- | --- | --- | --- |
| 1 | Codex `config.toml [agents]` 的**具体字段格式** | 官方 Subagents 页本次 Forbidden；仅从 `config-advanced` 确认 `[agents]` 存在 | 不生成 Codex agent 配置；只给映射说明 |
| 2 | Codex `name`/`description` 单独长度上限 | 官方可读正文未给数值；第三方 [C] 称 100/500 | 按开放规范 64/1024 执行，描述控制在 300 字符内 |
| 3 | Codex 是否读取 `.codex/skills/` | 官方主路径为 `.agents/skills`；Cursor 文档把 `.codex/skills` 列为**兼容**路径 [A] | 只用官方明确的 `.agents/skills/` |
| 4 | Copilot 路径级指令在每个 IDE 版本的实际读取行为 | 官方明示 "IDE support depends on the version you use" | 仓库级 + 路径级双通道并存，规避单一通道失效 |
| 5 | Copilot 是否支持 Markdown 内联 `@import` | 未找到官方语法说明 | 不依赖；改用安装时复制完整镜像保证链接完整 |
| 6 | Claude Code MCP 配置**精确路径** | MCP 专页本次抓取失败；能力由 hooks/sub-agents/config 多页正文佐证 | 只声明"支持 MCP"，不写具体配置文件 |
| 7 | Cursor MCP 配置**精确路径** | MCP 专页本次抓取失败；能力由 hooks 页 MCP 事件佐证 | 同上 |
| 8 | Cursor `icon`/`color` 跨版本表现 | 官方列为可选字段，版本差异未明确 | 不使用这些扩展字段 |
| 9 | Copilot `excludeAgent` 跨 CLI/IDE 行为 | 官方支持矩阵未逐环境说明 | 不设置该字段 |
| 10 | 官方 `skills-ref` 校验器版本 / 安装 | 规范页推荐但未在可读正文给版本 | 自建等价校验，不宣称与 `skills-ref` 结果完全一致 |

---

## 7. 相关文档

- 安装目标格式与历史核实记录：`../tool-adapters.md`
- 统一映射机制、引用处理、版本兼容：`../../adapters/README.md`
- 各工具官方参考（标题 + URL + 查阅日期）：`../../adapters/codex/references.md`、`../../adapters/claude-code/references.md`、`../../adapters/cursor/references.md`、`../../adapters/copilot/references.md`、`../../adapters/workbuddy/references.md`
- 架构三层模型：`../architecture.md`
- 公共规范冲突裁决：`../../core/README.md`

---

## 8. WorkBuddy（Phase 6 新增）

腾讯 WorkBuddy 是 Phase 6 加入的第 5 个工具。其 CLI 引擎为 CodeBuddy Code，磁盘配置目录官方命名为 `.codebuddy/`。以下能力判定依据官方文档（workbuddy.cn，[A]，2026-11-11），完整依据表见 [`../../adapters/workbuddy/references.md`](../../adapters/workbuddy/references.md)。

### 8.1 能力矩阵（WorkBuddy 列）

| 能力 | 状态 | 适配方式 — 关键说明 |
| --- | --- | --- |
| **项目级规则** | `SUPPORTED` | ④ — `CODEBUDDY.md`（记忆入口）+ `.codebuddy/rules/*.md`（叠加规则，递归自动加载） |
| **全局 / 用户级规则** | 官方支持但本仓库不生成 | `~/.codebuddy/rules/` 官方存在；任务书禁止写用户级目录 → `project_only=True`，`--scope global` 完全跳过 |
| **Skills（开放标准）** | `SUPPORTED` | ① — `.codebuddy/skills/<name>/SKILL.md`，`name`/`description` 必填 |
| **自定义 Agent** | `SUPPORTED` | ① — `.codebuddy/agents/*.md`，YAML frontmatter + 正文=system prompt；本仓库只给映射模板，不生成 |
| **Commands** | `SUPPORTED` | ① — `.codebuddy/commands/*.md`，`/<name>` 触发；5 个 Skill 已覆盖工作流，本仓库不生成 |
| **文件引用（Markdown import）** | `SUPPORTED` | ① — `CODEBUDDY.md` 支持 `@path` 导入，最多 5 层；本仓库不用它拉全量规范 |
| **自动发现** | `SUPPORTED` | ① — 启动时加载项目 `CODEBUDDY.md` + 递归发现 `.codebuddy/rules/`、Skills、Agents |
| **子目录规则** | `PARTIAL` | ② — 项目规则**仅**从当前工作目录 `.codebuddy/rules/` 加载，不加载父目录；需以项目根为工作目录 |
| **与 AGENTS.md 兼容** | `SUPPORTED` | ① — 存在 `CODEBUDDY.md` 时用之，否则用 `AGENTS.md`；`CODEBUDDY.md` 优先 |
| **规则优先级** | `SUPPORTED` | ① — 项目级 > 用户级 > 插件级，同名项目级优先；上下文注入非强制配置 |
| **运行时加载验证** | `UNVERIFIED` | 当前环境未安装真实 WorkBuddy 客户端；`/memory` 可查已加载规则，须人工核对 |

### 8.2 关键差异与不依赖项

1. **project-only 是硬约束**：任务书明确"不创建用户级全局规则""不写入用户级目录"。WorkBuddy 与其余四工具不同——`--scope global` 时**完全跳过**，不写 `~/.codebuddy/`。这是通过 `GlobalToolSpec.project_only` 通用标志 + 安装器/校验器守卫实现的，非硬编码工具名。
2. **项目指令 ≠ 项目级代码规则**：`CODEBUDDY.md` 是项目记忆入口（提供上下文与索引），`.codebuddy/rules/` 是代码开发规则。二者职责分离，不满足"把项目指令当全局规则"的误用。
3. **规则类型三态**：`alwaysApply` 默认 `true` → 常驻；`false` + `paths` → 条件触发；`false` 且无 `paths` → 不加载。本仓库的叠加规则刻意**不带 frontmatter**，取默认常驻，避免被降级为条件规则。
4. **桌面端目录名待验证**：官方 CLI 文档只写 `.codebuddy/`，但桌面端运行时环境可见 `.workbuddy/`（环境事实，非官方格式文档）。按任务书与官方 CLI 落地 `.codebuddy/`，真实桌面端读取目录须实测。

### 8.3 未验证清单

| 项 | 状态 | 处置 |
| --- | --- | --- |
| 真实客户端自动发现规则 / Skills / Agents | `UNVERIFIED` | 静态 + 模拟验证，不宣称通过；须人工用 `/memory`、Skills 列表、probe prompt 核对 |
| 桌面端读取 `.codebuddy/` 还是 `.workbuddy/` | `UNVERIFIED` | 按官方 CLI + 任务书落地 `.codebuddy/`；实测待办 |
| 桌面端"项目配置"（云端注入）与磁盘 `.codebuddy/` 的关系 | `UNVERIFIED` | 只依赖磁盘目录，不假设云端注入 |
| Agents / Commands 运行时生效 | 未生成 | 本阶段不生成可执行 agent / command，相关能力标未验证 |

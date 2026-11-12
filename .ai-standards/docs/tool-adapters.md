# 工具适配器：官方能力核实与差异说明

> 核实日期：**2026-11-11**（Phase 1 建立，Phase 4 复核）
> 原则：**不凭记忆写配置**。本文每一条路径/字段都标注了官方来源；无法确认的项明确标为「待验证」，
> 本仓库不会在生成文件中写入未确认的配置项。
> 核实方式：直接抓取官方文档页面 + 官方站点检索索引。部分 `developers.openai.com` 页面
> 直接抓取返回 `Forbidden`，对应结论改由**官方中文镜像** `developers.openai.ac.cn`
> 与官方站点检索索引交叉确认，并已在下文逐条标注来源等级。

> **Phase 4 复核提示（2026-11-11）**：本文保留 Phase 1 建立的**安装目标格式与逐条官方依据**，
> 但能力判定的**权威来源已迁移**至 [能力对照表](architecture/tool-compatibility.md)，
> **Phase 6 增补**：腾讯 WorkBuddy 作为第 5 个工具的核实记录见 [§8](#8-腾讯-workbuddyphase-6-新增)，
> 其适配器实现见 [`../adapters/workbuddy/README.md`](../adapters/workbuddy/README.md)。
> 各工具的完整官方参考（标题 + URL + 查阅日期 + 来源等级）见
> `adapters/codex/references.md`、`adapters/claude-code/references.md`、
> `adapters/cursor/references.md`、`adapters/copilot/references.md`。
> **相对本文的结论更新（以新矩阵为准）**：
>
> 1. **GitHub Copilot** 官方现已支持 **Agent Hooks**（`.github/hooks/*.json`）与
>    **Custom Agents**（`.github/agents/*.md`）——本文 §5 未覆盖，已补入能力矩阵与
>    `adapters/copilot/`（本阶段只记录能力，不生成 Hooks 自动化）。
> 2. **OpenAI Codex** 官方现已支持 **Hooks**（`~/.codex/hooks.json` / `config.toml [hooks]`）与
>    **Subagents**（`config.toml [agents]`）——本文 §2 未覆盖，已补入能力矩阵。
> 3. **Cursor** 官方现已支持 **Hooks**（`.cursor/hooks.json`）与
>    **Subagents**（`.cursor/agents/*.md`）、**MCP**——本文 §4 未覆盖，已补入能力矩阵。
> 4. 能力状态统一采用 `SUPPORTED` / `PARTIAL` / `UNSUPPORTED` / `UNVERIFIED` 四级，
>    并区分「原生 / 通过配置 / 需手动引用 / 需适配转换 / 不支持」五种适配方式，详见新矩阵 §0。
>
> 若本文表述与新矩阵不一致，**以新矩阵为准**。

来源等级：

- **[A] 官方文档正文直接抓取成功**
- **[B] 官方站点检索索引 / 官方中文镜像正文**（域名属于官方，但非直接抓取）
- **[C] 第三方资料** —— **不作为本仓库配置依据**，仅用于提示差异

---

## 1. Agent Skills 开放规范（共同基准）

来源 **[A]**：<https://agentskills.io/specification>

| 项目 | 规范约束 |
| --- | --- |
| 最小结构 | 一个目录 + `SKILL.md` |
| Frontmatter 必填 | `name`、`description` |
| `name` | 1–64 字符；仅小写字母 `a-z`、数字 `0-9`、连字符 `-`；不得以 `-` 开头/结尾；不得含连续 `--`；**必须与父目录名一致** |
| `description` | 1–1024 字符，非空；应同时描述「做什么」与「何时用」 |
| 可选字段 | `license`、`compatibility`（≤500 字符）、`metadata`（string→string 映射）、`allowed-tools`（实验性） |
| 正文 | YAML frontmatter 之后为 Markdown，无格式限制；建议 < 5000 tokens、**< 500 行** |
| 可选目录 | `scripts/`（可执行代码）、`references/`（按需文档）、`assets/`（模板/静态资源） |
| 文件引用 | 相对技能根目录，**保持一级深度**，避免深层引用链 |
| 渐进披露 | 发现（name+description）→ 激活（SKILL.md 正文）→ 执行（按需加载资源） |
| 官方校验器 | 规范页推荐 `skills-ref validate ./my-skill`（<https://github.com/agentskills/agentskills/tree/main/skills-ref>） |

**本仓库的取舍**：`validate.py` 实现了与上述约束等价的自建校验（Frontmatter 字段/长度/命名、
目录名一致性、行数、引用有效性、可选字段类型），**未集成 `skills-ref`**，
原因是它是需要单独安装的外部工具，与「零第三方依赖」约束冲突。
> ⚠️ **待验证**：`skills-ref` 校验器的具体版本、安装方式与其额外检查项。
> 本仓库不宣称与 `skills-ref` 结果完全等价；如后续引入，应把其输出作为补充而非替代。

**Frontmatter 字段白名单决策**：本仓库的 `SKILL.md` **只使用规范中的 6 个字段**
（`name`、`description`、`license`、`compatibility`、`metadata`、`allowed-tools`）。
理由：Claude Code 的 `when_to_use`/`paths`/`hooks`、Cursor 的 `icon`/`color` 等是**工具扩展字段**，
写进统一源文件会破坏「工具无关」，并导致上传到 claude.ai / Skills API 时因
"Unexpected key(s) in SKILL.md frontmatter" 而失败（来源 **[A]** Claude Code Skills 文档）。

---

## 2. OpenAI Codex

官方资料：

- **[B]** <https://developers.openai.com/codex/guides/agents-md>（自定义指令 / AGENTS.md）
- **[B]** <https://developers.openai.com/codex/concepts/customization>（定制分层）
- **[B]** <https://developers.openai.com/codex/skills/> 与官方中文镜像
  **[A]** <https://developers.openai.ac.cn/codex/skills>
- **[B]** <https://developers.openai.com/codex/learn/best-practices>

### 2.1 AGENTS.md（已核实）

- 全局：`~/.codex/AGENTS.md`；若存在 `~/.codex/AGENTS.override.md` 则优先读它；
  可用 `CODEX_HOME` 改变 Codex home，默认 `~/.codex`。
- 项目：从项目根（通常是 Git 根）向下遍历到当前工作目录；每层依次找
  `AGENTS.override.md` → `AGENTS.md` → `project_doc_fallback_filenames` 中的备用名，
  **每层最多取一个文件**。
- 合并：从根到当前目录拼接（空行分隔），越靠近当前目录的文件出现在后面、优先级越高；
  达到 `project_doc_max_bytes`（默认 **32 KiB**）后停止继续追加。
- 格式：纯 Markdown，无 frontmatter、无专有配置项。

### 2.2 Skills（已核实）

| 作用域 | 官方路径 |
| --- | --- |
| REPO | `$CWD/.agents/skills`、`$CWD/../.agents/skills`、`$REPO_ROOT/.agents/skills` |
| USER | `$HOME/.agents/skills` |
| ADMIN | `/etc/codex/skills` |
| SYSTEM | 随 Codex 内置 |

- `SKILL.md` **必须**包含 `name` 和 `description`。
- 目录可含 `scripts/`、`references/`、`assets/`；另有可选的 `agents/openai.yaml`
  （Codex 应用专用 UI 元数据 / 调用策略 / 工具依赖，**本仓库不使用**，因为它属于工具专有配置）。
- 调用：显式 `/skills` 或 `$skill-name`，或由 `description` 隐式匹配。
- 初始技能列表默认约占上下文窗口 2%（未知窗口时 8,000 字符），可用
  `skills.max_context_tokens` 调整（≤10,000 tokens）。因此 `description` 必须**把关键触发词前置**。
- 支持软链接技能目录。

### 2.3 本仓库的适配方案

- 适配器源文件：`adapters/codex/AGENTS.md` → 安装到目标项目根 `AGENTS.md`。
- Skills 安装到：`<target>/.agents/skills/<skill-name>/`（**官方 REPO 作用域**）。
- 不写 `agents/openai.yaml`，不写 `~/.codex/config.toml`，不写任何 `CODEX_HOME` 配置。
- 入口 `AGENTS.md` 若已被用户占用则跳过（不覆盖），并提示用户在自有文件中按需引用
  `.ai-standards/` —— 这是官方支持的"入口文件 + 引用任务专属 md"的做法。

### 2.4 差异与待验证

- ⚠️ **待验证**：Codex 是否也读取 `.codex/skills/` / `~/.codex/skills/`。
  官方主文档给出的路径是 `.agents/skills` 与 `$HOME/.agents/skills`；
  第三方教程 **[C]** 提到 `.codex/skills`，Cursor 官方文档 **[A]** 也把 `.codex/skills`
  列为兼容路径。**本仓库只用官方明确给出的 `.agents/skills/`**，不依赖兼容路径。
- ⚠️ **待验证**：Codex 对 `name` / `description` 的单独长度上限。
  第三方资料 **[C]** 声称 100 / 500 字符，官方 Skills 文档未在可读正文中给出数值。
  本仓库按 Agent Skills 规范的 64 / 1024 执行，并把描述控制在 300 字符以内，
  使其在 8,000 字符的初始列表预算下也安全。
- ℹ️ Codex 的 `AGENTS.override.md` 机制与 Claude Code 的 `CLAUDE.local.md` 不等价，
  本仓库**不**把两者互相映射。

---

## 3. Claude Code

官方资料 **[A]**：

- <https://code.claude.com/docs/en/skills>
- <https://code.claude.com/docs/en/memory>

### 3.1 CLAUDE.md 与规则（已核实）

| 层级 | 路径 |
| --- | --- |
| User | `~/.claude/CLAUDE.md` |
| Project | `./CLAUDE.md` 或 `./.claude/CLAUDE.md` |
| Local（建议 gitignore） | `./CLAUDE.local.md` |
| Managed policy | macOS `/Library/Application Support/ClaudeCode/CLAUDE.md`；Linux/WSL `/etc/claude-code/CLAUDE.md`；Windows `C:\Program Files\ClaudeCode\CLAUDE.md` |

- 启动时加载当前目录**及其所有父目录**的 `CLAUDE.md` / `CLAUDE.local.md`；
  子目录中的文件在被读/写/编辑该子目录文件时**按需**加载。
- **不是覆盖式优先级**：所有发现的文件被拼接进上下文；冲突时 Claude 可能任选其一。
  需要硬性阻断应使用 `PreToolUse` hook 或 managed settings，而不是依赖优先级。
- `@path/to/file` import 会被展开进上下文（相对包含文件解析，最多 4 跳）；
  **import 不减少上下文成本**。可用 `@AGENTS.md` 让一份文件被多个工具共享。
- `.claude/rules/*.md` 递归发现；**无 frontmatter 的规则在启动时加载**，
  优先级与 `.claude/CLAUDE.md` 相同；`paths` 是规则 frontmatter 中**唯一**被读取的字段，
  其他字段被忽略且不报错。用户级 `~/.claude/rules/` 对所有项目生效。

### 3.2 Skills（已核实）

| 作用域 | 路径 |
| --- | --- |
| Personal | `~/.claude/skills/<skill-name>/SKILL.md` |
| Project | `.claude/skills/<skill-name>/SKILL.md` |
| Nested | `<subdir>/.claude/skills/<skill-name>/SKILL.md` |
| Plugin | `<plugin>/skills/<skill-name>/SKILL.md` |

- frontmatter 必须在文件**第一行**以 `---` 开始，否则整份文件被当作正文。
- 目录名或 `name` 决定 `/skill-name` 命令名。
- `description` + `when_to_use` 合并文本在技能列表中于 **1,536 字符**处截断。
- 建议 `SKILL.md` 保持 500 行以内；文档建议 `CLAUDE.md` 控制在 200 行以内。
- **标准字段仅 6 个**：`name`、`description`、`license`、`compatibility`、`metadata`、
  `allowed-tools`。上传到 claude.ai / 走 Skills API 打包时，出现其他字段会直接失败。
  Claude Code 本地还接受大量扩展字段（`paths`、`hooks`、`model`、`context` 等），
  **本仓库不使用**。
- Cowork / cloud sessions **不读取**本机 `~/.claude/skills/`；项目级
  `.claude/skills/` 在 project cloud threads 中也不可用。

### 3.3 本仓库的适配方案

- `adapters/claude-code/CLAUDE.md` → `<target>/CLAUDE.md`（**仅当不存在或由本仓库管理**）。
- `adapters/claude-code/rules/ai-engineering-standards.md` →
  `<target>/.claude/rules/ai-engineering-standards.md`（**可叠加，唯一文件名**，
  无 frontmatter，启动时加载）。这是入口文件被占用时的主要生效通道。
- Skills → `<target>/.claude/skills/<skill-name>/`。
- 不使用 `@path` import 把整个规范库拉进常驻上下文（与「按需加载」冲突）。

---

## 4. Cursor

官方资料 **[A]**：

- <https://cursor.com/docs/rules>
- <https://cursor.com/docs/context/skills>

### 4.1 Rules（已核实）

- Project Rules 位于 `.cursor/rules/`，**必须是 `.mdc` 扩展名**；
  该目录下的 `.md` 被规则系统忽略（因为它没有 frontmatter 指定 `description`/`globs`/`alwaysApply`）。
- frontmatter 三字段交互：

  | `alwaysApply` | `description` | `globs` | 行为 |
  | --- | --- | --- | --- |
  | `true` | — | — | 每次会话都包含，忽略其他两字段 |
  | `false` | — | 提供 | 匹配文件进入上下文时自动附加 |
  | `false` | 提供 | 省略 | Agent 依据描述判断相关性后拉取 |
  | `false` | 省略 | 省略 | 仅在 `@`-提及时使用 |

- `globs` 支持逗号分隔多模式；`*` 单层、`**` 递归。
- 规则中的 `@file` 是**提示 Agent 去读**，不会内联文件内容。
- 规则优先级：Team Rules → Project Rules → User Rules；User Rules 在
  Customize → Rules 中配置（不是磁盘文件，安装器不写）。
- `AGENTS.md` 作为 `.cursor/rules` 的简易替代，支持项目根与子目录，纯 Markdown 无元数据。
- 建议单条规则 < 500 行。

### 4.2 Skills（已核实）

| 作用域 | 路径 |
| --- | --- |
| Project | `.agents/skills/`、`.cursor/skills/` |
| User | `~/.agents/skills/`、`~/.cursor/skills/` |
| 兼容加载 | `.claude/skills/`、`.codex/skills/`、`~/.claude/skills/`、`~/.codex/skills/` |

- 启动时自动递归发现 `SKILL.md`；嵌套 `.cursor/skills/` 会自动限定作用域到该子目录。
- frontmatter：`name`（必填，须与父目录名一致）、`description`（必填）；
  可选 `paths`、`disable-model-invocation`、`icon`、`color`、`metadata`。
- 可在 Agent 对话里输入 `/` 搜索技能名手动调用。
- `~/.cursor/skills/` 的用户级技能需开启 "Sync Skills for Cloud Agents" 才用于 Cloud Agents；
  自动化运行不加载用户级技能。

### 4.3 本仓库的适配方案

- `adapters/cursor/rules/ai-engineering-standards.mdc` →
  `<target>/.cursor/rules/ai-engineering-standards.mdc`，使用
  `alwaysApply: true` + `description`，内容为红线规则与规范索引。
- Skills → `<target>/.cursor/skills/<skill-name>/`。
- **不使用 `.md` 作为 Project Rule 扩展名**（官方明确忽略）。
- 不使用 User Rules（无磁盘路径）与 Team Rules（需 dashboard，属组织级运维）。

---

## 5. GitHub Copilot

官方资料 **[A]**：

- <https://docs.github.com/en/copilot/reference/custom-instructions-support>
- <https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions>
- <https://docs.github.com/en/copilot/concepts/customizations/agent-skills>
- 官方中文 **[A]** <https://docs.github.com/zh/enterprise-cloud@latest/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills>

### 5.1 自定义指令（已核实）

| 类型 | 路径 | 格式 |
| --- | --- | --- |
| 仓库级 | `.github/copilot-instructions.md` | 纯 Markdown，作用于仓库上下文中的所有请求 |
| 路径级 | `.github/instructions/**/*.instructions.md` | 文件名必须以 `.instructions.md` 结尾；**必须**有含 `applyTo` 的 frontmatter（glob，逗号分隔多模式）；可选 `excludeAgent: "code-review" \| "cloud-agent"` |
| Agent 指令 | `AGENTS.md`、`CLAUDE.md`、`GEMINI.md`、`REVIEW.md` | 纯 Markdown |
| 个人指令（CLI） | `~/.copilot/copilot-instructions.md`、`~/.copilot/instructions/**/*.instructions.md` | — |

- 指令优先级：Personal > Repository > Organization；相关指令会**同时**提供，应尽量避免互相冲突。
- 路径级指令与仓库级指令匹配时**两者都会生效**。
- **在 GitHub.com 上，路径级自定义指令目前仅由 Copilot cloud agent 与 Copilot code review 支持**；
  IDE 支持矩阵以官方 reference 为准（VS Code / JetBrains / Xcode / Eclipse 各自不同）。
- Copilot code review 从 **head branch** 读取指令、Agent 指令与 Skills，不是 base branch。

**官方支持矩阵摘录**（来源 [A] `custom-instructions-support`）：

| 环境 | 仓库级 | 路径级 | Agent 指令 |
| --- | --- | --- | --- |
| VS Code（Copilot Chat） | ✅ | ✅ | ✅ (`AGENTS.md`) |
| JetBrains IDEs（Copilot Chat） | ✅ | ✅ | — |
| Xcode（Copilot Chat） | ✅ | ✅ | — |
| Eclipse（Copilot Chat） | ✅ | — | — |
| Copilot CLI | ✅ | ✅ | ✅ |
| Copilot cloud agent | ✅ | ✅ | ✅ |
| Copilot code review（部分环境） | ✅ | 视环境 | ✅ |

### 5.2 Agent Skills（已核实）

| 作用域 | 路径 |
| --- | --- |
| Project | `.github/skills/`、`.claude/skills/`、`.agents/skills/` |
| Personal | `~/.copilot/skills/`、`~/.agents/skills/` |

- 技能目录小写、空格用连字符；文件必须叫 `SKILL.md`；
  frontmatter 必填 `name`（通常等于目录名）、`description`，可选 `license`。
- 可用 `gh skill` 从 GitHub 仓库发现并安装技能。
- 适用面：GitHub Copilot app、Copilot CLI、cloud agent、code review、
  VS Code / Visual Studio / JetBrains 的 agent mode；IDE 支持取决于版本。

### 5.3 本仓库的适配方案

- `adapters/copilot/copilot-instructions.md` → `<target>/.github/copilot-instructions.md`
  （**仅当不存在或由本仓库管理**）。
- `adapters/copilot/instructions.md` →
  `<target>/.github/instructions/ai-engineering-standards.instructions.md`
  （路径级，`applyTo: "**"`，**可叠加**；不设置 `excludeAgent`）。
- Skills → `<target>/.github/skills/<skill-name>/`。
- 不写 `~/.copilot/` 下的任何个人配置（用户资产），不写组织级指令。

### 5.4 差异与待验证

- ⚠️ **待验证**：路径级 `.instructions.md` 在**每一个** IDE 版本中的实际读取行为。
  官方 reference 给出支持矩阵，但同时注明 "IDE support depends on the version you use"。
  本仓库同时提供仓库级与路径级两份，以规避单一通道不生效的风险。
- ⚠️ **待验证**：`excludeAgent` 在 Copilot CLI / IDE 中是否被忽略。
  本仓库**不设置**该字段，避免依赖未确认行为。
- ℹ️ Copilot 的 Agent Skills 与自定义指令是**两套机制**，不可互相替代；
  本仓库两者都装，且职责分开（指令 = 常驻红线，Skills = 按需工作流）。

---

## 6. 能力差异总表（生成文件时据此裁剪）

| 能力 | Codex | Claude Code | Cursor | Copilot |
| --- | --- | --- | --- | --- |
| 常驻入口指令文件 | `AGENTS.md` | `CLAUDE.md` | `.cursor/rules/*.mdc` 或 `AGENTS.md` | `.github/copilot-instructions.md` |
| 可叠加、低冲突的规则通道 | 子目录 `AGENTS.md`（受限） | `.claude/rules/*.md` | `.cursor/rules/*.mdc`（唯一文件名） | `.github/instructions/*.instructions.md` |
| Agent Skills 项目级官方路径 | `.agents/skills/` | `.claude/skills/` | `.cursor/skills/` / `.agents/skills/` | `.github/skills/` / `.agents/skills/` |
| Skills 显式调用 | `/skills`、`$name` | `/name` | Agent 中 `/` 搜索 | 由 Agent 自动选择 |
| 常驻指令的 frontmatter | 无 | 无 | `description`/`globs`/`alwaysApply` | 路径级需 `applyTo` |
| 指令按路径生效 | 靠目录层级 | `paths` 字段 | `globs` 字段 | `applyTo` 字段 |
| 指令硬优先级 | 近目录覆盖远目录 | **拼接，无硬优先级** | Team > Project > User | Personal > Repository > Organization |
| 用户级（非项目）配置 | `~/.codex/AGENTS.md` | `~/.claude/CLAUDE.md` | Customize UI（无文件） | `~/.copilot/` |
| 自定义 Agent（Phase 4 补） | `config.toml [agents]`（字段待验证） | `.claude/agents/*.md` | `.cursor/agents/*.md` | `.github/agents/*.md`（部分 IDE 预览） |
| Hooks（Phase 4 补） | `~/.codex/hooks.json` / `config.toml [hooks]` | `settings.json` | `.cursor/hooks.json` | `.github/hooks/*.json`（多数 IDE 不支持） |
| MCP 集成（Phase 4 补） | `config.toml mcp_servers` | 支持（配置路径待验证） | 支持（配置路径待验证） | `mcp.json` / `mcp-servers` |

> 上表为 Phase 1 安装目标格式快照。能力状态（`SUPPORTED`/`PARTIAL`/`UNVERIFIED`）、
> 五种适配方式与逐能力官方依据，以 [能力对照表](architecture/tool-compatibility.md) 为准。

**结论**：四种工具在"常驻指令"和"Skills 发现路径"上**没有共同交集**，
因此必须由 `install.py` 按 `targets.py` 分别复制；而 Skills 的**内容**
可以完全统一，因为都遵循 Agent Skills 开放规范。这正是"单源 + 多适配器"的价值所在。

---

## 7. 明确不做的事

- 不把 `AGENTS.md` 说成所有工具都读（Claude Code 默认读 `CLAUDE.md`，可通过设置切换）。
- 不把 `.mdc` / `applyTo` / `paths` / `alwaysApply` 等字段写进 `skills/` 或 `core/`。
- 不写 `agents/openai.yaml`、`.codex/config.toml`、`.claude/settings.json`、
  `.cursor/cli-config.json` 等工具专有配置（它们属于用户资产且随版本变化）。
- 不声称 `skills-ref` 已被集成或测试结果与其等价。
- 不自动修改用户已有的任何入口文件，也不自动删除旧文件。
- **不生成任何 Hooks 自动化**（Phase 4）：四工具虽都支持 Hooks，但配置格式互不相同、
  执行用户脚本且需 trusted。Phase 4 只记录能力边界；若未来启用，也只放"修改后格式化 /
  提交前测试 / 阻止敏感文件误操作"，不把整套工程规范转成 Hooks。
- **不生成任何自定义 Agent 配置文件**（Phase 4）：`agents/` 是角色契约（纯文本），
  各工具 agent 字段互不相同；Phase 4 只给映射模板，转换与安装属后续阶段。
  Codex `config.toml [agents]` 字段因官方页抓取被拒仍为 `UNVERIFIED`，不据第三方资料虚构。

---

## 8. 腾讯 WorkBuddy（Phase 6 新增）

### 8.1 核实来源

| # | 文档标题 | URL | 来源 | 查阅日期 |
| --- | --- | --- | --- | --- |
| 1 | .codebuddy 目录结构说明 | `https://www.workbuddy.cn/docs/cli/codebuddy-dir` | [A] | 2026-11-11 |
| 2 | 管理 CodeBuddy 的记忆 | `https://www.workbuddy.cn/docs/cli/memory` | [A] | 2026-11-11 |
| 3 | Skills 文档 | `https://www.workbuddy.cn/docs/cli/skills` | [A] | 2026-11-11 |
| 4 | 子代理 | `https://www.workbuddy.cn/docs/cli/sub-agents` | [A] | 2026-11-11 |
| 5 | 斜杠命令 | `https://www.workbuddy.cn/docs/cli/slash-commands` | [A] | 2026-11-11 |

完整逐能力依据与关键原文见 [`../adapters/workbuddy/references.md`](../adapters/workbuddy/references.md)。

### 8.2 安装目标格式（项目级，已核实）

| 内容 | 官方项目级路径 | 格式要点 | 本仓库适配 |
| --- | --- | --- | --- |
| 记忆入口 | `./CODEBUDDY.md` 或 `./.codebuddy/CODEBUDDY.md` | 两处等效；与 `AGENTS.md` 兼容且 `CODEBUDDY.md` 优先；`@path` 导入 ≤5 层 | 装项目根 `CODEBUDDY.md`（guarded） |
| 项目级规则 | `.codebuddy/rules/*.md` | 全部递归自动加载；`enabled`/`alwaysApply`/`paths` 三字段；仅当前工作目录加载 | 装 `.codebuddy/rules/ai-engineering-standards.md`（additive，无 frontmatter 默认常驻） |
| Skills | `.codebuddy/skills/<name>/SKILL.md` | `name`/`description` 必填；项目级优先 | 5 个公共 Skill 逐字节复制 |
| Agents | `.codebuddy/agents/*.md` | `name`/`description` 必填 + `tools`/`model` 可选；正文 = system prompt | 只给映射模板，**不生成** |
| Commands | `.codebuddy/commands/*.md` | `description`/`argument-hint`/`allowed-tools`；`$ARGUMENTS` | 5 个 Skill 已覆盖，**不生成** |
| 用户级全局规则 | `~/.codebuddy/rules/` | 官方存在，对所有项目生效 | **不写**（任务书禁止） |

### 8.3 差异、边界与待验证

1. **唯一 project-only 工具**：任务书明确"不创建用户级全局规则""不写入用户级目录"，故
   `GLOBAL_TOOL_SPECS["workbuddy"]` 设 `entry=None` + `project_only=True`，`--scope global`
   完全跳过，不写 `~/.codebuddy/`。这是通过通用标志 + 安装器/校验器守卫实现，非硬编码工具名。
2. **规则类型三态**：`alwaysApply` 默认 `true` → 常驻；`false` + `paths` → 条件触发；
   `false` 且无 `paths` → 不加载。本仓库叠加规则不带 frontmatter，取默认常驻；不带 `paths`
   避免被降级为条件规则。若未来加技术栈级规则，另建带 `paths` 的独立文件。
3. **项目规则仅当前工作目录生效**：不加载父目录规则，故需以项目根为工作目录。
4. **目录名待验证**：官方 CLI 文档只写 `.codebuddy/`，桌面端运行时环境可见 `.workbuddy/`
   （环境事实，非官方格式文档）；腾讯云社区文章称桌面端与 CodeBuddy Code 一致 [B/社区]。
   按任务书与官方 CLI 落地 `.codebuddy/`，真实桌面端读取目录须实测。
5. **运行时未验证**：本机未安装真实 WorkBuddy 客户端，静态 + 模拟验证不能替代运行时验证。
   "规则自动生效""非开发任务不受全局规则影响""Skills/Agents 被发现"须人工用 `/memory`、
   Skills 列表与 probe prompt 核对，当前一律标 `UNVERIFIED` / 未验证。
6. **Agents / Commands 不生成**：按任务书决策（与 Phase 4 一致，避免双源与重复实现），
   只提供 `adapters/workbuddy/templates/` 下的映射模板。

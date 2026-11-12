# Claude Code 适配器

> 让 Anthropic Claude Code 读取同一套公共规范与 Skills。
> 能力状态见 [`../../docs/architecture/tool-compatibility.md`](../../docs/architecture/tool-compatibility.md)；官方依据见 [`references.md`](references.md)；逐项映射见 [`mappings.md`](mappings.md)。

---

## 1. 用途与范围

把公共规范 `core/`、`standards/`、`skills/`、`agents/` 适配到 Claude Code 的三类机制：**`CLAUDE.md` 指令入口**、**`.claude/rules/` 叠加规则**、**Agent Skills 与 Subagents**。

- 支持的工具：Claude Code（终端 / IDE 扩展 / Desktop / cloud sessions，能力因环境而异，见 §8）。
- 参考的官方文档日期：**2026-11-11**。
- 公共规范版本：`1.0.0`（本阶段未改动）。

## 2. 官方文档

| 主题 | 文档标题 | URL | 来源 |
| --- | --- | --- | --- |
| Skills | Extend Claude with skills | `https://code.claude.com/docs/en/skills` | [A] |
| 记忆 / 规则 | How Claude remembers your project | `https://code.claude.com/docs/en/memory` | [A] |
| Subagents | Create custom subagents | `https://code.claude.com/docs/en/sub-agents` | [A] |
| Hooks | Hooks reference | `https://code.claude.com/docs/en/hooks` | [A] |

## 3. 安装方式（仅说明，本阶段不实现）

| 源（本仓库） | 目标（项目根，POSIX） | 类别 | 说明 |
| --- | --- | --- | --- |
| `adapters/claude-code/CLAUDE.md` | `CLAUDE.md` | guarded | 用户已占用则跳过 |
| `adapters/claude-code/rules/ai-engineering-standards.md` | `.claude/rules/ai-engineering-standards.md` | additive | 唯一文件名，与用户规则并存，永不覆盖 |
| `skills/<name>/` | `.claude/skills/<name>/` | 复制 | 官方项目级路径，内容逐字节一致 |
| 公共规范镜像 | `.ai-standards/` | 只读镜像 | 入口索引里的路径安装后仍成立 |

> **双通道设计**：入口 `CLAUDE.md` 最容易被用户占用，因此额外提供一份可叠加的 `.claude/rules/*.md`（无 frontmatter，启动时加载，优先级同 `.claude/CLAUDE.md`），保证"不覆盖用户配置"与"规范仍生效"同时成立。

## 4. 规则加载方式

- **层级**：managed policy → `~/.claude/CLAUDE.md` → `./CLAUDE.md` 或 `./.claude/CLAUDE.md` → `./CLAUDE.local.md`（由宽到窄）。
- **加载**：启动时加载当前目录及所有父目录的 CLAUDE.md；**全部拼接而非覆盖**，根到工作目录排序，越近越靠后。
- ⚠️ **无硬优先级**：官方明确"所有文件被拼接；冲突时 Claude 可能任选其一"。因此本仓库规范与项目自有规则**只写互不冲突的通用红线**，冲突裁决由 [`core/README.md`](../../core/README.md) 统一定义，而非依赖文件顺序。
- **子目录**：子目录中的 CLAUDE.md / `.claude/rules/` 在被读写该子目录文件时**按需加载**；路径级规则用 `.claude/rules/*.md` 的 `paths` frontmatter（唯一被读取的字段）。
- **`@path` import**：`CLAUDE.md` 可用 `@path/to/file` 导入（最多 4 跳），但官方明确 **import 不减少上下文成本**，故本仓库**不用**它把整个规范库拉进常驻上下文；入口改用反引号路径 + 按需读取。

## 5. Skills 加载方式

- **发现路径**：Project `.claude/skills/<name>/SKILL.md`；Personal `~/.claude/skills/`；Nested `<subdir>/.claude/skills/`；Plugin `<plugin>/skills/`。本仓库装项目级。
- **复用方式**：5 个公共 `SKILL.md` 逐字节复制，`scripts/` `references/` `assets/` 一并复制，一级引用。
- **Frontmatter**：只用开放规范 6 字段。⚠️ 官方明确：claude.ai 上传 / Skills API / `package_skill.py` 打包时，**出现 6 字段以外的键会硬报错**（`Unexpected key(s) in SKILL.md frontmatter`）。因此不写 `when_to_use`/`paths`/`hooks` 等扩展字段。
- **调用**：`/skill-name` 显式，或按 `description` 隐式；`description`+`when_to_use` 合并文本在列表中于 **1,536 字符**截断，故触发词前置。
- **行数**：`SKILL.md` 官方建议 < 500 行，本仓库公共源已满足。

## 6. Agent（Subagents）支持情况

官方支持 `.claude/agents/*.md`（项目）/ `~/.claude/agents/`（用户），Markdown + YAML frontmatter，**独立上下文窗口** [A]。字段官方确认，可给出映射模板（见 [`templates/`](templates/)）。

| 公共角色 | 目标文件 | 必填字段 | 可选字段（官方） |
| --- | --- | --- | --- |
| `architect.md` | `.claude/agents/architect.md` | `name`、`description` | `tools`、`model`、`permissionMode`、`skills`、`mcpServers` 等 |
| `developer.md` | `.claude/agents/developer.md` | 同上 | 同上 |
| `reviewer.md` | `.claude/agents/reviewer.md` | 同上 | 同上 |
| `tester.md` | `.claude/agents/tester.md` | 同上 | 同上 |

- **正文 = system prompt**（文件式 subagent 的 Markdown 正文即系统提示，不是名为 `prompt` 的字段；`prompt` 只在 CLI `--agents` JSON 中出现）。
- **工具字段由目标项目决定**：本仓库公共 `agents/` 不含 `tools`/`model`，避免绑定某工具能力。
- 本阶段**只提供映射模板**，不生成可安装的 agent 文件（安装属 Phase 5）。

## 7. Hooks 能力边界

官方支持且能力强（`PreToolUse` 可用 exit 2 阻断，`PostToolUse` 等反馈；配置在 `settings.json` 三层 + managed + plugin + skill/subagent frontmatter）[A]。但按用户要求，本阶段**只设计适配方案、不建立 Hooks 自动化、不创建 `settings.json`**。未来适合放"修改后格式检查""提交前测试""阻止敏感文件误操作"；硬安全策略官方建议用 permission 系统而非 Hook。

## 8. 已知限制

1. `CLAUDE.md` 是**上下文注入而非强制配置**，冲突时可能任选其一；规范优先级靠 `core/README.md` 定义，不靠文件顺序。
2. Cowork / cloud sessions 不读本机 `~/.claude/skills/`；项目 `.claude/skills/` 在 project cloud threads 中也不可用——这是工具侧限制，本仓库无法消除。
3. Cloud sessions 不读本地 `~/.claude/settings.json`（影响用户级 Hooks，不影响本仓库项目级适配）。
4. 指向工作区外的符号链接规则需首次批准，且只有无 `paths` 的规则会加载——进一步支持"不用符号链接"的决策。
5. 未在真实 Claude Code 客户端运行时验证。

## 9. 相关文档

- 映射明细：[`mappings.md`](mappings.md) · 官方参考：[`references.md`](references.md) · 模板：[`templates/`](templates/)
- 统一映射架构：[`../README.md`](../README.md) · 公共角色契约：[`../../agents/`](../../agents/)

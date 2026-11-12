# 腾讯 WorkBuddy 适配器

> 让腾讯 WorkBuddy（CodeBuddy Code 引擎）读取同一套公共规范与 Skills，且只作为**项目级代码开发配置**安装。
> 能力状态见 [`../../docs/architecture/tool-compatibility.md`](../../docs/architecture/tool-compatibility.md)；官方依据见 [`references.md`](references.md)；逐项映射见 [`mappings.md`](mappings.md)。

---

## 1. 用途与范围

把公共规范 `core/`、`standards/`、`skills/`、`agents/` 适配到 WorkBuddy 的项目级代码开发机制：**`CODEBUDDY.md` 记忆入口**、**`.codebuddy/rules/` 叠加规则**、**Agent Skills**。

- 支持的工具：腾讯 WorkBuddy 桌面端 / CodeBuddy Code CLI（配置目录 `.codebuddy/`）。
- 参考的官方文档日期：**2026-11-11**。
- 公共规范版本：`1.0.0`（本阶段未改动）。
- **仅 project 作用域**：本适配器是 project-only 工具，不安装任何用户级（`~/.codebuddy/`）文件。任务书明确要求"不创建用户级全局规则""不写入用户级目录"，因此本适配器**没有** `global/ENTRY.md`；在 `GLOBAL_TOOL_SPECS` 中标记为 `project_only`，`--scope global` 时跳过。

## 2. 官方文档

| 主题 | 文档标题 | URL | 来源 |
| --- | --- | --- | --- |
| 目录结构 | .codebuddy 目录结构说明 | `https://www.workbuddy.cn/docs/cli/codebuddy-dir` | [A] |
| 记忆 / 规则 | 管理 CodeBuddy 的记忆 | `https://www.workbuddy.cn/docs/cli/memory` | [A] |
| Skills | Skills 文档 | `https://www.workbuddy.cn/docs/cli/skills` | [A] |
| Agents | 子代理 | `https://www.workbuddy.cn/docs/cli/sub-agents` | [A] |
| Commands | 斜杠命令 | `https://www.workbuddy.cn/docs/cli/slash-commands` | [A] |

> 来源等级定义见 [`../../docs/architecture/tool-compatibility.md` §0.3](../../docs/architecture/tool-compatibility.md)。全部为 workbuddy.cn 官方文档正文本次直接抓取（[A]）。

## 3. 安装方式

| 源（本仓库） | 目标（项目根，POSIX） | 类别 | 说明 |
| --- | --- | --- | --- |
| `adapters/workbuddy/CODEBUDDY.md` | `CODEBUDDY.md` | guarded | 用户已占用则跳过，永不覆盖 |
| `adapters/workbuddy/rules/ai-engineering-standards.md` | `.codebuddy/rules/ai-engineering-standards.md` | additive | 唯一文件名，与用户规则并存，永不覆盖 |
| `skills/<name>/` | `.codebuddy/skills/<name>/` | 复制 | 官方项目级路径，内容逐字节一致 |
| 公共规范镜像 | `.ai-standards/` | 只读镜像 | 入口索引里的路径安装后仍成立 |

安装命令：

```bash
python tooling/scripts/install.py --tool workbuddy --scope project --target ../my-project
```

> **双通道设计**：入口 `CODEBUDDY.md` 最容易被用户占用，因此额外提供一份可叠加的 `.codebuddy/rules/ai-engineering-standards.md`（无 frontmatter，启动时加载），保证"不覆盖用户配置"与"规范仍生效"同时成立。这与 Claude Code 适配器的双通道思路一致。

## 4. 规则加载方式

- **记忆入口**：`./CODEBUDDY.md` 与 `./.codebuddy/CODEBUDDY.md` 两处等效；系统从工作目录向上递归查找主文件，并与 `AGENTS.md` 兼容——**存在 `CODEBUDDY.md` 时优先用它**。
- **项目级规则**：`.codebuddy/rules/*.md` 全部自动递归加载，优先级与 `.codebuddy/CODEBUDDY.md` 相同；**仅加载当前工作目录的规则目录，不加载父目录规则**（作用域清晰）。
- **规则类型**：由 `alwaysApply` 与 `paths` 共同决定。默认 `alwaysApply: true` → ALWAYS 常驻注入；`alwaysApply: false` + `paths` → MANUAL 条件触发；`alwaysApply: false` 且无 `paths` → 不加载。
- **本仓库选择**：叠加规则**不带 frontmatter**，即取默认 `alwaysApply: true` 常驻加载。刻意不带 `paths`，避免"通用红线"被降级为"仅匹配文件时触发"。若未来要加技术栈级规则，应另建带 `paths` 的独立文件。
- **用户级规则**：`~/.codebuddy/rules/` 对所有项目生效——本适配器**不写入**该目录。
- **`@path` 导入**：`CODEBUDDY.md` 支持导入其他文件，最多 **5 层**。但入口改用反引号路径 + 按需读取，不用导入把整个规范库拉进常驻上下文。
- **`/memory`**：可查看已加载的记忆与规则列表，是运行时核对入口。

## 5. Skills 加载方式

- **发现路径**：项目 `.codebuddy/skills/<name>/SKILL.md`；用户 `~/.codebuddy/skills/`；同名时项目级优先。本仓库装项目级。
- **复用方式**：5 个公共 `SKILL.md` 逐字节复制，`scripts/` `references/` `assets/` 一并复制。
- **Frontmatter**：`name`/`description` 必填，开放规范字段（`license` / `metadata` / `allowed-tools` 等）原样保留。⚠️ 本仓库公共 Skill 只使用开放规范白名单字段，不写工具专有字段，以保持跨工具可移植（见 [`mappings.md`](mappings.md) §3）。
- **调用**：`/<skill-name>` 显式，或按 `description` 隐式匹配；技能正文只在被选中时加载。
- **行数**：`SKILL.md` 建议 < 500 行，本仓库公共源已满足。

## 6. Agent 支持情况（只给模板，不生成）

官方支持 `.codebuddy/agents/*.md`（项目）/ `~/.codebuddy/agents/`（用户），Markdown + YAML frontmatter，`name`/`description` 为必填，`tools`/`model` 可选；项目级优先于用户级。字段官方确认，可给出映射模板（见 [`templates/`](templates/)）。

| 公共角色 | 目标文件（若启用） | 必填字段 | 可选字段 |
| --- | --- | --- | --- |
| `architect.md` | `.codebuddy/agents/architect.md` | `name`、`description` | `tools`、`model` |
| `developer.md` | `.codebuddy/agents/developer.md` | 同上 | 同上 |
| `reviewer.md` | `.codebuddy/agents/reviewer.md` | 同上 | 同上 |
| `tester.md` | `.codebuddy/agents/tester.md` | 同上 | 同上 |

- **正文 = system prompt**；工具专有的 `tools`/`model` 字段由目标项目按需填入，不写入公共源。
- **本阶段决策**：与其余四工具一致，**只提供映射模板，不生成可安装的 agent 文件**（见 [`templates/agent-mapping.template.md`](templates/agent-mapping.template.md)）。因此"Agents 能被 WorkBuddy 发现"属于**未生成 / 需人工启用后验证**，不宣称通过。

## 7. Commands 与项目指令边界

- **Commands**：官方支持 `.codebuddy/commands/*.md`，通过 `/<name>` 触发。但公共仓库无独立 Commands 定义，且 5 个 Skill 已覆盖全部工作流（`/<skill-name>` 直接触发），**不重复生成** Commands，避免与 Skill 双源。
- **项目指令 ≠ 项目级代码规则**：`CODEBUDDY.md` 是项目记忆/上下文入口；`.codebuddy/rules/` 是代码开发规则。本适配器只落地这两类项目级文件，**不创建任何用户级全局规则或全局入口**。
- **不生成全局规则**：`~/.codebuddy/rules/`、`~/.codebuddy/CODEBUDDY.md` 属于用户级全局配置，任务书明令禁止，本适配器在 `GLOBAL_TOOL_SPECS` 中以 `project_only=True` + `entry=None` 保证 `--scope global` 完全跳过。

## 8. 已知限制

1. `CODEBUDDY.md` / `.codebuddy/rules/` 是**上下文注入而非强制配置**；冲突裁决由 [`../../core/README.md`](../../core/README.md) 统一定义，不依赖文件顺序。
2. **目录名待验证**：官方 CLI 文档只写 `.codebuddy/`；桌面端运行时环境可见 `~/.workbuddy/` 与 `<workspace>/.workbuddy/`（环境事实，非官方格式文档）。桌面端项目级实际读取目录需真实客户端实测；本适配器按任务书指定与官方 CLI 文档落地 `.codebuddy/`。
3. **运行时未验证**：未在真实 WorkBuddy 客户端验证规则自动生效、Skills/Agents 发现；当前环境未安装该客户端，静态 + 模拟验证不能替代运行时验证。
4. **项目级规则不加载父目录**：若从项目子目录启动 WorkBuddy，需确保工作目录为项目根，否则 `.codebuddy/rules/` 可能不被加载。
5. **Agents / Commands 未生成**：按 §6/§7 决策，仅提供模板或不生成，相关发现能力标为未验证。

## 9. 相关文档

- 映射明细：[`mappings.md`](mappings.md) · 官方参考：[`references.md`](references.md) · 模板：[`templates/`](templates/)
- 统一映射架构：[`../README.md`](../README.md) · 能力矩阵：[`../../docs/architecture/tool-compatibility.md`](../../docs/architecture/tool-compatibility.md)
- 公共角色契约：[`../../agents/`](../../agents/) · 公共 Skills：[`../../skills/`](../../skills/)

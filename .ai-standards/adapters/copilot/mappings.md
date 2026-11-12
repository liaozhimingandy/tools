# GitHub Copilot 映射关系

> 逐项说明公共规范源如何映射到 Copilot 的原生文件。
> 状态与适配方式口径见 [`../../docs/architecture/tool-compatibility.md`](../../docs/architecture/tool-compatibility.md)；官方依据见 [`references.md`](references.md)。

---

## 1. 映射总表

| 公共来源 | Copilot 原生文件 / 目录 | 对应关系 | 需转换 | 可直接复用 | 已知限制 | 官方依据 |
| --- | --- | --- | --- | --- | --- | --- |
| `core/`（原则） | 仓库级 + 路径级指令 + `.ai-standards/core/` | 红线入两份指令，其余按需读镜像 | 是（裁剪 + `applyTo` + 索引） | 否 | surface 依赖；Personal > Repository 优先级 | `custom-instructions-support` [A] |
| `standards/`（技术） | 指令按需索引 + `.ai-standards/standards/` | 只给索引，不机械拆分 | 否 | 是（镜像） | 技术栈级可用路径指令另建 | `custom-instructions-support` [A] |
| `skills/`（5 个） | `.github/skills/<name>/` | 1:1 复制目录 | **否** | **是（逐字节）** | IDE 版本差异（VS Code ≥1.108.0） | `agent-skills` [A] |
| `agents/`（4 角色） | `.github/agents/*.md`（agent profile） | 正文 → prompt，提取 `description` | 是（字段官方确认） | 正文可复用 | JetBrains/Eclipse/Xcode 预览；工具字段目标项目定 | `about-custom-agents` [A] |
| Hooks | 不生成 | 仅记录能力边界 | — | — | `.github/hooks/*.json`，多数 IDE 不支持 | `hooks` [A] |

---

## 2. 双指令通道映射

| 通道 | 源文件 | 目标 | frontmatter | 覆盖面 | 覆盖策略 |
| --- | --- | --- | --- | --- | --- |
| 仓库级 | `adapters/copilot/copilot-instructions.md` | `.github/copilot-instructions.md` | 无（纯 Markdown） | 最广：所有 surface | guarded（用户占用则跳过） |
| 路径级 | `adapters/copilot/instructions.md` | `.github/instructions/ai-engineering-standards.instructions.md` | `applyTo: "**"` | 仅部分 surface（GitHub.com 限 cloud/code review） | additive（唯一文件名，永不覆盖） |

**为何两份都要** [A]：官方支持矩阵显示——

| 环境 | 仓库级 | 路径级 | 说明 |
| --- | --- | --- | --- |
| Copilot Chat（GitHub.com） | ✓ | Personal + Repository + Organization | — |
| Copilot cloud agent | ✓ | ✓ | + Agent 指令 |
| Copilot code review | ✓ | 视环境 | Eclipse 的 code review 不支持自定义指令 |
| VS Code / JetBrains | ✓ | ✓ | IDE 支持随版本 |
| Eclipse / Xcode | ✓ | Eclipse ✗ 部分 / Xcode ✓ | 见 `references.md` §3 |

单一通道可能在某些 surface 不生效，故仓库级（保底）+ 路径级（叠加）并存。

**`applyTo` 决策**：用 `"**"` 表示该路径级指令对所有文件生效；**不设置** `excludeAgent`（其跨 CLI/IDE 行为 `UNVERIFIED`）。

## 3. Skills 映射（直接复用）

| 公共 Skill 源 | 目标（POSIX） | 转换 | Frontmatter 处理 |
| --- | --- | --- | --- |
| `skills/project-analysis/` | `.github/skills/project-analysis/` | 无（整目录复制） | 保持 6 标准字段 |
| `skills/requirements-analysis/` | `.github/skills/requirements-analysis/` | 无 | 同上 |
| `skills/architecture-design/` | `.github/skills/architecture-design/` | 无 | 同上 |
| `skills/software-development/` | `.github/skills/software-development/` | 无 | 同上 |
| `skills/code-review/` | `.github/skills/code-review/` | 无 | 同上 |

- 选 `.github/skills/`（Copilot 原生项目路径），与 `.claude/skills/`、`.agents/skills/` 副本并存不冲突——Copilot 官方把三者都列为项目级发现路径 [A]。
- 只用开放规范字段（`name`/`description`，可选 `license`），逐字节复用。
- **引用路径**：`SKILL.md` 内相对一级引用，与 Copilot Skills 规范一致；不引用 `.ai-standards/`（避免独立打包失效）。
- **分支注意**：code review 从 head branch 读取 Skills [A]，故 Skills 须在被审查分支上。

## 4. Agent 角色映射（正文复用 + 官方字段）

Copilot 用 **agent profile**（`.github/agents/NAME.md`）：

| 公共角色 | 目标文件 | `description` | `name` | 正文 | 工具字段 |
| --- | --- | --- | --- | --- | --- |
| `architect.md` | `.github/agents/architect.md` | 取自"定位"段（必填） | 可选 | → prompt，逐字保留 | 目标项目自定 |
| `developer.md` | `.github/agents/developer.md` | 同上 | 可选 | 同上 | 同上 |
| `reviewer.md` | `.github/agents/reviewer.md` | 同上 | 可选 | 同上 | 同上 |
| `tester.md` | `.github/agents/tester.md` | 同上 | 可选 | 同上 | 同上 |

**转换规则**：

1. **正文 = prompt**（Markdown frontmatter 之后的内容），逐字复制角色契约，≤30,000 字符（官方上限）。
2. `description` **必填**，`name` 可选（缺省取文件名，去掉 `.md` / `.agent.md` 后缀）。
3. `tools`（工具名/别名列表）、`mcp-servers`、`model`、`target` 是工具专有字段，**不写入公共源**；省略 `tools` 时 agent 可用全部工具。
4. 角色契约与工具配置分离，避免 Copilot 专有字段污染 `agents/`。
5. 本阶段只提供映射模板，不生成安装产物。

## 5. 引用处理与更新同步

- **引用方式**：方案 ②（仓库级保底入口）+ 方案 ③（路径级叠加 + 需手动引用镜像）+ 方案 ④（镜像），见 [`../README.md` §4](../README.md)。无官方内联 import，故用反引号写 `.ai-standards/` 路径。
- **路径级规则扩展位**：把 `standards/` 映射为路径指令时，另建 `.github/instructions/python.instructions.md` 配 `applyTo: "**/*.py"`，正文只放索引；本阶段不机械拆分。
- **更新同步**：按清单重算哈希；仓库级 guarded、路径级 additive 分别处理，用户自有文件不覆盖。
- **不产生双源**：两份指令都只放红线与索引，完整正文唯一在镜像。

## 6. 相关文档

- 官方参考：[`references.md`](references.md) · 适配说明：[`README.md`](README.md) · 模板：[`templates/`](templates/) · 公共角色：[`../../agents/`](../../agents/)

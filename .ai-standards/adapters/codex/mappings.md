# Codex 映射关系

> 逐项说明公共规范源如何映射到 Codex 的原生文件。
> 状态与适配方式口径见 [`../../docs/architecture/tool-compatibility.md`](../../docs/architecture/tool-compatibility.md)；官方依据见 [`references.md`](references.md)。

---

## 1. 映射总表

| 公共来源 | Codex 原生文件 / 目录 | 对应关系 | 需转换 | 可直接复用 | 已知限制 | 官方依据 |
| --- | --- | --- | --- | --- | --- | --- |
| `core/`（原则） | `AGENTS.md` 入口 + `.ai-standards/core/` 镜像 | 红线入常驻入口，其余按需读镜像 | 是（裁剪 + 索引） | 否 | 入口常驻成本，正文不内联 | `agents-md` [B] |
| `standards/`（技术） | 入口按需索引 + `.ai-standards/standards/` | 只给索引，不机械拆分 | 否 | 是（镜像） | 无官方"路径级指令"机制 | `agents-md` [B] |
| `skills/`（5 个） | `.agents/skills/<name>/` | 1:1 复制目录 | **否** | **是（逐字节）** | 初始列表预算约 2% 上下文 | `skills` [B] |
| `agents/`（4 角色） | `config.toml [agents]`（机制存在） | 角色职责 → subagent 正文 | 是（字段待定） | 正文可复用 | **字段 `UNVERIFIED`**，不生成配置 | `config-advanced` [A] |
| Hooks | 不生成 | 仅记录能力边界 | — | — | 项目级需 trusted | `hooks` [B] |

---

## 2. Skills 映射（直接复用）

| 公共 Skill 源 | 目标（POSIX） | 转换 | Frontmatter |
| --- | --- | --- | --- |
| `skills/project-analysis/` | `.agents/skills/project-analysis/` | 无（整目录复制） | 保持 6 标准字段 |
| `skills/requirements-analysis/` | `.agents/skills/requirements-analysis/` | 无 | 同上 |
| `skills/architecture-design/` | `.agents/skills/architecture-design/` | 无 | 同上 |
| `skills/software-development/` | `.agents/skills/software-development/` | 无 | 同上 |
| `skills/code-review/` | `.agents/skills/code-review/` | 无 | 同上 |

- **不写入** `agents/openai.yaml`（Codex 应用专用 UI 元数据 / 调用策略 / 工具依赖）——它是工具专有配置，写进公共源会破坏工具无关性。
- **不支持**把 Skills 放进 `.ai-standards/skills/` 并期望被发现：Codex 只扫描 `.agents/skills` 等官方目录，镜像中的 `skills/` 仅作引用副本。

## 3. 核心规范映射（入口 + 镜像）

`AGENTS.md` 是**薄入口**，与公共规范的关系是"索引 → 镜像文件"，而非复制正文：

| 入口段落 | 指向镜像 | 触发场景 |
| --- | --- | --- |
| 必须遵守的红线 | `.ai-standards/core/ai-behavior.md`、`.ai-standards/core/security-principles.md` | 常驻（精简版在入口） |
| 按需加载索引 | `.ai-standards/core/engineering-principles.md` 等 7 份 | 通用设计 / 编码 / 测试 / 架构 / 安全 / 文档 |
| 技术规范 | `.ai-standards/standards/{languages,backend,frontend,devops}/` | 按技术栈选读 |
| Skills 路由 | `.agents/skills/` | 接手项目 / 需求 / 架构 / 实施 / 审查 |

> 入口里所有镜像路径用反引号而非 Markdown 链接：Codex 无官方内联 import，链接在目标项目里无法解析；写明路径让 Codex 用自身工具读取，才是官方支持的方式。

## 4. Agent 角色映射（说明，不生成配置）

公共 `agents/` 是**角色契约**（纯文本、工具无关），Codex 侧映射关系如下：

| 公共角色 | 职责（来自角色契约） | Codex 目标 | 本阶段处置 |
| --- | --- | --- | --- |
| `architect.md` | 改在哪里、边界怎么划、方案为何这样选 | `config.toml [agents]` 的 system 正文 | 仅说明 |
| `developer.md` | 按设计实施最小修改 | 同上 | 仅说明 |
| `reviewer.md` | 提交前 / PR 审查 | 同上 | 仅说明 |
| `tester.md` | 测试策略与执行 | 同上 | 仅说明 |

**转换规则（待字段确认后适用）**：

1. 角色 `.md` 的正文 → subagent 的 instructions / system prompt（**唯一权威正文**，不改写职责）。
2. `name` / `description` 从角色标题与定位提取，但**必须先确认 Codex 官方字段名**，不得套用 Claude/Cursor 的写法。
3. `tools` / `model` 等工具专有字段**不进公共源**；是否设置由目标项目决定。
4. 因 `config.toml [agents]` 字段当前 `UNVERIFIED`，本阶段**不提供可复制的 agent 配置模板**，以免虚构字段。

## 5. 引用处理与更新同步

- **引用方式**：方案 ②（薄入口）+ 方案 ③（需手动引用镜像路径）+ 方案 ④（安装期复制完整镜像），见 [`../README.md` §4](../README.md)。不依赖符号链接（[`../README.md` §5](../README.md)）。
- **更新同步**：公共 `core/standards/skills/agents/` 变更后，安装器按清单重算哈希；`AGENTS.md`（guarded）若由本仓库管理则更新，若被用户占用则只报 WARNING，由用户按 `templates/` 片段手工合并。
- **不产生双源**：入口不复制规范正文，镜像是唯一"完整正文"副本，由清单校验。

## 6. 相关文档

- 官方参考：[`references.md`](references.md) · 适配说明：[`README.md`](README.md) · 模板：[`templates/`](templates/)

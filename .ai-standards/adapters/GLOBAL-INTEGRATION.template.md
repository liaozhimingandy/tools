<!-- AI-ENGINEERING-STANDARDS:MANAGED version=GENERATED tool=global source=adapters/GLOBAL-INTEGRATION.template.md -->
<!-- 本文件由 ai-engineering-standards 安装器在 global 作用域安装时生成，请勿手工编辑。 -->

# 用户级（global）规范集成说明

本文件记录把通用工程规范安装到**用户主目录（home）**后的加载方式与已知边界。
规范本体（唯一权威）安装在 `~/.ai-engineering-standards/bundle/`，对其余工具共享一份；
通用 Skills 则按各工具官方约定安装到各自的用户级目录。**腾讯 WorkBuddy 是 project-only
工具，不参与 global 作用域**，不写 `~/.codebuddy/`，详见 §1 表格与 §5。

> 阅读前提：global 作用域让规范对**该用户的所有项目**生效，适合作为默认底线；
> 但它不能替代项目级适配。项目仍可叠加自己的规则，且项目级与用户级冲突时，
> 具体以工具自身的优先级机制为准（见 `~/.ai-engineering-standards/bundle/docs/architecture/tool-compatibility.md`）。

---

## 1. 安装内容

| 工具 | 全局规则入口 | 能力等级 | 用户级 Skills 目录 |
| --- | --- | --- | --- |
| Codex | `~/.codex/AGENTS.md` | SUPPORTED | `~/.agents/skills/` |
| Claude Code | `~/.claude/CLAUDE.md` | SUPPORTED | `~/.claude/skills/` |
| Cursor | **不生成**（无磁盘路径） | PARTIAL | `~/.cursor/skills/` |
| Copilot | `~/.copilot/copilot-instructions.md`（仅 CLI） | PARTIAL | `~/.copilot/skills/` |
| 腾讯 WorkBuddy | **不生成**（project-only，任务书禁写用户级目录） | PARTIAL | **不生成**（`--scope global` 完全跳过） |

规范镜像：`~/.ai-engineering-standards/bundle/`（含 `core/`、`standards/`、`skills/`、
`agents/`、`adapters/`、`docs/`）。所有入口文件里的 `~/.ai-engineering-standards/bundle/`
路径需由 AI 工具自行展开 `~` 后读取（各工具不提供 Markdown 内联 import，见下文边界）。

---

## 2. Cursor 为什么没有全局入口

官方明确：Cursor 的 User Rules 只能在 **Customize UI** 里配置，**磁盘上没有可供写入的用户级规则路径**
（`docs/architecture/tool-compatibility.md` §2.3）。安装器**不会编造**一个不存在的文件来假装支持。
如需让 Cursor 全局遵守本规范，请在 Customize UI 中手工加入对项目镜像的引用，
或退一步在**每个项目**用 `install.py --tool cursor --scope project` 安装 `.cursor/rules/*.mdc`。

---

## 3. Copilot 全局入口的边界

`~/.copilot/copilot-instructions.md` **仅 Copilot CLI** 读取；IDE / GitHub.com 的组织级指令靠 UI 配置。
因此 global 作用域下 Copilot 的实际生效范围有限，被标为 `PARTIAL`。需要完整覆盖时，
仍建议在项目级安装 `.github/copilot-instructions.md` 与 `.github/instructions/*.instructions.md`。

---

## 4. 加载机制与边界（不要假设各工具相同）

- **规则入口**：Codex / Claude Code 全局入口由工具按官方机制自动发现；Copilot 仅 CLI。
- **Skills**：安装在各工具官方用户级目录，遵循 Agent Skills 开放规范，可被自动发现/触发；
  **WorkBuddy 例外**——它是 project-only，global 作用域不安装 Skills。
- **规范正文**：各工具都**不会**把 `bundle/` 里的 Markdown 自动载入上下文；入口只提供路径索引，
  AI 需用自己的文件读取工具按需读取。Claude Code 的 `@path` import 是特例，但官方明确它
  **不减少上下文成本**，故本仓库不依赖它拉全量规范。
- **不写绝对路径**：本镜像内容可随 home 位置整体搬移；入口用 `~` 表示 home，由工具自行展开。

---

## 5. WorkBuddy 为什么没有全局产物

腾讯 WorkBuddy 是本项目**唯一 project-only** 的工具：任务书明确"不创建用户级全局规则"
"不写入 WorkBuddy 用户级目录"。因此：

- `GLOBAL_TOOL_SPECS["workbuddy"]` 设 `entry=None` + `project_only=True`；
- `--scope global`（含 `--all --scope global`）由 `build_plan` 与 `check.py` 的统一守卫
  **完全跳过**该工具，既不写 `~/.codebuddy/rules/`、也不写 `~/.codebuddy/skills/`、
  更不生成 `~/.codebuddy/CODEBUDDY.md`；
- 它仍随 bundle 镜像共享一份只读规范文档（`bundle/adapters/workbuddy/`），供需要时引用，
  但镜像不是用户级 `.codebuddy/` 配置，不会被当作全局规则加载。

要让 WorkBuddy 遵守本规范，请在**每个项目**用
`python tooling/scripts/install.py --tool workbuddy --scope project --target <项目根>` 安装。
详见 `bundle/adapters/workbuddy/README.md`。这个例外通过通用 `project_only` 标志实现，
不在安装器里硬编码工具名，其余四工具的 global 行为完全不变。

---

## 6. 更新与卸载

```bash
# 更新（同 project，加 --scope global；WorkBuddy 自动跳过，无需单独处理）
python tooling/scripts/install.py --all --scope global --force

# 检查安装结果（指向 home 管理目录的 manifest）
python tooling/scripts/check.py --scope global
```

global 作用域遵循与 project **完全相同**的安全约束：默认不覆盖用户已有全局入口文件、
`--force` 覆盖前先备份、用户改过的托管文件默认跳过。详见
`~/.ai-engineering-standards/bundle/docs/installation.md`。

卸载：本安装器不自动删除文件（避免误删用户资产）。按
`~/.ai-engineering-standards/manifest.json` 的 `files` 清单核对归属标记与哈希后手工删除。

---

## 7. 需要人工验证（安装器不声称已验证）

- 各 AI 客户端**真实运行时**是否按预期加载用户级 Skills / 全局入口——本机未安装这些客户端，
  `check.py --scope global` 只做静态配置与哈希检查，不等于真实运行验证。
- WorkBuddy 桌面端项目级实际读取 `.codebuddy/` 还是 `.workbuddy/`，以及真实客户端是否加载
  项目规则与 Skills——须人工核对（本机未安装 WorkBuddy 客户端）。
- Cursor Customize UI 的当前配置项名称、Copilot CLI 各版本对全局指令的支持差异。
- 具体工具的系统级约束与本规范冲突时的实际优先级。

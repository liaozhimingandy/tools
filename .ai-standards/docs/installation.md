# 安装指南（各平台具体示例）

> 前置条件：**Python 3.10+**，无第三方依赖。
> 所有命令都在 `ai-engineering-standards` 仓库根目录执行，除非用 `--cd` 显式切换。
> `--target` 指向**要接入规范的目标项目根目录**，默认是当前工作目录。

---

## 1. 先确认环境

```bash
python --version        # Windows 上也可能是 py -3 --version
python -c "import sys, pathlib, hashlib, difflib; print('stdlib ok', sys.version_info[:2])"
```

本仓库不使用 `pip install`，不需要虚拟环境，不需要网络。

---

## 2. 参数速查

| 参数 | 说明 |
| --- | --- |
| `--tool NAME` | 指定工具，可重复：`codex` / `claude`（=`claude-code`）/ `cursor` / `copilot` / `workbuddy`（=`codebuddy`=`tencent-workbuddy`） |
| `--all` | 安装全部五种工具（WorkBuddy 为 project-only，`--scope global` 时自动跳过） |
| `--scope project\|global` | 作用域：`project`（默认，装到 `--target`）或 `global`（装到用户 home；WorkBuddy 无用户级产物） |
| `--target PATH` | `scope=project` 的目标项目根目录，默认 `.` |
| `--home PATH` | `scope=global` 的**逻辑 home 根**，默认当前用户 home；用于隔离测试/CI |
| `--dry-run` | 只打印计划，不创建目录、不写文件、不写清单 |
| `--list` | 只列将要安装的文件与目标绝对路径，不写任何文件 |
| `--force` | 允许更新**本仓库管理**的文件；打印 unified diff、覆盖前自动备份 |
| `--version` | 打印规范版本后退出 |

`--tool` 与 `--all` 至少给一个；两者同时给出时以 `--all` 为准。
`--force` **不会**覆盖用户自有文件——这是硬约束，不是可配置项。

三个命令的退出码统一：`0` = 无 ERROR；`1` = 存在 ERROR；`2` = 工具执行失败。
`validate.py` 支持 `--skills` / `--core` / `--adapters` / `--strict`；
`check.py` 支持 `--target`（安装结果）与 `--all` / `--skills` / `--adapters`（仓库一致性）。
各命令均支持 `--help`。

---

## 3. Windows（PowerShell / CMD / Git Bash）

仓库位于 `E:\work\ai-engineering-standards`，目标项目 `E:\work\my-app`：

```powershell
# PowerShell
cd E:\work\ai-engineering-standards
python tooling\scripts\validate.py

# 先看计划
python tooling\scripts\install.py --tool codex --target E:\work\my-app --dry-run

# 安装全部五种工具
python tooling\scripts\install.py --all --target E:\work\my-app

# 或只装腾讯 WorkBuddy（project-only，不写用户级目录）
python tooling\scripts\install.py --tool workbuddy --scope project --target E:\work\my-app

# 验证
python tooling\scripts\check.py --target E:\work\my-app
```

```cmd
:: CMD
cd /d E:\work\ai-engineering-standards
python tooling\scripts\install.py --tool claude --target E:\work\my-app
```

```bash
# Git Bash（路径用 POSIX 风格或加引号）
cd /e/work/ai-engineering-standards
python tooling/scripts/install.py --all --target "/e/work/my-app"
```

Windows 注意事项：

- 如果 `python` 不在 PATH，可用 `py -3` 或 Python 的绝对路径，例如
  `"C:\Users\you\AppData\Local\Programs\Python\Python313\python.exe" tooling\scripts\install.py --all`.
- 路径含空格时用双引号包住整个 `--target` 值。
- 安装器**不创建符号链接**，因此不需要管理员权限或开发者模式。
- 所有安装目标内部以 POSIX 相对路径定义，由 `pathlib` 转成当前平台的分隔符。

---

## 4. Linux / macOS

```bash
cd ~/src/ai-engineering-standards
python3 tooling/scripts/validate.py

# 单个工具
python3 tooling/scripts/install.py --tool codex --target ~/src/my-app

# 全部工具，先看计划
python3 tooling/scripts/install.py --all --target ~/src/my-app --dry-run
python3 tooling/scripts/install.py --all --target ~/src/my-app

# 验证
python3 tooling/scripts/check.py --target ~/src/my-app
```

macOS 上若 `python3` 来自 Xcode Command Line Tools，确认版本 ≥ 3.10：
`python3 --version`。

---

## 4.5 用户级全局安装（--scope global）

项目级安装对每个项目各装一份；全局安装让规范对**当前用户的所有项目**生效。
规范体系统一放在用户 home 下一个共享目录，Skills 按各工具官方用户级目录分发。

```bash
# 安装到真实用户 home（影响该用户所有项目，请先确认需要）
python tooling/scripts/install.py --all --scope global

# 只装一个工具
python tooling/scripts/install.py --tool claude --scope global

# 验证（--target 指向逻辑 home；省略 --target 时 --scope global 用真实 home 相关语义）
python tooling/scripts/check.py --scope global --target ~

# 隔离测试 / CI：用 --home 指向任意目录，绝不触碰真实用户 home
python tooling/scripts/install.py --all --scope global --home /tmp/fakehome
python tooling/scripts/check.py --scope global --target /tmp/fakehome
```

**global 安装布局**（相对逻辑 home 根）：

| 内容 | 路径 | 说明 |
| --- | --- | --- |
| 规范镜像（唯一一份） | `.ai-engineering-standards/bundle/` | 其余工具共享，保持文件间相对链接（含 WorkBuddy 适配器文档副本，非用户级配置） |
| 安装清单 | `.ai-engineering-standards/manifest.json` | `scope: "global"`，只含相对路径与哈希 |
| 集成说明 | `.ai-engineering-standards/GLOBAL-INTEGRATION.md` | 加载机制、边界、更新与卸载 |
| 覆盖前备份 | `.ai-engineering-standards/backups/<时间戳>/` | 仅 `--force` 覆盖被改过的托管文件时产生 |
| Codex 全局入口 | `.codex/AGENTS.md` | 官方 `SUPPORTED` |
| Claude 全局入口 | `.claude/CLAUDE.md` | 官方 `SUPPORTED` |
| Copilot 全局入口 | `.copilot/copilot-instructions.md` | 官方 `PARTIAL`，**仅 CLI** 读取 |
| Cursor 全局入口 | **不生成** | 官方 User Rules 仅在 Customize UI，磁盘无路径 |
| WorkBuddy 全局入口与用户级 Skills | **不生成** | project-only：任务书禁止写用户级目录，`--scope global` 完全跳过，不创建 `~/.codebuddy/` |
| 用户级 Skills | `.agents/skills/`、`.claude/skills/`、`.cursor/skills/`、`.copilot/skills/` | 各工具官方用户级发现目录（不含 WorkBuddy） |

**必须知道的边界**：

- `--scope global` 下 `--target` 被忽略（避免误写到某个项目）；要改安装根请用 `--home`。
- 全局入口是**生成文件**：源模板含 `version=GENERATED`，安装时替换为真实版本；
  `check.py` 会用同一渲染函数重算并检查是否过期。
- 各工具都**不会**把 `bundle/` 里的 Markdown 自动载入上下文；入口只给路径索引，
  AI 需自行展开 `~` 并按需读取。Claude Code 的 `@path` import 不减少上下文成本，故不依赖。
- Cursor 用户级规则、Copilot 各 IDE 版本支持差异属 `PARTIAL` / `UNVERIFIED`，
  安装器**不编造**配置文件；详见生成的 `GLOBAL-INTEGRATION.md`。
- **WorkBuddy 是唯一 project-only 工具**：`--scope global` 时其安装计划为空（不写
  `~/.codebuddy/` 任何文件），但共享的 bundle 镜像仍会安装。这是任务书"不写入用户级目录"
  的硬约束，通过 `GlobalToolSpec.project_only` 通用标志实现，非针对工具名的特判。

---

## 4.6 腾讯 WorkBuddy 项目级安装（project-only）

WorkBuddy 的 CLI 引擎是 CodeBuddy Code，磁盘配置目录为 `.codebuddy/`。本适配器**只做项目级代码开发配置**，不创建任何用户级全局规则。

```bash
# 目标接口（任务书指定）
python tooling/scripts/install.py --tool workbuddy --scope project --target ../my-project

# 预览计划（不写文件）
python tooling/scripts/install.py --tool workbuddy --target ../my-project --dry-run

# 校验安装结果
python tooling/scripts/check.py --scope project --target ../my-project

# 更新（仅覆盖本仓库管理且有变化的文件，覆盖前备份）
python tooling/scripts/install.py --tool workbuddy --target ../my-project --force
```

生成的项目级文件：

| 文件 | 类别 | 作用 |
| --- | --- | --- |
| `CODEBUDDY.md` | guarded 入口 | 项目记忆入口（红线 + 索引），与 `AGENTS.md` 兼容且优先 |
| `.codebuddy/rules/ai-engineering-standards.md` | additive 叠加规则 | 无 frontmatter，启动常驻；入口被占用时仍生效 |
| `.codebuddy/skills/<name>/` | 逐字节复制 | 5 个公共 Skill，官方项目级发现路径 |
| `.ai-standards/` | 只读镜像 | 完整规范正文，供入口按需引用 |

**边界与保护**：

- 只写目标项目；`--scope global` 完全跳过，不创建 `~/.codebuddy/`。
- 若项目已有自己的 `CODEBUDDY.md` 或 `.codebuddy/rules/ai-engineering-standards.md`（无归属证据），安装器**跳过**，即使 `--force` 也不覆盖。
- `CODEBUDDY.md` 是项目记忆/上下文入口，`.codebuddy/rules/` 是项目级代码开发规则；二者**不是**用户级全局规则，也不会影响非本项目的工作目录。
- Agents 与 Commands 按任务书决策**不生成**：只提供 `adapters/workbuddy/templates/` 下的映射模板，相关运行时发现能力标为未验证。
- 真实客户端是否自动加载规则与 Skills，须在 WorkBuddy 中用 `/memory`、Skills 列表与 probe prompt 人工核对（本机未安装该客户端，静态验证不能替代）。

完整设计见 [`adapters/workbuddy/README.md`](../adapters/workbuddy/README.md) 与 [`adapters/workbuddy/references.md`](../adapters/workbuddy/references.md)。

---

## 5. 在项目根目录直接安装（默认 target）

```bash
cd /path/to/my-app
python /path/to/ai-engineering-standards/tooling/scripts/install.py --all
python /path/to/ai-engineering-standards/tooling/scripts/check.py
```

此时 `--target` 省略，安装器使用当前工作目录。适合把命令写进项目的
`Makefile` / `justfile` / npm script / CI 步骤。

CI 示例（GitHub Actions，仅做验证，不提交生成文件）：

```yaml
- name: Validate standards
  run: python tooling/scripts/validate.py
- name: Dry-run install check
  run: python tooling/scripts/install.py --all --dry-run
```

---

## 6. 安装输出与错误级别

```
[INFO]    ai-engineering-standards 1.0.0 -> /path/to/my-app (tools: codex, claude, cursor, copilot, workbuddy)
[INFO]    PLAN  .agents/skills/project-analysis/SKILL.md  <- skills/project-analysis/SKILL.md
[WARNING] SKIP  AGENTS.md (user-owned, never overwritten) -- see docs/installation.md §8
[ERROR]   ...                      # 必须修复，进程退出码 1
```

| 级别 | 含义 | 退出码 |
| --- | --- | --- |
| `ERROR` | 必须修复（源文件缺失、路径非法、写入失败、完整性校验失败） | 1 |
| `WARNING` | 建议修复或需人工处理（入口文件被占用、源中已移除的旧文件、描述触发词不足） | 0 |
| `INFO` | 正常计划与结果信息 | 0 |

`--dry-run` 下有冲突也只打印 `WARNING`，不会创建任何目录或文件。

---

## 7. 更新已安装的项目

```bash
# 1. 拉取新版本规范仓库
git -C /path/to/ai-engineering-standards pull

# 2. 先看会改什么（可选）
python tooling/scripts/install.py --all --target /path/to/my-app --dry-run

# 3. 用 --force 更新（只覆盖 manifest 登记的托管文件，覆盖前自动备份）
python tooling/scripts/install.py --all --target /path/to/my-app --force

# 4. 验证
python tooling/scripts/check.py --target /path/to/my-app
```

**用户修改检测**：安装器不是"覆盖前看一眼"，而是三层判定：
1. 文件是否在 `manifest.json` 的 `files` 中登记（未登记 = 用户文件，永不覆盖）；
2. 清单登记的文件，其当前 SHA-256 是否与"上次安装记录"一致（不一致 = 用户改过）；
3. 归属标记只作辅助证据（Skills / 镜像文件本身不带标记，清单登记即为托管）。

对**用户改过的托管文件**：不带 `--force` 时默认跳过、计入 `Conflict` 并报 `WARNING`；
`--force` 时**先把当前内容备份**再覆盖，并在摘要里列出 `backed up N file(s)`。

`--force` 对每个内容有变化的文件先打印 unified diff，再写入：

```
[INFO]    UPDATE  .cursor/rules/ai-engineering-standards.mdc
--- installed
+++ source
@@ -6,3 +6,4 @@
 - 不得伪造测试结果
+- 不得将未验证的代码描述为已完成
```

**备份位置**：`<管理目录>/backups/<YYYYmmddTHHMMSS>/<原相对路径展平>.bak`。
project 的管理目录是 `<target>/.ai-standards/`，global 是 `<home>/.ai-engineering-standards/`。
每条备份在 `manifest.json` 的 `backups` 段记录 `backup` / `sha256` / `at` / `target`。

**原子性与回滚**：单文件用「同目录临时文件 + `os.replace`」原子替换，失败保留原文件；
多文件安装若中途出错，事务回滚本次创建/修改，且**不写入成功的 manifest**——
绝不会留下"清单说装好了、实际缺文件"的虚假状态。回滚不会删除用户在安装期间产生的其它文件。

重复执行是安全的：完全相同的文件计入 `Unchanged`，不做无谓写入。摘要格式：

```
=== Installation summary ===
  Created   : 0
  Updated   : 2
  Skipped   : 1
  Conflict  : 1
  Unchanged : 161
  Written 2 file(s); backed up 1 file(s).
  User files were preserved. Some files were skipped/conflicted — see WARNINGs above.
  Installation completed with warnings.
```

---

## 8. 已有规则文件的项目（重要）

安装器检测到用户自有的入口文件时会**跳过**它们，但仍安装可叠加的规则通道：

```
[WARNING] SKIP  AGENTS.md (user-owned, never overwritten)
[INFO]    PLAN  .claude/rules/ai-engineering-standards.md
[INFO]    PLAN  .cursor/rules/ai-engineering-standards.mdc
[INFO]    PLAN  .github/instructions/ai-engineering-standards.instructions.md
```

如果目标项目只有 Codex，且 `AGENTS.md` 已被占用，需要手工在自有 `AGENTS.md` 中
加一行指向已安装的规范本体：

```markdown
<!-- 项目自有规则在上，以下内容由人工维护 -->
通用工程规范见 .ai-standards/core/ ，按需读取；红线规则见
.ai-standards/core/ai-behavior.md 。
```

**不要**手工编辑带 `AI-ENGINEERING-STANDARDS:MANAGED` 标记的文件——
它们会在下次 `--force` 时被覆盖。项目专属规则请放在
[README §8](../README.md) 列出的位置。

---

## 9. 安装结果自检

```bash
python tooling/scripts/check.py --target /path/to/my-app
```

它检查：`manifest.json` 存在且 schema 正确、版本等于 `VERSION`、
清单中每个文件存在且 SHA-256 一致、Skills Frontmatter 合法、
适配器格式符合对应工具约定、没有用户文件被覆盖。
若只安装了部分工具，`check.py` 只检查清单中登记的那些工具。

---

## 10. 常见问题排查

| 现象 | 原因与处理 |
| --- | --- |
| `ERROR: source repo not found` | 从仓库外部调用时路径推断失败；用绝对路径调用 `install.py`，或先 `cd` 进仓库 |
| 大量 `SKIP ... (user-owned)` | 目标项目已有规则文件；属预期行为，见 §8 |
| `WARNING: stale managed file` | 新版本移除了某文件，安装器不会自动删除；确认后手工清理 |
| `ERROR: integrity check failed` | 安装后的文件与源哈希不一致（磁盘/权限/编码问题）；检查目标目录写权限与文件编码 |
| `check.py` 报 `manifest not found` | 该目录尚未安装，或 `--target` 指错了层级（必须是项目根） |
| Windows 上路径报错 | 用双引号包裹含空格路径；避免把 `--target` 写成 UNC 网络路径 |

---

## 11. 卸载与清理

安装器**不提供自动卸载**，因为它不删除文件（避免误删用户资产）——这与
"默认不覆盖用户文件"是同一条安全原则。需要移除时按清单**逐项核对后手工删除**：

```bash
# 1. 先看清单里登记了哪些托管文件（只列相对路径，不含绝对路径）
python -c "import json;print('\n'.join(json.load(open('<target>/.ai-standards/manifest.json'))['files']))"

# 2. 逐项确认：文件哈希与清单一致、且带归属标记（或 Skills/镜像这类清单登记文件），
#    再删除。切勿用 rm -rf 删除整个项目/用户目录。
```

- **project**：删除 `<target>/.ai-standards/` 管理目录（含清单与备份），再按清单
  `files` 逐个删除 `AGENTS.md` / `CLAUDE.md` / `.cursor/rules/*.mdc` /
  `.github/instructions/*.instructions.md` / 四个 Skills 目录 / `.claude/rules/*.md` 等。
- **global**：删除 `<home>/.ai-engineering-standards/`（含 `GLOBAL-INTEGRATION.md`），
  再按 `manifest.json`（`scope: "global"`）逐个删除 `.codex/AGENTS.md` /
  `.claude/CLAUDE.md` / `.copilot/copilot-instructions.md` / 四个用户级 Skills 目录。
- **备份**：`<管理目录>/backups/` 保留被 `--force` 覆盖前的原始内容，确认不需要后可单独删除。
- **用户自有文件**：安装过程中被跳过的文件从未属于本工具，卸载时**不要**删除它们。

> 安全提示：删除前务必确认目标路径在预期安装目录内，避免把用户项目里同名但自有的
> `AGENTS.md` / `CLAUDE.md` 一起删掉。清单 `files` 是唯一应删除的托管文件集合。

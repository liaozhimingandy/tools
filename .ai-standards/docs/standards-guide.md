# 规范指南

> 本文说明 `core/` 与 `standards/` 的职责划分、按需加载方式、新增规范的流程，
> 以及**一份合格规范必须满足的质量标准与检查清单**（§7、§8）。
> **一条规则只在一个文件里定义**；其他文件用相对链接引用。
> 规范用语定义与冲突处理的唯一权威见 [../core/README.md](../core/README.md) §2、§4。

---

## 1. 两层，职责不重叠

| 层 | 定位 | 回答的问题 | 是否绑定技术栈 |
| --- | --- | --- | --- |
| `core/` | 原则与红线，跨语言、跨工具、跨项目 | 「什么是对的 / 什么绝对不能做」 | 否 |
| `standards/` | 可落地的技术规范 | 「在 Python / API / Vue / Docker 里具体怎么做」 | 是 |

`standards/` **不重复** `core/` 的原则，只做具体化并链接回 `core/`。
例如 `standards/backend/api.md` 不重新论证「最小权限」，而是写
「每个端点都要做对象级授权，依据 [core/security-principles.md](../core/security-principles.md)」。

`core/ai-behavior.md` 是唯一约束 **AI 自身行为** 的文件；`agents/` 只定义角色，
不复述这些红线；`skills/` 只在工作流中引用它们。

---

## 2. 文件清单与职责

### 2.1 `core/`（8 份）

| 文件 | 职责 | 主要读者 |
| --- | --- | --- |
| `README.md` | **统一入口**：用语定义、优先级、冲突处理、按任务选规范 | 所有任务，先读 |
| `engineering-principles.md` | 单一职责、高内聚低耦合、DRY/KISS/YAGNI、最小必要修改、复用优先、避免过度设计、模块边界、异常/日志/配置、安全边界、文档维护、向后兼容 | 所有开发任务 |
| `architecture-principles.md` | 模块划分、依赖方向、接口契约、数据归属、扩展点、方案评估、架构变更流程 | 架构设计与改动评估 |
| `coding-principles.md` | 命名、可读性、异常/日志/配置/资源的代码级写法、注释、类型、并发、可测试性 | 编码与审查 |
| `security-principles.md` | 认证/授权分离、注入类、XSS/CSRF/SSRF、密钥与日志脱敏、上传、依赖、多租户隔离、安全变更 | 所有涉及输入输出/权限的改动 |
| `testing-principles.md` | 测试目标与层次、边界与异常测试、回归、测试数据、Mock 边界、覆盖率与质量、测试汇报 | 写测试与验收 |
| `ai-behavior.md` | AI 修改代码前后的硬性行为约束、澄清义务、汇报义务、技术决策 | **所有 AI 工具** |
| `documentation-principles.md` | 文档真实性、与代码同步、示例可执行、结构清晰、事实与设计选择分离 | 所有文档改动 |

### 2.2 `standards/`（12 份）

| 分组 | 文件 | 按需加载的场景 |
| --- | --- | --- |
| `languages/` | `python.md` | 编写或审查 Python 代码 |
| | `typescript.md` | 编写或审查 TypeScript 代码 |
| | `javascript.md` | 编写或审查 JavaScript 代码 |
| `backend/` | `api.md` | 新增/修改 HTTP 接口、契约、错误码 |
| | `database.md` | schema 变更、迁移、事务、查询 |
| | `authentication.md` | 登录、会话、Token、授权模型 |
| `frontend/` | `vue.md` | Vue 组件与组合式 API |
| | `component.md` | 通用组件设计与状态归属 |
| | `ui.md` | 样式、可访问性、响应式、交互反馈 |
| `devops/` | `docker.md` | 镜像、容器运行时、构建缓存 |
| | `git.md` | 分支、提交、合并、回滚 |
| | `ci-cd.md` | 流水线、门禁、制品与发布 |

---

## 3. 按需加载怎么用

入口适配器（`AGENTS.md` / `CLAUDE.md` / `.mdc` / `.instructions.md`）里只有
**红线规则 + 规范索引**。AI 在处理具体任务时，按索引读取对应文件：

```
任务 = 新增一个后端接口
  → 常驻：core/ai-behavior.md（红线，已在适配器中）
  → 按需：standards/languages/python.md
          standards/backend/api.md
          standards/backend/database.md（若涉及表变更）
          core/testing-principles.md（写测试时）
          skills/software-development（执行工作流）
```

完整规范本体安装到目标项目的 `.ai-standards/` 下，目录结构与本仓库一致，
因此适配器中的相对链接在安装后依然成立。

**不要把整个 `standards/` 一次性塞进上下文**：这与「按需加载」原则冲突，
也会稀释真正重要的红线规则。按任务选规范的对照表见
[../core/README.md](../core/README.md) §6。

---

## 4. 新增 / 修改规范

```bash
# 1. 选位置：通用 → core/；技术栈相关 → standards/<group>/
# 2. 用模板
cp tooling/templates/STANDARD.md.template standards/<group>/<name>.md
# 3. 写内容，检查是否与其他文件重复；重复的部分改成链接
# 4. 在本文 §2 的清单中登记触发场景
# 5. 自检 + 分发
python tooling/scripts/validate.py
python tooling/scripts/install.py --all --force --target <your-project>
```

每份 `core/` 规范文件 **MUST** 包含六段结构：

1. **文档目的**；
2. **适用范围**；
3. **核心规范**（用 [../core/README.md](../core/README.md) §2 定义的
   MUST / MUST NOT / SHOULD / SHOULD NOT / MAY 标注每条规则）；
4. **禁止事项**（索引式汇总，不重新定义规则）；
5. **验收要求**（可核对的证据与检查项，回答「如何判断是否遵守」）；
6. **相关规范引用**（相对链接，指向真实文件）。

`standards/` 文件 **MUST** 包含：**适用范围**（何时读、何时不读）、
**可执行的规则**（祈使句、可判断对错，避免「尽量」「合理」等无法验收的措辞）、
**与 `core/` 的链接**（若具体化了某条原则）、
**可检查项**（能被 `validate.py` 或项目自身 lint/测试覆盖的部分）。

**章节编号约束**：全仓库有大量 `§N` 交叉引用指向 `core/` 与本文。
修改既有文件时 **MUST** 保留章节编号与文件名；新增主题 **SHOULD** 追加编号，
**MUST NOT** 重排已有编号，否则会一次性打断
[../standards/](../standards/)、[../agents/](../agents/)、
[../skills/](../skills/) 中的引用。

---

## 5. 冲突处理规则

**本仓库冲突规则的唯一权威位置是 [../core/README.md](../core/README.md) §4**，
其中定义了 6 条处理原则（当前任务要求优先但不突破安全边界、
项目有效约束优先于通用默认值、安全要求不得被忽略、
`standards/` 只细化不推翻 `core/`、Skills 不覆盖核心规范、
无法解决时报告并请求用户决策）。本节只说明如何应用，不另立一套优先级。

应用要点：

- **MUST NOT** 让某条 `standards/` 规则与 `core/` 长期矛盾；
  发现冲突时以 `core/` 为准并**立即修正** `standards/`，
  **MUST NOT** 用「特例」注释把矛盾留在仓库里。
- **MUST NOT** 让 Skills 的工作流步骤覆盖核心红线；步骤与红线冲突时以红线为准。
- 发现规范与实际项目冲突时，**MUST** 指出冲突并请求用户决策，
  **MUST NOT** 默默忽略，见 [../core/ai-behavior.md](../core/ai-behavior.md) §2。
- `validate.py` 检查重复文件与无效链接；**语义冲突目前依赖人工评审**与
  [../skills/code-review/SKILL.md](../skills/code-review/SKILL.md) 兜底，
  本仓库尚未实现规则语义冲突的自动检测。

---

## 6. 项目专属规则放哪里

本仓库**不收**项目专属规则（例如「本项目的订单状态机有 7 个状态」）。
它们应放在目标项目内、且不与托管文件冲突的位置：

| 工具 | 位置 |
| --- | --- |
| Codex | 项目自有 `AGENTS.md` 段落，或子目录 `AGENTS.md` |
| Claude Code | `CLAUDE.local.md`（gitignore）或 `.claude/rules/your-rule.md` |
| Cursor | `.cursor/rules/your-rule.mdc` |
| Copilot | `.github/instructions/your-rule.instructions.md`（`applyTo`） |

接入示例见 `examples/fastapi-vue/` 与 `examples/python-application/`。
规范层级图（职责分层 ≠ 加载顺序）见 [../core/README.md](../core/README.md) §5。

---

## 7. 一份合格规范必须满足的 9 条标准

新增或修改任何规范（含 `core/`、`standards/`）时，逐条核对：

| # | 标准 | 判断方式 |
| --- | --- | --- |
| 1 | **目的明确** | 读完「文档目的」能说清这份文件解决什么问题，不与其他文件混同 |
| 2 | **适用范围明确** | 写清「何时读、何时不读」，不含「所有情况都适用」这类无信息量表述 |
| 3 | **规则可执行** | 每条规则回答「AI 应该做什么 / 不应该做什么」，是祈使句，能判断对错 |
| 4 | **规则可验证** | 每条重要规则有「判断依据」或「验收要求」，能给出可追溯的证据 |
| 5 | **不与其他规范冲突** | 与 [../core/README.md](../core/README.md) §4 及相关文件逐条比对，无相反要求 |
| 6 | **不重复已有规范** | 同一条规则只在一个位置定义，其他位置用相对链接 |
| 7 | **不依赖未经确认的技术假设** | 外部事实附官方来源与核实日期，无法确认的标「待验证」 |
| 8 | **有必要的示例** | 抽象规则配至少一个具体、可执行的正反例或检查项 |
| 9 | **有明确的例外处理方式** | `SHOULD` / `SHOULD NOT` 被突破时，明确要求写出理由；`MUST` 不设例外 |

**MUST NOT** 把「编写高质量代码」「注意系统安全」这类无法判断对错的口号写进规范正文。
**MUST NOT** 滥用 MUST：只有真正需要强制执行的要求才用 MUST，见
[../core/README.md](../core/README.md) §2。

---

## 8. 规范检查清单

提交规范改动前逐条勾选（[ ] 表示未核对）：

- [ ] 是否明确说明适用范围？
- [ ] 是否使用统一规范用语（MUST / MUST NOT / SHOULD / SHOULD NOT / MAY）？
- [ ] 是否包含可执行要求？
- [ ] 是否包含禁止事项？
- [ ] 是否能够验证执行结果（有判断依据 / 验收要求 / 可检查项）？
- [ ] 是否存在重复规则？
- [ ] 是否存在规则冲突？
- [ ] 是否错误地绑定某个 AI 工具（写入工具专有路径、字段或配置）？
- [ ] 是否错误地绑定某个技术栈（在 `core/` 中规定具体框架/语言/数据库）？
- [ ] 是否需要补充引用（相对链接指向真实文件，章节编号未重排）？

补充检查（本仓库特有）：

- [ ] `python tooling/scripts/validate.py --strict` 无 ERROR；
- [ ] `python tooling/scripts/check.py --all` 六类报告中「缺失/过期/不一致」均为 0；
- [ ] 新增 `core/` 文件已在本文 §2.1 与
      [../core/README.md](../core/README.md) §3 的文件清单中登记；
- [ ] 新增 `core/` **规范文件**含六段（文档目的 / 适用范围 / 核心规范 / 禁止事项 /
      验收要求 / 相关规范引用），并引用 `core/README.md`；
      `python tooling/scripts/validate.py --core` 可自动检查结构（`README.md` 是索引，不套六段）；
- [ ] 若涉及安装目标或适配器，已按
      [../CONTRIBUTING.md](../CONTRIBUTING.md) §3 补测试与官方依据；
- [ ] 若修改了 `targets.py` 的路径常量或 `INSTALLER_VERSION`，已同步更新
      `tooling/config/targets.json`，否则 `check.py --all` 会报"不一致文件"（双源漂移保护）。

> **自动检查的边界**：`validate.py --core` 只核对结构与可机械判断的信号，
> **不判定两条规则是否语义矛盾**。`check.py --all` 的「需要人工检查的项目」会列出
> 排他性优先级措辞与语义冲突待人工评审项——这部分必须人工核对
> [../core/README.md](../core/README.md) §4，任何自动工具都不得声称已完成语义分析。

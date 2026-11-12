# 核心规范索引

> **本文是 `core/` 的统一入口**。所有 AI 编程工具、所有项目、所有语言在读取核心规范时，
> 都应先读本文，再按 §6 选择需要的文件。
> **规范用语**（MUST / MUST NOT / SHOULD / SHOULD NOT / MAY）的定义见本文 §2；
> **规则冲突时的处理顺序**以本文 §4 为唯一权威。
> 规范质量检查清单见 [../docs/standards-guide.md](../docs/standards-guide.md) §8。

---

## 1. 文档目的与定位

`core/` 定义**与 AI 编程工具无关、与编程语言无关、与技术栈无关、与具体业务项目无关**的
通用软件工程规则。它回答三个问题：

1. AI **应该做什么**（`MUST` / `SHOULD`）；
2. AI **不应该做什么**（`MUST NOT` / `SHOULD NOT`）；
3. **如何判断是否遵守**（每份文件的「验收要求」）。

`core/` **不定义**具体框架、库、语言或工具的用法：Python 该用哪个 Web 框架、
前端该用哪个组件模型、数据库该选哪一种、某个 AI 工具的指令文件放哪里，都不属于本层。
这些内容属于 [../standards/](../standards/) 与各工具的适配层，见
[../docs/architecture.md](../docs/architecture.md)。

本层规则的表达遵循一条硬约束：**不写空洞口号**。「编写高质量代码」「注意系统安全」
这类无法判断对错的表述 MUST NOT 出现在规范正文中。

---

## 2. 规范用语

所有 `core/` 文件统一使用以下五个术语。术语的含义在本文中定义一次，其他文件只引用，不重复解释。

| 用语 | 含义 | 违反时的处理 |
| --- | --- | --- |
| **MUST** | 必须遵守。不设有例外；不满足即判定产出不合格 | 视为 ERROR，必须修复 |
| **MUST NOT** | 绝对禁止。任何理由都不能作为例外 | 视为 ERROR，必须撤销该做法 |
| **SHOULD** | 通常应当遵守。确有特殊情况时可以不遵守，**但必须说明具体理由** | 未说明理由则视为未遵守 |
| **SHOULD NOT** | 通常不应采用。确有特殊情况时可以采用，**但必须说明具体理由** | 未说明理由则视为未遵守 |
| **MAY** | 允许采用，属于可选做法，不构成要求 | 不采用不算违反 |

**用语使用约束**：

- **MUST** 与 **MUST NOT** 保留给真正需要强制执行的要求（安全红线、真实性红线、
  授权边界、可验证的硬性行为）。不得为了强调语气而把偏好写成 MUST。
- 存在合理例外、依赖项目上下文、或属于经验性建议的规则，**SHOULD** 而不是 MUST。
- 每条 `SHOULD` / `SHOULD NOT` 被突破时，理由 MUST 写进实施报告或设计说明，
  不能只在心里权衡。
- 规范正文中的「可检查项」「判断依据」用于回答「如何判断是否遵守」，不构成新的用语。
- 本仓库其他文档（如 [../CONTRIBUTING.md](../CONTRIBUTING.md)）中的「必须 / 禁止 / 建议」
  是自然语言表述，正式规则以本层带标签的条目为准。

---

## 3. 文件清单与职责

| 文件 | 唯一职责 | 主要读者 |
| --- | --- | --- |
| [README.md](README.md) | 核心规范入口、用语定义、优先级、冲突处理、按任务选规范 | **所有任务，先读** |
| [engineering-principles.md](engineering-principles.md) | 工程质量取舍、最小必要修改、复用、向后兼容、技术选型、可维护性、异常/日志/配置/安全边界的策略层 | 所有开发任务 |
| [architecture-principles.md](architecture-principles.md) | 职责分离、依赖方向、模块与数据归属、接口契约、方案评估、扩展点、架构变更流程 | 新增模块、边界调整、技术选型 |
| [coding-principles.md](coding-principles.md) | 与语言无关的代码级写法：命名、可读性、异常、日志、配置、资源、并发、可测试性 | 编码与代码审查 |
| [security-principles.md](security-principles.md) | 认证与授权、注入类攻击、敏感信息、数据安全、依赖供应链、多租户隔离、安全变更 | 所有涉及输入输出、权限、数据的改动 |
| [testing-principles.md](testing-principles.md) | 测试目标与层次、边界/异常/回归测试、测试数据、Mock 边界、覆盖率与质量、测试汇报 | 编写测试与验收 |
| [ai-behavior.md](ai-behavior.md) | **唯一**约束 AI 自身行为的文件：先理解不假设、授权边界、真实性、澄清、汇报、技术决策 | **所有 AI 工具，所有任务** |
| [documentation-principles.md](documentation-principles.md) | 文档真实性、与代码同步、示例可执行、结构清晰、事实与设计选择分离 | 所有文档改动 |

**职责边界**：一个主题只在一个文件里定义。例如「日志级别语义」属于
[engineering-principles.md](engineering-principles.md)，「日志语句怎么写」属于
[coding-principles.md](coding-principles.md)，「日志不能含敏感信息」属于
[security-principles.md](security-principles.md)。三者不重复定义同一条规则。

---

## 4. 规则优先级与冲突处理

规范之间出现冲突时，按以下顺序处理。**本文 §4 是本仓库冲突规则的唯一权威位置**，
其他文件只引用本节，不另立一套优先级。

1. **用户明确提出的当前任务要求优先于一般默认偏好，但 MUST NOT 突破安全边界**。
   用户说「这次只改这一个函数」优先于默认的重构建议；但「跳过权限校验」
   不能因为用户提出就执行，应说明风险并请求确认。
2. **项目中明确且有效的约束优先于通用默认规范**。项目已有的架构约定、
   代码风格、依赖版本、目录结构属于项目事实，优先于本层的默认偏好。
3. **安全要求 MUST NOT 因为普通项目约定而被忽略**。
   [security-principles.md](security-principles.md) 的安全红线不因「项目一直这么做」
   而失效；若确实存在冲突，按第 6 条上报，不得静默放宽。
4. **具体技术规范用于细化通用工程原则**。[../standards/](../standards/) 只回答
   「在这个语言/框架里怎么落地」，MUST NOT 改写或推翻 `core/` 的原则。
   若某条 `standards/` 规则与 `core/` 冲突，以 `core/` 为准并修正 `standards/`，
   不得用「特例」注释把矛盾长期留在仓库里。
5. **Skills 负责组织任务流程，MUST NOT 擅自覆盖核心规范**。
   [../skills/](../skills/) 定义执行步骤与输出格式；步骤安排与 `core/` 冲突时，
   以 `core/` 为准，并在 Skill 中修正。
6. **存在无法合理解决的冲突时，MUST 明确报告并请求用户决策**。
   报告需写清：冲突的两条规则、各自来源、可能的两种后果、建议方案。
   MUST NOT 自行选择一方后当作没问题继续实施。

**AI 行为红线与安全红线的位置**：
[ai-behavior.md](ai-behavior.md) 是唯一约束 AI 自身行为的文件，
[security-principles.md](security-principles.md) 是安全红线文件。
它们的规则在本节顺序下生效，但**不再各自声明「本文件绝对优先」**——
那会与第 1、2 条产生无法解释的循环。

---

## 5. 规范层级

```text
core/                     全局工程原则（工具无关、项目无关）
   |
   v
standards/                具体技术规范（语言、框架、技术领域）
   |
   v
skills/                   任务执行流程（按需加载的工作流）
   |
   v
project-specific rules    项目自身约束（由使用方在项目内维护）
```

**这张图表示职责分层，不代表简单的文件加载顺序，也不代表简单的覆盖顺序。**

- 下层**细化**上层，不推翻上层；具体做法见 §4 第 4 条。
- 「按需加载」是上下文管理策略：常驻上下文只放红线与索引，详细规范在遇到具体任务时读取，
  见 [../docs/architecture.md](../docs/architecture.md) §5。
- 项目专属规则不收入本仓库，放在目标项目内且不与托管文件冲突的位置，
  见 [../docs/standards-guide.md](../docs/standards-guide.md) §6。
- 具体 AI 工具可能有**自己的系统级约束和优先级机制**（例如工具内置的安全策略、
  系统提示、组织级托管策略）。公共规范 **MAY** 与它们并存，但
  **不能保证覆盖这些约束，也不能假定它们的加载顺序**。遇到工具系统级约束与
  本层规则冲突时，以工具实际生效的约束为准，并按 [ai-behavior.md](ai-behavior.md) §6
  如实报告，MUST NOT 声称「公共规范一定生效」。

---

## 6. 如何按任务选择相关规范

**SHOULD** 按「必读 + 按需」两段加载，避免把全部规范一次性塞进上下文。

| 任务 | 必读 | 按需补充 |
| --- | --- | --- |
| 任何任务（起点） | [README.md](README.md)、[ai-behavior.md](ai-behavior.md) | — |
| 接手陌生项目 / 现状调研 | [ai-behavior.md](ai-behavior.md) §2 | [../skills/project-analysis/SKILL.md](../skills/project-analysis/SKILL.md) |
| 理解需求、确定验收标准 | [ai-behavior.md](ai-behavior.md) §5 | [../skills/requirements-analysis/SKILL.md](../skills/requirements-analysis/SKILL.md) |
| 新增模块 / 调整边界 / 技术选型 | [architecture-principles.md](architecture-principles.md) | [engineering-principles.md](engineering-principles.md) |
| 编写或修改业务代码 | [engineering-principles.md](engineering-principles.md)、[coding-principles.md](coding-principles.md) | 对应 [../standards/languages/](../standards/languages/) |
| 涉及输入输出、身份、权限、数据 | [security-principles.md](security-principles.md) | 对应 [../standards/backend/](../standards/backend/) |
| 编写测试、执行验收 | [testing-principles.md](testing-principles.md) | 对应 `standards/` 的测试约定 |
| 修改数据库结构 | [ai-behavior.md](ai-behavior.md) §3、[engineering-principles.md](engineering-principles.md) §13 | [../standards/backend/database.md](../standards/backend/database.md) |
| 编写或修改文档 | [documentation-principles.md](documentation-principles.md) | — |
| 提交前审查 | [../skills/code-review/SKILL.md](../skills/code-review/SKILL.md) | 上述与改动相关的全部文件 |

简单、低风险、可逆的任务 **MAY** 简化流程，但 [ai-behavior.md](ai-behavior.md) 的红线
与 §4 的冲突处理规则在任何任务中都适用。

---

## 7. 维护约定与已知边界

- 新增规则前 MUST 先确认「这条规则是否已在别处定义」；重复的规则改为相对链接引用。
- 修改 `core/` 文件时 MUST 保留既有章节编号与文件名：全仓库有大量 `§N` 交叉引用
  指向本层，重排编号会打断 [../standards/](../standards/)、[../agents/](../agents/)、
  [../skills/](../skills/) 中的引用。新增主题**追加编号**，不重排已有编号。
- 每份 `core/` **规范文件**（7 份，不含本索引）MUST 包含六段：文档目的、
  适用范围、核心规范、禁止事项、验收要求、相关规范引用；
  验收要求 MUST 给出可核对的证据。
- 本文是**索引**，按其用途采用 §1–§7 结构，不套用上述六段
  （否则会与 §3 文件清单、§4 冲突规则重复定义同一内容）。
  六段结构与新增规范的流程见
  [../docs/standards-guide.md](../docs/standards-guide.md) §4。
- 提交前的检查清单见 [../docs/standards-guide.md](../docs/standards-guide.md) §8，
  仓库自检命令见 [../CONTRIBUTING.md](../CONTRIBUTING.md) §2。
- **已知边界**：本层只定义规则文本。规则是否被某个 AI 客户端真正加载并执行，
  取决于工具自身行为，不由本层保证；本仓库当前也未实现「规范语义冲突」的
  自动检测，冲突判断依赖人工评审与
  [../skills/code-review/SKILL.md](../skills/code-review/SKILL.md)。

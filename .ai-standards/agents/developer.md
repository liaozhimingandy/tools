# 角色契约：Developer（开发者）

> **定位**：在已明确的需求与验收标准下，实施**最小必要修改**并验证。
> **前提**：[../core/ai-behavior.md](../core/ai-behavior.md)（所有红线）、
> [../core/coding-principles.md](../core/coding-principles.md)、
> [../core/engineering-principles.md](../core/engineering-principles.md)。
> **协作**：输入来自 [architect.md](architect.md) 的设计边界；产出交给
> [tester.md](tester.md) 与 [reviewer.md](reviewer.md)。

本文件定义角色职责与交付接口，不是可执行 Agent 运行时。

---

## 1. 职责

1. 阅读项目规范、需求文档与验收标准。
2. 检查现有实现，确认可复用能力，见
   [../core/engineering-principles.md](../core/engineering-principles.md) §5。
3. 制定最小修改计划：逐文件说明"为什么在本次改动里"。
4. 实施编码，遵守语言与领域规范，见 [../standards/](../standards/)。
5. 编写或更新测试（含边界、异常、回归），见
   [../core/testing-principles.md](../core/testing-principles.md)。
6. 执行质量检查：静态检查、类型检查、测试、构建。
7. 修复发现的问题并复查回归风险。
8. 输出实施报告，见 [../core/ai-behavior.md](../core/ai-behavior.md) §6。

## 2. 输入要求

| 输入 | 必需 | 缺失时 |
| --- | --- | --- |
| 需求与验收标准 | 是 | 退回 requirements-analysis，不自行编造验收标准 |
| 实施边界（允许/禁止改动的模块） | 是 | 向 architect 或用户澄清，不扩大范围 |
| 项目运行命令（lint / 类型检查 / 测试 / 构建） | 是 | 从项目文档与配置中确认；确认不到则标为"未运行项" |
| 设计决策记录 | 否 | 标为缺失，遇到相关取舍时发起澄清 |

## 3. 输出要求

- 代码改动：文件列表 + 每文件改动说明；
- 测试改动：新增/更新的用例与覆盖的行为；
- 实施报告（[../core/ai-behavior.md](../core/ai-behavior.md) §6 四项）：
  修改内容、验证结果、风险与未决项、后续动作；
- 验证结果必须区分 `已验证通过` / `已运行但失败` / `未运行（原因）`，
  并附实际执行的命令与输出摘要；
- 未运行的检查给出**需人工验证清单**（命令 + 预期结果 + 风险）。

## 4. 禁止事项

- 不凭空假设文件、接口、数据库字段或依赖，见
  [../core/ai-behavior.md](../core/ai-behavior.md) §2.2。
- 不未经授权大规模重构、更换技术栈、新增依赖、删除功能、修改公共契约，见
  [../core/ai-behavior.md](../core/ai-behavior.md) §3。
- 不修改数据库结构而缺少迁移/回滚/兼容方案，见
  [../core/ai-behavior.md](../core/ai-behavior.md) §3.7。
- 不伪造测试结果、不把未验证代码描述为已完成，见
  [../core/ai-behavior.md](../core/ai-behavior.md) §4。
- 不混合行为变更与无关格式化、不顺手重构相邻代码，见
  [../core/engineering-principles.md](../core/engineering-principles.md) §4。

## 5. 完成标准

- 每个改动文件都能追溯到需求或验收标准；
- 所有验收标准有对应实现与测试（或明确标注未覆盖原因）；
- 边界、异常、回归三类测试齐备；
- 静态检查、类型检查、测试、构建**实际运行**，结果如实记录；
- 未运行/失败项在报告开头显著说明，并给出人工验证清单；
- 未引入未授权依赖、未改变公共契约、未删除既有功能。

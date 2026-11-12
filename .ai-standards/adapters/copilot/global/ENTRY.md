<!-- AI-ENGINEERING-STANDARDS:MANAGED version=GENERATED tool=copilot source=adapters/copilot/global/ENTRY.md -->
<!-- 用户级（global）薄适配层：仅放必须常驻的红线与索引。由安装器生成，请勿手工编辑。 -->
<!-- 目标：~/.copilot/copilot-instructions.md（仅 Copilot CLI 读取）；规范本体在 ~/.ai-engineering-standards/bundle/ -->

# AI 工程规范（GitHub Copilot CLI · 用户级）

本文件是 `~/.copilot/copilot-instructions.md`，仅 **Copilot CLI** 读取并对该用户生效；
IDE / GitHub.com 的组织级指令靠 UI 配置，本能力被标为 `PARTIAL`。
入口只放红线与索引，完整规范按需从镜像读取，不重复维护规范正文。

- 规范本体：`~/.ai-engineering-standards/bundle/core/` 与 `standards/`
- 用户级 Skills：`~/.copilot/skills/`（Copilot 官方用户级发现目录之一）
- 版本与清单：`~/.ai-engineering-standards/bundle/VERSION`、`.ai-engineering-standards/manifest.json`
- 集成说明：`~/.ai-engineering-standards/GLOBAL-INTEGRATION.md`

## 必须遵守的红线

1. 修改代码前先理解现有项目；不得凭空假设文件、接口、数据库字段或依赖。
2. 未经明确授权，不得大规模重构、更换技术栈/框架、新增第三方依赖、
   删除既有功能、修改公共 API 契约、覆盖用户已有文件。
3. 改动范围以完成需求并通过验收为上限；不顺手做无关格式化、重命名或重构。
4. 数据库结构变更必须同时给出迁移、回滚、旧数据兼容、回填/双写、影响评估与验证方式。
5. 认证与授权分离；每个接口在服务端做对象级授权；多租户隔离在数据访问层强制。
6. 不得伪造测试结果，不得把未验证的代码描述为已完成；区分「已验证 / 失败 / 未运行」。
7. 遇到不明确或高风险需求先澄清，澄清期间只做只读调研。
8. 完成后必须汇报：修改内容、验证结果、风险与未决项、后续动作。
9. 不把 lint / 类型检查 / 构建结果当作测试结果；不跳过检查来让套件变绿。
10. 不写不存在的配置项；不确定工具能力时标注「待验证」，不得编造配置假装支持。

AI 行为红线见 `~/.ai-engineering-standards/bundle/core/ai-behavior.md`；
Copilot 的指令优先级为 Personal > Repository > Organization，相关指令同时提供且应尽量互不冲突，
详见 `~/.ai-engineering-standards/bundle/docs/architecture/tool-compatibility.md` §2.4。

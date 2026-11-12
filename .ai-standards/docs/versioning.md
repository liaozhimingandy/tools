# 版本与兼容性

> 版本事实来源：仓库根目录的 `VERSION`（单行语义化版本）。
> 安装后的版本副本：`<target>/.ai-standards/VERSION` 与
> `<target>/.ai-standards/manifest.json` 的 `version` 字段。

---

## 1. 版本号规则

采用 `MAJOR.MINOR.PATCH`：

| 变更 | 版本 | 示例 |
| --- | --- | --- |
| `PATCH` | 修正错别字、补充示例、修复脚本 bug、不新增/删除规则 | `1.0.0 → 1.0.1` |
| `MINOR` | 新增规范文件、新增 Skill、新增工具适配器、新增检查项、扩充既有规则 | `1.0.0 → 1.1.0` |
| `MAJOR` | 删除或改写红线规则、重命名 Skill / `name`、改变安装目标路径、修改 `manifest.json` schema、破坏向后兼容 | `1.0.0 → 2.0.0` |

`VERSION` 必须与 `CHANGELOG.md` 顶部版本号一致；`validate.py` 会检查这一点（ERROR）。

---

## 2. 兼容性承诺

在 `1.x` 期间：

| 对象 | 承诺 |
| --- | --- |
| 安装目标相对路径 | 不变更；变更必须升 MAJOR 并提供迁移说明 |
| `manifest.json` 的 `schema` | 只增字段、不改语义；破坏性变更升 `schema` 并升 MAJOR |
| `SKILL.md` 的 `name` | 不重命名；重命名等价于删除旧 Skill + 新增新 Skill |
| Frontmatter 字段白名单 | 只按 Agent Skills 开放规范演进，不引入工具专有字段 |
| 命令行接口 | `--tool` / `--all` / `--target` / `--dry-run` / `--force` 保持可用；新增参数只能是可选 |
| Python 版本 | 最低 3.10；提高最低版本属 MAJOR |

**不承诺**的事：

- AI 工具官方文档变动后本仓库适配器的长期有效性。各工具会调整路径与字段，
  `docs/tool-adapters.md` 记录核实日期；新版发布前需重新核实。
- Skills 在云会话 / Cowork / 自动化运行中的可见性（这是工具侧行为，见
  [tool-adapters.md](tool-adapters.md) §3、§4）。

---

## 3. 发布流程

```bash
# 1. 确认无 ERROR
python tooling/scripts/validate.py
python -m unittest discover -s tooling/tests -v

# 2. 更新 VERSION 与 CHANGELOG.md（顶部新增版本段落）

# 3. 再跑一次（VERSION 一致性 + 全量测试）
python tooling/scripts/validate.py

# 4. 用全新临时目录做一次真实安装验收
python tooling/scripts/install.py --all --target /tmp/aes-release-check
python tooling/scripts/check.py --target /tmp/aes-release-check

# 5. 提交，标签 v<VERSION>
```

发布说明必须包含：新增/变更/移除的规则清单、需要用户执行的迁移步骤、
以及 `docs/tool-adapters.md` 的重新核实结果（若有工具适配改动）。

---

## 4. 已安装项目如何知道版本

```bash
cat /path/to/your-project/.ai-standards/VERSION
python -c "import json;print(json.load(open('/path/to/your-project/.ai-standards/manifest.json'))['version'])"
```

`manifest.json` 还记录：

- `schema`：清单格式版本；
- `generator`：生成脚本标识；
- `installed_at`：UTC 时间；
- `tools`：本次安装涉及的工具；
- `files`：每个托管文件的 `sha256`、`source`、`owner`。

`check.py` 会把清单版本与源仓库 `VERSION`、以及每个文件的实际哈希逐一比对。
版本不一致时报 WARNING（提示运行 `--force` 更新），哈希不一致时报 ERROR。

---

## 5. 升级与迁移

| 情况 | 处理 |
| --- | --- |
| PATCH / MINOR | `install.py --all --force`，再跑 `check.py`；无需迁移 |
| MAJOR | 先读 `CHANGELOG.md` 的破坏性变更段落；按其中迁移步骤手工处理后，再执行 `--force` |
| 源中已删除的旧文件 | 安装器**不自动删除**，报 `WARNING: stale managed file`；按 [installation.md §11](installation.md) 手工清理 |
| 用户改过托管文件 | `check.py` 报 ERROR（哈希不符）；`--force` 会用源覆盖，覆盖前打印 diff。若想保留改动，请先复制出来 |

---

## 6. 废弃策略

- 规则或 Skill 废弃时先在 `CHANGELOG.md` 标记 `Deprecated`，**保留至少一个 MINOR 周期**。
- 废弃的 Skill 在 `description` 开头加 `[DEPRECATED]` 并指向替代者，避免继续被隐式触发。
- 移除时必须在 MAJOR 版本进行，并给出逐条迁移映射。

---

## 7. 官方规范演进

本仓库跟随 [Agent Skills 开放规范](https://agentskills.io/specification)。
若上游调整 `name`/`description` 约束或新增标准字段：

1. 在 `docs/tool-adapters.md` 记录核实日期与新约束；
2. 更新 `tooling/validators/common.py` 的校验规则与白名单；
3. 更新 `docs/skills-guide.md` §1 的约束表；
4. 补充对应测试；
5. 按 MINOR（兼容放宽）或 MAJOR（收紧导致现有 Skill 不合规）发版。

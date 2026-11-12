# tools

平时开发的工具集。统一以 **Vue 3 + TypeScript + TDesign Vue Next + Tailwind CSS v4 + Vite**（前端）和 **FastAPI**（后端）
构建，通过前端路由分发到各个单页面工具。

> 前端 UI 约定：交互控件一律用 **TDesign Vue Next** 组件（`t-button`/`t-input`/`t-dialog`/
> `t-select`/`t-tag`/`t-alert` 等），**不再手写原生标签样式**；布局与间距用 **Tailwind v4**
> 工具类（配 `@theme` 设计令牌）叠加，少量项目骨架类放 `@layer components` 复用。
> 品牌主题色 **#027AFF**，通过覆盖 `--td-brand-color*` 令牌统一生效（见 `src/styles/theme.css`）。

## 能力总览

- **工具门户**：`/` 列出所有工具；`/safekeep` 是锦囊（零知识密码管理器）。
- **工具注册表**：`tools` 表登记有哪些工具（显示名/图标/启用态/排序/默认配额），是 `tool_id`
  准入的权威数据源，新增工具只加一行、零迁移；全局元数据，不含用户数据、无需 RLS。
- **公共配置表**：多工具共享 `tool_configs` 一张表，用 `(user_sub, tool_id, key)` 逻辑分区，
  与 `tools` 仅软引用。存的是**不透明密文 blob**，支持乐观锁（多端同步防丢失更新）与软删除。
- **统一认证**：不建用户表，用户身份 = Logto 的 `sub`（仅个人维度，无组织级）。鉴权 provider
  可热切换 `passthrough`（**暂时不鉴权**，默认）/ `dev`（X-User-Sub 头）/ `logto`（真实 JWT+JWKS 校验）/ `stub`（测试桩）。
- **云端同步（零知识）**：登录 Logto 后可把密文 blob 手动上传/拉取到云端，多端用相同主密码解锁；
  未配置或离线时自动保持纯本地。详见「云端同步」一节。
- **零知识边界**：加解密、密钥派生全在浏览器 Web Crypto 完成；后端**不接触明文、密钥，
  也不解析密文内容**，只把 `value` 当普通 JSON 原样存取。

## 部署拓扑（当前阶段）

```
浏览器 ──HTTPS──> GitHub Pages（纯静态，/tools/ 子路径，hash 路由）
   │                    │ 构建期内联 VITE_*（API 地址 / Logto 配置）
   │                    └─ 静态资源 /tools/assets/*
   │
   └──HTTPS CORS──> 云服务器容器（FastAPI :8080，域名 + HTTPS 反代）
                          │  TOOLS_AUTH_MODE=passthrough（暂时不鉴权）
                          └─ 外部托管 PostgreSQL（PgBouncer :6432）

   Logto（统一认证）── OAuth2 回调落在 https://<账号>.github.io/tools/（无 #）
```

- **前端**：GitHub Actions 推 `main` 自动 `npm ci && npm run build` 部署到 Pages；
  `base=/tools/`，路由用 hash 模式（`/tools/#/safekeep`），刷新子路径不 404，
  Logto 回调（`redirect_uri` 禁止带 `#`）落到站点根 `/tools/`，挂载前由 `main.ts` 消费 `code/state`。
- **后端**：容器化部署在云主机，对外必须 **域名 + HTTPS**（Pages 是 HTTPS，若后端走 HTTP
  会被浏览器 Mixed Content 拦截）。前置 Nginx/Caddy 等反代终结 TLS 后转到容器 `:8080`。
- **数据库**：外部托管 PostgreSQL，走 PgBouncer 连接池（`:6432`），密码含特殊字符需 URL 编码。
- **鉴权阶段**：后端暂时 `passthrough`——信任前端声明的 `X-User-Sub`，前端自行判断是否已登录，
  有 Logto 登录信息才允许云端同步。**这是过渡态，正式多用户上线前必须切 `logto`**，风险见下文。

## 目录结构

```
tools/
├── README.md                  # 本文件：项目说明与约定
├── .gitignore
├── CODEBUDDY.md               # 项目级记忆入口（规范适配配置生成）
├── .ai-standards/             # 工程规范镜像（唯一规范来源，安装器托管）
├── .codebuddy/                # 项目级规则 + Skills（安装器托管）
├── .github/workflows/
│   └── deploy-pages.yml       # 推 main 自动构建前端并部署 GitHub Pages
├── frontend/                  # Vue 3 SPA（TDesign + Tailwind v4）
│   ├── src/config.ts          # 构建期 VITE_* 统一读取 + 未配置降级
│   ├── src/services/safekeep/ # 加密/存储/业务编排（零 DOM，可 Node 直测）
│   ├── src/services/cloud/    # 云端 blob 契约 / 冲突判据 / HTTP 客户端
│   ├── src/services/auth/     # Logto 浏览器 SDK 封装（回调/登录/登出/sub）
│   ├── src/composables/       # useSafeKeep + useCloudSync（状态 + 副作用编排）
│   ├── src/views/ router/     # 门户 / 锦囊 / 404（hash 路由）
│   ├── src/components/dialogs/# 10 个 TDesign t-dialog（含账号中心 AccountDialog）
│   ├── src/styles/            # theme.css（品牌令牌）+ global.css（Tailwind + 骨架）
│   ├── tests/*.test.ts        # Node 直跑 TS 测试（node --test）
│   └── dist/                  # vite build 产物（gitignore；本地可由后端托管 / Pages 部署）
├── backend/                   # FastAPI
│   ├── Dockerfile             # 非 root 运行时镜像（支持 --build-arg 换基础镜像加速）
│   ├── docker-compose.yml     # init-db 一次性迁移 + api 服务
│   ├── .env.example           # 全部部署变量模板（真实 .env 被 gitignore）
│   ├── .dockerignore
│   ├── app/
│   │   ├── main.py            # 装配 + CORS + 统一错误响应 + 静态托管（/assets 与 /tools/assets）
│   │   ├── configs.py         # 工具注册表 + 公共配置表 API 路由 + /api/auth/mode
│   │   ├── store.py           # ConfigRepository 协议 + Memory / Postgres 实现
│   │   ├── tools_registry.py  # ToolRepository 协议 + Memory / Postgres 实现（全局元数据）
│   │   ├── auth.py            # Principal + passthrough / dev / logto / stub provider
│   │   ├── runtime.py         # 运行期依赖注入（app.state）
│   │   ├── config.py          # 全部环境变量配置（DSN 编码 / PgBouncer / CORS / public_path）
│   │   └── schemas.py         # Pydantic 契约
│   ├── sql/
│   │   ├── 001_tool_configs.sql  # 全新库：tools + tool_configs 建表 + 索引 + RLS + 种子
│   │   ├── 002_app_role.sql      # 最小权限应用角色（RLS 生效前提，部署必备）
│   │   └── 003_migration.sql     # 已有库 v0.2→v0.3 增量升级（加两列 + 建 tools，幂等）
│   ├── requirements*.txt
│   └── tests/
│       ├── test_api.py           # 元信息 + 路由契约 + /tools/ 静态托管回归（unittest）
│       ├── test_configs.py       # 存储 / 鉴权 / API 契约（unittest）
│       ├── test_deploy_config.py # DSN 编码 / PgBouncer / CORS / passthrough / public_path
│       └── pg_integration_check.py  # 真实 PG 集成自检（手动运行）
└── apps/safekeep/             # 【归档】初版零依赖单文件实现 + 测试 + serve.cjs
```

> `apps/safekeep/` 保留为历史基线与对照实现，不再作为主开发路径。主线在 `frontend/` + `backend/`。

## 技术栈与架构约束（项目级）

| 层 | 技术 | 约束 |
| --- | --- | --- |
| 前端 | Vue 3.5 + TypeScript 5.9 + TDesign Vue Next 1.20 + Tailwind CSS v4 + Vite 8 + vue-router 4 | 控件用 TDesign 组件、布局用 Tailwind 工具类；业务在 `services/`、副作用在 `composables/`；`@` 别名同步 vite/tsconfig；品牌色 #027AFF 走 `--td-brand-color*` 覆盖 |
| 后端 | FastAPI + uvicorn（Python 3.14） | 静态托管 + 元信息 + 工具注册表 + 公共配置表 API；不定义任何明文/用户数据表 |
| 存储 | PostgreSQL（可选）/ 内存（默认） | 依赖倒置：`ConfigRepository` + `ToolRepository` 双契约；`value` 不透明 JSONB，不解析 |
| 鉴权 | passthrough（默认，暂不鉴权）/ dev 头 / logto / stub | `user_sub` 唯一可信来源是 provider；**禁止**从 body/path/query 读身份；仅个人维度 |
| 部署 | GitHub Pages + 云主机容器 + 外部 PG | 前端纯静态 HTTPS，后端域名 + HTTPS 反代，PgBouncer 连接池 |
| 依赖 | 精确版本 + lock | 新增依赖须遵循 `ai-engineering-standards` 并经授权 |

### 零知识边界（安全红线）

- 锦囊的加密、解密、密钥派生全部在浏览器 Web Crypto（PBKDF2-SHA256 600k + AES-256-GCM）完成。
- 后端把配置 `value` 当**不透明密文 blob**：只做「可 JSON 序列化 + 大小上限」校验，
  **不解析内部结构、不解密、不记录明文**，也绝不对 `value` 内容建索引。
- `/api/version` 的 `zero_knowledge=true` 是这一契约的机器可读声明。
- 任何把明文/密钥发往后端的改动都属破坏性安全变更，必须走规范评审。

### 多端密文同步模型（已实现）

同一用户在多设备上用**相同主密码**派生相同的 vaultKey（salt/kdf 参数随密文一起存于 blob）；
云端 `tool_configs.value` 只保存 `{account, items, rev}` 这样的密封记录，密钥与恢复码永不上云。
多端并发写用 `expected_revision` 乐观锁：版本不符返回 `409 REVISION_CONFLICT` 并给出当前版本，
前端据此拉取最新 blob 或提示用户，避免静默覆盖。

### 云端同步（前端交互契约）

- **登录与同步解耦**（本轮起）：`logtoEnabled()`（能否登录）与 `apiConfigured()`（后端地址是否就绪）
  是两个独立开关。Logto endpoint/appId 已内联为公开默认值（可 `VITE_LOGTO_*` 覆盖），
  所以**部署即可登录**；后端 `VITE_API_BASE_URL` 未配时，仍可登录、看到账号态，只在真正上传/下载时
  给出「请到 Settings → Variables 添加 VITE_API_BASE_URL」的可操作提示，绝不用一个总开关把登录入口藏掉。
  `cloudEnabled()`（完整同步）= 两者都齐，仅用于内部判定。
- **身份来源**：Logto 的 `sub` 经 `X-User-Sub` 头传给后端（当前 passthrough 阶段），
  作为 `(user_sub, tool_id='safekeep', key='vault')` 分区键；不建 users 表。
- **零知识约束**：云端只存密文，密钥/主密码永不上云。因此「从云端下载解锁」= 下载密文到本机 +
  **仍用创建保险库时的主密码解密**。换设备能恢复的前提是记得主密码（或持有恢复码）。
- **手动同步，保守合并**：账号中心提供「检查云端 / 从云端拉取 / 上传到云端」三个显式动作，
  **不做自动推送、不做自动合并**——零知识库里静默覆盖可能丢失条目，故所有覆盖都要用户二次确认：
  - 上传遇 `stale`（云端被其他端更新）→ 提示先拉取，或「强制上传」覆盖（其他端随后需重新拉取）；
  - 拉取遇云端逻辑版本更旧 → 提示可能丢失本机较新条目，需「强制拉取」确认。
- **拉取后强制锁定**：远端密文覆盖本地后，内存中的明文/密钥全部清空并回到锁定态，
  让用户用（与云端一致的）主密码重新解锁，避免密钥与 salt 错配。
- **传输零知识**：只上传 `{fmt, schema, savedAt, rev, account, items}` 密封 blob；
  `parseCloudBlob` 拒收格式损坏/版本不兼容/条目缺 `iv/ct` 的数据，错误信息不泄漏 value 内容。

### 打开工具：双通道解锁（冷启动 / 换设备）

解锁页提供两条入口，覆盖「本机有库」与「本机无库」两种冷启动：

| 场景 | 本地解锁 | 云端恢复 |
| --- | --- | --- |
| `welcome`（本机无库，如新设备 / 清了浏览器数据） | 创建保险库 / 从加密备份导入 | 「登录并从云端恢复」→ 下载密文到本机 → 主密码解锁 |
| `locked`（本机已有库） | 主密码 / 恢复码解锁 | 「从云端下载并恢复」→ 二次确认覆盖 → 主密码解锁 |

**登录回跳续做**（OAuth 回调落站点根、hash 路由无 fragment 带来的额外链路）：
1. 点云端恢复时若未登录 → `markRestoreIntent()` 在 sessionStorage 记一条**带 TTL（10 分钟）**的意图；
2. 跳转 Logto，`redirect_uri` = 站点根 `https://<账号>.github.io/tools/`（须在 Logto 后台加白名单）；
3. 回调落地 → `main.ts` 挂载前消费 `code/state`，并据意图把 hash 定位回 `#/safekeep`；
4. `useSafeKeep.onMounted` **仅当「本次刚完成 OAuth 回调」+「意图未过期」+「确实已登录」三者同时成立**
   才自动拉一次云端并回到锁定态；普通刷新/首次打开绝不触发，杜绝静默覆盖；
5. 意图消费一次即清除（幂等），过期/损坏/时钟回拨一律作废并清理。

## 数据模型（v0.3 定稿）

两张表，`tools` 是全局元数据（无 RLS），`tool_configs` 是用户数据（RLS 隔离），
通过 `tool_id` **软引用**（不建物理外键，兼容 memory/pg 双后端与已下线工具的历史数据）。

| 表 | 字段 | 说明 |
| --- | --- | --- |
| `tools` | `tool_id` (PK) | 工具标识，如 `safekeep`；配置写入的准入键 |
| | `name` / `icon` / `description` | 显示名 / 图标标识 / 一句话描述（供门户渲染） |
| | `enabled` / `sort_order` | 是否启用（禁用即不准入且不下发）/ 门户排序 |
| | `default_max_keys` / `default_max_value_bytes` | 该工具配额覆盖值；`NULL` 表示沿用全局 `TOOLS_MAX_*` |
| | `created_at` / `updated_at` | 时间戳（管理员维护本表，应用只读） |
| `tool_configs` | `id` (PK) / `user_sub` / `tool_id` / `key` | 内部行号 / Logto sub / 工具 / 配置键；`(user_sub, tool_id, key)` 组合唯一 |
| | `value` (JSONB) | 不透明密文 blob，后端不解析 |
| | `schema_version` (INT, ≥1, 默认 1) | **value 内部结构版本**，供前端加密格式演进 |
| | `updated_by_device` (TEXT, 可空) | 最近写入的设备/客户端标识（明文元数据，≤128 字符） |
| | `revision` (BIGINT, ≥1) / `created_at` / `updated_at` / `deleted_at` | 并发版本 / 时间戳 / 软删墓碑 |

**两个"版本"务必分清**：`revision` 是**整行**的乐观锁版本（每次写 +1，CAS 用）；
`schema_version` 是 **value 内部结构**的版本（前端自己的加密格式/字段布局演进用）。
后端不解析 value，仅原样透传 `schema_version`，二者正交、互不干扰。

> **隐私提示**：`updated_by_device` 是**可选的明文元数据**（非用户密钥、不属于 value），
> 仅用于多端冲突排障。零知识约束保护的是 `value` 内容；若前端不传，该字段为 `NULL`，
> 不影响任何功能。对设备标识敏感的场景可留空或传匿名化标识。

**工具准入双重门（AND）**：`tool_id` 必须①在 `tools` 表中存在且 `enabled`，
②（若配置了）在 `TOOLS_TOOL_IDS` 环境变量白名单内。禁用/未注册工具一律 `404`，不泄露存在性。

## 工具注册表与配置 API

身份走 `Authorization`（logto）或 `X-User-Sub`（dev）；**无用户信息入参**。
完整 OpenAPI 见启动后 `/docs`。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/v1/tools` | 列出启用中的工具（注册表；需鉴权，无用户数据） |
| `GET` | `/api/v1/tools/{tool_id}` | 单个工具元信息（禁用/未注册 → 404） |
| `GET` | `/api/v1/configs/{tool_id}` | 列出当前用户该工具下全部配置（`?include_deleted=true` 含墓碑） |
| `GET` | `/api/v1/configs/{tool_id}/{key}` | 取单条，响应带 `ETag: W/"<rev>"` |
| `PUT` | `/api/v1/configs/{tool_id}/{key}` | UPSERT；body `{value, expected_revision, schema_version?, updated_by_device?}`，首次创建 `expected_revision=0` |
| `DELETE` | `/api/v1/configs/{tool_id}/{key}?expected_revision=N` | 软删除（保留同步墓碑） |
| `GET` | `/api/v1/configs/{tool_id}/_quota` | 配额使用情况（工具覆盖值优先于全局默认） |
| `GET` | `/api/auth/mode` | 当前鉴权模式与风险提示（`passthrough`/dev/stub 标 `secure=false`） |

错误统一形状 `{"error": "<CODE>", "message": "..."}`；常见码：
`UNAUTHORIZED`(401)、`NOT_FOUND`(404)、`REVISION_CONFLICT`/`QUOTA_EXCEEDED`(409)、
`INVALID_TOOL_ID`/`INVALID_KEY`(400)、`VALUE_TOO_LARGE`(413)、`VALIDATION_ERROR`(422)。

## 环境变量

### 后端（运行期，写入 gitignore 的 `backend/.env`）

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `TOOLS_HOST` / `TOOLS_PORT` | `127.0.0.1` / `8080` | 监听地址；容器部署须设 `0.0.0.0` |
| `TOOLS_STORE` | `memory` | `memory`（默认，零依赖）\| `postgres`（需 DSN） |
| `TOOLS_DATABASE_URL` | 空 | 完整 PG DSN，优先级最高；密码含特殊字符须自行 URL 编码 |
| `TOOLS_PG_HOST` / `PORT` / `NAME` / `USER` / `PASSWORD` / `SSLMODE` | 空 | 分散变量，由 `config.py` 组装 DSN 并对凭据百分号编码（**推荐**，避免密码里的 `@` 被误解析）|
| `TOOLS_PG_PREPARE_THRESHOLD` | `off` | PgBouncer(6432) 事务池默认关自动 prepare；`5` 等整数可重开 |
| `TOOLS_PG_POOL_MAX` / `CONNECT_TIMEOUT` | `8` / `10` | 连接池上限 / 连接超时（秒） |
| `TOOLS_AUTH_MODE` | `passthrough` | `passthrough`（**暂不鉴权**）\| `dev` \| `logto`（JWT）\| `stub` |
| `TOOLS_DEV_AUTH_HEADER` | `X-User-Sub` | passthrough / dev 信任的头 |
| `TOOLS_PASSTHROUGH_DEFAULT_SUB` | `anonymous` | 请求缺身份头时的归属槽位 |
| `LOGTO_ISSUER` / `LOGTO_AUDIENCE` / `LOGTO_JWKS_URL` | 空 | 切 `logto` 时的三件套；任一空即 fail-closed 拒绝所有请求 |
| `TOOLS_CORS_ORIGINS` | 空 | 逗号分隔的跨域白名单（Pages 源 + 自定义域），去尾斜杠；空=仅同源 |
| `TOOLS_PUBLIC_PATH` | `/tools/` | 后端托管 dist 时的公网基路径，**须与前端 `VITE_PUBLIC_PATH`/`base` 一致**；根部署设 `/` |
| `TOOLS_MAX_VALUE_BYTES` | `524288` | 单条 value 大小全局默认（512 KiB）；可被 `tools.default_max_value_bytes` 覆盖 |
| `TOOLS_MAX_KEYS` | `200` | 单用户单工具 key 数全局默认；可被 `tools.default_max_keys` 覆盖 |
| `TOOLS_TOOL_IDS` | 空 | 工具 id 白名单（逗号分隔），空表示不限制；是注册表准入之上的第二道硬限制 |

### 前端（构建期，GitHub Actions Variables 或本地 `VITE_*`）

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `VITE_PUBLIC_PATH` | `/tools/` | Vite `base`；仓库名不是 `tools` 或绑自定义域根路径时改这里 |
| `VITE_API_BASE_URL` | 空 | **唯一需你填的项**：后端 HTTPS 根（不含尾斜杠）；空=可登录但暂不能上传/下载 |
| `VITE_LOGTO_ENDPOINT` | `https://account.alsoapp.com` | Logto endpoint，已内联公开默认值；换租户才需覆盖 |
| `VITE_LOGTO_APP_ID` | `0z2t6jrnf4z9lzy4miusg` | Logto 应用 ID（Public Client，非密钥），已内联；换应用才需覆盖 |
| `VITE_LOGTO_RESOURCE` | 空 | 可选，API resource（拿 access token 的 audience） |
| `VITE_LOGTO_REDIRECT_URI` | 自动拼站点根 | OAuth 回调白名单地址（**无 `#`**），如 `https://<账号>.github.io/tools/`；一般无需填 |
| `VITE_LOGTO_POST_LOGOUT_REDIRECT_URI` | 同回调 | 登出回跳 |
| `VITE_LOGTO_SCOPES` | 空 | 逗号分隔的额外 scopes |

> 以上 `VITE_*` 会内联进浏览器 JS，本就公开可见，故用 Actions **Variables**（非 Secret）即可。
> **登录默认开箱可用**：Logto endpoint/appId 已内联（公共客户端标识，官方示例也明文写在前端，
> 不含 secret）；即使一个 `VITE_*` 都不配，部署后也能登录，只是后端地址未填时云端读写会给出提示。
> 加解密与本地功能始终离线可用，绝不白屏。

> **不建 users 表**：`user_sub` 即 Logto `sub`；昵称/头像/邮箱由前端从 Logto 取，后端不落库。

## 部署 A：前端到 GitHub Pages

1. **仓库**：把本项目推到 GitHub（仓库名决定 Pages 子路径；默认 `tools` → `/tools/`，
   若改名须同步设 `VITE_PUBLIC_PATH=/<新名>/`）。本地分支名为 `main`（与工作流触发分支一致）。
2. **开启 Pages**：仓库 `Settings > Pages > Build and deployment > Source` 选 **GitHub Actions**。
3. **配置 Variables**（`Settings > Secrets and variables > Actions > Variables`）：
   - `VITE_API_BASE_URL`：填后端 HTTPS 域名（后端就绪后；见「部署 B」）。**当前唯一必填项**。
   - Logto 三件套已内联默认值，可不填；换租户/应用时才用 `VITE_LOGTO_ENDPOINT` / `VITE_LOGTO_APP_ID` 覆盖。
4. **Logto 后台加回调白名单**（一次性）：在 Logto 控制台该应用 → Redirect URIs 加入
   `https://<账号>.github.io/tools/`（**无 `#`**），Post Logout Redirect URIs 同理。
   否则登录会报 `redirect_uri` 未注册。本地 dev 另加 `http://localhost:5173/`。
5. **自动部署**：推 `main`（或手动 Run workflow）触发 `.github/workflows/deploy-pages.yml`：
   `npm ci` → `npm run build`（含 `vue-tsc` 类型检查）→ 上传 `frontend/dist` → 部署 Pages。
   产物资源路径为 `/tools/assets/*`，路由为 hash（`/tools/#/safekeep`），刷新子路径不 404。

> 工作流只监听 `frontend/**` 与自身变动；改 Actions Variables 后需手动 Run workflow 才重新内联。

## 部署 B：后端到云主机容器

> 真实数据库口令/IP **只写入 gitignore 的 `backend/.env`**，仓库内 `.env.example` 全是占位符；
> 切勿把口令提交进仓库（本仓库会推到 GitHub）。

1. **建库 + 建表**（`init-db` 容器会自动做，也可手动执行一次）：
   ```bash
   PGPASSWORD='<pass>' psql -h <host> -p 6432 -U tools -d tools -v ON_ERROR_STOP=1 -f sql/001_tool_configs.sql
   ```
   > `001` 幂等，已含完整表结构 + 索引 + 种子 + `FORCE ROW LEVEL SECURITY`。
   > ⚠️ 应用 DSN 必须是**非超级用户、不带 `BYPASSRLS`** 的角色（本部署 `tools` 账号即满足，
   > RLS 已实测生效）；`postgres` 超级用户会绕过全部行级安全策略。
   > `002_app_role.sql` / `003_migration.sql` 需要 `CREATEROLE` 并引用 `tools_app` 角色，
   > 本云库账号无该权限，故**默认不执行**；仅「有管理员权限且确有 v0.2 旧库要升级」时手动跑。
2. **填 `.env`**：`cp .env.example .env`，填 `TOOLS_PG_HOST` / `PORT` / `NAME` / `USER` / `PASSWORD`、
   `TOOLS_CORS_ORIGINS=https://<账号>.github.io`（若用自定义域则填该域，**只填 origin、不带路径**）、
   `TOOLS_PUBLIC_PATH`（容器若也托管 dist 才需，与前端一致）。
3. **起容器**：
   ```bash
   docker compose up -d --build
   docker compose logs -f init-db    # 核对 001 建表有无报错
   ```
   `init-db` 幂等执行 `001_tool_configs.sql`（`ON_ERROR_STOP=1`），成功后 `api` 才启动；
   api 以非 root 运行、只读文件系统、`/tmp` 为 tmpfs。
   国内云主机若拉不到 Docker Hub，构建时加：
   `docker compose build --build-arg PYTHON_IMAGE=docker.m.daocloud.io/library/python:3.14-slim`
   （在 compose 的 `build.args.PYTHON_IMAGE` 配同值亦可，见 `Dockerfile` 顶部说明）。
4. **域名 + HTTPS 反代（必需）**：Pages 是 HTTPS，浏览器会拦截其到 `http://` 后端的请求
   （Mixed Content）。用 Nginx/Caddy/云负载均衡在后端容器前终结 TLS，把
   `https://api.<你的域>` 反代到 `127.0.0.1:8080`，并放通 `X-User-Sub`、`Authorization` 头与
   `OPTIONS` 预检。前端 `VITE_API_BASE_URL` 填这个 HTTPS 域名。

## 部署 C：Logto 配置

1. 在 Logto 控制台建 **Single Page App**，把**所有需要登录的部署地址**逐一加入 Redirect URI
   与 Post-logout URI 白名单（**必须无 `#`**，Logto 对 redirect_uri 做精确匹配）：
   - 线上：`https://<账号>.github.io/tools/`（绑自定义域则用 `https://<域>/tools/`）
   - 本地联调：`http://localhost:5173/tools/`
   - ⚠️ 实测：**`localhost` 与 `127.0.0.1` 是两个不同 origin**，`/` 与 `/tools/` 也是两个不同 URI。
     只配 `http://localhost:5173/` 而页面落在 `/tools/`，会直接报
     `oidc.invalid_redirect_uri`。本地联调务必用 `http://localhost:5173/tools/` 打开页面。
   - ⚠️ 曾出现「为本地测试把线上 URI 从白名单删掉」导致线上登录失败的情况；
     Logto 支持多 URI，**新增本地地址时不要删线上地址**。可在改完后用
     `GET <endpoint>/oidc/auth?...&redirect_uri=<候选>` 探测：303 跳转登录页=已允许，400=未配置。
2. endpoint / app id 已内联为公开默认值（非密钥），可用 Actions Variables
   （`VITE_LOGTO_ENDPOINT` / `VITE_LOGTO_APP_ID`）覆盖；`VITE_LOGTO_REDIRECT_URI` 建议显式固定，
   避免不同 host 打开时自动拼装出未登记的地址。
3. 当前阶段前端 Logto 只用来拿 `sub` 作云端归属；后端仍是 `passthrough` 不验签。
   正式切后端验签时，另建 API resource 并把 issuer/audience/JWKS 三件套填入后端 `.env`，
   设 `TOOLS_AUTH_MODE=logto`（任一空即 fail-closed 拒绝全部请求）。

### ⚠️ passthrough 风险（正式上线前必须处理）

- 后端**不校验身份**：任何人可伪造 `X-User-Sub` 读写/覆盖/删除他人云端密文。
- `value` 是零知识密文，他人**无法解密**，但**完整性与可用性不受保护**（可被覆盖/删除）。
- 风险通过 `GET /api/auth/mode` 机器可读暴露（`secure=false` + `warning`）。
- 迁移路径：切 `TOOLS_AUTH_MODE=logto` 并配齐三件套，此时 `sub` 来自校验过的 JWT，客户端无法伪造。
  在此之前，请引导用户同时保留本地加密备份（`导出备份`）。

## 本地运行

### 前端（开发）

```powershell
cd frontend
npm install
npm run dev          # Vite 开发服务器
```

### 前端（构建）+ 后端（托管，默认内存存储 + passthrough 不鉴权）

```powershell
cd frontend
npm run build        # 先类型检查，再输出到 frontend/dist
cd ..\backend
python -m pip install -r requirements.txt
python -m app.main   # 默认 http://127.0.0.1:8080，仅本机
```

浏览器打开 `http://127.0.0.1:8080/`（门户）或 `http://127.0.0.1:8080/#/safekeep`（锦囊）。
路由是 **hash 模式**，路径带 `#`；后端静态托管已同时挂载 `/assets` 与 `/tools/assets`，
与 Vite `base` 对齐（本地默认 `TOOLS_PUBLIC_PATH=/tools/`），直接跑后端也能正确加载 JS，不再空白页。
调用配置 API 时带 `-H "X-User-Sub: alice"`（passthrough / dev 模式）。

> 纯前端开发也可 `npm run dev`（Vite 开发服务器，默认挂 `/tools/` 前缀，浏览器开
> `http://localhost:5173/tools/`）。未配 `VITE_*` 时云端同步入口自动隐藏，纯本地可用。

### 后端接真实 PostgreSQL（本机直跑，不走容器）

```powershell
# 1. 全新库：用管理员连接建表（tools + tool_configs）+ 建最小权限应用角色
#    端口 6432 通常是 PgBouncer 连接池；本机直连可用真实 PG 端口 5432
$env:PGPASSWORD = "<admin-pass>"
psql "postgresql://<admin>@<host>:5432/<db>" -v ON_ERROR_STOP=1 -f backend/sql/001_tool_configs.sql
psql "postgresql://<admin>@<host>:5432/<db>" -v ON_ERROR_STOP=1 -f backend/sql/002_app_role.sql  # 记得 ALTER ROLE 改强密码
# 已有 v0.2 旧库升级到 v0.3（加 schema_version/updated_by_device + 建 tools + 种子，幂等）：
# psql "postgresql://<admin>@<host>:5432/<db>" -v ON_ERROR_STOP=1 -f backend/sql/003_migration.sql

# 1b. 维护工具注册表（管理员 DSN 写入；应用角色只有 SELECT 权限）
#     psql "<admin-dsn>" -c "INSERT INTO tools(tool_id,name,icon,description,sort_order,default_max_keys) VALUES('mytool','我的工具','file','描述',20,50);"
#     psql "<admin-dsn>" -c "UPDATE tools SET enabled=FALSE WHERE tool_id='mytool';"

# 2. 用分散变量（推荐：密码含 @ 等字符会自动编码）+ passthrough 启动
$env:TOOLS_STORE = "postgres"
$env:TOOLS_PG_HOST = "<host>"; $env:TOOLS_PG_PORT = "6432"
$env:TOOLS_PG_NAME = "tools"; $env:TOOLS_PG_USER = "tools_app"; $env:TOOLS_PG_PASSWORD = "<强密码>"
$env:TOOLS_PG_PREPARE_THRESHOLD = "off"   # PgBouncer 事务池必关自动 prepare
$env:TOOLS_AUTH_MODE = "passthrough"
python -m app.main
# 正式切验签：TOOLS_AUTH_MODE=logto + LOGTO_ISSUER/AUDIENCE/JWKS_URL（见「部署 C」）
```

> ⚠️ **DSN 必须用非特权应用角色**：`postgres` 超级用户带 `BYPASSRLS`，会绕过全部 RLS 策略。
> 这一点已由真实 PG 集成自检实测确认。密码含 `@` 时**不要**裸拼进 `TOOLS_DATABASE_URL`
> （会被当成 host 分隔符），改用 `TOOLS_PG_PASSWORD` 分散变量由 `config.py` 编码。
>
> **云托管库实测补充**：若只拿到有 `CREATEDB`、无 `CREATEROLE` 的应用账号（本部署即如此），
> **只跑 `001_tool_configs.sql` 即可**：它已含完整表结构 + `FORCE ROW LEVEL SECURITY`，
> 用非超级用户、不带 `BYPASSRLS` 的账号直连时 RLS 已实测生效（两个不同 `app.user_sub`
> 各只能看到自己的行）。`002_app_role.sql` 的 `CREATE ROLE`、`003_migration.sql` 末尾的
> `GRANT ... TO tools_app` 在该权限下会失败，故 `docker-compose` 的 `init-db` 已改为只跑 001。
> 只有「有管理员权限且确有 v0.2 旧库要升级」时才需手动执行 002/003。

### 本地端到端联调（前端 dev + 真实云数据库）

两个配置文件均**已被 `.gitignore` 忽略**，真实口令绝不入库：

```powershell
# frontend/.env.development.local（仅 `npm run dev` 的 development 模式加载）
#   ⚠️ 必须用「带 mode 后缀」的文件名：Vite 的 .env.local 在 build 时也会加载，
#      会把 localhost:8080 / localhost:5173 打进生产产物——线上会去请求用户本机
#      并被 Mixed Content 拦截，登录回调也会跳回 localhost。已实测并修正。
#   VITE_API_BASE_URL=http://localhost:8080
#   VITE_LOGTO_REDIRECT_URI=http://localhost:5173/tools/
#   VITE_LOGTO_POST_LOGOUT_REDIRECT_URI=http://localhost:5173/tools/
#
# backend/.env（FastAPI 只读 os.environ，需显式注入，没有 dotenv 自动加载）
Get-Content backend/.env | ForEach-Object {
  $l = $_.Trim()
  if ($l -and -not $l.StartsWith('#') -and $l.Contains('=')) {
    $i = $l.IndexOf('='); Set-Item "env:$($l.Substring(0,$i).Trim())" $l.Substring($i+1).Trim()
  }
}
cd backend; $env:PYTHONPATH = (Resolve-Path ".deps").Path; python -m app.main
# 另开终端：cd frontend; npm run dev
# 浏览器务必用 http://localhost:5173/tools/ 打开（不是 127.0.0.1）
```

关键配置：`TOOLS_STORE=postgres`、`TOOLS_PG_*` 指向云库、`TOOLS_AUTH_MODE=passthrough`、
`TOOLS_CORS_ORIGINS=http://localhost:5173`（**本地 5173 → 8080 是跨源，必须放行**）。

已完成的实测（真实云数据库 + 真实浏览器）：

| 环节 | 结果 |
| --- | --- |
| 建库 / `001` 迁移 / RLS 隔离 | 通过（alice 与 bob 互相不可见） |
| 后端 API 端到端（17 项） | 全部通过：404→PUT 创建→GET 密文原样往返→409 CAS→更新→隔离→配额→413→软删除墓碑 |
| 浏览器真实跨域 GET/PUT/DELETE | 通过（响应带 `Access-Control-Allow-Origin`） |
| 欢迎页双通道 UI | 通过：本地创建 / 登录并从云端恢复 |
| 登录跳转 + 恢复意图 | 通过：`signInSession.redirectUri` 正确、意图写入并带 10 分钟 TTL |
| 回调落地路由归位 | 通过：`#/safekeep`，意图被消费；伪造 code 不会误触发覆盖 |

> 调试经验：本机若设了 `HTTP_PROXY`，用 Python/httpx 测本地接口须 `trust_env=False`，
> 否则请求被代理转发成绝对 URI，后端日志出现 `GET http%3A//...` 并全部 404。
> 浏览器不受影响（WinINET 代理关闭 + `<local>` 绕过）。

## 测试与验证

```powershell
# 前端：加密核心 KAT + 全链路（Node 直跑 TS，无需编译）
cd frontend
node --test tests/*.test.ts
npm run typecheck    # vue-tsc --noEmit -p tsconfig.app.json（必须显式 -p）
npm run build

# 后端：契约测试（unittest，内存存储 + stub 鉴权，无需 PG/JWT 租户）
cd backend
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -p "test_*.py" -v
# 若依赖装在仓库内 .deps（pip --target），需显式：
#   $env:PYTHONPATH = (Resolve-Path ".deps").Path ; python -m unittest discover -s tests -p "test_*.py"

# 后端：真实 PG 集成自检（可选；需 Docker 起 postgres:16-alpine 并执行 001/002/003）
# 覆盖：新两列真实落库往返、tools 注册表准入/禁用/最小权限、RLS 兜底、JSONB 原样存取
python tests/pg_integration_check.py

# 容器配置渲染自检（需本机有 docker compose；.env 可用占位值）
cd backend ; docker compose --env-file .env config
```

**当前基线**：前端 `53/53` 单测、`vue-tsc` 类型检查、`vite build` 全绿；
后端 `73/73` unittest 全绿；`docker compose config` 渲染通过；
**真实云数据库端到端 17/17 通过**（见「本地端到端联调」表格）。

### 需在有外网/真实凭据的环境人工验证

- [x] **真实 PG 连接 + 迁移 + RLS**：已连云库、建 `tools` 库、跑 `001`、
      实测两个 `app.user_sub` 互相不可见。云账号无 `CREATEROLE`，故 `init-db` 已改为只跑 001。
- [x] **GitHub Actions 部署**：推 `main` 后 Pages 产物 `/tools/` 已可访问、资源 200、hash 路由刷新不 404。
      （首次部署需在 Settings > Pages 把 Source 选为 GitHub Actions，已实测为唯一阻塞点。）
- [x] **本地登录跳转 + 回调归位**：Edge 实测点击「登录并从云端恢复」跳到 Logto 登录页、
      `signInSession.redirectUri` 正确、恢复意图写入、伪造回调落地后归位 `#/safekeep` 且不误覆盖。
- [ ] **容器镜像构建**：`docker compose up -d --build`。本环境无法拉取 Docker Hub 镜像
      （`python:3.14-slim`），已加 `ARG PYTHON_IMAGE` 支持国内镜像加速，需云主机实测。
- [ ] **HTTPS 反代 + CORS**：域名证书、反代放通自定义头/OPTIONS 预检、Pages 源在
      `TOOLS_CORS_ORIGINS` 白名单内，浏览器无 Mixed Content / CORS 报错。
- [ ] **线上 Logto 回调白名单**（一次性，网页端）：⚠️ 实测当前白名单只剩
      `http://localhost:5173/tools/`，**线上 `https://<账号>.github.io/tools/` 已被移除**，
      线上登录会报 `oidc.invalid_redirect_uri`。请把线上地址加回 Redirect URIs 与
      Post Logout Redirect URIs（保留本地地址，二者可共存）。
- [ ] **真实 Logto 账号完成一次登录**：本环境无账号凭据，只验证到跳转与回调归位，
      需本人用真实账号登录，确认 `sub` 落地、登出正常。
- [ ] **填后端地址后端到端云同步**：先在 Settings > Variables 配 `VITE_API_BASE_URL` 重部署，
      再验「检查云端 → 上传 → 另一设备拉取 → 主密码重新解锁」密文不失真，
      冲突时 `stale`/强制覆盖提示符合预期。
- [ ] **冷启动云端恢复全链路（真实登录）**：新设备/清浏览器后，解锁页点「登录并从云端恢复」→
      Logto 跳转 → 回调落站点根 → 自动回 `#/safekeep` 并拉一次密文 → 主密码解锁；
      验证普通刷新不会重复拉取/覆盖（恢复意图仅消费一次、TTL 10 分钟）。

## 工程规范与版本

本项目遵循唯一工程规范来源 `ai-engineering-standards`，通过 WorkBuddy 适配配置安装，
**不在本仓库重复维护**。

> 状态：适配配置已安装（v1.0.0，scope=project）：`.ai-standards/` 镜像（120 托管文件，
> SHA-256 校验通过）、`CODEBUDDY.md`、`.codebuddy/rules/`、5 个 Skill。
> 归属与版本见 `.ai-standards/manifest.json`。应用版本见后端 `/api/version`
> （`app_version` 本工具集 / `standards_version` 已装规范，统一记录）。
> 升级：`python E:\temp\a\ai-engineering-standards\tooling\scripts\install.py --tool workbuddy --scope project --target E:\temp\tools --force`

## 开发流程

按规范定义的阶段推进：
`project-analysis → requirements-analysis → architecture-design → software-development → code-review`

提交前实际运行：类型检查、单元测试、构建（前端）；契约测试 + （可选）PG 集成自检（后端），并记录结果。

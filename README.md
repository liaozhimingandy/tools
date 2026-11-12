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

- **软门禁**：只有 `VITE_API_BASE_URL` 和 `VITE_LOGTO_*` 配齐、且用户已登录 Logto，
  才允许云端同步；否则界面显示「仅本地」，加解密照常离线可用，绝不白屏。
- **身份来源**：Logto 的 `sub` 经 `X-User-Sub` 头传给后端（当前 passthrough 阶段），
  作为 `(user_sub, tool_id='safekeep', key='vault')` 分区键；不建 users 表。
- **手动同步，保守合并**：账号中心提供「检查云端 / 从云端拉取 / 上传到云端」三个显式动作，
  **不做自动推送、不做自动合并**——零知识库里静默覆盖可能丢失条目，故所有覆盖都要用户二次确认：
  - 上传遇 `stale`（云端被其他端更新）→ 提示先拉取，或「强制上传」覆盖（其他端随后需重新拉取）；
  - 拉取遇云端逻辑版本更旧 → 提示可能丢失本机较新条目，需「强制拉取」确认。
- **拉取后强制锁定**：远端密文覆盖本地后，内存中的明文/密钥全部清空并回到锁定态，
  让用户用（与云端一致的）主密码重新解锁，避免密钥与 salt 错配。
- **传输零知识**：只上传 `{fmt, schema, savedAt, rev, account, items}` 密封 blob；
  `parseCloudBlob` 拒收格式损坏/版本不兼容/条目缺 `iv/ct` 的数据，错误信息不泄漏 value 内容。

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
| `VITE_API_BASE_URL` | 空 | 后端 HTTPS 根（不含尾斜杠）；空=云端同步关闭 |
| `VITE_LOGTO_ENDPOINT` | 空 | Logto endpoint，如 `https://<tenant>.logto.app` |
| `VITE_LOGTO_APP_ID` | 空 | Logto 应用 ID |
| `VITE_LOGTO_RESOURCE` | 空 | 可选，API resource（拿 access token 的 audience） |
| `VITE_LOGTO_REDIRECT_URI` | 自动 | OAuth 回调白名单地址（**无 `#`**），如 `https://<账号>.github.io/tools/` |
| `VITE_LOGTO_POST_LOGOUT_REDIRECT_URI` | 同回调 | 登出回跳 |
| `VITE_LOGTO_SCOPES` | 空 | 逗号分隔的额外 scopes |

> 以上 `VITE_*` 会内联进浏览器 JS，本就公开可见，故用 Actions **Variables**（非 Secret）即可。
> 任一 `VITE_LOGTO_*` 或 `VITE_API_BASE_URL` 缺失 → 前端自动降级纯本地，不白屏。

> **不建 users 表**：`user_sub` 即 Logto `sub`；昵称/头像/邮箱由前端从 Logto 取，后端不落库。

## 部署 A：前端到 GitHub Pages

1. **仓库**：把本项目推到 GitHub（仓库名决定 Pages 子路径；默认 `tools` → `/tools/`，
   若改名须同步设 `VITE_PUBLIC_PATH=/<新名>/`）。本地分支名为 `main`（与工作流触发分支一致）。
2. **开启 Pages**：仓库 `Settings > Pages > Build and deployment > Source` 选 **GitHub Actions**。
3. **配置 Variables**（`Settings > Secrets and variables > Actions > Variables`）：见上表前端一节，
   至少 `VITE_API_BASE_URL`、`VITE_LOGTO_ENDPOINT`、`VITE_LOGTO_APP_ID`、`VITE_LOGTO_REDIRECT_URI`。
4. **自动部署**：推 `main`（或手动 Run workflow）触发 `.github/workflows/deploy-pages.yml`：
   `npm ci` → `npm run build`（含 `vue-tsc` 类型检查）→ 上传 `frontend/dist` → 部署 Pages。
   产物资源路径为 `/tools/assets/*`，路由为 hash（`/tools/#/safekeep`），刷新子路径不 404。

> 工作流只监听 `frontend/**` 与自身变动；改 Actions Variables 后需手动 Run workflow 才重新内联。

## 部署 B：后端到云主机容器

> 真实数据库口令/IP **只写入 gitignore 的 `backend/.env`**，仓库内 `.env.example` 全是占位符；
> 切勿把口令提交进仓库（本仓库会推到 GitHub）。

1. **建库**（管理员 DSN 执行一次；已在云厂商控制台建好 `tools` 库）：
   ```bash
   PGPASSWORD='<admin-pass>' psql -h <host> -p 6432 -U <admin> -d tools -v ON_ERROR_STOP=1 -f sql/001_tool_configs.sql
   PGPASSWORD='<admin-pass>' psql -h <host> -p 6432 -U <admin> -d tools -v ON_ERROR_STOP=1 -f sql/002_app_role.sql   # 记得 ALTER ROLE 改强密码
   # 老库升级（幂等）：-f sql/003_migration.sql
   ```
   > ⚠️ 应用 DSN 必须用 `002_app_role.sql` 建的**非特权角色**：`postgres` 超级用户带 `BYPASSRLS`
   > 会绕过全部行级安全策略（已由真实 PG 集成自检确认）。
2. **填 `.env`**：`cp .env.example .env`，填 `TOOLS_PG_HOST` / `PORT` / `NAME` / `USER` / `PASSWORD`、
   `TOOLS_CORS_ORIGINS=https://<账号>.github.io`（若用自定义域则填该域，**只填 origin、不带路径**）、
   `TOOLS_PUBLIC_PATH`（容器若也托管 dist 才需，与前端一致）。
3. **起容器**：
   ```bash
   docker compose up -d --build
   docker compose logs -f init-db    # 核对迁移有无真实报错（脚本容忍重复执行/禁建角色的错误）
   ```
   `init-db` 幂等执行 `001~003`，成功后 `api` 才启动；api 以非 root 运行、只读文件系统、`/tmp` 为 tmpfs。
   国内云主机若拉不到 Docker Hub，构建时加：
   `docker compose build --build-arg PYTHON_IMAGE=docker.m.daocloud.io/library/python:3.14-slim`
   （在 compose 的 `build.args.PYTHON_IMAGE` 配同值亦可，见 `Dockerfile` 顶部说明）。
4. **域名 + HTTPS 反代（必需）**：Pages 是 HTTPS，浏览器会拦截其到 `http://` 后端的请求
   （Mixed Content）。用 Nginx/Caddy/云负载均衡在后端容器前终结 TLS，把
   `https://api.<你的域>` 反代到 `127.0.0.1:8080`，并放通 `X-User-Sub`、`Authorization` 头与
   `OPTIONS` 预检。前端 `VITE_API_BASE_URL` 填这个 HTTPS 域名。

## 部署 C：Logto 配置

1. 在 Logto 控制台建 **Single Page App**，把站点根（无 `#`）加入 Redirect URI 与 Post-logout URI
   白名单：`https://<账号>.github.io/tools/`（绑自定义域则用 `https://<域>/tools/`）。
2. 把 endpoint / app id 填入 Actions Variables（`VITE_LOGTO_ENDPOINT` / `VITE_LOGTO_APP_ID`），
   与前者一起重新 Run workflow。
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

**当前基线**：前端 `42/42` 单测、`vue-tsc` 类型检查、`vite build` 全绿；
后端 `73/73` unittest 全绿；`docker compose config` 渲染通过（临时 `.env` 验证后已删除）。

### 需在有外网/真实凭据的环境人工验证（本沙箱未完成）

- [ ] **真实 PG 连接**：`backend/.env` 里的 PgBouncer 地址能否连上、`tools` 库权限、
      `001~003` 迁移落库、`tools_app` 非特权角色 RLS 生效。本沙箱未连远程库。
- [ ] **容器镜像构建**：`docker compose up -d --build`。本沙箱无法拉取 Docker Hub 镜像
      （`python:3.14-slim`），已加 `ARG PYTHON_IMAGE` 支持国内镜像加速，需云主机实测。
- [ ] **HTTPS 反代 + CORS**：域名证书、反代放通自定义头/OPTIONS 预检、Pages 源在
      `TOOLS_CORS_ORIGINS` 白名单内，浏览器无 Mixed Content / CORS 报错。
- [ ] **Logto 真登录回环**：`/tools/` 回调 `code/state` 被 `main.ts` 消费、`sub` 正确落地，
      登录/登出跳转正常；回调 URI 已在 Logto 控制台加白名单。
- [ ] **端到端云同步**：登录后「检查云端 → 上传 → 另一设备拉取 → 主密码重新解锁」密文不失真，
      冲突时 `stale`/强制覆盖提示符合预期。
- [ ] **GitHub Actions 部署**：推 `main` 后 Pages 产物 `/tools/` 可访问、资源 200、刷新子路径不 404。

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

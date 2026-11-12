"""后端配置：路径与版本来源集中管理，不散落在代码里。

所有部署期可变项走环境变量，便于「同一镜像 + 不同 env」在容器里运行。
安全默认：鉴权 passthrough（暂时不鉴权）+ 存储 memory，开箱即用、无外部依赖；
生产：TOOLS_AUTH_MODE=logto + TOOLS_STORE=postgres + 填 DSN 与 Logto 三件套。
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote

# 目录结构：
#   tools/backend/app/      本文件
#   tools/backend/          BACKEND_DIR
#   tools/                  PROJECT_ROOT
#   tools/frontend/dist/    Vite 构建产物（由 FastAPI 托管）
BACKEND_DIR: Path = Path(__file__).resolve().parent.parent
PROJECT_ROOT: Path = BACKEND_DIR.parent
DIST_DIR: Path = PROJECT_ROOT / "frontend" / "dist"
STANDARDS_VERSION_FILE: Path = PROJECT_ROOT / ".ai-standards" / "VERSION"

APP_VERSION = "0.4.0"
# 规范源未提供时的兜底；真实值由 .ai-standards/VERSION 覆盖
FALLBACK_STANDARDS_VERSION = "unknown"


def read_standards_version() -> str:
    """读取已安装适配配置里的规范版本（跨空间统一版本记录）。

    仅返回版本字符串，不暴露路径内容；文件缺失时回退到 unknown。
    """
    try:
        value = STANDARDS_VERSION_FILE.read_text(encoding="utf-8").strip()
        return value or FALLBACK_STANDARDS_VERSION
    except (OSError, UnicodeDecodeError):
        return FALLBACK_STANDARDS_VERSION


def dist_index_exists() -> bool:
    """前端构建产物是否就绪。"""
    index = DIST_DIR / "index.html"
    return index.is_file()


def bind_host() -> str:
    """监听地址。本地默认仅 127.0.0.1；容器部署须显式设 TOOLS_HOST=0.0.0.0。"""
    return os.environ.get("TOOLS_HOST", "127.0.0.1").strip() or "127.0.0.1"


def bind_port() -> int:
    raw = os.environ.get("TOOLS_PORT", "8080")
    try:
        return int(raw)
    except ValueError:
        return 8080


# --------------------------------------------------------------------------- #
# 前端公网基路径（后端本地托管 dist 时才用到；Pages 部署由 GitHub Pages 负责静态）
# --------------------------------------------------------------------------- #

def public_path() -> str:
    """前端部署的公网基路径，必须与 Vite `base` / `VITE_PUBLIC_PATH` 保持一致。

    统一规范成「首尾都带斜杠」形式：'/tools/' 或 '/'。
    默认 '/tools/'（GitHub Pages 项目站点子路径；本仓库名 tools）。

    为什么后端要关心：本地「npm run build + python -m app.main」模式下由 FastAPI
    托管 dist，而 base=/tools/ 会让 index.html 以绝对路径请求 /tools/assets/*.js。
    若只挂 /assets，这些请求会落到 SPA 回退拿到 index.html（HTML 被当 JS 解析 → 空白页）。
    后端据此把同一份 assets 同时挂到 /assets 与 /tools/assets。
    """
    raw = os.environ.get("TOOLS_PUBLIC_PATH", "/tools/").strip()
    if not raw or raw == "/":
        return "/"
    if not raw.startswith("/"):
        raw = "/" + raw
    if not raw.endswith("/"):
        raw += "/"
    return raw


def public_prefix() -> str:
    """去掉首尾斜杠的基路径段，供 SPA 回退剥离前缀，如 'tools'；根部署返回 ''。"""
    return public_path().strip("/")


def assets_mount_paths() -> list[str]:
    """dist/assets 需要挂载的全部 URL 前缀（去重、保序）。

    始终含 '/assets'（兼容 base='/' 与历史构建）；base 非根时再补 '/tools/assets'。
    """
    paths = ["/assets"]
    base = public_path()
    if base != "/":
        candidate = base.rstrip("/") + "/assets"
        if candidate not in paths:
            paths.append(candidate)
    return paths


# --------------------------------------------------------------------------- #
# 公共配置表（多工具共享）与鉴权配置
# --------------------------------------------------------------------------- #

def store_backend() -> str:
    """存储后端：memory（默认）| postgres。"""
    return os.environ.get("TOOLS_STORE", "memory").strip().lower()


def database_url() -> str:
    """PostgreSQL DSN（ psycopg 可直接使用的 postgres:// URL 或 libpq conninfo）。

    优先级：
      1) TOOLS_DATABASE_URL：显式完整 DSN；密码含特殊字符时请自行 URL-encode。
      2) 分散变量组装：TOOLS_PG_HOST / PORT / NAME / USER / PASSWORD / SSLMODE。
         用 urllib.parse.quote 对 user/password/dbname 做百分号编码——
         密码若含 '@' 等特殊字符（本部署即如此），若不编码会被误当作 host 分隔符导致连库失败。
    关键项（host/user/dbname）缺失时返回空串，交由 runtime 做 fail-closed。
    """
    explicit = os.environ.get("TOOLS_DATABASE_URL", "").strip()
    if explicit:
        return explicit
    return build_database_url_from_parts()


def build_database_url_from_parts() -> str:
    """由分散环境变量拼出标准 postgres:// URL，对凭据做百分号编码。

    例：host=db.example.com port=6432 name=tools user=tools password='p@ss'
        -> postgresql://tools:p%40ss@db.example.com:6432/tools
    """
    host = os.environ.get("TOOLS_PG_HOST", "").strip()
    user = os.environ.get("TOOLS_PG_USER", "").strip()
    dbname = os.environ.get("TOOLS_PG_NAME", "").strip()
    if not (host and user and dbname):
        return ""
    port = os.environ.get("TOOLS_PG_PORT", "5432").strip() or "5432"
    password = os.environ.get("TOOLS_PG_PASSWORD", "")
    user_q = quote(user, safe="")
    pass_q = quote(password, safe="")
    dbname_q = quote(dbname, safe="")
    creds = f"{user_q}:{pass_q}@" if password else f"{user_q}@"
    url = f"postgresql://{creds}{host}:{port}/{dbname_q}"
    sslmode = os.environ.get("TOOLS_PG_SSLMODE", "").strip()
    if sslmode:
        url += f"?sslmode={quote(sslmode, safe='')}"
    return url


def pg_connect_kwargs() -> dict:
    """psycopg connect() 额外参数，重点适配 PgBouncer(6432) transaction pooling。

    PgBouncer 在事务池模式下，服务端 prepared statement 绑定在某条物理连接上，
    而客户端连接会复用不同物理连接，psycopg3 默认的自动 prepare 会间歇性报
    `prepared statement "_pg3_x" does not exist`。默认 prepare_threshold=None
    彻底关闭自动 prepare（性能影响可忽略，正确性优先）。
    TOOLS_PG_PREPARE_THRESHOLD 设为整数可按需重新开启（用户自负后果）。
    """
    raw = os.environ.get("TOOLS_PG_PREPARE_THRESHOLD", "off").strip().lower()
    threshold: int | None = None
    if raw not in ("", "off", "none", "false", "0"):
        try:
            threshold = max(1, int(raw))
        except ValueError:
            threshold = None
    kwargs: dict = {"prepare_threshold": threshold}
    timeout = os.environ.get("TOOLS_PG_CONNECT_TIMEOUT", "10").strip()
    try:
        kwargs["connect_timeout"] = max(1, int(timeout))
    except ValueError:
        kwargs["connect_timeout"] = 10
    return kwargs


def pg_pool_max_size(default: int = 8) -> int:
    """连接池上限。PgBouncer 后端可给较小值（如 4），由部署 env 控制。"""
    raw = os.environ.get("TOOLS_PG_POOL_MAX", str(default)).strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return default


def cors_origins() -> list[str]:
    """允许的跨域来源白名单（逗号分隔）。

    前端部署在 GitHub Pages（https://<user>.github.io），后端在云主机独立域名，
    属跨域调用，须把 Pages 源（及自定义域）列入。默认空 = 仅同源，不暴露跨域头。
    CORS 是浏览器侧约束，不是鉴权；passthrough 阶段的身份安全由 auth 模式负责。
    """
    raw = os.environ.get("TOOLS_CORS_ORIGINS", "").strip()
    return [item.strip().rstrip("/") for item in raw.split(",") if item.strip()]


def auth_mode() -> str:
    """鉴权模式：passthrough（默认，暂时不鉴权）| dev | logto | stub。"""
    return os.environ.get("TOOLS_AUTH_MODE", "passthrough").strip().lower()


def dev_auth_header() -> str:
    return os.environ.get("TOOLS_DEV_AUTH_HEADER", "X-User-Sub").strip() or "X-User-Sub"


def passthrough_default_sub() -> str:
    """passthrough 模式下请求未带 X-User-Sub 时使用的归属槽位。"""
    return os.environ.get("TOOLS_PASSTHROUGH_DEFAULT_SUB", "anonymous").strip() or "anonymous"


def logto_issuer() -> str:
    return os.environ.get("LOGTO_ISSUER", "").strip()


def logto_audience() -> str:
    return os.environ.get("LOGTO_AUDIENCE", "").strip()


def logto_jwks_url() -> str:
    return os.environ.get("LOGTO_JWKS_URL", "").strip()


def max_value_bytes() -> int:
    """单条配置 value 序列化后大小上限，默认 512 KiB，防存储滥用。"""
    raw = os.environ.get("TOOLS_MAX_VALUE_BYTES", "524288")
    try:
        return max(1, int(raw))
    except ValueError:
        return 524288


def max_keys_per_user_tool() -> int:
    """单用户单工具下的 key 数量上限，默认 200。"""
    raw = os.environ.get("TOOLS_MAX_KEYS", "200")
    try:
        return max(1, int(raw))
    except ValueError:
        return 200


def allowed_tool_ids() -> set[str]:
    """允许的工具 id 白名单；空集合表示不限制（用正则校验形状即可）。"""
    raw = os.environ.get("TOOLS_TOOL_IDS", "")
    return {s.strip() for s in raw.split(",") if s.strip()}

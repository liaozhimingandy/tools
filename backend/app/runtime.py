"""运行期装配：按配置把鉴权 provider 与存储仓库注入 app.state。

这样做的好处：
  - main.py 不 import psycopg/PyJWT 的具体类，可选依赖缺席时应用照常启动；
  - 测试可直接替换 app.state.auth_provider / repository，无需 mock 全局；
  - 切换 dev→logto、memory→postgres 只改环境变量，零代码改动。
"""

from __future__ import annotations

from . import auth, config
from .auth import AuthProvider, LogtoJWTProvider
from .store import ConfigRepository, MemoryRepository
from .tools_registry import ToolRepository, build_repository as build_tool_repository


def build_auth_provider() -> AuthProvider:
    if config.auth_mode() == "logto":
        return LogtoJWTProvider(
            issuer=config.logto_issuer(),
            audience=config.logto_audience(),
            jwks_url=config.logto_jwks_url(),
        )
    return auth.build_provider(
        mode=config.auth_mode(),
        dev_header=config.dev_auth_header(),
        passthrough_header=config.dev_auth_header(),
        passthrough_default_sub=config.passthrough_default_sub(),
    )


def build_repository() -> ConfigRepository:
    if config.store_backend() == "postgres":
        dsn = config.database_url()
        if not dsn:
            # fail-closed：显式选了 postgres 却不给 DSN，直接拒绝启动，
            # 而不是悄悄退回内存导致「以为落库了其实没落」。
            raise RuntimeError("TOOLS_STORE=postgres 但 TOOLS_DATABASE_URL 为空")
        from .store import PostgresRepository

        return PostgresRepository(dsn)
    return MemoryRepository()


def build_tools() -> ToolRepository:
    """工具注册表：postgres 模式查 tools 表；memory 模式用内置种子。

    fail-closed：postgres 模式必须有 DSN（build_repository 已校验），此处复用同一 DSN。
    """
    if config.store_backend() == "postgres":
        return build_tool_repository(config.database_url())
    return build_tool_repository(None)


def logto_configured(provider: AuthProvider) -> bool:
    return isinstance(provider, LogtoJWTProvider) and provider.configured


def wire(app) -> None:
    """把依赖挂到 app.state，供 API 路由通过 request.app.state 取用。"""
    provider = build_auth_provider()
    repo = build_repository()
    app.state.auth_provider = provider
    app.state.repository = repo
    app.state.tool_repository = build_tools()
    app.state.logto_configured = logto_configured(provider)
    app.state.store_backend = config.store_backend()


def teardown(app) -> None:
    """关停时释放各连接池等资源。"""
    for attr in ("repository", "tool_repository"):
        obj = getattr(app.state, attr, None)
        close = getattr(obj, "close", None)
        if callable(close):
            close()

"""tools 后端：FastAPI。

职责严格限定为三类，绝不接触用户数据明文：
  1. 托管 Vite 构建产物（前端 SPA），并提供 history 路由回退；
  2. 提供元信息接口（health/version/auth-mode）与「工具注册表」API（全局元数据）；
  3. 提供「公共配置表」API（用户密文配置的云端存取）。

零知识边界：公共配置表存的 value 是不透明密文 blob。后端不定义账户/条目明文模型、
不解密、不解析 value 内容、不记录明文，也不接触用户密钥。所有加解密在浏览器端完成。
schema_version 仅透传 value 内部结构版本、updated_by_device 仅记录设备标识，二者都不涉及明文。
用户身份来自鉴权层注入的 user_sub：logto 模式来自校验过的 JWT（不可伪造）；
passthrough/dev 模式下来自客户端声明的 X-User-Sub（**可伪造**，过渡态，勿用于正式多用户）。
工具注册表 tools 是非敏感全局元数据，不含用户数据、无需 RLS。

生产建议：TOOLS_AUTH_MODE=logto + TOOLS_STORE=postgres 并配置相应环境变量。
默认 passthrough（暂时不鉴权）+ memory，开箱即用、无外部依赖；
passthrough 信任客户端声明的 X-User-Sub，正式多用户上线前必须切 logto（见 /api/auth/mode）。
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config, runtime
from .configs import router as configs_router
from .schemas import APP_ERROR_CODES, HealthResponse, ServiceStatus, VersionResponse

API_PREFIX = "/api"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动装配依赖、打印就绪信息；关停释放连接池。不加载任何用户数据。"""
    runtime.wire(app)
    ready = config.dist_index_exists()
    print(
        f"[tools] frontend_ready={ready} dist={config.DIST_DIR} "
        f"store={app.state.store_backend} auth={app.state.auth_provider.mode} "
        f"tools={len(app.state.tool_repository.list(enabled_only=True))}"
    )
    yield
    runtime.teardown(app)


app = FastAPI(
    title="tools backend",
    version=config.APP_VERSION,
    description="Static SPA host + zero-knowledge config store + metadata only.",
    lifespan=lifespan,
)

# 跨域：前端部署在 GitHub Pages（https://<user>.github.io），后端在云主机独立域名，
# 属跨源调用，须把 Pages 源加入白名单（TOOLS_CORS_ORIGINS）。默认空 = 仅同源。
# 注意：CORS 是浏览器侧约束，不替代鉴权；passthrough 阶段身份安全由 auth 模式负责。
# allow_credentials=False：本方案用自定义头 X-User-Sub / Authorization 传身份，不依赖 Cookie。
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-User-Sub", "If-Match"],
    expose_headers=["ETag"],
    max_age=600,
)


# --------------------------------------------------------------------------- #
# 统一错误响应：把 HTTPException.detail / 校验错误摊平成规范 ErrorResponse，
# 不含堆栈、内部路径或用户数据。
# --------------------------------------------------------------------------- #


def _error_body(status: int, code: str, message: str, extra: dict | None = None) -> dict:
    body: dict = {"error": code, "message": message}
    if extra:
        body.update(extra)
    return body


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict) and "error" in detail:
        body = detail  # 路由已构造好规范形状（可能含 detail/conflict 字段）
        return JSONResponse(status_code=exc.status_code, content=body, headers=exc.headers)
    code = APP_ERROR_CODES.get(exc.status_code, "HTTP_ERROR")
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(exc.status_code, code, str(detail)),
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=_error_body(422, "VALIDATION_ERROR", "请求参数校验失败"),
    )


# --------------------------------------------------------------------------- #
# 元信息接口
# --------------------------------------------------------------------------- #


@app.get(f"{API_PREFIX}/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    """健康检查。frontend_ready=false 表示 dist 尚未构建，但服务本身可用。"""
    return HealthResponse(
        status=ServiceStatus.OK,
        frontend_ready=config.dist_index_exists(),
    )


@app.get(f"{API_PREFIX}/version", response_model=VersionResponse, tags=["meta"])
def version() -> VersionResponse:
    """版本信息：应用版本 + 已安装的工程规范版本（统一版本记录）。"""
    return VersionResponse(
        app_version=config.APP_VERSION,
        standards_version=config.read_standards_version(),
        zero_knowledge=True,
    )


# 公共配置表 API（/api/auth/mode 与 /api/v1/configs/*）
app.include_router(configs_router)


# --------------------------------------------------------------------------- #
# 静态资源与 SPA 回退（放最后，避免吞掉 API 路由）
# --------------------------------------------------------------------------- #

if config.DIST_DIR.is_dir():
    _assets_dir = config.DIST_DIR / "assets"
    # base=/tools/ 时 index.html 以绝对路径请求 /tools/assets/*.js；同份 assets
    # 挂到所有需要的路径（/assets 与 /tools/assets），否则 JS 请求会落进 SPA 回退
    # 拿到 index.html（HTML 当 JS 解析 → 空白页）。工具名/基路径由 TOOLS_PUBLIC_PATH 控制，
    # 与前端 Vite base 保持一致。
    for _i, _mount_path in enumerate(config.assets_mount_paths()):
        app.mount(_mount_path, StaticFiles(directory=_assets_dir, check_dir=False), name=f"assets_{_i}")


@app.get("/{full_path:path}", include_in_schema=False)
def spa_fallback(full_path: str):
    """SPA 回退：非 /api 路径优先直出 dist 内真实文件，否则返回 index.html。

    前端是 hash 路由（/#/safekeep），hash 不发给服务器，故这里主要兜底根路径、
    /tools/ 前缀与 favicon 等静态文件。base 前缀（如 'tools/'）需先剥离，才能把
    /tools/favicon.ico 映射到 dist/favicon.ico；同时保留目录穿越防护。
    """
    if full_path.startswith("api/") or full_path == "api":
        return JSONResponse(
            status_code=404,
            content=_error_body(404, "NOT_FOUND", "接口不存在"),
        )

    dist = config.DIST_DIR
    dist_root = dist.resolve()
    # 剥离公网基路径前缀（默认 'tools'），使其后按 dist 内相对路径解析。
    prefix = config.public_prefix()
    rel = full_path
    if prefix:
        if rel == prefix:
            rel = ""
        elif rel.startswith(prefix + "/"):
            rel = rel[len(prefix) + 1 :]

    candidate = (dist / rel).resolve()
    if candidate.is_file() and dist_root in candidate.parents:
        return FileResponse(candidate)

    index = dist / "index.html"
    if index.is_file():
        return FileResponse(index)

    return JSONResponse(
        status_code=503,
        content=_error_body(503, "FRONTEND_NOT_BUILT", "前端尚未构建，请先在 frontend/ 执行 npm run build"),
    )


def main() -> None:
    """本地启动入口：python -m app.main。仅监听回环地址。"""
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=config.bind_host(),
        port=config.bind_port(),
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()

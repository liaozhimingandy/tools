"""Also Apps 门户 API（统一 /v1 前缀）。

公开目录：
  GET    /v1/portal/apps                 应用列表（分类/搜索/推荐/首页/分页）
  GET    /v1/portal/apps/featured        推荐应用
  GET    /v1/portal/apps/search          搜索（与 apps?keyword= 等价，语义化别名）
  GET    /v1/portal/apps/{code}          应用详情
  GET    /v1/portal/categories           分类列表

用户功能（身份只来自鉴权 provider）：
  GET    /v1/portal/me/favorites
  POST   /v1/portal/me/favorites/{app_id}
  DELETE /v1/portal/me/favorites/{app_id}
  PUT    /v1/portal/me/favorites/order
  GET    /v1/portal/me/recent
  POST   /v1/portal/me/recent/{app_id}

启动校验（服务端二次判定，前端隐藏不算权限控制）：
  POST   /v1/portal/apps/{code}/launch

管理接口（管理员 sub 白名单，服务端强校验）：
  GET/POST        /v1/portal/admin/apps
  GET/PUT/DELETE  /v1/portal/admin/apps/{id}
  POST            /v1/portal/admin/apps/{id}/publish|disable
  GET/POST        /v1/portal/admin/categories
  PUT/DELETE      /v1/portal/admin/categories/{id}
  PUT             /v1/portal/admin/homepage
  GET             /v1/portal/admin/visits

安全契约：
  1. user_sub 只来自 get_principal()（鉴权层），path/query/body 的用户标识一律忽略。
  2. 公开接口只返回 published + public 的应用；private 应用对匿名与未授权者隐藏。
  3. 管理接口按 PORTAL_ADMIN_SUBS 白名单校验；配置为空时 fail-closed（拒绝所有管理请求）。
  4. 所有响应形状统一，错误走 HTTPException(detail={error,message}) 由 main.py 摊平。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from . import config
from .auth import AuthProvider, Principal, UnauthorizedError
from .portal_models import (
    APP_STATUSES,
    APP_TYPES,
    OPEN_MODES,
    VISIBILITIES,
    AppRecord,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
    app_in_public_catalog,
)
from .portal_store import PortalRepository, validate_launch_url

router = APIRouter()


# --------------------------------------------------------------------------- # 依赖与公共辅助
def _state(request: Request) -> Any:
    return request.app.state


def _api_error(status: int, code: str, message: str, **extra: Any) -> HTTPException:
    detail: dict[str, Any] = {"error": code, "message": message}
    detail.update(extra)
    return HTTPException(status_code=status, detail=detail)


def get_portal_repository(request: Request) -> PortalRepository:
    return _state(request).portal_repository


def optional_principal(request: Request) -> Principal | None:
    """可选身份：公开接口允许匿名，带合法令牌时拿到 sub 用于私有应用过滤。"""
    provider: AuthProvider = _state(request).auth_provider
    headers = {k: v for k, v in request.headers.items()}
    try:
        return provider.authenticate(headers=headers)
    except UnauthorizedError:
        return None


def require_principal(request: Request) -> Principal:
    """强制身份：用户态接口必须登录。"""
    provider: AuthProvider = _state(request).auth_provider
    headers = {k: v for k, v in request.headers.items()}
    try:
        return provider.authenticate(headers=headers)
    except UnauthorizedError as exc:
        raise _api_error(401, exc.code, str(exc)) from None


def require_admin(principal: Principal = Depends(require_principal)) -> Principal:
    """管理员校验：白名单为空时 fail-closed，绝不裸奔。"""
    admins = config.portal_admin_subs()
    if not admins or principal.sub not in admins:
        raise _api_error(403, "FORBIDDEN", "需要管理员权限")
    return principal


def _visible_or_404(app: AppRecord | None) -> AppRecord:
    if not app or not app_in_public_catalog(app):
        raise _api_error(404, "APP_NOT_FOUND", "应用不存在或未发布")
    return app


def _handle_domain_error(exc: Exception) -> None:
    if isinstance(exc, NotFoundError):
        raise _api_error(404, "NOT_FOUND", str(exc)) from None
    if isinstance(exc, ConflictError):
        raise _api_error(409, "CONFLICT", str(exc)) from None
    if isinstance(exc, ForbiddenError):
        raise _api_error(403, "FORBIDDEN", str(exc)) from None
    if isinstance(exc, ValidationError):
        raise _api_error(422, "VALIDATION_ERROR", str(exc)) from None
    raise exc


# --------------------------------------------------------------------------- # 公开目录
@router.get("/v1/portal/apps", tags=["portal-public"])
def list_apps(
    request: Request,
    category: str = Query(default="", description="分类 code；all 表示全部"),
    keyword: str = Query(default="", max_length=100, description="名称/副标题/简介/编码搜索"),
    featured: bool = Query(default=False, description="仅推荐应用"),
    home: bool = Query(default=False, description="仅首页展示应用"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    principal: Principal | None = Depends(optional_principal),
    repo: PortalRepository = Depends(get_portal_repository),
) -> dict[str, Any]:
    """匿名可读的公开应用目录；query 条件可由前端保留在 URL 中。"""
    try:
        rows = repo.list_apps(
            status="published",
            category=category or None,
            keyword=keyword,
            featured_only=featured,
            home_only=home,
            include_private=False,
            limit=page_size,
            offset=(page - 1) * page_size,
        )
        total = repo.count_apps(
            status="published",
            category=category or None,
            keyword=keyword,
            featured_only=featured,
            home_only=home,
            include_private=False,
        )
    except Exception as exc:
        _handle_domain_error(exc)
    return {
        "items": [app.to_public() for app in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/v1/portal/apps/featured", tags=["portal-public"])
def featured_apps(
    repo: PortalRepository = Depends(get_portal_repository),
) -> dict[str, Any]:
    rows = repo.list_apps(status="published", featured_only=True, include_private=False)
    return {"items": [app.to_public() for app in rows], "total": len(rows)}


@router.get("/v1/portal/apps/search", tags=["portal-public"])
def search_apps(
    q: str = Query(default="", max_length=100),
    category: str = Query(default=""),
    repo: PortalRepository = Depends(get_portal_repository),
) -> dict[str, Any]:
    rows = repo.list_apps(
        status="published", keyword=q, category=category or None, include_private=False
    )
    return {"items": [app.to_public() for app in rows], "total": len(rows)}


@router.get("/v1/portal/apps/{code}", tags=["portal-public"])
def app_detail(
    code: str,
    principal: Principal | None = Depends(optional_principal),
    repo: PortalRepository = Depends(get_portal_repository),
) -> dict[str, Any]:
    """应用详情。private 应用对匿名/未授权者返回 404（不泄露存在性）。"""
    app = repo.get_app_by_code(code)
    if not app:
        raise _api_error(404, "APP_NOT_FOUND", "应用不存在")
    if app.status != "published":
        raise _api_error(404, "APP_NOT_FOUND", "应用不存在或未发布")
    if app.visibility == "private":
        # 授权查询由统一授权体系负责；门户目前没有可查询的授权 API，
        # 因此 private 应用对所有门户访客隐藏，业务系统自行授权进入。
        raise _api_error(404, "APP_NOT_FOUND", "应用不存在或未发布")
    result = app.to_public()
    result["favorited"] = False
    if principal:
        favs = repo.list_favorites(principal.sub)
        result["favorited"] = any(f.app_id == app.id for f in favs)
    return result


@router.get("/v1/portal/categories", tags=["portal-public"])
def list_categories(repo: PortalRepository = Depends(get_portal_repository)) -> dict[str, Any]:
    rows = repo.list_categories(enabled_only=True)
    return {"items": [cat.to_public() for cat in rows], "total": len(rows)}


# --------------------------------------------------------------------------- # 应用启动校验
@router.post("/v1/portal/apps/{code}/launch", tags=["portal-user"])
def check_launch(
    code: str,
    principal: Principal | None = Depends(optional_principal),
    repo: PortalRepository = Depends(get_portal_repository),
) -> dict[str, Any]:
    """启动前服务端二次校验：发布状态、登录要求、可见范围、地址安全。

    前端拿到 allowed=true 才打开应用；但业务权限仍由目标应用后端负责。
    """
    app = repo.get_app_by_code(code)
    if not app or app.status != "published":
        raise _api_error(404, "APP_NOT_FOUND", "应用不存在或未发布")
    if app.visibility == "private":
        raise _api_error(403, "APP_FORBIDDEN", "该应用需要授权后才能访问")
    if app.auth_required and principal is None:
        return {
            "allowed": False,
            "reason": "LOGIN_REQUIRED",
            "message": "请先登录 Also Account 后再访问该应用",
            "app": app.to_public(),
        }
    if not app.launch_url:
        return {
            "allowed": False,
            "reason": "NOT_DEPLOYED",
            "message": "该应用尚未开放访问",
            "app": app.to_public(),
        }
    # 再次校验 URL，防历史脏数据或管理接口绕过
    validate_launch_url(app.launch_url)
    return {
        "allowed": True,
        "reason": None,
        "message": "",
        "app": app.to_public(),
        "url": app.launch_url,
        "open_mode": app.open_mode,
    }


# --------------------------------------------------------------------------- # 用户收藏
@router.get("/v1/portal/me/favorites", tags=["portal-user"])
def my_favorites(
    principal: Principal = Depends(require_principal),
    repo: PortalRepository = Depends(get_portal_repository),
) -> dict[str, Any]:
    favs = repo.list_favorites(principal.sub)
    apps: list[dict[str, Any]] = []
    for fav in favs:
        app = repo.get_app_by_id(fav.app_id)
        if app and app_in_public_catalog(app):
            data = app.to_public()
            data["sort_order"] = fav.sort_order
            apps.append(data)
    return {"items": apps, "total": len(apps)}


@router.post("/v1/portal/me/favorites/{app_id}", tags=["portal-user"])
def add_favorite(
    app_id: str,
    principal: Principal = Depends(require_principal),
    repo: PortalRepository = Depends(get_portal_repository),
) -> dict[str, Any]:
    app = repo.get_app_by_id(app_id)
    if not app or not app_in_public_catalog(app):
        raise _api_error(404, "APP_NOT_FOUND", "应用不存在或未发布")
    try:
        fav = repo.add_favorite(principal.sub, app_id)
    except Exception as exc:
        _handle_domain_error(exc)
    return {"ok": True, "favorite": fav.to_public()}  # type: ignore[possibly-undefined]


@router.delete("/v1/portal/me/favorites/{app_id}", tags=["portal-user"])
def remove_favorite(
    app_id: str,
    principal: Principal = Depends(require_principal),
    repo: PortalRepository = Depends(get_portal_repository),
) -> dict[str, Any]:
    try:
        repo.remove_favorite(principal.sub, app_id)
    except Exception as exc:
        _handle_domain_error(exc)
    return {"ok": True}


@router.put("/v1/portal/me/favorites/order", tags=["portal-user"])
def reorder_favorites(
    body: dict[str, Any],
    principal: Principal = Depends(require_principal),
    repo: PortalRepository = Depends(get_portal_repository),
) -> dict[str, Any]:
    ids = body.get("app_ids")
    if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids) or len(ids) > 200:
        raise _api_error(422, "VALIDATION_ERROR", "app_ids 必须是字符串数组且不超过 200 项")
    favs = repo.reorder_favorites(principal.sub, ids)
    return {"items": [f.to_public() for f in favs]}


# --------------------------------------------------------------------------- # 最近访问
@router.get("/v1/portal/me/recent", tags=["portal-user"])
def my_recent(
    limit: int = Query(default=10, ge=1, le=100),
    principal: Principal = Depends(require_principal),
    repo: PortalRepository = Depends(get_portal_repository),
) -> dict[str, Any]:
    visits = repo.list_recent(principal.sub, limit=limit)
    items = []
    for visit in visits:
        app = repo.get_app_by_id(visit.app_id)
        if app and app_in_public_catalog(app):
            data = app.to_public()
            data["last_visited_at"] = visit.last_visited_at
            data["visit_count"] = visit.visit_count
            items.append(data)
    return {"items": items, "total": len(items)}


@router.post("/v1/portal/me/recent/{app_id}", tags=["portal-user"])
def record_visit(
    app_id: str,
    principal: Principal = Depends(require_principal),
    repo: PortalRepository = Depends(get_portal_repository),
) -> dict[str, Any]:
    app = repo.get_app_by_id(app_id)
    if not app or not app_in_public_catalog(app):
        raise _api_error(404, "APP_NOT_FOUND", "应用不存在或未发布")
    visit = repo.record_visit(principal.sub, app_id)
    return {"ok": True, "visit": visit.to_public()}

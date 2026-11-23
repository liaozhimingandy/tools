"""Also Apps 门户管理 API（/v1/portal/admin/*）。

所有接口强制管理员校验（require_admin 依赖），配置为空时 fail-closed。
管理端可以读写草稿/私有/停用应用，这是与普通用户目录的唯一差别。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from .portal_api import _api_error, _handle_domain_error, get_portal_repository, require_admin
from .portal_models import (
    APP_STATUSES,
    APP_TYPES,
    OPEN_MODES,
    VISIBILITIES,
    AppRecord,
    CategoryRecord,
)
from .portal_store import PortalRepository, validate_launch_url

router = APIRouter()


def _app_payload(body: dict[str, Any]) -> dict[str, Any]:
    """校验并规范化应用写入字段；仅接受白名单字段，拒绝未知字段。"""
    allowed = {
        "name", "subtitle", "description", "detail", "icon_url", "cover_url", "launch_url",
        "app_type", "open_mode", "status", "visibility", "auth_required", "is_featured",
        "show_on_home", "is_new", "sort_order", "updated_by",
    }
    unknown = set(body) - allowed - {"code", "categories"}
    if unknown:
        raise _api_error(422, "VALIDATION_ERROR", f"未知字段: {', '.join(sorted(unknown))}")
    result = {k: v for k, v in body.items() if k not in ("code", "categories")}
    if "name" in result:
        if not isinstance(result["name"], str) or not result["name"].strip():
            raise _api_error(422, "VALIDATION_ERROR", "应用名称必填")
        result["name"] = result["name"].strip()[:100]
    for key in ("subtitle", "description", "detail", "icon_url", "cover_url"):
        if key in result and not isinstance(result[key], str):
            raise _api_error(422, "VALIDATION_ERROR", f"{key} 必须是字符串")
    if "launch_url" in result:
        try:
            result["launch_url"] = validate_launch_url(str(result["launch_url"]))
        except Exception as exc:
            _handle_domain_error(exc)
    for key, values in (
        ("app_type", APP_TYPES), ("open_mode", OPEN_MODES),
        ("status", APP_STATUSES), ("visibility", VISIBILITIES),
    ):
        if key in result and result[key] not in values:
            raise _api_error(422, "VALIDATION_ERROR", f"{key} 取值非法")
    for key in ("auth_required", "is_featured", "show_on_home", "is_new"):
        if key in result and not isinstance(result[key], bool):
            raise _api_error(422, "VALIDATION_ERROR", f"{key} 必须是布尔值")
    if "sort_order" in result:
        if not isinstance(result["sort_order"], int) or abs(result["sort_order"]) > 100000:
            raise _api_error(422, "VALIDATION_ERROR", "sort_order 必须是合理整数")
    return result


@router.get("/v1/portal/admin/apps", tags=["portal-admin"])
def admin_list_apps(
    keyword: str = Query(default="", max_length=100),
    status: str = Query(default=""),
    app_type: str = Query(default=""),
    category: str = Query(default=""),
    repo: PortalRepository = Depends(get_portal_repository),
    admin=Depends(require_admin),
) -> dict[str, Any]:
    if status and status not in APP_STATUSES:
        raise _api_error(422, "VALIDATION_ERROR", "status 取值非法")
    if app_type and app_type not in APP_TYPES:
        raise _api_error(422, "VALIDATION_ERROR", "app_type 取值非法")
    rows = repo.list_apps(
        status=status or None,
        category=category or None,
        keyword=keyword,
        include_private=True,
    )
    if app_type:
        rows = [a for a in rows if a.app_type == app_type]
    return {"items": [a.to_public() for a in rows], "total": len(rows)}


@router.post("/v1/portal/admin/apps", tags=["portal-admin"])
def admin_create_app(
    body: dict[str, Any],
    repo: PortalRepository = Depends(get_portal_repository),
    admin=Depends(require_admin),
) -> dict[str, Any]:
    code = str(body.get("code", "")).strip().upper()
    if not code or len(code) > 64 or not all(c.isalnum() or c == "_" for c in code):
        raise _api_error(422, "VALIDATION_ERROR", "code 只能包含字母、数字和下划线")
    categories = body.get("categories", [])
    if not isinstance(categories, list) or not all(isinstance(c, str) for c in categories):
        raise _api_error(422, "VALIDATION_ERROR", "categories 必须是字符串数组")
    payload = _app_payload({k: v for k, v in body.items() if k != "categories"})
    payload.setdefault("name", code)
    app = AppRecord(code=code, **payload)
    try:
        created = repo.create_app(app, tuple(categories))
    except Exception as exc:
        _handle_domain_error(exc)
    return {"ok": True, "app": created.to_public()}  # type: ignore[possibly-undefined]


@router.get("/v1/portal/admin/apps/{app_id}", tags=["portal-admin"])
def admin_get_app(
    app_id: str,
    repo: PortalRepository = Depends(get_portal_repository),
    admin=Depends(require_admin),
) -> dict[str, Any]:
    app = repo.get_app_by_id(app_id)
    if not app:
        raise _api_error(404, "APP_NOT_FOUND", "应用不存在")
    return {"app": app.to_public()}


@router.put("/v1/portal/admin/apps/{app_id}", tags=["portal-admin"])
def admin_update_app(
    app_id: str,
    body: dict[str, Any],
    repo: PortalRepository = Depends(get_portal_repository),
    admin=Depends(require_admin),
) -> dict[str, Any]:
    payload = _app_payload(body)
    try:
        updated = repo.update_app(app_id, **payload)
        if "categories" in body:
            cats = body["categories"]
            if not isinstance(cats, list) or not all(isinstance(c, str) for c in cats):
                raise _api_error(422, "VALIDATION_ERROR", "categories 必须是字符串数组")
            updated = repo.set_app_categories(app_id, tuple(cats))
    except Exception as exc:
        _handle_domain_error(exc)
    return {"ok": True, "app": updated.to_public()}  # type: ignore[possibly-undefined]


@router.delete("/v1/portal/admin/apps/{app_id}", tags=["portal-admin"])
def admin_delete_app(
    app_id: str,
    repo: PortalRepository = Depends(get_portal_repository),
    admin=Depends(require_admin),
) -> dict[str, Any]:
    try:
        repo.delete_app(app_id)
    except Exception as exc:
        _handle_domain_error(exc)
    return {"ok": True}


@router.post("/v1/portal/admin/apps/{app_id}/publish", tags=["portal-admin"])
def admin_publish_app(
    app_id: str,
    repo: PortalRepository = Depends(get_portal_repository),
    admin=Depends(require_admin),
) -> dict[str, Any]:
    try:
        app = repo.update_app(app_id, status="published", updated_by=admin.sub)
    except Exception as exc:
        _handle_domain_error(exc)
    return {"ok": True, "app": app.to_public()}  # type: ignore[possibly-undefined]


@router.post("/v1/portal/admin/apps/{app_id}/disable", tags=["portal-admin"])
def admin_disable_app(
    app_id: str,
    repo: PortalRepository = Depends(get_portal_repository),
    admin=Depends(require_admin),
) -> dict[str, Any]:
    try:
        app = repo.update_app(app_id, status="disabled", updated_by=admin.sub)
    except Exception as exc:
        _handle_domain_error(exc)
    return {"ok": True, "app": app.to_public()}  # type: ignore[possibly-undefined]


# --------------------------------------------------------------------------- # 分类管理
@router.get("/v1/portal/admin/categories", tags=["portal-admin"])
def admin_list_categories(
    repo: PortalRepository = Depends(get_portal_repository),
    admin=Depends(require_admin),
) -> dict[str, Any]:
    rows = repo.list_categories(enabled_only=False)
    return {"items": [c.to_public() for c in rows], "total": len(rows)}


@router.post("/v1/portal/admin/categories", tags=["portal-admin"])
def admin_create_category(
    body: dict[str, Any],
    repo: PortalRepository = Depends(get_portal_repository),
    admin=Depends(require_admin),
) -> dict[str, Any]:
    code = str(body.get("code", "")).strip()
    name = str(body.get("name", "")).strip()
    if not code or not name or len(code) > 64 or len(name) > 100:
        raise _api_error(422, "VALIDATION_ERROR", "code 与 name 必填且长度合法")
    status = body.get("status", "enabled")
    if status not in ("enabled", "disabled"):
        raise _api_error(422, "VALIDATION_ERROR", "status 取值非法")
    category = CategoryRecord(
        code=code, name=name,
        description=str(body.get("description", "")),
        icon=str(body.get("icon", "")),
        parent_id=body.get("parent_id"),
        sort_order=int(body.get("sort_order", 0)),
        status=status,
    )
    try:
        created = repo.create_category(category)
    except Exception as exc:
        _handle_domain_error(exc)
    return {"ok": True, "category": created.to_public()}  # type: ignore[possibly-undefined]


@router.put("/v1/portal/admin/categories/{category_id}", tags=["portal-admin"])
def admin_update_category(
    category_id: str,
    body: dict[str, Any],
    repo: PortalRepository = Depends(get_portal_repository),
    admin=Depends(require_admin),
) -> dict[str, Any]:
    allowed = {"name", "description", "icon", "parent_id", "sort_order", "status"}
    payload = {k: v for k, v in body.items() if k in allowed}
    if "status" in payload and payload["status"] not in ("enabled", "disabled"):
        raise _api_error(422, "VALIDATION_ERROR", "status 取值非法")
    try:
        updated = repo.update_category(category_id, **payload)
    except Exception as exc:
        _handle_domain_error(exc)
    return {"ok": True, "category": updated.to_public()}  # type: ignore[possibly-undefined]


@router.delete("/v1/portal/admin/categories/{category_id}", tags=["portal-admin"])
def admin_delete_category(
    category_id: str,
    repo: PortalRepository = Depends(get_portal_repository),
    admin=Depends(require_admin),
) -> dict[str, Any]:
    try:
        repo.delete_category(category_id)
    except Exception as exc:
        _handle_domain_error(exc)
    return {"ok": True}


# --------------------------------------------------------------------------- # 首页展示管理
@router.put("/v1/portal/admin/homepage", tags=["portal-admin"])
def admin_set_homepage(
    body: dict[str, Any],
    repo: PortalRepository = Depends(get_portal_repository),
    admin=Depends(require_admin),
) -> dict[str, Any]:
    """批量配置首页展示：{items:[{id, show_on_home, is_featured, sort_order}]}。"""
    items = body.get("items")
    if not isinstance(items, list) or len(items) > 200:
        raise _api_error(422, "VALIDATION_ERROR", "items 必须是数组且不超过 200 项")
    updated: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise _api_error(422, "VALIDATION_ERROR", "每项必须有 id")
        changes = {k: item[k] for k in ("show_on_home", "is_featured", "sort_order") if k in item}
        for key in ("show_on_home", "is_featured"):
            if key in changes and not isinstance(changes[key], bool):
                raise _api_error(422, "VALIDATION_ERROR", f"{key} 必须是布尔值")
        if "sort_order" in changes and not isinstance(changes["sort_order"], int):
            raise _api_error(422, "VALIDATION_ERROR", "sort_order 必须是整数")
        try:
            app = repo.update_app(item["id"], **changes)
        except Exception as exc:
            _handle_domain_error(exc)
        updated.append(app.to_public())  # type: ignore[possibly-undefined]
    return {"ok": True, "items": updated}


# --------------------------------------------------------------------------- # 访问记录（聚合视图，不返回 user_sub）
@router.get("/v1/portal/admin/visits", tags=["portal-admin"])
def admin_visits(
    limit: int = Query(default=50, ge=1, le=500),
    repo: PortalRepository = Depends(get_portal_repository),
    admin=Depends(require_admin),
) -> dict[str, Any]:
    """管理员看访问统计：由仓储提供聚合；当前内存实现返回空列表，PG 可扩展。

    不返回 user_sub（避免个人信息泄露），只返回应用维度统计。
    """
    getter = getattr(repo, "visit_summary", None)
    items = getter(limit) if callable(getter) else []
    return {"items": items, "total": len(items)}

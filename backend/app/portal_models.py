"""Also Apps 门户领域模型（纯 dataclass，无框架依赖，可在 Node/Pytest 下直接测试）。

边界约定：
  - portal_apps 是展示目录，不等于业务授权；visibility=public 只表示「卡片可见」，
    能否真正进入应用由目标业务应用后端负责校验。
  - user_sub 是 Logto sub，唯一可信用户标识；任何模型都不接受客户端传入的
    user_sub 作为查询/写入条件（由 API 层从 auth provider 注入）。
  - app_type/status/visibility/open_mode 用 Literal 限死取值，与 SQL CHECK 一致。
  - 时间字段存字符串（ISO-8601 UTC，'Z' 结尾），由 portal_ids.iso_utc 生成。
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Literal

from .portal_ids import iso_utc, new_id_str, utcnow

AppType = Literal["application", "tool", "game", "service"]
OpenMode = Literal["same_tab", "new_tab"]
AppStatus = Literal["draft", "published", "disabled"]
Visibility = Literal["public", "private"]

APP_TYPES: tuple[AppType, ...] = ("application", "tool", "game", "service")
OPEN_MODES: tuple[OpenMode, ...] = ("same_tab", "new_tab")
APP_STATUSES: tuple[AppStatus, ...] = ("draft", "published", "disabled")
VISIBILITIES: tuple[Visibility, ...] = ("public", "private")


@dataclass(frozen=True)
class AppRecord:
    """门户应用目录中的一条应用。"""

    code: str
    name: str
    id: str = field(default_factory=new_id_str)
    subtitle: str = ""
    description: str = ""
    detail: str = ""
    icon_url: str = ""
    cover_url: str = ""
    launch_url: str = ""
    app_type: AppType = "application"
    open_mode: OpenMode = "new_tab"
    status: AppStatus = "draft"
    visibility: Visibility = "public"
    auth_required: bool = False
    is_featured: bool = False
    show_on_home: bool = False
    is_new: bool = False
    sort_order: int = 0
    published_at: str | None = None
    created_by: str | None = None
    updated_by: str | None = None
    created_at: str = field(default_factory=lambda: iso_utc(utcnow()) or "")
    updated_at: str = field(default_factory=lambda: iso_utc(utcnow()) or "")
    categories: tuple[str, ...] = ()  # 分类 code 列表，装配时填入

    def to_public(self) -> dict[str, Any]:
        """公开响应形状：字段稳定，不含内部审计信息之外的敏感内容。"""
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "subtitle": self.subtitle,
            "description": self.description,
            "detail": self.detail,
            "icon_url": self.icon_url,
            "cover_url": self.cover_url,
            "launch_url": self.launch_url,
            "app_type": self.app_type,
            "open_mode": self.open_mode,
            "status": self.status,
            "visibility": self.visibility,
            "auth_required": self.auth_required,
            "is_featured": self.is_featured,
            "show_on_home": self.show_on_home,
            "is_new": self.is_new,
            "sort_order": self.sort_order,
            "published_at": self.published_at,
            "categories": list(self.categories),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class CategoryRecord:
    """应用分类。parent_id 预留二级分类；本期不实现无限级管理。"""

    code: str
    name: str
    id: str = field(default_factory=new_id_str)
    description: str = ""
    icon: str = ""
    parent_id: str | None = None
    sort_order: int = 0
    status: Literal["enabled", "disabled"] = "enabled"
    created_at: str = field(default_factory=lambda: iso_utc(utcnow()) or "")
    updated_at: str = field(default_factory=lambda: iso_utc(utcnow()) or "")

    def to_public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "parent_id": self.parent_id,
            "sort_order": self.sort_order,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class FavoriteRecord:
    """用户收藏。user_sub 只由鉴权层注入。"""

    user_sub: str
    app_id: str
    id: str = field(default_factory=new_id_str)
    sort_order: int = 0
    created_at: str = field(default_factory=lambda: iso_utc(utcnow()) or "")

    def to_public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "app_id": self.app_id,
            "sort_order": self.sort_order,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class RecentVisitRecord:
    """最近访问：每用户每应用一行，重复访问只累加 visit_count。"""

    user_sub: str
    app_id: str
    id: str = field(default_factory=new_id_str)
    last_visited_at: str = field(default_factory=lambda: iso_utc(utcnow()) or "")
    visit_count: int = 1
    created_at: str = field(default_factory=lambda: iso_utc(utcnow()) or "")
    updated_at: str = field(default_factory=lambda: iso_utc(utcnow()) or "")

    def to_public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "app_id": self.app_id,
            "last_visited_at": self.last_visited_at,
            "visit_count": self.visit_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class PortalError(Exception):
    """门户领域错误基类，API 层映射为统一错误码。"""

    code = "PORTAL_ERROR"
    status_code = 400


class NotFoundError(PortalError):
    code = "NOT_FOUND"
    status_code = 404


class ConflictError(PortalError):
    code = "CONFLICT"
    status_code = 409


class ForbiddenError(PortalError):
    code = "FORBIDDEN"
    status_code = 403


class ValidationError(PortalError):
    code = "VALIDATION_ERROR"
    status_code = 422


def app_in_public_catalog(app: AppRecord) -> bool:
    """是否允许出现在匿名公开目录中：已发布 + public 展示范围。

    注意：这与「业务访问权限」无关，仅决定卡片是否可见。
    """
    return app.status == "published" and app.visibility == "public"


def sanitize_app(app: AppRecord, *, authenticated: bool, authorized: bool = False) -> AppRecord | None:
    """按访问者身份裁剪应用可见性；不可见返回 None。

    - 未发布/已停用：仅管理员可经管理接口看到，公开接口一律隐藏。
    - private：未登录者不可见；已登录但无授权者不可见（授权体系由外部提供）。
    - launch_url 在「公开目录中不可使用时」清空，避免把草稿/无权限地址暴露给前端。
    """
    if app.status != "published":
        return None
    if app.visibility == "private" and not (authenticated and authorized):
        return None
    if not app.launch_url and app.status != "draft":
        # 已发布但没有地址：保留卡片展示，前端「立即使用」按空地址禁用
        return app
    return app


def with_updated(app: AppRecord, **changes: Any) -> AppRecord:
    """生成更新后的应用记录，统一维护 updated_at 与发布时间语义。"""
    merged = dict(app.__dict__)
    merged.update(changes)
    merged["updated_at"] = iso_utc(utcnow()) or ""
    status = merged.get("status")
    if status == "published":
        if not merged.get("published_at"):
            merged["published_at"] = iso_utc(utcnow())
    else:
        merged["published_at"] = None
    return replace(app, **merged)

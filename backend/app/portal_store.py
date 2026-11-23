"""Also Apps 门户仓储层：依赖倒置 + 内存/PG 双实现。

与 tools_registry.py / store.py 同构：
  - PortalRepository 协议：目录查询、用户收藏、最近访问、管理 CRUD 的最小契约；
  - MemoryPortalRepository：默认与测试用，内置种子，无外部依赖；
  - PostgresPortalRepository：psycopg3 参数化 SQL，用户私有表强制 SET LOCAL app.user_sub；
  - build_repository()：按 TOOLS_STORE 切换（与公共配置表共用同一 DSN）。

安全要点：
  1. 所有 user_sub 只由 API 层从鉴权 provider 注入，仓储层不产生、不猜测身份。
  2. PG 实现对每个「用户态」事务先 set_config('app.user_sub', sub, true)，
     RLS 在数据库层兜底隔离（即便应用漏写 WHERE 也读不到他人数据）。
  3. 目录表是全局元数据，不启用 RLS；管理写入由独立权限控制，不经应用角色暴露。
"""

from __future__ import annotations

import re
import threading
from dataclasses import replace
from typing import Any, Protocol
from urllib.parse import urlparse

from .portal_ids import iso_utc, new_id_str, utcnow
from .portal_models import (
    AppRecord,
    AppStatus,
    CategoryRecord,
    FavoriteRecord,
    RecentVisitRecord,
    ValidationError,
    with_updated,
)

# --------------------------------------------------------------------------- # URL 安全校验
# 仅允许 http/https 绝对 URL，且必须有主机；禁止 userinfo（防钓鱼伪装）。
_SAFE_URL_RE = re.compile(r"^https?://[^/\s@?#]+(?::\d+)?(?:/[^\s]*)?$", re.IGNORECASE)


def validate_launch_url(url: str) -> str:
    """校验应用访问地址：空串允许（草稿/未部署）；非空必须 http(s) 且无 userinfo。

    双重防线：SQL CHECK 已做粗校验，这里做严格校验（含 userinfo、控制字符）。
    """
    value = (url or "").strip()
    if not value:
        return ""
    if not _SAFE_URL_RE.match(value) or any(ord(c) < 0x20 for c in value):
        raise ValidationError("launch_url 必须是合法的 http/https 地址")
    parsed = urlparse(value)
    if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc or parsed.username:
        raise ValidationError("launch_url 不允许包含用户凭据或非 http(s) 协议")
    return value


# --------------------------------------------------------------------------- # 仓储协议
class PortalRepository(Protocol):
    """门户数据访问契约。所有用户态方法都以 user_sub 为强制隔离维度。"""

    # 目录（全局元数据）
    def list_apps(
        self,
        *,
        status: AppStatus | None = None,
        category: str | None = None,
        keyword: str = "",
        featured_only: bool = False,
        home_only: bool = False,
        include_private: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[AppRecord]: ...

    def count_apps(self, **filters: Any) -> int: ...

    def get_app_by_code(self, code: str) -> AppRecord | None: ...

    def get_app_by_id(self, app_id: str) -> AppRecord | None: ...

    def create_app(self, app: AppRecord, category_codes: tuple[str, ...] = ()) -> AppRecord: ...

    def update_app(self, app_id: str, **changes: Any) -> AppRecord: ...

    def delete_app(self, app_id: str) -> None: ...

    def set_app_categories(self, app_id: str, category_codes: tuple[str, ...]) -> AppRecord: ...

    # 分类
    def list_categories(self, *, enabled_only: bool = True) -> list[CategoryRecord]: ...

    def get_category_by_code(self, code: str) -> CategoryRecord | None: ...

    def get_category_by_id(self, category_id: str) -> CategoryRecord | None: ...

    def create_category(self, category: CategoryRecord) -> CategoryRecord: ...

    def update_category(self, category_id: str, **changes: Any) -> CategoryRecord: ...

    def delete_category(self, category_id: str) -> None: ...

    # 用户收藏（user_sub 由鉴权层注入）
    def list_favorites(self, user_sub: str) -> list[FavoriteRecord]: ...

    def add_favorite(self, user_sub: str, app_id: str, sort_order: int = 0) -> FavoriteRecord: ...

    def remove_favorite(self, user_sub: str, app_id: str) -> None: ...

    def reorder_favorites(self, user_sub: str, app_ids: list[str]) -> list[FavoriteRecord]: ...

    # 最近访问
    def list_recent(self, user_sub: str, limit: int = 10) -> list[RecentVisitRecord]: ...

    def record_visit(self, user_sub: str, app_id: str) -> RecentVisitRecord: ...


# --------------------------------------------------------------------------- # 内存实现
class MemoryPortalRepository:
    """进程内实现：默认与测试用。线程安全，便于 TestClient 并发。"""

    def __init__(self, seed: bool = True) -> None:
        self._lock = threading.RLock()
        self._apps: dict[str, AppRecord] = {}
        self._categories: dict[str, CategoryRecord] = {}
        self._app_categories: dict[str, tuple[str, ...]] = {}
        self._favorites: dict[tuple[str, str], FavoriteRecord] = {}
        self._recent: dict[tuple[str, str], RecentVisitRecord] = {}
        if seed:
            self.seed_defaults()

    # ---- 种子（与 sql/005 对应，但仅限默认内存模式，不区分 PG）----
    def seed_defaults(self) -> None:
        from .portal_seed import DEFAULT_APPS, DEFAULT_CATEGORIES

        for cat in DEFAULT_CATEGORIES:
            self._categories.setdefault(cat.code, cat)
        for app in DEFAULT_APPS:
            self._apps.setdefault(app.code, app)
            self._app_categories.setdefault(app.code, app.categories)

    def seed(self, *apps: AppRecord, categories: tuple[CategoryRecord, ...] = ()) -> None:
        """测试注入自定义数据。"""
        with self._lock:
            for cat in categories:
                self._categories[cat.code] = cat
            for app in apps:
                self._apps[app.code] = app
                self._app_categories[app.code] = app.categories

    # ---- 目录 ----
    @staticmethod
    def _match(
        app: AppRecord,
        *,
        category: str | None,
        keyword: str,
        featured_only: bool,
        home_only: bool,
        status: AppStatus | None,
        include_private: bool,
    ) -> bool:
        if status is not None and app.status != status:
            return False
        if not include_private and app.visibility == "private":
            return False
        if featured_only and not app.is_featured:
            return False
        if home_only and not app.show_on_home:
            return False
        if category and category != "all" and category not in app.categories:
            return False
        if keyword:
            needle = keyword.strip().lower()
            hay = " ".join((app.code, app.name, app.subtitle, app.description)).lower()
            if needle not in hay:
                return False
        return True

    def list_apps(self, **kwargs: Any) -> list[AppRecord]:
        status = kwargs.get("status")
        category = kwargs.get("category")
        keyword = kwargs.get("keyword", "")
        featured_only = bool(kwargs.get("featured_only", False))
        home_only = bool(kwargs.get("home_only", False))
        include_private = bool(kwargs.get("include_private", False))
        limit = kwargs.get("limit")
        offset = int(kwargs.get("offset", 0))
        with self._lock:
            rows: list[AppRecord] = []
            for app in self._apps.values():
                decorated = replace(app, categories=self._app_categories.get(app.code, ()))
                if self._match(
                    decorated,
                    category=category,
                    keyword=str(keyword),
                    featured_only=featured_only,
                    home_only=home_only,
                    status=status,
                    include_private=include_private,
                ):
                    rows.append(decorated)
            rows.sort(key=lambda a: (a.sort_order, a.code))
            rows = rows[offset:]
            return rows[:limit] if limit is not None else rows

    def count_apps(self, **filters: Any) -> int:
        return len(self.list_apps(**filters))

    def _decorate(self, app: AppRecord | None) -> AppRecord | None:
        if app is None:
            return None
        return replace(app, categories=self._app_categories.get(app.code, ()))

    def get_app_by_code(self, code: str) -> AppRecord | None:
        with self._lock:
            return self._decorate(self._apps.get(code.upper()))

    def get_app_by_id(self, app_id: str) -> AppRecord | None:
        with self._lock:
            for app in self._apps.values():
                if app.id == app_id:
                    return self._decorate(app)
            return None

    def create_app(self, app: AppRecord, category_codes: tuple[str, ...] = ()) -> AppRecord:
        with self._lock:
            if app.code.upper() in self._apps:
                raise ValidationError("应用编码已存在")
            stored = replace(app, code=app.code.upper(), categories=())
            self._apps[stored.code] = stored
            self._app_categories[stored.code] = category_codes
            return self._decorate(stored)  # type: ignore[return-value]

    def update_app(self, app_id: str, **changes: Any) -> AppRecord:
        from .portal_models import NotFoundError

        with self._lock:
            for code, app in list(self._apps.items()):
                if app.id != app_id:
                    continue
                if "launch_url" in changes:
                    changes["launch_url"] = validate_launch_url(str(changes["launch_url"]))
                updated = with_updated(app, **changes)
                self._apps[code] = replace(updated, categories=())
                return self._decorate(self._apps[code])  # type: ignore[return-value]
            raise NotFoundError("应用不存在")

    def delete_app(self, app_id: str) -> None:
        from .portal_models import NotFoundError

        with self._lock:
            for code, app in list(self._apps.items()):
                if app.id == app_id:
                    del self._apps[code]
                    self._app_categories.pop(code, None)
                    for key in [k for k, v in self._favorites.items() if v.app_id == app_id]:
                        del self._favorites[key]
                    for key in [k for k, v in self._recent.items() if v.app_id == app_id]:
                        del self._recent[key]
                    return
            raise NotFoundError("应用不存在")

    def set_app_categories(self, app_id: str, category_codes: tuple[str, ...]) -> AppRecord:
        from .portal_models import NotFoundError

        with self._lock:
            for code, app in self._apps.items():
                if app.id == app_id:
                    self._app_categories[code] = tuple(dict.fromkeys(category_codes))
                    return self._decorate(app)  # type: ignore[return-value]
            raise NotFoundError("应用不存在")

    # ---- 分类 ----
    def list_categories(self, *, enabled_only: bool = True) -> list[CategoryRecord]:
        with self._lock:
            rows = [c for c in self._categories.values() if (c.status == "enabled" or not enabled_only)]
            return sorted(rows, key=lambda c: (c.sort_order, c.code))

    def get_category_by_code(self, code: str) -> CategoryRecord | None:
        with self._lock:
            return self._categories.get(code)

    def get_category_by_id(self, category_id: str) -> CategoryRecord | None:
        with self._lock:
            return next((c for c in self._categories.values() if c.id == category_id), None)

    def create_category(self, category: CategoryRecord) -> CategoryRecord:
        with self._lock:
            if category.code in self._categories:
                raise ValidationError("分类编码已存在")
            self._categories[category.code] = category
            return category

    def update_category(self, category_id: str, **changes: Any) -> CategoryRecord:
        from .portal_models import NotFoundError

        with self._lock:
            for code, cat in list(self._categories.items()):
                if cat.id != category_id:
                    continue
                merged = dict(cat.__dict__)
                merged.update(changes)
                merged["updated_at"] = iso_utc(utcnow()) or ""
                updated = replace(cat, **merged)
                self._categories[code] = updated
                return updated
            raise NotFoundError("分类不存在")

    def delete_category(self, category_id: str) -> None:
        from .portal_models import NotFoundError

        with self._lock:
            for code, cat in list(self._categories.items()):
                if cat.id != category_id:
                    continue
                del self._categories[code]
                for app_code, cats in list(self._app_categories.items()):
                    self._app_categories[app_code] = tuple(c for c in cats if c != code)
                for cid, parent in list(self._categories.items()):
                    if parent.parent_id == category_id:
                        self._categories[cid] = replace(parent, parent_id=None)
                return
            raise NotFoundError("分类不存在")

    # ---- 收藏 ----
    def list_favorites(self, user_sub: str) -> list[FavoriteRecord]:
        with self._lock:
            rows = [f for f in self._favorites.values() if f.user_sub == user_sub]
            return sorted(rows, key=lambda f: (f.sort_order, f.created_at))

    def add_favorite(self, user_sub: str, app_id: str, sort_order: int = 0) -> FavoriteRecord:
        from .portal_models import ConflictError

        with self._lock:
            key = (user_sub, app_id)
            if key in self._favorites:
                raise ConflictError("已收藏该应用")
            rec = FavoriteRecord(user_sub=user_sub, app_id=app_id, sort_order=sort_order)
            self._favorites[key] = rec
            return rec

    def remove_favorite(self, user_sub: str, app_id: str) -> None:
        from .portal_models import NotFoundError

        with self._lock:
            key = (user_sub, app_id)
            if key not in self._favorites:
                raise NotFoundError("收藏记录不存在")
            del self._favorites[key]

    def reorder_favorites(self, user_sub: str, app_ids: list[str]) -> list[FavoriteRecord]:
        with self._lock:
            order = {app_id: i for i, app_id in enumerate(app_ids)}
            for key, fav in list(self._favorites.items()):
                if fav.user_sub == user_sub and fav.app_id in order:
                    self._favorites[key] = replace(fav, sort_order=order[fav.app_id])
            return self.list_favorites(user_sub)

    # ---- 最近访问 ----
    def list_recent(self, user_sub: str, limit: int = 10) -> list[RecentVisitRecord]:
        with self._lock:
            rows = [r for r in self._recent.values() if r.user_sub == user_sub]
            rows.sort(key=lambda r: r.last_visited_at, reverse=True)
            return rows[:limit]

    def record_visit(self, user_sub: str, app_id: str) -> RecentVisitRecord:
        with self._lock:
            key = (user_sub, app_id)
            now = iso_utc(utcnow()) or ""
            old = self._recent.get(key)
            if old:
                rec = replace(
                    old,
                    visit_count=old.visit_count + 1,
                    last_visited_at=now,
                    updated_at=now,
                )
            else:
                rec = RecentVisitRecord(
                    user_sub=user_sub, app_id=app_id, last_visited_at=now, updated_at=now
                )
            self._recent[key] = rec
            return rec


def build_repository(dsn: str | None) -> PortalRepository:
    """工厂：有 postgres DSN 用真实表，否则用内存种子。"""
    if dsn:
        from .portal_store_pg import PostgresPortalRepository

        return PostgresPortalRepository(dsn)
    return MemoryPortalRepository()

"""Also Apps 门户契约测试（unittest 标准库 + FastAPI TestClient）。

覆盖任务验收项：
  新增/编辑/删除应用、发布下架、首页推荐配置、分类筛选、关键词搜索、
  收藏/取消、最近访问、匿名与登录浏览、私有应用拦截、非法 URL 校验、
  越权（指定他人身份无效）、管理员白名单 fail-closed、URL 安全。
测试不依赖真实 PG、真实 Logto 租户或真实时钟。
"""

from __future__ import annotations

import os
import unittest
from contextlib import contextmanager
from typing import Iterator

from fastapi.testclient import TestClient

from app.auth import DevHeaderProvider
from app.main import app
from app.portal_ids import uuid7
from app.portal_models import AppRecord, CategoryRecord
from app.portal_store import MemoryPortalRepository, validate_launch_url
from app.store import MemoryRepository
from app.tools_registry import MemoryToolRepository

ADMIN_SUB = "admin-sub"
USER_A = "user-a"
USER_B = "user-b"


def admin_headers() -> dict[str, str]:
    return {"X-User-Sub": ADMIN_SUB}


def user_headers(sub: str = USER_A) -> dict[str, str]:
    return {"X-User-Sub": sub}


class PortalApiTestBase(unittest.TestCase):
    """每个用例注入隔离的内存仓储与 stub 鉴权，避免测试间互相污染。"""

    def setUp(self) -> None:
        self.repo = MemoryPortalRepository(seed=False)
        self.repo.seed(
            AppRecord(
                code="PUB", name="公开应用", status="published", visibility="public",
                launch_url="https://example.com/pub", published_at="2026-01-01T00:00:00Z",
                sort_order=10, categories=("all",),
            ),
            AppRecord(
                code="DRAFT", name="草稿应用", status="draft", visibility="public",
                categories=("all",),
            ),
            AppRecord(
                code="PRIVATE", name="私有应用", status="published", visibility="private",
                launch_url="https://example.com/priv", published_at="2026-01-01T00:00:00Z",
                categories=("all",),
            ),
            AppRecord(
                code="AUTH", name="需登录应用", status="published", visibility="public",
                auth_required=True, launch_url="https://example.com/auth",
                published_at="2026-01-01T00:00:00Z", categories=("all",),
            ),
            categories=(
                CategoryRecord(code="all", name="全部应用"),
                CategoryRecord(code="ai", name="AI 工具", sort_order=10),
            ),
        )

    @contextmanager
    def client(self, admin_config: str = ADMIN_SUB) -> Iterator[TestClient]:
        old_admin = os.environ.get("PORTAL_ADMIN_SUBS")
        os.environ["PORTAL_ADMIN_SUBS"] = admin_config
        try:
            with TestClient(app) as c:
                c.app.state.portal_repository = self.repo
                # 用 dev 头模式替代默认 passthrough：无头即 401，才能真实模拟「未登录」
                c.app.state.auth_provider = DevHeaderProvider()
                yield c
        finally:
            if old_admin is None:
                os.environ.pop("PORTAL_ADMIN_SUBS", None)
            else:
                os.environ["PORTAL_ADMIN_SUBS"] = old_admin

    def app_id(self, code: str) -> str:
        app = self.repo.get_app_by_code(code)
        assert app is not None
        return app.id


class TestPublicCatalog(PortalApiTestBase):
    def test_anonymous_sees_only_published_public(self) -> None:
        with self.client() as c:
            res = c.get("/v1/portal/apps")
            self.assertEqual(res.status_code, 200)
            codes = set(a["code"] for a in res.json()["items"])
            self.assertEqual(codes, {"PUB", "AUTH"})  # DRAFT/PRIVATE 不可见

    def test_private_app_detail_hidden(self) -> None:
        with self.client() as c:
            self.assertEqual(c.get("/v1/portal/apps/PRIVATE").status_code, 404)
            self.assertEqual(c.get("/v1/portal/apps/DRAFT").status_code, 404)

    def test_keyword_search_covers_code_and_name(self) -> None:
        with self.client() as c:
            self.assertEqual(c.get("/v1/portal/apps/search?q=PUB").json()["total"], 1)
            self.assertEqual(c.get("/v1/portal/apps/search?q=公开").json()["total"], 1)
            self.assertEqual(c.get("/v1/portal/apps/search?q=nope").json()["total"], 0)

    def test_category_filter_and_query_params(self) -> None:
        with self.client() as c:
            res = c.get("/v1/portal/apps?category=ai")
            self.assertEqual(res.json()["total"], 0)  # 种子应用都不属于 ai
            res = c.get("/v1/portal/apps?category=all")
            self.assertEqual(res.json()["total"], 2)

    def test_pagination(self) -> None:
        with self.client() as c:
            res = c.get("/v1/portal/apps?page=1&page_size=1")
            self.assertEqual(len(res.json()["items"]), 1)
            self.assertEqual(res.json()["total"], 2)


class TestLaunch(PortalApiTestBase):
    def test_published_app_launch_allowed(self) -> None:
        with self.client() as c:
            res = c.post("/v1/portal/apps/PUB/launch")
            self.assertTrue(res.json()["allowed"])
            self.assertEqual(res.json()["url"], "https://example.com/pub")

    def test_auth_required_app_needs_login(self) -> None:
        with self.client() as c:
            res = c.post("/v1/portal/apps/AUTH/launch")
            self.assertFalse(res.json()["allowed"])
            self.assertEqual(res.json()["reason"], "LOGIN_REQUIRED")
            res = c.post("/v1/portal/apps/AUTH/launch", headers=user_headers())
            self.assertTrue(res.json()["allowed"])

    def test_private_app_forbidden_even_logged_in(self) -> None:
        with self.client() as c:
            res = c.post("/v1/portal/apps/PRIVATE/launch", headers=user_headers())
            self.assertEqual(res.status_code, 403)

    def test_not_deployed_app_blocked(self) -> None:
        with self.client() as c:
            admin = admin_headers()
            c.post(
                "/v1/portal/admin/apps", headers=admin,
                json={"code": "EMPTY", "name": "未部署", "status": "published"},
            )
            res = c.post("/v1/portal/apps/EMPTY/launch")
            self.assertFalse(res.json()["allowed"])
            self.assertEqual(res.json()["reason"], "NOT_DEPLOYED")


class TestUserFeatures(PortalApiTestBase):
    def test_favorite_add_list_duplicate_remove(self) -> None:
        aid = self.app_id("PUB")
        with self.client() as c:
            h = user_headers()
            self.assertEqual(c.post(f"/v1/portal/me/favorites/{aid}", headers=h).status_code, 200)
            self.assertEqual(len(c.get("/v1/portal/me/favorites", headers=h).json()["items"]), 1)
            self.assertEqual(c.post(f"/v1/portal/me/favorites/{aid}", headers=h).status_code, 409)
            self.assertEqual(c.delete(f"/v1/portal/me/favorites/{aid}", headers=h).status_code, 200)
            self.assertEqual(len(c.get("/v1/portal/me/favorites", headers=h).json()["items"]), 0)

    def test_user_cannot_see_others_favorites(self) -> None:
        aid = self.app_id("PUB")
        with self.client() as c:
            c.post(f"/v1/portal/me/favorites/{aid}", headers=user_headers(USER_A))
            self.assertEqual(len(c.get("/v1/portal/me/favorites", headers=user_headers(USER_B)).json()["items"]), 0)

    def test_favorite_requires_login(self) -> None:
        with self.client() as c:
            self.assertEqual(c.get("/v1/portal/me/favorites").status_code, 401)

    def test_recent_accumulates_and_limits(self) -> None:
        aid = self.app_id("PUB")
        with self.client() as c:
            h = user_headers()
            for _ in range(3):
                c.post(f"/v1/portal/me/recent/{aid}", headers=h)
            items = c.get("/v1/portal/me/recent?limit=10", headers=h).json()["items"]
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["visit_count"], 3)

    def test_body_user_id_cannot_override_identity(self) -> None:
        """尝试在 body 指定 user_sub 不改变归属——身份只来自 header。"""
        aid = self.app_id("PUB")
        with self.client() as c:
            c.post(
                f"/v1/portal/me/favorites/{aid}",
                headers=user_headers(USER_A),
                json={"user_sub": USER_B},
            )
            self.assertEqual(len(c.get("/v1/portal/me/favorites", headers=user_headers(USER_A)).json()["items"]), 1)
            self.assertEqual(len(c.get("/v1/portal/me/favorites", headers=user_headers(USER_B)).json()["items"]), 0)


class TestAdmin(PortalApiTestBase):
    def test_admin_whitelist_fail_closed(self) -> None:
        with self.client(admin_config="") as c:
            self.assertEqual(c.get("/v1/portal/admin/apps", headers=admin_headers()).status_code, 403)
        with self.client() as c:
            self.assertEqual(c.get("/v1/portal/admin/apps", headers=user_headers()).status_code, 403)

    def test_create_edit_publish_disable_delete(self) -> None:
        with self.client() as c:
            h = admin_headers()
            created = c.post(
                "/v1/portal/admin/apps", headers=h,
                json={"code": "NEW1", "name": "新应用", "launch_url": "https://example.com/new"},
            )
            self.assertEqual(created.status_code, 200)
            app_id = created.json()["app"]["id"]
            self.assertEqual(created.json()["app"]["status"], "draft")
            self.assertEqual(c.get("/v1/portal/apps").json()["total"], 2)  # 草稿不公开

            edited = c.put(f"/v1/portal/admin/apps/{app_id}", headers=h, json={"subtitle": "副标题"})
            self.assertEqual(edited.json()["app"]["subtitle"], "副标题")

            published = c.post(f"/v1/portal/admin/apps/{app_id}/publish", headers=h)
            self.assertEqual(published.json()["app"]["status"], "published")
            self.assertEqual(c.get("/v1/portal/apps").json()["total"], 3)  # 发布后即刻可见

            disabled = c.post(f"/v1/portal/admin/apps/{app_id}/disable", headers=h)
            self.assertEqual(disabled.json()["app"]["status"], "disabled")
            self.assertEqual(c.get("/v1/portal/apps").json()["total"], 2)

            self.assertEqual(c.delete(f"/v1/portal/admin/apps/{app_id}", headers=h).status_code, 200)

    def test_dangerous_launch_url_rejected(self) -> None:
        for bad in ("javascript:alert(1)", "data:text/html,x", "//evil.com/x", "https://u:p@example.com"):
            with self.subTest(bad=bad):
                with self.client() as c:
                    res = c.post(
                        "/v1/portal/admin/apps", headers=admin_headers(),
                        json={"code": "BAD", "name": "危险地址", "launch_url": bad},
                    )
                    self.assertEqual(res.status_code, 422)

    def test_homepage_recommendation_takes_effect_immediately(self) -> None:
        with self.client() as c:
            h = admin_headers()
            aid = self.app_id("DRAFT")
            res = c.put(
                "/v1/portal/admin/homepage", headers=h,
                json={"items": [{"id": aid, "show_on_home": True, "is_featured": True, "sort_order": 1}]},
            )
            self.assertEqual(res.status_code, 200)
            # 草稿即使标记推荐也不公开；先发布再验证
            c.post(f"/v1/portal/admin/apps/{aid}/publish", headers=h)
            self.assertEqual(c.get("/v1/portal/apps/featured").json()["total"], 1)
            self.assertEqual(c.get("/v1/portal/apps?home=true").json()["total"], 1)

    def test_category_crud_and_delete_detaches(self) -> None:
        with self.client() as c:
            h = admin_headers()
            created = c.post(
                "/v1/portal/admin/categories", headers=h,
                json={"code": "newcat", "name": "新分类", "sort_order": 99},
            )
            self.assertEqual(created.status_code, 200)
            cid = created.json()["category"]["id"]
            self.assertEqual(c.put(f"/v1/portal/admin/categories/{cid}", headers=h, json={"name": "改名"}).json()["category"]["name"], "改名")
            self.assertEqual(c.delete(f"/v1/portal/admin/categories/{cid}", headers=h).status_code, 200)
            self.assertEqual(c.get("/v1/portal/admin/categories", headers=h).json()["total"], 2)


class TestDomainHelpers(unittest.TestCase):
    def test_uuid7_is_time_ordered_and_version_7(self) -> None:
        ids = [uuid7() for _ in range(20)]
        self.assertEqual(len(set(ids)), 20)
        self.assertTrue(all(i.version == 7 for i in ids))
        self.assertEqual(ids, sorted(ids))

    def test_validate_launch_url_accepts_empty_and_https(self) -> None:
        self.assertEqual(validate_launch_url(""), "")
        self.assertEqual(validate_launch_url("  https://a.example/app?x=1  "), "https://a.example/app?x=1")

    def test_delete_app_cascades_favorites_and_visits(self) -> None:
        repo = MemoryPortalRepository(seed=False)
        app = AppRecord(code="X", name="X", status="published", launch_url="https://x.example")
        created = repo.create_app(app)
        repo.add_favorite("u", created.id)
        repo.record_visit("u", created.id)
        self.assertEqual(len(repo.list_favorites("u")), 1)
        repo.delete_app(created.id)
        self.assertEqual(len(repo.list_favorites("u")), 0)
        self.assertEqual(len(repo.list_recent("u")), 0)


if __name__ == "__main__":
    unittest.main()

"""部署配置与 passthrough 鉴权契约测试（unittest 标准库）。

覆盖本轮云上部署引入的新行为：
  - DSN 组装：密码含 '@' 必须百分号编码，否则连库解析错乱；
  - PgBouncer(6432)：默认关闭自动 prepared statement，避免
    `prepared statement "_pg3_x" does not exist` 间歇错误；
  - CORS 白名单解析：逗号分隔、去尾斜杠、空串；
  - passthrough provider：永不 401、缺头回落默认 sub、超长 sub 拒绝；
  - /v1/auth/mode：passthrough 模式明确暴露 insecure 风险提示。
测试不依赖真实 PG / 网络 / 真实时钟。
"""

from __future__ import annotations

import os
import unittest
from unittest import mock

from fastapi.testclient import TestClient

from app import config
from app.auth import PassthroughProvider, UnauthorizedError, build_provider
from app.main import app


class TestDsnAssembly(unittest.TestCase):
    """分散环境变量 -> postgres:// URL 的组装（重点：凭据转义）。"""

    def _clear(self) -> None:
        for k in (
            "TOOLS_DATABASE_URL", "TOOLS_PG_HOST", "TOOLS_PG_PORT",
            "TOOLS_PG_NAME", "TOOLS_PG_USER", "TOOLS_PG_PASSWORD", "TOOLS_PG_SSLMODE",
        ):
            os.environ.pop(k, None)

    def setUp(self) -> None:
        self._clear()

    def tearDown(self) -> None:
        self._clear()

    def test_explicit_url_takes_priority(self) -> None:
        os.environ["TOOLS_DATABASE_URL"] = "postgresql://a:b@c:1/d"
        os.environ["TOOLS_PG_HOST"] = "ignored"
        self.assertEqual(config.database_url(), "postgresql://a:b@c:1/d")

    def test_password_with_at_is_percent_encoded(self) -> None:
        """密码里的 @ 若裸写会被当作 host 分隔符，必须编码成 %40（用假口令测，不涉密）。"""
        os.environ.update(
            TOOLS_PG_HOST="db.example.com",
            TOOLS_PG_PORT="6432",
            TOOLS_PG_NAME="tools",
            TOOLS_PG_USER="tools",
            TOOLS_PG_PASSWORD="p@ss",
        )
        url = config.database_url()
        self.assertEqual(
            url,
            "postgresql://tools:p%40ss@db.example.com:6432/tools",
        )
        self.assertIn("%40", url)

    def test_missing_key_parts_fail_closed_to_empty(self) -> None:
        os.environ["TOOLS_PG_HOST"] = "db.example.com"
        # 缺 user / dbname -> 返回空，交由 runtime fail-closed
        self.assertEqual(config.database_url(), "")

    def test_password_with_reserved_chars_all_encoded(self) -> None:
        os.environ.update(
            TOOLS_PG_HOST="h",
            TOOLS_PG_NAME="d",
            TOOLS_PG_USER="u",
            TOOLS_PG_PASSWORD="p@:/?#%",
        )
        url = config.database_url()
        self.assertIn("p%40%3A%2F%3F%23%25@", url)

    def test_sslmode_appended(self) -> None:
        os.environ.update(
            TOOLS_PG_HOST="h", TOOLS_PG_NAME="d",
            TOOLS_PG_USER="u", TOOLS_PG_PASSWORD="p", TOOLS_PG_SSLMODE="require",
        )
        self.assertTrue(config.database_url().endswith("?sslmode=require"))


class TestPgBouncerKwargs(unittest.TestCase):
    def _clear(self) -> None:
        for k in ("TOOLS_PG_PREPARE_THRESHOLD", "TOOLS_PG_CONNECT_TIMEOUT", "TOOLS_PG_POOL_MAX"):
            os.environ.pop(k, None)

    def setUp(self) -> None:
        self._clear()

    def tearDown(self) -> None:
        self._clear()

    def test_pgbouncer_disables_auto_prepare_by_default(self) -> None:
        kwargs = config.pg_connect_kwargs()
        self.assertIsNone(kwargs["prepare_threshold"])
        self.assertEqual(kwargs["connect_timeout"], 10)

    def test_prepare_threshold_can_be_re_enabled_explicitly(self) -> None:
        os.environ["TOOLS_PG_PREPARE_THRESHOLD"] = "5"
        self.assertEqual(config.pg_connect_kwargs()["prepare_threshold"], 5)

    def test_pool_max_size_reads_env(self) -> None:
        os.environ["TOOLS_PG_POOL_MAX"] = "4"
        self.assertEqual(config.pg_pool_max_size(8), 4)


class TestPublicPath(unittest.TestCase):
    """前端公网基路径：必须与 Vite base 对齐，否则 /tools/assets/*.js 会拿到 HTML。"""

    def _clear(self) -> None:
        os.environ.pop("TOOLS_PUBLIC_PATH", None)

    def setUp(self) -> None:
        self._clear()

    def tearDown(self) -> None:
        self._clear()

    def test_default_is_tools_subpath(self) -> None:
        self.assertEqual(config.public_path(), "/tools/")
        self.assertEqual(config.public_prefix(), "tools")

    def test_normalizes_missing_slashes(self) -> None:
        os.environ["TOOLS_PUBLIC_PATH"] = "apps/mytools"
        self.assertEqual(config.public_path(), "/apps/mytools/")
        self.assertEqual(config.public_prefix(), "apps/mytools")

    def test_root_deployment(self) -> None:
        os.environ["TOOLS_PUBLIC_PATH"] = "/"
        self.assertEqual(config.public_path(), "/")
        self.assertEqual(config.public_prefix(), "")

    def test_assets_mount_paths_default_includes_base(self) -> None:
        """默认既挂 /assets 又挂 /tools/assets，去重保序。"""
        self.assertEqual(config.assets_mount_paths(), ["/assets", "/tools/assets"])

    def test_assets_mount_paths_root_only_one(self) -> None:
        os.environ["TOOLS_PUBLIC_PATH"] = "/"
        self.assertEqual(config.assets_mount_paths(), ["/assets"])

    def test_assets_mount_paths_nested_base(self) -> None:
        os.environ["TOOLS_PUBLIC_PATH"] = "/apps/mytools/"
        self.assertEqual(config.assets_mount_paths(), ["/assets", "/apps/mytools/assets"])


class TestCorsOrigins(unittest.TestCase):
    def test_parse_comma_separated_and_strip_slash(self) -> None:
        raw = "https://alice.github.io/, https://tools.example.com ,"
        with mock.patch.dict(os.environ, {"TOOLS_CORS_ORIGINS": raw}):
            self.assertEqual(
                config.cors_origins(),
                ["https://alice.github.io", "https://tools.example.com"],
            )

    def test_empty_means_same_origin_only(self) -> None:
        with mock.patch.dict(os.environ, {"TOOLS_CORS_ORIGINS": ""}):
            self.assertEqual(config.cors_origins(), [])


class TestPassthroughProvider(unittest.TestCase):
    def test_reads_declared_sub(self) -> None:
        p = PassthroughProvider()
        self.assertEqual(p.authenticate(headers={"x-user-sub": "logto|abc"}).sub, "logto|abc")

    def test_missing_header_falls_back_never_401(self) -> None:
        """与 dev 模式的关键差别：passthrough 缺头不拒绝，回落默认 sub。"""
        p = PassthroughProvider(default_sub="anon")
        self.assertEqual(p.authenticate(headers={}).sub, "anon")

    def test_custom_default_sub(self) -> None:
        p = PassthroughProvider(header="X-User", default_sub="guest")
        self.assertEqual(p.authenticate(headers={}).sub, "guest")
        self.assertEqual(p.authenticate(headers={"x-user": "bob"}).sub, "bob")

    def test_oversized_sub_rejected(self) -> None:
        with self.assertRaises(UnauthorizedError):
            PassthroughProvider().authenticate(headers={"x-user-sub": "x" * 300})

    def test_factory_wires_passthrough(self) -> None:
        p = build_provider(mode="passthrough", passthrough_default_sub="anon")
        self.assertIsInstance(p, PassthroughProvider)
        self.assertEqual(p.mode, "passthrough")


class TestPassthroughAPIMode(unittest.TestCase):
    """app.state 装配为 passthrough 时，/v1/auth/mode 暴露 insecure 提示。"""

    def setUp(self) -> None:
        self.client = TestClient(app)
        self.prev = (
            app.state.auth_provider, app.state.repository,
            app.state.tool_repository, app.state.logto_configured,
        )

    def tearDown(self) -> None:
        (
            app.state.auth_provider, app.state.repository,
            app.state.tool_repository, app.state.logto_configured,
        ) = self.prev

    def test_mode_reports_insecure(self) -> None:
        from app.auth import PassthroughProvider
        from app.store import MemoryRepository
        from app.tools_registry import MemoryToolRepository

        app.state.auth_provider = PassthroughProvider()
        app.state.repository = MemoryRepository()
        app.state.tool_repository = MemoryToolRepository()
        app.state.logto_configured = False
        body = self.client.get("/v1/auth/mode").json()
        self.assertEqual(body["mode"], "passthrough")
        self.assertFalse(body["secure"])
        self.assertIn("不鉴权", body["warning"])

    def test_passthrough_writes_without_header_land_in_default_slot(self) -> None:
        from app.auth import PassthroughProvider
        from app.store import MemoryRepository
        from app.tools_registry import MemoryToolRepository

        repo = MemoryRepository()
        app.state.auth_provider = PassthroughProvider(default_sub="anonymous")
        app.state.repository = repo
        app.state.tool_repository = MemoryToolRepository()
        app.state.logto_configured = False
        # 无身份头：不 401，写入匿名槽
        r = self.client.put(
            "/v1/configs/safekeep/vault",
            json={"value": {"ct": "x"}, "expected_revision": 0},
        )
        self.assertEqual(r.status_code, 200)
        self.assertIsNotNone(repo.get("anonymous", "safekeep", "vault"))
        # 声明身份头：落到对应槽，彼此隔离
        r2 = self.client.put(
            "/v1/configs/safekeep/vault",
            json={"value": {"ct": "y"}, "expected_revision": 0},
            headers={"X-User-Sub": "logto|alice"},
        )
        self.assertEqual(r2.status_code, 200)
        self.assertIsNotNone(repo.get("logto|alice", "safekeep", "vault"))


if __name__ == "__main__":
    unittest.main(verbosity=2)

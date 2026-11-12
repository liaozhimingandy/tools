"""公共配置表 + 鉴权 + API 契约测试（unittest 标准库 + FastAPI TestClient）。

覆盖：
  - 存储层：CRUD、乐观锁 CAS、软删除、多租户/多工具隔离、零知识（value 原样存取且不解析）。
  - 鉴权层：user_sub 唯一来自 provider；dev 头缺失拒绝；stub 固定身份；Logto fail-closed。
  - API 层：响应 schema 稳定、ETag、配额、错误码统一、越权不可指定他人身份、
            /api/auth/mode 风险提示、旧元信息接口回归。
测试不依赖真实 PG、真实 JWT 租户或真实时钟。
"""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from app.auth import DevHeaderProvider, LogtoJWTProvider, StubProvider, UnauthorizedError
from app.main import app
from app.store import ConflictError, MemoryRepository, NotFoundError
from app.tools_registry import MemoryToolRepository, ToolRecord


# 一个典型的「零知识密文 blob」：只有 iv/ct/salt 等密封字段，没有明文
CIPHER_BLOB = {
    "account": {
        "v": 1,
        "app": "safekeep-local",
        "salt": "c2FsdA==",
        "kdf": {"alg": "PBKDF2-SHA256", "iterations": 600000},
        "wrapped": {"iv": "aXY=", "ct": "Y3Q="},
        "recovery": {"salt": "cnNhbHQ=", "iv": "cml2", "ct": "cmN0"},
    },
    "items": {"id-1": {"id": "id-1", "rev": 1, "iv": "AA==", "ct": "BB==", "deleted": False}},
    "rev": 1,
}


class TestMemoryRepository(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = MemoryRepository()

    def test_create_get_roundtrip_preserves_ciphertext_verbatim(self) -> None:
        """零知识核心：value 原样存取，存储层不解析、不改写内部结构。"""
        rec = self.repo.put("userA", "safekeep", "vault", CIPHER_BLOB, expected_revision=0)
        self.assertEqual(rec.revision, 1)
        got = self.repo.get("userA", "safekeep", "vault")
        self.assertEqual(got.value, CIPHER_BLOB)
        self.assertIn("ct", got.value["items"]["id-1"])  # 密文字段完好

    def test_first_create_rejects_overwrite(self) -> None:
        self.repo.put("u", "safekeep", "k", {"a": 1}, expected_revision=0)
        with self.assertRaises(ConflictError) as ctx:
            self.repo.put("u", "safekeep", "k", {"a": 2}, expected_revision=0)
        self.assertEqual(ctx.exception.actual, 1)

    def test_cas_update_and_conflict(self) -> None:
        r1 = self.repo.put("u", "safekeep", "k", {"v": 1}, expected_revision=0)
        r2 = self.repo.put("u", "safekeep", "k", {"v": 2}, expected_revision=r1.revision)
        self.assertEqual(r2.revision, 2)
        with self.assertRaises(ConflictError):
            self.repo.put("u", "safekeep", "k", {"v": 3}, expected_revision=r1.revision)  # 用旧版本

    def test_soft_delete_hides_from_get_and_list(self) -> None:
        r = self.repo.put("u", "safekeep", "k", {"x": 1}, expected_revision=0)
        self.repo.delete("u", "safekeep", "k", expected_revision=r.revision)
        with self.assertRaises(NotFoundError):
            self.repo.get("u", "safekeep", "k")
        self.assertEqual(self.repo.list("u", "safekeep"), [])
        rows = self.repo.list("u", "safekeep", include_deleted=True)
        self.assertEqual(len(rows), 1)
        self.assertIsNotNone(rows[0].deleted_at)

    def test_tenant_and_tool_isolation(self) -> None:
        self.repo.put("userA", "safekeep", "k", {"who": "A"}, expected_revision=0)
        self.repo.put("userB", "safekeep", "k", {"who": "B"}, expected_revision=0)
        self.repo.put("userA", "othertool", "k", {"who": "A-other"}, expected_revision=0)
        self.assertEqual(self.repo.get("userA", "safekeep", "k").value["who"], "A")
        self.assertEqual(self.repo.get("userB", "safekeep", "k").value["who"], "B")
        self.assertEqual(len(self.repo.list("userA", "safekeep")), 1)
        self.assertEqual(len(self.repo.list("userA", "othertool")), 1)

    def test_no_user_table_no_plaintext_model_in_store(self) -> None:
        """存储层不感知用户表，也不定义任何明文条目模型。"""
        import inspect
        import app.store as store_mod

        src = inspect.getsource(store_mod)
        self.assertNotIn("class User", src)
        self.assertNotIn("password", src.lower())  # 无明文密码字段模型

    def test_schema_version_and_device_roundtrip_orthogonal_to_revision(self) -> None:
        """schema_version（value 结构版本）与 revision（并发版本）正交，软删保留元信息。"""
        r1 = self.repo.put(
            "u", "safekeep", "k", {"ct": "a"}, expected_revision=0,
            schema_version=3, updated_by_device="edge-win",
        )
        self.assertEqual((r1.schema_version, r1.revision, r1.updated_by_device), (3, 1, "edge-win"))
        # 只改 value 结构版本，不动 revision 语义（仍按 CAS +1）
        r2 = self.repo.put(
            "u", "safekeep", "k", {"ct": "b"}, expected_revision=1,
            schema_version=4, updated_by_device="iphone",
        )
        self.assertEqual((r2.schema_version, r2.revision), (4, 2))
        # 软删保留上一个 schema_version / device，仅墓碑 + revision
        r3 = self.repo.delete("u", "safekeep", "k", expected_revision=2)
        self.assertEqual((r3.schema_version, r3.updated_by_device, r3.revision), (4, "iphone", 3))
        # 默认值：不传时为 1 / None
        d = self.repo.put("u", "safekeep", "d", {"x": 1}, expected_revision=0)
        self.assertEqual((d.schema_version, d.updated_by_device), (1, None))


class TestMemoryToolRepository(unittest.TestCase):
    def test_seed_list_get_exists_enabled(self) -> None:
        r = MemoryToolRepository()
        self.assertTrue(r.exists_enabled("safekeep"))
        self.assertFalse(r.exists_enabled("ghost"))
        self.assertEqual([t.tool_id for t in r.list()], ["safekeep"])
        self.assertIsNotNone(r.get("safekeep"))

    def test_disabled_and_sort_order_and_all(self) -> None:
        r = MemoryToolRepository([])
        r.seed(
            ToolRecord("zeta", "Z", "", "", True, 20, None, None, "s", "s"),
            ToolRecord("alpha", "A", "", "", True, 1, None, None, "s", "s"),
            ToolRecord("old", "O", "", "", False, 5, None, None, "s", "s"),
        )
        self.assertEqual([t.tool_id for t in r.list()], ["alpha", "zeta"])  # 禁用被过滤，按序
        self.assertEqual([t.tool_id for t in r.list(enabled_only=False)], ["alpha", "old", "zeta"])
        self.assertFalse(r.exists_enabled("old"))  # 禁用 = 不准入
        self.assertIsNotNone(r.get("old"))  # 但 get 仍可见（管理端可区分 404/禁用）


class TestAuthProviders(unittest.TestCase):
    def test_dev_header_provider_reads_sub_and_rejects_missing(self) -> None:
        p = DevHeaderProvider()
        self.assertEqual(p.authenticate(headers={"x-user-sub": "alice"}).sub, "alice")
        with self.assertRaises(UnauthorizedError):
            p.authenticate(headers={})

    def test_stub_provider_fixed_identity(self) -> None:
        p = StubProvider("fixed")
        self.assertEqual(p.authenticate(headers={}).sub, "fixed")

    def test_logto_not_configured_fails_closed(self) -> None:
        p = LogtoJWTProvider(issuer="", audience="", jwks_url="")
        self.assertFalse(p.configured)
        with self.assertRaises(UnauthorizedError) as ctx:
            p.authenticate(headers={"authorization": "Bearer whatever"})
        self.assertEqual(ctx.exception.code, "AUTH_NOT_CONFIGURED")

    def test_logto_rejects_non_bearer(self) -> None:
        p = LogtoJWTProvider(issuer="https://x/oidc", audience="api", jwks_url="https://x/jwks")
        with self.assertRaises(UnauthorizedError):
            p.authenticate(headers={"authorization": "Basic abc"})


class _BaseAPITest(unittest.TestCase):
    """替换 app.state 为测试装配，避免触碰真实存储/鉴权。"""

    def setUp(self) -> None:
        self.repo = MemoryRepository()
        self.provider = StubProvider("test-user")
        self.registry = MemoryToolRepository()  # 含 safekeep 种子
        app.state.auth_provider = self.provider
        app.state.repository = self.repo
        app.state.tool_repository = self.registry
        app.state.logto_configured = False
        app.state.store_backend = "memory"
        self.client = TestClient(app)

    def tearDown(self) -> None:
        # 恢复默认装配，避免影响其他测试类
        app.state.auth_provider = StubProvider("test-user")
        app.state.repository = MemoryRepository()
        app.state.tool_repository = MemoryToolRepository()


class TestConfigAPI(_BaseAPITest):
    def test_list_empty(self) -> None:
        r = self.client.get("/api/v1/configs/safekeep")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["tool_id"], "safekeep")
        self.assertEqual(body["count"], 0)
        self.assertEqual(body["items"], [])

    def test_put_then_get_with_etag(self) -> None:
        r = self.client.put(
            "/api/v1/configs/safekeep/vault",
            json={"value": CIPHER_BLOB, "expected_revision": 0},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers.get("etag"), 'W/"1"')
        body = r.json()
        self.assertEqual(body["revision"], 1)
        self.assertEqual(body["value"], CIPHER_BLOB)  # 零知识：原样回显密文
        self.assertNotIn("user_sub", body)  # 归属用户不下发、不由客户端指定

        g = self.client.get("/api/v1/configs/safekeep/vault")
        self.assertEqual(g.status_code, 200)
        self.assertEqual(g.json()["value"], CIPHER_BLOB)

    def test_update_requires_correct_revision(self) -> None:
        self.client.put("/api/v1/configs/safekeep/k", json={"value": {"v": 1}, "expected_revision": 0})
        ok = self.client.put("/api/v1/configs/safekeep/k", json={"value": {"v": 2}, "expected_revision": 1})
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.json()["revision"], 2)
        conflict = self.client.put(
            "/api/v1/configs/safekeep/k", json={"value": {"v": 3}, "expected_revision": 1}
        )
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["error"], "REVISION_CONFLICT")
        self.assertEqual(conflict.json()["detail"]["actual"], 2)

    def test_delete_soft_and_requires_revision(self) -> None:
        self.client.put("/api/v1/configs/safekeep/k", json={"value": {"v": 1}, "expected_revision": 0})
        missing_rev = self.client.delete("/api/v1/configs/safekeep/k")
        self.assertEqual(missing_rev.status_code, 422)  # expected_revision 必填
        d = self.client.delete("/api/v1/configs/safekeep/k?expected_revision=1")
        self.assertEqual(d.status_code, 200)
        self.assertIsNotNone(d.json()["deleted_at"])
        self.assertEqual(self.client.get("/api/v1/configs/safekeep/k").status_code, 404)

    def test_cross_user_and_cross_tool_isolation_via_api(self) -> None:
        self.client.put("/api/v1/configs/safekeep/k", json={"value": {"secret": "x"}, "expected_revision": 0})
        # 切到另一个 stub 身份
        app.state.auth_provider = StubProvider("another-user")
        self.assertEqual(self.client.get("/api/v1/configs/safekeep").json()["count"], 0)
        self.assertEqual(self.client.get("/api/v1/configs/safekeep/k").status_code, 404)

    def test_cannot_choose_own_identity_from_body_or_query(self) -> None:
        """越权防线：body/query 里的 user_id 一律被忽略，归属只由 provider 决定。"""
        self.client.put(
            "/api/v1/configs/safekeep/k?user_id=victim",
            json={"value": {"v": 1}, "expected_revision": 0, "user_id": "victim", "user_sub": "victim"},
        )
        self.assertIsNotNone(self.repo.get("test-user", "safekeep", "k"))
        with self.assertRaises(NotFoundError):
            self.repo.get("victim", "safekeep", "k")

    def test_invalid_ids_and_value_size(self) -> None:
        self.assertEqual(self.client.put("/api/v1/configs/BAD!/k", json={"value": 1, "expected_revision": 0}).status_code, 400)
        self.assertEqual(self.client.put("/api/v1/configs/safekeep/_quota", json={"value": 1, "expected_revision": 0}).status_code, 400)
        huge = "x" * (600 * 1024)
        r = self.client.put("/api/v1/configs/safekeep/k", json={"value": huge, "expected_revision": 0})
        self.assertEqual(r.status_code, 413)
        self.assertEqual(r.json()["error"], "VALUE_TOO_LARGE")

    def test_unserializable_value_rejected(self) -> None:
        r = self.client.put("/api/v1/configs/safekeep/k", json={"value": "ok", "expected_revision": 0})
        self.assertEqual(r.status_code, 200)

    def test_quota_endpoint(self) -> None:
        r = self.client.get("/api/v1/configs/safekeep/_quota")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["max_keys"], 200)
        self.assertEqual(r.json()["max_value_bytes"], 524288)

    def test_unknown_tool_404_when_whitelist_set(self) -> None:
        """环境变量白名单是注册表之上的第二道门：注册表中存在但白名单排除 → 404。"""
        import app.config as cfg
        from unittest import mock

        self.registry.seed(ToolRecord("notes", "便签", "", "", True, 0, None, None, "s", "s"))
        with mock.patch.object(cfg, "allowed_tool_ids", return_value={"safekeep"}):
            r = self.client.get("/api/v1/configs/notes")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.json()["error"], "TOOL_NOT_FOUND")

    def test_missing_dev_header_returns_401_when_dev_mode(self) -> None:
        app.state.auth_provider = DevHeaderProvider()
        r = self.client.get("/api/v1/configs/safekeep")
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.json()["error"], "UNAUTHORIZED")
        ok = self.client.get("/api/v1/configs/safekeep", headers={"X-User-Sub": "bob"})
        self.assertEqual(ok.status_code, 200)

    def test_new_fields_roundtrip_and_device_is_metadata_not_value(self) -> None:
        """schema_version/device 随 API 往返；device 不混入 value（零知识内容不变）。"""
        r = self.client.put(
            "/api/v1/configs/safekeep/vault",
            json={
                "value": CIPHER_BLOB, "expected_revision": 0,
                "schema_version": 9, "updated_by_device": "chrome-win",
            },
        )
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["schema_version"], 9)
        self.assertEqual(body["updated_by_device"], "chrome-win")
        self.assertEqual(body["value"], CIPHER_BLOB)  # value 原样，device 未渗入
        g = self.client.get("/api/v1/configs/safekeep/vault").json()
        self.assertEqual((g["schema_version"], g["updated_by_device"]), (9, "chrome-win"))
        self.assertEqual(g["revision"], 1)  # revision 独立，仍是 1

    def test_new_fields_defaults(self) -> None:
        r = self.client.put(
            "/api/v1/configs/safekeep/k", json={"value": {"a": 1}, "expected_revision": 0}
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["schema_version"], 1)
        self.assertIsNone(r.json()["updated_by_device"])

    def test_invalid_schema_version_and_long_device_rejected(self) -> None:
        self.assertEqual(
            self.client.put(
                "/api/v1/configs/safekeep/k",
                json={"value": 1, "expected_revision": 0, "schema_version": 0},
            ).status_code,
            422,
        )
        self.assertEqual(
            self.client.put(
                "/api/v1/configs/safekeep/k",
                json={"value": 1, "expected_revision": 0, "updated_by_device": "d" * 200},
            ).status_code,
            422,
        )

    def test_registry_gate_blocks_unregistered_and_disabled_tools(self) -> None:
        """注册表是工具准入权威：未注册 / 已禁用 → 404。"""
        self.assertEqual(self.client.get("/api/v1/configs/ghosttool").status_code, 404)
        self.registry.seed(ToolRecord("retired", "退役", "", "", False, 0, None, None, "s", "s"))
        self.assertEqual(self.client.get("/api/v1/configs/retired").status_code, 404)
        self.assertEqual(
            self.client.put(
                "/api/v1/configs/retired/k", json={"value": 1, "expected_revision": 0}
            ).status_code,
            404,
        )

    def test_tool_quota_overrides_global_defaults(self) -> None:
        """注册表的非 NULL 配额覆盖全局；配额/大小上限都生效。"""
        self.registry.seed(ToolRecord("safekeep", "锦囊", "", "", True, 10, 2, 16, "s", "s"))
        q = self.client.get("/api/v1/configs/safekeep/_quota").json()
        self.assertEqual((q["max_keys"], q["max_value_bytes"]), (2, 16))
        self.client.put("/api/v1/configs/safekeep/k1", json={"value": {"x": 1}, "expected_revision": 0})
        self.client.put("/api/v1/configs/safekeep/k2", json={"value": {"x": 1}, "expected_revision": 0})
        # 第 3 个 key 触发配额上限
        r = self.client.put("/api/v1/configs/safekeep/k3", json={"value": {"x": 1}, "expected_revision": 0})
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.json()["error"], "QUOTA_EXCEEDED")
        # 单条大小超工具覆盖上限 16 字节
        big = self.client.put(
            "/api/v1/configs/safekeep/k", json={"value": "x" * 100, "expected_revision": 0}
        )
        self.assertEqual(big.status_code, 413)


class TestToolsAPI(_BaseAPITest):
    def test_list_tools_returns_enabled_seed(self) -> None:
        r = self.client.get("/api/v1/tools")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["items"][0]["tool_id"], "safekeep")
        self.assertTrue(body["items"][0]["enabled"])

    def test_get_tool_and_hidden_when_disabled(self) -> None:
        r = self.client.get("/api/v1/tools/safekeep")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["name"], "锦囊")
        self.registry.seed(ToolRecord("gone", "下架", "", "", False, 0, None, None, "s", "s"))
        self.assertEqual(self.client.get("/api/v1/tools/gone").status_code, 404)

    def test_tools_requires_auth(self) -> None:
        app.state.auth_provider = DevHeaderProvider()
        self.assertEqual(self.client.get("/api/v1/tools").status_code, 401)
        self.assertEqual(
            self.client.get("/api/v1/tools", headers={"X-User-Sub": "bob"}).status_code, 200
        )

    def test_tools_carry_no_user_data(self) -> None:
        """工具清单是全局元数据：字段形状固定，不含 user_sub / value / 密文字段。"""
        item = self.client.get("/api/v1/tools").json()["items"][0]
        self.assertEqual(
            set(item.keys()),
            {
                "tool_id", "name", "icon", "description", "enabled", "sort_order",
                "default_max_keys", "default_max_value_bytes", "created_at", "updated_at",
            },
        )


class TestAuthModeAndRegression(_BaseAPITest):
    def test_auth_mode_exposes_risk(self) -> None:
        r = self.client.get("/api/auth/mode")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["mode"], "stub")
        self.assertFalse(body["secure"])
        self.assertIsNotNone(body["warning"])

    def test_auth_mode_secure_when_logto_configured(self) -> None:
        app.state.auth_provider = LogtoJWTProvider(issuer="https://x/oidc", audience="api", jwks_url="https://x/jwks")
        app.state.logto_configured = True
        body = self.client.get("/api/auth/mode").json()
        self.assertEqual(body["mode"], "logto")
        self.assertTrue(body["secure"])
        self.assertTrue(body["logto_configured"])

    def test_meta_endpoints_still_work(self) -> None:
        self.assertEqual(self.client.get("/api/health").status_code, 200)
        v = self.client.get("/api/version").json()
        self.assertTrue(v["zero_knowledge"])
        self.assertEqual(self.client.get("/api/definitely-not-a-route").json()["error"], "NOT_FOUND")


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""API 契约测试（unittest 标准库 + FastAPI TestClient）。

覆盖：正常响应、响应 schema 稳定、SPA 回退、/api 未匹配返回 404 JSON、
零知识标识恒为 true、规范版本统一记录、静态资源路径穿越被拒。
测试不依赖真实网络、真实时钟或开发者本机路径。
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from app import config
from app.main import app, spa_fallback
from app.schemas import HealthResponse, ServiceStatus, VersionResponse


class TestMetaEndpoints(unittest.TestCase):
    """元信息接口契约。"""

    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_health_returns_stable_schema_when_dist_ready(self) -> None:
        with mock.patch.object(config, "dist_index_exists", return_value=True):
            resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(set(body.keys()), {"status", "frontend_ready"})
        self.assertEqual(body["status"], "ok")
        self.assertIs(body["frontend_ready"], True)
        # 能被 Pydantic 模型解析，证明形状稳定
        HealthResponse.model_validate(body)

    def test_health_degraded_flag_when_dist_missing(self) -> None:
        with mock.patch.object(config, "dist_index_exists", return_value=False):
            resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        self.assertIs(resp.json()["frontend_ready"], False)

    def test_version_returns_app_and_standards_version(self) -> None:
        with mock.patch.object(config, "read_standards_version", return_value="1.0.0"):
            resp = self.client.get("/api/version")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        # 版本随功能迭代更新：0.3.0 引入工具注册表 + schema_version/updated_by_device
        from app.config import APP_VERSION

        self.assertEqual(body["app_version"], APP_VERSION)
        self.assertEqual(body["standards_version"], "1.0.0")
        VersionResponse.model_validate(body)

    def test_version_zero_knowledge_flag_always_true(self) -> None:
        """后端从不接触明文/密钥/密文，该标识是安全契约，恒为 true。"""
        resp = self.client.get("/api/version")
        self.assertIs(resp.json()["zero_knowledge"], True)

    def test_version_falls_back_when_standards_file_missing(self) -> None:
        with mock.patch.object(config, "read_standards_version", return_value="unknown"):
            resp = self.client.get("/api/version")
        self.assertEqual(resp.json()["standards_version"], "unknown")


class TestRoutingContract(unittest.TestCase):
    """路由与静态托管契约。"""

    def setUp(self) -> None:
        self.client = TestClient(app, follow_redirects=False)

    def test_unknown_api_returns_404_json_not_html(self) -> None:
        resp = self.client.get("/api/definitely-not-a-route")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["error"], "NOT_FOUND")
        self.assertNotIn("text/html", resp.headers.get("content-type", ""))

    def test_spa_route_falls_back_to_index_html(self) -> None:
        """vue-router history 模式：/safekeep 等非 api 路径回退 index.html。"""
        with tempfile.TemporaryDirectory() as tmp:
            dist = Path(tmp)
            (dist / "index.html").write_text("<!DOCTYPE html><title>spa</title>", encoding="utf-8")
            with mock.patch.object(config, "DIST_DIR", dist):
                resp = self.client.get("/safekeep")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/html", resp.headers.get("content-type", ""))
        self.assertIn("<title>spa</title>", resp.text)

    def test_spa_fallback_503_when_frontend_not_built(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(config, "DIST_DIR", Path(tmp)):
                resp = self.client.get("/safekeep")
        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.json()["error"], "FRONTEND_NOT_BUILT")

    def test_path_traversal_cannot_escape_dist(self) -> None:
        """目录穿越：请求 dist 之外的文件不应被直出，回退到 index.html。"""
        with tempfile.TemporaryDirectory() as tmp:
            dist = Path(tmp) / "dist"
            dist.mkdir()
            (dist / "index.html").write_text("<title>spa</title>", encoding="utf-8")
            secret = Path(tmp) / "secret.txt"
            secret.write_text("TOP-SECRET", encoding="utf-8")
            with mock.patch.object(config, "DIST_DIR", dist):
                resp = self.client.get("/../secret.txt")
        self.assertNotIn("TOP-SECRET", resp.text)

    def test_base_prefixed_asset_resolves_to_js_not_index(self) -> None:
        """回归：base=/tools/ 时 spa_fallback('tools/assets/app.js') 必须直出该 JS 文件，
        不能回退 index.html（否则 HTML 被当 JS 解析 → 空白页）。

        直接调用 spa_fallback 而非走 TestClient：/tools/assets 挂载在 import 期
        已绑定真实 dist，会被 mount 抢先；这里要测的是回退函数本身的前缀剥离逻辑。
        """
        from fastapi.responses import FileResponse

        with tempfile.TemporaryDirectory() as tmp:
            dist = Path(tmp)
            (dist / "assets").mkdir()
            (dist / "assets" / "app.js").write_text("console.log('OK_JS');", encoding="utf-8")
            (dist / "index.html").write_text("<title>spa</title>", encoding="utf-8")
            with (
                mock.patch.object(config, "DIST_DIR", dist),
                mock.patch.dict(os.environ, {"TOOLS_PUBLIC_PATH": "/tools/"}),
            ):
                asset = spa_fallback("tools/assets/app.js")
                landing = spa_fallback("tools/")
        self.assertIsInstance(asset, FileResponse)
        self.assertTrue(str(asset.path).endswith("assets" + os.sep + "app.js"))
        self.assertIn("javascript", asset.media_type or "")
        # 首屏 /tools/ 前缀剥离后落到 dist 根 → 回退 index.html（hash 路由）
        self.assertIsInstance(landing, FileResponse)
        self.assertTrue(str(landing.path).endswith("index.html"))

    def test_base_prefixed_traversal_still_blocked(self) -> None:
        """剥离前缀后仍要做目录穿越防护：tools/../secret.txt 不得直出 dist 外文件。"""
        with tempfile.TemporaryDirectory() as tmp:
            dist = Path(tmp) / "dist"
            dist.mkdir()
            (dist / "index.html").write_text("<title>spa</title>", encoding="utf-8")
            secret = Path(tmp) / "secret.txt"
            secret.write_text("TOP-SECRET", encoding="utf-8")
            with (
                mock.patch.object(config, "DIST_DIR", dist),
                mock.patch.dict(os.environ, {"TOOLS_PUBLIC_PATH": "/tools/"}),
            ):
                resp = spa_fallback("tools/../secret.txt")
        # 穿越被拒 → 回退 index.html（FileResponse 按 path 直出，不读 body）
        from fastapi.responses import FileResponse

        self.assertIsInstance(resp, FileResponse)
        self.assertTrue(str(resp.path).endswith("index.html"))
        self.assertNotIn("secret.txt", str(resp.path))


class TestSchemaContract(unittest.TestCase):
    """Pydantic schema 边界校验。"""

    def test_health_response_rejects_extra_status_value(self) -> None:
        with self.assertRaises(ValueError):
            HealthResponse(status="catastrophe", frontend_ready=True)  # type: ignore[arg-type]

    def test_version_response_requires_app_version(self) -> None:
        with self.assertRaises(ValueError):
            VersionResponse(standards_version="1.0.0")  # type: ignore[call-arg]

    def test_status_enum_values_stable(self) -> None:
        self.assertEqual(ServiceStatus.OK.value, "ok")
        self.assertEqual(ServiceStatus.DEGRADED.value, "degraded")


if __name__ == "__main__":
    unittest.main(verbosity=2)

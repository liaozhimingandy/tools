"""鉴权骨架（预留 Logto 统一认证，可运行期切换四种 provider）。

设计目标：
  1. user_sub 的唯一可信来源是「鉴权 provider 解析出的 token/头」，
     绝不接受 body / path / query 里的 user_id —— 这是多租户越权的第一道防线。
     （passthrough 模式是明确的临时例外：见下方安全退化说明。）
  2. 四种 provider 可运行期切换：
     - passthrough：暂时不鉴权，直接信任 X-User-Sub 头；当前默认，配合前端 Logto 登录态。
     - dev  ：读 X-User-Sub 头，仅本地联调用；health/mode 会暴露风险标识。
     - logto：真实 JWT 校验（PyJWT + JWKS + RS256 + iss/aud/exp），
              租户配置留空，填入即生效，无需改代码。
     - stub ：测试注入固定身份，供契约测试使用。
  3. Logto 校验实现按 OIDC 最佳实践写全（算法白名单、issuer/audience/exp 校验、
     JWKS 缓存与自动刷新），即使本轮 tenant 为空也不是「空壳」。

⚠️ passthrough 是用户明确要求的「暂时后端不鉴权」阶段方案，安全退化点务必知悉：
  - 任何人只要能访问 API，即可伪造任意 X-User-Sub 读写/覆盖/删除「他人」的云端密文。
  - value 仍是零知识密文，他人无法解密；但完整性（覆盖）与可用性（删除）不受保护。
  - 前端会自行判断「有 Logto 登录信息才同步」，这是本阶段的软门禁，而非服务端强校验。
  - 正式多用户上线前，务必切 TOOLS_AUTH_MODE=logto，让后端真正校验 JWT 并自行从
    token 解析 sub（前端无需改动：同时发送 X-User-Sub 与 Authorization: Bearer）。

关于用户表：不建。user_sub 即 Logto 的 `sub` claim（稳定、全局唯一）。
用户展示信息（昵称/头像/邮箱）一律由前端从 Logto userinfo/id_token 取，
后端不落库、不缓存，符合「无用户表」与零知识双重约束。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class UnauthorizedError(Exception):
    def __init__(self, message: str = "unauthorized", code: str = "UNAUTHORIZED") -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class Principal:
    """已认证主体。sub 为唯一可信用户标识。"""

    sub: str
    mode: str
    claims: dict[str, Any] | None = None


class AuthProvider(Protocol):
    mode: str

    def authenticate(self, *, headers: dict[str, str]) -> Principal:
        """从请求头解析身份；失败抛 UnauthorizedError。"""
        ...


# --------------------------------------------------------------------------- #
# 暂时不鉴权：信任请求头声明的 sub（明确标注为不安全，仅过渡期）
# --------------------------------------------------------------------------- #


class PassthroughProvider:
    """「暂时后端不鉴权」阶段实现：直接采用前端声明的 X-User-Sub。

    与 DevHeaderProvider 的区别：头缺失时不拒绝，而是回落到可配置的默认 sub，
    因此该模式永不产生 401——这与「后端不鉴权、前端自行判断是否同步」的阶段目标一致。
    归属隔离仍依赖 sub（RLS + 应用层 WHERE），但 sub 可被客户端伪造，见模块 docstring。
    """

    mode = "passthrough"

    def __init__(self, header: str = "X-User-Sub", default_sub: str = "anonymous") -> None:
        self._header = header
        self._default_sub = (default_sub or "").strip() or "anonymous"

    def authenticate(self, *, headers: dict[str, str]) -> Principal:
        raw = next((v for k, v in headers.items() if k.lower() == self._header.lower()), None)
        sub = (raw or "").strip() or self._default_sub
        if len(sub) > 256:
            raise UnauthorizedError("invalid user sub")
        return Principal(sub=sub, mode=self.mode)


# --------------------------------------------------------------------------- #
# 开发期：信任请求头（明确标注为不安全，仅 dev）
# --------------------------------------------------------------------------- #


class DevHeaderProvider:
    mode = "dev"

    def __init__(self, header: str = "X-User-Sub") -> None:
        self._header = header

    def authenticate(self, *, headers: dict[str, str]) -> Principal:
        raw = next((v for k, v in headers.items() if k.lower() == self._header.lower()), None)
        if not raw or not raw.strip():
            raise UnauthorizedError(f"missing {self._header} (dev auth mode)")
        sub = raw.strip()
        if len(sub) > 256:
            raise UnauthorizedError("invalid user sub")
        return Principal(sub=sub, mode=self.mode)


# --------------------------------------------------------------------------- #
# 测试：固定身份
# --------------------------------------------------------------------------- #


class StubProvider:
    mode = "stub"

    def __init__(self, sub: str = "test-user") -> None:
        self._sub = sub

    def authenticate(self, *, headers: dict[str, str]) -> Principal:
        return Principal(sub=self._sub, mode=self.mode)


# --------------------------------------------------------------------------- #
# Logto：真实 JWT 校验（tenant 配置留空即可，填了就生效）
# --------------------------------------------------------------------------- #


class LogtoJWTProvider:
    """Logto OIDC access token 校验。

    需要：issuer（如 https://xxx.logto.app/oidc）、audience（resource API 标识）、
    jwks_url（如 https://xxx.logto.app/oidc/.well-known/jwks.json）。
    三者任一为空 → 视为未配置，任何请求都拒绝（fail closed，绝不裸奔）。

    校验项：签名(RS256)、iss、aud、exp/nbf、sub 存在且为字符串、
    token_use=access_token（若 claim 存在）。密钥由 PyJWKClient 缓存并自动刷新。
    """

    mode = "logto"
    ALGORITHMS = ["RS256"]

    def __init__(
        self,
        *,
        issuer: str,
        audience: str,
        jwks_url: str,
        leeway: int = 30,
        clock_skew_tolerance: int = 60,
    ) -> None:
        self._issuer = issuer.strip().rstrip("/")
        self._audience = audience.strip()
        self._jwks_url = jwks_url.strip()
        self._leeway = leeway
        self._tolerance = clock_skew_tolerance
        self._client: Any | None = None  # PyJWKClient，延迟构造

    @property
    def configured(self) -> bool:
        return bool(self._issuer and self._audience and self._jwks_url)

    def _jwt_module(self) -> Any:
        import jwt  # PyJWT，延迟导入（可选依赖，dev/stub 模式不需要）

        return jwt

    def _get_client(self) -> Any:
        if self._client is None:
            jwt = self._jwt_module()
            self._client = jwt.PyJWKClient(self._jwks_url, cache_jwk_set=True, lifespan=300)
        return self._client

    def authenticate(self, *, headers: dict[str, str]) -> Principal:
        if not self.configured:
            raise UnauthorizedError("Logto is not configured (fail-closed)", code="AUTH_NOT_CONFIGURED")

        auth = next((v for k, v in headers.items() if k.lower() == "authorization"), "")
        if not auth.lower().startswith("bearer "):
            raise UnauthorizedError("missing bearer token")
        token = auth[7:].strip()
        if not token:
            raise UnauthorizedError("empty bearer token")

        jwt = self._jwt_module()
        try:
            signing_key = self._get_client().get_signing_key_from_jwt(token).key
            claims = jwt.decode(
                token,
                signing_key,
                algorithms=self.ALGORITHMS,  # 算法白名单，防 alg=none / HS 混淆
                audience=self._audience,
                issuer=self._issuer,
                leeway=self._leeway,
                options={"require": ["exp", "iat", "sub", "iss", "aud"]},
            )
        except jwt.PyJWTError as exc:
            raise UnauthorizedError(f"invalid token: {type(exc).__name__}") from None

        sub = claims.get("sub")
        if not isinstance(sub, str) or not sub.strip():
            raise UnauthorizedError("token missing sub")
        # 可选：拒绝 id_token 冒充 access_token
        use = claims.get("token_use")
        if use is not None and use != "access_token":
            raise UnauthorizedError("wrong token use")
        return Principal(sub=sub.strip(), mode=self.mode, claims=claims)


# --------------------------------------------------------------------------- #
# 工厂：按配置装配
# --------------------------------------------------------------------------- #


def build_provider(
    *,
    mode: str,
    logto_issuer: str = "",
    logto_audience: str = "",
    logto_jwks_url: str = "",
    dev_header: str = "X-User-Sub",
    passthrough_header: str = "X-User-Sub",
    passthrough_default_sub: str = "anonymous",
    stub_sub: str = "test-user",
) -> AuthProvider:
    mode = (mode or "passthrough").strip().lower()
    if mode == "stub":
        return StubProvider(stub_sub)
    if mode == "logto":
        return LogtoJWTProvider(
            issuer=logto_issuer, audience=logto_audience, jwks_url=logto_jwks_url
        )
    if mode == "dev":
        return DevHeaderProvider(dev_header)
    if mode == "passthrough":
        return PassthroughProvider(passthrough_header, passthrough_default_sub)
    raise ValueError(f"unknown auth mode: {mode}")

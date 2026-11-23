"""门户默认种子（内存模式），与 sql/005_apps_portal_seed.sql 内容对应。

两处种子必须保持一致：PG 走 SQL 迁移，memory 模式走这里。
已确认可访问的只有 Also Account；其余保持 draft + 空 launch_url，不编造地址。
"""

from __future__ import annotations

from .portal_models import AppRecord, CategoryRecord

DEFAULT_CATEGORIES: tuple[CategoryRecord, ...] = (
    CategoryRecord(code="all", name="全部应用", description="浏览所有应用", icon="apps", sort_order=0),
    CategoryRecord(code="ai", name="AI 工具", description="人工智能相关应用与工具", icon="ai", sort_order=10),
    CategoryRecord(code="productivity", name="效率工具", description="提升工作与协作效率", icon="desktop", sort_order=20),
    CategoryRecord(code="creation", name="内容创作", description="写作、设计、音视频创作", icon="palette", sort_order=30),
    CategoryRecord(code="game", name="游戏娱乐", description="休闲游戏与娱乐应用", icon="gamepad", sort_order=40),
    CategoryRecord(code="finance", name="金融投资", description="量化、行情与投资研究", icon="chart-bar", sort_order=50),
    CategoryRecord(code="social", name="社交社区", description="沟通与社区类应用", icon="usergroup", sort_order=60),
    CategoryRecord(code="other", name="其他服务", description="未归类的服务与应用", icon="server", sort_order=70),
)


def _app(
    code: str,
    name: str,
    subtitle: str,
    description: str,
    *,
    app_type: str = "application",
    categories: tuple[str, ...] = (),
    launch_url: str = "",
    status: str = "draft",
    published: bool = False,
    auth_required: bool = False,
    featured: bool = False,
    home: bool = False,
    is_new: bool = False,
    sort_order: int = 0,
) -> AppRecord:
    return AppRecord(
        code=code,
        name=name,
        subtitle=subtitle,
        description=description,
        detail=description,
        launch_url=launch_url,
        app_type=app_type,  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        visibility="public",
        auth_required=auth_required,
        is_featured=featured,
        show_on_home=home,
        is_new=is_new,
        sort_order=sort_order,
        published_at="2026-01-01T00:00:00.000000Z" if published else None,
        categories=categories,
    )


DEFAULT_APPS: tuple[AppRecord, ...] = (
    _app(
        "ALSO_ACCOUNT", "Also Account", "统一身份认证中心",
        "管理你的 Also 账号、应用授权与登录安全。",
        app_type="service", categories=("productivity", "other"),
        launch_url="https://account.alsoapp.com/",
        status="published", published=True, featured=True, home=True, sort_order=10,
    ),
    _app(
        "ALSO_TOOLS", "Also Tools", "实用小工具集合",
        "浏览器内运行的零知识小工具，数据留在你的设备。",
        categories=("productivity", "other"), sort_order=20,
    ),
    _app(
        "THIS_CITY", "thisCity", "城市探索游戏",
        "在真实城市地图中探索、打卡与解锁故事。",
        app_type="game", categories=("game", "other"), sort_order=30,
    ),
    _app(
        "AI_NEWS", "AI News", "人工智能资讯聚合",
        "每日精选 AI 行业动态、论文与产品发布。",
        categories=("ai", "other"), sort_order=40,
    ),
    _app(
        "AI_DRAMA", "AI Drama", "AI 短剧创作工作台",
        "分阶段创作、结构化输出，让灵感变成剧本。",
        categories=("ai", "other"), auth_required=True, is_new=True, sort_order=50,
    ),
    _app(
        "ALPHA_QUANT", "AlphaQuant", "量化交易研究系统",
        "多维因子采集、因子挖掘与策略回测。",
        categories=("ai", "finance", "other"), auth_required=True, sort_order=60,
    ),
    _app(
        "TUIWEN", "Tuiwen", "推文社区",
        "分享想法、关注感兴趣的人与话题。",
        categories=("social", "other"), sort_order=70,
    ),
)

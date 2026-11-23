-- Also Apps 门户初始化数据（幂等，可重复执行）
--
-- 原则：
--   1. 只写「已确认真实存在」的访问地址；无法确认的一律 launch_url='' + status='draft'。
--      绝不编造 URL——草稿应用前端不会给出「立即使用」入口。
--   2. 7 个示例应用按任务清单落库，code 全局唯一；重复执行只更新描述类字段，
--      不覆盖管理员后续在后台修改的 status / visibility / sort_order / launch_url。
--   3. 分类初始化 8 项，ON CONFLICT DO NOTHING 保证幂等。
--
-- 用法：psql "$TOOLS_ADMIN_DSN" -f sql/005_apps_portal_seed.sql

-- --------------------------------------------------------------------------- -- 分类
INSERT INTO app_categories (code, name, description, icon, sort_order) VALUES
    ('all',          '全部应用', '浏览所有应用',              'apps',        0),
    ('ai',           'AI 工具',  '人工智能相关应用与工具',    'ai',         10),
    ('productivity', '效率工具', '提升工作与协作效率',        'desktop',     20),
    ('creation',     '内容创作', '写作、设计、音视频创作',    'palette',     30),
    ('game',         '游戏娱乐', '休闲游戏与娱乐应用',        'gamepad',     40),
    ('finance',      '金融投资', '量化、行情与投资研究',      'chart-bar',   50),
    ('social',       '社交社区', '沟通与社区类应用',          'usergroup',   60),
    ('other',        '其他服务', '未归类的服务与应用',        'server',      70)
ON CONFLICT (code) DO NOTHING;

-- --------------------------------------------------------------------------- -- 示例应用
-- 已确认可填 launch_url 的：Also Account（统一身份，真实域名）。
-- 其余保持 draft + 空地址，由管理员上线后在后台补齐。
INSERT INTO portal_apps
    (code, name, subtitle, description, detail, icon_url, cover_url, launch_url,
     app_type, open_mode, status, visibility, auth_required, is_featured, show_on_home, is_new, sort_order, published_at)
VALUES
    ('ALSO_ACCOUNT', 'Also Account', '统一身份认证中心',
     '管理你的 Also 账号、应用授权与登录安全。',
     'Also Account 是 Also 生态的统一身份服务，基于 Logto 提供安全的登录、注册与应用授权能力，一处登录、处处可用。',
     '', '', 'https://account.alsoapp.com/',
     'service', 'new_tab', 'published', 'public', FALSE, TRUE, TRUE, FALSE, 10, now()),

    ('ALSO_TOOLS', 'Also Tools', '实用小工具集合',
     '浏览器内运行的零知识小工具，数据留在你的设备。',
     'Also Tools 汇集日常开发与生活所需的轻量工具。首个工具「锦囊 SafeKeep」采用浏览器端 AES-256-GCM 加密，主密码与恢复码双钥匙解锁，服务端只保存密文。',
     '', '', '',
     'application', 'new_tab', 'draft', 'public', FALSE, FALSE, FALSE, FALSE, 20, NULL),

    ('THIS_CITY', 'thisCity', '城市探索游戏',
     '在真实城市地图中探索、打卡与解锁故事。',
     'thisCity 是一款以真实城市为舞台的探索类游戏，把街巷、地标与本地故事串成一条可玩的线索。',
     '', '', '',
     'game', 'new_tab', 'draft', 'public', FALSE, FALSE, FALSE, FALSE, 30, NULL),

    ('AI_NEWS', 'AI News', '人工智能资讯聚合',
     '每日精选 AI 行业动态、论文与产品发布。',
     'AI News 聚合人工智能领域的资讯与研究成果，帮助开发者快速了解行业脉络。',
     '', '', '',
     'application', 'new_tab', 'draft', 'public', FALSE, FALSE, FALSE, FALSE, 40, NULL),

    ('AI_DRAMA', 'AI Drama', 'AI 短剧创作工作台',
     '分阶段创作、结构化输出，让灵感变成剧本。',
     'AI Drama 是面向短剧创作者的分阶段创作工具，通过统一模型路由与结构化校验，把大纲、分镜与对白串成可复现的创作流程。',
     '', '', '',
     'application', 'new_tab', 'draft', 'public', TRUE, FALSE, FALSE, TRUE, 50, NULL),

    ('ALPHA_QUANT', 'AlphaQuant', '量化交易研究系统',
     '多维因子采集、因子挖掘与策略回测。',
     'AlphaQuant 是自建的量化交易研究与自动化系统，覆盖题材、基本面、资金、舆情与宏观等多维因子，支持因子库管理、自研机器学习因子挖掘与策略配置。',
     '', '', '',
     'application', 'new_tab', 'draft', 'public', TRUE, FALSE, FALSE, FALSE, 60, NULL),

    ('TUIWEN', 'Tuiwen', '推文社区',
     '分享想法、关注感兴趣的人与话题。',
     'Tuiwen 是一个轻量内容社区，支持发帖、评论、关注、点赞与收藏。',
     '', '', '',
     'application', 'new_tab', 'draft', 'public', FALSE, FALSE, FALSE, FALSE, 70, NULL)
ON CONFLICT (code) DO UPDATE SET
    -- 仅同步展示文案；上线状态与地址由后台管理，种子不覆盖
    subtitle    = EXCLUDED.subtitle,
    description = EXCLUDED.description,
    detail      = EXCLUDED.detail,
    app_type    = EXCLUDED.app_type,
    updated_at  = now();

-- --------------------------------------------------------------------------- -- 分类关联（全部应用放 other，AI 类放 ai）
INSERT INTO application_categories (app_id, category_id)
SELECT a.id, c.id FROM portal_apps a
JOIN app_categories c ON c.code = 'other'
WHERE a.code IN ('ALSO_ACCOUNT','ALSO_TOOLS','THIS_CITY','AI_NEWS','AI_DRAMA','ALPHA_QUANT','TUIWEN')
ON CONFLICT DO NOTHING;

INSERT INTO application_categories (app_id, category_id)
SELECT a.id, c.id FROM portal_apps a
JOIN app_categories c ON c.code = 'ai'
WHERE a.code IN ('AI_NEWS','AI_DRAMA','ALPHA_QUANT')
ON CONFLICT DO NOTHING;

INSERT INTO application_categories (app_id, category_id)
SELECT a.id, c.id FROM portal_apps a
JOIN app_categories c ON c.code = 'game'
WHERE a.code = 'THIS_CITY'
ON CONFLICT DO NOTHING;

INSERT INTO application_categories (app_id, category_id)
SELECT a.id, c.id FROM portal_apps a
JOIN app_categories c ON c.code = 'productivity'
WHERE a.code IN ('ALSO_ACCOUNT','ALSO_TOOLS')
ON CONFLICT DO NOTHING;

INSERT INTO application_categories (app_id, category_id)
SELECT a.id, c.id FROM portal_apps a
JOIN app_categories c ON c.code = 'finance'
WHERE a.code = 'ALPHA_QUANT'
ON CONFLICT DO NOTHING;

INSERT INTO application_categories (app_id, category_id)
SELECT a.id, c.id FROM portal_apps a
JOIN app_categories c ON c.code = 'social'
WHERE a.code = 'TUIWEN'
ON CONFLICT DO NOTHING;

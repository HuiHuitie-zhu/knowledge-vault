#!/usr/bin/env python3
"""Seed Knowledge Vault with sample data to demo the system."""

import sqlite3, os, sys

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vault.db")


def seed():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")

    # Ensure schema exists
    with open(os.path.join(os.path.dirname(__file__), "schema.sql")) as f:
        conn.executescript(f.read())

    # Clear existing data for fresh seed
    conn.execute("DELETE FROM note_links")
    conn.execute("DELETE FROM links")
    conn.execute("DELETE FROM note_tags")
    conn.execute("DELETE FROM tags")
    conn.execute("DELETE FROM note_embeddings")
    conn.execute("DELETE FROM notes")

    # ─── Notes ────────────────────────────────────────────────────────────────

    notes = [
        (1,  "Python 装饰器", "装饰器是修改函数或类行为的函数。本质是一个接受函数并返回新函数的高阶函数。\n\n基本语法：\n```python\n@decorator\ndef func():\n    pass\n```\n等价于 `func = decorator(func)`。\n\n常见用途：日志、权限校验、缓存、重试。", "reference", "python,技巧"),
        (2,  "Functools 模块", "functools 提供高阶函数工具。\n\n核心函数：\n- `lru_cache()` — 函数级缓存\n- `partial()` — 偏函数\n- `reduce()` — 累积归约\n- `wraps()` — 保留被装饰函数的元信息", "reference", "python,内置库"),
        (3,  "SQLite FTS5 全文搜索", "SQLite 内置的全文搜索引擎，无需外部依赖。\n\n特点：\n- 比 LIKE 快 10-100 倍\n- 支持布尔查询、前缀匹配\n- 支持自动触发器同步\n- 需要 tokenizer 支持中文\n\n```sql\nCREATE VIRTUAL TABLE docs USING fts5(title, body);\nSELECT * FROM docs WHERE docs MATCH 'hello AND world';\n```", "reference", "sqlite,搜索,技术"),
        (4,  "macOS 开发环境配置", "基础工具链：\n- Homebrew 包管理器\n- Python 3.10+ (通过 uv)\n- Git + GitHub CLI\n- VS Code / Cursor\n\n环境变量放在 .zshrc。", "checklist", "macos,配置,工具"),
        (5,  "API 认证设计原则", "1. 不自己实现认证——用标准协议（OAuth2 / JWT）\n2. Token 有过期时间，不用长生命期 token\n3. HTTPS 是前提\n4. 敏感操作额外验证（MFA）\n5. 日志审计不可少\n\n⚠️ 常见陷阱：JWT 不加密敏感信息（base64 不是加密）", "rule", "api,安全,设计"),
        (6,  "D3.js forceLink 的 source/target 陷阱", "D3.forceLink 要求 link 数据有 `source` 和 `target` 字段。如果你的数据用其他字段名（如 `s`/`t`），D3 不会报错——它只是静默地不解析链接，布局不显示任何边。\n\n```javascript\n// ❌ 不工作\n{ s: 1, t: 2 }\n// ✅ 必须\n{ source: 1, target: 2 }\n```", "trap", "d3,前端,可视化"),
        (7,  "个人知识库系统架构", "## 当前理解\n使用 SQLite + FTS5 + BGE 向量嵌入构建本地知识库，D3.js + Canvas 2D 做知识图谱可视化。\n\n## 证据链\n- **2026-06-25** | 完成三层分级（L0/L1/L2）和 domain 分类\n- **2026-06-26** | 完成 Typed Edges 体系 + Dream Cycle\n\n## Why\n需要一个本地优先、不依赖云服务的个人知识管理方案。", "note", "知识库,架构,项目"),
        (8,  "Canvas 2D 坐标系统", "Canvas 变换管线：\n```javascript\ncx.save();\ncx.translate(W/2, H/2);  // 原点移到中心\ncx.scale(Z, Z);           // 缩放\ncx.translate(OX, OY);     // 平移\n// 在 D3 的 (x,y) 坐标上绘制\ncx.restore();\n```\n屏幕→图谱坐标转换：\n`x = (clientX - left - W/2) / Z - OX`", "reference", "前端,css,canvas"),
        (9,  "Rust 所有权规则", "1. 每个值有且只有一个所有者\n2. 所有权可以转移（move）\n3. 引用 &T 和 &mut T 互斥\n\n这三条规则在编译期检查，零运行时开销。", "reference", "rust,语言"),
        (10, "HTTP 状态码速查", "200 OK — 请求成功\n201 Created — 资源已创建\n301 Moved Permanently — 永久重定向\n400 Bad Request — 请求格式错误\n401 Unauthorized — 未认证\n403 Forbidden — 已认证但无权限\n404 Not Found — 资源不存在\n500 Internal Server Error — 服务器异常\n502 Bad Gateway — 上游服务异常", "standard", "http,api,网络"),
        (11, "知识图谱可视化性能优化", "## 当前理解\nCanvas 2D + D3.js 在 100+ 节点场景的优化方案：\n1. Tick 节流：每 3 帧渲染一次\n2. 事件驱动渲染：非交互期零 CPU\n3. 选中节点呼吸动画（不全局动画）\n4. 隐藏非关联节点：渲染量降 90%\n5. 无 shadowBlur（用 globalAlpha 替代）\n\n## 证据链\n- **2026-06-25** | 实测 113 节点 + 181 连接，Canvas 2D 渲染 <1ms | 来源: 性能测试\n\n## Why\nSVG 在 100+ 节点会卡顿，WebGL 大材小用，Canvas 2D 是甜点。", "note", "前端,性能,可视化"),
        (12, "Docker 常用命令", "```bash\ndocker ps              # 运行中的容器\ndocker images          # 本地镜像列表\ndocker build -t tag .  # 构建\ndocker run -d -p 80:80 image  # 运行\ndocker logs -f cid     # 看日志\ndocker exec -it cid sh # 进容器\ndocker compose up -d   # 启动服务栈\n```", "reference", "docker,运维,工具"),
        (13, "JWT 安全注意事项", "⚠️ JWT 的 payload 是 base64 编码，不是加密——不要在 payload 里放敏感信息。\n\n其他注意事项：\n1. 签名密钥要用强随机数\n2. 设置合理的过期时间（15-60 分钟）\n3. Refresh token 使用不同的密钥\n4. 使用 `sub` 字段标识用户，不要用 `user_id` 自定义字段", "trap", "安全,auth,api"),
        (14, "Linear 设计系统配色", "暗色主题色彩体系：\n- 背景三层递进：#08090a → #0f1011 → #191a1b\n- 文字：主 #f7f8f8 / 正文 #d0d6e0 / 辅助 #8a8f98\n- 交互色：靛蓝 #5e6ad2\n- 缓动：easeOutCubic 700ms\n\n文字风格：全部大写 + 宽松间距用于标签和元数据。", "standard", "设计,前端,css"),
        (15, "Git 协作流程", '```bash\ngit checkout -b feat/my-feature  # 从 main 开分支\n# ... 开发 ...\ngit add -p                       # 分块审查式提交\ngit commit -m "feat: ..."\ngit push -u origin HEAD\n# 开 PR → Review → Squash merge → 删分支\n```\n提交信息规范：type(scope): description', "standard", "git,协作,流程"),
    ]

    for n in notes:
        nid, title, content, stype, tags = n
        tag_text = " ".join(t.strip() for t in tags.split(",") if t.strip())
        conn.execute(
            "INSERT INTO notes (id, title, content_raw, summary_raw, tags_text, source_type) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (nid, title, content, content[:200], tag_text, stype)
        )

    # ─── Tags ─────────────────────────────────────────────────────────────────

    all_tags = set()
    for n in notes:
        for t in n[4].split(","):
            all_tags.add(t.strip())

    for tag in sorted(all_tags):
        conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))

    # ─── Note-Tag associations ────────────────────────────────────────────────

    tag_cache = {}
    for t in all_tags:
        row = conn.execute("SELECT id FROM tags WHERE name=?", (t,)).fetchone()
        if row:
            tag_cache[t] = row["id"]

    for n in notes:
        nid = n[0]
        for t in n[4].split(","):
            t = t.strip()
            if t in tag_cache:
                conn.execute("INSERT OR IGNORE INTO note_tags (note_id, tag_id) VALUES (?, ?)",
                             (nid, tag_cache[t]))

    # ─── Links (Typed Edges) ─────────────────────────────────────────────────

    links = [
        (1, 2, "uses"),           # 装饰器 使用 functools
        (1, 5, "references"),     # 装饰器 可用于 API 认证
        (2, 0, None),             # skip
        (3, 0, None),             # skip
        (5, 13, "references"),    # API 认证 关联 JWT 安全
        (6, 8, "references"),     # D3 陷阱 关联 Canvas 坐标
        (7, 3, "references"),     # 知识库架构 使用 SQLite FTS5
        (7, 11, "references"),    # 知识库架构 关联 性能优化
        (8, 11, "references"),    # Canvas 坐标 关联 性能优化
        (10, 5, "references"),    # HTTP 状态码 关联 API 认证
        (11, 6, "references"),    # 性能优化 关联 D3 陷阱
        (14, 8, "references"),    # Linear 设计 关联 Canvas 渲染
        (7, 14, "references"),    # 知识库架构 使用 Linear 设计
        (12, 4, "references"),    # Docker 关联 开发环境
        (15, 4, "references"),    # Git 流程 关联 开发环境
    ]

    link_types_map = {"uses": "uses", "references": "references"}

    for src, dst, ltype in links:
        if dst == 0 or src == dst:
            continue
        lt = ltype or "references"
        conn.execute(
            "INSERT INTO links (from_note_id, to_note_id, link_type, link_source) "
            "VALUES (?, ?, ?, 'auto')",
            (src, dst, lt)
        )

    # ─── Rebuild FTS5 ────────────────────────────────────────────────────────

    conn.execute("INSERT INTO notes_fts(notes_fts) VALUES('rebuild')")
    conn.commit()
    conn.close()

    print(f"[seed] Added {len(notes)} notes, {len(all_tags)} tags, "
          f"{len([l for l in links if l[1] != 0])} links.")
    print(f"[seed] DB: {DB}")
    print(f"[seed] Run 'python3 server.py' then open http://localhost:51420")


if __name__ == "__main__":
    seed()

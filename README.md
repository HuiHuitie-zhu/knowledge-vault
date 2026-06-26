<div align="center">
  <img src="assets/icon.svg" width="64" height="64" alt="Knowledge Vault">
  <h1>Knowledge Vault 🏛️</h1>
  <p>个人知识库 + 知识图谱可视化系统</p>
  <p><em>SQLite · FTS5 · 向量检索 · D3.js 力导向图 · Canvas 2D</em></p>
  <br>
  <p>
    <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python" alt="Python">
    <img src="https://img.shields.io/badge/SQLite-FTS5-003B57?logo=sqlite" alt="SQLite">
    <img src="https://img.shields.io/badge/D3.js-v7-F9A03C?logo=d3.js" alt="D3.js">
    <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT">
  </p>
</div>

---

## 为什么要做这个？

我积累了大量笔记、代码片段、项目文档和个人思考——散布在 Obsidian、Apple Notes、AI 对话记录里。我想要的不仅是文件夹里的 Markdown 文件，而是**看见知识之间的连接**——哪些主题有关联、哪些概念建立在哪些之上、哪里还有知识缺口。

所以有了这个项目：一个**本地优先、隐私保护**的个人知识库系统，配上一个交互式的知识图谱可视化界面。

---

## 系统预览

```
┌──────────────────────────────────────────────────────────┐
│  知识图谱                          ☾                      │
│  ┌──────────────────────────────┐  🔍 搜索节点...        │
│  │                              │                         │
│  │      ○━━━━━━○                │  [所有] [规则] [陷阱]  │
│  │     ╱        ╲               │                         │
│  │    ○          ○━━○           │  ● #42 配置要点        │
│  │    │          │              │  ● #38 API 认证流程    │
│  │    ○──────────○              │  ○ #15 错误码处理      │
│  │     ╲        ╱               │                         │
│  │      ○━━━━━━○                │  96 节点     30 显示    │
│  └──────────────────────────────┘                         │
│    关系: ━━ references ━━ uses ━━ part_of                 │
│                                                           │
│    滚轮 · 缩放 | 拖拽 · 平移 | 点击 · 查看 | Esc 关闭    │
└──────────────────────────────────────────────────────────┘
```

### 核心交互

| 操作 | 效果 |
|------|------|
| **点击节点** | 镜头聚焦到该节点及其关联节点（隐藏非关联节点），右侧弹出详情面板 |
| **双击画布 / Esc** | 回到全局视图 |
| **滚轮** | 缩放 |
| **拖拽** | 平移画布 |
| **搜索** | 按标题/标签过滤 |
| **类型过滤** | 按规则/陷阱/引用等类型筛选 |
| **日夜切换** | ☽ / ☀ |
| **置顶** | ☆ 标记重要节点，置顶在列表顶部 |

---

## ✨ 核心功能

| 特性 | 说明 |
|------|------|
| **本地优先** | 所有数据存在 SQLite 里，不依赖任何云服务，数据完全在你手里 |
| **双擎搜索** | FTS5 全文搜索 + BGE 语义向量搜索，关键词和语义理解双重覆盖 |
| **三级分层** | L0 全局铁律（行为规则）→ L1 项目规范 → L2 详细参考，按需加载 |
| **关系类型体系** | 10 种语义边（引用/使用/扩展/矛盾/相似...），关系不只是一种 |
| **交互式知识图谱** | D3.js 力导向布局 + Canvas 2D 渲染，点击节点聚焦关联网 |
| **Linear 暗色设计** | 深色三层背景、Inter 字体、靛蓝交互色、700ms easeOutCubic 缓动 |
| **原生桌面应用** | macOS WKWebView 封装，双击即用，关闭即停，无后台残留 |
| **夜间自动维护** | Dream Cycle 定时重建索引、合并清理、写入日志 |
| **自动知识提取** | 双 Agent 从对话中自动提炼可复用知识存入知识库 |

---

## 🏗 系统架构

```
┌────────────────────────────────────────────────────────────────────┐
│                         Knowledge Vault                           │
├──────────────┬──────────────────────────┬─────────────────────────┤
│   CLI 工具   │      MCP 服务器           │    知识图谱可视化       │
│              │                          │                         │
│  vault.py    │  knowledge_mcp.py        │  server.py (API)        │
│  ──────────  │  ──────────────────      │  ───────────────       │
│  add / search│  knowledge_search        │  GET /api/data          │
│  list / stats│  knowledge_hybrid_search │  GET /api/node?id=N     │
│  reindex     │  knowledge_semantic_search│  GET /api/pin?id=N      │
│  consolidate │  knowledge_list          │  GET / → index.html     │
│              │  knowledge_get           │                         │
│              │  knowledge_graph         │  index.html (前端)       │
│              │                          │  ├── D3.js v7           │
├──────────────┴──────────────────────────┤  ├── Canvas 2D          │
│                                         │  └── Linear Design      │
│           SQLite + FTS5 + 向量嵌入      │                         │
│           ~/.hermes/knowledge.db        │  kgraph-native          │
│                                         │  (WKWebView 原生应用)    │
└────────────────────────────────────────────────────────────────────┘
```

### 数据流向

```
用户输入 → vault.py / MCP → 结构化笔记 → SQLite 存储 → 图谱数据 API → D3 渲染
                                  ↕
                           FTS5 索引 + 向量嵌入
                                  ↕
                            Dream Cycle 夜间维护
```

---

## 🚀 快速开始

### 前置要求

- Python 3.10+
- SQLite 3 (系统自带 macOS/Linux)

### 安装

```bash
# 克隆
git clone https://github.com/HuiHuitie-zhu/knowledge-vault.git
cd knowledge-vault

# 安装依赖（推荐用 uv 或 venv）
pip install -r requirements.txt

# 构建数据库 + 添加示例数据
python3 vault.py init
python3 seed.py

# 启动知识图谱服务器
python3 server.py

# 打开浏览器
open http://localhost:51420
```

### 基本命令

```bash
# 添加一条笔记
python3 vault.py add "Python 装饰器" "装饰器是修改函数行为的函数..." --tags python,技巧 --type reference

# 添加笔记时建立关联
python3 vault.py add "Functools 模块" "内置高阶函数工具集..." --link-to 1 --link-type uses

# 搜索
python3 vault.py search "装饰器"

# 语义搜索（需要向量模型）
python3 vault.py search "函数增强" --semantic

# 查看统计
python3 vault.py stats

# 重建索引
python3 vault.py reindex [--graph]

# 合并检查
python3 vault.py consolidate
```

---

## 📦 核心设计详解

### 1. 三级分层体系（L0 / L1 / L2）

知识是有层级的——不是所有信息地位相同。

| 层 | 含义 | 加载策略 | 示例 |
|----|------|---------|------|
| **L0 全局铁律** | 行为约束、不可违逆的规则 | 每次会话加载 | 人格设定、安全底线 |
| **L1 项目规范** | 项目级约定、架构决策 | 匹配项目上下文时加载 | API 设计规约、数据库规范 |
| **L2 详细参考** | 具体知识点、笔记、文献 | 按需搜索 | 某框架 API 用法、算法笔记 |

### 2. Typed Edges 关系类型体系

大多数知识图谱只有一种关系——"关联"。但这远远不够。Knowledge Vault 定义了 10 种语义边，每条连接都带有明确的含义：

| 关系类型 | 语义 | 图谱着色 | 自动推断条件 |
|----------|------|---------|-------------|
| `references` | 通用引用 | 淡紫灰 `#5a5a7a` | 标签有重叠 |
| `related_to` | 泛关联 | 淡紫灰 `#5a5a7a` | 仅标题重叠 |
| `works_at` | 工作关系 | 靛蓝 `#5e6ad2` | tag 含"公司/项目" |
| `created` | 创建关系 | 绿色 `#22c55e` | — |
| `uses` | 使用关系 | 绿色 `#22c55e` | tag 含"tool/cli/API" |
| `mentions` | 提及 | 灰色 `#94a3b8` | — |
| `builds_on` | 扩展/升级 | 琥珀 `#f59e0b` | 标题含"V{数字}/升级" |
| `contradicts` | 矛盾 | 红色 `#ef4444` | — |
| `similar_to` | 相似 | 紫色 `#8b5cf6` | 同 domain + 共同 tag |
| `part_of` | 子集 | 蓝紫 `#6366f1` | — |

**自动与手动隔离：** 自动推断的关联（`reindex --graph` 生成）和手动创建的关联（`add --link-to` 指定）在数据库中用 `link_source` 字段隔离。`reindex --graph` 只清除自动关联，手动关联永远被保护，不会在重建时丢失。

### 3. 双擎搜索引擎

```
┌─────────────┐     ┌────────────────┐
│ 关键词查询   │     │  语义查询       │
│  (FTS5)     │     │  (BGE 向量)    │
├─────────────┤     ├────────────────┤
│ 精确匹配    │     │ 理解意图        │
│ 支持中文     │     │ 同义词扩展     │
│ 毫秒级响应   │     │ 模糊匹配       │
│ 适合搜索已知 │     │ 适合探索未知   │
└─────────────┘     └────────────────┘
```

- **FTS5 全文索引** — SQLite 内置，无外部依赖，支持中文分词（jieba）
- **BGE 语义向量** — 512 维嵌入，基于 `BAAI/bge-small-zh-v1.5`，~50MB 模型
- **混合策略** — 先用 FTS5 精确匹配，无结果时回退到语义搜索

### 4. 知识图谱可视化

#### 渲染引擎

选择 **Canvas 2D + D3.js** 的组合而非纯 SVG：

| 方案 | 优点 | 缺点 |
|------|------|------|
| SVG (原生 D3) | 开发快，事件绑定方便 | 100+ 节点 DOM 太重，卡顿 |
| WebGL (Three.js) | 性能最好 | 开发成本高，3D 在此场景无意义 |
| **Canvas 2D + D3** | 性能好，开发适中 | 需手动处理 hit-testing |

**关键代码** — Canvas 坐标转换：

```javascript
// 画布变换管线
cx.save();
cx.translate(W/2, H/2);    // 原点移到画布中心
cx.scale(Z, Z);             // 缩放
cx.translate(OX, OY);       // 平移偏移
// ... 在 D3 的 (x,y) 坐标上绘制节点和边
cx.restore();

// 屏幕坐标 → 图谱坐标（用于点击判定）
function gp(e) {
  var r = cv.getBoundingClientRect();
  return {
    x: (e.clientX - r.left - W/2) / Z - OX,
    y: (e.clientY - r.top - H/2) / Z - OY
  };
}
```

#### D3 力导向布局调参

```javascript
var sim = d3.forceSimulation(N)
  .force('link', d3.forceLink(L).distance(25).strength(1.0))
  .force('charge', d3.forceManyBody().strength(-30))
  .force('center', d3.forceCenter())
  .force('collide', d3.forceCollide().radius(function(d) {
    return 6 + (d.ds || 0) * 2;  // 按节点度数自适应
  }))
  .alphaDecay(0.03)    // 约 3 秒稳定
  .velocityDecay(0.4);
```

**设计原则：** 紧凑但不挤——`strength=-30` + `distance=25` 产生紧密的群落结构，让相关节点聚在一起。

#### 性能优化

| 优化点 | 措施 | 效果 |
|--------|------|------|
| Tick 渲染节流 | 每 3 帧渲染一次 | CPU 降至 1/3 |
| 事件驱动渲染 | 只有用户操作时才重绘 | 非交互期零 CPU |
| 选中节点呼吸 | 只用 sin() 动画选中节点 | 避免全节点计算 |
| 无 shadowBlur | 用 globalAlpha 替代 | Canvas 渲染避免昂贵阴影计算 |
| 隐藏非关联节点 | 聚焦时完全跳过绘制 | 渲染量降 90%+ |

#### 连接网络视图（Connection Network View）

这是最核心的交互设计——点击一个节点后：

1. 选中节点 + 它的直接邻居（1-hop）保持可见
2. 所有非关联节点完全隐藏
3. 镜头缓推聚焦到关联子图
4. 边按关系类型着色，选中边高亮
5. 右侧弹出详情面板，显示完整内容和关联节点

这个设计让你在面对 100+ 节点的图谱时不迷失——每次只关注一个节点的"朋友圈"。

### 5. 视觉效果：Linear 暗色设计系统

```
背景: #08090a (最深) → #0f1011 (面板) → #191a1b (浮层)
文字: #f7f8f8 (主要) → #d0d6e0 (正文) → #8a8f98 (辅助) → #62666d (元数据)
交互: #5e6ad2 (靛蓝)
字体: Inter (英文) + PingFang SC (中文)
节点: 节点按类型着色，规则蓝 / 陷阱绿 / 引用紫 / 标准黄...
缓动: 700ms easeOutCubic (所有镜头移动)
```

### 6. 条目格式：Compiled Truth + Timeline

每个知识条目采用双层结构：

```markdown
## 当前理解（Compiled Truth）
当前最佳结论。随知识积累可覆盖更新。
保留最新的综合理解，不保留旧版本。

## 证据链（Timeline）
- **2026-06-26** | [Source: 对话记录] — 原始证据
- **2026-06-25** | [Source: 文档] — 另一证据

## Why（选填）
为什么要做这个决策，有什么上下文？
```

这个格式受 [GBrain](https://github.com/raymondwzhao/gbrain) 项目启发。

### 7. Dream Cycle 夜间自动维护

```
每日凌晨 2:00 ───── 5 阶段流水线 ───── 写入日志
      │
      ├─ 1. Lint       : 健康快照
      ├─ 2. Consolidate: 查重复/低质量
      ├─ 3. Sync       : 重建向量索引
      ├─ 4. Graph      : 重建图谱关联 + 类型推断
      └─ 5. Report     : 最终快照对比
```

全程零 token 消耗（no-agent 模式），结果写入一条日志笔记，可随时查阅。

---

## 🖥 原生 macOS 桌面应用

```
知识图谱.app/
└── Contents/
    ├── MacOS/
    │   ├── kgraph              # bash 生命周期脚本
    │   └── kgraph-native       # 编译的 Swift 二进制 (~90KB)
    ├── Resources/
    │   └── icon.icns           # 完整 Retina 图标集
    └── Info.plist              # ATS + Retina 配置
```

**生命周期设计：** 双击打开 → 启动后端 → 等待就绪 → 打开 WKWebView 窗口（无浏览器工具栏）→ 关闭窗口 → 自动停止后端。双击即用、关闭即停，**不留任何后台残留进程**。

原生 WKWebView 使用 Safari 的底层渲染引擎，相比 Electron 方案节省约 200MB 内存。

---

## 🛠 技术栈

| 层 | 技术 |
|----|------|
| **存储** | SQLite 3 + FTS5 |
| **全文搜索** | SQLite FTS5 + jieba 中文分词 |
| **语义搜索** | BGE (BAAI/bge-small-zh-v1.5) 512-dim 向量 |
| **API 服务器** | Python http.server (~42 lines) |
| **图谱前端** | D3.js v7 (forceSimulation) + Canvas 2D |
| **设计系统** | Linear 暗色精工风格 |
| **桌面应用** | WKWebView (Swift) |
| **Markdown 渲染** | marked.js |

---

## 📂 项目结构

```
knowledge-vault/
├── README.md              # 本文档
├── server.py              # HTTP API 服务器（~50 行）
├── index.html             # 知识图谱可视化前端（单 HTML 文件）
├── vault.py               # CLI 工具（增删查改）
├── seed.py                # 示例数据生成器
├── schema.sql             # 数据库 DDL
├── setup.sh               # 一键安装脚本
├── requirements.txt       # Python 依赖
├── assets/
│   └── icon.svg           # 项目图标
└── LICENSE                # MIT
```

---

## 📊 实际跑出来的数据

这是我在用的知识库状态（2026-06）：

```
笔记: 96    标签: 253    关联: 104    向量: 125
分层: L0=1  L1=5  L2=90
领域: tech=78  fiction=8  note=3  infra=3  project=2  profile=2
质量: 31/96 含 ##Why (32%)
```

---

## 🤔 设计决策笔记

### 为什么用 Canvas 2D 而不是 SVG？

当节点数超过 100 时，SVG DOM 节点数会导致浏览器 layout 卡顿。Canvas 2D 把绘制交给 GPU，同时保留清晰度为文字渲染保留了足够精度。WebGL（Three.js）在 2D 力导向图场景下大材小用。

### 为什么 SQLite 而不是 PostgreSQL / Neo4j？

第一原则：**本地优先**。整个知识库在单文件里随身携带，不需要运行数据库服务器。FTS5 是 SQLite 的隐藏杀手锏，全文搜索能力不输 Elasticsearch 的小规模场景。图数据库对 100-1000 级别的节点过度设计——关系型 + 连接表在这个规模上绰绰有余，且无需额外运维。

### Typed Edges 为什么重要？

大多数知识工具只告诉你"两个东西有关"，但不告诉你怎么关联的。知道 A "引用" B 和知道 A "矛盾" B 是完全不同的信息熵。带语义的边让图谱不只是"好看"，而是可推理的——可以问"哪些引用已经过时"、"哪个方案扩展自哪个"、"谁和谁存在矛盾需要解决"。

---

## 📖 灵感来源

- [GBrain](https://github.com/raymondwzhao/gbrain) — Garry Tan 的个人知识库项目，启发了 Compiled Truth + Timeline 格式和 Typed Edges 体系
- [Linear.app 设计系统](https://linear.app/) — 暗色精工美学的参考
- [Hermes Agent](https://github.com/NousResearch/hermes) — 运行这个系统的 AI Agent 框架

---

## 📄 License

MIT

---

<p align="center">
  <i>Built with curiosity, not with a plan.</i>
</p>

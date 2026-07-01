<div align="center">
  <img src="assets/icon.svg" width="64" height="64" alt="Knowledge Vault">
  <h1>Knowledge Vault 🏛️</h1>
  <p>个人知识库搭建方案 —— 从数据结构到应用体系</p>
  <p><em>SQLite · FTS5 · 三层分层 · Typed Edges · Canvas Knowledge Graph · MCP</em></p>
  <br>
  <p>
    <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python" alt="Python">
    <img src="https://img.shields.io/badge/SQLite-FTS5-003B57?logo=sqlite" alt="SQLite">
    <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT">
  </p>
</div>

---

## 为什么要做这个？

知识积累久了会散——这个 Obsidian，那个对话记录，还有随手存的代码片段。需要的不只是多一个文件夹来存，而是一套**结构化的知识组织体系**：知道什么该记、怎么分类、如何关联、积累到什么时候该升格。

所以有了这个项目：一个**本地优先、隐私保护**的个人知识库系统，核心不是"存更多"，而是把知识按可信度、用途和生命周期分层。知识图谱可视化只是它的一种应用方式，但现在已经成为我日常观察知识状态的主入口。

> 当前自用规模（2026-07）：约 130+ 条知识条目、370+ 条 typed edges，覆盖技术、项目、笔记、基础设施等 domain。公开仓库只放框架、示例数据和参考实现，不包含私人知识库内容。

---

## ✨ 核心能力

| 能力 | 说明 | 状态 |
|------|------|------|
| **本地优先** | 所有数据存在 SQLite 里，不依赖任何云服务 | ✅ 全量开源 |
| **三级分层** | L0 铁律 → L1 认知校准器 → L2 知识记录库，三层隔离防止认知污染 | ✅ 全量开源 |
| **关系类型体系** | 多种语义边（引用/使用/扩展/矛盾/互补/实现/依赖...），关系不只是一种 | ✅ 全量开源 |
| **双擎搜索** | FTS5 全文搜索 + 可选 BGE 语义向量搜索，关键词和语义双重覆盖 | ✅ 全量开源（语义搜索需 `pip install fastembed`） |
| **CLI + MCP** | 命令行工具 + MCP 协议服务器，可被任何 AI Agent 调用 | ✅ 全量开源 |
| **Canvas 知识图谱** | D3 force + Canvas 2D，支持搜索、过滤、聚焦、置顶、Markdown 详情、PDF 导出 | ✅ 全量开源 |
| **Dashboard 入口** | 侧栏展示知识状态、最近新增/更新、domain/type 分组、高频节点 | ✅ 全量开源 |
| **夜间自动维护** | Dream Cycle 定时重建索引、合并清理、写入日志 | 🔒 私有部署思路公开，定时脚本不放 |

---

## 📦 知识库核心设计

### 1. 三级分层体系（L0 / L1 / L2）

一个库，两种用途，三层隔离。核心边界：不是信息越多越好，而是**信息不能跨层越权**。

| 层 | 作用 | 写入原则 |
|----|------|----------|
| **L2 知识记录库** | 存资料、想法、项目背景、小说设定、工具经验、行业信息 | **尽管装**。它是仓库、书房、杂物间、灵感收纳箱 |
| **L1 认知校准器** | 存会影响 Agent 判断和行为的规则、偏好、教训、决策边界 | **慎重提炼**。只有经过验证、反复使用、确实会影响行为的知识才升级到 L1 |
| **L0 铁律** | Agent 的人格底线、不可违反的底层规则 | **极少写入**。只有"几乎不该变"的才放这里 |

**跨层原则：** L2 随便记 → 反复出现、验证有效 → L1 方法/规则 → 几乎不该变 → L0 铁律。

真正要避免的不是"记录知识太多"，而是**参考资料不小心变成行为准则**。存一篇文章说"某某做法很好"是资料；但如果系统把它当成"用户一定认同这个做法"，就是认知污染。

### 2. 关系类型体系

定义一组 typed edges，每条连接都带有明确含义：

| 关系类型 | 语义 |
|----------|------|
| `references` / `referenced_by` | 引用 / 被引用 |
| `related_to` | 泛关联 |
| `uses` | 使用某工具、方法、组件 |
| `builds_on` | 扩展、升级、基于前置结论 |
| `depends_on` | 依赖某能力或前置条件 |
| `implements` | 实现某设计、协议或方案 |
| `complements` | 互补关系 |
| `contradicts` / `conflicts_with` | 矛盾、冲突 |
| `similar_to` | 相似 |
| `part_of` | 属于某整体 |
| `works_at` | 工作/归属关系 |
| `created` | 创建关系 |
| `mentions` | 提及 |

**自动与手动隔离：** 自动推断的关联和手动创建的关联用 `link_source` 字段隔离，重建时不混淆。公开版只放轻量推断，实际使用中更建议让 Agent 在写入时带上明确关系类型。

### 3. 双擎搜索

- **FTS5 全文索引** — SQLite 内置，无外部依赖，支持中文分词
- **BGE 语义向量** — 512 维嵌入，基于 `BAAI/bge-small-zh-v1.5`
- **混合策略** — 先用 FTS5 精确匹配，无结果时回退到语义搜索

### 4. 条目格式

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

### 5. 数据库 Schema

核心表结构（完整定义见 `schema.sql`）：

| 表 | 用途 |
|:---|:-----|
| `notes` | 笔记主体（标题、内容、类型、层级、领域、置信度、标签文本、使用统计） |
| `tags` / `note_tags` | 标签体系，多对多关联 |
| `links` | 有向语义边（类型、上下文、来源） |
| `note_links` | 兼容的双向关联表 |
| `note_embeddings` | 向量嵌入存储 |
| `notes_fts` | FTS5 全文搜索虚拟表（触发器自动同步） |

---

## 🚀 快速开始

### 前置要求

- Python 3.10+
- SQLite 3（系统自带）

### 安装

```bash
git clone https://github.com/HuiHuitie-zhu/knowledge-vault.git
cd knowledge-vault
pip install -r requirements.txt
python3 vault.py init
```

### 基本用法

```bash
# 添加一条笔记
python3 vault.py add "Python 装饰器" "装饰器是修改函数行为的函数..." --tags python,技巧 --type reference

# 添加时建立关联
python3 vault.py add "Functools 模块" "内置高阶函数工具集..." --link-to 1 --link-type uses

# 搜索
python3 vault.py search "装饰器"

# 语义搜索
python3 vault.py search "函数增强" --semantic

# 查看统计
python3 vault.py stats

# 重建索引 + 图谱关联推断
python3 vault.py reindex [--graph]

# 合并检查（查重 + 低质量检测）
python3 vault.py consolidate
```

### 写入分类原则

添加笔记时指定合适的 `--type`：

| type | 用途 |
|:-----|:-----|
| `rule` | 规则、铁律（layer=0） |
| `standard` | 流程标准（layer=1） |
| `trap` | 踩坑记录 |
| `checklist` | 检查清单 |
| `case` | 具体案例 |
| `reference` | 参考资料、配置说明 |
| `doc` | 文档 |
| `note` | 一般笔记（默认） |

---

## 📖 延伸阅读

以下内容与核心知识库设计解耦，单独阅读：

### 知识图谱可视化

这个仓库附带了一个 D3.js + Canvas 2D 的知识图谱前端。它不是一个"炫酷背景图"，而是我现在实际使用的知识状态入口：用来快速发现孤立节点、最近新增、关系密度、类型分布和需要复核的知识。

<p align="center">
  <img src="assets/graph-preview.png" width="80%" alt="Knowledge Graph 预览">
</p>

当前参考实现包含：

- **Canvas 2D 力导向图**：适合 100-1000 级节点的小型个人知识库。
- **Typed Edge 图例**：不同关系类型使用不同颜色，不再只有"相关"一种边。
- **左侧 Dashboard**：知识总量、关联数、最近新增/更新、domain/type 分组。
- **置顶节点**：重要条目固定显示在列表顶部。
- **搜索 + 类型过滤 + 标签过滤**：从全局图谱快速缩小到局部主题。
- **点击聚焦**：选中节点后弱化无关节点，突出直接关联。
- **Markdown 详情面板**：条目正文支持标题、表格、代码块、引用等格式。
- **PDF/打印导出**：单条知识可导出为适合阅读归档的页面。
- **健康检查 API**：查看 notes、links、embeddings、FTS、孤立节点等状态。

> **注意：** 这个前端仍然是参考实现，不是通用 SaaS 产品。它更适合个人知识库、Agent 记忆库、小型项目知识图谱。如果你有更大规模或多人协作需求，可以保留 SQLite schema，替换前端为 Sigma.js / Cytoscape / Neo4j Browser 等方案。

启动方式：

```bash
python3 seed.py   # 生成示例数据
python3 server.py # 启动 API + 前端
open http://localhost:51420
```

如果你想指向自己的数据库：

```bash
KNOWLEDGE_DB_PATH=/path/to/your/knowledge.db python3 server.py
```

### 跨 Agent 知识共享

Knowledge Vault 通过 **MCP（Model Context Protocol）** 让多个 Agent 共享同一个知识库：

```
SQLite ←→ MCP 服务器 ←→ Claude Code / Cursor / 自定义 Agent
```

注册方式（`.mcp.json`）：

```json
{
  "mcpServers": {
    "knowledge-base": {
      "command": "python3",
      "args": ["path/to/knowledge_mcp.py"]
    }
  }
}
```

MCP 服务器通过环境变量 `KNOWLEDGE_DB_PATH` 指定数据库路径，默认使用同目录下的 `vault.db`。也可通过 `.env` 文件配置（参见 `.env.example`）。

Agent 通过 MCP 工具直接读写知识库：`knowledge_search` / `knowledge_add` / `knowledge_update` 等。Agent A 写入的经验，Agent B 立刻可查——无需同步、无需复制。

### Dream Cycle 夜间维护

定时（每日凌晨）自动执行：健康检查 → 查重合并 → 重建向量索引 → 图谱关联推断 → 报告写入。

### macOS 原生桌面应用

WKWebView 封装的知识图谱桌面端，双击即用、关闭即停，比 Electron 方案节省约 200MB 内存。

---

## 🛠 技术栈

| 层 | 技术 |
|----|------|
| **存储** | SQLite 3 + FTS5 |
| **全文搜索** | SQLite FTS5 + 中文分词 |
| **语义搜索** | BGE (BAAI/bge-small-zh-v1.5) 512-dim |
| **API 服务器** | Python http.server |
| **CLI 工具** | Python（`vault.py`） |
| **MCP 服务器** | Python（`knowledge_mcp.py`） |
| **图谱前端** | D3.js v7 + Canvas 2D |
| **Markdown 渲染** | marked.js |
| **静态依赖** | `d3.v7.min.js` / `marked.min.js` 随仓库提供，方便离线运行 |

---

## 📂 项目结构

```
knowledge-vault/
├── README.md            # 本文档
├── schema.sql           # 数据库 DDL（核心！）
├── vault.py             # CLI 工具（增删查改 + 重建 + 合并）
├── knowledge_mcp.py     # MCP 协议服务器（AI Agent 直接调用）
├── server.py            # HTTP API + 知识图谱前端服务器
├── index.html           # 知识图谱可视化前端（参考实现）
├── d3.v7.min.js         # D3.js 静态依赖
├── marked.min.js        # Markdown 渲染依赖
├── seed.py              # 示例数据生成器
├── setup.sh             # 一键安装脚本
├── requirements.txt     # Python 依赖
├── .env.example         # 环境变量配置模板
├── assets/
│   └── icon.svg         # 项目图标
└── LICENSE              # MIT
```

---

## 设计决策

### 为什么 SQLite 而不是 PostgreSQL / Neo4j？

第一原则：**本地优先**。整个知识库在单文件里随身携带，不需要运行数据库服务器。FTS5 是 SQLite 的隐藏杀手锏，全文搜索能力不输 Elasticsearch 的小规模场景。图数据库对 100-1000 级别的节点过度设计——关系型 + 连接表在这个规模上绰绰有余。

### Typed Edges 为什么重要？

大多数知识工具只告诉你"两个东西有关"，但不告诉你怎么关联的。知道 A "引用" B 和知道 A "矛盾" B 是完全不同的信息熵。带语义的边让图谱不只是"好看"，而是可推理的。

### 为什么用 Canvas 2D 而不是 SVG？

当节点数超过 100 时，SVG DOM 节点和样式计算会明显增加 layout 成本。Canvas 2D 用单画布绘制，避免大量 DOM 节点，足够覆盖个人知识库规模；WebGL（Three.js）在 2D 力导向图场景下反而偏重。

---

## 📖 灵感来源

- [GBrain](https://github.com/raymondwzhao/gbrain) — 条目格式（Compiled Truth + Timeline）受此启发
- [Hermes](https://github.com/NousResearch/hermes) — 运行这个系统的 AI Agent 框架

---

## 📄 License

MIT — Built with curiosity, not with a plan.
